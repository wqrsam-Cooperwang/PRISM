from __future__ import annotations

"""EvidenceFusionEngine orchestration integrating aging, dependency, covariance,
posterior computation, deduplication, and conflict resolution.

This module provides the high-level fuse() entrypoint and constructs a
PosteriorMatchState per the Architecture Freeze.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping, Dict, Any, List, Tuple

import numpy as np

from src.evidence.models import EvidenceResult
from src.inference.models import PosteriorMatchState, PosteriorLatent, EvidenceContribution
from src.evidence.aging import apply_decay
from src.governance.dependency_matrix import DependencyMatrix
from src.inference.covariance import build_covariance_matrix, project_to_psd
from src.inference.posterior import compute_posterior
from src.inference.dedup_conflict import Observation, deduplicate_observations, resolve_conflicts
from src.governance.audit import AuditLogger


EPS = 1e-12


@dataclass
class FusionConfig:
    prior_means: Mapping[str, float]
    prior_variances: Mapping[str, float]
    dependency_matrix: DependencyMatrix | None = None
    conflict_threshold: float = 2.0
    conflict_prior_inflation: float = 4.0


class EvidenceFusionEngine:
    def __init__(self, config: FusionConfig) -> None:
        self.config = config
        self.latents = sorted(list(config.prior_means.keys()))
        self.latent_index = {name: i for i, name in enumerate(self.latents)}
        self.audit = AuditLogger()

    def fuse(self, evidences: Iterable[EvidenceResult]) -> PosteriorMatchState:
        now = datetime.now(timezone.utc)
        # Convert EvidenceResult -> Observations list
        raw_obs: List[Observation] = []
        for e in evidences:
            r_eff = apply_decay(e, now=now)
            for t in e.targets:
                if t not in e.suggestion:
                    continue
                if t not in e.variance:
                    continue
                # Validate target exists in priors; if not, skip with audit
                if t not in self.latent_index:
                    self.audit.record(
                        {
                            "event_type": "unknown_target",
                            "message": f"Evidence for unknown target {t} from {e.provider_id} ignored",
                            "timestamp": now.isoformat().replace("+00:00", "Z"),
                        }
                    )
                    continue
                y = float(e.suggestion[t])
                v = float(e.variance[t])
                v = max(v, EPS)
                raw_obs.append(Observation(provider=e.provider_id, target=t, y=y, var=v, reliability=float(r_eff)))

        # Group observations by target
        obs_by_target: Dict[str, List[Observation]] = {}
        for o in raw_obs:
            obs_by_target.setdefault(o.target, []).append(o)

        # Per-target dedup and conflict resolution
        merged_obs_all: List[Observation] = []
        per_latent_prior_vars: Dict[str, float] = {}
        for latent in self.latents:
            prior_var = float(self.config.prior_variances.get(latent, 1.0))
            per_latent_prior_vars[latent] = prior_var
            obs_list = obs_by_target.get(latent, [])
            if not obs_list:
                continue
            merged = deduplicate_observations(obs_list, dependency_matrix=self.config.dependency_matrix, kappa=1.0, audit=self.audit)
            resolved, new_prior = resolve_conflicts(merged, prior_variance=prior_var, threshold=self.config.conflict_threshold, inflation=self.config.conflict_prior_inflation, audit=self.audit)
            per_latent_prior_vars[latent] = new_prior
            merged_obs_all.extend(resolved)

        # If no observations at all, return prior-only PosteriorMatchState
        d = len(self.latents)
        if len(merged_obs_all) == 0:
            p_latents = []
            for i, name in enumerate(self.latents):
                pm = PosteriorLatent(
                    name=name,
                    prior_mean=float(self.config.prior_means[name]),
                    prior_variance=float(self.config.prior_variances[name]),
                    posterior_mean=float(self.config.prior_means[name]),
                    posterior_variance=float(self.config.prior_variances[name]),
                    contributors=(),
                )
                p_latents.append(pm)
            cov_map = {}
            for a in self.latents:
                for b in self.latents:
                    cov_map[(a, b)] = 0.0
            pm = PosteriorMatchState(
                match_id="",
                generated_at=now.isoformat().replace("+00:00", "Z"),
                lambda_home=p_latents[0] if p_latents else PosteriorLatent(name="lambda_home", prior_mean=0.0, prior_variance=1.0, posterior_mean=0.0, posterior_variance=1.0, contributors=()),
                lambda_away=p_latents[1] if len(p_latents) > 1 else (p_latents[0] if p_latents else PosteriorLatent(name="lambda_away", prior_mean=0.0, prior_variance=1.0, posterior_mean=0.0, posterior_variance=1.0, contributors=())),
                tempo=next((pl for pl in p_latents if pl.name == "tempo"), p_latents[0] if p_latents else PosteriorLatent(name="tempo", prior_mean=1.0, prior_variance=0.1, posterior_mean=1.0, posterior_variance=0.1, contributors=())),
                tactical_state={},
                rotation_state={},
                scenario_weights={},
                covariance_matrix=cov_map,
                evidence_summary=(),
                entropy=0.0,
            )
            return pm

        # Build H, Y, V
        n = len(merged_obs_all)
        d = len(self.latents)
        H = np.zeros((n, d), dtype=float)
        Y = np.zeros((n,), dtype=float)
        observations_for_cov = []
        for i, ob in enumerate(merged_obs_all):
            idx = self.latent_index[ob.target]
            H[i, idx] = 1.0
            Y[i] = ob.y
            observations_for_cov.append({"provider": ob.provider, "var": ob.var})

        V = build_covariance_matrix(observations_for_cov, dependency_matrix=self.config.dependency_matrix, kappa=1.0)
        # ensure PSD
        V = project_to_psd(V)

        # Build prior vectors/matrices
        mu0 = np.array([float(self.config.prior_means[name]) for name in self.latents], dtype=float)
        Sigma0 = np.diag([max(float(per_latent_prior_vars.get(name, self.config.prior_variances.get(name, 1.0))), EPS) for name in self.latents])

        # compute posterior
        mu_post, Sigma_post = compute_posterior(mu0, Sigma0, H, Y, V)

        # contributors: compute precision weights
        precisions = np.array([1.0 / max(EPS, ob.var) for ob in merged_obs_all], dtype=float)
        norm_weights = precisions / max(EPS, float(np.sum(precisions)))
        contributor_map: Dict[str, List[EvidenceContribution]] = {name: [] for name in self.latents}
        for i, ob in enumerate(merged_obs_all):
            name = ob.target
            contrib = EvidenceContribution(
                evidence_id=f"{ob.provider}:{ob.target}",
                provider_id=ob.provider,
                suggested=float(ob.y),
                variance=float(ob.var),
                weight=float(norm_weights[i]),
                reliability=float(ob.reliability),
                normalized_weight=float(norm_weights[i]),
            )
            contributor_map[name].append(contrib)

        # build PosteriorLatent list
        p_latents = []
        for i, name in enumerate(self.latents):
            pl = PosteriorLatent(
                name=name,
                prior_mean=float(mu0[i]),
                prior_variance=float(Sigma0[i, i]),
                posterior_mean=float(mu_post[i]),
                posterior_variance=float(Sigma_post[i, i]),
                contributors=tuple(contributor_map[name]),
            )
            p_latents.append(pl)

        cov_map: Dict[Tuple[str, str], float] = {}
        for i, a in enumerate(self.latents):
            for j, b in enumerate(self.latents):
                cov_map[(a, b)] = float(Sigma_post[i, j])

        # entropy approx
        entropy = 0.0
        for i in range(len(self.latents)):
            entropy += 0.5 * np.log(2 * np.pi * np.e * max(EPS, Sigma_post[i, i]))

        pm = PosteriorMatchState(
            match_id="",
            generated_at=now.isoformat().replace("+00:00", "Z"),
            lambda_home=p_latents[0] if len(p_latents) > 0 else PosteriorLatent(name="lambda_home", prior_mean=0.0, prior_variance=1.0, posterior_mean=0.0, posterior_variance=1.0, contributors=()),
            lambda_away=p_latents[1] if len(p_latents) > 1 else (p_latents[0] if p_latents else PosteriorLatent(name="lambda_away", prior_mean=0.0, prior_variance=1.0, posterior_mean=0.0, posterior_variance=1.0, contributors=())),
            tempo=next((pl for pl in p_latents if pl.name == "tempo"), p_latents[0] if p_latents else PosteriorLatent(name="tempo", prior_mean=1.0, prior_variance=0.1, posterior_mean=1.0, posterior_variance=0.1, contributors=())),
            tactical_state={},
            rotation_state={},
            scenario_weights={},
            covariance_matrix=cov_map,
            evidence_summary=tuple({"provider": ob.provider, "target": ob.target, "y": ob.y, "var": ob.var, "reliability": ob.reliability} for ob in merged_obs_all),
            entropy=float(entropy),
        )
        return pm

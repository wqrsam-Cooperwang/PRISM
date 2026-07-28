"""Core EvidenceFusionEngine implementation.

This module implements the EvidenceFusionEngine according to the Architecture
Freeze. It focuses on mathematical correctness and numerical stability first.

Required external dependency: numpy
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping, Tuple, Dict, Any

import numpy as np
from numpy.linalg import LinAlgError

from src.evidence.models import EvidenceResult
from src.inference.models import PosteriorMatchState, PosteriorLatent, EvidenceContribution
from src.evidence.aging import apply_decay
from src.governance.dependency_matrix import DependencyMatrix


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
        # build latent ordering
        self.latents = sorted(list(config.prior_means.keys()))
        self.latent_index = {name: i for i, name in enumerate(self.latents)}

    def _fingerprint(self, e: EvidenceResult, target: str) -> Tuple[str, str, float, float]:
        # deterministic fingerprint for duplicate detection
        val = float(e.suggestion[target])
        var = float(e.variance[target])
        return (e.provider_id, target, round(val, 12), round(var, 12))

    def _collapse_duplicates(self, observations: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        # observations: list of dicts with keys: provider, target, y, var, reliability
        # collapse by fingerprint
        groups: Dict[Tuple[str, str, float, float], list[Dict[str, Any]]] = {}
        for obs in observations:
            key = (obs["provider"], obs["target"], round(float(obs["y"]), 12), round(float(obs["var"]), 12))
            groups.setdefault(key, []).append(obs)
        collapsed = []
        for key, members in groups.items():
            if len(members) == 1:
                collapsed.append(members[0])
                continue
            # precision-weighted combine
            sum_wy = 0.0
            sum_w = 0.0
            for m in members:
                v = float(m["var"]) if float(m["var"]) > EPS else EPS
                w = 1.0 / v
                sum_wy += float(m["y"]) * w
                sum_w += w
            y_comb = sum_wy / sum_w
            v_comb = 1.0 / sum_w
            # aggregate reliability/weight as weighted average
            rel = float(sum(m["reliability"] for m in members) / len(members))
            collapsed.append({
                "provider": members[0]["provider"],
                "target": members[0]["target"],
                "y": float(y_comb),
                "var": float(v_comb),
                "reliability": float(rel),
            })
        return collapsed

    def _assemble_observations(self, evidences: Iterable[EvidenceResult]) -> list[Dict[str, Any]]:
        obs = []
        now = datetime.now(timezone.utc)
        for e in evidences:
            # validate minimal fields already done externally; compute decayed reliability
            r_eff = apply_decay(e, now=now)
            for t in e.targets:
                if t not in e.suggestion:
                    continue
                y = float(e.suggestion[t])
                v = float(e.variance[t])
                v = max(v, EPS)
                obs.append({
                    "provider": e.provider_id,
                    "target": t,
                    "y": y,
                    "var": v,
                    "reliability": float(r_eff),
                })
        # collapse duplicates
        obs = self._collapse_duplicates(obs)
        return obs

    def _build_covariance(self, observations: list[Dict[str, Any]]) -> np.ndarray:
        n = len(observations)
        V = np.zeros((n, n), dtype=float)
        for i in range(n):
            V[i, i] = observations[i]["var"]
        # off-diagonals via dependency matrix
        dm = self.config.dependency_matrix
        if dm is None:
            # assume independence
            return V
        for i in range(n):
            for j in range(i + 1, n):
                prov_i = observations[i]["provider"]
                prov_j = observations[j]["provider"]
                rho = dm.correlation(prov_i, prov_j)
                cov = rho * np.sqrt(max(EPS, observations[i]["var"] * observations[j]["var"]))
                V[i, j] = cov
                V[j, i] = cov
        return V

    def _ensure_psd(self, M: np.ndarray) -> np.ndarray:
        # ensure symmetric
        M = 0.5 * (M + M.T)
        try:
            # attempt Cholesky; if succeeds, it's PSD
            np.linalg.cholesky(M + EPS * np.eye(M.shape[0]))
            return M
        except LinAlgError:
            # project to nearest PSD via eigenvalue clipping
            vals, vecs = np.linalg.eigh(M)
            vals_clipped = np.clip(vals, a_min=0.0, a_max=None)
            M_psd = (vecs * vals_clipped) @ vecs.T
            # ensure symmetry
            M_psd = 0.5 * (M_psd + M_psd.T)
            return M_psd

    def fuse(self, evidences: Iterable[EvidenceResult]) -> PosteriorMatchState:
        # assemble observations
        observations = self._assemble_observations(evidences)
        n = len(observations)
        d = len(self.latents)

        # prior mean and covariance
        mu0 = np.array([float(self.config.prior_means[name]) for name in self.latents], dtype=float)
        Sigma0 = np.diag([max(float(self.config.prior_variances[name]), EPS) for name in self.latents])

        if n == 0:
            # return prior-only posterior
            contributors = ()
            lambda_home = PosteriorLatent(
                name=self.latents[0],
                prior_mean=mu0[0],
                prior_variance=Sigma0[0, 0],
                posterior_mean=mu0[0],
                posterior_variance=Sigma0[0, 0],
                contributors=contributors,
            )
            # build minimal PosteriorMatchState with priors for known latents
            pm = PosteriorMatchState(
                match_id="", generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                lambda_home=lambda_home,
                lambda_away=lambda_home,
                tempo=lambda_home,
                tactical_state={}, rotation_state={}, scenario_weights={}, covariance_matrix={}, evidence_summary=(), entropy=0.0,
            )
            return pm

        # build H and Y
        H = np.zeros((n, d), dtype=float)
        Y = np.zeros((n,), dtype=float)
        for i, ob in enumerate(observations):
            tgt = ob["target"]
            if tgt not in self.latent_index:
                raise ValueError(f"Unknown latent target in observation: {tgt}")
            j = self.latent_index[tgt]
            H[i, j] = 1.0
            Y[i] = float(ob["y"])

        V = self._build_covariance(observations)
        # ensure PSD and numeric stability
        V = self._ensure_psd(V + EPS * np.eye(n))
        # compute inverses safely
        try:
            Vinv = np.linalg.inv(V)
        except LinAlgError:
            # fallback to pseudo-inverse
            Vinv = np.linalg.pinv(V)

        # Compute posterior precision and mean
        Sigma0_inv = np.linalg.inv(Sigma0)
        A = Sigma0_inv + H.T @ Vinv @ H
        # ensure PSD
        A = 0.5 * (A + A.T)
        try:
            Ainv = np.linalg.inv(A)
        except LinAlgError:
            Ainv = np.linalg.pinv(A)
        mu_post = Ainv @ (Sigma0_inv @ mu0 + H.T @ Vinv @ Y)
        Sigma_post = Ainv

        # ensure PSD and non-negative variances
        Sigma_post = self._ensure_psd(Sigma_post)
        # clip variances
        variances = np.diag(Sigma_post)
        variances = np.clip(variances, a_min=EPS, a_max=None)
        for i in range(d):
            Sigma_post[i, i] = variances[i]

        # build contributors list per latent
        contributor_map: Dict[int, list[EvidenceContribution]] = {i: [] for i in range(d)}
        # compute normalized weights per observation: precision-weighted
        precisions = np.array([1.0 / max(EPS, ob["var"]) for ob in observations], dtype=float)
        total_prec = np.sum(precisions)
        norm_weights = precisions / max(EPS, total_prec)
        for i, ob in enumerate(observations):
            j = self.latent_index[ob["target"]]
            contrib = EvidenceContribution(
                evidence_id=f"{ob['provider']}:{ob['target']}",
                provider_id=ob["provider"],
                suggested=float(ob["y"]),
                variance=float(ob["var"]),
                weight=float(norm_weights[i]),
                reliability=float(ob["reliability"]),
                normalized_weight=float(norm_weights[i]),
            )
            contributor_map[j].append(contrib)

        # wrap into PosteriorMatchState fields
        p_latents = []
        for i, name in enumerate(self.latents):
            pl = PosteriorLatent(
                name=name,
                prior_mean=float(mu0[i]),
                prior_variance=float(Sigma0[i, i]),
                posterior_mean=float(mu_post[i]),
                posterior_variance=float(Sigma_post[i, i]),
                contributors=tuple(contributor_map[i]),
            )
            p_latents.append(pl)

        # build covariance map
        cov_map: Dict[Tuple[str, str], float] = {}
        for i, a in enumerate(self.latents):
            for j, b in enumerate(self.latents):
                cov_map[(a, b)] = float(Sigma_post[i, j])

        # compute entropy approx: sum of 0.5*log(2*pi*e*var) for independent approx
        entropy = 0.0
        for i in range(d):
            entropy += 0.5 * np.log(2 * np.pi * np.e * max(EPS, Sigma_post[i, i]))

        pm = PosteriorMatchState(
            match_id="",
            generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            lambda_home=p_latents[0] if len(p_latents) > 0 else PosteriorLatent(name="lambda_home", prior_mean=0.0, prior_variance=1.0, posterior_mean=0.0, posterior_variance=1.0, contributors=()),
            lambda_away=p_latents[1] if len(p_latents) > 1 else p_latents[0] if p_latents else PosteriorLatent(name="lambda_away", prior_mean=0.0, prior_variance=1.0, posterior_mean=0.0, posterior_variance=1.0, contributors=()),
            tempo=next((pl for pl in p_latents if pl.name == "tempo"), p_latents[0] if p_latents else PosteriorLatent(name="tempo", prior_mean=1.0, prior_variance=0.1, posterior_mean=1.0, posterior_variance=0.1, contributors=())),
            tactical_state={},
            rotation_state={},
            scenario_weights={},
            covariance_matrix=cov_map,
            evidence_summary=tuple({"provider": ob["provider"], "target": ob["target"], "y": ob["y"], "var": ob["var"], "reliability": ob["reliability"]} for ob in observations),
            entropy=float(entropy),
        )
        return pm

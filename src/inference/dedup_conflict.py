"""Duplicate detection and conflict resolution utilities for EvidenceFusion.

Implements:
- fingerprinting
- duplicate grouping
- precision-weighted merge using GLS for correlated observations
- conflict metric and prior inflation strategy
- governance audit record emission (simple in-memory logger stub)

Golden Rule: every mathematical routine has an analytic reference test.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, List, Dict, Tuple

import numpy as np

from src.governance.dependency_matrix import DependencyMatrix
from src.governance.audit import AuditLogger, AuditRecord

EPS = 1e-12


@dataclass
class Observation:
    provider: str
    target: str
    y: float
    var: float
    reliability: float


def fingerprint(obs: Observation) -> Tuple[str, str, float, float]:
    return (obs.provider, obs.target, round(float(obs.y), 12), round(float(obs.var), 12))


def group_duplicates(observations: Iterable[Observation]) -> Dict[Tuple[str, str, float, float], List[Observation]]:
    groups: Dict[Tuple[str, str, float, float], List[Observation]] = {}
    for o in observations:
        key = fingerprint(o)
        groups.setdefault(key, []).append(o)
    return groups


def merge_group_gls(group: List[Observation], dependency_matrix: DependencyMatrix | None = None, kappa: float = 1.0) -> Observation:
    """Merge a group of observations (identical y/value) using GLS that accounts for correlations.

    The combined variance is v* = 1 / (1^T V^{-1} 1) where V is the covariance of the group.
    The combined estimate y* = (1^T V^{-1} y_vec) * v* (but since y_vec elements equal y, y* = y).
    """
    n = len(group)
    if n == 1:
        return group[0]
    ys = np.array([o.y for o in group], dtype=float)
    vs = np.array([max(EPS, o.var) for o in group], dtype=float)
    providers = [o.provider for o in group]
    # Build covariance matrix
    V = np.zeros((n, n), dtype=float)
    for i in range(n):
        V[i, i] = vs[i]
    if dependency_matrix is not None:
        for i in range(n):
            for j in range(i + 1, n):
                s = dependency_matrix.get(providers[i], providers[j])
                rho = min(1.0, float(kappa) * float(s))
                cov = rho * np.sqrt(vs[i] * vs[j])
                V[i, j] = cov
                V[j, i] = cov
    # invert V safely
    try:
        V_inv = np.linalg.inv(V)
    except np.linalg.LinAlgError:
        V_inv = np.linalg.pinv(V)
    one = np.ones((n,), dtype=float)
    denom = float(one.T @ V_inv @ one)
    if denom <= 0:
        # fallback to precision-weighted independent formula
        w = 1.0 / vs
        y_comb = float(np.sum(w * ys) / np.sum(w))
        v_comb = float(1.0 / np.sum(w))
    else:
        v_comb = 1.0 / denom
        # Since ys may not be exactly identical numerically, compute weighted mean
        y_comb = float(v_comb * (one.T @ V_inv @ ys))
    # aggregate reliability as mean
    rel = float(sum(o.reliability for o in group) / n)
    return Observation(provider=group[0].provider, target=group[0].target, y=y_comb, var=v_comb, reliability=rel)


def deduplicate_observations(observations: Iterable[Observation], dependency_matrix: DependencyMatrix | None = None, kappa: float = 1.0, audit: AuditLogger | None = None) -> List[Observation]:
    groups = group_duplicates(observations)
    merged: List[Observation] = []
    for key, group in groups.items():
        if len(group) == 1:
            merged.append(group[0])
            continue
        merged_obs = merge_group_gls(group, dependency_matrix=dependency_matrix, kappa=kappa)
        merged.append(merged_obs)
        if audit is not None:
            audit.record(AuditRecord(event_type="dedup", message=f"Merged {len(group)} duplicates for target {merged_obs.target} from provider {merged_obs.provider}", metadata={"providers": [o.provider for o in group]}))
    return merged


def conflict_metric(observations: Iterable[Observation]) -> float:
    ys = [o.y for o in observations]
    vars = [o.var for o in observations]
    if not ys:
        return 0.0
    y_max = max(ys)
    y_min = min(ys)
    mean_var = float(sum(vars) / len(vars)) if vars else 0.0
    if mean_var <= 0:
        return float('inf') if y_max != y_min else 0.0
    return float((y_max - y_min) / (mean_var ** 0.5))


def resolve_conflicts(observations: Iterable[Observation], prior_variance: float, threshold: float = 1.5, inflation: float = 2.0, audit: AuditLogger | None = None) -> Tuple[List[Observation], float]:
    """Detect conflicts per target and apply prior variance inflation and down-weighting.

    Returns modified observations list and possibly inflated prior_variance.
    """
    obs_list = list(observations)
    if not obs_list:
        return obs_list, prior_variance
    c = conflict_metric(obs_list)
    if c <= threshold:
        return obs_list, prior_variance
    # conflict detected: inflate prior variance
    new_prior_var = float(prior_variance * inflation)
    # down-weight low-reliability evidence: multiply var by factor for those below median reliability
    reliabilities = [o.reliability for o in obs_list]
    median_rel = float(np.median(reliabilities))
    new_obs = []
    for o in obs_list:
        if o.reliability < median_rel:
            # increase variance (lower precision)
            o2 = Observation(provider=o.provider, target=o.target, y=o.y, var=float(o.var * inflation), reliability=o.reliability)
            new_obs.append(o2)
        else:
            new_obs.append(o)
    if audit is not None:
        audit.record(AuditRecord(event_type="conflict", message=f"Conflict detected (C={c:.3f}) inflated prior var {prior_variance}->{new_prior_var}", metadata={"conflict_metric": c}))
    return new_obs, new_prior_var

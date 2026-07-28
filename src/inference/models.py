from __future__ import annotations

"""Posterior models for inference results.

These dataclasses represent the outputs of the EvidenceFusionEngine and are
frozen by the Architecture Freeze.
"""

from dataclasses import dataclass
from typing import Mapping, Any


@dataclass(frozen=True)
class EvidenceContribution:
    evidence_id: str
    provider_id: str
    suggested: float
    variance: float
    weight: float
    reliability: float
    normalized_weight: float


@dataclass(frozen=True)
class PosteriorLatent:
    name: str
    prior_mean: float
    prior_variance: float
    posterior_mean: float
    posterior_variance: float
    contributors: tuple[EvidenceContribution, ...]


@dataclass(frozen=True)
class PosteriorMatchState:
    match_id: str
    generated_at: str  # ISO 8601
    lambda_home: PosteriorLatent
    lambda_away: PosteriorLatent
    tempo: PosteriorLatent
    tactical_state: Mapping[str, float]
    rotation_state: Mapping[str, float]
    scenario_weights: Mapping[str, float]
    covariance_matrix: Mapping[tuple[str, str], float]
    evidence_summary: tuple[Mapping[str, Any], ...]
    entropy: float

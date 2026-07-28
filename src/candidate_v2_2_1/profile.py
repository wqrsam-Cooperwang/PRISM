"""Governed V2.2.1 candidate dispersion profile assembly.

This module combines conditional tail-width controls with bounded scenario-mixture
weights while remaining isolated from V2.1 production behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.candidate_v2_2_1.dispersion import (
    DispersionDecision,
    DispersionSignals,
    conditional_tail_width,
)
from src.candidate_v2_2_1.scenario_mix import ScenarioMixture, build_scenario_mixture

CANDIDATE_PROFILE_VERSION = "V2.2.1-research-1"


@dataclass(frozen=True)
class CandidateDispersionProfile:
    """One immutable research profile derived from governed pre-match signals."""

    version: str
    decision: DispersionDecision
    mixture: ScenarioMixture


def build_candidate_dispersion_profile(
    signals: DispersionSignals,
) -> CandidateDispersionProfile:
    """Assemble one fail-closed V2.2.1 dispersion profile from governed signals."""

    decision = conditional_tail_width(signals)
    mixture = build_scenario_mixture(decision)
    total_weight = sum(
        (
            mixture.baseline_weight,
            mixture.low_event_weight,
            mixture.dominant_tail_weight,
        )
    )
    if abs(total_weight - 1.0) > 1e-12:
        raise ValueError("scenario mixture weights must sum to 1")
    if mixture.baseline_weight < 0.0:
        raise ValueError("baseline scenario weight must be non-negative")

    return CandidateDispersionProfile(
        version=CANDIDATE_PROFILE_VERSION,
        decision=decision,
        mixture=mixture,
    )

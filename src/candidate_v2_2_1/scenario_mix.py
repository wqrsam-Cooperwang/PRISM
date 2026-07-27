"""Research-only scenario mixture controls for PRISM V2.2.1.

This module converts governed dispersion decisions into bounded mixture weights.
It remains isolated from V2.1 production and does not mutate baseline expected goals.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from src.candidate_v2_2_1.dispersion import DispersionDecision


@dataclass(frozen=True)
class ScenarioMixture:
    """Bounded candidate-only mixture allocation across baseline and tail scenarios."""

    baseline_weight: float
    low_event_weight: float
    dominant_tail_weight: float


MAX_TOTAL_SCENARIO_WEIGHT = 0.70


def build_scenario_mixture(decision: DispersionDecision) -> ScenarioMixture:
    """Build a fail-closed scenario mixture from a governed dispersion decision."""

    values = (
        decision.home_width,
        decision.away_width,
        decision.low_event_weight,
        decision.dominant_tail_weight,
    )
    if any(not isfinite(value) for value in values):
        raise ValueError("dispersion decision values must be finite")
    if decision.home_width <= 0.0 or decision.away_width <= 0.0:
        raise ValueError("dispersion widths must be positive")
    if not 0.0 <= decision.low_event_weight <= 1.0:
        raise ValueError("low_event_weight must be in [0, 1]")
    if not 0.0 <= decision.dominant_tail_weight <= 1.0:
        raise ValueError("dominant_tail_weight must be in [0, 1]")

    requested_total = decision.low_event_weight + decision.dominant_tail_weight
    if requested_total <= MAX_TOTAL_SCENARIO_WEIGHT:
        low_event_weight = decision.low_event_weight
        dominant_tail_weight = decision.dominant_tail_weight
    elif requested_total == 0.0:
        low_event_weight = 0.0
        dominant_tail_weight = 0.0
    else:
        scale = MAX_TOTAL_SCENARIO_WEIGHT / requested_total
        low_event_weight = decision.low_event_weight * scale
        dominant_tail_weight = decision.dominant_tail_weight * scale

    baseline_weight = 1.0 - low_event_weight - dominant_tail_weight
    return ScenarioMixture(
        baseline_weight=baseline_weight,
        low_event_weight=low_event_weight,
        dominant_tail_weight=dominant_tail_weight,
    )

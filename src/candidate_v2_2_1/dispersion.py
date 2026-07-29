"""Research-only scenario dispersion controls for PRISM V2.2.1 candidate.

This module is intentionally isolated from V2.1 production. It adjusts the width of a
candidate score distribution from governed scenario signals without mutating baseline
expected goals.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class DispersionSignals:
    """Governed inputs that may widen or narrow candidate scoreline tails."""

    regime_break: float = 0.0
    low_event_risk: float = 0.0
    dominance_risk: float = 0.0
    information_uncertainty: float = 0.0


@dataclass(frozen=True)
class DispersionDecision:
    """Research-only width multipliers for home and away score distributions."""

    home_width: float
    away_width: float
    low_event_weight: float
    dominant_tail_weight: float


def conditional_tail_width(signals: DispersionSignals) -> DispersionDecision:
    """Map scenario signals into bounded candidate-only dispersion controls.

    The function does not alter mean goal expectations. It only controls candidate
    distribution width and explicit low-event / dominant-tail scenario weights.

    Information uncertainty is deliberately non-directional: it widens both score
    distributions but cannot create low-event or dominant-tail scenario mass by itself.
    Scenario weights require scenario-specific governed evidence.

    Mutually contradictory low-event and directional-tail signals are damped before
    allocation. Conflict damping is share-aware: the weaker requested tail absorbs more
    of the penalty, preserving a clearly supported scenario while preventing simultaneous
    saturation of incompatible tails. A conflict-dependent joint tail budget then
    guarantees that contradictory scenarios retain governed baseline probability mass.
    """

    values = (
        signals.regime_break,
        signals.low_event_risk,
        signals.dominance_risk,
        signals.information_uncertainty,
    )
    if any(not isfinite(value) or value < 0.0 or value > 1.0 for value in values):
        raise ValueError("dispersion signals must be finite values in [0, 1]")

    uncertainty = 0.30 * signals.information_uncertainty
    regime = 0.35 * signals.regime_break
    dominance = 0.45 * signals.dominance_risk
    low_event = 0.40 * signals.low_event_risk

    directional_signal = max(signals.regime_break, signals.dominance_risk)
    scenario_conflict = signals.low_event_risk * directional_signal
    width_conflict_damping = 1.0 - 0.35 * scenario_conflict

    home_delta = uncertainty + regime + dominance - 0.15 * signals.low_event_risk
    away_delta = uncertainty + 0.10 * signals.regime_break - 0.15 * signals.dominance_risk
    home_width = _bounded(1.0 + home_delta * width_conflict_damping)
    away_width = _bounded(1.0 + away_delta * width_conflict_damping)

    requested_low_event = low_event
    requested_dominant_tail = dominance + 0.15 * signals.regime_break
    requested_total = requested_low_event + requested_dominant_tail
    if requested_total == 0.0:
        low_event_share = 0.0
        dominant_tail_share = 0.0
    else:
        low_event_share = requested_low_event / requested_total
        dominant_tail_share = requested_dominant_tail / requested_total

    low_event_damping = 1.0 - 0.35 * scenario_conflict * dominant_tail_share
    dominant_tail_damping = 1.0 - 0.35 * scenario_conflict * low_event_share
    low_event_weight = _bounded_weight(requested_low_event * low_event_damping)
    dominant_tail_weight = _bounded_weight(
        requested_dominant_tail * dominant_tail_damping
    )

    joint_tail_budget = 1.0 - 0.30 * scenario_conflict
    allocated_tail = low_event_weight + dominant_tail_weight
    if allocated_tail > joint_tail_budget:
        budget_scale = joint_tail_budget / allocated_tail
        low_event_weight *= budget_scale
        dominant_tail_weight *= budget_scale

    return DispersionDecision(
        home_width=home_width,
        away_width=away_width,
        low_event_weight=low_event_weight,
        dominant_tail_weight=dominant_tail_weight,
    )


def _bounded(value: float) -> float:
    return min(1.80, max(0.75, value))


def _bounded_weight(value: float) -> float:
    return min(0.60, max(0.0, value))

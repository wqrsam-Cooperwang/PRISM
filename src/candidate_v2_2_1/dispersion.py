"""Research-only scenario dispersion controls for PRISM V2.2.1 candidate.

This module is intentionally isolated from V2.1 production. It adjusts the width of a
candidate score distribution from governed scenario signals without mutating baseline
expected goals.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


_SCENARIO_ACTIVATION_FLOOR = 0.15
_CONFLICT_UNCERTAINTY_WEIGHT = 0.20
_AWAY_LOW_EVENT_NARROWING = 0.10


@dataclass(frozen=True)
class DispersionSignals:
    """Governed inputs that may widen or narrow candidate scoreline tails."""

    regime_break: float = 0.0
    low_event_risk: float = 0.0
    dominance_risk: float = 0.0
    information_uncertainty: float = 0.0
    directional_evidence_overlap: float = 0.0


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

    Sub-threshold scenario evidence may still adjust distribution width, but it cannot
    allocate explicit scenario mass. Above the activation floor, smoothstep activation
    avoids a discontinuous jump while ensuring weak evidence cannot create brittle tails.

    Mutually contradictory low-event and directional-tail signals are damped before
    allocation. Conflict damping is share-aware: the weaker requested tail absorbs more
    of the penalty, preserving a clearly supported scenario while preventing simultaneous
    saturation of incompatible tails. A conflict-dependent joint tail budget then
    guarantees that contradictory scenarios retain governed baseline probability mass.

    Contradictory evidence also creates epistemic uncertainty. That uncertainty is
    redistributed symmetrically into both widths before directional conflict damping, so
    a low-event-versus-dominance disagreement cannot make either side spuriously narrow.

    Low-event evidence narrows both score distributions when no directional scenario is
    supported. The away-side narrowing decays quadratically as cumulative directional
    evidence rises, preventing low-event suppression from erasing a governed regime-break
    or dominant-tail pathway while retaining a conservative low-event response under weak
    directionality.

    Regime-break and dominance evidence are combined as a bounded probabilistic union for
    width and conflict control. A governed overlap signal discounts only the incremental
    union gain when both inputs may derive from shared evidence. The same overlap control
    also discounts the weaker activated contribution when explicit dominant-tail mass is
    allocated. Zero overlap retains independent evidence accumulation; full overlap falls
    back to the stronger contribution. This prevents double counting across both width and
    scenario-mass paths while preserving either signal in isolation.
    """

    values = (
        signals.regime_break,
        signals.low_event_risk,
        signals.dominance_risk,
        signals.information_uncertainty,
        signals.directional_evidence_overlap,
    )
    if any(not isfinite(value) or value < 0.0 or value > 1.0 for value in values):
        raise ValueError("dispersion signals must be finite values in [0, 1]")

    uncertainty = 0.30 * signals.information_uncertainty
    regime = 0.35 * signals.regime_break
    dominance = 0.45 * signals.dominance_risk

    directional_signal = _overlap_adjusted_union(
        signals.regime_break,
        signals.dominance_risk,
        signals.directional_evidence_overlap,
    )
    scenario_conflict = signals.low_event_risk * directional_signal
    conflict_uncertainty = _CONFLICT_UNCERTAINTY_WEIGHT * scenario_conflict
    width_conflict_damping = 1.0 - 0.35 * scenario_conflict
    away_low_event_narrowing = (
        _AWAY_LOW_EVENT_NARROWING
        * signals.low_event_risk
        * (1.0 - directional_signal) ** 2
    )

    home_delta = (
        uncertainty
        + conflict_uncertainty
        + regime
        + dominance
        - 0.15 * signals.low_event_risk
    )
    away_delta = (
        uncertainty
        + conflict_uncertainty
        + 0.10 * signals.regime_break
        - 0.15 * signals.dominance_risk
        - away_low_event_narrowing
    )
    home_width = _bounded(1.0 + home_delta * width_conflict_damping)
    away_width = _bounded(1.0 + away_delta * width_conflict_damping)

    activated_low_event = _scenario_activation(signals.low_event_risk)
    activated_regime = _scenario_activation(signals.regime_break)
    activated_dominance = _scenario_activation(signals.dominance_risk)
    requested_low_event = 0.40 * activated_low_event
    requested_dominant_tail = _overlap_adjusted_additive_support(
        0.45 * activated_dominance,
        0.15 * activated_regime,
        signals.directional_evidence_overlap,
    )
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


def _overlap_adjusted_union(first: float, second: float, overlap: float) -> float:
    independent_union = 1.0 - (1.0 - first) * (1.0 - second)
    strongest_signal = max(first, second)
    incremental_union_gain = independent_union - strongest_signal
    return independent_union - overlap * incremental_union_gain


def _overlap_adjusted_additive_support(
    first: float,
    second: float,
    overlap: float,
) -> float:
    independent_support = first + second
    strongest_support = max(first, second)
    incremental_support = independent_support - strongest_support
    return independent_support - overlap * incremental_support


def _scenario_activation(value: float) -> float:
    if value <= _SCENARIO_ACTIVATION_FLOOR:
        return 0.0
    scaled = (value - _SCENARIO_ACTIVATION_FLOOR) / (
        1.0 - _SCENARIO_ACTIVATION_FLOOR
    )
    return scaled * scaled * (3.0 - 2.0 * scaled)


def _bounded(value: float) -> float:
    return min(1.80, max(0.75, value))


def _bounded_weight(value: float) -> float:
    return min(0.60, max(0.0, value))

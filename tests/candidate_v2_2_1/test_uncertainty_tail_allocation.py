"""Governed uncertainty validation for V2.2.1 scenario allocation."""

from __future__ import annotations

import pytest

from src.candidate_v2_2_1.dispersion import DispersionSignals, conditional_tail_width


def test_information_uncertainty_returns_explicit_tail_mass_to_baseline() -> None:
    certain = conditional_tail_width(
        DispersionSignals(low_event_risk=0.8, dominance_risk=0.7)
    )
    uncertain = conditional_tail_width(
        DispersionSignals(
            low_event_risk=0.8,
            dominance_risk=0.7,
            information_uncertainty=0.5,
        )
    )

    assert uncertain.low_event_weight == pytest.approx(0.5 * certain.low_event_weight)
    assert uncertain.dominant_tail_weight == pytest.approx(
        0.5 * certain.dominant_tail_weight
    )
    assert uncertain.home_width > certain.home_width
    assert uncertain.away_width > certain.away_width


def test_complete_information_uncertainty_fails_closed_to_baseline_mass() -> None:
    decision = conditional_tail_width(
        DispersionSignals(
            regime_break=1.0,
            low_event_risk=1.0,
            dominance_risk=1.0,
            information_uncertainty=1.0,
        )
    )

    assert decision.low_event_weight == 0.0
    assert decision.dominant_tail_weight == 0.0
    assert decision.home_width > 1.0
    assert decision.away_width > 1.0


def test_tail_allocation_decreases_monotonically_with_uncertainty() -> None:
    allocations = []
    for uncertainty in (0.0, 0.25, 0.5, 0.75, 1.0):
        decision = conditional_tail_width(
            DispersionSignals(
                regime_break=0.6,
                low_event_risk=0.7,
                dominance_risk=0.8,
                information_uncertainty=uncertainty,
                directional_evidence_overlap=0.4,
            )
        )
        allocations.append(decision.low_event_weight + decision.dominant_tail_weight)

    assert allocations == sorted(allocations, reverse=True)
    assert allocations[-1] == 0.0


def test_uncertainty_does_not_change_relative_supported_tail_shares() -> None:
    certain = conditional_tail_width(
        DispersionSignals(
            regime_break=0.5,
            low_event_risk=0.7,
            dominance_risk=0.8,
            information_uncertainty=0.0,
        )
    )
    uncertain = conditional_tail_width(
        DispersionSignals(
            regime_break=0.5,
            low_event_risk=0.7,
            dominance_risk=0.8,
            information_uncertainty=0.6,
        )
    )

    certain_share = certain.low_event_weight / (
        certain.low_event_weight + certain.dominant_tail_weight
    )
    uncertain_share = uncertain.low_event_weight / (
        uncertain.low_event_weight + uncertain.dominant_tail_weight
    )

    assert uncertain_share == pytest.approx(certain_share)

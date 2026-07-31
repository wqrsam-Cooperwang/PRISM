"""Sensitivity invariants for V2.2.1 research-only dispersion controls."""

from __future__ import annotations

import pytest

from src.candidate_v2_2_1.dispersion import DispersionSignals, conditional_tail_width


def test_regime_break_monotonically_widens_home_distribution() -> None:
    low = conditional_tail_width(DispersionSignals(regime_break=0.25))
    high = conditional_tail_width(DispersionSignals(regime_break=0.75))

    assert high.home_width > low.home_width
    assert high.dominant_tail_weight > low.dominant_tail_weight


def test_low_event_risk_monotonically_increases_low_event_mass() -> None:
    low = conditional_tail_width(DispersionSignals(low_event_risk=0.25))
    high = conditional_tail_width(DispersionSignals(low_event_risk=0.75))

    assert high.low_event_weight > low.low_event_weight
    assert high.home_width < low.home_width


def test_information_uncertainty_widens_both_distributions_without_scenario_mass() -> None:
    baseline = conditional_tail_width(DispersionSignals())
    uncertain = conditional_tail_width(DispersionSignals(information_uncertainty=0.8))

    assert uncertain.home_width > baseline.home_width
    assert uncertain.away_width > baseline.away_width
    assert uncertain.low_event_weight == 0.0
    assert uncertain.dominant_tail_weight == 0.0


def test_uncertainty_monotonically_releases_governed_scenario_mass() -> None:
    uncertainty_levels = (0.0, 0.25, 0.5, 0.75, 1.0)
    low_event_decisions = [
        conditional_tail_width(
            DispersionSignals(low_event_risk=0.7, information_uncertainty=uncertainty)
        )
        for uncertainty in uncertainty_levels
    ]
    dominant_decisions = [
        conditional_tail_width(
            DispersionSignals(
                regime_break=0.6,
                dominance_risk=0.8,
                information_uncertainty=uncertainty,
            )
        )
        for uncertainty in uncertainty_levels
    ]

    assert all(
        later.low_event_weight < earlier.low_event_weight
        for earlier, later in zip(low_event_decisions, low_event_decisions[1:])
    )
    assert all(
        later.dominant_tail_weight < earlier.dominant_tail_weight
        for earlier, later in zip(dominant_decisions, dominant_decisions[1:])
    )
    assert low_event_decisions[-1].low_event_weight == 0.0
    assert dominant_decisions[-1].dominant_tail_weight == 0.0
    assert low_event_decisions[-1].home_width > low_event_decisions[0].home_width
    assert low_event_decisions[-1].away_width > low_event_decisions[0].away_width
    assert dominant_decisions[-1].home_width > dominant_decisions[0].home_width
    assert dominant_decisions[-1].away_width > dominant_decisions[0].away_width


def test_uncertainty_gate_preserves_relative_tail_allocation_before_fail_closed() -> None:
    baseline = conditional_tail_width(
        DispersionSignals(regime_break=0.7, low_event_risk=0.8, dominance_risk=0.9)
    )
    uncertain = conditional_tail_width(
        DispersionSignals(
            regime_break=0.7,
            low_event_risk=0.8,
            dominance_risk=0.9,
            information_uncertainty=0.6,
        )
    )

    baseline_total = baseline.low_event_weight + baseline.dominant_tail_weight
    uncertain_total = uncertain.low_event_weight + uncertain.dominant_tail_weight

    assert uncertain_total < baseline_total
    assert uncertain.low_event_weight / uncertain_total == pytest.approx(
        baseline.low_event_weight / baseline_total
    )
    assert uncertain.dominant_tail_weight / uncertain_total == pytest.approx(
        baseline.dominant_tail_weight / baseline_total
    )


def test_dominance_signal_is_asymmetric_by_design() -> None:
    baseline = conditional_tail_width(DispersionSignals())
    dominant = conditional_tail_width(DispersionSignals(dominance_risk=1.0))

    assert dominant.home_width > baseline.home_width
    assert dominant.away_width < baseline.away_width
    assert dominant.dominant_tail_weight > 0.0


def test_conflicting_low_event_and_directional_signals_preserve_baseline_mass() -> None:
    low_event_only = conditional_tail_width(DispersionSignals(low_event_risk=1.0))
    dominant_only = conditional_tail_width(
        DispersionSignals(regime_break=1.0, dominance_risk=1.0)
    )
    conflicted = conditional_tail_width(
        DispersionSignals(regime_break=1.0, low_event_risk=1.0, dominance_risk=1.0)
    )

    independent_requested_tail = (
        low_event_only.low_event_weight + dominant_only.dominant_tail_weight
    )
    conflicted_requested_tail = (
        conflicted.low_event_weight + conflicted.dominant_tail_weight
    )

    assert conflicted_requested_tail < independent_requested_tail
    assert conflicted_requested_tail <= 0.70


def test_conflict_damping_reduces_directional_overconfidence() -> None:
    directional = conditional_tail_width(
        DispersionSignals(regime_break=1.0, dominance_risk=1.0)
    )
    conflicted = conditional_tail_width(
        DispersionSignals(regime_break=1.0, low_event_risk=1.0, dominance_risk=1.0)
    )

    assert conflicted.home_width < directional.home_width
    assert conflicted.away_width > directional.away_width
    assert conflicted.dominant_tail_weight < directional.dominant_tail_weight


def test_share_aware_conflict_preserves_strong_low_event_signal() -> None:
    low_event_only = conditional_tail_width(DispersionSignals(low_event_risk=1.0))
    mostly_low_event = conditional_tail_width(
        DispersionSignals(regime_break=0.2, low_event_risk=1.0, dominance_risk=0.2)
    )

    assert mostly_low_event.low_event_weight > mostly_low_event.dominant_tail_weight
    assert mostly_low_event.low_event_weight > 0.95 * low_event_only.low_event_weight


def test_share_aware_conflict_preserves_strong_dominant_tail_signal() -> None:
    dominant_only = conditional_tail_width(
        DispersionSignals(regime_break=1.0, dominance_risk=1.0)
    )
    mostly_dominant = conditional_tail_width(
        DispersionSignals(regime_break=1.0, low_event_risk=0.2, dominance_risk=1.0)
    )

    assert mostly_dominant.dominant_tail_weight > mostly_dominant.low_event_weight
    assert mostly_dominant.dominant_tail_weight > 0.95 * dominant_only.dominant_tail_weight

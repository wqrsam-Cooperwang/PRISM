"""Sensitivity invariants for V2.2.1 research-only dispersion controls."""

from __future__ import annotations

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


def test_information_uncertainty_widens_both_distributions_without_dominant_tail() -> None:
    baseline = conditional_tail_width(DispersionSignals())
    uncertain = conditional_tail_width(DispersionSignals(information_uncertainty=0.8))

    assert uncertain.home_width > baseline.home_width
    assert uncertain.away_width > baseline.away_width
    assert uncertain.dominant_tail_weight == 0.0


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

"""Research-only tests for V2.2.1 conditional tail-width controls."""

from __future__ import annotations

import pytest

from src.candidate_v2_2_1.dispersion import DispersionSignals, conditional_tail_width


def test_neutral_signals_preserve_unit_width_without_tail_weight() -> None:
    decision = conditional_tail_width(DispersionSignals())

    assert decision.home_width == 1.0
    assert decision.away_width == 1.0
    assert decision.low_event_weight == 0.0
    assert decision.dominant_tail_weight == 0.0


def test_regime_and_dominance_widen_home_tail_without_mutating_away_equally() -> None:
    decision = conditional_tail_width(DispersionSignals(regime_break=1.0, dominance_risk=1.0))

    assert decision.home_width == pytest.approx(1.8)
    assert decision.away_width == pytest.approx(0.95)
    assert decision.dominant_tail_weight == pytest.approx(0.6)
    assert decision.low_event_weight == 0.0


def test_low_event_risk_adds_explicit_mass_and_narrows_both_widths() -> None:
    decision = conditional_tail_width(DispersionSignals(low_event_risk=1.0))

    assert decision.home_width == pytest.approx(0.85)
    assert decision.away_width == pytest.approx(0.9)
    assert decision.low_event_weight == pytest.approx(0.4)
    assert decision.dominant_tail_weight == 0.0


def test_information_uncertainty_widens_both_sides_without_scenario_mass() -> None:
    decision = conditional_tail_width(DispersionSignals(information_uncertainty=1.0))

    assert decision.home_width == pytest.approx(1.3)
    assert decision.away_width == pytest.approx(1.3)
    assert decision.low_event_weight == 0.0
    assert decision.dominant_tail_weight == 0.0


@pytest.mark.parametrize(
    "signals",
    (
        DispersionSignals(low_event_risk=0.05),
        DispersionSignals(low_event_risk=0.15),
        DispersionSignals(regime_break=0.15),
        DispersionSignals(dominance_risk=0.15),
    ),
)
def test_subthreshold_scenario_evidence_cannot_allocate_tail_mass(
    signals: DispersionSignals,
) -> None:
    decision = conditional_tail_width(signals)

    assert decision.low_event_weight == 0.0
    assert decision.dominant_tail_weight == 0.0


def test_subthreshold_evidence_can_adjust_width_without_creating_scenario_mass() -> None:
    decision = conditional_tail_width(
        DispersionSignals(low_event_risk=0.15, information_uncertainty=0.4)
    )

    assert decision.home_width != 1.0
    assert decision.away_width > 1.0
    assert decision.low_event_weight == 0.0
    assert decision.dominant_tail_weight == 0.0


def test_directional_evidence_quadratically_releases_away_low_event_narrowing() -> None:
    weak_directional = conditional_tail_width(
        DispersionSignals(low_event_risk=0.8, dominance_risk=0.2)
    )
    strong_directional = conditional_tail_width(
        DispersionSignals(low_event_risk=0.8, dominance_risk=0.8)
    )

    assert weak_directional.away_width < 1.0
    assert strong_directional.away_width >= 1.0


def test_conflicting_scenarios_redistribute_disagreement_into_symmetric_width() -> None:
    decision = conditional_tail_width(
        DispersionSignals(low_event_risk=1.0, regime_break=1.0, dominance_risk=1.0)
    )

    assert decision.home_width == pytest.approx(1.5525)
    assert decision.away_width == pytest.approx(1.0975)
    assert decision.low_event_weight + decision.dominant_tail_weight == pytest.approx(0.7)


def test_conflict_uncertainty_prevents_spurious_away_tail_narrowing() -> None:
    conflicting = conditional_tail_width(
        DispersionSignals(low_event_risk=0.8, dominance_risk=0.8)
    )
    directional_only = conditional_tail_width(DispersionSignals(dominance_risk=0.8))

    assert directional_only.away_width < 1.0
    assert conflicting.away_width >= 1.0
    assert conflicting.home_width < directional_only.home_width


@pytest.mark.parametrize(
    "signals",
    (
        DispersionSignals(regime_break=-0.01),
        DispersionSignals(low_event_risk=1.01),
        DispersionSignals(dominance_risk=float("nan")),
        DispersionSignals(information_uncertainty=float("inf")),
    ),
)
def test_invalid_signals_fail_closed(signals: DispersionSignals) -> None:
    with pytest.raises(
        ValueError,
        match=r"dispersion signals must be finite values in \[0, 1\]",
    ):
        conditional_tail_width(signals)

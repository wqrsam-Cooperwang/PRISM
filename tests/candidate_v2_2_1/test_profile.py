"""Tests for governed V2.2.1 candidate dispersion profiles."""

import pytest

from src.candidate_v2_2_1.dispersion import DispersionSignals
from src.candidate_v2_2_1.profile import (
    CANDIDATE_PROFILE_VERSION,
    build_candidate_dispersion_profile,
)


def test_neutral_profile_preserves_baseline_only_mixture() -> None:
    profile = build_candidate_dispersion_profile(DispersionSignals())

    assert profile.version == CANDIDATE_PROFILE_VERSION
    assert profile.decision.home_width == 1.0
    assert profile.decision.away_width == 1.0
    assert profile.mixture.baseline_weight == 1.0
    assert profile.mixture.low_event_weight == 0.0
    assert profile.mixture.dominant_tail_weight == 0.0


def test_low_event_profile_shifts_mass_without_mutating_width_contract() -> None:
    profile = build_candidate_dispersion_profile(DispersionSignals(low_event_risk=1.0))

    assert profile.decision.home_width == pytest.approx(0.85)
    assert profile.decision.away_width == pytest.approx(1.0)
    assert profile.mixture.low_event_weight == pytest.approx(0.4)
    assert profile.mixture.dominant_tail_weight == 0.0
    assert profile.mixture.baseline_weight == pytest.approx(0.6)


def test_dominant_profile_preserves_normalized_candidate_mixture() -> None:
    profile = build_candidate_dispersion_profile(
        DispersionSignals(regime_break=1.0, dominance_risk=1.0)
    )

    assert profile.decision.home_width == pytest.approx(1.8)
    assert profile.decision.away_width == pytest.approx(0.95)
    total = (
        profile.mixture.baseline_weight
        + profile.mixture.low_event_weight
        + profile.mixture.dominant_tail_weight
    )
    assert total == pytest.approx(1.0)
    assert profile.mixture.dominant_tail_weight == pytest.approx(0.6)
    assert profile.mixture.baseline_weight == pytest.approx(0.4)


def test_invalid_signals_fail_closed_at_profile_boundary() -> None:
    with pytest.raises(
        ValueError,
        match=r"dispersion signals must be finite values in \[0, 1\]",
    ):
        build_candidate_dispersion_profile(DispersionSignals(information_uncertainty=float("nan")))

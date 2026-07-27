"""Research-only tests for V2.2.1 bounded scenario mixtures."""

from __future__ import annotations

import math

import pytest

from src.candidate_v2_2_1.dispersion import DispersionDecision
from src.candidate_v2_2_1.scenario_mix import (
    MAX_TOTAL_SCENARIO_WEIGHT,
    build_scenario_mixture,
)


def test_zero_tail_weights_preserve_full_baseline_mass() -> None:
    mixture = build_scenario_mixture(
        DispersionDecision(
            home_width=1.0,
            away_width=1.0,
            low_event_weight=0.0,
            dominant_tail_weight=0.0,
        )
    )

    assert mixture.baseline_weight == 1.0
    assert mixture.low_event_weight == 0.0
    assert mixture.dominant_tail_weight == 0.0


def test_valid_tail_weights_are_preserved_below_cap() -> None:
    mixture = build_scenario_mixture(
        DispersionDecision(
            home_width=1.2,
            away_width=0.95,
            low_event_weight=0.2,
            dominant_tail_weight=0.3,
        )
    )

    assert mixture.baseline_weight == pytest.approx(0.5)
    assert mixture.low_event_weight == pytest.approx(0.2)
    assert mixture.dominant_tail_weight == pytest.approx(0.3)


def test_tail_weights_scale_proportionally_when_cap_is_exceeded() -> None:
    mixture = build_scenario_mixture(
        DispersionDecision(
            home_width=1.8,
            away_width=0.95,
            low_event_weight=0.6,
            dominant_tail_weight=0.6,
        )
    )

    assert mixture.low_event_weight == pytest.approx(0.35)
    assert mixture.dominant_tail_weight == pytest.approx(0.35)
    assert mixture.baseline_weight == pytest.approx(1.0 - MAX_TOTAL_SCENARIO_WEIGHT)
    assert (
        mixture.baseline_weight + mixture.low_event_weight + mixture.dominant_tail_weight
    ) == pytest.approx(1.0)


@pytest.mark.parametrize(
    "decision, message",
    (
        (
            DispersionDecision(
                home_width=math.nan,
                away_width=1.0,
                low_event_weight=0.0,
                dominant_tail_weight=0.0,
            ),
            "dispersion decision values must be finite",
        ),
        (
            DispersionDecision(
                home_width=0.0,
                away_width=1.0,
                low_event_weight=0.0,
                dominant_tail_weight=0.0,
            ),
            "dispersion widths must be positive",
        ),
        (
            DispersionDecision(
                home_width=1.0,
                away_width=1.0,
                low_event_weight=-0.01,
                dominant_tail_weight=0.0,
            ),
            "low_event_weight must be in [0, 1]",
        ),
        (
            DispersionDecision(
                home_width=1.0,
                away_width=1.0,
                low_event_weight=0.0,
                dominant_tail_weight=1.01,
            ),
            "dominant_tail_weight must be in [0, 1]",
        ),
    ),
)
def test_invalid_mixture_inputs_fail_closed(
    decision: DispersionDecision,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message.replace("[", r"\[").replace("]", r"\]")):
        build_scenario_mixture(decision)

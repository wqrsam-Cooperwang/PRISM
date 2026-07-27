import pytest

from src.consensus import DirectionCalibrationOutput
from src.scoreline import (
    ScorelineRegime,
    ScorelineRegimeClassifier,
    scenario_weights_for_regime,
)


def _direction(home: float, draw: float, away: float) -> DirectionCalibrationOutput:
    return DirectionCalibrationOutput(
        home_probability=home,
        draw_probability=draw,
        away_probability=away,
        reliability=0.8,
        raw_leading_probability=max(home, draw, away),
        calibrated_leading_probability=max(home, draw, away),
    )


@pytest.mark.parametrize(
    ("direction", "home_xg", "away_xg", "expected"),
    (
        (_direction(0.36, 0.32, 0.32), 1.10, 1.05, ScorelineRegime.BALANCED_LOW),
        (_direction(0.36, 0.32, 0.32), 1.55, 1.45, ScorelineRegime.BALANCED_OPEN),
        (_direction(0.52, 0.28, 0.20), 1.55, 0.75, ScorelineRegime.HOME_CONTROL),
        (_direction(0.20, 0.28, 0.52), 0.75, 1.55, ScorelineRegime.AWAY_CONTROL),
        (_direction(0.52, 0.24, 0.24), 1.85, 1.10, ScorelineRegime.HOME_OPEN),
        (_direction(0.24, 0.24, 0.52), 1.10, 1.85, ScorelineRegime.AWAY_OPEN),
    ),
)
def test_regime_classifier_covers_registered_shapes(
    direction: DirectionCalibrationOutput,
    home_xg: float,
    away_xg: float,
    expected: ScorelineRegime,
) -> None:
    result = ScorelineRegimeClassifier().run(direction, home_xg, away_xg)

    assert result.regime is expected
    assert result.total_xg == pytest.approx(home_xg + away_xg)
    assert result.xg_gap == pytest.approx(home_xg - away_xg)


def test_regime_classifier_rejects_negative_xg() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        ScorelineRegimeClassifier().run(_direction(0.5, 0.3, 0.2), -0.1, 1.0)


def test_regime_scenario_weights_are_normalized_and_shape_specific() -> None:
    for regime in ScorelineRegime:
        weights = scenario_weights_for_regime(regime)
        assert sum(weight for _, weight in weights) == pytest.approx(1.0)

    balanced_open = dict(scenario_weights_for_regime(ScorelineRegime.BALANCED_OPEN))
    home_control = dict(scenario_weights_for_regime(ScorelineRegime.HOME_CONTROL))
    away_control = dict(scenario_weights_for_regime(ScorelineRegime.AWAY_CONTROL))

    assert balanced_open["early_open"] > home_control["early_open"]
    assert home_control["home_scores_first"] > home_control["away_scores_first"]
    assert away_control["away_scores_first"] > away_control["home_scores_first"]

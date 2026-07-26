import pytest

from src.domain.models import ModelOutput
from src.regression import (
    ScorelineRegressionCase,
    compare_scoreline_case,
    summarize_scoreline_regression,
)


def _model(model_id: str, home_xg: float, away_xg: float) -> ModelOutput:
    return ModelOutput(
        model_id=model_id,
        model_version="1.0.0",
        home_probability=0.55,
        draw_probability=0.25,
        away_probability=0.20,
        expected_home_goals=home_xg,
        expected_away_goals=away_xg,
    )


def test_regression_case_validates_inputs() -> None:
    with pytest.raises(ValueError, match="case_id"):
        ScorelineRegressionCase(" ", (_model("xg", 1.0, 1.0),), 1, 1)
    with pytest.raises(ValueError, match="at least one model"):
        ScorelineRegressionCase("case", (), 1, 1)
    with pytest.raises(ValueError, match="non-negative integers"):
        ScorelineRegressionCase("case", (_model("xg", 1.0, 1.0),), -1, 1)


def test_v21_diversity_can_break_legacy_shared_story_pair() -> None:
    case = ScorelineRegressionCase(
        case_id="shared-story",
        models=(_model("xg", 1.7, 0.5),),
        actual_home_goals=1,
        actual_away_goals=1,
    )

    comparison = compare_scoreline_case(case)

    assert comparison.v1.shared_story_pair is True
    assert comparison.v21.shared_story_pair is False
    assert comparison.v21.minimum_manhattan_distance <= comparison.v1.minimum_manhattan_distance


def test_regression_summary_counts_hits_distance_and_story_pairs() -> None:
    first = compare_scoreline_case(ScorelineRegressionCase("first", (_model("a", 1.7, 0.5),), 1, 1))
    second = compare_scoreline_case(
        ScorelineRegressionCase("second", (_model("b", 1.2, 1.0),), 1, 1)
    )

    summary = summarize_scoreline_regression((first, second))

    assert summary.case_count == 2
    assert summary.v1_shared_story_pairs >= summary.v21_shared_story_pairs
    assert summary.v1_mean_minimum_distance >= 0.0
    assert summary.v21_mean_minimum_distance >= 0.0
    assert (
        summary.v21_distance_improved_cases
        + summary.v21_distance_worsened_cases
        + summary.distance_tied_cases
        == 2
    )


def test_regression_summary_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="at least one"):
        summarize_scoreline_regression(())


def test_regression_requires_xg_for_both_engines() -> None:
    model = ModelOutput("plain", "1.0.0", 0.5, 0.3, 0.2)
    case = ScorelineRegressionCase("missing-xg", (model,), 1, 0)

    with pytest.raises(ValueError, match="expected-goal"):
        compare_scoreline_case(case)

import pytest

from src.domain.models import ModelOutput
from src.regression import ScorelineRegressionCase, run_batch_scoreline_regression


def _model(model_id: str, home_xg: float, away_xg: float) -> ModelOutput:
    return ModelOutput(
        model_id=model_id,
        model_version="1.0.0",
        home_probability=0.50,
        draw_probability=0.30,
        away_probability=0.20,
        expected_home_goals=home_xg,
        expected_away_goals=away_xg,
    )


def test_batch_regression_returns_stable_summary_and_json_shape() -> None:
    cases = (
        ScorelineRegressionCase("case-a", (_model("a", 1.7, 0.5),), 1, 1),
        ScorelineRegressionCase("case-b", (_model("b", 1.2, 1.0),), 1, 0),
    )

    result = run_batch_scoreline_regression(cases)
    payload = result.to_dict()

    assert result.summary.case_count == 2
    assert tuple(item.case_id for item in result.comparisons) == ("case-a", "case-b")
    assert payload["summary"]["case_count"] == 2
    assert payload["comparisons"][0]["case_id"] == "case-a"
    assert len(payload["comparisons"][0]["v1"]["recommendations"]) == 2
    assert len(payload["comparisons"][0]["v21"]["recommendations"]) == 2


def test_batch_regression_rejects_empty_cases() -> None:
    with pytest.raises(ValueError, match="at least one"):
        run_batch_scoreline_regression(())

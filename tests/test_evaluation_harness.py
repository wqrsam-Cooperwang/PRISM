from datetime import datetime, timezone
from math import log

import pytest

from src.domain.models import ModelOutput
from src.evaluation import EvaluationCase, RealMatchEvaluationHarness
from src.runtime import MatchRequest


def complete_evidence() -> dict[str, float]:
    return {
        "lineup": 1.0,
        "injuries": 1.0,
        "odds": 1.0,
        "weather": 1.0,
        "tactical_data": 1.0,
        "historical_data": 1.0,
        "market_data": 1.0,
        "motivation": 1.0,
    }


def request() -> MatchRequest:
    return MatchRequest(
        match_id="eval-match-1",
        competition="Evaluation League",
        kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        home_team_id="home",
        home_team_name="Home FC",
        away_team_id="away",
        away_team_name="Away FC",
        model_outputs=(
            ModelOutput("poisson", "1.0.0", 0.60, 0.22, 0.18, 1.7, 0.8),
            ModelOutput("elo", "1.0.0", 0.58, 0.23, 0.19, 1.5, 0.8),
        ),
        lineups={"confirmed": True},
        injuries={"home": [], "away": []},
        market={"home_odds": 2.20, "draw_odds": 4.50, "away_odds": 7.00},
        weather={"condition": "clear"},
        schedule={"home_rest_days": 6, "away_rest_days": 6},
        tactical={"home_shape": "4-3-3", "away_shape": "4-2-3-1"},
    )


def case(case_id: str, home_goals: int, away_goals: int) -> EvaluationCase:
    return EvaluationCase(
        case_id=case_id,
        request=request(),
        completeness=complete_evidence(),
        prism_version="3.2.0-alpha1",
        actual_home_goals=home_goals,
        actual_away_goals=away_goals,
        session_id=f"session-{case_id}",
        created_at=datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc),
        git_commit="eval123",
    )


def test_evaluate_scores_production_prediction_against_actual_result() -> None:
    result = RealMatchEvaluationHarness().evaluate(case("home-win", 1, 0))

    assert result.actual_outcome == "home"
    assert result.home_probability == pytest.approx(0.59)
    assert result.draw_probability == pytest.approx(0.225)
    assert result.away_probability == pytest.approx(0.185)
    assert result.leading_outcome == "home"
    assert result.leading_probability == pytest.approx(0.59)
    assert result.brier_score == pytest.approx((0.59 - 1.0) ** 2 + 0.225**2 + 0.185**2)
    assert result.log_loss == pytest.approx(-log(0.59))
    assert result.top1_correct is True
    assert result.scoreline_top3_hit is True
    assert result.decision_action == "candidate"
    assert result.selected_market == "home"
    assert result.candidate_correct is True
    assert result.report.provenance.session_id == "session-home-win"


def test_evaluate_records_wrong_top1_and_candidate_without_changing_prediction() -> None:
    result = RealMatchEvaluationHarness().evaluate(case("away-win", 0, 1))

    assert result.actual_outcome == "away"
    assert result.leading_outcome == "home"
    assert result.top1_correct is False
    assert result.candidate_correct is False
    assert result.home_probability == pytest.approx(0.59)
    assert result.away_probability == pytest.approx(0.185)


def test_evaluate_many_aggregates_only_eligible_scoreline_and_candidate_cases() -> None:
    harness = RealMatchEvaluationHarness()
    summary = harness.evaluate_many((case("first", 1, 0), case("second", 0, 1)))

    assert summary.case_count == 2
    assert tuple(result.case_id for result in summary.results) == ("first", "second")
    assert summary.top1_accuracy == pytest.approx(0.5)
    assert summary.scoreline_available_count == 2
    assert summary.scoreline_top3_hit_rate == pytest.approx(0.5)
    assert summary.candidate_count == 2
    assert summary.candidate_accuracy == pytest.approx(0.5)
    assert summary.mean_brier_score == pytest.approx(
        sum(result.brier_score for result in summary.results) / 2
    )
    assert summary.mean_log_loss == pytest.approx(
        sum(result.log_loss for result in summary.results) / 2
    )


def test_evaluate_many_rejects_empty_batches() -> None:
    with pytest.raises(ValueError, match="at least one case"):
        RealMatchEvaluationHarness().evaluate_many(())


def test_evaluation_case_rejects_invalid_observed_goals() -> None:
    with pytest.raises(ValueError, match="actual_home_goals"):
        EvaluationCase(
            case_id="invalid",
            request=request(),
            completeness=complete_evidence(),
            prism_version="3.2.0-alpha1",
            actual_home_goals=-1,
            actual_away_goals=0,
        )

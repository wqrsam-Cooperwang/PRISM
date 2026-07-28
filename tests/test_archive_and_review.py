from pathlib import Path

from src.prism_enterprise.archive import MatchResult, PredictionRecord, PredictionRepository
from src.prism_enterprise.review import build_review


def sample_prediction() -> PredictionRecord:
    return PredictionRecord(
        prediction_id="pred-001",
        match_id="match-001",
        competition="Test League",
        kickoff_utc="2026-07-28T19:00:00+00:00",
        prediction_time_utc="2026-07-27T19:00:00+00:00",
        home_team="Home FC",
        away_team="Away FC",
        model_version="PRISM-Exact-Score-V3.1",
        lambda_home=1.4,
        lambda_away=1.1,
        outcome_home=0.42,
        outcome_draw=0.30,
        outcome_away=0.28,
        confidence=0.72,
        primary_score_home=1,
        primary_score_away=1,
        alternate_scores=((2, 1),),
        rationale={"summary": "balanced match"},
    )


def test_archive_round_trip(tmp_path: Path) -> None:
    repository = PredictionRepository(tmp_path / "prism.db")
    repository.initialize()
    prediction = sample_prediction()

    repository.save_prediction(
        prediction,
        {
            "PERF-001": {
                "value": 1.4,
                "confidence": 0.9,
                "source": "test",
                "observed_at_utc": prediction.prediction_time_utc,
            }
        },
    )
    repository.save_result(
        MatchResult(
            match_id="match-001",
            home_goals=2,
            away_goals=1,
            home_xg=1.8,
            away_xg=0.9,
            result_source="test",
            observed_at_utc="2026-07-28T21:00:00+00:00",
        )
    )

    stored_prediction = repository.get_prediction("pred-001")
    stored_result = repository.get_result("match-001")

    assert stored_prediction is not None
    assert stored_prediction["model_version"] == "PRISM-Exact-Score-V3.1"
    assert stored_result is not None
    assert stored_result["home_goals"] == 2


def test_review_metrics() -> None:
    prediction = sample_prediction()
    result = MatchResult(
        match_id="match-001",
        home_goals=2,
        away_goals=1,
        home_xg=1.8,
        away_xg=0.9,
        result_source="test",
        observed_at_utc="2026-07-28T21:00:00+00:00",
    )

    review = build_review(prediction, result)

    assert review.outcome_correct is False
    assert review.exact_score_correct is False
    assert review.btts_correct is True
    assert review.total_goals_error == 0.5
    assert 0 <= review.brier_score <= 1
    assert review.attribution == ("normal_scoreline_variance",)


def test_red_card_is_flagged() -> None:
    prediction = sample_prediction()
    result = MatchResult(
        match_id="match-001",
        home_goals=0,
        away_goals=3,
        home_red_cards=1,
        result_source="test",
        observed_at_utc="2026-07-28T21:00:00+00:00",
    )

    review = build_review(prediction, result)

    assert "red_card" in review.anomaly_flags
    assert "red_card" in review.attribution

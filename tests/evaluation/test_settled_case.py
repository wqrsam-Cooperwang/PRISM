"""Tests for settled V2.1 versus V2.2 forward-test comparisons."""

from datetime import datetime, timedelta, timezone

import pytest

from src.evaluation.settled_case import evaluate_settled_case
from src.ledger.models import PredictionLedgerSnapshot
from src.ledger.outcomes import MatchOutcome


def _snapshot(
    *,
    match_id: str = "match-a",
    production: tuple[str, str] = ("1-0", "1-1"),
    shadow: tuple[str, str] = ("2-0", "2-1"),
) -> PredictionLedgerSnapshot:
    kickoff = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
    return PredictionLedgerSnapshot(
        prediction_id=f"prediction-{match_id}",
        match_id=match_id,
        frozen_at=kickoff - timedelta(hours=1),
        payload={
            "report": {
                "match": {"kickoff": kickoff.isoformat()},
                "provenance": {
                    "prism_version": "V2.1",
                    "schema_version": "1",
                    "runtime_version": "1",
                    "session_id": "session-evaluation",
                },
                "scoreline": {
                    "available": True,
                    "recommended_scorelines": list(production),
                },
            },
            "model_outputs": [{"model_id": "prism", "model_version": "V2.1"}],
            "shadow_predictions": {
                "v2_2": {
                    "schema_version": "1",
                    "candidate_version": "V2.2-shadow",
                    "status": "available",
                    "direction_calibration": {"status": "available"},
                    "scoreline": {
                        "available": True,
                        "recommended_scorelines": list(shadow),
                    },
                }
            },
        },
    )


def _outcome(match_id: str, home: int, away: int) -> MatchOutcome:
    return MatchOutcome(
        match_id=match_id,
        home_goals=home,
        away_goals=away,
        settled_at=datetime(2026, 7, 28, 14, 0, tzinfo=timezone.utc),
        source="user_verified_final_score",
    )


def test_shadow_delta_is_negative_when_v22_is_closer() -> None:
    evaluation = evaluate_settled_case(
        _snapshot(production=("1-0", "1-1"), shadow=("3-0", "2-0")),
        _outcome("match-a", 4, 0),
    )

    assert evaluation.production.goal_distance == 3
    assert evaluation.shadow.goal_distance == 1
    assert evaluation.shadow_distance_delta == -2


def test_shadow_delta_is_zero_when_models_are_equally_wrong() -> None:
    evaluation = evaluate_settled_case(
        _snapshot(production=("1-0", "1-1"), shadow=("0-1", "1-1")),
        _outcome("match-a", 0, 0),
    )

    assert evaluation.production.goal_distance == 1
    assert evaluation.shadow.goal_distance == 1
    assert evaluation.shadow_distance_delta == 0


def test_settled_case_rejects_mismatched_match_identity() -> None:
    with pytest.raises(ValueError, match="snapshot and outcome match_id must match"):
        evaluate_settled_case(_snapshot(match_id="match-a"), _outcome("match-b", 0, 0))

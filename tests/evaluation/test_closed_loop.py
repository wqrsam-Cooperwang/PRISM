"""Tests for the governed post-match settlement and evaluation loop."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.evaluation.closed_loop import process_verified_match_outcome
from src.ledger.accepted import persist_accepted_formal_prediction
from src.ledger.models import PredictionLedgerSnapshot
from src.ledger.outcomes import MatchOutcome
from src.ledger.store import FileSystemPredictionLedgerStore


def _snapshot() -> PredictionLedgerSnapshot:
    kickoff = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
    return PredictionLedgerSnapshot(
        prediction_id="prediction-match-a",
        match_id="match-a",
        frozen_at=kickoff - timedelta(hours=1),
        payload={
            "report": {
                "match": {"kickoff": kickoff.isoformat()},
                "provenance": {
                    "prism_version": "V2.1",
                    "schema_version": "1",
                    "runtime_version": "1",
                    "session_id": "session-closed-loop",
                },
                "scoreline": {
                    "available": True,
                    "recommended_scorelines": ["1-0", "1-1"],
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
                        "recommended_scorelines": ["0-0", "2-1"],
                    },
                }
            },
        },
    )


def test_verified_outcome_runs_full_governed_post_match_loop(tmp_path: Path) -> None:
    prediction_root = tmp_path / "predictions"
    outcome_root = tmp_path / "outcomes"
    persist_accepted_formal_prediction(
        _snapshot(),
        FileSystemPredictionLedgerStore(prediction_root),
    )
    outcome = MatchOutcome(
        match_id="match-a",
        home_goals=0,
        away_goals=0,
        settled_at=datetime(2026, 7, 28, 15, 0, tzinfo=timezone.utc),
        source="user_verified_final_score",
    )

    result = process_verified_match_outcome(
        outcome,
        prediction_root=prediction_root,
        outcome_root=outcome_root,
        minimum_promotion_cases=20,
    )

    assert result.settlement.outcome == outcome
    assert result.evaluation.manifest.case_count == 1
    assert result.evaluation.summary.shadow_exact_hits == 1
    assert result.promotion_evidence.eligible is False
    assert result.promotion_evidence.reason == "insufficient governed cases: 1/20"

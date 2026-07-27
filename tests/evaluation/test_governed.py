"""Tests for the governed settled-cohort evaluation entry point."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.evaluation.governed import evaluate_governed_settled_cohort
from src.ledger.accepted import persist_accepted_formal_prediction
from src.ledger.models import PredictionLedgerSnapshot
from src.ledger.outcomes import FileSystemOutcomeLedgerStore, MatchOutcome
from src.ledger.settlement import settle_verified_outcome
from src.ledger.store import FileSystemPredictionLedgerStore


def _snapshot(match_id: str) -> PredictionLedgerSnapshot:
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
                    "session_id": "session-governed-evaluation",
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


def test_governed_entry_point_evaluates_exact_settled_cohort(tmp_path: Path) -> None:
    prediction_root = tmp_path / "predictions"
    outcome_root = tmp_path / "outcomes"
    prediction_store = FileSystemPredictionLedgerStore(prediction_root)
    outcome_store = FileSystemOutcomeLedgerStore(outcome_root)

    for match_id, score in (("rosenborg-fredrikstad", (4, 0)), ("haecken-aik", (0, 0))):
        snapshot = _snapshot(match_id)
        persist_accepted_formal_prediction(snapshot, prediction_store)
        settle_verified_outcome(
            MatchOutcome(
                match_id=match_id,
                home_goals=score[0],
                away_goals=score[1],
                settled_at=datetime(2026, 7, 28, 15, 0, tzinfo=timezone.utc),
                source="user_verified_final_score",
            ),
            outcome_store,
            prediction_root=prediction_root,
        )

    result = evaluate_governed_settled_cohort(prediction_root, outcome_root)

    assert result.manifest.case_count == 2
    assert result.summary.case_count == 2
    assert tuple(case.match_id for case in result.cases) == (
        "haecken-aik",
        "rosenborg-fredrikstad",
    )
    assert result.summary.production_mean_distance == 2.0
    assert result.summary.shadow_mean_distance == 1.5
    assert result.summary.production_exact_hits == 0
    assert result.summary.shadow_exact_hits == 1
    assert result.summary.shadow_better_cases == 1
    assert result.summary.tied_cases == 1
    assert result.summary.shadow_worse_cases == 0

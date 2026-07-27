"""Tests for governed settlement of verified match outcomes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.ledger.accepted import persist_accepted_formal_prediction
from src.ledger.models import PredictionLedgerSnapshot
from src.ledger.outcomes import FileSystemOutcomeLedgerStore, MatchOutcome
from src.ledger.settlement import settle_verified_outcome
from src.ledger.store import FileSystemPredictionLedgerStore


def _snapshot(match_id: str = "match-a") -> PredictionLedgerSnapshot:
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
                    "session_id": "session-settlement",
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
                        "recommended_scorelines": ["1-1", "2-1"],
                    },
                }
            },
        },
    )


def test_verified_outcome_settles_exact_formal_prediction(tmp_path: Path) -> None:
    prediction_root = tmp_path / "predictions"
    outcome_root = tmp_path / "outcomes"
    snapshot = _snapshot()
    persist_accepted_formal_prediction(
        snapshot,
        FileSystemPredictionLedgerStore(prediction_root),
    )
    outcome = MatchOutcome(
        match_id="match-a",
        home_goals=4,
        away_goals=0,
        settled_at=datetime(2026, 7, 28, 14, 0, tzinfo=timezone.utc),
        source="user_verified_final_score",
    )

    result = settle_verified_outcome(
        outcome,
        FileSystemOutcomeLedgerStore(outcome_root),
        prediction_root=prediction_root,
    )

    assert result.snapshot == snapshot
    assert result.outcome == outcome
    assert result.ledger_path == outcome_root / "match-a.json"
    assert result.ledger_path.is_file()


def test_outcome_without_formal_prediction_is_rejected(tmp_path: Path) -> None:
    outcome_root = tmp_path / "outcomes"
    outcome = MatchOutcome(
        match_id="missing-match",
        home_goals=0,
        away_goals=0,
        settled_at=datetime(2026, 7, 28, 14, 0, tzinfo=timezone.utc),
        source="user_verified_final_score",
    )

    with pytest.raises(ValueError, match="no formal prediction exists"):
        settle_verified_outcome(
            outcome,
            FileSystemOutcomeLedgerStore(outcome_root),
            prediction_root=tmp_path / "predictions",
        )

    assert not outcome_root.exists()

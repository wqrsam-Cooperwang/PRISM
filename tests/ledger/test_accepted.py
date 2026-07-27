"""Tests for fail-closed persistence of externally accepted predictions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.ledger.accepted import persist_accepted_formal_prediction
from src.ledger.models import PredictionLedgerSnapshot
from src.ledger.store import FileSystemPredictionLedgerStore


def _valid_snapshot(*, frozen_after_kickoff: bool = False) -> PredictionLedgerSnapshot:
    kickoff = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
    frozen_at = (
        kickoff + timedelta(minutes=1)
        if frozen_after_kickoff
        else kickoff - timedelta(hours=1)
    )
    return PredictionLedgerSnapshot(
        prediction_id="prediction-match-a",
        match_id="match-a",
        frozen_at=frozen_at,
        payload={
            "report": {
                "match": {"kickoff": kickoff.isoformat()},
                "provenance": {
                    "prism_version": "V2.1",
                    "schema_version": "1",
                    "runtime_version": "1",
                    "session_id": "session-accepted",
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


def test_accepted_prediction_is_formal_only_after_durable_round_trip(tmp_path: Path) -> None:
    store = FileSystemPredictionLedgerStore(tmp_path)
    snapshot = _valid_snapshot()

    result = persist_accepted_formal_prediction(snapshot, store)

    assert result.snapshot == snapshot
    assert result.ledger_path == tmp_path / "prediction-match-a.json"
    assert result.ledger_path.is_file()


def test_invalid_accepted_prediction_fails_before_any_ledger_write(tmp_path: Path) -> None:
    store = FileSystemPredictionLedgerStore(tmp_path)
    snapshot = _valid_snapshot(frozen_after_kickoff=True)

    with pytest.raises(ValueError, match="formal prediction must be frozen before kickoff"):
        persist_accepted_formal_prediction(snapshot, store)

    assert list(tmp_path.glob("*.json")) == []

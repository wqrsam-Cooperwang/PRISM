"""Governed regression dataset admission tests."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from src.regression.governed_dataset import load_governed_ledger_regression_dataset


def _prediction_record(match_id: str = "match-1") -> dict[str, object]:
    kickoff = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
    return {
        "schema_version": "1.0.0",
        "prediction_id": f"prediction-{match_id}",
        "match_id": match_id,
        "frozen_at": (kickoff - timedelta(hours=1)).isoformat(),
        "payload": {
            "report": {
                "match": {"kickoff": kickoff.isoformat()},
                "provenance": {
                    "prism_version": "V2.1",
                    "schema_version": "1",
                    "runtime_version": "1",
                    "session_id": "session-1",
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
    }


def _write(root, name: str, value: object) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(json.dumps(value), encoding="utf-8")


def _outcome(match_id: str = "match-1") -> dict[str, object]:
    return {
        "match_id": match_id,
        "home_goals": 1,
        "away_goals": 1,
        "settled_at": datetime(2026, 7, 28, 14, 0, tzinfo=timezone.utc).isoformat(),
        "source": "verified_result",
    }


def test_unsettled_formal_prediction_is_skipped(tmp_path):
    predictions = tmp_path / "predictions"
    _write(predictions, "prediction.json", _prediction_record())

    assert load_governed_ledger_regression_dataset(predictions, tmp_path / "outcomes") == ()


def test_settled_formal_prediction_enters_dataset(tmp_path):
    predictions = tmp_path / "predictions"
    outcomes = tmp_path / "outcomes"
    _write(predictions, "prediction.json", _prediction_record())
    _write(outcomes, "match-1.json", _outcome())

    cases = load_governed_ledger_regression_dataset(predictions, outcomes)

    assert len(cases) == 1
    assert cases[0].match_id == "match-1"
    assert cases[0].actual_scoreline == "1-1"


def test_invalid_formal_prediction_cannot_bypass_cohort_gate(tmp_path):
    predictions = tmp_path / "predictions"
    outcomes = tmp_path / "outcomes"
    prediction = _prediction_record()
    prediction["payload"]["report"]["scoreline"]["recommended_scorelines"] = ["1-0"]
    _write(predictions, "prediction.json", prediction)
    _write(outcomes, "match-1.json", _outcome())

    with pytest.raises(ValueError, match="exactly two production scorelines"):
        load_governed_ledger_regression_dataset(predictions, outcomes)


def test_existing_malformed_outcome_fails_closed(tmp_path):
    predictions = tmp_path / "predictions"
    outcomes = tmp_path / "outcomes"
    _write(predictions, "prediction.json", _prediction_record())
    bad_outcome = _outcome()
    bad_outcome["home_goals"] = True
    _write(outcomes, "match-1.json", bad_outcome)

    with pytest.raises(ValueError, match="home_goals must be a non-negative integer"):
        load_governed_ledger_regression_dataset(predictions, outcomes)


def test_outcome_identity_must_match_prediction(tmp_path):
    predictions = tmp_path / "predictions"
    outcomes = tmp_path / "outcomes"
    _write(predictions, "prediction.json", _prediction_record())
    _write(outcomes, "match-1.json", _outcome("different-match"))

    with pytest.raises(ValueError, match="match_id"):
        load_governed_ledger_regression_dataset(predictions, outcomes)

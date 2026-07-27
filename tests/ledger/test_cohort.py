"""Forward-testing cohort admission tests."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from src.ledger.cohort import load_formal_forward_testing_cohort


def _record() -> dict[str, object]:
    kickoff = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
    return {
        "schema_version": "1.0.0",
        "prediction_id": "prediction-1",
        "match_id": "match-1",
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
            "model_outputs": [
                {"model_id": "prism", "model_version": "V2.1"},
            ],
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
                },
            },
        },
    }


def _write(root, name: str, record: object) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(json.dumps(record), encoding="utf-8")


def test_empty_or_missing_ledger_returns_empty_cohort(tmp_path):
    assert load_formal_forward_testing_cohort(tmp_path / "missing") == ()


def test_valid_formal_records_load_deterministically(tmp_path):
    second = _record()
    second["prediction_id"] = "prediction-2"
    second["match_id"] = "match-2"
    _write(tmp_path, "b.json", second)
    _write(tmp_path, "a.json", _record())

    cohort = load_formal_forward_testing_cohort(tmp_path)

    assert [snapshot.prediction_id for snapshot in cohort] == [
        "prediction-1",
        "prediction-2",
    ]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda record: record.update({"frozen_at": "not-a-datetime"}),
        lambda record: record.update({"payload": []}),
        lambda record: record["payload"]["report"]["scoreline"].update(
            {"recommended_scorelines": ["1-0"]}
        ),
        lambda record: record["payload"]["shadow_predictions"]["v2_2"].update(
            {"status": "unavailable"}
        ),
    ],
)
def test_invalid_formal_record_fails_closed(tmp_path, mutate):
    record = _record()
    mutate(record)
    _write(tmp_path, "invalid.json", record)

    with pytest.raises(ValueError):
        load_formal_forward_testing_cohort(tmp_path)


def test_malformed_json_fails_closed(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid formal ledger record"):
        load_formal_forward_testing_cohort(tmp_path)

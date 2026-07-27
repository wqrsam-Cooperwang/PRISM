"""Contract tests for deterministic governed promotion cohort identity."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.regression.governed_manifest import build_governed_cohort_manifest


def _prediction_record(match_id: str, prediction_id: str | None = None) -> dict[str, object]:
    kickoff = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
    return {
        "schema_version": "1.0.0",
        "prediction_id": prediction_id or f"prediction-{match_id}",
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


def _outcome(match_id: str) -> dict[str, object]:
    return {
        "match_id": match_id,
        "home_goals": 1,
        "away_goals": 1,
        "settled_at": datetime(2026, 7, 28, 14, 0, tzinfo=timezone.utc).isoformat(),
        "source": "verified_result",
    }


def _write(root: Path, name: str, value: object) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(json.dumps(value), encoding="utf-8")


def _write_settled_case(
    predictions: Path,
    outcomes: Path,
    match_id: str,
    *,
    prediction_id: str | None = None,
    prediction_filename: str | None = None,
) -> None:
    _write(
        predictions,
        prediction_filename or f"{match_id}.json",
        _prediction_record(match_id, prediction_id),
    )
    _write(outcomes, f"{match_id}.json", _outcome(match_id))


def test_manifest_contract_has_canonical_membership_and_digest(tmp_path: Path) -> None:
    predictions = tmp_path / "predictions"
    outcomes = tmp_path / "outcomes"
    _write_settled_case(predictions, outcomes, "match-b")
    _write_settled_case(predictions, outcomes, "match-a")

    manifest = build_governed_cohort_manifest(predictions, outcomes)

    assert manifest.to_dict() == {
        "case_count": 2,
        "prediction_ids": ["prediction-match-a", "prediction-match-b"],
        "match_ids": ["match-a", "match-b"],
        "sha256": "f0f24400f83cc9cf3c8babaf5f81306a2eed9f7bfbfd91077936f60825a364bc",
    }


def test_manifest_identity_is_stable_across_file_creation_and_path_order(tmp_path: Path) -> None:
    first_predictions = tmp_path / "first-predictions"
    first_outcomes = tmp_path / "first-outcomes"
    second_predictions = tmp_path / "second-predictions"
    second_outcomes = tmp_path / "second-outcomes"

    _write_settled_case(
        first_predictions,
        first_outcomes,
        "match-b",
        prediction_filename="z-last.json",
    )
    _write_settled_case(
        first_predictions,
        first_outcomes,
        "match-a",
        prediction_filename="a-first.json",
    )
    _write_settled_case(
        second_predictions,
        second_outcomes,
        "match-a",
        prediction_filename="z-last.json",
    )
    _write_settled_case(
        second_predictions,
        second_outcomes,
        "match-b",
        prediction_filename="a-first.json",
    )

    first = build_governed_cohort_manifest(first_predictions, first_outcomes)
    second = build_governed_cohort_manifest(second_predictions, second_outcomes)

    assert first.to_dict() == second.to_dict()


def test_manifest_identity_changes_when_cohort_membership_changes(tmp_path: Path) -> None:
    predictions = tmp_path / "predictions"
    outcomes = tmp_path / "outcomes"
    _write_settled_case(predictions, outcomes, "match-a")

    before = build_governed_cohort_manifest(predictions, outcomes)
    _write_settled_case(predictions, outcomes, "match-b")
    after = build_governed_cohort_manifest(predictions, outcomes)

    assert before.case_count == 1
    assert after.case_count == 2
    assert before.sha256 != after.sha256


def test_manifest_identity_changes_on_prediction_substitution(tmp_path: Path) -> None:
    first_predictions = tmp_path / "first-predictions"
    second_predictions = tmp_path / "second-predictions"
    outcomes = tmp_path / "outcomes"
    _write(outcomes, "match-a.json", _outcome("match-a"))
    _write(
        first_predictions,
        "prediction.json",
        _prediction_record("match-a", "prediction-original"),
    )
    _write(
        second_predictions,
        "prediction.json",
        _prediction_record("match-a", "prediction-substitute"),
    )

    original = build_governed_cohort_manifest(first_predictions, outcomes)
    substitute = build_governed_cohort_manifest(second_predictions, outcomes)

    assert original.match_ids == substitute.match_ids == ("match-a",)
    assert original.prediction_ids != substitute.prediction_ids
    assert original.sha256 != substitute.sha256


def test_unsettled_prediction_is_not_admitted_to_manifest(tmp_path: Path) -> None:
    predictions = tmp_path / "predictions"
    outcomes = tmp_path / "outcomes"
    _write_settled_case(predictions, outcomes, "match-a")
    _write(predictions, "unsettled.json", _prediction_record("match-unsettled"))

    manifest = build_governed_cohort_manifest(predictions, outcomes)

    assert manifest.case_count == 1
    assert manifest.prediction_ids == ("prediction-match-a",)
    assert manifest.match_ids == ("match-a",)


def test_manifest_rejects_duplicate_prediction_ids(tmp_path: Path) -> None:
    predictions = tmp_path / "predictions"
    outcomes = tmp_path / "outcomes"
    _write_settled_case(
        predictions,
        outcomes,
        "match-a",
        prediction_id="prediction-duplicate",
        prediction_filename="a.json",
    )
    _write_settled_case(
        predictions,
        outcomes,
        "match-b",
        prediction_id="prediction-duplicate",
        prediction_filename="b.json",
    )

    with pytest.raises(
        ValueError,
        match="governed promotion cohort contains duplicate prediction_id: prediction-duplicate",
    ):
        build_governed_cohort_manifest(predictions, outcomes)


def test_manifest_rejects_duplicate_match_ids(tmp_path: Path) -> None:
    predictions = tmp_path / "predictions"
    outcomes = tmp_path / "outcomes"
    _write(outcomes, "match-a.json", _outcome("match-a"))
    _write(
        predictions,
        "first.json",
        _prediction_record("match-a", "prediction-first"),
    )
    _write(
        predictions,
        "second.json",
        _prediction_record("match-a", "prediction-second"),
    )

    with pytest.raises(
        ValueError,
        match="governed promotion cohort contains duplicate match_id: match-a",
    ):
        build_governed_cohort_manifest(predictions, outcomes)

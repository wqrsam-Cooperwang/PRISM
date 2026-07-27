import json
from copy import deepcopy
from datetime import datetime, timezone

import pytest

from src.ledger import (
    FileSystemPredictionLedgerStore,
    PredictionLedgerSnapshot,
    validate_formal_prediction_snapshot,
    validate_persisted_formal_snapshot,
)

FROZEN_AT = datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc)
KICKOFF = datetime(2026, 7, 27, 10, 30, tzinfo=timezone.utc)


def _payload() -> dict[str, object]:
    scorelines = [
        {"home_goals": 1, "away_goals": 0, "probability": 0.16},
        {"home_goals": 1, "away_goals": 1, "probability": 0.14},
    ]
    return {
        "report": {
            "match": {
                "match_id": "formal-contract-001",
                "competition": "Test League",
                "kickoff": KICKOFF.isoformat(),
                "home_team": "Home",
                "away_team": "Away",
            },
            "scoreline": {
                "available": True,
                "method": "scenario_mixture_poisson_v2_1",
                "recommended_scorelines": scorelines,
            },
            "provenance": {
                "prism_version": "2.1.0",
                "schema_version": "1.0.0",
                "runtime_version": "1.0.0",
                "session_id": "formal-contract-session",
            },
        },
        "observations": [],
        "collection_gate": {"decision": "ready"},
        "features": {"schema_version": "1.0.0"},
        "model_outputs": [
            {
                "model_id": "team_scoring_rate_xg",
                "model_version": "1.0.0",
                "home_probability": 0.40,
                "draw_probability": 0.30,
                "away_probability": 0.30,
                "expected_home_goals": 1.25,
                "expected_away_goals": 1.05,
                "diagnostics": {},
            }
        ],
        "shadow_predictions": {
            "v2_2": {
                "schema_version": "1.0.0",
                "candidate_version": "2.2.0-candidate1",
                "status": "available",
                "direction_calibration": {
                    "home_probability": 0.40,
                    "draw_probability": 0.30,
                    "away_probability": 0.30,
                    "reliability": 0.80,
                },
                "scoreline": {
                    "available": True,
                    "method": "regime_scenario_mixture_poisson_v2_2_candidate",
                    "recommended_scorelines": scorelines,
                },
            }
        },
    }


def _snapshot(
    *,
    payload: dict[str, object] | None = None,
    frozen_at: datetime = FROZEN_AT,
) -> PredictionLedgerSnapshot:
    return PredictionLedgerSnapshot(
        prediction_id="pred-formal-contract-001",
        match_id="formal-contract-001",
        frozen_at=frozen_at,
        payload=payload or _payload(),
    )


def _nested_mapping(payload: dict[str, object], *keys: str) -> dict[str, object]:
    current: object = payload
    for key in keys:
        assert isinstance(current, dict)
        current = current[key]
    assert isinstance(current, dict)
    return current


def test_formal_prediction_contract_accepts_complete_pre_match_snapshot(tmp_path) -> None:
    snapshot = _snapshot()

    validate_formal_prediction_snapshot(snapshot)
    path = FileSystemPredictionLedgerStore(tmp_path).persist(snapshot)
    validate_persisted_formal_snapshot(snapshot, path)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("production_unavailable", "available production scoreline"),
        ("production_not_dual", "exactly two production scorelines"),
        ("missing_model_version", "model_version must be a non-empty string"),
        ("shadow_unavailable", "available V2.2 shadow prediction"),
        ("missing_direction_calibration", "direction_calibration must be a mapping"),
        ("shadow_not_dual", "exactly two V2.2 shadow scorelines"),
        ("missing_candidate_version", "candidate_version must be a non-empty string"),
    ],
)
def test_formal_prediction_contract_rejects_incomplete_formal_samples(
    mutation: str,
    message: str,
) -> None:
    payload = deepcopy(_payload())
    production = _nested_mapping(payload, "report", "scoreline")
    shadow = _nested_mapping(payload, "shadow_predictions", "v2_2")
    shadow_scoreline = _nested_mapping(payload, "shadow_predictions", "v2_2", "scoreline")

    if mutation == "production_unavailable":
        production["available"] = False
    elif mutation == "production_not_dual":
        production["recommended_scorelines"] = production["recommended_scorelines"][:1]
    elif mutation == "missing_model_version":
        models = payload["model_outputs"]
        assert isinstance(models, list)
        assert isinstance(models[0], dict)
        models[0]["model_version"] = ""
    elif mutation == "shadow_unavailable":
        shadow["status"] = "scoreline_unavailable"
    elif mutation == "missing_direction_calibration":
        shadow["direction_calibration"] = None
    elif mutation == "shadow_not_dual":
        shadow_scoreline["recommended_scorelines"] = shadow_scoreline["recommended_scorelines"][:1]
    elif mutation == "missing_candidate_version":
        shadow["candidate_version"] = ""
    else:
        raise AssertionError(f"unknown mutation: {mutation}")

    with pytest.raises(ValueError, match=message):
        validate_formal_prediction_snapshot(_snapshot(payload=payload))


def test_formal_prediction_contract_rejects_freeze_at_kickoff() -> None:
    with pytest.raises(ValueError, match="frozen before kickoff"):
        validate_formal_prediction_snapshot(_snapshot(frozen_at=KICKOFF))


def test_formal_prediction_contract_rejects_sensitive_fields() -> None:
    payload = deepcopy(_payload())
    payload["provider_api_key"] = "must-not-persist"

    with pytest.raises(ValueError, match="sensitive field name"):
        validate_formal_prediction_snapshot(_snapshot(payload=payload))


def test_formal_prediction_contract_rejects_nested_sensitive_fields() -> None:
    payload = deepcopy(_payload())
    provenance = _nested_mapping(payload, "report", "provenance")
    provenance["access-token"] = "must-not-persist"

    with pytest.raises(ValueError, match="sensitive field name"):
        validate_formal_prediction_snapshot(_snapshot(payload=payload))


def test_formal_prediction_contract_rejects_tampered_persisted_record(tmp_path) -> None:
    snapshot = _snapshot()
    path = FileSystemPredictionLedgerStore(tmp_path).persist(snapshot)
    persisted = json.loads(path.read_text(encoding="utf-8"))
    persisted["match_id"] = "tampered"
    path.write_text(json.dumps(persisted), encoding="utf-8")

    with pytest.raises(ValueError, match="persisted match_id"):
        validate_persisted_formal_snapshot(snapshot, path)


def test_formal_prediction_contract_rejects_tampered_persisted_payload(tmp_path) -> None:
    snapshot = _snapshot()
    path = FileSystemPredictionLedgerStore(tmp_path).persist(snapshot)
    persisted = json.loads(path.read_text(encoding="utf-8"))
    persisted["payload"]["collection_gate"]["decision"] = "tampered"
    path.write_text(json.dumps(persisted), encoding="utf-8")

    with pytest.raises(ValueError, match="persisted payload"):
        validate_persisted_formal_snapshot(snapshot, path)

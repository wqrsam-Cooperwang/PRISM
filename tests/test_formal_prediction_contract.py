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


def _snapshot(*, payload: dict[str, object] | None = None) -> PredictionLedgerSnapshot:
    return PredictionLedgerSnapshot(
        prediction_id="pred-formal-contract-001",
        match_id="formal-contract-001",
        frozen_at=FROZEN_AT,
        payload=payload or _payload(),
    )


def test_formal_prediction_contract_accepts_complete_pre_match_snapshot(tmp_path) -> None:
    snapshot = _snapshot()

    validate_formal_prediction_snapshot(snapshot)
    path = FileSystemPredictionLedgerStore(tmp_path).persist(snapshot)
    validate_persisted_formal_snapshot(snapshot, path)


def test_formal_prediction_contract_rejects_unavailable_shadow() -> None:
    payload = deepcopy(_payload())
    shadows = payload["shadow_predictions"]
    assert isinstance(shadows, dict)
    shadow = shadows["v2_2"]
    assert isinstance(shadow, dict)
    shadow["status"] = "scoreline_unavailable"

    with pytest.raises(ValueError, match="available V2.2 shadow prediction"):
        validate_formal_prediction_snapshot(_snapshot(payload=payload))


def test_formal_prediction_contract_rejects_sensitive_fields() -> None:
    payload = deepcopy(_payload())
    payload["provider_api_key"] = "must-not-persist"

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

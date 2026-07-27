"""Machine-enforced contract for formal PRISM live prediction snapshots."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from src.ledger.models import PredictionLedgerSnapshot

_SENSITIVE_KEY_FRAGMENTS = ("api_key", "apikey", "secret", "token", "password")


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a mapping")
    return value


def _non_empty_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _reject_sensitive_keys(value: Any, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if any(fragment in normalized for fragment in _SENSITIVE_KEY_FRAGMENTS):
                raise ValueError(f"formal snapshot contains sensitive field name at {path}.{key}")
            _reject_sensitive_keys(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_sensitive_keys(item, f"{path}[{index}]")


def validate_formal_prediction_snapshot(snapshot: PredictionLedgerSnapshot) -> None:
    """Fail closed unless a snapshot is eligible for formal forward testing."""

    payload = _mapping(snapshot.payload, "payload")
    report = _mapping(payload.get("report"), "payload.report")
    match = _mapping(report.get("match"), "payload.report.match")
    provenance = _mapping(report.get("provenance"), "payload.report.provenance")
    production_scoreline = _mapping(report.get("scoreline"), "payload.report.scoreline")

    kickoff_text = _non_empty_text(match.get("kickoff"), "payload.report.match.kickoff")
    from datetime import datetime

    kickoff = datetime.fromisoformat(kickoff_text)
    if kickoff.tzinfo is None or kickoff.utcoffset() is None:
        raise ValueError("payload.report.match.kickoff must be timezone-aware")
    if snapshot.frozen_at >= kickoff:
        raise ValueError("formal prediction must be frozen before kickoff")

    for field_name in ("prism_version", "schema_version", "runtime_version", "session_id"):
        _non_empty_text(provenance.get(field_name), f"payload.report.provenance.{field_name}")

    if production_scoreline.get("available") is not True:
        raise ValueError("formal prediction requires an available production scoreline")
    production_recommendations = production_scoreline.get("recommended_scorelines")
    if not isinstance(production_recommendations, list) or len(production_recommendations) != 2:
        raise ValueError("formal prediction requires exactly two production scorelines")

    model_outputs = payload.get("model_outputs")
    if not isinstance(model_outputs, list) or not model_outputs:
        raise ValueError("formal prediction requires frozen model outputs")
    for index, model in enumerate(model_outputs):
        model_mapping = _mapping(model, f"payload.model_outputs[{index}]")
        _non_empty_text(model_mapping.get("model_id"), f"payload.model_outputs[{index}].model_id")
        _non_empty_text(
            model_mapping.get("model_version"),
            f"payload.model_outputs[{index}].model_version",
        )

    shadows = _mapping(payload.get("shadow_predictions"), "payload.shadow_predictions")
    shadow = _mapping(shadows.get("v2_2"), "payload.shadow_predictions.v2_2")
    _non_empty_text(shadow.get("schema_version"), "payload.shadow_predictions.v2_2.schema_version")
    _non_empty_text(
        shadow.get("candidate_version"),
        "payload.shadow_predictions.v2_2.candidate_version",
    )
    if shadow.get("status") != "available":
        raise ValueError("formal prediction requires an available V2.2 shadow prediction")
    _mapping(
        shadow.get("direction_calibration"),
        "payload.shadow_predictions.v2_2.direction_calibration",
    )
    shadow_scoreline = _mapping(
        shadow.get("scoreline"),
        "payload.shadow_predictions.v2_2.scoreline",
    )
    if shadow_scoreline.get("available") is not True:
        raise ValueError("formal prediction requires an available V2.2 shadow scoreline")
    shadow_recommendations = shadow_scoreline.get("recommended_scorelines")
    if not isinstance(shadow_recommendations, list) or len(shadow_recommendations) != 2:
        raise ValueError("formal prediction requires exactly two V2.2 shadow scorelines")

    _reject_sensitive_keys(payload)


def validate_persisted_formal_snapshot(
    snapshot: PredictionLedgerSnapshot,
    ledger_path: Path,
) -> None:
    """Verify the durable ledger record matches the in-memory formal snapshot."""

    if not ledger_path.is_file():
        raise ValueError("formal prediction ledger persistence did not create a file")
    try:
        persisted = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("formal prediction ledger record is not readable JSON") from exc

    if persisted.get("prediction_id") != snapshot.prediction_id:
        raise ValueError("persisted prediction_id does not match formal snapshot")
    if persisted.get("match_id") != snapshot.match_id:
        raise ValueError("persisted match_id does not match formal snapshot")
    if persisted.get("frozen_at") != snapshot.frozen_at.isoformat():
        raise ValueError("persisted frozen_at does not match formal snapshot")
    if persisted.get("payload") != snapshot.payload:
        raise ValueError("persisted payload does not match formal snapshot")

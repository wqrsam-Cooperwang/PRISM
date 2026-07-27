"""Load only contract-valid formal predictions into forward-testing cohorts."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.ledger.formal_contract import validate_formal_prediction_snapshot
from src.ledger.models import PredictionLedgerSnapshot


def load_formal_forward_testing_cohort(
    root: Path | str = "data/performance-ledger",
) -> tuple[PredictionLedgerSnapshot, ...]:
    """Return deterministic, contract-valid formal snapshots from the ledger root.

    Cohort construction fails closed: malformed JSON, malformed ledger envelopes,
    or snapshots that no longer satisfy the formal prediction contract are rejected
    instead of silently entering regression or forward-performance evaluation.
    """

    ledger_root = Path(root)
    if not ledger_root.exists():
        return ()

    snapshots: list[PredictionLedgerSnapshot] = []
    for path in sorted(ledger_root.glob("*.json")):
        snapshots.append(_load_formal_snapshot(path))
    return tuple(snapshots)


def _load_formal_snapshot(path: Path) -> PredictionLedgerSnapshot:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid formal ledger record: {path}") from exc
    if not isinstance(record, dict):
        raise ValueError(f"formal ledger record must be a mapping: {path}")

    snapshot = PredictionLedgerSnapshot(
        prediction_id=_text(record.get("prediction_id"), "prediction_id", path),
        match_id=_text(record.get("match_id"), "match_id", path),
        frozen_at=_datetime(record.get("frozen_at"), "frozen_at", path),
        payload=_payload(record.get("payload"), path),
        schema_version=_text(record.get("schema_version"), "schema_version", path),
    )
    validate_formal_prediction_snapshot(snapshot)
    return snapshot


def _text(value: Any, field: str, path: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"formal ledger {field} must be non-empty: {path}")
    return value.strip()


def _datetime(value: Any, field: str, path: Path) -> datetime:
    text = _text(value, field, path)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"formal ledger {field} must be ISO-8601: {path}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"formal ledger {field} must be timezone-aware: {path}")
    return parsed


def _payload(value: Any, path: Path) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"formal ledger payload must be a mapping: {path}")
    return value

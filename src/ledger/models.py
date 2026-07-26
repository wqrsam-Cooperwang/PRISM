"""Immutable autonomous performance-ledger models for PRISM."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

LEDGER_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class PredictionLedgerSnapshot:
    """Frozen pre-match record for one formal PRISM prediction."""

    prediction_id: str
    match_id: str
    frozen_at: datetime
    payload: dict[str, Any]
    schema_version: str = LEDGER_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prediction_id": self.prediction_id,
            "match_id": self.match_id,
            "frozen_at": self.frozen_at.isoformat(),
            "payload": self.payload,
        }

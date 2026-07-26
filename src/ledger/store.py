"""Append-only performance-ledger storage for PRISM."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from src.ledger.models import PredictionLedgerSnapshot


class PredictionLedgerStore(Protocol):
    """Durable store contract for frozen prediction snapshots."""

    def persist(self, snapshot: PredictionLedgerSnapshot) -> Path:
        """Persist one frozen snapshot and return its durable path."""
        ...


class FileSystemPredictionLedgerStore:
    """Write deterministic append-only JSON records under the repository ledger root."""

    def __init__(self, root: Path | str = "data/performance-ledger") -> None:
        self.root = Path(root)

    def persist(self, snapshot: PredictionLedgerSnapshot) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        destination = self.root / f"{snapshot.prediction_id}.json"
        if destination.exists():
            raise FileExistsError(f"Prediction snapshot already exists: {snapshot.prediction_id}")

        encoded = json.dumps(
            snapshot.to_dict(),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(encoded + "\n", encoding="utf-8")
        temporary.replace(destination)
        return destination

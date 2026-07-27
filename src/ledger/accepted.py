"""Persistence boundary for externally accepted formal PRISM prediction snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.ledger.formal_contract import (
    validate_formal_prediction_snapshot,
    validate_persisted_formal_snapshot,
)
from src.ledger.models import PredictionLedgerSnapshot
from src.ledger.store import PredictionLedgerStore


@dataclass(frozen=True)
class AcceptedPredictionResult:
    """One already-produced prediction accepted only after durable formal persistence."""

    snapshot: PredictionLedgerSnapshot
    ledger_path: Path


def persist_accepted_formal_prediction(
    snapshot: PredictionLedgerSnapshot,
    ledger_store: PredictionLedgerStore,
) -> AcceptedPredictionResult:
    """Atomically turn an accepted prediction into a governed forward-test record.

    The acceptance boundary fails closed: a snapshot is not considered formally
    accepted unless it satisfies the formal prediction contract, is durably written,
    and the persisted record matches the exact in-memory snapshot.
    """

    validate_formal_prediction_snapshot(snapshot)
    ledger_path = ledger_store.persist(snapshot)
    validate_persisted_formal_snapshot(snapshot, ledger_path)
    return AcceptedPredictionResult(snapshot=snapshot, ledger_path=ledger_path)

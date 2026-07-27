"""Governed settlement boundary for verified PRISM match outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.ledger.cohort import load_formal_forward_testing_cohort
from src.ledger.models import PredictionLedgerSnapshot
from src.ledger.outcomes import FileSystemOutcomeLedgerStore, MatchOutcome


@dataclass(frozen=True)
class SettledOutcomeResult:
    """One verified outcome linked to exactly one frozen formal prediction."""

    snapshot: PredictionLedgerSnapshot
    outcome: MatchOutcome
    ledger_path: Path


def settle_verified_outcome(
    outcome: MatchOutcome,
    outcome_store: FileSystemOutcomeLedgerStore,
    *,
    prediction_root: Path | str = "data/performance-ledger",
) -> SettledOutcomeResult:
    """Persist an outcome only when it settles one exact formal prediction."""

    cohort = load_formal_forward_testing_cohort(prediction_root)
    matches = tuple(snapshot for snapshot in cohort if snapshot.match_id == outcome.match_id)
    if not matches:
        raise ValueError(f"no formal prediction exists for match_id: {outcome.match_id}")
    if len(matches) != 1:
        raise ValueError(f"ambiguous formal prediction match_id: {outcome.match_id}")

    snapshot = matches[0]
    kickoff = _kickoff(snapshot)
    if outcome.settled_at <= kickoff:
        raise ValueError("verified outcome must be settled after kickoff")

    ledger_path = outcome_store.persist(outcome)
    return SettledOutcomeResult(
        snapshot=snapshot,
        outcome=outcome,
        ledger_path=ledger_path,
    )


def _kickoff(snapshot: PredictionLedgerSnapshot) -> datetime:
    report = snapshot.payload["report"]
    match = report["match"]
    kickoff = datetime.fromisoformat(match["kickoff"])
    if kickoff.tzinfo is None or kickoff.utcoffset() is None:
        raise ValueError("formal prediction kickoff must be timezone-aware")
    return kickoff

"""Governed regression dataset construction from formal prediction and outcome ledgers."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from src.ledger import MatchOutcome, load_formal_forward_testing_cohort
from src.regression.importer import regression_case_from_ledgers
from src.regression.scoreline import ScorelineRegressionCase


def load_governed_ledger_regression_dataset(
    prediction_root: Path | str = "data/performance-ledger",
    outcome_root: Path | str = "data/outcome-ledger",
) -> tuple[ScorelineRegressionCase, ...]:
    """Build replay cases only from contract-valid formal predictions with outcomes.

    Predictions enter through the formal forward-testing cohort loader, so malformed
    or non-formal snapshots cannot bypass the admission contract. Missing outcomes
    are treated as unsettled forward-test cases and are skipped; an existing but
    malformed outcome record fails closed.
    """

    snapshots = load_formal_forward_testing_cohort(prediction_root)
    outcomes = Path(outcome_root)
    cases: list[ScorelineRegressionCase] = []
    for snapshot in snapshots:
        outcome_path = outcomes / f"{snapshot.match_id}.json"
        if not outcome_path.exists():
            continue
        outcome = _load_outcome(outcome_path)
        cases.append(regression_case_from_ledgers(snapshot, outcome))
    return tuple(cases)


def _load_outcome(path: Path) -> MatchOutcome:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid outcome ledger record: {path}") from exc
    if not isinstance(record, dict):
        raise ValueError(f"outcome ledger record must be a mapping: {path}")
    return MatchOutcome(
        match_id=_text(record.get("match_id"), "match_id", path),
        home_goals=_goal(record.get("home_goals"), "home_goals", path),
        away_goals=_goal(record.get("away_goals"), "away_goals", path),
        settled_at=_datetime(record.get("settled_at"), "settled_at", path),
        source=_text(record.get("source"), "source", path),
    )


def _text(value: Any, field: str, path: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"outcome ledger {field} must be non-empty: {path}")
    return value.strip()


def _goal(value: Any, field: str, path: Path) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"outcome ledger {field} must be a non-negative integer: {path}")
    return cast(int, value)


def _datetime(value: Any, field: str, path: Path) -> datetime:
    text = _text(value, field, path)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"outcome ledger {field} must be ISO-8601: {path}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"outcome ledger {field} must be timezone-aware: {path}")
    return parsed

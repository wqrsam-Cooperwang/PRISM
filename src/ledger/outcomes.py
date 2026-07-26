"""Immutable post-match outcome records for PRISM performance evaluation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class MatchOutcome:
    """One verified final score linked to a PRISM match identity."""

    match_id: str
    home_goals: int
    away_goals: int
    settled_at: datetime
    source: str = "verified_result"

    def __post_init__(self) -> None:
        if not self.match_id.strip():
            raise ValueError("match_id must not be blank")
        for value in (self.home_goals, self.away_goals):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError("outcome goals must be non-negative integers")
        if self.settled_at.tzinfo is None or self.settled_at.utcoffset() is None:
            raise ValueError("settled_at must be timezone-aware")
        if not self.source.strip():
            raise ValueError("source must not be blank")

    def to_dict(self) -> dict[str, object]:
        return {
            "match_id": self.match_id,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "settled_at": self.settled_at.isoformat(),
            "source": self.source,
        }


class FileSystemOutcomeLedgerStore:
    """Persist one append-only verified outcome per match."""

    def __init__(self, root: Path | str = "data/outcome-ledger") -> None:
        self.root = Path(root)

    def persist(self, outcome: MatchOutcome) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        destination = self.root / f"{outcome.match_id}.json"
        if destination.exists():
            raise FileExistsError(f"Match outcome already exists: {outcome.match_id}")
        encoded = json.dumps(
            outcome.to_dict(),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(encoded + "\n", encoding="utf-8")
        temporary.replace(destination)
        return destination

"""Immutable acquisition request models for PRISM provider clients."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.intelligence.models import MatchTarget


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_aware_datetime(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


@dataclass(frozen=True)
class ProviderFetchRequest:
    """One immutable match-scoped provider acquisition request."""

    request_id: str
    target: MatchTarget
    requested_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _require_text(self.request_id, "request_id"))
        object.__setattr__(
            self,
            "requested_at",
            _require_aware_datetime(self.requested_at, "requested_at"),
        )

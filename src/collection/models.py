"""Immutable source payload models for PRISM automated collection."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any

from src.intelligence.models import SourceRef


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
class SourceEnvelope:
    """One retrieved external-source payload plus immutable provenance."""

    adapter_id: str
    source: SourceRef
    retrieved_at: datetime
    payload: Mapping[str, Any]
    request_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "adapter_id", _require_text(self.adapter_id, "adapter_id"))
        object.__setattr__(
            self,
            "retrieved_at",
            _require_aware_datetime(self.retrieved_at, "retrieved_at"),
        )
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))
        if self.request_id is not None:
            object.__setattr__(self, "request_id", _require_text(self.request_id, "request_id"))

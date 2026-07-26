"""Immutable HTTP transport models for PRISM provider connectors."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite
from types import MappingProxyType


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_timeout(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("timeout_seconds must be a positive finite number")
    result = float(value)
    if not isfinite(result) or result <= 0:
        raise ValueError("timeout_seconds must be a positive finite number")
    return result


def _require_aware_datetime(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


@dataclass(frozen=True)
class HttpRequest:
    """One immutable outbound HTTP request."""

    method: str
    url: str
    headers: Mapping[str, str] = field(default_factory=dict, repr=False)
    query: Mapping[str, str] = field(default_factory=dict, repr=False)
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        method = _require_text(self.method, "method").upper()
        if method not in {"GET", "POST"}:
            raise ValueError("method must be GET or POST")
        url = _require_text(self.url, "url")
        if not url.startswith(("https://", "http://")):
            raise ValueError("url must use http or https")
        headers = {str(key): str(value) for key, value in self.headers.items()}
        query = {str(key): str(value) for key, value in self.query.items()}
        object.__setattr__(self, "method", method)
        object.__setattr__(self, "url", url)
        object.__setattr__(self, "headers", MappingProxyType(headers))
        object.__setattr__(self, "query", MappingProxyType(query))
        object.__setattr__(self, "timeout_seconds", _require_timeout(self.timeout_seconds))


@dataclass(frozen=True)
class HttpResponse:
    """One immutable HTTP response captured with receipt provenance."""

    status_code: int
    headers: Mapping[str, str]
    body: bytes
    received_at: datetime

    def __post_init__(self) -> None:
        if isinstance(self.status_code, bool) or not isinstance(self.status_code, int):
            raise ValueError("status_code must be an integer")
        if not 100 <= self.status_code <= 599:
            raise ValueError("status_code must be between 100 and 599")
        if not isinstance(self.body, bytes):
            raise TypeError("body must be bytes")
        object.__setattr__(
            self,
            "headers",
            MappingProxyType({str(key): str(value) for key, value in self.headers.items()}),
        )
        object.__setattr__(
            self,
            "received_at",
            _require_aware_datetime(self.received_at, "received_at"),
        )

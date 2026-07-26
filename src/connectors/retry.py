"""Deterministic retry policy for PRISM HTTP provider connectors."""

from __future__ import annotations

from dataclasses import dataclass

from src.connectors.errors import HttpStatusError, HttpTransportError
from src.connectors.interface import HttpTransport
from src.connectors.models import HttpRequest, HttpResponse

_DEFAULT_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded retry policy without operational sleep/backoff concerns."""

    max_attempts: int = 3
    retryable_statuses: frozenset[int] = _DEFAULT_RETRYABLE_STATUSES

    def __post_init__(self) -> None:
        if isinstance(self.max_attempts, bool) or not isinstance(self.max_attempts, int):
            raise ValueError("max_attempts must be an integer")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        statuses = frozenset(self.retryable_statuses)
        if not all(isinstance(item, int) and not isinstance(item, bool) for item in statuses):
            raise ValueError("retryable_statuses must contain integer HTTP status codes")
        if not all(100 <= item <= 599 for item in statuses):
            raise ValueError("retryable_statuses must contain valid HTTP status codes")
        object.__setattr__(self, "retryable_statuses", statuses)


def send_with_retry(
    transport: HttpTransport,
    request: HttpRequest,
    policy: RetryPolicy = RetryPolicy(),
) -> HttpResponse:
    """Execute one request with bounded retry and fail-closed HTTP status handling."""

    last_transport_error: HttpTransportError | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            response = transport.send(request)
        except HttpTransportError as exc:
            last_transport_error = exc
            if attempt == policy.max_attempts:
                raise
            continue

        if 200 <= response.status_code <= 299:
            return response
        if response.status_code in policy.retryable_statuses and attempt < policy.max_attempts:
            continue
        raise HttpStatusError(response.status_code)

    if last_transport_error is not None:
        raise last_transport_error
    raise RuntimeError("HTTP retry loop exhausted without response or transport error")

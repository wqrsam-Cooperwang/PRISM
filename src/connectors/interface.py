"""HTTP transport protocol for provider-neutral PRISM connectors."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.connectors.models import HttpRequest, HttpResponse


@runtime_checkable
class HttpTransport(Protocol):
    """Contract implemented by real and fixture HTTP transports."""

    def send(self, request: HttpRequest) -> HttpResponse:
        """Execute one HTTP request or raise a transport-layer exception."""
        ...

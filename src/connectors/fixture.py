"""Deterministic fixture HTTP transport for connector tests and replay."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.connectors.errors import HttpTransportError
from src.connectors.models import HttpRequest, HttpResponse


@dataclass
class FixtureHttpTransport:
    """Replay preconfigured HTTP outcomes without network access."""

    outcomes: list[HttpResponse | HttpTransportError]
    requests: list[HttpRequest] = field(default_factory=list)

    def send(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request)
        if not self.outcomes:
            raise HttpTransportError("Fixture transport has no remaining outcomes")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, HttpTransportError):
            raise outcome
        return outcome

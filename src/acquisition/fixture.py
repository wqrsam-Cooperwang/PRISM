"""Fixture-backed provider client for deterministic acquisition tests."""

from __future__ import annotations

from dataclasses import dataclass

from src.acquisition.models import ProviderFetchRequest
from src.collection.models import SourceEnvelope


@dataclass(frozen=True)
class FixtureProviderClient:
    """Return predefined source envelopes for one acquisition request."""

    client_id: str
    envelopes: tuple[SourceEnvelope, ...]

    def fetch(self, request: ProviderFetchRequest) -> tuple[SourceEnvelope, ...]:
        del request
        return tuple(self.envelopes)

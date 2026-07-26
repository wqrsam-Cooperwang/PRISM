"""Provider-client protocol for PRISM live acquisition."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.acquisition.models import ProviderFetchRequest
from src.collection.models import SourceEnvelope


@runtime_checkable
class ProviderClient(Protocol):
    """Contract implemented by provider-specific acquisition clients."""

    @property
    def client_id(self) -> str:
        """Stable provider-client identifier."""
        ...

    def fetch(self, request: ProviderFetchRequest) -> tuple[SourceEnvelope, ...]:
        """Retrieve provider payloads for one immutable match-scoped request."""
        ...

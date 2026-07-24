"""Adapter protocol for deterministic PRISM source translation."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.collection.models import SourceEnvelope
from src.intelligence.models import MatchTarget, Observation


@runtime_checkable
class ObservationAdapter(Protocol):
    """Contract implemented by every PRISM external-source adapter."""

    @property
    def adapter_id(self) -> str:
        """Stable adapter identifier."""
        ...

    def adapt(
        self,
        target: MatchTarget,
        envelope: SourceEnvelope,
    ) -> tuple[Observation, ...]:
        """Translate one source payload into existing intelligence observations."""
        ...

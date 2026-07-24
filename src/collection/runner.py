"""Governed execution helpers for PRISM source adapters."""

from __future__ import annotations

from collections.abc import Iterable

from src.collection.interface import ObservationAdapter
from src.collection.models import SourceEnvelope
from src.intelligence.models import MatchTarget, Observation


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def collect_observations(
    target: MatchTarget,
    adapters: Iterable[ObservationAdapter],
    envelopes: Iterable[SourceEnvelope],
) -> tuple[Observation, ...]:
    """Run adapters deterministically and return uniquely identified observations."""

    configured = tuple(adapters)
    adapter_ids = tuple(_require_text(adapter.adapter_id, "adapter_id") for adapter in configured)
    if len(set(adapter_ids)) != len(adapter_ids):
        raise ValueError("Collection adapter identifiers must be unique")

    by_id = {adapter.adapter_id: adapter for adapter in configured}
    ordered_envelopes = tuple(
        sorted(
            envelopes,
            key=lambda envelope: (
                envelope.adapter_id,
                envelope.source.source_id,
                envelope.retrieved_at.isoformat(),
                envelope.request_id or "",
            ),
        )
    )

    observations: list[Observation] = []
    for envelope in ordered_envelopes:
        adapter = by_id.get(envelope.adapter_id)
        if adapter is None:
            raise ValueError(f"No collection adapter configured for {envelope.adapter_id}")
        produced = adapter.adapt(target, envelope)
        observations.extend(produced)

    observation_ids = tuple(item.observation_id for item in observations)
    if len(set(observation_ids)) != len(observation_ids):
        raise ValueError("Collected observation identifiers must be unique")

    return tuple(sorted(observations, key=lambda item: item.observation_id))

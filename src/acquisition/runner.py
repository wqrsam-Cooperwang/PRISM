"""Deterministic provider acquisition orchestration for PRISM."""

from __future__ import annotations

from collections.abc import Iterable

from src.acquisition.interface import ProviderClient
from src.acquisition.models import ProviderFetchRequest
from src.collection.models import SourceEnvelope


class ProviderAcquisitionError(RuntimeError):
    """Wrap one provider-client failure with stable client identity."""

    def __init__(self, client_id: str) -> None:
        self.client_id = client_id
        super().__init__(f"Provider acquisition failed: {client_id}")


def _client_id(client: ProviderClient) -> str:
    value = client.client_id
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Provider client_id must be a non-empty string")
    return value.strip()


def _envelope_identity(envelope: SourceEnvelope) -> tuple[str, str, str]:
    return (
        envelope.adapter_id,
        envelope.source.source_id,
        envelope.request_id or "",
    )


def acquire_source_envelopes(
    request: ProviderFetchRequest,
    clients: Iterable[ProviderClient],
) -> tuple[SourceEnvelope, ...]:
    """Run unique provider clients and return deterministic source envelopes."""

    materialized = tuple(clients)
    client_ids = tuple(_client_id(client) for client in materialized)
    if len(client_ids) != len(set(client_ids)):
        raise ValueError("Provider client_ids must be unique")

    envelopes: list[SourceEnvelope] = []
    client_pairs = zip(materialized, client_ids, strict=True)
    for client, client_id in sorted(client_pairs, key=lambda item: item[1]):
        try:
            fetched = tuple(client.fetch(request))
        except Exception as exc:
            raise ProviderAcquisitionError(client_id) from exc
        for envelope in fetched:
            if envelope.request_id != request.request_id:
                raise ValueError(
                    f"Provider envelope request_id does not match acquisition request: {client_id}"
                )
            envelopes.append(envelope)

    identities = tuple(_envelope_identity(item) for item in envelopes)
    if len(identities) != len(set(identities)):
        raise ValueError("Provider acquisition emitted duplicate source envelope identities")

    return tuple(sorted(envelopes, key=_envelope_identity))

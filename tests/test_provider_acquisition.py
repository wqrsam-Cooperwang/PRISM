from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from src.acquisition import (
    FixtureProviderClient,
    ProviderAcquisitionError,
    ProviderFetchRequest,
    acquire_source_envelopes,
)
from src.collection import FixtureObservationAdapter, SourceEnvelope, collect_observations
from src.intelligence import MatchTarget, SourceRef, SourceType

NOW = datetime(2026, 7, 26, 10, 0, tzinfo=timezone.utc)


def _target() -> MatchTarget:
    return MatchTarget(
        match_id="acquisition-001",
        competition="Test League",
        kickoff=datetime(2026, 7, 27, 18, 0, tzinfo=timezone.utc),
        home_team_id="home-id",
        home_team_name="Home FC",
        away_team_id="away-id",
        away_team_name="Away FC",
    )


def _request() -> ProviderFetchRequest:
    return ProviderFetchRequest(
        request_id="request-001",
        target=_target(),
        requested_at=NOW,
    )


def _envelope(source_id: str, observation_id: str) -> SourceEnvelope:
    return SourceEnvelope(
        adapter_id="fixture_observations",
        source=SourceRef(source_id=source_id, source_type=SourceType.PRIMARY_DATA),
        retrieved_at=NOW,
        request_id="request-001",
        payload={
            "observations": (
                {
                    "observation_id": observation_id,
                    "category": "team_strength",
                    "subject": "home",
                    "claim_key": "elo_rating",
                    "value": 1600,
                    "observed_at": "2026-07-26T09:30:00+00:00",
                },
            )
        },
    )


def test_acquisition_is_deterministic_across_client_order() -> None:
    first = FixtureProviderClient("z-client", (_envelope("z-source", "z-observation"),))
    second = FixtureProviderClient("a-client", (_envelope("a-source", "a-observation"),))

    forward = acquire_source_envelopes(_request(), (first, second))
    reverse = acquire_source_envelopes(_request(), (second, first))

    assert forward == reverse
    assert tuple(item.source.source_id for item in forward) == ("a-source", "z-source")


def test_acquired_envelopes_enter_existing_collection_path() -> None:
    client = FixtureProviderClient("fixture-client", (_envelope("source", "observation"),))
    envelopes = acquire_source_envelopes(_request(), (client,))

    observations = collect_observations(
        _target(),
        (FixtureObservationAdapter(),),
        envelopes,
    )

    assert len(observations) == 1
    assert observations[0].observation_id == "observation"
    assert observations[0].value == 1600


def test_duplicate_client_ids_fail_closed() -> None:
    first = FixtureProviderClient("duplicate", (_envelope("a-source", "a"),))
    second = FixtureProviderClient("duplicate", (_envelope("b-source", "b"),))

    with pytest.raises(ValueError, match="client_ids must be unique"):
        acquire_source_envelopes(_request(), (first, second))


def test_mismatched_request_id_fails_closed() -> None:
    envelope = SourceEnvelope(
        adapter_id="fixture_observations",
        source=SourceRef(source_id="source", source_type=SourceType.PRIMARY_DATA),
        retrieved_at=NOW,
        request_id="wrong-request",
        payload={"observations": ()},
    )
    client = FixtureProviderClient("fixture-client", (envelope,))

    with pytest.raises(ValueError, match="request_id does not match"):
        acquire_source_envelopes(_request(), (client,))


def test_duplicate_envelope_identity_fails_closed() -> None:
    envelope = _envelope("source", "observation")
    client = FixtureProviderClient("fixture-client", (envelope, envelope))

    with pytest.raises(ValueError, match="duplicate source envelope identities"):
        acquire_source_envelopes(_request(), (client,))


def test_provider_failure_preserves_client_identity() -> None:
    @dataclass(frozen=True)
    class FailingClient:
        client_id: str = "failing-client"

        def fetch(self, request: ProviderFetchRequest) -> tuple[SourceEnvelope, ...]:
            del request
            raise RuntimeError("provider unavailable")

    with pytest.raises(ProviderAcquisitionError) as captured:
        acquire_source_envelopes(_request(), (FailingClient(),))

    assert captured.value.client_id == "failing-client"

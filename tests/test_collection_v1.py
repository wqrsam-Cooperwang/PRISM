from datetime import datetime, timezone

import pytest

from src.collection import FixtureObservationAdapter, SourceEnvelope, collect_observations
from src.intelligence import (
    IntelligenceCategory,
    MatchTarget,
    SourceRef,
    SourceType,
    build_intelligence_bundle,
)

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
KICKOFF = datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc)


def _target() -> MatchTarget:
    return MatchTarget(
        match_id="collection-match-001",
        competition="Test League",
        kickoff=KICKOFF,
        home_team_id="home-id",
        home_team_name="Home FC",
        away_team_id="away-id",
        away_team_name="Away FC",
    )


def _envelope(
    source_id: str,
    observations: list[dict[str, object]],
    *,
    adapter_id: str = "fixture_observations",
) -> SourceEnvelope:
    return SourceEnvelope(
        adapter_id=adapter_id,
        source=SourceRef(source_id=source_id, source_type=SourceType.PRIMARY_DATA),
        retrieved_at=NOW,
        payload={"observations": observations},
        request_id=f"request-{source_id}",
    )


def _row(
    observation_id: str,
    category: IntelligenceCategory,
    claim_key: str,
    value: object,
    *,
    subject: str | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "observation_id": observation_id,
        "category": category.value,
        "claim_key": claim_key,
        "value": value,
        "observed_at": "2026-07-24T11:00:00+00:00",
    }
    if subject is not None:
        row["subject"] = subject
    return row


def test_fixture_adapter_emits_existing_observation_domain() -> None:
    envelope = _envelope(
        "provider-a",
        [
            _row(
                "elo-home",
                IntelligenceCategory.TEAM_STRENGTH,
                "elo_rating",
                1600,
                subject="home",
            ),
            _row(
                "elo-away",
                IntelligenceCategory.TEAM_STRENGTH,
                "elo_rating",
                1500,
                subject="away",
            ),
        ],
    )

    observations = collect_observations(_target(), (FixtureObservationAdapter(),), (envelope,))

    assert tuple(item.observation_id for item in observations) == ("elo-away", "elo-home")
    assert observations[0].source.source_id == "provider-a"
    assert observations[0].collected_at == NOW


def test_collected_observations_feed_existing_verification_pipeline() -> None:
    envelope = _envelope(
        "provider-a",
        [
            _row(
                "market-home",
                IntelligenceCategory.MARKET,
                "home_decimal_odds",
                2.0,
            )
        ],
    )
    observations = collect_observations(_target(), (FixtureObservationAdapter(),), (envelope,))

    bundle = build_intelligence_bundle(_target(), observations, collected_at=NOW)

    assert bundle.observations == observations
    assert bundle.claims[0].claim_key == "home_decimal_odds"
    assert bundle.claims[0].value == 2.0


def test_collection_order_is_deterministic_across_envelope_order() -> None:
    first = _envelope(
        "provider-b",
        [_row("obs-b", IntelligenceCategory.RECENT_FORM, "points_last_5", 8, subject="away")],
    )
    second = _envelope(
        "provider-a",
        [_row("obs-a", IntelligenceCategory.RECENT_FORM, "points_last_5", 10, subject="home")],
    )
    adapter = FixtureObservationAdapter()

    left = collect_observations(_target(), (adapter,), (first, second))
    right = collect_observations(_target(), (adapter,), (second, first))

    assert left == right
    assert tuple(item.observation_id for item in left) == ("obs-a", "obs-b")


def test_duplicate_observation_ids_fail_closed() -> None:
    first = _envelope(
        "provider-a",
        [_row("duplicate", IntelligenceCategory.SCHEDULE, "rest_days", 5, subject="home")],
    )
    second = _envelope(
        "provider-b",
        [_row("duplicate", IntelligenceCategory.SCHEDULE, "rest_days", 6, subject="away")],
    )

    with pytest.raises(ValueError, match="observation identifiers must be unique"):
        collect_observations(_target(), (FixtureObservationAdapter(),), (first, second))


def test_duplicate_adapter_ids_fail_closed() -> None:
    envelope = _envelope(
        "provider-a",
        [_row("obs", IntelligenceCategory.WEATHER, "temperature_c", 18)],
    )

    with pytest.raises(ValueError, match="adapter identifiers must be unique"):
        collect_observations(
            _target(),
            (FixtureObservationAdapter(), FixtureObservationAdapter()),
            (envelope,),
        )


def test_unconfigured_adapter_fails_closed() -> None:
    envelope = _envelope(
        "provider-a",
        [_row("obs", IntelligenceCategory.WEATHER, "temperature_c", 18)],
        adapter_id="missing-adapter",
    )

    with pytest.raises(ValueError, match="No collection adapter configured"):
        collect_observations(_target(), (FixtureObservationAdapter(),), (envelope,))


def test_fixture_adapter_rejects_missing_value_without_imputation() -> None:
    row = _row("obs", IntelligenceCategory.AVAILABILITY, "missing_starters", 1)
    del row["value"]
    envelope = _envelope("provider-a", [row])

    with pytest.raises(ValueError, match="must contain value"):
        collect_observations(_target(), (FixtureObservationAdapter(),), (envelope,))

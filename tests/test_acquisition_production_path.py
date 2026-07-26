from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from src.acquisition import (
    FixtureProviderClient,
    ProviderAcquisitionError,
    ProviderFetchRequest,
    run_acquired_prediction_path,
)
from src.collection import (
    AvailabilityScheduleAdapter,
    FixtureObservationAdapter,
    MarketOdds1X2Adapter,
    SourceEnvelope,
    TeamStrengthFormAdapter,
    WeatherLineupAdapter,
)
from src.intelligence import MatchTarget, SourceRef, SourceType

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
KICKOFF = datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc)
REQUEST_ID = "acquired-production-001"


def _target() -> MatchTarget:
    return MatchTarget(
        match_id="acquired-production-001",
        competition="Test League",
        kickoff=KICKOFF,
        home_team_id="home-id",
        home_team_name="Home FC",
        away_team_id="away-id",
        away_team_name="Away FC",
        season="2026",
        stage="Round 10",
        venue="Test Ground",
    )


def _request() -> ProviderFetchRequest:
    return ProviderFetchRequest(request_id=REQUEST_ID, target=_target(), requested_at=NOW)


def _envelope(
    adapter_id: str,
    source_id: str,
    source_type: SourceType,
    payload: dict[str, object],
) -> SourceEnvelope:
    return SourceEnvelope(
        adapter_id=adapter_id,
        source=SourceRef(source_id=source_id, source_type=source_type),
        retrieved_at=NOW,
        request_id=REQUEST_ID,
        payload=payload,
    )


def _market_envelope() -> SourceEnvelope:
    return _envelope(
        "market_odds_1x2",
        "market-provider",
        SourceType.MARKET,
        {
            "observed_at": "2026-07-24T11:30:00+00:00",
            "home_team_id": "home-id",
            "away_team_id": "away-id",
            "home_decimal_odds": 1.95,
            "draw_decimal_odds": 3.4,
            "away_decimal_odds": 4.2,
        },
    )


def _strength_envelope() -> SourceEnvelope:
    return _envelope(
        "team_strength_form",
        "strength-provider",
        SourceType.PRIMARY_DATA,
        {
            "observed_at": "2026-07-24T11:00:00+00:00",
            "home_team_id": "home-id",
            "away_team_id": "away-id",
            "home": {"elo_rating": 1620, "points_last_5": 11},
            "away": {"elo_rating": 1540, "points_last_5": 6},
        },
    )


def _availability_envelope() -> SourceEnvelope:
    return _envelope(
        "availability_schedule",
        "availability-provider",
        SourceType.OFFICIAL,
        {
            "observed_at": "2026-07-24T10:45:00+00:00",
            "home_team_id": "home-id",
            "away_team_id": "away-id",
            "home": {"missing_starters": 1, "rest_days": 6},
            "away": {"missing_starters": 3, "rest_days": 4},
        },
    )


def _weather_envelope() -> SourceEnvelope:
    return _envelope(
        "weather_lineup",
        "weather-lineup-provider",
        SourceType.OFFICIAL,
        {
            "observed_at": "2026-07-24T11:15:00+00:00",
            "home_team_id": "home-id",
            "away_team_id": "away-id",
            "weather": {"temperature_c": 18.5},
            "home": {"formation": "4-3-3"},
            "away": {"formation": "4-2-3-1"},
        },
    )


def _ready_adapters():
    return (
        MarketOdds1X2Adapter(),
        TeamStrengthFormAdapter(),
        AvailabilityScheduleAdapter(),
        WeatherLineupAdapter(),
    )


def _ready_clients():
    return (
        FixtureProviderClient("z-weather", (_weather_envelope(),)),
        FixtureProviderClient("a-market", (_market_envelope(),)),
        FixtureProviderClient("m-strength", (_strength_envelope(),)),
        FixtureProviderClient("n-availability", (_availability_envelope(),)),
    )


def test_ready_acquisition_runs_through_final_report() -> None:
    result = run_acquired_prediction_path(
        _request(),
        _ready_clients(),
        _ready_adapters(),
        collected_at=NOW,
        prism_version="test",
        created_at=NOW,
        git_commit="acquired-test-commit",
        data_version="acquired-fixture-v1",
    )

    assert result.collection_gate.decision.value == "ready"
    assert len(result.observations) == 14
    assert result.features.values["elo_difference"] == pytest.approx(80.0)
    assert result.report.scoreline is not None
    assert result.report.provenance.git_commit == "acquired-test-commit"
    assert result.report.provenance.data_version == "acquired-fixture-v1"


def _degraded_envelope() -> SourceEnvelope:
    rows = (
        {
            "observation_id": "elo-home",
            "category": "team_strength",
            "subject": "home",
            "claim_key": "elo_rating",
            "value": 1620,
            "observed_at": "2026-07-24T11:00:00+00:00",
        },
        {
            "observation_id": "elo-away",
            "category": "team_strength",
            "subject": "away",
            "claim_key": "elo_rating",
            "value": 1540,
            "observed_at": "2026-07-24T11:00:00+00:00",
        },
    )
    return _envelope(
        "fixture_observations",
        "elo-fixture",
        SourceType.PRIMARY_DATA,
        {"observations": rows},
    )


def test_degraded_acquisition_preserves_governance_through_runtime() -> None:
    clients = (
        FixtureProviderClient("elo-client", (_degraded_envelope(),)),
        FixtureProviderClient("market-client", (_market_envelope(),)),
    )
    result = run_acquired_prediction_path(
        _request(),
        clients,
        (FixtureObservationAdapter(), MarketOdds1X2Adapter()),
        collected_at=NOW,
        prism_version="test",
        created_at=NOW,
    )

    assert result.collection_gate.decision.value == "degraded"
    records = tuple(
        output
        for output in result.runtime_result.context.rule_outputs
        if output.get("governance_source") == "collection_readiness_gate"
    )
    assert len(records) == 1
    assert records[0]["collection_gate_decision"] == "degraded"
    assert records[0]["suppressed_effects"] == ("restrict_high_confidence_action",)
    assert result.report.adjustment is not None
    assert result.report.adjustment.decision_blocked is True


def test_provider_failure_stops_before_prediction() -> None:
    @dataclass(frozen=True)
    class FailingClient:
        client_id: str = "failing-client"

        def fetch(self, request: ProviderFetchRequest) -> tuple[SourceEnvelope, ...]:
            del request
            raise RuntimeError("provider unavailable")

    with pytest.raises(ProviderAcquisitionError) as captured:
        run_acquired_prediction_path(
            _request(),
            (FailingClient(),),
            _ready_adapters(),
            collected_at=NOW,
            prism_version="test",
            created_at=NOW,
        )

    assert captured.value.client_id == "failing-client"


def test_client_order_does_not_change_downstream_artifacts() -> None:
    clients = _ready_clients()
    forward = run_acquired_prediction_path(
        _request(),
        clients,
        _ready_adapters(),
        collected_at=NOW,
        prism_version="test",
        created_at=NOW,
    )
    reverse = run_acquired_prediction_path(
        _request(),
        tuple(reversed(clients)),
        _ready_adapters(),
        collected_at=NOW,
        prism_version="test",
        created_at=NOW,
    )

    assert forward.observations == reverse.observations
    assert forward.features == reverse.features
    assert forward.collection_gate == reverse.collection_gate
    assert forward.report == reverse.report

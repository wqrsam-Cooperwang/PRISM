import json
from datetime import datetime, timezone

import pytest

from src.acquisition import (
    FixtureProviderClient,
    ProviderFetchRequest,
    run_live_market_prediction_path,
)
from src.collection import (
    AvailabilityScheduleAdapter,
    SourceEnvelope,
    TeamStrengthFormAdapter,
    WeatherLineupAdapter,
)
from src.connectors import FixtureHttpTransport, HttpResponse
from src.intelligence import MatchTarget, SourceRef, SourceType

NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)
KICKOFF = datetime(2026, 7, 27, 10, 30, tzinfo=timezone.utc)
REQUEST_ID = "live-production-001"
SECRET = "live-secret-test-key"


def _target() -> MatchTarget:
    return MatchTarget(
        match_id="live-production-001",
        competition="K League 1",
        kickoff=KICKOFF,
        home_team_id="anyang",
        home_team_name="FC Anyang",
        away_team_id="gangwon",
        away_team_name="Gangwon FC",
        season="2026",
        stage="Round 20",
    )


def _request() -> ProviderFetchRequest:
    return ProviderFetchRequest(request_id=REQUEST_ID, target=_target(), requested_at=NOW)


def _market_transport() -> FixtureHttpTransport:
    payload = [
        {
            "id": "provider-event-001",
            "sport_key": "soccer_korea_kleague1",
            "commence_time": "2026-07-27T10:30:00Z",
            "home_team": "FC Anyang",
            "away_team": "Gangwon FC",
            "bookmakers": [
                {
                    "key": "pinnacle",
                    "title": "Pinnacle",
                    "last_update": "2026-07-26T11:58:00Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "last_update": "2026-07-26T11:59:00Z",
                            "outcomes": [
                                {"name": "FC Anyang", "price": 2.6},
                                {"name": "Gangwon FC", "price": 2.75},
                                {"name": "Draw", "price": 3.1},
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    response = HttpResponse(
        status_code=200,
        headers={},
        body=json.dumps(payload).encode(),
        received_at=NOW,
    )
    return FixtureHttpTransport([response])


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


def _supplemental_clients() -> tuple[FixtureProviderClient, ...]:
    strength = _envelope(
        "team_strength_form",
        "strength-provider",
        SourceType.PRIMARY_DATA,
        {
            "observed_at": "2026-07-26T11:00:00+00:00",
            "home_team_id": "anyang",
            "away_team_id": "gangwon",
            "home": {"elo_rating": 1540, "points_last_5": 7},
            "away": {"elo_rating": 1620, "points_last_5": 11},
        },
    )
    availability = _envelope(
        "availability_schedule",
        "availability-provider",
        SourceType.OFFICIAL,
        {
            "observed_at": "2026-07-26T10:45:00+00:00",
            "home_team_id": "anyang",
            "away_team_id": "gangwon",
            "home": {"missing_starters": 1, "rest_days": 6},
            "away": {"missing_starters": 1, "rest_days": 6},
        },
    )
    weather = _envelope(
        "weather_lineup",
        "weather-provider",
        SourceType.OFFICIAL,
        {
            "observed_at": "2026-07-26T11:15:00+00:00",
            "home_team_id": "anyang",
            "away_team_id": "gangwon",
            "weather": {"temperature_c": 24.0},
            "home": {"formation": "4-3-3"},
            "away": {"formation": "4-2-3-1"},
        },
    )
    return (
        FixtureProviderClient("strength", (strength,)),
        FixtureProviderClient("availability", (availability,)),
        FixtureProviderClient("weather", (weather,)),
    )


def _supplemental_adapters():
    return (
        TeamStrengthFormAdapter(),
        AvailabilityScheduleAdapter(),
        WeatherLineupAdapter(),
    )


def test_live_market_data_runs_through_existing_full_production_path() -> None:
    result = run_live_market_prediction_path(
        _request(),
        _supplemental_clients(),
        _supplemental_adapters(),
        collected_at=NOW,
        prism_version="test",
        environment={"THE_ODDS_API_KEY": SECRET},
        transport=_market_transport(),
        session_id="live-production-test",
        created_at=NOW,
    )

    assert result.collection_gate.decision.value == "ready"
    by_key = {item.claim_key: item.value for item in result.observations}
    assert by_key["home_decimal_odds"] == pytest.approx(2.6)
    assert by_key["draw_decimal_odds"] == pytest.approx(3.1)
    assert by_key["away_decimal_odds"] == pytest.approx(2.75)
    assert result.features.values["elo_difference"] == pytest.approx(-80.0)
    assert result.report.scoreline is not None
    assert SECRET not in repr(result)


def test_market_only_live_run_is_rejected_by_existing_collection_gate() -> None:
    with pytest.raises(ValueError, match="team strength baseline inputs are unavailable"):
        run_live_market_prediction_path(
            _request(),
            (),
            (),
            collected_at=NOW,
            prism_version="test",
            environment={"THE_ODDS_API_KEY": SECRET},
            transport=_market_transport(),
            session_id="market-only-rejected",
            created_at=NOW,
        )

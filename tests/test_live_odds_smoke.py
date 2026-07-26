import json
from dataclasses import asdict
from datetime import datetime, timezone

from src.acquisition import ProviderFetchRequest, TheOddsApiV4MarketClient
from src.acquisition.live_smoke import run_live_odds_smoke
from src.connectors import FixtureHttpTransport, HttpResponse, RetryPolicy
from src.intelligence import MatchTarget

NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)
KICKOFF = datetime(2026, 7, 26, 10, 30, tzinfo=timezone.utc)


def _request() -> ProviderFetchRequest:
    return ProviderFetchRequest(
        request_id="live-smoke-test",
        requested_at=NOW,
        target=MatchTarget(
            match_id="anyang-gangwon-test",
            competition="K League 1",
            kickoff=KICKOFF,
            home_team_id="home",
            home_team_name="FC Anyang",
            away_team_id="away",
            away_team_name="Gangwon FC",
        ),
    )


def _response() -> HttpResponse:
    body = json.dumps(
        [
            {
                "id": "provider-event-1",
                "sport_key": "soccer_korea_kleague1",
                "commence_time": "2026-07-26T10:30:00Z",
                "home_team": "FC Anyang",
                "away_team": "Gangwon FC",
                "bookmakers": [
                    {
                        "key": "pinnacle",
                        "last_update": "2026-07-26T09:55:00Z",
                        "markets": [
                            {
                                "key": "h2h",
                                "last_update": "2026-07-26T09:55:00Z",
                                "outcomes": [
                                    {"name": "FC Anyang", "price": 3.2},
                                    {"name": "Draw", "price": 3.1},
                                    {"name": "Gangwon FC", "price": 2.3},
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    ).encode()
    return HttpResponse(status_code=200, headers={}, body=body, received_at=NOW)


def test_live_smoke_returns_secret_free_summary() -> None:
    secret = "super-secret-api-key"
    client = TheOddsApiV4MarketClient(
        api_key=secret,
        sport_key="soccer_korea_kleague1",
        bookmaker_key="pinnacle",
        transport=FixtureHttpTransport([_response()]),
        retry_policy=RetryPolicy(max_attempts=1),
    )

    summary = run_live_odds_smoke(_request(), client)
    serialized = json.dumps(asdict(summary), default=str, sort_keys=True)

    assert summary.home_decimal_odds == 3.2
    assert summary.draw_decimal_odds == 3.1
    assert summary.away_decimal_odds == 2.3
    assert summary.source_id == "the-odds-api:pinnacle"
    assert summary.sport_key == "soccer_korea_kleague1"
    assert summary.bookmaker_key == "pinnacle"
    assert secret not in repr(summary)
    assert secret not in serialized


def test_live_smoke_uses_provider_observation_timestamp() -> None:
    client = TheOddsApiV4MarketClient(
        api_key="secret",
        sport_key="soccer_korea_kleague1",
        bookmaker_key="pinnacle",
        transport=FixtureHttpTransport([_response()]),
        retry_policy=RetryPolicy(max_attempts=1),
    )

    summary = run_live_odds_smoke(_request(), client)

    assert summary.observed_at == "2026-07-26T09:55:00+00:00"
    assert summary.retrieved_at == NOW
    assert summary.home_team == "FC Anyang"
    assert summary.away_team == "Gangwon FC"

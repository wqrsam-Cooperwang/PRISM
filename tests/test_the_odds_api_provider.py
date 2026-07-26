import json
from datetime import datetime, timezone

import pytest

from src.acquisition import ProviderFetchRequest, TheOddsApiV4MarketClient
from src.collection import MarketOdds1X2Adapter, collect_observations
from src.connectors import FixtureHttpTransport, HttpResponse, ProviderSchemaError
from src.intelligence import MatchTarget

NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)
KICKOFF = datetime(2026, 7, 27, 10, 30, tzinfo=timezone.utc)
API_KEY = "super-secret-test-key"


def _target() -> MatchTarget:
    return MatchTarget(
        match_id="anyang-gangwon-20260727",
        competition="K League 1",
        kickoff=KICKOFF,
        home_team_id="anyang",
        home_team_name="FC Anyang",
        away_team_id="gangwon",
        away_team_name="Gangwon FC",
    )


def _request() -> ProviderFetchRequest:
    return ProviderFetchRequest(
        request_id="odds-api-request-001",
        target=_target(),
        requested_at=NOW,
    )


def _payload(
    *,
    home_team: str = "FC Anyang",
    away_team: str = "Gangwon FC",
    commence_time: str = "2026-07-27T10:30:00Z",
    outcomes: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    market_outcomes = outcomes or [
        {"name": "FC Anyang", "price": 2.6},
        {"name": "Gangwon FC", "price": 2.75},
        {"name": "Draw", "price": 3.1},
    ]
    return [
        {
            "id": "provider-event-001",
            "sport_key": "soccer_korea_kleague1",
            "commence_time": commence_time,
            "home_team": home_team,
            "away_team": away_team,
            "bookmakers": [
                {
                    "key": "pinnacle",
                    "title": "Pinnacle",
                    "last_update": "2026-07-26T11:58:00Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "last_update": "2026-07-26T11:59:00Z",
                            "outcomes": market_outcomes,
                        }
                    ],
                }
            ],
        }
    ]


def _response(payload: object) -> HttpResponse:
    return HttpResponse(
        status_code=200,
        headers={},
        body=json.dumps(payload).encode(),
        received_at=NOW,
    )


def _client(payload: object) -> tuple[TheOddsApiV4MarketClient, FixtureHttpTransport]:
    transport = FixtureHttpTransport([_response(payload)])
    client = TheOddsApiV4MarketClient(
        api_key=API_KEY,
        sport_key="soccer_korea_kleague1",
        bookmaker_key="pinnacle",
        transport=transport,
    )
    return client, transport


def test_real_provider_client_emits_standard_market_envelope() -> None:
    client, transport = _client(_payload())

    envelopes = client.fetch(_request())

    assert len(envelopes) == 1
    envelope = envelopes[0]
    assert envelope.adapter_id == "market_odds_1x2"
    assert envelope.source.source_id == "the-odds-api:pinnacle"
    assert envelope.source.source_type.value == "market"
    assert envelope.request_id == "odds-api-request-001"
    assert envelope.retrieved_at == NOW
    assert envelope.payload["observed_at"] == "2026-07-26T11:59:00+00:00"
    assert envelope.payload["home_decimal_odds"] == pytest.approx(2.6)
    assert envelope.payload["draw_decimal_odds"] == pytest.approx(3.1)
    assert envelope.payload["away_decimal_odds"] == pytest.approx(2.75)

    outbound = transport.requests[0]
    assert outbound.query["bookmakers"] == "pinnacle"
    assert outbound.query["markets"] == "h2h"
    assert outbound.query["oddsFormat"] == "decimal"
    assert outbound.query["apiKey"] == API_KEY
    assert API_KEY not in repr(outbound)
    assert API_KEY not in repr(client)


def test_provider_envelope_enters_existing_market_adapter_without_glue() -> None:
    client, _ = _client(_payload())
    envelopes = client.fetch(_request())

    observations = collect_observations(_target(), (MarketOdds1X2Adapter(),), envelopes)

    assert len(observations) == 3
    by_key = {item.claim_key: item.value for item in observations}
    assert by_key == {
        "home_decimal_odds": 2.6,
        "draw_decimal_odds": 3.1,
        "away_decimal_odds": 2.75,
    }


def test_provider_matching_is_case_and_whitespace_normalized_but_not_fuzzy() -> None:
    client, _ = _client(_payload(home_team="  fc ANYANG ", away_team="gangwon fc"))
    assert len(client.fetch(_request())) == 1

    wrong_client, _ = _client(_payload(home_team="Anyang United"))
    with pytest.raises(ProviderSchemaError, match="No provider event matches"):
        wrong_client.fetch(_request())


def test_provider_kickoff_mismatch_fails_closed() -> None:
    client, _ = _client(_payload(commence_time="2026-07-28T10:30:00Z"))

    with pytest.raises(ProviderSchemaError, match="commence_time differs"):
        client.fetch(_request())


def test_missing_draw_or_invalid_price_fails_closed() -> None:
    missing_draw = [
        {"name": "FC Anyang", "price": 2.6},
        {"name": "Gangwon FC", "price": 2.75},
    ]
    client, _ = _client(_payload(outcomes=missing_draw))
    with pytest.raises(ProviderSchemaError, match="home, draw, and away"):
        client.fetch(_request())

    invalid_price = [
        {"name": "FC Anyang", "price": 1.0},
        {"name": "Gangwon FC", "price": 2.75},
        {"name": "Draw", "price": 3.1},
    ]
    bad_client, _ = _client(_payload(outcomes=invalid_price))
    with pytest.raises(ProviderSchemaError, match="greater than 1"):
        bad_client.fetch(_request())


def test_provider_response_must_be_json_array_and_unique_match() -> None:
    client, _ = _client({"not": "an array"})
    with pytest.raises(ProviderSchemaError, match="must be an array"):
        client.fetch(_request())

    duplicated = _payload() + _payload()
    duplicate_client, _ = _client(duplicated)
    with pytest.raises(ProviderSchemaError, match="Multiple provider events"):
        duplicate_client.fetch(_request())

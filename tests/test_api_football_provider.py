import json
from datetime import datetime, timezone

import pytest

from src.acquisition.api_football import ApiFootballTeamStatisticsClient
from src.acquisition.models import ProviderFetchRequest
from src.connectors import FixtureHttpTransport, HttpResponse, ProviderSchemaError
from src.intelligence import MatchTarget

NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)
KICKOFF = datetime(2026, 7, 27, 14, 30, tzinfo=timezone.utc)
API_KEY = "api-football-secret"


def _target() -> MatchTarget:
    return MatchTarget(
        match_id="gais-halmstad-20260727",
        competition="Allsvenskan",
        kickoff=KICKOFF,
        home_team_id="gais",
        home_team_name="GAIS",
        away_team_id="halmstads-bk",
        away_team_name="Halmstads BK",
        season="2026",
    )


def _request() -> ProviderFetchRequest:
    return ProviderFetchRequest(
        request_id="api-football-request-001",
        target=_target(),
        requested_at=NOW,
    )


def _statistics(team_id: int, team_name: str) -> dict[str, object]:
    return {
        "league": {"id": 113, "name": "Allsvenskan", "season": 2026},
        "team": {"id": team_id, "name": team_name},
        "form": "WWDLW",
        "fixtures": {
            "played": {"home": 8, "away": 8, "total": 16},
            "wins": {"home": 5, "away": 3, "total": 8},
            "draws": {"home": 2, "away": 2, "total": 4},
            "loses": {"home": 1, "away": 3, "total": 4},
        },
        "goals": {
            "for": {"total": {"home": 15, "away": 10, "total": 25}},
            "against": {"total": {"home": 7, "away": 12, "total": 19}},
        },
    }


def _response(payload: object) -> HttpResponse:
    return HttpResponse(
        status_code=200,
        headers={},
        body=json.dumps(payload).encode(),
        received_at=NOW,
    )


def _api_payload(statistics: dict[str, object]) -> dict[str, object]:
    return {
        "get": "teams/statistics",
        "parameters": {},
        "errors": [],
        "results": 1,
        "response": statistics,
    }


def _client(
    home_payload: object,
    away_payload: object,
) -> tuple[ApiFootballTeamStatisticsClient, FixtureHttpTransport]:
    transport = FixtureHttpTransport([_response(home_payload), _response(away_payload)])
    return (
        ApiFootballTeamStatisticsClient(
            api_key=API_KEY,
            league_id=113,
            season=2026,
            home_team_id=111,
            away_team_id=222,
            transport=transport,
        ),
        transport,
    )


def test_api_football_client_fetches_two_team_statistics_envelopes() -> None:
    client, transport = _client(
        _api_payload(_statistics(111, "GAIS")),
        _api_payload(_statistics(222, "Halmstads BK")),
    )

    envelopes = client.fetch(_request())

    assert len(envelopes) == 2
    assert envelopes[0].adapter_id == "team_statistics"
    assert envelopes[0].payload["side"] == "home"
    assert envelopes[1].payload["side"] == "away"
    assert envelopes[0].payload["statistics"]["form"] == "WWDLW"
    assert envelopes[0].request_id == "api-football-request-001"

    assert len(transport.requests) == 2
    first = transport.requests[0]
    assert first.headers["x-apisports-key"] == API_KEY
    assert first.query == {
        "league": "113",
        "season": "2026",
        "team": "111",
        "date": "2026-07-27",
    }
    assert API_KEY not in repr(first)
    assert API_KEY not in repr(client)


def test_api_football_provider_errors_fail_closed() -> None:
    client, _ = _client(
        {"errors": {"requests": "rate limit"}, "response": {}},
        _api_payload(_statistics(222, "Halmstads BK")),
    )

    with pytest.raises(ProviderSchemaError, match="provider errors"):
        client.fetch(_request())


def test_api_football_identity_mismatch_fails_closed() -> None:
    wrong = _statistics(999, "Wrong Team")
    client, _ = _client(
        _api_payload(wrong),
        _api_payload(_statistics(222, "Halmstads BK")),
    )

    with pytest.raises(ProviderSchemaError, match="team id"):
        client.fetch(_request())

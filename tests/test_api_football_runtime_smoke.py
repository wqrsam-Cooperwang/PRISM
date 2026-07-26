import json
from datetime import datetime, timezone

import pytest

from src.acquisition import (
    ApiFootballRuntimeConfig,
    ProviderFetchRequest,
    build_api_football_team_statistics_client,
    run_live_team_statistics_smoke,
)
from src.connectors import FixtureHttpTransport, HttpResponse, RetryPolicy
from src.intelligence import MatchTarget

NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)
SECRET = "api-football-secret"


def _environment() -> dict[str, str]:
    return {
        "API_FOOTBALL_KEY": SECRET,
        "PRISM_API_FOOTBALL_LEAGUE_ID": "113",
        "PRISM_API_FOOTBALL_SEASON": "2026",
        "PRISM_API_FOOTBALL_HOME_TEAM_ID": "1001",
        "PRISM_API_FOOTBALL_AWAY_TEAM_ID": "1002",
    }


def _request() -> ProviderFetchRequest:
    target = MatchTarget(
        match_id="allsvenskan-gais-halmstad-20260726",
        competition="Allsvenskan",
        kickoff=datetime(2026, 7, 26, 14, 30, tzinfo=timezone.utc),
        home_team_id="gais",
        home_team_name="GAIS",
        away_team_id="halmstads-bk",
        away_team_name="Halmstads BK",
        season="2026",
    )
    return ProviderFetchRequest(request_id="api-football-smoke-001", target=target, requested_at=NOW)


def _statistics_payload(team_id: int) -> bytes:
    payload = {
        "errors": [],
        "response": {
            "team": {"id": team_id},
            "league": {"id": 113, "season": 2026},
            "form": "WWDLW",
            "fixtures": {
                "played": {"home": 7, "away": 7, "total": 14},
                "wins": {"home": 5, "away": 3, "total": 8},
                "draws": {"home": 1, "away": 2, "total": 3},
                "loses": {"home": 1, "away": 2, "total": 3},
            },
            "goals": {
                "for": {"total": {"home": 15, "away": 11, "total": 26}},
                "against": {"total": {"home": 7, "away": 10, "total": 17}},
            },
        },
    }
    return json.dumps(payload).encode()


def test_runtime_config_reads_secret_and_positive_identifiers() -> None:
    config = ApiFootballRuntimeConfig.from_environment(_environment())

    assert config.league_id == 113
    assert config.season == 2026
    assert config.home_team_id == 1001
    assert config.away_team_id == 1002
    assert SECRET not in repr(config)


def test_runtime_config_fails_closed_for_missing_or_invalid_values() -> None:
    with pytest.raises(RuntimeError, match="API_FOOTBALL_KEY"):
        ApiFootballRuntimeConfig.from_environment({})

    invalid = _environment()
    invalid["PRISM_API_FOOTBALL_LEAGUE_ID"] = "not-an-integer"
    with pytest.raises(RuntimeError, match="must be an integer"):
        ApiFootballRuntimeConfig.from_environment(invalid)


def test_live_smoke_returns_secret_free_two_team_summary() -> None:
    responses = [
        HttpResponse(200, {}, _statistics_payload(1001), NOW),
        HttpResponse(200, {}, _statistics_payload(1002), NOW),
    ]
    transport = FixtureHttpTransport(responses)
    config = ApiFootballRuntimeConfig.from_environment(_environment())
    client = build_api_football_team_statistics_client(
        config,
        transport=transport,
        retry_policy=RetryPolicy(max_attempts=1),
    )

    summary = run_live_team_statistics_smoke(_request(), client)

    assert summary.home_team == "GAIS"
    assert summary.away_team == "Halmstads BK"
    assert summary.home_provider_team_id == 1001
    assert summary.away_provider_team_id == 1002
    assert SECRET not in repr(summary)
    assert SECRET not in repr(transport.requests)

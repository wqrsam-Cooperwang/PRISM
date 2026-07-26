import json
from datetime import datetime, timezone

from src.acquisition import (
    ProviderFetchRequest,
    TheSportsDbEventSearchClient,
    run_live_thesportsdb_smoke,
)
from src.connectors import FixtureHttpTransport, HttpResponse
from src.intelligence import MatchTarget

NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)


def _request() -> ProviderFetchRequest:
    return ProviderFetchRequest(
        request_id="thesportsdb-live-001",
        requested_at=NOW,
        target=MatchTarget(
            match_id="allsvenskan-gais-halmstad-20260726",
            competition="Swedish Allsvenskan",
            kickoff=datetime(2026, 7, 26, 14, 30, tzinfo=timezone.utc),
            home_team_id="gais",
            home_team_name="GAIS",
            away_team_id="halmstad",
            away_team_name="Halmstad",
            season="2026",
        ),
    )


def _transport() -> FixtureHttpTransport:
    body = json.dumps(
        {
            "event": [
                {
                    "idEvent": "2225245",
                    "dateEvent": "2026-07-26",
                    "strHomeTeam": "GAIS",
                    "strAwayTeam": "Halmstad",
                    "strLeague": "Swedish Allsvenskan",
                }
            ]
        }
    ).encode()
    return FixtureHttpTransport([HttpResponse(200, {}, body, NOW)])


def test_event_search_uses_public_free_key_without_exposing_it() -> None:
    transport = _transport()
    client = TheSportsDbEventSearchClient(transport=transport)

    summary = run_live_thesportsdb_smoke(_request(), client)

    assert summary.provider_event_id == "2225245"
    assert summary.home_team == "GAIS"
    assert summary.away_team == "Halmstad"
    assert "123" not in repr(client)
    assert transport.requests[0].query["e"] == "GAIS_vs_Halmstad"
    assert transport.requests[0].query["s"] == "2026"

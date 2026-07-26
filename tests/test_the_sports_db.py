import json
from datetime import datetime, timezone

import pytest

from src.acquisition.models import ProviderFetchRequest
from src.acquisition.the_sports_db import TheSportsDbScheduleClient
from src.connectors import FixtureHttpTransport, HttpResponse, ProviderSchemaError
from src.intelligence import MatchTarget

NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)
SECRET = "test-key"


def _request() -> ProviderFetchRequest:
    return ProviderFetchRequest(
        request_id="sportsdb-001",
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


def _transport(events: list[dict[str, object]]) -> FixtureHttpTransport:
    body = json.dumps({"events": events}).encode()
    return FixtureHttpTransport([HttpResponse(200, {}, body, NOW)])


def test_schedule_client_resolves_target_fixture_without_leaking_key() -> None:
    transport = _transport(
        [
            {
                "idEvent": "2225245",
                "dateEvent": "2026-07-26",
                "strHomeTeam": "GAIS",
                "strAwayTeam": "Halmstad",
                "strLeague": "Swedish Allsvenskan",
                "intHomeScore": None,
                "intAwayScore": None,
            }
        ]
    )
    client = TheSportsDbScheduleClient(
        api_key=SECRET,
        league_id=4347,
        season="2026",
        transport=transport,
    )

    envelopes = client.fetch(_request())

    assert len(envelopes) == 1
    assert envelopes[0].payload["provider_event_id"] == "2225245"
    assert envelopes[0].source.publisher == "TheSportsDB"
    assert SECRET not in repr(client)


def test_schedule_client_fails_closed_when_fixture_is_ambiguous() -> None:
    event = {
        "idEvent": "2225245",
        "dateEvent": "2026-07-26",
        "strHomeTeam": "GAIS",
        "strAwayTeam": "Halmstad",
    }
    client = TheSportsDbScheduleClient(
        api_key=SECRET,
        league_id=4347,
        season="2026",
        transport=_transport([event, dict(event)]),
    )

    with pytest.raises(ProviderSchemaError, match="exactly one"):
        client.fetch(_request())

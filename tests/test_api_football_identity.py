import json
from datetime import datetime, timezone

import pytest

from src.acquisition.api_football_identity import ApiFootballIdentityResolver
from src.connectors import FixtureHttpTransport, HttpResponse, ProviderSchemaError, RetryPolicy

NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)
SECRET = "identity-secret"


def _response(payload: dict[str, object]) -> HttpResponse:
    return HttpResponse(
        status_code=200,
        headers={},
        body=json.dumps(payload).encode(),
        received_at=NOW,
    )


def _resolver(responses: list[HttpResponse]) -> ApiFootballIdentityResolver:
    return ApiFootballIdentityResolver(
        api_key=SECRET,
        transport=FixtureHttpTransport(responses),
        retry_policy=RetryPolicy(max_attempts=1),
    )


def test_identity_resolver_maps_exact_league_and_team_names() -> None:
    resolver = _resolver(
        [
            _response(
                {
                    "errors": [],
                    "response": [{"league": {"id": 113, "name": "Allsvenskan"}}],
                }
            ),
            _response(
                {
                    "errors": [],
                    "response": [
                        {"team": {"id": 1, "name": "GAIS"}},
                        {"team": {"id": 2, "name": "Halmstads BK"}},
                    ],
                }
            ),
        ]
    )

    identity = resolver.resolve(
        competition="Allsvenskan",
        season=2026,
        home_team="GAIS",
        away_team="Halmstads BK",
    )

    assert identity.league_id == 113
    assert identity.home_team_id == 1
    assert identity.away_team_id == 2
    assert SECRET not in repr(resolver)
    assert SECRET not in repr(identity)


def test_identity_resolver_fails_closed_when_team_name_is_not_exact() -> None:
    resolver = _resolver(
        [
            _response(
                {
                    "errors": [],
                    "response": [{"league": {"id": 113, "name": "Allsvenskan"}}],
                }
            ),
            _response(
                {
                    "errors": [],
                    "response": [{"team": {"id": 1, "name": "GAIS"}}],
                }
            ),
        ]
    )

    with pytest.raises(ProviderSchemaError, match="away team resolution"):
        resolver.resolve(
            competition="Allsvenskan",
            season=2026,
            home_team="GAIS",
            away_team="Halmstads BK",
        )

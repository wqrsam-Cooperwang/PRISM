"""API-Football V3 team-statistics provider client."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, cast

from src.acquisition.models import ProviderFetchRequest
from src.collection.models import SourceEnvelope
from src.connectors import (
    HttpRequest,
    HttpTransport,
    ProviderSchemaError,
    RetryPolicy,
    decode_json_object,
    send_with_retry,
)
from src.intelligence.models import SourceRef, SourceType

_BASE_URL = "https://v3.football.api-sports.io/teams/statistics"


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProviderSchemaError(f"{field_name} must be an object")
    return cast(Mapping[str, Any], value)


def _sequence(value: Any, field_name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ProviderSchemaError(f"{field_name} must be an array")
    return cast(Sequence[Any], value)


def _integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProviderSchemaError(f"{field_name} must be an integer")
    return cast(int, value)


def _validate_api_errors(payload: Mapping[str, Any]) -> None:
    errors = payload.get("errors")
    if errors in (None, [], {}):
        return
    raise ProviderSchemaError("API-Football response contains provider errors")


def _response_object(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    _validate_api_errors(payload)
    response = payload.get("response")
    if response is None:
        raise ProviderSchemaError("API-Football response is missing response")
    if isinstance(response, Mapping):
        return cast(Mapping[str, Any], response)
    items = _sequence(response, "response")
    if len(items) != 1:
        raise ProviderSchemaError(
            "API-Football response must contain exactly one team statistics object"
        )
    return _mapping(items[0], "response[0]")


def _validate_identity(
    statistics: Mapping[str, Any],
    *,
    team_id: int,
    league_id: int,
    season: int,
) -> None:
    team = _mapping(statistics.get("team"), "response.team")
    league = _mapping(statistics.get("league"), "response.league")
    if _integer(team.get("id"), "response.team.id") != team_id:
        raise ProviderSchemaError("API-Football team id does not match configured team")
    if _integer(league.get("id"), "response.league.id") != league_id:
        raise ProviderSchemaError("API-Football league id does not match configured league")
    if _integer(league.get("season"), "response.league.season") != season:
        raise ProviderSchemaError("API-Football season does not match configured season")


@dataclass(frozen=True)
class ApiFootballTeamStatisticsClient:
    """Fetch factual pre-match statistics for the target home and away teams."""

    api_key: str = field(repr=False)
    league_id: int
    season: int
    home_team_id: int
    away_team_id: int
    transport: HttpTransport = field(repr=False)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy, repr=False)
    client_id: str = "api-football-team-statistics"

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("api_key must not be blank")
        for name in ("league_id", "season", "home_team_id", "away_team_id"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.home_team_id == self.away_team_id:
            raise ValueError("home_team_id and away_team_id must differ")

    def _fetch_team(
        self,
        request: ProviderFetchRequest,
        *,
        side: str,
        team_id: int,
    ) -> SourceEnvelope:
        outbound = HttpRequest(
            method="GET",
            url=_BASE_URL,
            headers={"x-apisports-key": self.api_key},
            query={
                "league": str(self.league_id),
                "season": str(self.season),
                "team": str(team_id),
                "date": request.target.kickoff.date().isoformat(),
            },
        )
        response = send_with_retry(self.transport, outbound, self.retry_policy)
        payload = decode_json_object(response)
        statistics = _response_object(payload)
        _validate_identity(
            statistics,
            team_id=team_id,
            league_id=self.league_id,
            season=self.season,
        )
        return SourceEnvelope(
            adapter_id="team_statistics",
            source=SourceRef(
                source_id=f"api-football:team-statistics:{team_id}",
                source_type=SourceType.PRIMARY_DATA,
                publisher="API-Football",
            ),
            retrieved_at=response.received_at,
            request_id=request.request_id,
            payload={
                "observed_at": response.received_at.isoformat(),
                "side": side,
                "provider_team_id": team_id,
                "league_id": self.league_id,
                "season": self.season,
                "statistics": dict(statistics),
            },
        )

    def fetch(self, request: ProviderFetchRequest) -> tuple[SourceEnvelope, ...]:
        """Fetch home then away statistics deterministically."""

        home = self._fetch_team(request, side="home", team_id=self.home_team_id)
        away = self._fetch_team(request, side="away", team_id=self.away_team_id)
        return (home, away)

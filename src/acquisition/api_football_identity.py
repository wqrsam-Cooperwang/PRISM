"""Deterministic identity resolution for API-Football V3."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

from src.connectors import (
    HttpRequest,
    HttpTransport,
    ProviderSchemaError,
    RetryPolicy,
    decode_json_object,
    send_with_retry,
)

_LEAGUES_URL = "https://v3.football.api-sports.io/leagues"
_TEAMS_URL = "https://v3.football.api-sports.io/teams"


def _normalize_name(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").split())


def _provider_error_summary(errors: Any) -> str:
    """Return useful provider diagnostics without ever including credentials."""

    if isinstance(errors, dict):
        parts: list[str] = []
        for key, value in sorted(errors.items(), key=lambda item: str(item[0])):
            safe_key = str(key)
            safe_value = str(value)
            if "key" in safe_key.casefold() or "token" in safe_key.casefold():
                safe_value = "<redacted>"
            parts.append(f"{safe_key}: {safe_value}")
        return "; ".join(parts) or "unspecified provider error"
    if isinstance(errors, list):
        return "; ".join(str(item) for item in errors) or "unspecified provider error"
    return str(errors)


def _response_list(payload: dict[str, Any], field_name: str) -> list[dict[str, Any]]:
    errors = payload.get("errors")
    if errors not in (None, [], {}):
        detail = _provider_error_summary(errors)
        raise ProviderSchemaError(f"API-Football identity response error: {detail}")
    response = payload.get("response")
    if not isinstance(response, list):
        raise ProviderSchemaError(f"{field_name} response must be an array")
    items: list[dict[str, Any]] = []
    for item in response:
        if not isinstance(item, dict):
            raise ProviderSchemaError(f"{field_name} response item must be an object")
        items.append(item)
    return items


def _positive_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ProviderSchemaError(f"{field_name} must be a positive integer")
    return cast(int, value)


def _text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProviderSchemaError(f"{field_name} must be non-blank text")
    return value.strip()


@dataclass(frozen=True)
class ApiFootballResolvedIdentity:
    """Resolved stable API-Football identifiers for one match."""

    league_id: int
    league_name: str
    season: int
    home_team_id: int
    home_team_name: str
    away_team_id: int
    away_team_name: str


@dataclass(frozen=True)
class ApiFootballIdentityResolver:
    """Resolve league and team names without exposing the provider secret."""

    api_key: str = field(repr=False)
    transport: HttpTransport = field(repr=False)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy, repr=False)

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("api_key must not be blank")

    def _get(self, url: str, query: dict[str, str]) -> dict[str, Any]:
        response = send_with_retry(
            self.transport,
            HttpRequest(
                method="GET",
                url=url,
                headers={"x-apisports-key": self.api_key},
                query=query,
            ),
            self.retry_policy,
        )
        return dict(decode_json_object(response))

    def _resolve_league(self, competition: str, season: int) -> tuple[int, str]:
        payload = self._get(
            _LEAGUES_URL,
            {"search": competition, "season": str(season)},
        )
        matches: list[tuple[int, str]] = []
        target = _normalize_name(competition)
        for item in _response_list(payload, "leagues"):
            league = item.get("league")
            if not isinstance(league, dict):
                continue
            name = league.get("name")
            if isinstance(name, str) and _normalize_name(name) == target:
                matches.append((_positive_int(league.get("id"), "league.id"), name.strip()))
        if len(matches) != 1:
            raise ProviderSchemaError(
                f"API-Football league resolution expected one exact match, found {len(matches)}"
            )
        return matches[0]

    def _resolve_teams(
        self,
        league_id: int,
        season: int,
        home_team: str,
        away_team: str,
    ) -> tuple[tuple[int, str], tuple[int, str]]:
        payload = self._get(
            _TEAMS_URL,
            {"league": str(league_id), "season": str(season)},
        )
        targets = {
            "home": _normalize_name(home_team),
            "away": _normalize_name(away_team),
        }
        found: dict[str, list[tuple[int, str]]] = {"home": [], "away": []}
        for item in _response_list(payload, "teams"):
            team = item.get("team")
            if not isinstance(team, dict):
                continue
            name = team.get("name")
            if not isinstance(name, str):
                continue
            normalized = _normalize_name(name)
            for side, target in targets.items():
                if normalized == target:
                    found[side].append(
                        (_positive_int(team.get("id"), "team.id"), _text(name, "team.name"))
                    )
        for side in ("home", "away"):
            if len(found[side]) != 1:
                raise ProviderSchemaError(
                    f"API-Football {side} team resolution expected one exact match, "
                    f"found {len(found[side])}"
                )
        return found["home"][0], found["away"][0]

    def resolve(
        self,
        *,
        competition: str,
        season: int,
        home_team: str,
        away_team: str,
    ) -> ApiFootballResolvedIdentity:
        """Resolve provider IDs using exact normalized names and fail closed on ambiguity."""

        if season <= 0:
            raise ValueError("season must be positive")
        league_id, league_name = self._resolve_league(competition, season)
        home, away = self._resolve_teams(league_id, season, home_team, away_team)
        if home[0] == away[0]:
            raise ProviderSchemaError("Resolved home and away teams must differ")
        return ApiFootballResolvedIdentity(
            league_id=league_id,
            league_name=league_name,
            season=season,
            home_team_id=home[0],
            home_team_name=home[1],
            away_team_id=away[0],
            away_team_name=away[1],
        )

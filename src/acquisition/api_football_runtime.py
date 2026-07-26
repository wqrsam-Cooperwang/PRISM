"""Secret-safe runtime configuration for API-Football team statistics."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from src.acquisition.api_football import ApiFootballTeamStatisticsClient
from src.connectors import HttpTransport, RetryPolicy, StdlibHttpTransport


def _required_secret(environment: Mapping[str, str], name: str) -> str:
    value = environment.get(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Required provider secret is missing: {name}")
    return value.strip()


def _positive_integer(environment: Mapping[str, str], name: str) -> int:
    raw = environment.get(name)
    if raw is None or not raw.strip():
        raise RuntimeError(f"Required provider configuration is missing: {name}")
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Provider configuration must be an integer: {name}") from exc
    if value <= 0:
        raise RuntimeError(f"Provider configuration must be positive: {name}")
    return value


@dataclass(frozen=True)
class ApiFootballRuntimeConfig:
    """Validated runtime values for one API-Football pre-match statistics request."""

    api_key: str = field(repr=False)
    league_id: int
    season: int
    home_team_id: int
    away_team_id: int

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> "ApiFootballRuntimeConfig":
        source = os.environ if environment is None else environment
        return cls(
            api_key=_required_secret(source, "API_FOOTBALL_KEY"),
            league_id=_positive_integer(source, "PRISM_API_FOOTBALL_LEAGUE_ID"),
            season=_positive_integer(source, "PRISM_API_FOOTBALL_SEASON"),
            home_team_id=_positive_integer(source, "PRISM_API_FOOTBALL_HOME_TEAM_ID"),
            away_team_id=_positive_integer(source, "PRISM_API_FOOTBALL_AWAY_TEAM_ID"),
        )


def build_api_football_team_statistics_client(
    config: ApiFootballRuntimeConfig,
    *,
    transport: HttpTransport | None = None,
    retry_policy: RetryPolicy | None = None,
) -> ApiFootballTeamStatisticsClient:
    """Build the real API-Football team-statistics client from validated configuration."""

    return ApiFootballTeamStatisticsClient(
        api_key=config.api_key,
        league_id=config.league_id,
        season=config.season,
        home_team_id=config.home_team_id,
        away_team_id=config.away_team_id,
        transport=StdlibHttpTransport() if transport is None else transport,
        retry_policy=RetryPolicy() if retry_policy is None else retry_policy,
    )

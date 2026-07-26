"""Secret-free live API-Football smoke diagnostics for PRISM."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.acquisition.api_football import ApiFootballTeamStatisticsClient
from src.acquisition.models import ProviderFetchRequest
from src.collection.models import SourceEnvelope


@dataclass(frozen=True)
class LiveTeamStatisticsSmokeSummary:
    """Credential-free summary of one two-team statistics acquisition."""

    request_id: str
    match_id: str
    home_team: str
    away_team: str
    league_id: int
    season: int
    home_provider_team_id: int
    away_provider_team_id: int
    home_source_id: str
    away_source_id: str
    home_retrieved_at: datetime
    away_retrieved_at: datetime


def _validate_envelopes(envelopes: tuple[SourceEnvelope, ...]) -> tuple[SourceEnvelope, SourceEnvelope]:
    if len(envelopes) != 2:
        raise RuntimeError("Live team-statistics smoke test expected exactly two envelopes")
    home, away = envelopes
    if home.adapter_id != "team_statistics" or away.adapter_id != "team_statistics":
        raise RuntimeError("Live team-statistics smoke test received unexpected adapter payloads")
    if home.payload.get("side") != "home" or away.payload.get("side") != "away":
        raise RuntimeError("Live team-statistics smoke test received unexpected team sides")
    return home, away


def run_live_team_statistics_smoke(
    request: ProviderFetchRequest,
    client: ApiFootballTeamStatisticsClient,
) -> LiveTeamStatisticsSmokeSummary:
    """Fetch real home/away statistics and return a secret-free diagnostic summary."""

    home, away = _validate_envelopes(client.fetch(request))
    return LiveTeamStatisticsSmokeSummary(
        request_id=request.request_id,
        match_id=request.target.match_id,
        home_team=request.target.home_team_name,
        away_team=request.target.away_team_name,
        league_id=client.league_id,
        season=client.season,
        home_provider_team_id=client.home_team_id,
        away_provider_team_id=client.away_team_id,
        home_source_id=home.source.source_id,
        away_source_id=away.source.source_id,
        home_retrieved_at=home.retrieved_at,
        away_retrieved_at=away.retrieved_at,
    )

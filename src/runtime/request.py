"""Application input models and MatchContext construction for PRISM."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.domain.models import AnalysisSession, MatchContext, MatchInfo, ModelOutput, TeamInfo


@dataclass(frozen=True)
class MatchRequest:
    """Application-level input required to create a fresh PRISM MatchContext."""

    match_id: str
    competition: str
    kickoff: datetime
    home_team_id: str
    home_team_name: str
    away_team_id: str
    away_team_name: str
    model_outputs: tuple[ModelOutput, ...]
    venue: str | None = None
    season: str | None = None
    stage: str | None = None
    home_country: str | None = None
    away_country: str | None = None
    home_elo_rating: float | None = None
    away_elo_rating: float | None = None
    lineups: Mapping[str, Any] = field(default_factory=dict)
    injuries: Mapping[str, Any] = field(default_factory=dict)
    market: Mapping[str, Any] = field(default_factory=dict)
    weather: Mapping[str, Any] = field(default_factory=dict)
    schedule: Mapping[str, Any] = field(default_factory=dict)
    tactical: Mapping[str, Any] = field(default_factory=dict)


def build_match_context(
    request: MatchRequest,
    *,
    prism_version: str,
    session_id: str | None = None,
    created_at: datetime | None = None,
    git_commit: str | None = None,
    data_version: str | None = None,
    rule_version: str | None = None,
    model_version: str | None = None,
    prompt_version: str | None = None,
    operator: str | None = None,
    ai_models: tuple[str, ...] = (),
) -> MatchContext:
    """Convert application input into a validated, immutable MatchContext."""

    session = AnalysisSession(
        session_id=session_id or str(uuid4()),
        created_at=created_at or datetime.now(timezone.utc),
        prism_version=prism_version,
        git_commit=git_commit,
        data_version=data_version,
        rule_version=rule_version,
        model_version=model_version,
        prompt_version=prompt_version,
        operator=operator,
        ai_models=ai_models,
    )
    match = MatchInfo(
        match_id=request.match_id,
        competition=request.competition,
        kickoff=request.kickoff,
        venue=request.venue,
        season=request.season,
        stage=request.stage,
    )
    home_team = TeamInfo(
        request.home_team_id,
        request.home_team_name,
        country=request.home_country,
        elo_rating=request.home_elo_rating,
    )
    away_team = TeamInfo(
        request.away_team_id,
        request.away_team_name,
        country=request.away_country,
        elo_rating=request.away_elo_rating,
    )
    return MatchContext(
        session=session,
        match=match,
        home_team=home_team,
        away_team=away_team,
        lineups=request.lineups,
        injuries=request.injuries,
        market=request.market,
        weather=request.weather,
        schedule=request.schedule,
        tactical=request.tactical,
        model_outputs=request.model_outputs,
    )

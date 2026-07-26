"""Secret-free live TheSportsDB smoke diagnostics for PRISM."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.acquisition.models import ProviderFetchRequest
from src.acquisition.the_sports_db_search import TheSportsDbEventSearchClient
from src.collection.models import SourceEnvelope


@dataclass(frozen=True)
class LiveTheSportsDbSmokeSummary:
    """Safe diagnostic projection of one TheSportsDB event acquisition."""

    request_id: str
    match_id: str
    home_team: str
    away_team: str
    competition: str
    season: str
    provider_event_id: str
    source_id: str
    retrieved_at: datetime


def _single_event(envelopes: tuple[SourceEnvelope, ...]) -> SourceEnvelope:
    if len(envelopes) != 1:
        raise RuntimeError("TheSportsDB live smoke test expected exactly one envelope")
    envelope = envelopes[0]
    if envelope.adapter_id != "thesportsdb_event":
        raise RuntimeError("TheSportsDB live smoke test received unexpected adapter payload")
    return envelope


def run_live_thesportsdb_smoke(
    request: ProviderFetchRequest,
    client: TheSportsDbEventSearchClient,
) -> LiveTheSportsDbSmokeSummary:
    """Fetch one real event and return a credential-free diagnostic summary."""

    envelope = _single_event(client.fetch(request))
    event_id = envelope.payload.get("provider_event_id")
    if not isinstance(event_id, str) or not event_id.strip():
        raise RuntimeError("TheSportsDB live smoke payload is missing provider_event_id")
    season = request.target.season
    if season is None or not str(season).strip():
        raise RuntimeError("TheSportsDB live smoke target is missing season")
    return LiveTheSportsDbSmokeSummary(
        request_id=request.request_id,
        match_id=request.target.match_id,
        home_team=request.target.home_team_name,
        away_team=request.target.away_team_name,
        competition=request.target.competition,
        season=str(season),
        provider_event_id=event_id.strip(),
        source_id=envelope.source.source_id,
        retrieved_at=envelope.retrieved_at,
    )

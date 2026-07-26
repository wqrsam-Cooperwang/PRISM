"""TheSportsDB V1 event-search provider client for PRISM."""

from __future__ import annotations

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

_BASE_URL = "https://www.thesportsdb.com/api/v1/json"


def _normalize(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").split())


def _event_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("event")
    if raw is None:
        raw = payload.get("events")
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ProviderSchemaError("TheSportsDB event search response must be an array")
    result: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ProviderSchemaError("TheSportsDB event search item must be an object")
        result.append(cast(dict[str, Any], item))
    return result


@dataclass(frozen=True)
class TheSportsDbEventSearchClient:
    """Resolve one target fixture by team names and season using TheSportsDB V1."""

    transport: HttpTransport = field(repr=False)
    api_key: str = field(default="123", repr=False)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy, repr=False)
    client_id: str = "thesportsdb-event-search"

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("api_key must not be blank")

    def fetch(self, request: ProviderFetchRequest) -> tuple[SourceEnvelope, ...]:
        season = request.target.season
        if season is None or not str(season).strip():
            raise ValueError("TheSportsDB event search requires target season")
        event_query = f"{request.target.home_team_name}_vs_{request.target.away_team_name}"
        response = send_with_retry(
            self.transport,
            HttpRequest(
                method="GET",
                url=f"{_BASE_URL}/{self.api_key}/searchevents.php",
                query={"e": event_query, "s": str(season)},
            ),
            self.retry_policy,
        )
        payload = dict(decode_json_object(response))
        home = _normalize(request.target.home_team_name)
        away = _normalize(request.target.away_team_name)
        kickoff_date = request.target.kickoff.date().isoformat()
        matches: list[dict[str, Any]] = []
        for event in _event_list(payload):
            event_home = event.get("strHomeTeam")
            event_away = event.get("strAwayTeam")
            event_date = event.get("dateEvent")
            if not isinstance(event_home, str) or not isinstance(event_away, str):
                continue
            if (
                _normalize(event_home) == home
                and _normalize(event_away) == away
                and event_date == kickoff_date
            ):
                matches.append(event)
        if len(matches) != 1:
            raise ProviderSchemaError(
                "TheSportsDB event search expected exactly one target fixture, "
                f"found {len(matches)}"
            )
        event = matches[0]
        event_id = event.get("idEvent")
        if not isinstance(event_id, str) or not event_id.strip():
            raise ProviderSchemaError("TheSportsDB target fixture is missing idEvent")
        return (
            SourceEnvelope(
                adapter_id="thesportsdb_event",
                source=SourceRef(
                    source_id=f"thesportsdb:event:{event_id}",
                    source_type=SourceType.PRIMARY_DATA,
                    publisher="TheSportsDB",
                ),
                retrieved_at=response.received_at,
                request_id=request.request_id,
                payload={
                    "observed_at": response.received_at.isoformat(),
                    "provider_event_id": event_id,
                    "season": str(season),
                    "event": dict(event),
                },
            ),
        )

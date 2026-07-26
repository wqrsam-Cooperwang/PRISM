"""TheSportsDB V1 schedule provider client for PRISM."""

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


def _events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    value = payload.get("events")
    if not isinstance(value, list):
        raise ProviderSchemaError("TheSportsDB events response must be an array")
    result: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ProviderSchemaError("TheSportsDB event must be an object")
        result.append(cast(dict[str, Any], item))
    return result


@dataclass(frozen=True)
class TheSportsDbScheduleClient:
    """Fetch a league season schedule and resolve one target fixture exactly."""

    api_key: str = field(repr=False)
    league_id: int
    season: str
    transport: HttpTransport = field(repr=False)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy, repr=False)
    client_id: str = "thesportsdb-schedule"

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("api_key must not be blank")
        if isinstance(self.league_id, bool) or not isinstance(self.league_id, int):
            raise ValueError("league_id must be an integer")
        if self.league_id <= 0:
            raise ValueError("league_id must be positive")
        if not self.season.strip():
            raise ValueError("season must not be blank")

    def fetch(self, request: ProviderFetchRequest) -> tuple[SourceEnvelope, ...]:
        response = send_with_retry(
            self.transport,
            HttpRequest(
                method="GET",
                url=f"{_BASE_URL}/{self.api_key}/eventsseason.php",
                query={"id": str(self.league_id), "s": self.season},
            ),
            self.retry_policy,
        )
        payload = dict(decode_json_object(response))
        home = _normalize(request.target.home_team_name)
        away = _normalize(request.target.away_team_name)
        kickoff_date = request.target.kickoff.date().isoformat()
        matches: list[dict[str, Any]] = []
        for event in _events(payload):
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
                "TheSportsDB fixture resolution expected exactly one target event, "
                f"found {len(matches)}"
            )
        event = matches[0]
        event_id = event.get("idEvent")
        if not isinstance(event_id, str) or not event_id.strip():
            raise ProviderSchemaError("TheSportsDB target event is missing idEvent")
        return (
            SourceEnvelope(
                adapter_id="thesportsdb_schedule",
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
                    "league_id": self.league_id,
                    "season": self.season,
                    "event": dict(event),
                },
            ),
        )

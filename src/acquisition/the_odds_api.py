"""The Odds API V4 market provider client for PRISM."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite
from typing import Any

from src.acquisition.models import ProviderFetchRequest
from src.collection.models import SourceEnvelope
from src.connectors import (
    HttpDecodeError,
    HttpRequest,
    HttpTransport,
    ProviderSchemaError,
    RetryPolicy,
    StdlibHttpTransport,
    send_with_retry,
)
from src.intelligence.models import SourceRef, SourceType

_API_BASE_URL = "https://api.the-odds-api.com/v4"


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _normalized_team_name(value: str) -> str:
    return " ".join(value.casefold().split())


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProviderSchemaError(f"{field_name} must be an object")
    return value


def _sequence(value: Any, field_name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ProviderSchemaError(f"{field_name} must be an array")
    return value


def _text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProviderSchemaError(f"{field_name} must be a non-empty string")
    return value.strip()


def _decimal_price(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProviderSchemaError(f"{field_name} must be a decimal odds number")
    result = float(value)
    if not isfinite(result) or result <= 1.0:
        raise ProviderSchemaError(f"{field_name} must be finite and greater than 1")
    return result


def _parse_datetime(value: Any, field_name: str) -> datetime:
    text = _text(value, field_name)
    try:
        result = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProviderSchemaError(f"{field_name} must be an ISO-8601 datetime") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ProviderSchemaError(f"{field_name} must be timezone-aware")
    return result


def _decode_event_array(body: bytes) -> Sequence[Any]:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HttpDecodeError("Provider response body must be UTF-8") from exc
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HttpDecodeError("Provider response body must contain valid JSON") from exc
    return _sequence(value, "provider response")


def _event_matches(event: Mapping[str, Any], request: ProviderFetchRequest) -> bool:
    home = _normalized_team_name(_text(event.get("home_team"), "event.home_team"))
    away = _normalized_team_name(_text(event.get("away_team"), "event.away_team"))
    expected_home = _normalized_team_name(request.target.home_team_name)
    expected_away = _normalized_team_name(request.target.away_team_name)
    return home == expected_home and away == expected_away


def _select_event(events: Sequence[Any], request: ProviderFetchRequest) -> Mapping[str, Any]:
    matches: list[Mapping[str, Any]] = []
    for index, raw_event in enumerate(events):
        event = _mapping(raw_event, f"provider response[{index}]")
        if _event_matches(event, request):
            matches.append(event)
    if not matches:
        raise ProviderSchemaError("No provider event matches MatchTarget team identity")
    if len(matches) > 1:
        raise ProviderSchemaError("Multiple provider events match MatchTarget team identity")
    return matches[0]


def _validate_kickoff(
    event: Mapping[str, Any],
    request: ProviderFetchRequest,
    tolerance_seconds: float,
) -> None:
    commence = _parse_datetime(event.get("commence_time"), "event.commence_time")
    delta = abs((commence - request.target.kickoff).total_seconds())
    if delta > tolerance_seconds:
        raise ProviderSchemaError("Provider commence_time differs from MatchTarget kickoff")


def _select_bookmaker(event: Mapping[str, Any], bookmaker_key: str) -> Mapping[str, Any]:
    bookmakers = _sequence(event.get("bookmakers"), "event.bookmakers")
    matches: list[Mapping[str, Any]] = []
    for index, raw_bookmaker in enumerate(bookmakers):
        bookmaker = _mapping(raw_bookmaker, f"event.bookmakers[{index}]")
        if _text(bookmaker.get("key"), "bookmaker.key") == bookmaker_key:
            matches.append(bookmaker)
    if len(matches) != 1:
        raise ProviderSchemaError("Requested bookmaker is missing or duplicated")
    return matches[0]


def _select_h2h_market(bookmaker: Mapping[str, Any]) -> Mapping[str, Any]:
    markets = _sequence(bookmaker.get("markets"), "bookmaker.markets")
    matches: list[Mapping[str, Any]] = []
    for index, raw_market in enumerate(markets):
        market = _mapping(raw_market, f"bookmaker.markets[{index}]")
        if _text(market.get("key"), "market.key") == "h2h":
            matches.append(market)
    if len(matches) != 1:
        raise ProviderSchemaError("Requested bookmaker h2h market is missing or duplicated")
    return matches[0]


def _market_prices(
    market: Mapping[str, Any],
    request: ProviderFetchRequest,
) -> tuple[float, float, float]:
    outcomes = _sequence(market.get("outcomes"), "market.outcomes")
    prices: dict[str, float] = {}
    for index, raw_outcome in enumerate(outcomes):
        outcome = _mapping(raw_outcome, f"market.outcomes[{index}]")
        name = _normalized_team_name(_text(outcome.get("name"), "outcome.name"))
        price = _decimal_price(outcome.get("price"), "outcome.price")
        if name in prices:
            raise ProviderSchemaError("h2h market contains duplicate outcome names")
        prices[name] = price

    home_key = _normalized_team_name(request.target.home_team_name)
    away_key = _normalized_team_name(request.target.away_team_name)
    draw_key = "draw"
    try:
        return prices[home_key], prices[draw_key], prices[away_key]
    except KeyError as exc:
        raise ProviderSchemaError("h2h market must contain home, draw, and away outcomes") from exc


def _observed_at(market: Mapping[str, Any], bookmaker: Mapping[str, Any]) -> str:
    value = market.get("last_update", bookmaker.get("last_update"))
    parsed = _parse_datetime(value, "market.last_update")
    return parsed.isoformat()


@dataclass(frozen=True)
class TheOddsApiV4MarketClient:
    """Fetch one bookmaker's football 1X2 odds from The Odds API V4."""

    api_key: str = field(repr=False)
    sport_key: str
    bookmaker_key: str
    transport: HttpTransport = field(default_factory=StdlibHttpTransport, repr=False)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy, repr=False)
    timeout_seconds: float = 10.0
    kickoff_tolerance_hours: float = 6.0
    client_id: str = "the-odds-api-v4-market"

    def __post_init__(self) -> None:
        object.__setattr__(self, "api_key", _require_text(self.api_key, "api_key"))
        object.__setattr__(self, "sport_key", _require_text(self.sport_key, "sport_key"))
        object.__setattr__(
            self,
            "bookmaker_key",
            _require_text(self.bookmaker_key, "bookmaker_key"),
        )
        object.__setattr__(self, "client_id", _require_text(self.client_id, "client_id"))
        if isinstance(self.kickoff_tolerance_hours, bool) or not isinstance(
            self.kickoff_tolerance_hours, (int, float)
        ):
            raise ValueError("kickoff_tolerance_hours must be a positive number")
        tolerance = float(self.kickoff_tolerance_hours)
        if not isfinite(tolerance) or tolerance <= 0:
            raise ValueError("kickoff_tolerance_hours must be a positive number")
        object.__setattr__(self, "kickoff_tolerance_hours", tolerance)

    def fetch(self, request: ProviderFetchRequest) -> tuple[SourceEnvelope, ...]:
        outbound = HttpRequest(
            method="GET",
            url=f"{_API_BASE_URL}/sports/{self.sport_key}/odds",
            query={
                "apiKey": self.api_key,
                "bookmakers": self.bookmaker_key,
                "markets": "h2h",
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            },
            timeout_seconds=self.timeout_seconds,
        )
        response = send_with_retry(self.transport, outbound, self.retry_policy)
        events = _decode_event_array(response.body)
        event = _select_event(events, request)
        _validate_kickoff(
            event,
            request,
            tolerance_seconds=self.kickoff_tolerance_hours * 60.0 * 60.0,
        )
        bookmaker = _select_bookmaker(event, self.bookmaker_key)
        market = _select_h2h_market(bookmaker)
        home_odds, draw_odds, away_odds = _market_prices(market, request)

        return (
            SourceEnvelope(
                adapter_id="market_odds_1x2",
                source=SourceRef(
                    source_id=f"the-odds-api:{self.bookmaker_key}",
                    source_type=SourceType.MARKET,
                ),
                retrieved_at=response.received_at,
                request_id=request.request_id,
                payload={
                    "observed_at": _observed_at(market, bookmaker),
                    "home_team_id": request.target.home_team_id,
                    "away_team_id": request.target.away_team_id,
                    "home_decimal_odds": home_odds,
                    "draw_decimal_odds": draw_odds,
                    "away_decimal_odds": away_odds,
                },
            ),
        )

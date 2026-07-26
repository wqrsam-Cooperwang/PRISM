"""Secret-free live provider smoke diagnostics for PRISM."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.acquisition.models import ProviderFetchRequest
from src.acquisition.the_odds_api import TheOddsApiV4MarketClient
from src.collection.models import SourceEnvelope


@dataclass(frozen=True)
class LiveOddsSmokeSummary:
    """Safe diagnostic projection of one live market acquisition."""

    request_id: str
    match_id: str
    home_team: str
    away_team: str
    source_id: str
    retrieved_at: datetime
    observed_at: str
    home_decimal_odds: float
    draw_decimal_odds: float
    away_decimal_odds: float
    sport_key: str
    bookmaker_key: str


def _single_market_envelope(envelopes: tuple[SourceEnvelope, ...]) -> SourceEnvelope:
    if len(envelopes) != 1:
        raise RuntimeError("Live odds smoke test expected exactly one source envelope")
    envelope = envelopes[0]
    if envelope.adapter_id != "market_odds_1x2":
        raise RuntimeError("Live odds smoke test received an unexpected adapter payload")
    return envelope


def _payload_text(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"Live odds smoke payload is missing {key}")
    return value.strip()


def _payload_odds(payload: Mapping[str, Any], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"Live odds smoke payload is missing {key}")
    return float(value)


def run_live_odds_smoke(
    request: ProviderFetchRequest,
    client: TheOddsApiV4MarketClient,
) -> LiveOddsSmokeSummary:
    """Fetch one real market payload and return a credential-free diagnostic summary."""

    envelope = _single_market_envelope(client.fetch(request))
    payload = envelope.payload
    return LiveOddsSmokeSummary(
        request_id=request.request_id,
        match_id=request.target.match_id,
        home_team=request.target.home_team_name,
        away_team=request.target.away_team_name,
        source_id=envelope.source.source_id,
        retrieved_at=envelope.retrieved_at,
        observed_at=_payload_text(payload, "observed_at"),
        home_decimal_odds=_payload_odds(payload, "home_decimal_odds"),
        draw_decimal_odds=_payload_odds(payload, "draw_decimal_odds"),
        away_decimal_odds=_payload_odds(payload, "away_decimal_odds"),
        sport_key=client.sport_key,
        bookmaker_key=client.bookmaker_key,
    )

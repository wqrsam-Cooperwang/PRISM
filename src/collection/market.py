"""Provider-neutral adapter for one pre-match 1X2 decimal-odds snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any

from src.collection.models import SourceEnvelope
from src.intelligence.models import IntelligenceCategory, MatchTarget, Observation


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _parse_datetime(value: Any, field_name: str) -> datetime:
    text = _require_text(value, field_name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return parsed


def _decimal_odds(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")
    result = float(value)
    if not isfinite(result) or result <= 1.0:
        raise ValueError(f"{field_name} must be finite and greater than 1.0")
    return result


def _validate_optional_team_identity(
    payload: dict[str, Any],
    field_name: str,
    expected: str,
) -> None:
    if field_name not in payload:
        return
    actual = _require_text(payload[field_name], field_name)
    if actual != expected:
        raise ValueError(f"{field_name} does not match MatchTarget")


@dataclass(frozen=True)
class MarketOdds1X2Adapter:
    """Translate one provider-neutral 1X2 odds snapshot into market observations."""

    adapter_id: str = "market_odds_1x2"

    def adapt(
        self,
        target: MatchTarget,
        envelope: SourceEnvelope,
    ) -> tuple[Observation, ...]:
        if envelope.adapter_id != self.adapter_id:
            raise ValueError("SourceEnvelope adapter_id does not match market odds adapter")

        payload = dict(envelope.payload)
        observed_at = _parse_datetime(payload.get("observed_at"), "observed_at")
        _validate_optional_team_identity(payload, "home_team_id", target.home_team_id)
        _validate_optional_team_identity(payload, "away_team_id", target.away_team_id)

        odds = {
            "home_decimal_odds": _decimal_odds(
                payload.get("home_decimal_odds"), "home_decimal_odds"
            ),
            "draw_decimal_odds": _decimal_odds(
                payload.get("draw_decimal_odds"), "draw_decimal_odds"
            ),
            "away_decimal_odds": _decimal_odds(
                payload.get("away_decimal_odds"), "away_decimal_odds"
            ),
        }
        source_id = envelope.source.source_id
        snapshot = observed_at.isoformat()
        return tuple(
            Observation(
                observation_id=f"{source_id}:{target.match_id}:{snapshot}:{claim_key}",
                category=IntelligenceCategory.MARKET,
                claim_key=claim_key,
                value=value,
                source=envelope.source,
                observed_at=observed_at,
                collected_at=envelope.retrieved_at,
            )
            for claim_key, value in odds.items()
        )

"""Provider-neutral pre-match weather and lineup adapter."""

from __future__ import annotations

from collections.abc import Mapping
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


def _finite_numeric(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a finite numeric value")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{field_name} must be a finite numeric value")
    return result


def _mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be a mapping")
    return value


def _validate_optional_team_id(
    payload: Mapping[str, Any],
    field_name: str,
    expected: str,
) -> None:
    value = payload.get(field_name)
    if value is None:
        return
    if _require_text(value, field_name) != expected:
        raise ValueError(f"{field_name} does not match MatchTarget")


@dataclass(frozen=True)
class WeatherLineupAdapter:
    """Translate weather and lineup facts into existing PRISM observations."""

    adapter_id: str = "weather_lineup"

    def adapt(
        self,
        target: MatchTarget,
        envelope: SourceEnvelope,
    ) -> tuple[Observation, ...]:
        if envelope.adapter_id != self.adapter_id:
            raise ValueError("SourceEnvelope adapter_id does not match weather/lineup adapter")

        payload = envelope.payload
        _validate_optional_team_id(payload, "home_team_id", target.home_team_id)
        _validate_optional_team_id(payload, "away_team_id", target.away_team_id)
        observed_at = _parse_datetime(payload.get("observed_at"), "observed_at")
        weather = _mapping(payload, "weather")
        home = _mapping(payload, "home")
        away = _mapping(payload, "away")

        temperature = _finite_numeric(weather.get("temperature_c"), "weather.temperature_c")
        home_formation = _require_text(home.get("formation"), "home.formation")
        away_formation = _require_text(away.get("formation"), "away.formation")

        rows = (
            (
                "weather-temperature",
                IntelligenceCategory.WEATHER,
                None,
                "temperature_c",
                temperature,
            ),
            (
                "home-lineup",
                IntelligenceCategory.LINEUP,
                "home",
                "formation",
                home_formation,
            ),
            (
                "away-lineup",
                IntelligenceCategory.LINEUP,
                "away",
                "formation",
                away_formation,
            ),
        )
        return tuple(
            Observation(
                observation_id=f"{envelope.source.source_id}:{target.match_id}:{suffix}",
                category=category,
                claim_key=claim_key,
                value=value,
                source=envelope.source,
                observed_at=observed_at,
                collected_at=envelope.retrieved_at,
                subject=subject,
            )
            for suffix, category, subject, claim_key, value in rows
        )

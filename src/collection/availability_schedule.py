"""Provider-neutral pre-match availability and schedule adapter."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
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


def _bounded_int(value: Any, field_name: str, *, minimum: int, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    result: int = value
    if result < minimum or (maximum is not None and result > maximum):
        if maximum is None:
            raise ValueError(f"{field_name} must be at least {minimum}")
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}")
    return result


def _team_payload(payload: Mapping[str, Any], side: str) -> Mapping[str, Any]:
    value = payload.get(side)
    if not isinstance(value, Mapping):
        raise ValueError(f"{side} must be a mapping")
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
class AvailabilityScheduleAdapter:
    """Translate availability and rest facts into existing PRISM observations."""

    adapter_id: str = "availability_schedule"

    def adapt(
        self,
        target: MatchTarget,
        envelope: SourceEnvelope,
    ) -> tuple[Observation, ...]:
        if envelope.adapter_id != self.adapter_id:
            raise ValueError("SourceEnvelope adapter_id does not match availability/schedule adapter")

        payload = envelope.payload
        _validate_optional_team_id(payload, "home_team_id", target.home_team_id)
        _validate_optional_team_id(payload, "away_team_id", target.away_team_id)
        observed_at = _parse_datetime(payload.get("observed_at"), "observed_at")
        home = _team_payload(payload, "home")
        away = _team_payload(payload, "away")

        home_missing = _bounded_int(
            home.get("missing_starters"),
            "home.missing_starters",
            minimum=0,
            maximum=11,
        )
        away_missing = _bounded_int(
            away.get("missing_starters"),
            "away.missing_starters",
            minimum=0,
            maximum=11,
        )
        home_rest = _bounded_int(home.get("rest_days"), "home.rest_days", minimum=0)
        away_rest = _bounded_int(away.get("rest_days"), "away.rest_days", minimum=0)

        rows = (
            (
                "home-availability",
                IntelligenceCategory.AVAILABILITY,
                "home",
                "missing_starters",
                home_missing,
            ),
            (
                "away-availability",
                IntelligenceCategory.AVAILABILITY,
                "away",
                "missing_starters",
                away_missing,
            ),
            ("home-schedule", IntelligenceCategory.SCHEDULE, "home", "rest_days", home_rest),
            ("away-schedule", IntelligenceCategory.SCHEDULE, "away", "rest_days", away_rest),
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

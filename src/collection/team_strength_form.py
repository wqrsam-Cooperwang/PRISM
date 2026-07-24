"""Provider-neutral team strength and recent-form adapter."""

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


def _points_last_5(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer from 0 through 15")
    points: int = value
    if not 0 <= points <= 15:
        raise ValueError(f"{field_name} must be an integer from 0 through 15")
    return points


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
class TeamStrengthFormAdapter:
    """Translate one provider strength/form snapshot into PRISM observations."""

    adapter_id: str = "team_strength_form"

    def adapt(
        self,
        target: MatchTarget,
        envelope: SourceEnvelope,
    ) -> tuple[Observation, ...]:
        if envelope.adapter_id != self.adapter_id:
            raise ValueError("SourceEnvelope adapter_id does not match team strength/form adapter")

        payload = envelope.payload
        _validate_optional_team_id(payload, "home_team_id", target.home_team_id)
        _validate_optional_team_id(payload, "away_team_id", target.away_team_id)
        observed_at = _parse_datetime(payload.get("observed_at"), "observed_at")
        home = _team_payload(payload, "home")
        away = _team_payload(payload, "away")

        home_elo = _finite_numeric(home.get("elo_rating"), "home.elo_rating")
        away_elo = _finite_numeric(away.get("elo_rating"), "away.elo_rating")
        home_points = _points_last_5(home.get("points_last_5"), "home.points_last_5")
        away_points = _points_last_5(away.get("points_last_5"), "away.points_last_5")

        rows = (
            ("home-elo", IntelligenceCategory.TEAM_STRENGTH, "home", "elo_rating", home_elo),
            ("away-elo", IntelligenceCategory.TEAM_STRENGTH, "away", "elo_rating", away_elo),
            (
                "home-form",
                IntelligenceCategory.RECENT_FORM,
                "home",
                "points_last_5",
                home_points,
            ),
            (
                "away-form",
                IntelligenceCategory.RECENT_FORM,
                "away",
                "points_last_5",
                away_points,
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

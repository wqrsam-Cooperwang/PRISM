"""Provider-neutral team statistics adapter for PRISM."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from src.collection.models import SourceEnvelope
from src.intelligence.models import IntelligenceCategory, MatchTarget, Observation


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a mapping")
    return cast(Mapping[str, Any], value)


def _integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return cast(int, value)


def _text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _nested_total(statistics: Mapping[str, Any], section: str, field_name: str) -> int:
    section_value = _mapping(statistics.get(section), f"statistics.{section}")
    return _integer(section_value.get("total"), field_name)


def _recent_points(form: str) -> int:
    normalized = "".join(character for character in form.upper() if character in {"W", "D", "L"})
    if not normalized:
        raise ValueError("statistics.form must contain W, D, or L results")
    last_five = normalized[-5:]
    return sum(3 if result == "W" else 1 if result == "D" else 0 for result in last_five)


def _team_metrics(statistics: Mapping[str, Any]) -> tuple[float, float, int]:
    fixtures = _mapping(statistics.get("fixtures"), "statistics.fixtures")
    played = _nested_total(fixtures, "played", "statistics.fixtures.played.total")
    wins = _nested_total(fixtures, "wins", "statistics.fixtures.wins.total")
    draws = _nested_total(fixtures, "draws", "statistics.fixtures.draws.total")
    losses = _nested_total(fixtures, "loses", "statistics.fixtures.loses.total")
    if played <= 0:
        raise ValueError("statistics.fixtures.played.total must be positive")
    if wins + draws + losses != played:
        raise ValueError("statistics fixture outcomes must sum to fixtures played")

    goals = _mapping(statistics.get("goals"), "statistics.goals")
    goals_for = _mapping(goals.get("for"), "statistics.goals.for")
    goals_against = _mapping(goals.get("against"), "statistics.goals.against")
    scored = _integer(
        _mapping(goals_for.get("total"), "statistics.goals.for.total").get("total"),
        "statistics.goals.for.total.total",
    )
    conceded = _integer(
        _mapping(goals_against.get("total"), "statistics.goals.against.total").get("total"),
        "statistics.goals.against.total.total",
    )

    points_per_game = (3.0 * wins + draws) / played
    goal_difference_per_game = (scored - conceded) / played
    points_last_5 = _recent_points(_text(statistics.get("form"), "statistics.form"))
    return points_per_game, goal_difference_per_game, points_last_5


@dataclass(frozen=True)
class TeamStatisticsAdapter:
    """Translate one API-neutral team-statistics envelope into PRISM observations."""

    adapter_id: str = "team_statistics"

    def adapt(
        self,
        target: MatchTarget,
        envelope: SourceEnvelope,
    ) -> tuple[Observation, ...]:
        if envelope.adapter_id != self.adapter_id:
            raise ValueError("SourceEnvelope adapter_id does not match team statistics adapter")

        payload = envelope.payload
        side = _text(payload.get("side"), "side")
        if side not in {"home", "away"}:
            raise ValueError("side must be home or away")
        statistics = _mapping(payload.get("statistics"), "statistics")
        points_per_game, goal_difference_per_game, points_last_5 = _team_metrics(statistics)

        rows = (
            ("ppg", IntelligenceCategory.TEAM_STRENGTH, "points_per_game", points_per_game),
            (
                "goal-diff-pg",
                IntelligenceCategory.TEAM_STRENGTH,
                "goal_difference_per_game",
                goal_difference_per_game,
            ),
            ("recent-form", IntelligenceCategory.RECENT_FORM, "points_last_5", points_last_5),
        )
        return tuple(
            Observation(
                observation_id=f"{envelope.source.source_id}:{target.match_id}:{suffix}",
                category=category,
                claim_key=claim_key,
                value=value,
                source=envelope.source,
                observed_at=envelope.retrieved_at,
                collected_at=envelope.retrieved_at,
                subject=side,
            )
            for suffix, category, claim_key, value in rows
        )

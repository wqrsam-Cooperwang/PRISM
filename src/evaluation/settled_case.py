"""Evaluate one settled PRISM forward-test case without hindsight mutation."""

from __future__ import annotations

from dataclasses import dataclass

from src.evaluation.scoreline_error import ScorelineError, minimum_scoreline_error
from src.ledger.models import PredictionLedgerSnapshot
from src.ledger.outcomes import MatchOutcome


@dataclass(frozen=True)
class SettledCaseEvaluation:
    """Comparable V2.1 production and V2.2 shadow errors for one match."""

    match_id: str
    production: ScorelineError
    shadow: ScorelineError

    @property
    def shadow_distance_delta(self) -> int:
        """Negative values mean the V2.2 shadow portfolio was closer."""

        return self.shadow.goal_distance - self.production.goal_distance


def evaluate_settled_case(
    snapshot: PredictionLedgerSnapshot,
    outcome: MatchOutcome,
) -> SettledCaseEvaluation:
    """Evaluate frozen production and shadow scorelines against one outcome."""

    if snapshot.match_id != outcome.match_id:
        raise ValueError("snapshot and outcome match_id must match")

    production_scores = _parse_scorelines(
        snapshot.payload["report"]["scoreline"]["recommended_scorelines"]
    )
    shadow_scores = _parse_scorelines(
        snapshot.payload["shadow_predictions"]["v2_2"]["scoreline"][
            "recommended_scorelines"
        ]
    )
    production = minimum_scoreline_error(
        production_scores,
        actual_home=outcome.home_goals,
        actual_away=outcome.away_goals,
    )
    shadow = minimum_scoreline_error(
        shadow_scores,
        actual_home=outcome.home_goals,
        actual_away=outcome.away_goals,
    )
    return SettledCaseEvaluation(
        match_id=snapshot.match_id,
        production=production,
        shadow=shadow,
    )


def _parse_scorelines(values: object) -> tuple[tuple[int, int], ...]:
    if not isinstance(values, list) or not values:
        raise ValueError("recommended_scorelines must be a non-empty list")
    parsed: list[tuple[int, int]] = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError("recommended scoreline must be text")
        parts = value.split("-")
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            raise ValueError(f"invalid recommended scoreline: {value}")
        parsed.append((int(parts[0]), int(parts[1])))
    return tuple(parsed)

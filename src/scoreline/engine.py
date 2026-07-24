"""Governed exact-score prediction from model expected-goal outputs."""

from __future__ import annotations

from math import exp, factorial

from src.domain.models import MatchContext
from src.scoreline.models import ScorelineCandidate, ScorelineOutput


class ScorelineEngine:
    """Generate a transparent exact-score baseline after Decision."""

    name = "scoreline"
    version = "1.0.0"
    max_goals = 10

    def run(self, context: MatchContext) -> ScorelineOutput:
        if context.decision is None:
            raise ValueError("Scoreline Engine requires Decision output")

        eligible = tuple(
            model
            for model in context.model_outputs
            if model.expected_home_goals is not None and model.expected_away_goals is not None
        )
        if not eligible:
            return ScorelineOutput(
                available=False,
                method="independent_poisson_equal_weight_xg",
                rationale=(
                    "Scoreline unavailable because no model supplied both expected-goal values.",
                ),
            )

        home_xg = sum(float(model.expected_home_goals) for model in eligible) / len(eligible)
        away_xg = sum(float(model.expected_away_goals) for model in eligible) / len(eligible)
        home_probs = tuple(self._poisson_probability(home_xg, goals) for goals in range(11))
        away_probs = tuple(self._poisson_probability(away_xg, goals) for goals in range(11))

        candidates = tuple(
            ScorelineCandidate(home_goals, away_goals, home_probs[home_goals] * away_probs[away_goals])
            for home_goals in range(11)
            for away_goals in range(11)
        )
        ranked = tuple(
            sorted(
                candidates,
                key=lambda item: (
                    -item.probability,
                    item.home_goals + item.away_goals,
                    item.home_goals,
                    item.away_goals,
                ),
            )
        )
        grid_mass = sum(item.probability for item in candidates)
        tail_mass = max(0.0, 1.0 - grid_mass)

        return ScorelineOutput(
            available=True,
            method="independent_poisson_equal_weight_xg",
            source_model_ids=tuple(model.model_id for model in eligible),
            expected_home_goals=home_xg,
            expected_away_goals=away_xg,
            top_scorelines=ranked[:3],
            grid_probability_mass=grid_mass,
            tail_mass=tail_mass,
            rationale=(
                "Expected goals are the equal-weight mean of eligible model outputs.",
                "Exact-score probabilities use an independent Poisson baseline over goals 0 through 10.",
            ),
        )

    @staticmethod
    def _poisson_probability(rate: float, goals: int) -> float:
        return exp(-rate) * (rate**goals) / factorial(goals)

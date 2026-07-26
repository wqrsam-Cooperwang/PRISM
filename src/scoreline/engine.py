"""Governed exact-score prediction from model expected-goal outputs."""

from __future__ import annotations

from math import exp, factorial, isfinite

from src.consensus.correlation import assumption_family, family_capped_weights
from src.domain.models import MatchContext, ModelOutput
from src.scoreline.diversity import select_diversified_pair
from src.scoreline.models import ScorelineCandidate, ScorelineOutput


class ScorelineEngine:
    """Generate PRISM Exact Score V2.1 after Decision."""

    name = "scoreline"
    version = "2.1.0"
    max_goals = 10
    scenario_weights = (
        ("balanced", 0.54),
        ("home_scores_first", 0.12),
        ("away_scores_first", 0.12),
        ("early_open", 0.14),
        ("symmetric_tail_floor", 0.08),
    )
    defensive_tail_rate_floor = 0.65

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
                method="scenario_mixture_poisson_v2_1",
                rationale=(
                    "Scoreline unavailable because no model supplied both expected-goal values.",
                ),
            )

        self._validate_expected_goals(eligible)
        xg_weights = family_capped_weights(eligible, use_assumption_family=True)
        base_home_xg = sum(
            float(model.expected_home_goals) * weight
            for model, weight in zip(eligible, xg_weights)
        )
        base_away_xg = sum(
            float(model.expected_away_goals) * weight
            for model, weight in zip(eligible, xg_weights)
        )

        scenarios = self._scenario_rates(base_home_xg, base_away_xg)
        candidate_probabilities = {
            (home_goals, away_goals): 0.0
            for home_goals in range(self.max_goals + 1)
            for away_goals in range(self.max_goals + 1)
        }
        effective_home_xg = 0.0
        effective_away_xg = 0.0
        for name, scenario_weight in self.scenario_weights:
            home_rate, away_rate = scenarios[name]
            effective_home_xg += scenario_weight * home_rate
            effective_away_xg += scenario_weight * away_rate
            home_probs = tuple(
                self._poisson_probability(home_rate, goals)
                for goals in range(self.max_goals + 1)
            )
            away_probs = tuple(
                self._poisson_probability(away_rate, goals)
                for goals in range(self.max_goals + 1)
            )
            for home_goals in range(self.max_goals + 1):
                for away_goals in range(self.max_goals + 1):
                    candidate_probabilities[(home_goals, away_goals)] += (
                        scenario_weight * home_probs[home_goals] * away_probs[away_goals]
                    )

        candidates = tuple(
            ScorelineCandidate(home_goals, away_goals, probability)
            for (home_goals, away_goals), probability in candidate_probabilities.items()
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
        recommended = select_diversified_pair(ranked)
        grid_mass = sum(item.probability for item in candidates)
        tail_mass = max(0.0, 1.0 - grid_mass)
        assumption_summary = ",".join(
            f"{model.model_id}:{assumption_family(model)}:{weight:.6f}"
            for model, weight in zip(eligible, xg_weights)
        )

        return ScorelineOutput(
            available=True,
            method="scenario_mixture_poisson_v2_1",
            source_model_ids=tuple(model.model_id for model in eligible),
            expected_home_goals=effective_home_xg,
            expected_away_goals=effective_away_xg,
            top_scorelines=ranked[:3],
            recommended_scorelines=recommended,
            grid_probability_mass=grid_mass,
            tail_mass=tail_mass,
            rationale=(
                "xG inputs use shared-assumption family caps before scenario generation.",
                f"effective_xg_weights={assumption_summary}",
                "Score probabilities are a deterministic mixture of balanced, first-goal, "
                "early-open, and symmetric-tail scenarios.",
                "The defensive-tail scenario applies a symmetric minimum scoring rate of 0.65.",
                "The two recommendations use a shared-story diversity penalty; raw Top 3 remain audited.",
            ),
        )

    @staticmethod
    def _validate_expected_goals(models: tuple[ModelOutput, ...]) -> None:
        for model in models:
            home_xg = float(model.expected_home_goals)
            away_xg = float(model.expected_away_goals)
            if not isfinite(home_xg) or not isfinite(away_xg) or home_xg < 0.0 or away_xg < 0.0:
                raise ValueError("Scoreline expected-goal inputs must be finite and non-negative")

    def _scenario_rates(self, home_xg: float, away_xg: float) -> dict[str, tuple[float, float]]:
        return {
            "balanced": (home_xg, away_xg),
            "home_scores_first": (home_xg * 0.95, away_xg * 1.20),
            "away_scores_first": (home_xg * 1.20, away_xg * 0.95),
            "early_open": (home_xg * 1.25, away_xg * 1.25),
            "symmetric_tail_floor": (
                max(home_xg, self.defensive_tail_rate_floor),
                max(away_xg, self.defensive_tail_rate_floor),
            ),
        }

    @staticmethod
    def _poisson_probability(rate: float, goals: int) -> float:
        return exp(-rate) * (rate**goals) / factorial(goals)

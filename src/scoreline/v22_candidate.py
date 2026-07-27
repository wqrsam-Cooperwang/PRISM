"""Candidate regime-conditioned scoreline engine for PRISM Exact Score V2.2."""

from __future__ import annotations

from src.consensus import DirectionCalibrationOutput
from src.consensus.correlation import assumption_family, family_capped_weights
from src.domain.models import MatchContext
from src.scoreline.diversity import select_diversified_pair
from src.scoreline.engine import ScorelineEngine
from src.scoreline.models import ScorelineCandidate, ScorelineOutput
from src.scoreline.regime import ScorelineRegimeClassifier
from src.scoreline.regime_policy import scenario_weights_for_regime


class V22CandidateScorelineEngine(ScorelineEngine):
    """Apply V2.1 scenario rates with regime-conditioned mixture weights."""

    version = "2.2.0-candidate1"

    def run_with_direction(
        self,
        context: MatchContext,
        direction: DirectionCalibrationOutput,
    ) -> ScorelineOutput:
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
                method="regime_scenario_mixture_poisson_v2_2_candidate",
                rationale=(
                    "Scoreline unavailable because no model supplied both expected-goal values.",
                ),
            )

        xg_weights = family_capped_weights(eligible, use_assumption_family=True)
        weighted_models = tuple(zip(eligible, xg_weights, strict=True))
        base_home_xg = sum(
            self._expected_goals(model)[0] * weight for model, weight in weighted_models
        )
        base_away_xg = sum(
            self._expected_goals(model)[1] * weight for model, weight in weighted_models
        )
        classification = ScorelineRegimeClassifier().run(
            direction,
            base_home_xg,
            base_away_xg,
        )
        scenario_weights = scenario_weights_for_regime(classification.regime)
        scenarios = self._scenario_rates(base_home_xg, base_away_xg)

        probabilities = {
            (home_goals, away_goals): 0.0
            for home_goals in range(self.max_goals + 1)
            for away_goals in range(self.max_goals + 1)
        }
        effective_home_xg = 0.0
        effective_away_xg = 0.0
        for name, scenario_weight in scenario_weights:
            home_rate, away_rate = scenarios[name]
            effective_home_xg += scenario_weight * home_rate
            effective_away_xg += scenario_weight * away_rate
            home_probs = tuple(
                self._poisson_probability(home_rate, goals) for goals in range(self.max_goals + 1)
            )
            away_probs = tuple(
                self._poisson_probability(away_rate, goals) for goals in range(self.max_goals + 1)
            )
            for home_goals in range(self.max_goals + 1):
                for away_goals in range(self.max_goals + 1):
                    probabilities[(home_goals, away_goals)] += (
                        scenario_weight * home_probs[home_goals] * away_probs[away_goals]
                    )

        candidates = tuple(
            ScorelineCandidate(home_goals, away_goals, probability)
            for (home_goals, away_goals), probability in probabilities.items()
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
        assumption_summary = ",".join(
            f"{model.model_id}:{assumption_family(model)}:{weight:.6f}"
            for model, weight in weighted_models
        )
        scenario_summary = ",".join(
            f"{name}:{weight:.2f}" for name, weight in scenario_weights
        )

        return ScorelineOutput(
            available=True,
            method="regime_scenario_mixture_poisson_v2_2_candidate",
            source_model_ids=tuple(model.model_id for model in eligible),
            expected_home_goals=effective_home_xg,
            expected_away_goals=effective_away_xg,
            top_scorelines=ranked[:3],
            recommended_scorelines=recommended,
            grid_probability_mass=grid_mass,
            tail_mass=max(0.0, 1.0 - grid_mass),
            rationale=(
                f"regime={classification.regime.value}",
                f"scenario_weights={scenario_summary}",
                f"effective_xg_weights={assumption_summary}",
                "Candidate only: production V2.1 remains unchanged pending A/B evidence.",
            ),
        )

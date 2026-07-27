"""Scenario weights for PRISM Exact Score V2.2 candidate regimes."""

from __future__ import annotations

from src.scoreline.regime import ScorelineRegime

ScenarioWeights = tuple[tuple[str, float], ...]


_REGIME_WEIGHTS: dict[ScorelineRegime, ScenarioWeights] = {
    ScorelineRegime.BALANCED_LOW: (("balanced", 0.66), ("home_scores_first", 0.08), ("away_scores_first", 0.08), ("early_open", 0.08), ("symmetric_tail_floor", 0.10)),
    ScorelineRegime.BALANCED_OPEN: (("balanced", 0.42), ("home_scores_first", 0.12), ("away_scores_first", 0.12), ("early_open", 0.26), ("symmetric_tail_floor", 0.08)),
    ScorelineRegime.HOME_CONTROL: (("balanced", 0.56), ("home_scores_first", 0.16), ("away_scores_first", 0.08), ("early_open", 0.10), ("symmetric_tail_floor", 0.10)),
    ScorelineRegime.AWAY_CONTROL: (("balanced", 0.56), ("home_scores_first", 0.08), ("away_scores_first", 0.16), ("early_open", 0.10), ("symmetric_tail_floor", 0.10)),
    ScorelineRegime.HOME_OPEN: (("balanced", 0.38), ("home_scores_first", 0.18), ("away_scores_first", 0.08), ("early_open", 0.28), ("symmetric_tail_floor", 0.08)),
    ScorelineRegime.AWAY_OPEN: (("balanced", 0.38), ("home_scores_first", 0.08), ("away_scores_first", 0.18), ("early_open", 0.28), ("symmetric_tail_floor", 0.08)),
}


def scenario_weights_for_regime(regime: ScorelineRegime) -> ScenarioWeights:
    weights = _REGIME_WEIGHTS[ScorelineRegime(regime)]
    if abs(sum(weight for _, weight in weights) - 1.0) > 1e-12:
        raise ValueError("regime scenario weights must sum to 1")
    return weights

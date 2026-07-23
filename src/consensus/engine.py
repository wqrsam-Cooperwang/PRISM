"""Consensus Engine for PRISM model probability outputs."""

from __future__ import annotations

from dataclasses import replace
from statistics import mean

from src.domain.models import ConsensusOutput, MatchContext, ModelOutput


class ConsensusEngine:
    """Aggregate model probabilities and measure inter-model agreement."""

    name = "consensus"
    version = "1.0.0"

    def run(self, context: MatchContext) -> MatchContext:
        models = context.model_outputs
        if not models:
            raise ValueError("Consensus Engine requires at least one model output")

        model_ids = tuple(model.model_id for model in models)
        if len(model_ids) != len(set(model_ids)):
            raise ValueError("Consensus Engine requires unique model ids")

        home_probability = mean(model.home_probability for model in models)
        draw_probability = mean(model.draw_probability for model in models)
        away_probability = mean(model.away_probability for model in models)

        if len(models) == 1:
            mean_distance = 0.50
            agreement = 0.50
        else:
            distances = _pairwise_distances(models)
            mean_distance = mean(distances)
            agreement = 1.0 - mean_distance

        max_spread = max(
            _spread(model.home_probability for model in models),
            _spread(model.draw_probability for model in models),
            _spread(model.away_probability for model in models),
        )
        leading_outcome, margin = _leading_outcome(
            home_probability,
            draw_probability,
            away_probability,
        )

        output = ConsensusOutput(
            model_count=len(models),
            model_ids=model_ids,
            home_probability=round(home_probability, 6),
            draw_probability=round(draw_probability, 6),
            away_probability=round(away_probability, 6),
            agreement=round(agreement, 6),
            mean_pairwise_distance=round(mean_distance, 6),
            max_spread=round(max_spread, 6),
            leading_outcome=leading_outcome,
            margin=round(margin, 6),
            rationale=(
                f"method=equal_weight_mean",
                f"model_count={len(models)}",
                f"agreement={agreement:.6f}",
                f"max_spread={max_spread:.6f}",
            ),
        )
        return replace(context, consensus=output)


def _pairwise_distances(models: tuple[ModelOutput, ...]) -> tuple[float, ...]:
    distances: list[float] = []
    for index, left in enumerate(models[:-1]):
        for right in models[index + 1 :]:
            distances.append(_probability_distance(left, right))
    return tuple(distances)


def _probability_distance(left: ModelOutput, right: ModelOutput) -> float:
    return (
        abs(left.home_probability - right.home_probability)
        + abs(left.draw_probability - right.draw_probability)
        + abs(left.away_probability - right.away_probability)
    ) / 2.0


def _spread(values) -> float:
    materialized = tuple(values)
    return max(materialized) - min(materialized)


def _leading_outcome(home: float, draw: float, away: float) -> tuple[str, float]:
    ranked = sorted(
        (("home", home), ("draw", draw), ("away", away)),
        key=lambda item: item[1],
        reverse=True,
    )
    if abs(ranked[0][1] - ranked[1][1]) <= 1e-12:
        return "tie", 0.0
    return ranked[0][0], ranked[0][1] - ranked[1][1]

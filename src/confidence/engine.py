"""Confidence Engine for PRISM."""

from __future__ import annotations

from dataclasses import replace
from statistics import mean

from src.domain.models import (
    ConfidenceBand,
    ConfidenceOutput,
    EvidenceGate,
    MatchContext,
    ModelOutput,
)

_GATE_CAPS: dict[EvidenceGate, float] = {
    EvidenceGate.DEEP: 1.0,
    EvidenceGate.STANDARD: 0.84,
    EvidenceGate.LIMITED: 0.64,
    EvidenceGate.REJECTED: 0.34,
}

_CONTEXT_FIELDS = ("lineups", "injuries", "market", "weather", "schedule", "tactical")


class ConfidenceEngine:
    """Attach confidence output to a new MatchContext."""

    name = "confidence"
    version = "1.0.0"

    def run(self, context: MatchContext) -> MatchContext:
        if context.evidence is None:
            raise ValueError("Confidence Engine requires evidence output")

        evidence_score = context.evidence.score / 100.0
        model_score = _model_confidence(context.model_outputs)
        context_score = _context_confidence(context)
        consensus_score = _consensus_confidence(context.model_outputs)

        uncapped = (
            evidence_score * 0.45
            + model_score * 0.20
            + context_score * 0.20
            + consensus_score * 0.15
        )
        cap = _GATE_CAPS[context.evidence.gate]
        overall = round(min(uncapped, cap), 4)

        penalties: tuple[str, ...] = ()
        if overall < uncapped:
            penalties = (f"evidence_gate_cap:{context.evidence.gate.value}:{cap:.2f}",)

        output = ConfidenceOutput(
            evidence=round(evidence_score, 4),
            model=round(model_score, 4),
            context=round(context_score, 4),
            consensus=round(consensus_score, 4),
            overall=overall,
            band=_band_from_score(overall),
            penalties=penalties,
            rationale=(
                f"evidence={evidence_score:.4f}",
                f"model={model_score:.4f}",
                f"context={context_score:.4f}",
                f"consensus={consensus_score:.4f}",
            ),
        )
        return replace(context, confidence=output)


def _model_confidence(models: tuple[ModelOutput, ...]) -> float:
    count = len(models)
    if count == 0:
        return 0.50
    if count == 1:
        return 0.65
    return min(0.95, 0.70 + 0.05 * count)


def _context_confidence(context: MatchContext) -> float:
    available = sum(bool(getattr(context, field_name)) for field_name in _CONTEXT_FIELDS)
    return available / len(_CONTEXT_FIELDS)


def _consensus_confidence(models: tuple[ModelOutput, ...]) -> float:
    if len(models) < 2:
        return 0.50

    distances: list[float] = []
    for index, left in enumerate(models[:-1]):
        for right in models[index + 1 :]:
            distances.append(_probability_distance(left, right))

    return max(0.0, 1.0 - mean(distances))


def _probability_distance(left: ModelOutput, right: ModelOutput) -> float:
    absolute_difference = (
        abs(left.home_probability - right.home_probability)
        + abs(left.draw_probability - right.draw_probability)
        + abs(left.away_probability - right.away_probability)
    )
    return absolute_difference / 2.0


def _band_from_score(score: float) -> ConfidenceBand:
    if score >= 0.85:
        return ConfidenceBand.VERY_HIGH
    if score >= 0.70:
        return ConfidenceBand.HIGH
    if score >= 0.50:
        return ConfidenceBand.MEDIUM
    if score >= 0.35:
        return ConfidenceBand.LOW
    return ConfidenceBand.VERY_LOW

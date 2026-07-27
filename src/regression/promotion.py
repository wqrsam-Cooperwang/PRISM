"""Promotion evidence for the V2.2 shadow candidate."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.regression.shadow_evaluation import (
    ShadowScorelineEvaluation,
    evaluate_governed_v22_shadow,
)


@dataclass(frozen=True)
class V22PromotionEvidence:
    """Fail-closed promotion evidence derived from governed forward testing only."""

    evaluation: ShadowScorelineEvaluation
    minimum_cases: int
    eligible: bool
    reasons: tuple[str, ...]


def build_v22_promotion_evidence(
    prediction_root: Path | str = "data/performance-ledger",
    outcome_root: Path | str = "data/outcome-ledger",
    *,
    minimum_cases: int = 30,
) -> V22PromotionEvidence:
    """Assess whether V2.2 has enough governed evidence to be considered for promotion.

    This gate does not promote a model. It only establishes whether the frozen
    shadow candidate has earned promotion review without degrading dual-score
    exact-hit performance on the governed settled cohort.
    """

    if minimum_cases <= 0:
        raise ValueError("minimum_cases must be positive")

    evaluation = evaluate_governed_v22_shadow(prediction_root, outcome_root)
    reasons: list[str] = []

    if evaluation.case_count < minimum_cases:
        reasons.append(
            f"insufficient governed cases: {evaluation.case_count} < {minimum_cases}"
        )
    if evaluation.shadow_dual_hits < evaluation.production_dual_hits:
        reasons.append("V2.2 shadow dual-score exact hits regress production")
    if evaluation.shadow_primary_hits < evaluation.production_primary_hits:
        reasons.append("V2.2 shadow primary exact hits regress production")

    return V22PromotionEvidence(
        evaluation=evaluation,
        minimum_cases=minimum_cases,
        eligible=not reasons,
        reasons=tuple(reasons),
    )

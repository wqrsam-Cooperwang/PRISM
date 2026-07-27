"""Evidence sufficiency gates for PRISM candidate promotion."""

from __future__ import annotations

from dataclasses import dataclass

from src.evaluation.cohort import CohortEvaluationSummary


@dataclass(frozen=True)
class PromotionEvidenceDecision:
    """Whether a settled forward-test cohort is large enough to judge promotion."""

    eligible: bool
    reason: str


def assess_promotion_evidence(
    summary: CohortEvaluationSummary,
    *,
    minimum_cases: int = 20,
) -> PromotionEvidenceDecision:
    """Fail closed until enough governed forward-test cases have settled."""

    if minimum_cases <= 0:
        raise ValueError("minimum_cases must be positive")
    if summary.case_count < minimum_cases:
        return PromotionEvidenceDecision(
            eligible=False,
            reason=f"insufficient governed cases: {summary.case_count}/{minimum_cases}",
        )
    return PromotionEvidenceDecision(
        eligible=True,
        reason=f"governed case threshold reached: {summary.case_count}/{minimum_cases}",
    )

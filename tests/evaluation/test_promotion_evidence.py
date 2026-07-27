"""Tests for governed promotion evidence sufficiency gates."""

import pytest

from src.evaluation.cohort_summary import CohortEvaluationSummary
from src.evaluation.promotion_evidence import assess_promotion_evidence


def _summary(case_count: int) -> CohortEvaluationSummary:
    return CohortEvaluationSummary(
        case_count=case_count,
        production_mean_distance=2.0,
        shadow_mean_distance=1.8,
        production_exact_hits=1,
        shadow_exact_hits=2,
        shadow_better_cases=6,
        tied_cases=3,
        shadow_worse_cases=1,
    )


def test_promotion_evidence_holds_below_minimum_case_threshold() -> None:
    decision = assess_promotion_evidence(_summary(19), minimum_cases=20)

    assert decision.eligible is False
    assert decision.reason == "insufficient governed cases: 19/20"


def test_promotion_evidence_allows_evaluation_at_threshold() -> None:
    decision = assess_promotion_evidence(_summary(20), minimum_cases=20)

    assert decision.eligible is True
    assert decision.reason == "governed case threshold reached: 20/20"


def test_promotion_evidence_rejects_non_positive_threshold() -> None:
    with pytest.raises(ValueError, match="minimum_cases must be positive"):
        assess_promotion_evidence(_summary(20), minimum_cases=0)

"""Canonical governed V2.2 promotion decision path."""

from __future__ import annotations

from pathlib import Path

from src.regression.governed_dataset import (
    load_governed_ledger_regression_dataset,
    load_governed_settled_ledger_pairs,
)
from src.regression.shadow_outcome import compare_frozen_shadow_outcome, summarize_frozen_shadow
from src.regression.shadow_validation import evaluate_v22_promotion_with_shadow
from src.regression.v22_ab import compare_v21_v22_scoreline_case, summarize_v21_v22_scoreline_ab
from src.regression.v22_promotion import V22PromotionPolicy, V22PromotionResult


def evaluate_governed_v22_promotion(
    prediction_root: Path | str = "data/performance-ledger",
    outcome_root: Path | str = "data/outcome-ledger",
    *,
    policy: V22PromotionPolicy | None = None,
) -> V22PromotionResult:
    """Evaluate V2.2 only from contract-valid, settled formal forward-test evidence.

    The scoreline-layer replay and the frozen full-stack shadow comparison are both
    derived from the same governed prediction/outcome cohort. The existing strict
    promotion policy remains the sole authority for promote/hold/reject decisions.
    """

    pairs = load_governed_settled_ledger_pairs(prediction_root, outcome_root)
    if not pairs:
        effective_policy = policy or V22PromotionPolicy()
        return V22PromotionResult(
            decision="hold",
            scoreline_case_count=0,
            full_stack_case_count=0,
            scoreline_layer_passed=False,
            full_stack_validation_passed=False,
            reasons=(
                "no governed settled forward-test cases are available; "
                f"minimum scoreline cases {effective_policy.minimum_scoreline_case_count}, "
                f"minimum full-stack cases {effective_policy.minimum_full_stack_case_count}",
            ),
        )

    cases = load_governed_ledger_regression_dataset(prediction_root, outcome_root)
    if len(cases) != len(pairs):
        raise ValueError(
            "governed scoreline and full-stack cohorts must have identical case counts"
        )

    scoreline_summary = summarize_v21_v22_scoreline_ab(
        tuple(compare_v21_v22_scoreline_case(case) for case in cases)
    )
    shadow_summary = summarize_frozen_shadow(
        tuple(compare_frozen_shadow_outcome(snapshot, outcome) for snapshot, outcome in pairs)
    )
    if scoreline_summary.case_count != shadow_summary.case_count:
        raise ValueError(
            "governed scoreline and full-stack summaries must cover the same cohort"
        )

    return evaluate_v22_promotion_with_shadow(
        scoreline_summary,
        shadow_summary,
        policy=policy,
    )

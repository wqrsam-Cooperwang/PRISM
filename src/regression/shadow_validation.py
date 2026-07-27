"""Validation rules for accumulated V2.2 full-stack shadow evidence."""

from __future__ import annotations

from src.regression.shadow_outcome import FrozenShadowSummary
from src.regression.v22_ab import V22ScorelineABSummary
from src.regression.v22_promotion import (
    V22PromotionPolicy,
    V22PromotionResult,
    evaluate_v22_promotion,
)


def full_stack_shadow_validation_passed(summary: FrozenShadowSummary) -> bool:
    """Require no measured regression plus at least one material improvement."""

    no_regression = (
        summary.v22_primary_hits >= summary.v21_primary_hits
        and summary.v22_dual_hits >= summary.v21_dual_hits
        and summary.v22_mean_minimum_distance <= summary.v21_mean_minimum_distance + 1e-12
        and summary.v22_shared_story_pairs <= summary.v21_shared_story_pairs
    )
    material_improvement = (
        summary.v22_primary_hits > summary.v21_primary_hits
        or summary.v22_dual_hits > summary.v21_dual_hits
        or summary.v22_mean_minimum_distance < summary.v21_mean_minimum_distance - 1e-12
        or summary.v22_shared_story_pairs < summary.v21_shared_story_pairs
    )
    return no_regression and material_improvement


def evaluate_v22_promotion_with_shadow(
    scoreline_summary: V22ScorelineABSummary,
    shadow_summary: FrozenShadowSummary,
    *,
    policy: V22PromotionPolicy | None = None,
) -> V22PromotionResult:
    """Evaluate promotion using the accumulated frozen full-stack shadow sample."""

    return evaluate_v22_promotion(
        scoreline_summary,
        full_stack_case_count=shadow_summary.case_count,
        full_stack_validation_passed=full_stack_shadow_validation_passed(shadow_summary),
        policy=policy,
    )

"""Validation rules for accumulated V2.2 full-stack shadow evidence."""

from __future__ import annotations

from src.regression.shadow_outcome import FrozenShadowSummary


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

"""Governed promotion policy for PRISM Exact Score V2.2 candidate."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from src.regression.v22_ab import V22ScorelineABSummary

V22_PROMOTION_POLICY_VERSION = "1.0.0"
V22PromotionDecision = Literal["promote", "hold", "reject"]


@dataclass(frozen=True)
class V22PromotionPolicy:
    """Conservative evidence requirements for candidate advancement."""

    minimum_scoreline_case_count: int = 30
    minimum_full_stack_case_count: int = 30
    require_full_stack_validation: bool = True

    def __post_init__(self) -> None:
        if self.minimum_scoreline_case_count <= 0:
            raise ValueError("minimum_scoreline_case_count must be positive")
        if self.minimum_full_stack_case_count <= 0:
            raise ValueError("minimum_full_stack_case_count must be positive")


@dataclass(frozen=True)
class V22PromotionResult:
    """Machine-readable governance decision for V2.2."""

    decision: V22PromotionDecision
    scoreline_case_count: int
    full_stack_case_count: int
    scoreline_layer_passed: bool
    full_stack_validation_passed: bool
    reasons: tuple[str, ...]
    policy_version: str = V22_PROMOTION_POLICY_VERSION

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def evaluate_v22_promotion(
    summary: V22ScorelineABSummary,
    *,
    full_stack_case_count: int = 0,
    full_stack_validation_passed: bool = False,
    policy: V22PromotionPolicy | None = None,
) -> V22PromotionResult:
    """Evaluate V2.2 without allowing small-sample or partial-stack promotion."""

    effective_policy = policy or V22PromotionPolicy()
    if full_stack_case_count < 0:
        raise ValueError("full_stack_case_count must be non-negative")

    regression_reasons: list[str] = []
    if summary.v22_primary_hits < summary.v21_primary_hits:
        regression_reasons.append("primary exact-score hits regressed")
    if summary.v22_dual_hits < summary.v21_dual_hits:
        regression_reasons.append("dual exact-score hits regressed")
    if (
        summary.v22_mean_minimum_distance
        > summary.v21_mean_minimum_distance + 1e-12
    ):
        regression_reasons.append("mean minimum score distance regressed")
    if summary.v22_shared_story_pairs > summary.v21_shared_story_pairs:
        regression_reasons.append("shared-story pair count regressed")

    if regression_reasons:
        return V22PromotionResult(
            decision="reject",
            scoreline_case_count=summary.case_count,
            full_stack_case_count=full_stack_case_count,
            scoreline_layer_passed=False,
            full_stack_validation_passed=full_stack_validation_passed,
            reasons=tuple(regression_reasons),
        )

    material_improvement = (
        summary.v22_primary_hits > summary.v21_primary_hits
        or summary.v22_dual_hits > summary.v21_dual_hits
        or summary.v22_mean_minimum_distance
        < summary.v21_mean_minimum_distance - 1e-12
        or summary.v22_shared_story_pairs < summary.v21_shared_story_pairs
    )
    scoreline_layer_passed = (
        summary.case_count >= effective_policy.minimum_scoreline_case_count
        and material_improvement
    )

    hold_reasons: list[str] = []
    if summary.case_count < effective_policy.minimum_scoreline_case_count:
        hold_reasons.append(
            "scoreline replay case count "
            f"{summary.case_count} is below minimum "
            f"{effective_policy.minimum_scoreline_case_count}"
        )
    elif not material_improvement:
        hold_reasons.append("scoreline layer has no material improvement over V2.1")

    full_stack_ready = (
        full_stack_case_count >= effective_policy.minimum_full_stack_case_count
        and full_stack_validation_passed
    )
    if effective_policy.require_full_stack_validation and not full_stack_ready:
        hold_reasons.append(
            "full-stack Direction Calibration validation is not yet sufficient "
            f"({full_stack_case_count}/{effective_policy.minimum_full_stack_case_count})"
        )

    if hold_reasons:
        return V22PromotionResult(
            decision="hold",
            scoreline_case_count=summary.case_count,
            full_stack_case_count=full_stack_case_count,
            scoreline_layer_passed=scoreline_layer_passed,
            full_stack_validation_passed=full_stack_ready,
            reasons=tuple(hold_reasons),
        )

    return V22PromotionResult(
        decision="promote",
        scoreline_case_count=summary.case_count,
        full_stack_case_count=full_stack_case_count,
        scoreline_layer_passed=True,
        full_stack_validation_passed=True,
        reasons=("V2.2 satisfies scoreline and full-stack promotion requirements",),
    )

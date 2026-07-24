"""Deterministic release governance for historical benchmark comparisons."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal

from src.evaluation.comparison import BenchmarkComparison, MetricComparison

PROMOTION_POLICY_VERSION = "1.0.0"
PromotionDecision = Literal["promote", "hold", "reject"]


@dataclass(frozen=True)
class PromotionPolicy:
    minimum_case_count: int = 100
    required_metrics: tuple[str, ...] = (
        "mean_brier_score",
        "mean_log_loss",
        "top1_accuracy",
    )
    minimum_brier_improvement: float = 0.001


@dataclass(frozen=True)
class PromotionResult:
    decision: PromotionDecision
    case_count: int
    reasons: tuple[str, ...]
    required_metrics: tuple[str, ...]
    brier_improvement: float | None
    policy_version: str = PROMOTION_POLICY_VERSION


def _validate_policy(policy: PromotionPolicy) -> None:
    if policy.minimum_case_count <= 0:
        raise ValueError("minimum_case_count must be positive")
    if not policy.required_metrics:
        raise ValueError("required_metrics must not be empty")
    if len(set(policy.required_metrics)) != len(policy.required_metrics):
        raise ValueError("required_metrics must be unique")
    threshold = float(policy.minimum_brier_improvement)
    if not isfinite(threshold) or threshold < 0.0:
        raise ValueError("minimum_brier_improvement must be finite and non-negative")


def _metrics_by_name(comparison: BenchmarkComparison) -> dict[str, MetricComparison]:
    metrics: dict[str, MetricComparison] = {}
    for metric in comparison.metrics:
        if metric.name in metrics:
            raise ValueError(f"comparison contains duplicate metric: {metric.name}")
        metrics[metric.name] = metric
    return metrics


def evaluate_promotion(
    comparison: BenchmarkComparison,
    policy: PromotionPolicy = PromotionPolicy(),
) -> PromotionResult:
    """Evaluate whether a governed benchmark candidate may replace its baseline."""

    _validate_policy(policy)
    metrics = _metrics_by_name(comparison)
    missing = tuple(name for name in policy.required_metrics if name not in metrics)
    if missing:
        return PromotionResult(
            decision="reject",
            case_count=comparison.case_count,
            reasons=(f"missing required metrics: {', '.join(missing)}",),
            required_metrics=policy.required_metrics,
            brier_improvement=None,
        )

    if comparison.case_count < policy.minimum_case_count:
        return PromotionResult(
            decision="hold",
            case_count=comparison.case_count,
            reasons=(
                f"case count {comparison.case_count} is below minimum {policy.minimum_case_count}",
            ),
            required_metrics=policy.required_metrics,
            brier_improvement=None,
        )

    required = tuple(metrics[name] for name in policy.required_metrics)
    not_comparable = tuple(metric.name for metric in required if metric.status == "not_comparable")
    if not_comparable:
        return PromotionResult(
            decision="hold",
            case_count=comparison.case_count,
            reasons=(f"required metrics not comparable: {', '.join(not_comparable)}",),
            required_metrics=policy.required_metrics,
            brier_improvement=None,
        )

    regressed = tuple(metric.name for metric in required if metric.status == "regressed")
    if regressed:
        return PromotionResult(
            decision="reject",
            case_count=comparison.case_count,
            reasons=(f"required metrics regressed: {', '.join(regressed)}",),
            required_metrics=policy.required_metrics,
            brier_improvement=_brier_improvement(metrics),
        )

    brier_improvement = _brier_improvement(metrics)
    if brier_improvement is None:
        return PromotionResult(
            decision="hold",
            case_count=comparison.case_count,
            reasons=("mean_brier_score is not comparable",),
            required_metrics=policy.required_metrics,
            brier_improvement=None,
        )
    if brier_improvement < policy.minimum_brier_improvement:
        return PromotionResult(
            decision="hold",
            case_count=comparison.case_count,
            reasons=(
                "Brier improvement "
                f"{brier_improvement:.6f} is below minimum "
                f"{policy.minimum_brier_improvement:.6f}",
            ),
            required_metrics=policy.required_metrics,
            brier_improvement=brier_improvement,
        )

    if comparison.overall_verdict != "improved":
        return PromotionResult(
            decision="hold",
            case_count=comparison.case_count,
            reasons=(f"overall benchmark verdict is {comparison.overall_verdict}",),
            required_metrics=policy.required_metrics,
            brier_improvement=brier_improvement,
        )

    return PromotionResult(
        decision="promote",
        case_count=comparison.case_count,
        reasons=("candidate satisfies Benchmark Promotion Gate V1",),
        required_metrics=policy.required_metrics,
        brier_improvement=brier_improvement,
    )


def _brier_improvement(metrics: dict[str, MetricComparison]) -> float | None:
    metric = metrics.get("mean_brier_score")
    if metric is None or metric.baseline_value is None or metric.candidate_value is None:
        return None
    return metric.baseline_value - metric.candidate_value

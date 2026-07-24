import pytest

from src.evaluation import (
    BenchmarkComparison,
    MetricComparison,
    PromotionPolicy,
    evaluate_promotion,
)


def _metric(
    name: str,
    baseline: float | None,
    candidate: float | None,
    direction: str,
    status: str,
) -> MetricComparison:
    delta = None if baseline is None or candidate is None else candidate - baseline
    return MetricComparison(  # type: ignore[arg-type]
        name=name,
        baseline_value=baseline,
        candidate_value=candidate,
        delta=delta,
        direction=direction,
        status=status,
    )


def _comparison(
    *,
    case_count: int = 500,
    brier_candidate: float = 0.510,
    log_status: str = "improved",
    top1_status: str = "improved",
    verdict: str = "improved",
) -> BenchmarkComparison:
    return BenchmarkComparison(  # type: ignore[arg-type]
        case_count=case_count,
        baseline_prism_versions=("3.2.0",),
        baseline_runtime_versions=("1.0.0",),
        baseline_git_commits=("base",),
        candidate_prism_versions=("3.3.0",),
        candidate_runtime_versions=("1.1.0",),
        candidate_git_commits=("candidate",),
        metrics=(
            _metric("mean_brier_score", 0.520, brier_candidate, "lower", "improved"),
            _metric("mean_log_loss", 1.020, 1.000, "lower", log_status),
            _metric("top1_accuracy", 0.530, 0.550, "higher", top1_status),
            _metric("mean_overall_confidence", 0.680, 0.710, "descriptive", "descriptive"),
        ),
        overall_verdict=verdict,
    )


def test_promotes_candidate_that_satisfies_default_policy() -> None:
    result = evaluate_promotion(_comparison())

    assert result.decision == "promote"
    assert result.brier_improvement == pytest.approx(0.01)
    assert result.policy_version == "1.0.0"
    assert result.reasons == ("candidate satisfies Benchmark Promotion Gate V1",)


def test_holds_when_sample_is_too_small() -> None:
    result = evaluate_promotion(_comparison(case_count=99))

    assert result.decision == "hold"
    assert "below minimum 100" in result.reasons[0]


def test_rejects_when_required_metric_regresses() -> None:
    result = evaluate_promotion(_comparison(log_status="regressed"))

    assert result.decision == "reject"
    assert result.reasons == ("required metrics regressed: mean_log_loss",)


def test_holds_when_required_metric_is_not_comparable() -> None:
    result = evaluate_promotion(_comparison(top1_status="not_comparable"))

    assert result.decision == "hold"
    assert result.reasons == ("required metrics not comparable: top1_accuracy",)


def test_holds_when_brier_improvement_is_below_threshold() -> None:
    result = evaluate_promotion(_comparison(brier_candidate=0.5195))

    assert result.decision == "hold"
    assert result.brier_improvement == pytest.approx(0.0005)
    assert "below minimum 0.001000" in result.reasons[0]


def test_holds_when_overall_verdict_is_not_improved() -> None:
    result = evaluate_promotion(_comparison(verdict="tie"))

    assert result.decision == "hold"
    assert result.reasons == ("overall benchmark verdict is tie",)


def test_rejects_missing_required_metric() -> None:
    comparison = _comparison()
    comparison = BenchmarkComparison(
        case_count=comparison.case_count,
        baseline_prism_versions=comparison.baseline_prism_versions,
        baseline_runtime_versions=comparison.baseline_runtime_versions,
        baseline_git_commits=comparison.baseline_git_commits,
        candidate_prism_versions=comparison.candidate_prism_versions,
        candidate_runtime_versions=comparison.candidate_runtime_versions,
        candidate_git_commits=comparison.candidate_git_commits,
        metrics=tuple(metric for metric in comparison.metrics if metric.name != "top1_accuracy"),
        overall_verdict=comparison.overall_verdict,
    )

    result = evaluate_promotion(comparison)

    assert result.decision == "reject"
    assert result.reasons == ("missing required metrics: top1_accuracy",)


def test_validates_policy() -> None:
    with pytest.raises(ValueError, match="minimum_case_count must be positive"):
        evaluate_promotion(_comparison(), PromotionPolicy(minimum_case_count=0))

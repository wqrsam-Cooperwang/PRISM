"""Read-only comparison of frozen PRISM historical benchmark datasets."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite
from typing import Literal

from src.evaluation.dataset import EvaluationRecord
from src.evaluation.importer import load_benchmark

MetricDirection = Literal["higher", "lower", "descriptive"]
MetricStatus = Literal["improved", "regressed", "tie", "not_comparable", "descriptive"]
ComparisonVerdict = Literal["improved", "regressed", "tie"]


@dataclass(frozen=True)
class MetricComparison:
    name: str
    baseline_value: float | None
    candidate_value: float | None
    delta: float | None
    direction: MetricDirection
    status: MetricStatus


@dataclass(frozen=True)
class BenchmarkComparison:
    case_count: int
    baseline_prism_versions: tuple[str, ...]
    baseline_runtime_versions: tuple[str, ...]
    baseline_git_commits: tuple[str, ...]
    candidate_prism_versions: tuple[str, ...]
    candidate_runtime_versions: tuple[str, ...]
    candidate_git_commits: tuple[str, ...]
    metrics: tuple[MetricComparison, ...]
    overall_verdict: ComparisonVerdict


def _index_records(
    records: Iterable[EvaluationRecord],
    *,
    label: str,
) -> dict[str, EvaluationRecord]:
    indexed: dict[str, EvaluationRecord] = {}
    for record in records:
        if record.case_id in indexed:
            raise ValueError(f"{label} dataset contains duplicate case_id: {record.case_id}")
        indexed[record.case_id] = record
    if not indexed:
        raise ValueError(f"{label} dataset must contain at least one record")
    return indexed


def _metric(
    name: str,
    baseline_value: float | None,
    candidate_value: float | None,
    *,
    direction: MetricDirection,
    tolerance: float,
) -> MetricComparison:
    if baseline_value is None or candidate_value is None:
        return MetricComparison(
            name=name,
            baseline_value=baseline_value,
            candidate_value=candidate_value,
            delta=None,
            direction=direction,
            status="not_comparable",
        )

    delta = candidate_value - baseline_value
    if direction == "descriptive":
        status: MetricStatus = "descriptive"
    elif abs(delta) <= tolerance:
        status = "tie"
    elif direction == "higher":
        status = "improved" if delta > 0.0 else "regressed"
    else:
        status = "improved" if delta < 0.0 else "regressed"

    return MetricComparison(
        name=name,
        baseline_value=baseline_value,
        candidate_value=candidate_value,
        delta=delta,
        direction=direction,
        status=status,
    )


def compare_benchmarks(
    baseline_records: Iterable[EvaluationRecord],
    candidate_records: Iterable[EvaluationRecord],
    *,
    tolerance: float = 1e-12,
) -> BenchmarkComparison:
    """Compare two frozen benchmark datasets on exactly the same evaluation cases."""

    tolerance_value = float(tolerance)
    if not isfinite(tolerance_value) or tolerance_value < 0.0:
        raise ValueError("tolerance must be finite and non-negative")

    baseline_by_case = _index_records(baseline_records, label="baseline")
    candidate_by_case = _index_records(candidate_records, label="candidate")
    baseline_cases = set(baseline_by_case)
    candidate_cases = set(candidate_by_case)
    if baseline_cases != candidate_cases:
        missing_from_candidate = tuple(sorted(baseline_cases - candidate_cases))
        extra_in_candidate = tuple(sorted(candidate_cases - baseline_cases))
        raise ValueError(
            "benchmark case_id sets must match: "
            f"missing_from_candidate={missing_from_candidate}, "
            f"extra_in_candidate={extra_in_candidate}"
        )

    baseline = load_benchmark(baseline_by_case.values())
    candidate = load_benchmark(candidate_by_case.values())
    metrics = (
        _metric(
            "mean_brier_score",
            baseline.mean_brier_score,
            candidate.mean_brier_score,
            direction="lower",
            tolerance=tolerance_value,
        ),
        _metric(
            "mean_log_loss",
            baseline.mean_log_loss,
            candidate.mean_log_loss,
            direction="lower",
            tolerance=tolerance_value,
        ),
        _metric(
            "top1_accuracy",
            baseline.top1_accuracy,
            candidate.top1_accuracy,
            direction="higher",
            tolerance=tolerance_value,
        ),
        _metric(
            "scoreline_top3_hit_rate",
            baseline.scoreline_top3_hit_rate,
            candidate.scoreline_top3_hit_rate,
            direction="higher",
            tolerance=tolerance_value,
        ),
        _metric(
            "candidate_accuracy",
            baseline.candidate_accuracy,
            candidate.candidate_accuracy,
            direction="higher",
            tolerance=tolerance_value,
        ),
        _metric(
            "mean_overall_confidence",
            baseline.mean_overall_confidence,
            candidate.mean_overall_confidence,
            direction="descriptive",
            tolerance=tolerance_value,
        ),
    )

    core_statuses = tuple(
        metric.status
        for metric in metrics
        if metric.direction != "descriptive" and metric.status != "not_comparable"
    )
    if "regressed" in core_statuses:
        verdict: ComparisonVerdict = "regressed"
    elif "improved" in core_statuses:
        verdict = "improved"
    else:
        verdict = "tie"

    return BenchmarkComparison(
        case_count=len(baseline_by_case),
        baseline_prism_versions=baseline.prism_versions,
        baseline_runtime_versions=baseline.runtime_versions,
        baseline_git_commits=baseline.git_commits,
        candidate_prism_versions=candidate.prism_versions,
        candidate_runtime_versions=candidate.runtime_versions,
        candidate_git_commits=candidate.git_commits,
        metrics=metrics,
        overall_verdict=verdict,
    )

"""Deterministic projections of governed historical benchmark comparisons."""

from __future__ import annotations

import json
from typing import Any

from src.evaluation.comparison import BenchmarkComparison, MetricComparison

COMPARISON_REPORT_VERSION = "1.0.0"


def _metric_payload(metric: MetricComparison) -> dict[str, Any]:
    return {
        "name": metric.name,
        "baseline_value": metric.baseline_value,
        "candidate_value": metric.candidate_value,
        "delta": metric.delta,
        "direction": metric.direction,
        "status": metric.status,
    }


def comparison_report_payload(comparison: BenchmarkComparison) -> dict[str, Any]:
    """Return the canonical serializable projection of a benchmark comparison."""

    return {
        "comparison_report_version": COMPARISON_REPORT_VERSION,
        "case_count": comparison.case_count,
        "baseline": {
            "prism_versions": list(comparison.baseline_prism_versions),
            "runtime_versions": list(comparison.baseline_runtime_versions),
            "git_commits": list(comparison.baseline_git_commits),
        },
        "candidate": {
            "prism_versions": list(comparison.candidate_prism_versions),
            "runtime_versions": list(comparison.candidate_runtime_versions),
            "git_commits": list(comparison.candidate_git_commits),
        },
        "metrics": [_metric_payload(metric) for metric in comparison.metrics],
        "overall_verdict": comparison.overall_verdict,
    }


def render_comparison_json(comparison: BenchmarkComparison) -> str:
    """Render deterministic machine-readable JSON for a benchmark comparison."""

    return json.dumps(
        comparison_report_payload(comparison),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _versions(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "N/A"


def _number(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.6f}"


def render_comparison_markdown(comparison: BenchmarkComparison) -> str:
    """Render deterministic human-readable Markdown for a benchmark comparison."""

    lines = [
        "# PRISM Historical Benchmark Comparison",
        "",
        f"Report version: `{COMPARISON_REPORT_VERSION}`",
        f"Cases: **{comparison.case_count}**",
        "",
        "## Provenance",
        "",
        "| Side | PRISM version(s) | Runtime version(s) | Git commit(s) |",
        "| --- | --- | --- | --- |",
        (
            "| Baseline | "
            f"{_versions(comparison.baseline_prism_versions)} | "
            f"{_versions(comparison.baseline_runtime_versions)} | "
            f"{_versions(comparison.baseline_git_commits)} |"
        ),
        (
            "| Candidate | "
            f"{_versions(comparison.candidate_prism_versions)} | "
            f"{_versions(comparison.candidate_runtime_versions)} | "
            f"{_versions(comparison.candidate_git_commits)} |"
        ),
        "",
        "## Metrics",
        "",
        "| Metric | Baseline | Candidate | Delta | Direction | Status |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    for metric in comparison.metrics:
        lines.append(
            f"| {metric.name} | {_number(metric.baseline_value)} | "
            f"{_number(metric.candidate_value)} | {_number(metric.delta)} | "
            f"{metric.direction} | {metric.status} |"
        )
    lines.extend(
        [
            "",
            "## Overall verdict",
            "",
            f"**{comparison.overall_verdict.upper()}**",
            "",
        ]
    )
    return "\n".join(lines)

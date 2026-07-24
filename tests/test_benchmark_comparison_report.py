import json

from src.evaluation import (
    BenchmarkComparison,
    MetricComparison,
    comparison_report_payload,
    render_comparison_json,
    render_comparison_markdown,
)


def _comparison() -> BenchmarkComparison:
    return BenchmarkComparison(
        case_count=500,
        baseline_prism_versions=("3.2.0",),
        baseline_runtime_versions=("1.0.0",),
        baseline_git_commits=("base123",),
        candidate_prism_versions=("3.3.0",),
        candidate_runtime_versions=("1.1.0",),
        candidate_git_commits=("cand456",),
        metrics=(
            MetricComparison(
                name="mean_brier_score",
                baseline_value=0.542,
                candidate_value=0.511,
                delta=-0.031,
                direction="lower",
                status="improved",
            ),
            MetricComparison(
                name="scoreline_top3_hit_rate",
                baseline_value=None,
                candidate_value=None,
                delta=None,
                direction="higher",
                status="not_comparable",
            ),
            MetricComparison(
                name="mean_overall_confidence",
                baseline_value=0.68,
                candidate_value=0.701,
                delta=0.021,
                direction="descriptive",
                status="descriptive",
            ),
        ),
        overall_verdict="improved",
    )


def test_comparison_report_payload_preserves_governed_result() -> None:
    payload = comparison_report_payload(_comparison())

    assert payload["comparison_report_version"] == "1.0.0"
    assert payload["case_count"] == 500
    assert payload["baseline"]["prism_versions"] == ["3.2.0"]
    assert payload["candidate"]["git_commits"] == ["cand456"]
    assert payload["metrics"][0]["delta"] == -0.031
    assert payload["metrics"][1]["candidate_value"] is None
    assert payload["metrics"][2]["status"] == "descriptive"
    assert payload["overall_verdict"] == "improved"


def test_comparison_json_is_deterministic_and_machine_readable() -> None:
    first = render_comparison_json(_comparison())
    second = render_comparison_json(_comparison())

    assert first == second
    parsed = json.loads(first)
    assert parsed["overall_verdict"] == "improved"
    assert parsed["metrics"][1]["baseline_value"] is None


def test_comparison_markdown_contains_provenance_metrics_and_verdict() -> None:
    rendered = render_comparison_markdown(_comparison())

    assert "# PRISM Historical Benchmark Comparison" in rendered
    assert "Cases: **500**" in rendered
    assert "| Baseline | 3.2.0 | 1.0.0 | base123 |" in rendered
    assert "| Candidate | 3.3.0 | 1.1.0 | cand456 |" in rendered
    assert "| mean_brier_score | 0.542000 | 0.511000 | -0.031000 | lower | improved |" in rendered
    assert "| scoreline_top3_hit_rate | N/A | N/A | N/A | higher | not_comparable |" in rendered
    assert (
        "| mean_overall_confidence | 0.680000 | 0.701000 | 0.021000 | descriptive | "
        "descriptive |" in rendered
    )
    assert "**IMPROVED**" in rendered

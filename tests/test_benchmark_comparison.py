from dataclasses import replace

import pytest

from src.evaluation import EvaluationRecord, compare_benchmarks


def _record(
    case_id: str,
    *,
    brier_score: float,
    log_loss: float,
    top1_correct: bool,
    scoreline_top3_hit: bool | None,
    candidate_correct: bool | None,
    overall_confidence: float,
    prism_version: str,
    git_commit: str,
) -> EvaluationRecord:
    return EvaluationRecord(
        dataset_schema_version="1.0.0",
        case_id=case_id,
        match_id=f"match-{case_id}",
        competition="Comparison League",
        kickoff="2026-07-25T18:00:00+00:00",
        home_team="Home FC",
        away_team="Away FC",
        actual_home_goals=1,
        actual_away_goals=0,
        actual_outcome="home",
        home_probability=0.60,
        draw_probability=0.22,
        away_probability=0.18,
        leading_outcome="home",
        leading_probability=0.60,
        brier_score=brier_score,
        log_loss=log_loss,
        top1_correct=top1_correct,
        scoreline_top3_hit=scoreline_top3_hit,
        decision_action="candidate",
        selected_market="home",
        candidate_correct=candidate_correct,
        overall_confidence=overall_confidence,
        evidence_gate="deep",
        prism_version=prism_version,
        runtime_version="1.0.0",
        git_commit=git_commit,
        data_version="data-v1",
        rule_version="rules-v1",
        model_version="models-v1",
        prompt_version="prompts-v1",
        session_id=f"session-{case_id}",
    )


def _baseline() -> tuple[EvaluationRecord, ...]:
    return (
        _record(
            "first",
            brier_score=0.40,
            log_loss=0.60,
            top1_correct=True,
            scoreline_top3_hit=True,
            candidate_correct=True,
            overall_confidence=0.70,
            prism_version="3.2.0",
            git_commit="base123",
        ),
        _record(
            "second",
            brier_score=0.60,
            log_loss=0.80,
            top1_correct=False,
            scoreline_top3_hit=False,
            candidate_correct=False,
            overall_confidence=0.60,
            prism_version="3.2.0",
            git_commit="base123",
        ),
    )


def _candidate_improved() -> tuple[EvaluationRecord, ...]:
    return (
        _record(
            "first",
            brier_score=0.30,
            log_loss=0.50,
            top1_correct=True,
            scoreline_top3_hit=True,
            candidate_correct=True,
            overall_confidence=0.80,
            prism_version="3.3.0",
            git_commit="cand456",
        ),
        _record(
            "second",
            brier_score=0.40,
            log_loss=0.60,
            top1_correct=True,
            scoreline_top3_hit=True,
            candidate_correct=True,
            overall_confidence=0.75,
            prism_version="3.3.0",
            git_commit="cand456",
        ),
    )


def test_compare_benchmarks_reports_metric_deltas_and_improvement() -> None:
    comparison = compare_benchmarks(_baseline(), _candidate_improved())

    metrics = {metric.name: metric for metric in comparison.metrics}
    assert comparison.case_count == 2
    assert comparison.overall_verdict == "improved"
    assert metrics["mean_brier_score"].status == "improved"
    assert metrics["mean_brier_score"].delta == pytest.approx(-0.15)
    assert metrics["mean_log_loss"].status == "improved"
    assert metrics["top1_accuracy"].status == "improved"
    assert metrics["scoreline_top3_hit_rate"].status == "improved"
    assert metrics["candidate_accuracy"].status == "improved"
    assert metrics["mean_overall_confidence"].status == "descriptive"
    assert comparison.baseline_prism_versions == ("3.2.0",)
    assert comparison.candidate_prism_versions == ("3.3.0",)
    assert comparison.baseline_git_commits == ("base123",)
    assert comparison.candidate_git_commits == ("cand456",)


def test_any_core_regression_makes_overall_verdict_regressed() -> None:
    candidate = tuple(
        replace(record, brier_score=record.brier_score + 0.20)
        for record in _candidate_improved()
    )

    comparison = compare_benchmarks(_baseline(), candidate)
    metrics = {metric.name: metric for metric in comparison.metrics}

    assert metrics["mean_brier_score"].status == "regressed"
    assert metrics["top1_accuracy"].status == "improved"
    assert comparison.overall_verdict == "regressed"


def test_tolerance_prevents_meaningless_float_differences_from_winning() -> None:
    candidate = tuple(
        replace(
            record,
            brier_score=record.brier_score - 1e-9,
            log_loss=record.log_loss - 1e-9,
            prism_version="3.2.1",
            git_commit="tiny789",
        )
        for record in _baseline()
    )

    comparison = compare_benchmarks(_baseline(), candidate, tolerance=1e-6)
    comparable = tuple(
        metric for metric in comparison.metrics if metric.direction != "descriptive"
    )

    assert all(metric.status == "tie" for metric in comparable)
    assert comparison.overall_verdict == "tie"


def test_optional_metrics_are_not_comparable_when_one_dataset_has_no_values() -> None:
    candidate = tuple(
        replace(
            record,
            scoreline_top3_hit=None,
            candidate_correct=None,
            prism_version="3.3.0",
            git_commit="cand456",
        )
        for record in _candidate_improved()
    )

    comparison = compare_benchmarks(_baseline(), candidate)
    metrics = {metric.name: metric for metric in comparison.metrics}

    assert metrics["scoreline_top3_hit_rate"].status == "not_comparable"
    assert metrics["candidate_accuracy"].status == "not_comparable"


def test_compare_benchmarks_rejects_mismatched_case_sets() -> None:
    candidate = (_candidate_improved()[0],)

    with pytest.raises(ValueError, match="case_id sets must match"):
        compare_benchmarks(_baseline(), candidate)


def test_compare_benchmarks_rejects_duplicate_case_ids() -> None:
    duplicate = (_baseline()[0], _baseline()[0])

    with pytest.raises(ValueError, match="duplicate case_id"):
        compare_benchmarks(duplicate, _candidate_improved())


def test_compare_benchmarks_rejects_invalid_tolerance() -> None:
    with pytest.raises(ValueError, match="finite and non-negative"):
        compare_benchmarks(_baseline(), _candidate_improved(), tolerance=-1.0)

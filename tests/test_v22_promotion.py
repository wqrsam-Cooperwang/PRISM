from pathlib import Path

from src.regression import (
    V22PromotionPolicy,
    V22ScorelineABSummary,
    compare_v21_v22_scoreline_case,
    evaluate_v22_promotion,
    load_scoreline_regression_dataset,
    render_v22_ab_json,
    render_v22_ab_markdown,
    summarize_v21_v22_scoreline_ab,
)

DATASET = Path("data/regression/legacy-airtable-2026-07.json")


def _summary(
    *,
    case_count: int = 30,
    v22_dual_hits: int = 8,
) -> V22ScorelineABSummary:
    return V22ScorelineABSummary(
        case_count=case_count,
        v21_primary_hits=4,
        v22_primary_hits=4,
        v21_dual_hits=7,
        v22_dual_hits=v22_dual_hits,
        v21_mean_minimum_distance=1.1,
        v22_mean_minimum_distance=1.0,
        v21_shared_story_pairs=8,
        v22_shared_story_pairs=7,
        v22_distance_improved_cases=8,
        v22_distance_worsened_cases=4,
        distance_tied_cases=18,
    )


def test_current_legacy_cohort_is_governed_hold_not_promotion() -> None:
    cases = load_scoreline_regression_dataset(DATASET)
    comparisons = tuple(compare_v21_v22_scoreline_case(case) for case in cases)
    summary = summarize_v21_v22_scoreline_ab(comparisons)

    result = evaluate_v22_promotion(summary)

    assert result.decision == "hold"
    assert result.scoreline_layer_passed is False
    assert result.full_stack_validation_passed is False
    assert any("12 is below minimum 30" in reason for reason in result.reasons)
    assert any("Direction Calibration" in reason for reason in result.reasons)


def test_promotion_requires_both_scoreline_and_full_stack_evidence() -> None:
    summary = _summary()

    held = evaluate_v22_promotion(summary, full_stack_case_count=30)
    promoted = evaluate_v22_promotion(
        summary,
        full_stack_case_count=30,
        full_stack_validation_passed=True,
    )

    assert held.decision == "hold"
    assert held.scoreline_layer_passed is True
    assert promoted.decision == "promote"
    assert promoted.full_stack_validation_passed is True


def test_material_regression_rejects_candidate() -> None:
    result = evaluate_v22_promotion(
        _summary(v22_dual_hits=6),
        full_stack_case_count=30,
        full_stack_validation_passed=True,
    )

    assert result.decision == "reject"
    assert "dual exact-score hits regressed" in result.reasons


def test_report_serializes_governed_hold() -> None:
    summary = _summary(case_count=12)
    result = evaluate_v22_promotion(
        summary,
        policy=V22PromotionPolicy(minimum_scoreline_case_count=30),
    )

    json_report = render_v22_ab_json(summary, result)
    markdown_report = render_v22_ab_markdown(summary, result)

    assert '"decision": "hold"' in json_report
    assert '"report_version": "1.0.0"' in json_report
    assert "**HOLD**" in markdown_report
    assert "Primary exact hits" in markdown_report

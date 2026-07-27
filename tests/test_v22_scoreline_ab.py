from pathlib import Path

import pytest

from src.regression import (
    compare_v21_v22_scoreline_case,
    load_scoreline_regression_dataset,
    summarize_v21_v22_scoreline_ab,
)

DATASET = Path("data/regression/legacy-airtable-2026-07.json")


def test_v22_scoreline_ab_uses_only_replayable_legacy_xg() -> None:
    cases = load_scoreline_regression_dataset(DATASET)
    comparisons = tuple(compare_v21_v22_scoreline_case(case) for case in cases)
    summary = summarize_v21_v22_scoreline_ab(comparisons)

    assert summary.case_count == 12
    assert summary.v21_primary_hits == 0
    assert summary.v22_primary_hits == 0
    assert summary.v21_dual_hits == 1
    assert summary.v22_dual_hits == 2
    assert summary.v21_mean_minimum_distance == pytest.approx(13 / 12)
    assert summary.v22_mean_minimum_distance == pytest.approx(1.0)
    assert summary.v21_shared_story_pairs == 2
    assert summary.v22_shared_story_pairs == 2
    assert summary.v22_distance_improved_cases == 1
    assert summary.v22_distance_worsened_cases == 0
    assert summary.distance_tied_cases == 11


def test_v22_scoreline_ab_marks_direction_as_xg_derived_not_calibration() -> None:
    case = load_scoreline_regression_dataset(DATASET)[0]
    comparison = compare_v21_v22_scoreline_case(case)

    assert comparison.v21.dual_exact_hit is False
    assert comparison.v22.dual_exact_hit is True
    assert comparison.distance_change == -1


def test_v22_scoreline_ab_summary_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="at least one"):
        summarize_v21_v22_scoreline_ab(())

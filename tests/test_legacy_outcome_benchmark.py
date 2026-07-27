from pathlib import Path

import pytest

from src.regression import load_legacy_outcome_cases, summarize_legacy_outcomes

DATASET = Path("data/regression/legacy-outcome-benchmark-2026-07.json")


def test_legacy_outcome_benchmark_is_deterministic() -> None:
    cases = load_legacy_outcome_cases(DATASET)
    summary, metrics = summarize_legacy_outcomes(cases)

    assert len(cases) == 40
    assert len(metrics) == 40
    assert summary.case_count == 40
    assert summary.primary_exact_hits == 10
    assert summary.any_exact_hits == 17
    assert summary.primary_direction_hits == 22
    assert summary.any_direction_hits == 28
    assert summary.mean_minimum_distance == pytest.approx(0.875)
    assert summary.clean_sheet_overconfidence_cases == 1
    assert summary.weak_side_tail_miss_cases == 1
    assert summary.same_result_story_cluster_cases == 13
    assert summary.path_changing_event_cases == 2
    assert summary.mean_absolute_total_goals_error == pytest.approx(0.975)


def test_legacy_outcome_loader_rejects_wrong_scope(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"scope":"scoreline_only","cases":[]}', encoding="utf-8")

    with pytest.raises(ValueError, match="outcome_benchmark"):
        load_legacy_outcome_cases(path)

from pathlib import Path

import pytest

from src.regression import load_scoreline_regression_dataset, run_batch_scoreline_regression

DATASET = Path("data/regression/legacy-airtable-2026-07.json")


def test_expanded_legacy_airtable_cohort_is_replayable_and_deterministic() -> None:
    cases = load_scoreline_regression_dataset(DATASET)
    result = run_batch_scoreline_regression(cases)

    assert len(cases) == 12
    assert result.summary.case_count == 12
    assert result.summary.v1_primary_hits == 2
    assert result.summary.v21_primary_hits == 0
    assert result.summary.v1_dual_hits == 2
    assert result.summary.v21_dual_hits == 1
    assert result.summary.v1_mean_minimum_distance == pytest.approx(13 / 12)
    assert result.summary.v21_mean_minimum_distance == pytest.approx(13 / 12)
    assert result.summary.v1_shared_story_pairs == 4
    assert result.summary.v21_shared_story_pairs == 2
    assert result.summary.v21_distance_improved_cases == 1
    assert result.summary.v21_distance_worsened_cases == 1
    assert result.summary.distance_tied_cases == 10


def test_dataset_loader_rejects_wrong_scope(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"scope":"full_model","cases":[]}', encoding="utf-8")

    with pytest.raises(ValueError, match="scoreline_only"):
        load_scoreline_regression_dataset(path)

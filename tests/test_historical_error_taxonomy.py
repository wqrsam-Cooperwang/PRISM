from pathlib import Path

import pytest

from src.regression import (
    build_historical_error_taxonomy,
    load_legacy_outcome_cases,
    summarize_legacy_outcomes,
)

DATASET = Path("data/regression/legacy-outcome-benchmark-2026-07.json")


def test_40_case_error_taxonomy_is_deterministic() -> None:
    cases = load_legacy_outcome_cases(DATASET)
    _, metrics = summarize_legacy_outcomes(cases)
    taxonomy = build_historical_error_taxonomy(metrics)

    assert taxonomy.case_count == 40
    assert taxonomy.primary_direction_misses == 18
    assert taxonomy.portfolio_direction_misses == 12
    assert taxonomy.underpredicted_total_cases == 18
    assert taxonomy.overpredicted_total_cases == 8
    assert taxonomy.exact_total_cases == 14
    assert taxonomy.same_story_cluster_cases == 13
    assert taxonomy.clean_sheet_overconfidence_cases == 1
    assert taxonomy.path_changing_event_cases == 2
    assert taxonomy.primary_direction_miss_rate == pytest.approx(0.45)
    assert taxonomy.portfolio_direction_miss_rate == pytest.approx(0.30)
    assert taxonomy.underpredicted_total_rate == pytest.approx(0.45)
    assert taxonomy.same_story_cluster_rate == pytest.approx(0.325)


def test_error_taxonomy_rejects_empty_metrics() -> None:
    with pytest.raises(ValueError, match="at least one"):
        build_historical_error_taxonomy(())

from datetime import datetime, timezone

import pytest

from src.ledger import MatchOutcome, PredictionLedgerSnapshot
from src.regression import (
    compare_frozen_shadow_outcome,
    full_stack_shadow_validation_passed,
    summarize_frozen_shadow,
)

NOW = datetime(2026, 7, 27, tzinfo=timezone.utc)


def _score(home: int, away: int, probability: float) -> dict[str, object]:
    return {
        "home_goals": home,
        "away_goals": away,
        "probability": probability,
    }


def _snapshot(*, shadow_status: str = "available") -> PredictionLedgerSnapshot:
    return PredictionLedgerSnapshot(
        prediction_id="pred-shadow-001",
        match_id="match-shadow-001",
        frozen_at=NOW,
        payload={
            "report": {
                "scoreline": {
                    "recommended_scorelines": [
                        _score(1, 0, 0.14),
                        _score(1, 1, 0.12),
                    ]
                }
            },
            "shadow_predictions": {
                "v2_2": {
                    "status": shadow_status,
                    "scoreline": {
                        "recommended_scorelines": [
                            _score(1, 0, 0.13),
                            _score(2, 1, 0.11),
                        ]
                    },
                }
            },
        },
    )


def _outcome() -> MatchOutcome:
    return MatchOutcome(
        match_id="match-shadow-001",
        home_goals=2,
        away_goals=1,
        settled_at=NOW,
    )


def test_frozen_shadow_comparison_uses_only_pre_match_recommendations() -> None:
    comparison = compare_frozen_shadow_outcome(_snapshot(), _outcome())

    assert comparison.v21.dual_exact_hit is False
    assert comparison.v22.dual_exact_hit is True
    assert comparison.distance_change == -1


def test_full_stack_shadow_summary_can_pass_validation() -> None:
    comparison = compare_frozen_shadow_outcome(_snapshot(), _outcome())
    summary = summarize_frozen_shadow((comparison,))

    assert summary.case_count == 1
    assert summary.v22_dual_hits == 1
    assert summary.v22_distance_worsened_cases == 0
    assert full_stack_shadow_validation_passed(summary) is True


def test_unavailable_shadow_is_excluded_from_full_stack_evaluation() -> None:
    with pytest.raises(ValueError, match="not available"):
        compare_frozen_shadow_outcome(_snapshot(shadow_status="unavailable"), _outcome())

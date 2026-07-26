"""Batch historical regression runner and machine-readable summaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.regression.scoreline import (
    ScorelineRegressionCase,
    ScorelineRegressionComparison,
    ScorelineRegressionSummary,
    compare_scoreline_case,
    summarize_scoreline_regression,
)


@dataclass(frozen=True)
class BatchScorelineRegressionResult:
    """Deterministic batch result for historical V1 versus V2.1 comparisons."""

    comparisons: tuple[ScorelineRegressionComparison, ...]
    summary: ScorelineRegressionSummary

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": asdict(self.summary),
            "comparisons": [
                {
                    "case_id": item.case_id,
                    "distance_change": item.distance_change,
                    "v1": {
                        "recommendations": [
                            {
                                "home_goals": candidate.home_goals,
                                "away_goals": candidate.away_goals,
                                "probability": candidate.probability,
                            }
                            for candidate in item.v1.recommendations
                        ],
                        "primary_exact_hit": item.v1.primary_exact_hit,
                        "dual_exact_hit": item.v1.dual_exact_hit,
                        "minimum_manhattan_distance": item.v1.minimum_manhattan_distance,
                        "shared_story_pair": item.v1.shared_story_pair,
                    },
                    "v21": {
                        "recommendations": [
                            {
                                "home_goals": candidate.home_goals,
                                "away_goals": candidate.away_goals,
                                "probability": candidate.probability,
                            }
                            for candidate in item.v21.recommendations
                        ],
                        "primary_exact_hit": item.v21.primary_exact_hit,
                        "dual_exact_hit": item.v21.dual_exact_hit,
                        "minimum_manhattan_distance": item.v21.minimum_manhattan_distance,
                        "shared_story_pair": item.v21.shared_story_pair,
                    },
                }
                for item in self.comparisons
            ],
        }


def run_batch_scoreline_regression(
    cases: tuple[ScorelineRegressionCase, ...],
) -> BatchScorelineRegressionResult:
    """Compare all cases in stable order and aggregate the result."""

    if not cases:
        raise ValueError("batch regression requires at least one historical case")
    comparisons = tuple(compare_scoreline_case(case) for case in cases)
    return BatchScorelineRegressionResult(
        comparisons=comparisons,
        summary=summarize_scoreline_regression(comparisons),
    )

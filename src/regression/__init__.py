"""Historical regression utilities for PRISM."""

from src.regression.batch import BatchScorelineRegressionResult, run_batch_scoreline_regression
from src.regression.dataset import load_scoreline_regression_dataset
from src.regression.importer import regression_case_from_ledgers
from src.regression.outcome_benchmark import (
    LegacyOutcomeCase,
    LegacyOutcomeMetrics,
    LegacyOutcomeSummary,
    evaluate_legacy_outcome_case,
    load_legacy_outcome_cases,
    summarize_legacy_outcomes,
)
from src.regression.scoreline import (
    ScorelineEngineMetrics,
    ScorelineRegressionCase,
    ScorelineRegressionComparison,
    ScorelineRegressionSummary,
    compare_scoreline_case,
    summarize_scoreline_regression,
)

__all__ = [
    "BatchScorelineRegressionResult",
    "LegacyOutcomeCase",
    "LegacyOutcomeMetrics",
    "LegacyOutcomeSummary",
    "ScorelineEngineMetrics",
    "ScorelineRegressionCase",
    "ScorelineRegressionComparison",
    "ScorelineRegressionSummary",
    "compare_scoreline_case",
    "evaluate_legacy_outcome_case",
    "load_legacy_outcome_cases",
    "load_scoreline_regression_dataset",
    "regression_case_from_ledgers",
    "run_batch_scoreline_regression",
    "summarize_legacy_outcomes",
    "summarize_scoreline_regression",
]

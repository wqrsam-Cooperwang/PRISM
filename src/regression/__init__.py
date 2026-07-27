"""Historical regression utilities for PRISM."""

from src.regression.batch import BatchScorelineRegressionResult, run_batch_scoreline_regression
from src.regression.dataset import load_scoreline_regression_dataset
from src.regression.error_taxonomy import HistoricalErrorTaxonomy, build_historical_error_taxonomy
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
from src.regression.v22_ab import (
    V22ScorelineABComparison,
    V22ScorelineABSummary,
    compare_v21_v22_scoreline_case,
    summarize_v21_v22_scoreline_ab,
)

__all__ = [
    "BatchScorelineRegressionResult",
    "HistoricalErrorTaxonomy",
    "LegacyOutcomeCase",
    "LegacyOutcomeMetrics",
    "LegacyOutcomeSummary",
    "ScorelineEngineMetrics",
    "ScorelineRegressionCase",
    "ScorelineRegressionComparison",
    "ScorelineRegressionSummary",
    "V22ScorelineABComparison",
    "V22ScorelineABSummary",
    "build_historical_error_taxonomy",
    "compare_scoreline_case",
    "compare_v21_v22_scoreline_case",
    "evaluate_legacy_outcome_case",
    "load_legacy_outcome_cases",
    "load_scoreline_regression_dataset",
    "regression_case_from_ledgers",
    "run_batch_scoreline_regression",
    "summarize_legacy_outcomes",
    "summarize_scoreline_regression",
    "summarize_v21_v22_scoreline_ab",
]

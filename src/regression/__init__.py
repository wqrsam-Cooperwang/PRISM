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
from src.regression.shadow_outcome import (
    FrozenShadowComparison,
    FrozenShadowSummary,
    compare_frozen_shadow_outcome,
    summarize_frozen_shadow,
)
from src.regression.shadow_validation import full_stack_shadow_validation_passed
from src.regression.v22_ab import (
    V22ScorelineABComparison,
    V22ScorelineABSummary,
    compare_v21_v22_scoreline_case,
    summarize_v21_v22_scoreline_ab,
)
from src.regression.v22_promotion import (
    V22_PROMOTION_POLICY_VERSION,
    V22PromotionPolicy,
    V22PromotionResult,
    evaluate_v22_promotion,
)
from src.regression.v22_report import (
    V22_AB_REPORT_VERSION,
    render_v22_ab_json,
    render_v22_ab_markdown,
    v22_ab_report_payload,
)

__all__ = [
    "BatchScorelineRegressionResult",
    "FrozenShadowComparison",
    "FrozenShadowSummary",
    "HistoricalErrorTaxonomy",
    "LegacyOutcomeCase",
    "LegacyOutcomeMetrics",
    "LegacyOutcomeSummary",
    "ScorelineEngineMetrics",
    "ScorelineRegressionCase",
    "ScorelineRegressionComparison",
    "ScorelineRegressionSummary",
    "V22_AB_REPORT_VERSION",
    "V22_PROMOTION_POLICY_VERSION",
    "V22PromotionPolicy",
    "V22PromotionResult",
    "V22ScorelineABComparison",
    "V22ScorelineABSummary",
    "build_historical_error_taxonomy",
    "compare_frozen_shadow_outcome",
    "compare_scoreline_case",
    "compare_v21_v22_scoreline_case",
    "evaluate_legacy_outcome_case",
    "evaluate_v22_promotion",
    "full_stack_shadow_validation_passed",
    "load_legacy_outcome_cases",
    "load_scoreline_regression_dataset",
    "regression_case_from_ledgers",
    "render_v22_ab_json",
    "render_v22_ab_markdown",
    "run_batch_scoreline_regression",
    "summarize_frozen_shadow",
    "summarize_legacy_outcomes",
    "summarize_scoreline_regression",
    "summarize_v21_v22_scoreline_ab",
    "v22_ab_report_payload",
]

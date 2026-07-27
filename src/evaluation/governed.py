"""One governed entry point for settled PRISM forward-test evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.evaluation.cohort_summary import CohortEvaluationSummary, summarize_settled_cohort
from src.evaluation.settled_case import SettledCaseEvaluation, evaluate_settled_case
from src.regression.governed_dataset import load_governed_settled_ledger_pairs
from src.regression.governed_manifest import GovernedCohortManifest, build_governed_cohort_manifest


@dataclass(frozen=True)
class GovernedEvaluationResult:
    """Manifest, settled case evaluations, and aggregate metrics for one cohort."""

    manifest: GovernedCohortManifest
    cases: tuple[SettledCaseEvaluation, ...]
    summary: CohortEvaluationSummary


def evaluate_governed_settled_cohort(
    prediction_root: Path | str = "data/performance-ledger",
    outcome_root: Path | str = "data/outcome-ledger",
) -> GovernedEvaluationResult:
    """Evaluate the exact governed cohort admitted by the frozen ledgers."""

    pairs = load_governed_settled_ledger_pairs(prediction_root, outcome_root)
    if not pairs:
        raise ValueError("governed settled cohort must not be empty")

    cases = tuple(evaluate_settled_case(snapshot, outcome) for snapshot, outcome in pairs)
    manifest = build_governed_cohort_manifest(prediction_root, outcome_root)
    summary = summarize_settled_cohort(cases)
    if manifest.case_count != summary.case_count:
        raise ValueError("governed manifest and evaluation case counts must match")
    return GovernedEvaluationResult(
        manifest=manifest,
        cases=cases,
        summary=summary,
    )

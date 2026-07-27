"""One governed post-match entry point for settlement and cohort evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.evaluation.governed import GovernedEvaluationResult, evaluate_governed_settled_cohort
from src.evaluation.promotion_evidence import PromotionEvidenceDecision, assess_promotion_evidence
from src.ledger.outcomes import FileSystemOutcomeLedgerStore, MatchOutcome
from src.ledger.settlement import SettledOutcomeResult, settle_verified_outcome


@dataclass(frozen=True)
class PostMatchClosedLoopResult:
    """Result of one verified outcome entering the governed forward-test loop."""

    settlement: SettledOutcomeResult
    evaluation: GovernedEvaluationResult
    promotion_evidence: PromotionEvidenceDecision


def process_verified_match_outcome(
    outcome: MatchOutcome,
    *,
    prediction_root: Path | str = "data/performance-ledger",
    outcome_root: Path | str = "data/outcome-ledger",
    minimum_promotion_cases: int = 20,
) -> PostMatchClosedLoopResult:
    """Settle one verified result, rebuild evaluation, and refresh promotion evidence."""

    settlement = settle_verified_outcome(
        outcome,
        FileSystemOutcomeLedgerStore(outcome_root),
        prediction_root=prediction_root,
    )
    evaluation = evaluate_governed_settled_cohort(prediction_root, outcome_root)
    promotion_evidence = assess_promotion_evidence(
        evaluation.summary,
        minimum_cases=minimum_promotion_cases,
    )
    return PostMatchClosedLoopResult(
        settlement=settlement,
        evaluation=evaluation,
        promotion_evidence=promotion_evidence,
    )

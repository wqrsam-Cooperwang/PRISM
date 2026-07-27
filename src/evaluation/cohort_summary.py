"""Aggregate settled PRISM forward-test evaluations across a governed cohort."""

from __future__ import annotations

from dataclasses import dataclass

from src.evaluation.settled_case import SettledCaseEvaluation


@dataclass(frozen=True)
class CohortEvaluationSummary:
    """Comparable V2.1 and V2.2 scoreline performance over settled cases."""

    case_count: int
    production_mean_distance: float
    shadow_mean_distance: float
    production_exact_hits: int
    shadow_exact_hits: int
    shadow_better_cases: int
    tied_cases: int
    shadow_worse_cases: int

    @property
    def mean_distance_delta(self) -> float:
        """Negative values mean V2.2 shadow is closer on average."""

        return self.shadow_mean_distance - self.production_mean_distance


def summarize_settled_cohort(
    evaluations: tuple[SettledCaseEvaluation, ...],
) -> CohortEvaluationSummary:
    """Summarize frozen production and shadow errors without hindsight weighting."""

    if not evaluations:
        raise ValueError("evaluations must not be empty")

    production_distances = tuple(case.production.goal_distance for case in evaluations)
    shadow_distances = tuple(case.shadow.goal_distance for case in evaluations)
    deltas = tuple(case.shadow_distance_delta for case in evaluations)
    case_count = len(evaluations)

    return CohortEvaluationSummary(
        case_count=case_count,
        production_mean_distance=sum(production_distances) / case_count,
        shadow_mean_distance=sum(shadow_distances) / case_count,
        production_exact_hits=sum(case.production.exact_hit for case in evaluations),
        shadow_exact_hits=sum(case.shadow.exact_hit for case in evaluations),
        shadow_better_cases=sum(delta < 0 for delta in deltas),
        tied_cases=sum(delta == 0 for delta in deltas),
        shadow_worse_cases=sum(delta > 0 for delta in deltas),
    )

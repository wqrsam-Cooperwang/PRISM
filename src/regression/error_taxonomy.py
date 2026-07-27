"""Observable historical error signatures for recovered PRISM predictions."""

from __future__ import annotations

from dataclasses import dataclass

from src.regression.outcome_benchmark import LegacyOutcomeMetrics


@dataclass(frozen=True)
class HistoricalErrorTaxonomy:
    """Aggregate observable signatures without claiming unobserved causal mechanisms."""

    case_count: int
    primary_direction_misses: int
    portfolio_direction_misses: int
    underpredicted_total_cases: int
    overpredicted_total_cases: int
    exact_total_cases: int
    same_story_cluster_cases: int
    clean_sheet_overconfidence_cases: int
    path_changing_event_cases: int

    @property
    def primary_direction_miss_rate(self) -> float:
        return self.primary_direction_misses / self.case_count

    @property
    def portfolio_direction_miss_rate(self) -> float:
        return self.portfolio_direction_misses / self.case_count

    @property
    def underpredicted_total_rate(self) -> float:
        return self.underpredicted_total_cases / self.case_count

    @property
    def same_story_cluster_rate(self) -> float:
        return self.same_story_cluster_cases / self.case_count


def build_historical_error_taxonomy(
    metrics: tuple[LegacyOutcomeMetrics, ...],
) -> HistoricalErrorTaxonomy:
    """Summarize observable failure signatures from benchmark metrics."""

    if not metrics:
        raise ValueError("historical error taxonomy requires at least one metric")

    return HistoricalErrorTaxonomy(
        case_count=len(metrics),
        primary_direction_misses=sum(not item.primary_direction_hit for item in metrics),
        portfolio_direction_misses=sum(not item.any_direction_hit for item in metrics),
        underpredicted_total_cases=sum(item.total_goals_error < 0 for item in metrics),
        overpredicted_total_cases=sum(item.total_goals_error > 0 for item in metrics),
        exact_total_cases=sum(item.total_goals_error == 0 for item in metrics),
        same_story_cluster_cases=sum(item.same_result_story_cluster for item in metrics),
        clean_sheet_overconfidence_cases=sum(item.clean_sheet_overconfidence for item in metrics),
        path_changing_event_cases=sum(item.path_changing_event for item in metrics),
    )

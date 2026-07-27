"""Evaluate frozen V2.1 production and V2.2 shadow scorelines after a match."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from statistics import mean
from typing import Any

from src.ledger.models import PredictionLedgerSnapshot
from src.ledger.outcomes import MatchOutcome
from src.regression.scoreline import ScorelineEngineMetrics
from src.scoreline.models import ScorelineCandidate


@dataclass(frozen=True)
class FrozenShadowComparison:
    """One post-match comparison using only predictions frozen before kickoff."""

    prediction_id: str
    match_id: str
    v21: ScorelineEngineMetrics
    v22: ScorelineEngineMetrics

    @property
    def distance_change(self) -> int:
        return self.v22.minimum_manhattan_distance - self.v21.minimum_manhattan_distance


@dataclass(frozen=True)
class FrozenShadowSummary:
    """Aggregate full-stack shadow evidence for V2.2 governance."""

    case_count: int
    v21_primary_hits: int
    v22_primary_hits: int
    v21_dual_hits: int
    v22_dual_hits: int
    v21_mean_minimum_distance: float
    v22_mean_minimum_distance: float
    v21_shared_story_pairs: int
    v22_shared_story_pairs: int
    v22_distance_improved_cases: int
    v22_distance_worsened_cases: int
    distance_tied_cases: int


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a mapping")
    return value


def _candidate(value: Any, field_name: str) -> ScorelineCandidate:
    item = _mapping(value, field_name)
    home = item.get("home_goals")
    away = item.get("away_goals")
    probability = item.get("probability")
    if isinstance(home, bool) or not isinstance(home, int):
        raise ValueError(f"{field_name}.home_goals must be an integer")
    if isinstance(away, bool) or not isinstance(away, int):
        raise ValueError(f"{field_name}.away_goals must be an integer")
    if isinstance(probability, bool) or not isinstance(probability, (int, float)):
        raise ValueError(f"{field_name}.probability must be numeric")
    return ScorelineCandidate(home, away, float(probability))


def _pair(value: Any, field_name: str) -> tuple[ScorelineCandidate, ScorelineCandidate]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{field_name} must contain exactly two frozen scorelines")
    return (
        _candidate(value[0], f"{field_name}[0]"),
        _candidate(value[1], f"{field_name}[1]"),
    )


def _result_family(candidate: ScorelineCandidate) -> str:
    if candidate.home_goals > candidate.away_goals:
        return "home"
    if candidate.home_goals < candidate.away_goals:
        return "away"
    return "draw"


def _clean_sheet_signature(candidate: ScorelineCandidate) -> str:
    if candidate.home_goals == 0 and candidate.away_goals == 0:
        return "both_zero"
    if candidate.home_goals == 0:
        return "home_zero"
    if candidate.away_goals == 0:
        return "away_zero"
    return "neither_zero"


def _metrics(
    pair: tuple[ScorelineCandidate, ScorelineCandidate],
    actual_home: int,
    actual_away: int,
) -> ScorelineEngineMetrics:
    actual = (actual_home, actual_away)
    scores = tuple((item.home_goals, item.away_goals) for item in pair)
    distances = tuple(abs(home - actual_home) + abs(away - actual_away) for home, away in scores)
    return ScorelineEngineMetrics(
        recommendations=pair,
        primary_exact_hit=scores[0] == actual,
        dual_exact_hit=actual in scores,
        minimum_manhattan_distance=min(distances),
        shared_story_pair=(
            _result_family(pair[0]) == _result_family(pair[1])
            and _clean_sheet_signature(pair[0]) == _clean_sheet_signature(pair[1])
        ),
    )


def compare_frozen_shadow_outcome(
    snapshot: PredictionLedgerSnapshot,
    outcome: MatchOutcome,
) -> FrozenShadowComparison:
    """Compare production and shadow recommendations exactly as frozen pre-match."""

    if snapshot.match_id != outcome.match_id:
        raise ValueError("prediction snapshot and outcome match_id must agree")

    report = _mapping(snapshot.payload.get("report"), "report")
    v21_scoreline = _mapping(report.get("scoreline"), "report.scoreline")
    v21_pair = _pair(
        v21_scoreline.get("recommended_scorelines"),
        "report.scoreline.recommended_scorelines",
    )

    shadows = _mapping(snapshot.payload.get("shadow_predictions"), "shadow_predictions")
    v22 = _mapping(shadows.get("v2_2"), "shadow_predictions.v2_2")
    if v22.get("status") != "available":
        raise ValueError("V2.2 shadow prediction is not available for full-stack evaluation")
    v22_scoreline = _mapping(v22.get("scoreline"), "shadow_predictions.v2_2.scoreline")
    v22_pair = _pair(
        v22_scoreline.get("recommended_scorelines"),
        "shadow_predictions.v2_2.scoreline.recommended_scorelines",
    )

    return FrozenShadowComparison(
        prediction_id=snapshot.prediction_id,
        match_id=snapshot.match_id,
        v21=_metrics(v21_pair, outcome.home_goals, outcome.away_goals),
        v22=_metrics(v22_pair, outcome.home_goals, outcome.away_goals),
    )


def summarize_frozen_shadow(
    comparisons: tuple[FrozenShadowComparison, ...],
) -> FrozenShadowSummary:
    """Aggregate full-stack production-versus-shadow evidence."""

    if not comparisons:
        raise ValueError("full-stack shadow summary requires at least one comparison")
    changes = tuple(item.distance_change for item in comparisons)
    return FrozenShadowSummary(
        case_count=len(comparisons),
        v21_primary_hits=sum(item.v21.primary_exact_hit for item in comparisons),
        v22_primary_hits=sum(item.v22.primary_exact_hit for item in comparisons),
        v21_dual_hits=sum(item.v21.dual_exact_hit for item in comparisons),
        v22_dual_hits=sum(item.v22.dual_exact_hit for item in comparisons),
        v21_mean_minimum_distance=mean(item.v21.minimum_manhattan_distance for item in comparisons),
        v22_mean_minimum_distance=mean(item.v22.minimum_manhattan_distance for item in comparisons),
        v21_shared_story_pairs=sum(item.v21.shared_story_pair for item in comparisons),
        v22_shared_story_pairs=sum(item.v22.shared_story_pair for item in comparisons),
        v22_distance_improved_cases=sum(change < 0 for change in changes),
        v22_distance_worsened_cases=sum(change > 0 for change in changes),
        distance_tied_cases=sum(change == 0 for change in changes),
    )

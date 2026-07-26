"""Historical exact-score regression comparison for PRISM V1 and V2.1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import exp, factorial
from statistics import mean

from src.domain.models import (
    AnalysisSession,
    DecisionOutput,
    MatchContext,
    MatchInfo,
    ModelOutput,
    TeamInfo,
)
from src.scoreline.engine import ScorelineEngine
from src.scoreline.models import ScorelineCandidate


@dataclass(frozen=True)
class ScorelineRegressionCase:
    """One historical match with frozen model inputs and the final score."""

    case_id: str
    models: tuple[ModelOutput, ...]
    actual_home_goals: int
    actual_away_goals: int

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("case_id must not be blank")
        if not self.models:
            raise ValueError("regression case requires at least one model")
        for value in (self.actual_home_goals, self.actual_away_goals):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError("actual goals must be non-negative integers")


@dataclass(frozen=True)
class ScorelineEngineMetrics:
    """Exact-score metrics for one engine on one historical case."""

    recommendations: tuple[ScorelineCandidate, ScorelineCandidate]
    primary_exact_hit: bool
    dual_exact_hit: bool
    minimum_manhattan_distance: int
    shared_story_pair: bool


@dataclass(frozen=True)
class ScorelineRegressionComparison:
    """One V1 versus V2.1 historical comparison."""

    case_id: str
    v1: ScorelineEngineMetrics
    v21: ScorelineEngineMetrics

    @property
    def distance_change(self) -> int:
        """Negative means V2.1 moved closer to the actual score."""

        return self.v21.minimum_manhattan_distance - self.v1.minimum_manhattan_distance


@dataclass(frozen=True)
class ScorelineRegressionSummary:
    """Aggregate V1 versus V2.1 historical regression summary."""

    case_count: int
    v1_primary_hits: int
    v21_primary_hits: int
    v1_dual_hits: int
    v21_dual_hits: int
    v1_mean_minimum_distance: float
    v21_mean_minimum_distance: float
    v1_shared_story_pairs: int
    v21_shared_story_pairs: int
    v21_distance_improved_cases: int
    v21_distance_worsened_cases: int
    distance_tied_cases: int


def _poisson(rate: float, goals: int) -> float:
    return exp(-rate) * (rate**goals) / factorial(goals)


def _expected_goals(model: ModelOutput) -> tuple[float, float]:
    home = model.expected_home_goals
    away = model.expected_away_goals
    if home is None or away is None:
        raise ValueError("regression model requires both expected-goal inputs")
    return float(home), float(away)


def _legacy_v1_pair(
    models: tuple[ModelOutput, ...],
) -> tuple[ScorelineCandidate, ScorelineCandidate]:
    eligible = tuple(
        model
        for model in models
        if model.expected_home_goals is not None and model.expected_away_goals is not None
    )
    if not eligible:
        raise ValueError("legacy V1 regression requires expected-goal inputs")
    rates = tuple(_expected_goals(model) for model in eligible)
    home_xg = mean(home for home, _ in rates)
    away_xg = mean(away for _, away in rates)
    candidates = tuple(
        ScorelineCandidate(
            home_goals,
            away_goals,
            _poisson(home_xg, home_goals) * _poisson(away_xg, away_goals),
        )
        for home_goals in range(11)
        for away_goals in range(11)
    )
    ranked = sorted(
        candidates,
        key=lambda item: (
            -item.probability,
            item.home_goals + item.away_goals,
            item.home_goals,
            item.away_goals,
        ),
    )
    return ranked[0], ranked[1]


def _v21_pair(
    models: tuple[ModelOutput, ...],
) -> tuple[ScorelineCandidate, ScorelineCandidate]:
    context = MatchContext(
        session=AnalysisSession(
            session_id="historical-regression",
            created_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
            prism_version="2.1.0",
        ),
        match=MatchInfo(
            match_id="historical-regression",
            competition="Historical Regression",
            kickoff=datetime(2000, 1, 2, tzinfo=timezone.utc),
        ),
        home_team=TeamInfo("historical-home", "Historical Home"),
        away_team=TeamInfo("historical-away", "Historical Away"),
        model_outputs=models,
        decision=DecisionOutput(),
    )
    output = ScorelineEngine().run(context)
    if not output.available or len(output.recommended_scorelines) != 2:
        raise ValueError("V2.1 regression requires available dual scoreline recommendations")
    return output.recommended_scorelines


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
    distances = tuple(
        abs(home - actual_home) + abs(away - actual_away) for home, away in scores
    )
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


def compare_scoreline_case(case: ScorelineRegressionCase) -> ScorelineRegressionComparison:
    """Replay one historical case through V1 and V2.1 exact-score logic."""

    v1_pair = _legacy_v1_pair(case.models)
    v21_pair = _v21_pair(case.models)
    return ScorelineRegressionComparison(
        case_id=case.case_id,
        v1=_metrics(v1_pair, case.actual_home_goals, case.actual_away_goals),
        v21=_metrics(v21_pair, case.actual_home_goals, case.actual_away_goals),
    )


def summarize_scoreline_regression(
    comparisons: tuple[ScorelineRegressionComparison, ...],
) -> ScorelineRegressionSummary:
    """Aggregate historical V1 versus V2.1 comparisons."""

    if not comparisons:
        raise ValueError("regression summary requires at least one comparison")
    changes = tuple(item.distance_change for item in comparisons)
    return ScorelineRegressionSummary(
        case_count=len(comparisons),
        v1_primary_hits=sum(item.v1.primary_exact_hit for item in comparisons),
        v21_primary_hits=sum(item.v21.primary_exact_hit for item in comparisons),
        v1_dual_hits=sum(item.v1.dual_exact_hit for item in comparisons),
        v21_dual_hits=sum(item.v21.dual_exact_hit for item in comparisons),
        v1_mean_minimum_distance=mean(
            item.v1.minimum_manhattan_distance for item in comparisons
        ),
        v21_mean_minimum_distance=mean(
            item.v21.minimum_manhattan_distance for item in comparisons
        ),
        v1_shared_story_pairs=sum(item.v1.shared_story_pair for item in comparisons),
        v21_shared_story_pairs=sum(item.v21.shared_story_pair for item in comparisons),
        v21_distance_improved_cases=sum(change < 0 for change in changes),
        v21_distance_worsened_cases=sum(change > 0 for change in changes),
        distance_tied_cases=sum(change == 0 for change in changes),
    )

"""Scoreline-layer A/B regression for PRISM V2.1 and V2.2 candidate.

Legacy replay cases do not contain frozen Consensus/Evidence outputs. This module
therefore derives a result-family distribution from the same frozen xG inputs via
a deterministic Poisson grid. The derived distribution is used only to select a
V2.2 scoreline regime; it does not claim to replay Direction Calibration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import exp, factorial
from statistics import mean

from src.consensus import DirectionCalibrationOutput
from src.domain.models import (
    AnalysisSession,
    DecisionOutput,
    MatchContext,
    MatchInfo,
    ModelOutput,
    TeamInfo,
)
from src.regression.scoreline import ScorelineEngineMetrics, ScorelineRegressionCase
from src.scoreline import ScorelineEngine, V22CandidateScorelineEngine
from src.scoreline.models import ScorelineCandidate


@dataclass(frozen=True)
class V22ScorelineABComparison:
    """One scoreline-layer comparison using only historically frozen xG inputs."""

    case_id: str
    v21: ScorelineEngineMetrics
    v22: ScorelineEngineMetrics

    @property
    def distance_change(self) -> int:
        """Negative means V2.2 moved closer to the actual score."""

        return self.v22.minimum_manhattan_distance - self.v21.minimum_manhattan_distance


@dataclass(frozen=True)
class V22ScorelineABSummary:
    """Aggregate scoreline-layer V2.1 versus V2.2 candidate metrics."""

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


def _poisson(rate: float, goals: int) -> float:
    return exp(-rate) * (rate**goals) / factorial(goals)


def _expected_goals(model: ModelOutput) -> tuple[float, float]:
    home = model.expected_home_goals
    away = model.expected_away_goals
    if home is None or away is None:
        raise ValueError("V2.2 A/B requires expected-goal inputs")
    return float(home), float(away)


def _aggregate_xg(models: tuple[ModelOutput, ...]) -> tuple[float, float]:
    eligible = tuple(
        model
        for model in models
        if model.expected_home_goals is not None and model.expected_away_goals is not None
    )
    if not eligible:
        raise ValueError("V2.2 A/B requires expected-goal inputs")
    rates = tuple(_expected_goals(model) for model in eligible)
    return (
        mean(home for home, _ in rates),
        mean(away for _, away in rates),
    )


def _xg_direction(home_xg: float, away_xg: float) -> DirectionCalibrationOutput:
    home_probability = 0.0
    draw_probability = 0.0
    away_probability = 0.0
    for home_goals in range(11):
        home_mass = _poisson(home_xg, home_goals)
        for away_goals in range(11):
            probability = home_mass * _poisson(away_xg, away_goals)
            if home_goals > away_goals:
                home_probability += probability
            elif home_goals < away_goals:
                away_probability += probability
            else:
                draw_probability += probability
    total = home_probability + draw_probability + away_probability
    if total <= 0.0:
        raise ValueError("xG-derived direction must have positive probability mass")
    probabilities = (
        home_probability / total,
        draw_probability / total,
        away_probability / total,
    )
    leading = max(probabilities)
    return DirectionCalibrationOutput(
        home_probability=probabilities[0],
        draw_probability=probabilities[1],
        away_probability=probabilities[2],
        reliability=1.0,
        raw_leading_probability=leading,
        calibrated_leading_probability=leading,
        method="legacy_xg_derived_direction_not_calibration",
    )


def _context(models: tuple[ModelOutput, ...]) -> MatchContext:
    return MatchContext(
        session=AnalysisSession(
            session_id="v22-scoreline-ab",
            created_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
            prism_version="2.2.0-candidate1",
        ),
        match=MatchInfo(
            match_id="v22-scoreline-ab",
            competition="Historical Regression",
            kickoff=datetime(2000, 1, 2, tzinfo=timezone.utc),
        ),
        home_team=TeamInfo("historical-home", "Historical Home"),
        away_team=TeamInfo("historical-away", "Historical Away"),
        model_outputs=models,
        decision=DecisionOutput(),
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


def compare_v21_v22_scoreline_case(
    case: ScorelineRegressionCase,
) -> V22ScorelineABComparison:
    """Compare V2.1 and V2.2 scoreline layers without fabricating legacy evidence."""

    context = _context(case.models)
    v21_output = ScorelineEngine().run(context)
    home_xg, away_xg = _aggregate_xg(case.models)
    direction = _xg_direction(home_xg, away_xg)
    v22_output = V22CandidateScorelineEngine().run_with_direction(context, direction)
    if (
        len(v21_output.recommended_scorelines) != 2
        or len(v22_output.recommended_scorelines) != 2
    ):
        raise ValueError("V2.1/V2.2 A/B requires dual scoreline recommendations")
    return V22ScorelineABComparison(
        case_id=case.case_id,
        v21=_metrics(
            v21_output.recommended_scorelines,
            case.actual_home_goals,
            case.actual_away_goals,
        ),
        v22=_metrics(
            v22_output.recommended_scorelines,
            case.actual_home_goals,
            case.actual_away_goals,
        ),
    )


def summarize_v21_v22_scoreline_ab(
    comparisons: tuple[V22ScorelineABComparison, ...],
) -> V22ScorelineABSummary:
    """Aggregate scoreline-layer A/B comparisons."""

    if not comparisons:
        raise ValueError("V2.1/V2.2 A/B summary requires at least one comparison")
    changes = tuple(item.distance_change for item in comparisons)
    return V22ScorelineABSummary(
        case_count=len(comparisons),
        v21_primary_hits=sum(item.v21.primary_exact_hit for item in comparisons),
        v22_primary_hits=sum(item.v22.primary_exact_hit for item in comparisons),
        v21_dual_hits=sum(item.v21.dual_exact_hit for item in comparisons),
        v22_dual_hits=sum(item.v22.dual_exact_hit for item in comparisons),
        v21_mean_minimum_distance=mean(
            item.v21.minimum_manhattan_distance for item in comparisons
        ),
        v22_mean_minimum_distance=mean(
            item.v22.minimum_manhattan_distance for item in comparisons
        ),
        v21_shared_story_pairs=sum(item.v21.shared_story_pair for item in comparisons),
        v22_shared_story_pairs=sum(item.v22.shared_story_pair for item in comparisons),
        v22_distance_improved_cases=sum(change < 0 for change in changes),
        v22_distance_worsened_cases=sum(change > 0 for change in changes),
        distance_tied_cases=sum(change == 0 for change in changes),
    )

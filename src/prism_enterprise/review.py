"""Automatic post-match review metrics for PRISM Enterprise V3.1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .archive import MatchResult, PredictionRecord


@dataclass(frozen=True)
class ReviewReport:
    prediction_id: str
    match_id: str
    outcome_correct: bool
    exact_score_correct: bool
    btts_correct: bool
    total_goals_error: float
    home_goal_error: float
    away_goal_error: float
    brier_score: float
    anomaly_flags: tuple[str, ...]
    attribution: tuple[str, ...]


def _outcome(home_goals: float, away_goals: float) -> str:
    if home_goals > away_goals:
        return "home"
    if home_goals < away_goals:
        return "away"
    return "draw"


def _brier_score(prediction: PredictionRecord, result: MatchResult) -> float:
    actual = {
        "home": 1.0 if result.home_goals > result.away_goals else 0.0,
        "draw": 1.0 if result.home_goals == result.away_goals else 0.0,
        "away": 1.0 if result.home_goals < result.away_goals else 0.0,
    }
    return (
        (prediction.outcome_home - actual["home"]) ** 2
        + (prediction.outcome_draw - actual["draw"]) ** 2
        + (prediction.outcome_away - actual["away"]) ** 2
    ) / 3.0


def _detect_anomalies(result: MatchResult) -> tuple[str, ...]:
    flags: list[str] = []
    if result.home_red_cards or result.away_red_cards:
        flags.append("red_card")
    if result.home_xg is not None and abs(result.home_goals - result.home_xg) >= 2.0:
        flags.append("home_finishing_variance")
    if result.away_xg is not None and abs(result.away_goals - result.away_xg) >= 2.0:
        flags.append("away_finishing_variance")
    return tuple(flags)


def _attribute_errors(
    prediction: PredictionRecord,
    result: MatchResult,
    anomaly_flags: Iterable[str],
) -> tuple[str, ...]:
    causes: list[str] = list(anomaly_flags)
    if result.home_xg is not None and abs(prediction.lambda_home - result.home_xg) >= 1.0:
        causes.append("home_chance_creation_miss")
    if result.away_xg is not None and abs(prediction.lambda_away - result.away_xg) >= 1.0:
        causes.append("away_chance_creation_miss")
    if not causes and (
        prediction.primary_score_home != result.home_goals
        or prediction.primary_score_away != result.away_goals
    ):
        causes.append("normal_scoreline_variance")
    return tuple(dict.fromkeys(causes))


def build_review(prediction: PredictionRecord, result: MatchResult) -> ReviewReport:
    """Compare one archived prediction with the final match result."""
    if prediction.match_id != result.match_id:
        raise ValueError("Prediction and result must reference the same match_id")

    predicted_outcome = _outcome(
        prediction.primary_score_home, prediction.primary_score_away
    )
    actual_outcome = _outcome(result.home_goals, result.away_goals)
    predicted_btts = prediction.primary_score_home > 0 and prediction.primary_score_away > 0
    actual_btts = result.home_goals > 0 and result.away_goals > 0
    anomalies = _detect_anomalies(result)

    return ReviewReport(
        prediction_id=prediction.prediction_id,
        match_id=prediction.match_id,
        outcome_correct=predicted_outcome == actual_outcome,
        exact_score_correct=(
            prediction.primary_score_home == result.home_goals
            and prediction.primary_score_away == result.away_goals
        ),
        btts_correct=predicted_btts == actual_btts,
        total_goals_error=abs(
            (prediction.lambda_home + prediction.lambda_away)
            - (result.home_goals + result.away_goals)
        ),
        home_goal_error=abs(prediction.lambda_home - result.home_goals),
        away_goal_error=abs(prediction.lambda_away - result.away_goals),
        brier_score=_brier_score(prediction, result),
        anomaly_flags=anomalies,
        attribution=_attribute_errors(prediction, result, anomalies),
    )

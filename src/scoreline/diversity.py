"""Diversity-aware dual-score selection for PRISM Exact Score V2.1."""

from __future__ import annotations

from src.scoreline.models import ScorelineCandidate


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


def diversity_adjusted_score(
    primary: ScorelineCandidate,
    candidate: ScorelineCandidate,
) -> float:
    """Penalize candidates that depend on the same broad match story as primary."""

    score = candidate.probability
    if _result_family(primary) == _result_family(candidate):
        score *= 0.72
    if _clean_sheet_signature(primary) == _clean_sheet_signature(candidate):
        score *= 0.75
    return score


def select_diversified_pair(
    ranked: tuple[ScorelineCandidate, ...],
) -> tuple[ScorelineCandidate, ScorelineCandidate]:
    """Return the raw top score and the best diversity-adjusted alternative."""

    if len(ranked) < 2:
        raise ValueError("dual-score selection requires at least two candidates")
    primary = ranked[0]
    alternatives = ranked[1:]
    second = max(
        alternatives,
        key=lambda item: (
            diversity_adjusted_score(primary, item),
            item.probability,
            -(item.home_goals + item.away_goals),
            -item.home_goals,
            -item.away_goals,
        ),
    )
    return primary, second

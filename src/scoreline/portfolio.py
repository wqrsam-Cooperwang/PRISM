"""Candidate portfolio optimization for PRISM Exact Score V2.2."""

from __future__ import annotations

from itertools import combinations

from src.scoreline.models import ScorelineCandidate


def _result_family(candidate: ScorelineCandidate) -> str:
    if candidate.home_goals > candidate.away_goals:
        return "home"
    if candidate.home_goals < candidate.away_goals:
        return "away"
    return "draw"


def _total_goals_bucket(candidate: ScorelineCandidate) -> str:
    total = candidate.home_goals + candidate.away_goals
    if total <= 2:
        return "low"
    if total <= 4:
        return "medium"
    return "high"


def _clean_sheet_signature(candidate: ScorelineCandidate) -> str:
    if candidate.home_goals == 0 and candidate.away_goals == 0:
        return "both_zero"
    if candidate.home_goals == 0:
        return "home_zero"
    if candidate.away_goals == 0:
        return "away_zero"
    return "neither_zero"


def _pair_utility(first: ScorelineCandidate, second: ScorelineCandidate) -> float:
    """Balance probability quality with independent match-story coverage."""

    probability_mass = first.probability + second.probability
    diversity_bonus = 0.0
    if _result_family(first) != _result_family(second):
        diversity_bonus += 0.18 * min(first.probability, second.probability)
    if _total_goals_bucket(first) != _total_goals_bucket(second):
        diversity_bonus += 0.12 * min(first.probability, second.probability)
    if _clean_sheet_signature(first) != _clean_sheet_signature(second):
        diversity_bonus += 0.10 * min(first.probability, second.probability)
    return probability_mass + diversity_bonus


def select_portfolio_pair(
    ranked: tuple[ScorelineCandidate, ...],
    *,
    candidate_limit: int = 12,
    minimum_relative_probability: float = 0.35,
) -> tuple[ScorelineCandidate, ScorelineCandidate]:
    """Select a high-quality pair with explicit multi-story coverage.

    The optimizer is deliberately conservative: candidates must retain at least
    a fixed fraction of the raw top score probability, preventing diversity from
    promoting implausible long-tail scores merely to look different.
    """

    if len(ranked) < 2:
        raise ValueError("portfolio selection requires at least two candidates")
    if candidate_limit < 2:
        raise ValueError("candidate_limit must be at least two")
    if not 0.0 < minimum_relative_probability <= 1.0:
        raise ValueError("minimum_relative_probability must be within (0, 1]")

    top_probability = ranked[0].probability
    floor = top_probability * minimum_relative_probability
    pool = tuple(candidate for candidate in ranked[:candidate_limit] if candidate.probability >= floor)
    if len(pool) < 2:
        return ranked[0], ranked[1]

    first, second = max(
        combinations(pool, 2),
        key=lambda pair: (
            _pair_utility(pair[0], pair[1]),
            pair[0].probability + pair[1].probability,
            -abs(
                (pair[0].home_goals + pair[0].away_goals)
                - (pair[1].home_goals + pair[1].away_goals)
            ),
            -pair[0].home_goals,
            -pair[0].away_goals,
            -pair[1].home_goals,
            -pair[1].away_goals,
        ),
    )
    if second.probability > first.probability:
        first, second = second, first
    return first, second

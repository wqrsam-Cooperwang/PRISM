import pytest

from src.scoreline import ScorelineCandidate, select_portfolio_pair


def _candidate(home: int, away: int, probability: float) -> ScorelineCandidate:
    return ScorelineCandidate(home, away, probability)


def test_portfolio_prefers_independent_story_when_probability_is_competitive() -> None:
    ranked = (
        _candidate(1, 0, 0.20),
        _candidate(2, 0, 0.19),
        _candidate(1, 1, 0.18),
        _candidate(2, 1, 0.12),
    )

    first, second = select_portfolio_pair(ranked)

    assert first == ranked[0]
    assert second == ranked[2]


def test_portfolio_probability_floor_blocks_implausible_diversity() -> None:
    ranked = (
        _candidate(1, 0, 0.30),
        _candidate(2, 0, 0.21),
        _candidate(1, 1, 0.05),
    )

    assert select_portfolio_pair(ranked) == (ranked[0], ranked[1])


def test_portfolio_validates_contract() -> None:
    with pytest.raises(ValueError, match="at least two"):
        select_portfolio_pair((_candidate(1, 0, 0.2),))
    with pytest.raises(ValueError, match="candidate_limit"):
        select_portfolio_pair((_candidate(1, 0, 0.2), _candidate(1, 1, 0.1)), candidate_limit=1)
    with pytest.raises(ValueError, match="minimum_relative_probability"):
        select_portfolio_pair(
            (_candidate(1, 0, 0.2), _candidate(1, 1, 0.1)),
            minimum_relative_probability=0.0,
        )

import pytest

from src.scoreline.diversity import diversity_adjusted_score, select_diversified_pair
from src.scoreline.models import ScorelineCandidate


def _candidate(home: int, away: int, probability: float) -> ScorelineCandidate:
    return ScorelineCandidate(home, away, probability)


def test_diversity_penalizes_same_result_and_clean_sheet_story() -> None:
    primary = _candidate(1, 0, 0.20)
    same_story = _candidate(2, 0, 0.18)
    different_story = _candidate(1, 1, 0.17)

    assert diversity_adjusted_score(primary, same_story) == pytest.approx(0.18 * 0.72 * 0.75)
    assert diversity_adjusted_score(primary, different_story) == pytest.approx(0.17)


def test_diversity_handles_away_and_draw_result_families() -> None:
    away_primary = _candidate(0, 1, 0.20)
    away_alternative = _candidate(1, 2, 0.18)
    draw_primary = _candidate(0, 0, 0.16)
    draw_alternative = _candidate(1, 1, 0.15)

    assert diversity_adjusted_score(away_primary, away_alternative) == pytest.approx(0.18 * 0.72)
    assert diversity_adjusted_score(draw_primary, draw_alternative) == pytest.approx(0.15 * 0.72)


def test_diversity_distinguishes_home_zero_and_neither_zero_signatures() -> None:
    home_zero = _candidate(0, 2, 0.20)
    another_home_zero = _candidate(0, 1, 0.18)
    neither_zero = _candidate(2, 1, 0.17)
    another_neither_zero = _candidate(3, 1, 0.16)

    assert diversity_adjusted_score(home_zero, another_home_zero) == pytest.approx(
        0.18 * 0.72 * 0.75
    )
    assert diversity_adjusted_score(neither_zero, another_neither_zero) == pytest.approx(
        0.16 * 0.72 * 0.75
    )


def test_dual_score_selector_requires_two_candidates() -> None:
    with pytest.raises(ValueError, match="at least two candidates"):
        select_diversified_pair((_candidate(1, 0, 0.2),))


def test_dual_score_selector_is_deterministic_on_ties() -> None:
    ranked = (
        _candidate(1, 0, 0.20),
        _candidate(1, 1, 0.15),
        _candidate(0, 0, 0.15),
    )

    first = select_diversified_pair(ranked)
    second = select_diversified_pair(ranked)

    assert first == second
    assert first[0] == ranked[0]

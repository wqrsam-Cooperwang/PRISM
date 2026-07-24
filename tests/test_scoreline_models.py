import pytest

from src.scoreline.models import ScorelineCandidate, ScorelineOutput


def candidate(home: int, away: int, probability: float) -> ScorelineCandidate:
    return ScorelineCandidate(home, away, probability)


def test_scoreline_candidate_validates_goals_and_probability() -> None:
    item = candidate(2, 1, 0.12)
    assert item.home_goals == 2
    assert item.away_goals == 1
    assert item.probability == 0.12

    with pytest.raises(ValueError, match="non-negative integer"):
        candidate(-1, 0, 0.1)
    with pytest.raises(ValueError, match="between 0 and 1"):
        candidate(1, 0, 1.1)


def test_available_scoreline_requires_three_candidates_and_source_model() -> None:
    with pytest.raises(ValueError, match="exactly three candidates"):
        ScorelineOutput(
            available=True,
            method="poisson",
            source_model_ids=("m1",),
            expected_home_goals=1.5,
            expected_away_goals=1.0,
            top_scorelines=(candidate(1, 0, 0.2),),
            grid_probability_mass=0.99,
            tail_mass=0.01,
        )

    with pytest.raises(ValueError, match="requires source models"):
        ScorelineOutput(
            available=True,
            method="poisson",
            expected_home_goals=1.5,
            expected_away_goals=1.0,
            top_scorelines=(
                candidate(1, 0, 0.2),
                candidate(1, 1, 0.18),
                candidate(2, 0, 0.15),
            ),
            grid_probability_mass=0.99,
            tail_mass=0.01,
        )


def test_unavailable_scoreline_cannot_contain_predictions() -> None:
    with pytest.raises(ValueError, match="cannot contain expected goals"):
        ScorelineOutput(
            available=False,
            method="poisson",
            expected_home_goals=1.0,
        )

    with pytest.raises(ValueError, match="cannot contain predictions"):
        ScorelineOutput(
            available=False,
            method="poisson",
            source_model_ids=("m1",),
        )


def test_grid_and_tail_probability_mass_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="must sum to 1"):
        ScorelineOutput(
            available=False,
            method="poisson",
            grid_probability_mass=0.8,
            tail_mass=0.1,
        )


def test_source_model_ids_must_be_unique() -> None:
    with pytest.raises(ValueError, match="must be unique"):
        ScorelineOutput(
            available=True,
            method="poisson",
            source_model_ids=("m1", "m1"),
            expected_home_goals=1.5,
            expected_away_goals=1.0,
            top_scorelines=(
                candidate(1, 0, 0.2),
                candidate(1, 1, 0.18),
                candidate(2, 0, 0.15),
            ),
            grid_probability_mass=0.99,
            tail_mass=0.01,
        )

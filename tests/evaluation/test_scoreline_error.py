"""Tests for settled forward-test scoreline error metrics."""

from src.evaluation.scoreline_error import minimum_scoreline_error


def test_minimum_error_detects_exact_scoreline_hit() -> None:
    error = minimum_scoreline_error(
        ((1, 1), (0, 0)),
        actual_home=0,
        actual_away=0,
    )

    assert error.goal_distance == 0
    assert error.exact_hit is True
    assert error.result_direction_hit is True


def test_minimum_error_preserves_bad_scoreline_miss() -> None:
    error = minimum_scoreline_error(
        ((1, 0), (1, 1)),
        actual_home=4,
        actual_away=0,
    )

    assert error.goal_distance == 3
    assert error.exact_hit is False
    assert error.result_direction_hit is True


def test_direction_hit_does_not_hide_scoreline_distance() -> None:
    error = minimum_scoreline_error(
        ((2, 1), (1, 0)),
        actual_home=4,
        actual_away=0,
    )

    assert error.result_direction_hit is True
    assert error.goal_distance == 3
    assert error.exact_hit is False

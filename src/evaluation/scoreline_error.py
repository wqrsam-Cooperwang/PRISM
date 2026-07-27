"""Scoreline error metrics for settled PRISM forward-test cases."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScorelineError:
    """Distance from one predicted scoreline to the verified final score."""

    predicted_home: int
    predicted_away: int
    actual_home: int
    actual_away: int

    @property
    def goal_distance(self) -> int:
        return abs(self.predicted_home - self.actual_home) + abs(
            self.predicted_away - self.actual_away
        )

    @property
    def exact_hit(self) -> bool:
        return self.goal_distance == 0

    @property
    def result_direction_hit(self) -> bool:
        return _direction(self.predicted_home, self.predicted_away) == _direction(
            self.actual_home,
            self.actual_away,
        )


def minimum_scoreline_error(
    predicted_scorelines: tuple[tuple[int, int], ...],
    *,
    actual_home: int,
    actual_away: int,
) -> ScorelineError:
    """Return the closest frozen scoreline to the verified result."""

    if not predicted_scorelines:
        raise ValueError("predicted_scorelines must not be empty")
    errors = tuple(
        ScorelineError(home, away, actual_home, actual_away)
        for home, away in predicted_scorelines
    )
    return min(errors, key=lambda error: error.goal_distance)


def _direction(home: int, away: int) -> int:
    if home > away:
        return 1
    if home < away:
        return -1
    return 0

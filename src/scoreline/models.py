"""Immutable scoreline output models."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


def _unit_interval(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be finite and between 0 and 1")
    return result


def _nonnegative(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


@dataclass(frozen=True)
class ScorelineCandidate:
    home_goals: int
    away_goals: int
    probability: float

    def __post_init__(self) -> None:
        for name in ("home_goals", "away_goals"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        object.__setattr__(self, "probability", _unit_interval(self.probability, "probability"))


@dataclass(frozen=True)
class ScorelineOutput:
    available: bool
    method: str
    source_model_ids: tuple[str, ...] = ()
    expected_home_goals: float | None = None
    expected_away_goals: float | None = None
    top_scorelines: tuple[ScorelineCandidate, ...] = ()
    grid_probability_mass: float = 0.0
    tail_mass: float = 1.0
    rationale: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.available, bool):
            raise ValueError("available must be boolean")
        if not isinstance(self.method, str) or not self.method.strip():
            raise ValueError("method must be a non-empty string")
        object.__setattr__(self, "method", self.method.strip())
        model_ids = tuple(item.strip() for item in self.source_model_ids)
        if any(not item for item in model_ids):
            raise ValueError("source_model_ids must not contain empty values")
        if len(set(model_ids)) != len(model_ids):
            raise ValueError("source_model_ids must be unique")
        object.__setattr__(self, "source_model_ids", model_ids)
        object.__setattr__(self, "top_scorelines", tuple(self.top_scorelines))
        object.__setattr__(self, "rationale", tuple(self.rationale))
        grid_mass = _unit_interval(self.grid_probability_mass, "grid_probability_mass")
        tail_mass = _unit_interval(self.tail_mass, "tail_mass")
        if abs(grid_mass + tail_mass - 1.0) > 1e-9:
            raise ValueError("grid_probability_mass and tail_mass must sum to 1")
        object.__setattr__(self, "grid_probability_mass", grid_mass)
        object.__setattr__(self, "tail_mass", tail_mass)

        if self.available:
            if self.expected_home_goals is None or self.expected_away_goals is None:
                raise ValueError("available scoreline output requires expected goals")
            object.__setattr__(
                self,
                "expected_home_goals",
                _nonnegative(self.expected_home_goals, "expected_home_goals"),
            )
            object.__setattr__(
                self,
                "expected_away_goals",
                _nonnegative(self.expected_away_goals, "expected_away_goals"),
            )
            if not self.source_model_ids:
                raise ValueError("available scoreline output requires source models")
            if len(self.top_scorelines) != 3:
                raise ValueError("available scoreline output requires exactly three candidates")
        else:
            if self.expected_home_goals is not None or self.expected_away_goals is not None:
                raise ValueError("unavailable scoreline output cannot contain expected goals")
            if self.source_model_ids or self.top_scorelines:
                raise ValueError("unavailable scoreline output cannot contain predictions")

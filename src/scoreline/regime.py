"""Deterministic match-regime classification for PRISM Exact Score V2.2 candidates."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.consensus.direction_calibration import DirectionCalibrationOutput


class ScorelineRegime(str, Enum):
    BALANCED_LOW = "balanced_low"
    BALANCED_OPEN = "balanced_open"
    HOME_CONTROL = "home_control"
    AWAY_CONTROL = "away_control"
    HOME_OPEN = "home_open"
    AWAY_OPEN = "away_open"


@dataclass(frozen=True)
class RegimeClassification:
    regime: ScorelineRegime
    total_xg: float
    xg_gap: float
    leading_probability: float


class ScorelineRegimeClassifier:
    """Classify scoreline shape without fitting parameters to historical outcomes."""

    version = "2.2.0-candidate1"
    open_total_threshold = 2.75
    balanced_probability_gap = 0.10
    directional_probability_threshold = 0.44

    def run(
        self,
        direction: DirectionCalibrationOutput,
        home_xg: float,
        away_xg: float,
    ) -> RegimeClassification:
        if home_xg < 0.0 or away_xg < 0.0:
            raise ValueError("regime expected goals must be non-negative")
        total_xg = home_xg + away_xg
        xg_gap = home_xg - away_xg
        probabilities = (
            direction.home_probability,
            direction.draw_probability,
            direction.away_probability,
        )
        leading_probability = max(probabilities)
        sorted_probabilities = sorted(probabilities, reverse=True)
        probability_gap = sorted_probabilities[0] - sorted_probabilities[1]
        is_balanced = probability_gap < self.balanced_probability_gap
        is_open = total_xg >= self.open_total_threshold

        if is_balanced:
            regime = (
                ScorelineRegime.BALANCED_OPEN if is_open else ScorelineRegime.BALANCED_LOW
            )
        elif (
            direction.home_probability >= self.directional_probability_threshold
            and direction.home_probability > direction.away_probability
        ):
            regime = ScorelineRegime.HOME_OPEN if is_open else ScorelineRegime.HOME_CONTROL
        elif (
            direction.away_probability >= self.directional_probability_threshold
            and direction.away_probability > direction.home_probability
        ):
            regime = ScorelineRegime.AWAY_OPEN if is_open else ScorelineRegime.AWAY_CONTROL
        else:
            regime = (
                ScorelineRegime.BALANCED_OPEN if is_open else ScorelineRegime.BALANCED_LOW
            )

        return RegimeClassification(
            regime=regime,
            total_xg=total_xg,
            xg_gap=xg_gap,
            leading_probability=leading_probability,
        )

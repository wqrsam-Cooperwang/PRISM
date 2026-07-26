"""Transparent baseline prediction models for PRISM."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite, sqrt

from src.domain.models import ModelOutput
from src.features.models import FeatureVector


def _finite_feature(features: FeatureVector, name: str) -> float:
    value = features.values[name]
    if not isfinite(value):
        raise ValueError(f"Feature {name} must be finite")
    return float(value)


@dataclass(frozen=True)
class MarketProbabilityModel:
    """Return governed de-vigged 1X2 market probabilities unchanged."""

    model_id: str = "market_probability"
    version: str = "1.0.0"
    required_features: tuple[str, ...] = (
        "market_home_implied_probability",
        "market_draw_implied_probability",
        "market_away_implied_probability",
    )

    def predict(self, features: FeatureVector) -> ModelOutput:
        home = _finite_feature(features, "market_home_implied_probability")
        draw = _finite_feature(features, "market_draw_implied_probability")
        away = _finite_feature(features, "market_away_implied_probability")
        return ModelOutput(
            model_id=self.model_id,
            model_version=self.version,
            home_probability=home,
            draw_probability=draw,
            away_probability=away,
            diagnostics={"method": "de_vigged_market_identity"},
        )


@dataclass(frozen=True)
class EloProbabilityModel:
    """Three-outcome Davidson-style Bradley-Terry probability baseline."""

    home_advantage_elo: float = 60.0
    draw_scale: float = 0.65
    model_id: str = "elo_probability"
    version: str = "1.0.0"
    required_features: tuple[str, ...] = ("elo_difference",)

    def __post_init__(self) -> None:
        if not isfinite(float(self.home_advantage_elo)):
            raise ValueError("home_advantage_elo must be finite")
        draw_scale = float(self.draw_scale)
        if not isfinite(draw_scale) or draw_scale < 0.0:
            raise ValueError("draw_scale must be finite and non-negative")
        object.__setattr__(self, "home_advantage_elo", float(self.home_advantage_elo))
        object.__setattr__(self, "draw_scale", draw_scale)

    def predict(self, features: FeatureVector) -> ModelOutput:
        elo_difference = _finite_feature(features, "elo_difference")
        strength_ratio = 10.0 ** ((elo_difference + self.home_advantage_elo) / 400.0)
        home_quality = strength_ratio
        away_quality = 1.0
        draw_quality = self.draw_scale * sqrt(strength_ratio)
        total = home_quality + draw_quality + away_quality
        if not isfinite(total) or total <= 0.0:
            raise ValueError("Elo probability qualities must have a positive finite total")

        return ModelOutput(
            model_id=self.model_id,
            model_version=self.version,
            home_probability=home_quality / total,
            draw_probability=draw_quality / total,
            away_probability=away_quality / total,
            diagnostics={
                "method": "davidson_bradley_terry",
                "home_advantage_elo": self.home_advantage_elo,
                "draw_scale": self.draw_scale,
                "elo_difference": elo_difference,
            },
        )


@dataclass(frozen=True)
class TeamStatisticsProbabilityModel:
    """Transparent provisional 1X2 baseline from season and recent team statistics."""

    points_per_game_weight: float = 0.90
    goal_difference_weight: float = 0.65
    recent_form_weight: float = 0.05
    home_advantage: float = 0.18
    draw_scale: float = 0.72
    model_id: str = "team_statistics_probability"
    version: str = "1.0.0"
    required_features: tuple[str, ...] = (
        "team_points_per_game_difference",
        "team_goal_difference_per_game_difference",
        "recent_points_difference",
    )

    def __post_init__(self) -> None:
        for name in (
            "points_per_game_weight",
            "goal_difference_weight",
            "recent_form_weight",
            "home_advantage",
            "draw_scale",
        ):
            value = float(getattr(self, name))
            if not isfinite(value):
                raise ValueError(f"{name} must be finite")
            if name == "draw_scale" and value < 0.0:
                raise ValueError("draw_scale must be non-negative")
            object.__setattr__(self, name, value)

    def predict(self, features: FeatureVector) -> ModelOutput:
        ppg_difference = _finite_feature(features, "team_points_per_game_difference")
        goal_difference = _finite_feature(
            features,
            "team_goal_difference_per_game_difference",
        )
        recent_difference = _finite_feature(features, "recent_points_difference")

        composite = (
            self.points_per_game_weight * ppg_difference
            + self.goal_difference_weight * goal_difference
            + self.recent_form_weight * recent_difference
            + self.home_advantage
        )
        strength_ratio = exp(composite)
        home_quality = strength_ratio
        away_quality = 1.0
        draw_quality = self.draw_scale * sqrt(strength_ratio)
        total = home_quality + draw_quality + away_quality
        if not isfinite(total) or total <= 0.0:
            raise ValueError(
                "Team-statistics probability qualities must have a positive finite total"
            )

        return ModelOutput(
            model_id=self.model_id,
            model_version=self.version,
            home_probability=home_quality / total,
            draw_probability=draw_quality / total,
            away_probability=away_quality / total,
            diagnostics={
                "method": "provisional_team_statistics_davidson",
                "points_per_game_weight": self.points_per_game_weight,
                "goal_difference_weight": self.goal_difference_weight,
                "recent_form_weight": self.recent_form_weight,
                "home_advantage": self.home_advantage,
                "draw_scale": self.draw_scale,
                "composite_strength_difference": composite,
            },
        )

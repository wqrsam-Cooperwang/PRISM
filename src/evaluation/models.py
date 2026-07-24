"""Immutable real-match evaluation models for PRISM."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite
from types import MappingProxyType

from src.report.models import PredictionReport
from src.runtime.request import MatchRequest


def _freeze_mapping(value: Mapping[str, float]) -> Mapping[str, float]:
    return MappingProxyType({str(key): float(item) for key, item in value.items()})


def _nonnegative_goal(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _finite(value: float, name: str) -> float:
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    request: MatchRequest
    completeness: Mapping[str, float]
    prism_version: str
    actual_home_goals: int
    actual_away_goals: int
    session_id: str | None = None
    created_at: datetime | None = None
    git_commit: str | None = None
    data_version: str | None = None
    rule_version: str | None = None
    model_version: str | None = None
    prompt_version: str | None = None
    operator: str | None = None
    ai_models: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id.strip():
            raise ValueError("case_id must be a non-empty string")
        if not isinstance(self.prism_version, str) or not self.prism_version.strip():
            raise ValueError("prism_version must be a non-empty string")
        object.__setattr__(self, "case_id", self.case_id.strip())
        object.__setattr__(self, "prism_version", self.prism_version.strip())
        object.__setattr__(
            self,
            "actual_home_goals",
            _nonnegative_goal(self.actual_home_goals, "actual_home_goals"),
        )
        object.__setattr__(
            self,
            "actual_away_goals",
            _nonnegative_goal(self.actual_away_goals, "actual_away_goals"),
        )
        object.__setattr__(self, "completeness", _freeze_mapping(self.completeness))
        object.__setattr__(self, "ai_models", tuple(self.ai_models))


@dataclass(frozen=True)
class EvaluationResult:
    case_id: str
    match_id: str
    actual_home_goals: int
    actual_away_goals: int
    actual_outcome: str
    home_probability: float
    draw_probability: float
    away_probability: float
    leading_outcome: str
    leading_probability: float
    brier_score: float
    log_loss: float
    top1_correct: bool
    scoreline_top3_hit: bool | None
    decision_action: str
    selected_market: str | None
    candidate_correct: bool | None
    overall_confidence: float
    evidence_gate: str
    report: PredictionReport

    def __post_init__(self) -> None:
        for name in (
            "home_probability",
            "draw_probability",
            "away_probability",
            "leading_probability",
            "brier_score",
            "log_loss",
            "overall_confidence",
        ):
            object.__setattr__(self, name, _finite(getattr(self, name), name))
        if self.actual_outcome not in {"home", "draw", "away"}:
            raise ValueError("actual_outcome must be home, draw, or away")
        if self.leading_outcome not in {"home", "draw", "away", "tie"}:
            raise ValueError("leading_outcome must be home, draw, away, or tie")


@dataclass(frozen=True)
class EvaluationSummary:
    case_count: int
    mean_brier_score: float
    mean_log_loss: float
    top1_accuracy: float
    scoreline_available_count: int
    scoreline_top3_hit_rate: float | None
    candidate_count: int
    candidate_accuracy: float | None
    mean_overall_confidence: float
    results: tuple[EvaluationResult, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if isinstance(self.case_count, bool) or not isinstance(self.case_count, int):
            raise ValueError("case_count must be an integer")
        if self.case_count < 1:
            raise ValueError("case_count must be at least 1")
        if self.case_count != len(self.results):
            raise ValueError("case_count must match results")
        for name in (
            "mean_brier_score",
            "mean_log_loss",
            "top1_accuracy",
            "mean_overall_confidence",
        ):
            object.__setattr__(self, name, _finite(getattr(self, name), name))
        for name in ("scoreline_top3_hit_rate", "candidate_accuracy"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _finite(value, name))
        object.__setattr__(self, "results", tuple(self.results))

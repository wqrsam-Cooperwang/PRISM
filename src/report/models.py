"""Immutable presentation models for governed PRISM prediction reports."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(value))


@dataclass(frozen=True)
class MatchReport:
    match_id: str
    competition: str
    kickoff: datetime
    home_team: str
    away_team: str


@dataclass(frozen=True)
class ConsensusReport:
    home_probability: float
    draw_probability: float
    away_probability: float
    leading_outcome: str
    agreement: float
    model_count: int


@dataclass(frozen=True)
class ConfidenceReport:
    overall: float
    band: str
    penalties: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceReport:
    score: int
    gate: str
    warnings: tuple[str, ...] = ()
    missing_categories: tuple[str, ...] = ()
    critical_caps_applied: tuple[str, ...] = ()


@dataclass(frozen=True)
class DecisionReport:
    action: str
    selected_market: str | None = None
    expected_value: float | None = None
    risk_level: str | None = None
    rationale: tuple[str, ...] = ()


@dataclass(frozen=True)
class AdjustmentReport:
    base_confidence: float
    adjusted_confidence: float
    confidence_cap: float | None
    decision_blocked: bool
    applied_effects: tuple[str, ...] = ()
    observed_effects: tuple[str, ...] = ()
    rule_outputs: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rule_outputs",
            tuple(_freeze_mapping(item) for item in self.rule_outputs),
        )


@dataclass(frozen=True)
class ScorelineCandidateReport:
    home_goals: int
    away_goals: int
    probability: float


@dataclass(frozen=True)
class ScorelineReport:
    available: bool
    method: str
    expected_home_goals: float | None = None
    expected_away_goals: float | None = None
    top_scorelines: tuple[ScorelineCandidateReport, ...] = ()
    source_model_ids: tuple[str, ...] = ()
    grid_probability_mass: float = 0.0
    tail_mass: float = 1.0


@dataclass(frozen=True)
class EngineTraceReport:
    name: str
    version: str
    status: str


@dataclass(frozen=True)
class ProvenanceReport:
    prism_version: str
    schema_version: str
    runtime_version: str
    session_id: str
    git_commit: str | None = None
    data_version: str | None = None
    rule_version: str | None = None
    model_version: str | None = None
    prompt_version: str | None = None
    ai_models: tuple[str, ...] = ()
    engine_trace: tuple[EngineTraceReport, ...] = ()


@dataclass(frozen=True)
class PredictionReport:
    match: MatchReport
    consensus: ConsensusReport | None
    confidence: ConfidenceReport | None
    evidence: EvidenceReport | None
    decision: DecisionReport | None
    adjustment: AdjustmentReport | None
    scoreline: ScorelineReport | None
    provenance: ProvenanceReport

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible dictionary without mutating report objects."""

        def convert(value: Any) -> Any:
            if isinstance(value, Enum):
                return value.value
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, Mapping):
                return {str(key): convert(item) for key, item in value.items()}
            if isinstance(value, (tuple, list)):
                return [convert(item) for item in value]
            if is_dataclass(value) and not isinstance(value, type):
                return {item.name: convert(getattr(value, item.name)) for item in fields(value)}
            return value

        result = convert(self)
        if not isinstance(result, dict):
            raise TypeError("PredictionReport serialization did not produce an object")
        return result

"""Canonical domain models for PRISM.

The objects in this module are immutable and JSON serializable. Engines should
return a new MatchContext, normally via dataclasses.replace, rather than mutate
an existing analysis state.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping


SCHEMA_VERSION = "1.0.0"


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_aware_datetime(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def _validate_unit_interval(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")
    result = float(value)
    if not isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{field_name} must be finite and between 0 and 1")
    return result


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("Expected a mapping")
    return MappingProxyType(dict(value))


class EvidenceGate(str, Enum):
    DEEP = "deep"
    STANDARD = "standard"
    LIMITED = "limited"
    REJECTED = "rejected"


class ConfidenceBand(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class DecisionAction(str, Enum):
    NO_DECISION = "no_decision"
    WATCH = "watch"
    NO_BET = "no_bet"
    CANDIDATE = "candidate"


@dataclass(frozen=True)
class AnalysisSession:
    session_id: str
    created_at: datetime
    prism_version: str
    schema_version: str = SCHEMA_VERSION
    git_commit: str | None = None
    data_version: str | None = None
    rule_version: str | None = None
    model_version: str | None = None
    prompt_version: str | None = None
    operator: str | None = None
    ai_models: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "session_id", _require_text(self.session_id, "session_id"))
        object.__setattr__(self, "created_at", _require_aware_datetime(self.created_at, "created_at"))
        object.__setattr__(self, "prism_version", _require_text(self.prism_version, "prism_version"))
        object.__setattr__(self, "schema_version", _require_text(self.schema_version, "schema_version"))
        object.__setattr__(self, "ai_models", tuple(self.ai_models))


@dataclass(frozen=True)
class MatchInfo:
    match_id: str
    competition: str
    kickoff: datetime
    venue: str | None = None
    season: str | None = None
    stage: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "match_id", _require_text(self.match_id, "match_id"))
        object.__setattr__(self, "competition", _require_text(self.competition, "competition"))
        object.__setattr__(self, "kickoff", _require_aware_datetime(self.kickoff, "kickoff"))


@dataclass(frozen=True)
class TeamInfo:
    team_id: str
    name: str
    country: str | None = None
    elo_rating: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "team_id", _require_text(self.team_id, "team_id"))
        object.__setattr__(self, "name", _require_text(self.name, "name"))
        if self.elo_rating is not None:
            value = float(self.elo_rating)
            if not isfinite(value):
                raise ValueError("elo_rating must be finite")
            object.__setattr__(self, "elo_rating", value)


@dataclass(frozen=True)
class EvidenceOutput:
    score: int
    raw_score: float
    gate: EvidenceGate
    category_scores: Mapping[str, float] = field(default_factory=dict)
    missing_categories: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    critical_caps_applied: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.score, bool) or not isinstance(self.score, int) or not 0 <= self.score <= 100:
            raise ValueError("score must be an integer between 0 and 100")
        raw = float(self.raw_score)
        if not isfinite(raw) or not 0.0 <= raw <= 100.0:
            raise ValueError("raw_score must be finite and between 0 and 100")
        object.__setattr__(self, "raw_score", raw)
        object.__setattr__(self, "gate", EvidenceGate(self.gate))
        object.__setattr__(self, "category_scores", _freeze_mapping(self.category_scores))
        object.__setattr__(self, "missing_categories", tuple(self.missing_categories))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(self, "critical_caps_applied", tuple(self.critical_caps_applied))


@dataclass(frozen=True)
class ModelOutput:
    model_id: str
    model_version: str
    home_probability: float
    draw_probability: float
    away_probability: float
    expected_home_goals: float | None = None
    expected_away_goals: float | None = None
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_id", _require_text(self.model_id, "model_id"))
        object.__setattr__(self, "model_version", _require_text(self.model_version, "model_version"))
        probabilities = (
            _validate_unit_interval(self.home_probability, "home_probability"),
            _validate_unit_interval(self.draw_probability, "draw_probability"),
            _validate_unit_interval(self.away_probability, "away_probability"),
        )
        if abs(sum(probabilities) - 1.0) > 1e-6:
            raise ValueError("Model probabilities must sum to 1")
        object.__setattr__(self, "home_probability", probabilities[0])
        object.__setattr__(self, "draw_probability", probabilities[1])
        object.__setattr__(self, "away_probability", probabilities[2])
        object.__setattr__(self, "diagnostics", _freeze_mapping(self.diagnostics))


@dataclass(frozen=True)
class ConfidenceOutput:
    evidence: float
    model: float
    context: float
    consensus: float
    overall: float
    band: ConfidenceBand
    penalties: tuple[str, ...] = ()
    rationale: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("evidence", "model", "context", "consensus", "overall"):
            object.__setattr__(self, name, _validate_unit_interval(getattr(self, name), name))
        object.__setattr__(self, "band", ConfidenceBand(self.band))
        object.__setattr__(self, "penalties", tuple(self.penalties))
        object.__setattr__(self, "rationale", tuple(self.rationale))


@dataclass(frozen=True)
class DecisionOutput:
    action: DecisionAction = DecisionAction.NO_DECISION
    selected_market: str | None = None
    expected_value: float | None = None
    risk_level: str | None = None
    rationale: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "action", DecisionAction(self.action))
        if self.expected_value is not None:
            value = float(self.expected_value)
            if not isfinite(value):
                raise ValueError("expected_value must be finite")
            object.__setattr__(self, "expected_value", value)
        object.__setattr__(self, "rationale", tuple(self.rationale))


@dataclass(frozen=True)
class MatchContext:
    session: AnalysisSession
    match: MatchInfo
    home_team: TeamInfo
    away_team: TeamInfo
    schema_version: str = SCHEMA_VERSION
    lineups: Mapping[str, Any] = field(default_factory=dict)
    injuries: Mapping[str, Any] = field(default_factory=dict)
    market: Mapping[str, Any] = field(default_factory=dict)
    weather: Mapping[str, Any] = field(default_factory=dict)
    schedule: Mapping[str, Any] = field(default_factory=dict)
    tactical: Mapping[str, Any] = field(default_factory=dict)
    evidence: EvidenceOutput | None = None
    rule_outputs: tuple[Mapping[str, Any], ...] = ()
    model_outputs: tuple[ModelOutput, ...] = ()
    confidence: ConfidenceOutput | None = None
    consensus: Mapping[str, Any] | None = None
    decision: DecisionOutput | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _require_text(self.schema_version, "schema_version"))
        if self.schema_version != self.session.schema_version:
            raise ValueError("MatchContext and AnalysisSession schema versions must agree")
        if self.home_team.team_id == self.away_team.team_id:
            raise ValueError("home_team and away_team must be different")
        for name in ("lineups", "injuries", "market", "weather", "schedule", "tactical"):
            object.__setattr__(self, name, _freeze_mapping(getattr(self, name)))
        object.__setattr__(self, "rule_outputs", tuple(_freeze_mapping(item) for item in self.rule_outputs))
        object.__setattr__(self, "model_outputs", tuple(self.model_outputs))
        if self.consensus is not None:
            object.__setattr__(self, "consensus", _freeze_mapping(self.consensus))
        if self.evidence is not None and self.evidence.gate is EvidenceGate.REJECTED:
            if self.decision is not None and self.decision.action is not DecisionAction.NO_DECISION:
                raise ValueError("Rejected evidence cannot produce an active decision")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible dictionary without mutating domain objects."""

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
            raise TypeError("MatchContext serialization did not produce an object")
        return result

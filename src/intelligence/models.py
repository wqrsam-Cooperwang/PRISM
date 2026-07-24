"""Immutable domain models for the PRISM automated match intelligence layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite
from typing import Any

INTELLIGENCE_SCHEMA_VERSION = "1.0.0"


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


def _unit_interval(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")
    result = float(value)
    if not isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{field_name} must be finite and between 0 and 1")
    return result


def _validate_json_value(value: Any, field_name: str = "value") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(f"{field_name} must not contain NaN or infinity")
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _validate_json_value(item, field_name)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{field_name} mapping keys must be strings")
            _validate_json_value(item, field_name)
        return
    raise ValueError(f"{field_name} must be JSON-compatible")


class IntelligenceCategory(str, Enum):
    IDENTITY = "identity"
    TEAM_STRENGTH = "team_strength"
    RECENT_FORM = "recent_form"
    AVAILABILITY = "availability"
    SCHEDULE = "schedule"
    MARKET = "market"
    LINEUP = "lineup"
    WEATHER = "weather"
    TACTICAL = "tactical"
    HEAD_TO_HEAD = "head_to_head"
    MOTIVATION_CONTEXT = "motivation_context"


class SourceType(str, Enum):
    OFFICIAL = "official"
    PRIMARY_DATA = "primary_data"
    MARKET = "market"
    REPUTABLE_MEDIA = "reputable_media"
    SPECIALIST = "specialist"
    AGGREGATOR = "aggregator"
    COMMUNITY = "community"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    PROVISIONAL = "provisional"
    CONFLICTED = "conflicted"
    UNSUPPORTED = "unsupported"


class ReadinessLevel(str, Enum):
    DEEP = "deep"
    STANDARD = "standard"
    LIMITED = "limited"
    REJECTED = "rejected"


@dataclass(frozen=True)
class MatchTarget:
    match_id: str
    competition: str
    kickoff: datetime
    home_team_id: str
    home_team_name: str
    away_team_id: str
    away_team_name: str
    season: str | None = None
    stage: str | None = None
    venue: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "match_id",
            "competition",
            "home_team_id",
            "home_team_name",
            "away_team_id",
            "away_team_name",
        ):
            object.__setattr__(self, name, _require_text(getattr(self, name), name))
        object.__setattr__(self, "kickoff", _require_aware_datetime(self.kickoff, "kickoff"))
        if self.home_team_id == self.away_team_id:
            raise ValueError("home_team_id and away_team_id must differ")


@dataclass(frozen=True)
class SourceRef:
    source_id: str
    source_type: SourceType
    uri: str | None = None
    publisher: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _require_text(self.source_id, "source_id"))
        object.__setattr__(self, "source_type", SourceType(self.source_type))
        if self.uri is not None:
            object.__setattr__(self, "uri", _require_text(self.uri, "uri"))
        if self.publisher is not None:
            object.__setattr__(self, "publisher", _require_text(self.publisher, "publisher"))


@dataclass(frozen=True)
class Observation:
    observation_id: str
    category: IntelligenceCategory
    claim_key: str
    value: Any
    source: SourceRef
    observed_at: datetime
    collected_at: datetime
    subject: str | None = None
    confidence: float | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "observation_id", _require_text(self.observation_id, "observation_id")
        )
        object.__setattr__(self, "category", IntelligenceCategory(self.category))
        object.__setattr__(self, "claim_key", _require_text(self.claim_key, "claim_key"))
        _validate_json_value(self.value)
        object.__setattr__(
            self, "observed_at", _require_aware_datetime(self.observed_at, "observed_at")
        )
        object.__setattr__(
            self, "collected_at", _require_aware_datetime(self.collected_at, "collected_at")
        )
        if self.observed_at > self.collected_at:
            raise ValueError("observed_at cannot be after collected_at")
        if self.subject is not None:
            object.__setattr__(self, "subject", _require_text(self.subject, "subject"))
        if self.confidence is not None:
            object.__setattr__(self, "confidence", _unit_interval(self.confidence, "confidence"))
        if self.notes is not None:
            object.__setattr__(self, "notes", _require_text(self.notes, "notes"))


@dataclass(frozen=True)
class VerifiedClaim:
    category: IntelligenceCategory
    claim_key: str
    value: Any
    status: VerificationStatus
    confidence: float
    supporting_observation_ids: tuple[str, ...]
    conflicting_observation_ids: tuple[str, ...]
    latest_source_at: datetime
    subject: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "category", IntelligenceCategory(self.category))
        object.__setattr__(self, "claim_key", _require_text(self.claim_key, "claim_key"))
        if self.value is not None:
            _validate_json_value(self.value)
        object.__setattr__(self, "status", VerificationStatus(self.status))
        object.__setattr__(self, "confidence", _unit_interval(self.confidence, "confidence"))
        object.__setattr__(
            self,
            "supporting_observation_ids",
            tuple(_require_text(item, "observation_id") for item in self.supporting_observation_ids),
        )
        object.__setattr__(
            self,
            "conflicting_observation_ids",
            tuple(_require_text(item, "observation_id") for item in self.conflicting_observation_ids),
        )
        object.__setattr__(
            self,
            "latest_source_at",
            _require_aware_datetime(self.latest_source_at, "latest_source_at"),
        )
        if self.subject is not None:
            object.__setattr__(self, "subject", _require_text(self.subject, "subject"))


@dataclass(frozen=True)
class CategoryAssessment:
    category: IntelligenceCategory
    covered: bool
    score: float
    verified_claims: int
    provisional_claims: int
    conflicted_claims: int
    stale: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "category", IntelligenceCategory(self.category))
        object.__setattr__(self, "score", _unit_interval(self.score, "score"))
        for name in ("verified_claims", "provisional_claims", "conflicted_claims"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")


@dataclass(frozen=True)
class IntelligenceReadiness:
    level: ReadinessLevel
    score: float
    missing_required_categories: tuple[IntelligenceCategory, ...] = ()
    stale_categories: tuple[IntelligenceCategory, ...] = ()
    conflicted_claim_keys: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "level", ReadinessLevel(self.level))
        object.__setattr__(self, "score", _unit_interval(self.score, "score"))
        object.__setattr__(
            self,
            "missing_required_categories",
            tuple(IntelligenceCategory(item) for item in self.missing_required_categories),
        )
        object.__setattr__(
            self,
            "stale_categories",
            tuple(IntelligenceCategory(item) for item in self.stale_categories),
        )
        object.__setattr__(self, "conflicted_claim_keys", tuple(self.conflicted_claim_keys))
        object.__setattr__(self, "warnings", tuple(self.warnings))


@dataclass(frozen=True)
class IntelligenceBundle:
    target: MatchTarget
    collected_at: datetime
    observations: tuple[Observation, ...]
    claims: tuple[VerifiedClaim, ...]
    category_assessments: tuple[CategoryAssessment, ...]
    readiness: IntelligenceReadiness
    fingerprint: str
    schema_version: str = INTELLIGENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "collected_at", _require_aware_datetime(self.collected_at, "collected_at")
        )
        object.__setattr__(self, "observations", tuple(self.observations))
        object.__setattr__(self, "claims", tuple(self.claims))
        object.__setattr__(self, "category_assessments", tuple(self.category_assessments))
        object.__setattr__(self, "fingerprint", _require_text(self.fingerprint, "fingerprint"))
        object.__setattr__(
            self, "schema_version", _require_text(self.schema_version, "schema_version")
        )

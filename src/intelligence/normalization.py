"""Normalize verified match intelligence into existing PRISM runtime inputs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Any

from src.domain.models import ModelOutput
from src.intelligence.models import (
    IntelligenceBundle,
    IntelligenceCategory,
    ReadinessLevel,
    VerificationStatus,
    VerifiedClaim,
)
from src.runtime.request import MatchRequest

_USABLE_STATUSES = {VerificationStatus.VERIFIED, VerificationStatus.PROVISIONAL}

_CONTEXT_CATEGORY_FIELDS: Mapping[IntelligenceCategory, str] = MappingProxyType(
    {
        IntelligenceCategory.LINEUP: "lineups",
        IntelligenceCategory.AVAILABILITY: "injuries",
        IntelligenceCategory.MARKET: "market",
        IntelligenceCategory.WEATHER: "weather",
        IntelligenceCategory.SCHEDULE: "schedule",
        IntelligenceCategory.TACTICAL: "tactical",
    }
)


def _freeze_feature_data(
    value: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Mapping[str, Any]]:
    return MappingProxyType(
        {category: MappingProxyType(dict(values)) for category, values in value.items()}
    )


@dataclass(frozen=True)
class NormalizedIntelligenceFacts:
    """Pre-model normalized intelligence used to construct deterministic features."""

    evidence_completeness: Mapping[str, float]
    model_feature_data: Mapping[str, Mapping[str, Any]]
    intelligence_fingerprint: str
    readiness: ReadinessLevel

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "evidence_completeness",
            MappingProxyType(dict(self.evidence_completeness)),
        )
        object.__setattr__(
            self,
            "model_feature_data",
            _freeze_feature_data(self.model_feature_data),
        )
        object.__setattr__(self, "readiness", ReadinessLevel(self.readiness))


@dataclass(frozen=True)
class NormalizedMatchInput:
    """Bridge object consumed by the existing context builder and runtime factory."""

    request: MatchRequest
    evidence_completeness: Mapping[str, float]
    model_feature_data: Mapping[str, Mapping[str, Any]]
    intelligence_fingerprint: str
    readiness: ReadinessLevel

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "evidence_completeness",
            MappingProxyType(dict(self.evidence_completeness)),
        )
        object.__setattr__(
            self,
            "model_feature_data",
            _freeze_feature_data(self.model_feature_data),
        )
        object.__setattr__(self, "readiness", ReadinessLevel(self.readiness))


def _usable_claims(bundle: IntelligenceBundle) -> tuple[VerifiedClaim, ...]:
    return tuple(
        claim
        for claim in bundle.claims
        if claim.status in _USABLE_STATUSES and claim.value is not None
    )


def _insert_claim(target: dict[str, Any], claim: VerifiedClaim) -> None:
    if claim.subject is None:
        if claim.claim_key in target:
            raise ValueError(f"Duplicate normalized claim path: {claim.claim_key}")
        target[claim.claim_key] = claim.value
        return

    if claim.subject in target and not isinstance(target[claim.subject], dict):
        raise ValueError(f"Duplicate normalized claim path: {claim.subject}")
    subject_values = target.setdefault(claim.subject, {})
    if not isinstance(subject_values, dict):
        raise ValueError(f"Duplicate normalized claim path: {claim.subject}")
    if claim.claim_key in subject_values:
        raise ValueError(f"Duplicate normalized claim path: {claim.subject}.{claim.claim_key}")
    subject_values[claim.claim_key] = claim.value


def _category_payload(
    claims: tuple[VerifiedClaim, ...],
    category: IntelligenceCategory,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for claim in claims:
        if claim.category == category:
            _insert_claim(result, claim)
    return result


def _team_side(bundle: IntelligenceBundle, subject: str | None) -> str | None:
    if subject is None:
        return None
    target = bundle.target
    if subject in {"home", target.home_team_id, target.home_team_name}:
        return "home"
    if subject in {"away", target.away_team_id, target.away_team_name}:
        return "away"
    return None


def _elo_ratings(
    bundle: IntelligenceBundle,
    claims: tuple[VerifiedClaim, ...],
) -> tuple[float | None, float | None]:
    home: float | None = None
    away: float | None = None
    for claim in claims:
        if claim.category != IntelligenceCategory.TEAM_STRENGTH or claim.claim_key != "elo_rating":
            continue
        if isinstance(claim.value, bool) or not isinstance(claim.value, (int, float)):
            raise ValueError("elo_rating must be a finite numeric value")
        value = float(claim.value)
        if not isfinite(value):
            raise ValueError("elo_rating must be a finite numeric value")
        side = _team_side(bundle, claim.subject)
        if side == "home":
            if home is not None:
                raise ValueError("Duplicate normalized home elo_rating")
            home = value
        elif side == "away":
            if away is not None:
                raise ValueError("Duplicate normalized away elo_rating")
            away = value
    return home, away


def _assessment_scores(bundle: IntelligenceBundle) -> dict[IntelligenceCategory, float]:
    return {assessment.category: assessment.score for assessment in bundle.category_assessments}


def _evidence_completeness(bundle: IntelligenceBundle) -> dict[str, float]:
    scores = _assessment_scores(bundle)
    historical = (
        scores[IntelligenceCategory.TEAM_STRENGTH]
        + scores[IntelligenceCategory.RECENT_FORM]
        + scores[IntelligenceCategory.HEAD_TO_HEAD]
    ) / 3.0
    return {
        "lineup": scores[IntelligenceCategory.LINEUP],
        "injuries": scores[IntelligenceCategory.AVAILABILITY],
        "odds": scores[IntelligenceCategory.MARKET],
        "weather": scores[IntelligenceCategory.WEATHER],
        "tactical_data": scores[IntelligenceCategory.TACTICAL],
        "historical_data": historical,
        "market_data": scores[IntelligenceCategory.MARKET],
        "motivation": scores[IntelligenceCategory.MOTIVATION_CONTEXT],
    }


def normalize_intelligence_facts(bundle: IntelligenceBundle) -> NormalizedIntelligenceFacts:
    """Normalize verified intelligence for feature construction before model execution."""

    claims = _usable_claims(bundle)
    feature_data = {
        category.value: payload
        for category in IntelligenceCategory
        if (payload := _category_payload(claims, category))
    }
    return NormalizedIntelligenceFacts(
        evidence_completeness=_evidence_completeness(bundle),
        model_feature_data=feature_data,
        intelligence_fingerprint=bundle.fingerprint,
        readiness=bundle.readiness.level,
    )


def normalize_intelligence_bundle(
    bundle: IntelligenceBundle,
    model_outputs: tuple[ModelOutput, ...],
) -> NormalizedMatchInput:
    """Convert a verified intelligence snapshot into existing PRISM runtime inputs."""

    if not model_outputs:
        raise ValueError("Normalization requires at least one model output")

    facts = normalize_intelligence_facts(bundle)
    claims = _usable_claims(bundle)
    home_elo_rating, away_elo_rating = _elo_ratings(bundle, claims)
    context_payloads = {
        field_name: _category_payload(claims, category)
        for category, field_name in _CONTEXT_CATEGORY_FIELDS.items()
    }

    target = bundle.target
    request = MatchRequest(
        match_id=target.match_id,
        competition=target.competition,
        kickoff=target.kickoff,
        home_team_id=target.home_team_id,
        home_team_name=target.home_team_name,
        away_team_id=target.away_team_id,
        away_team_name=target.away_team_name,
        model_outputs=tuple(model_outputs),
        venue=target.venue,
        season=target.season,
        stage=target.stage,
        home_elo_rating=home_elo_rating,
        away_elo_rating=away_elo_rating,
        lineups=context_payloads["lineups"],
        injuries=context_payloads["injuries"],
        market=context_payloads["market"],
        weather=context_payloads["weather"],
        schedule=context_payloads["schedule"],
        tactical=context_payloads["tactical"],
    )
    return NormalizedMatchInput(
        request=request,
        evidence_completeness=facts.evidence_completeness,
        model_feature_data=facts.model_feature_data,
        intelligence_fingerprint=facts.intelligence_fingerprint,
        readiness=facts.readiness,
    )

"""Deterministic verification and readiness for PRISM match intelligence."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any

from src.intelligence.models import (
    CategoryAssessment,
    IntelligenceBundle,
    IntelligenceCategory,
    IntelligenceReadiness,
    MatchTarget,
    Observation,
    ReadinessLevel,
    SourceType,
    VerificationStatus,
    VerifiedClaim,
)

_REQUIRED_CATEGORIES = (
    IntelligenceCategory.IDENTITY,
    IntelligenceCategory.TEAM_STRENGTH,
    IntelligenceCategory.RECENT_FORM,
    IntelligenceCategory.AVAILABILITY,
    IntelligenceCategory.SCHEDULE,
    IntelligenceCategory.MARKET,
)

_MAX_AGE = {
    IntelligenceCategory.LINEUP: timedelta(hours=12),
    IntelligenceCategory.AVAILABILITY: timedelta(hours=72),
    IntelligenceCategory.MARKET: timedelta(hours=6),
    IntelligenceCategory.WEATHER: timedelta(hours=12),
    IntelligenceCategory.RECENT_FORM: timedelta(days=14),
    IntelligenceCategory.TEAM_STRENGTH: timedelta(days=14),
    IntelligenceCategory.SCHEDULE: timedelta(days=7),
    IntelligenceCategory.TACTICAL: timedelta(days=7),
    IntelligenceCategory.MOTIVATION_CONTEXT: timedelta(days=7),
    IntelligenceCategory.HEAD_TO_HEAD: timedelta(days=30),
    IntelligenceCategory.IDENTITY: timedelta(days=3650),
}

_SOURCE_WEIGHT = {
    SourceType.OFFICIAL: 1.00,
    SourceType.PRIMARY_DATA: 0.95,
    SourceType.MARKET: 0.90,
    SourceType.REPUTABLE_MEDIA: 0.80,
    SourceType.SPECIALIST: 0.75,
    SourceType.AGGREGATOR: 0.60,
    SourceType.COMMUNITY: 0.40,
}


def _canonical_value(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _freshness_factor(observation: Observation) -> tuple[float, bool]:
    maximum_age = _MAX_AGE[observation.category]
    age = observation.collected_at - observation.observed_at
    if age <= maximum_age:
        return 1.0, False
    if age <= maximum_age * 2:
        return 0.60, True
    return 0.25, True


def _category_source_cap(observation: Observation) -> float:
    source_type = observation.source.source_type
    category = observation.category
    if source_type == SourceType.MARKET and category != IntelligenceCategory.MARKET:
        return 0.55
    if source_type == SourceType.COMMUNITY:
        return 0.45
    if category == IntelligenceCategory.AVAILABILITY and source_type == SourceType.AGGREGATOR:
        return 0.65
    return 1.0


def _effective_weight(observation: Observation) -> tuple[float, bool]:
    freshness, stale = _freshness_factor(observation)
    provider_confidence = observation.confidence if observation.confidence is not None else 1.0
    authority = min(
        _SOURCE_WEIGHT[observation.source.source_type],
        _category_source_cap(observation),
    )
    return authority * freshness * provider_confidence, stale


def _verify_group(observations: tuple[Observation, ...]) -> VerifiedClaim:
    support: dict[str, float] = defaultdict(float)
    members: dict[str, list[Observation]] = defaultdict(list)
    total = 0.0
    for observation in observations:
        key = _canonical_value(observation.value)
        weight, _ = _effective_weight(observation)
        support[key] += weight
        members[key].append(observation)
        total += weight

    ranked = sorted(support.items(), key=lambda item: (-item[1], item[0]))
    winner_key, winner_weight = ranked[0]
    second_weight = ranked[1][1] if len(ranked) > 1 else 0.0
    share = winner_weight / total if total > 0 else 0.0
    conflict_ratio = second_weight / winner_weight if winner_weight > 0 else 1.0

    winner_members = tuple(sorted(members[winner_key], key=lambda item: item.observation_id))
    winner_ids = tuple(item.observation_id for item in winner_members)
    conflict_ids = tuple(
        sorted(
            item.observation_id
            for key, group_members in members.items()
            if key != winner_key
            for item in group_members
        )
    )
    latest_source_at = max(item.observed_at for item in observations)

    if total <= 0.0:
        status = VerificationStatus.UNSUPPORTED
        value: Any = None
        confidence = 0.0
    elif len(ranked) > 1 and conflict_ratio >= 0.70:
        status = VerificationStatus.CONFLICTED
        value = None
        confidence = max(0.0, min(1.0, share * (1.0 - conflict_ratio)))
    else:
        strongest_single = max(_effective_weight(item)[0] for item in winner_members)
        corroborated = len(winner_members) >= 2
        if share >= 0.67 and (corroborated or strongest_single >= 0.85):
            status = VerificationStatus.VERIFIED
        else:
            status = VerificationStatus.PROVISIONAL
        value = winner_members[0].value
        confidence = max(0.0, min(1.0, share * min(1.0, winner_weight)))

    first = observations[0]
    return VerifiedClaim(
        category=first.category,
        subject=first.subject,
        claim_key=first.claim_key,
        value=value,
        status=status,
        confidence=confidence,
        supporting_observation_ids=winner_ids,
        conflicting_observation_ids=conflict_ids,
        latest_source_at=latest_source_at,
    )


def verify_observations(
    observations: tuple[Observation, ...],
) -> tuple[VerifiedClaim, ...]:
    """Group and deterministically verify observations into auditable claims."""

    observation_ids = [item.observation_id for item in observations]
    if len(set(observation_ids)) != len(observation_ids):
        raise ValueError("observation_id values must be unique")

    grouped: dict[tuple[IntelligenceCategory, str | None, str], list[Observation]] = defaultdict(
        list
    )
    for observation in observations:
        grouped[(observation.category, observation.subject, observation.claim_key)].append(
            observation
        )

    claims = [
        _verify_group(tuple(sorted(group, key=lambda item: item.observation_id)))
        for _, group in sorted(
            grouped.items(),
            key=lambda item: (item[0][0].value, item[0][1] or "", item[0][2]),
        )
    ]
    return tuple(claims)


def _assess_categories(
    observations: tuple[Observation, ...],
    claims: tuple[VerifiedClaim, ...],
) -> tuple[CategoryAssessment, ...]:
    assessments: list[CategoryAssessment] = []
    for category in IntelligenceCategory:
        if category == IntelligenceCategory.IDENTITY:
            assessments.append(
                CategoryAssessment(category, True, 1.0, 1, 0, 0, False)
            )
            continue
        category_claims = tuple(item for item in claims if item.category == category)
        category_observations = tuple(
            item for item in observations if item.category == category
        )
        verified = sum(
            item.status == VerificationStatus.VERIFIED for item in category_claims
        )
        provisional = sum(
            item.status == VerificationStatus.PROVISIONAL for item in category_claims
        )
        conflicted = sum(
            item.status == VerificationStatus.CONFLICTED for item in category_claims
        )
        usable = tuple(
            item
            for item in category_claims
            if item.status
            in {VerificationStatus.VERIFIED, VerificationStatus.PROVISIONAL}
            and item.value is not None
        )
        covered = bool(usable)
        score = (
            sum(item.confidence for item in usable) / len(usable) if usable else 0.0
        )
        stale = bool(category_observations) and all(
            _freshness_factor(item)[1] for item in category_observations
        )
        if stale:
            score *= 0.6
        assessments.append(
            CategoryAssessment(
                category,
                covered,
                score,
                verified,
                provisional,
                conflicted,
                stale,
            )
        )
    return tuple(assessments)


def _readiness(
    assessments: tuple[CategoryAssessment, ...],
    claims: tuple[VerifiedClaim, ...],
) -> IntelligenceReadiness:
    by_category = {item.category: item for item in assessments}
    missing = tuple(
        category
        for category in _REQUIRED_CATEGORIES
        if not by_category[category].covered
    )
    stale = tuple(item.category for item in assessments if item.stale)
    conflicted = tuple(
        sorted(
            f"{item.category.value}:{item.subject or '-'}:{item.claim_key}"
            for item in claims
            if item.status == VerificationStatus.CONFLICTED
        )
    )
    required_scores = tuple(by_category[category].score for category in _REQUIRED_CATEGORIES)
    score = sum(required_scores) / len(required_scores)
    optional_covered = sum(
        item.covered for item in assessments if item.category not in _REQUIRED_CATEGORIES
    )
    warnings: list[str] = []
    if missing:
        warnings.append("missing required intelligence categories")
    if stale:
        warnings.append("one or more intelligence categories are stale")
    if conflicted:
        warnings.append("one or more claims have unresolved conflicts")

    non_identity_covered = sum(
        item.category != IntelligenceCategory.IDENTITY for item in assessments if item.covered
    )
    if non_identity_covered == 0:
        level = ReadinessLevel.REJECTED
    elif missing:
        level = ReadinessLevel.LIMITED
    elif (
        conflicted
        or stale
        or any(by_category[category].provisional_claims for category in _REQUIRED_CATEGORIES)
    ):
        level = ReadinessLevel.STANDARD
    elif optional_covered >= 3 and score >= 0.75:
        level = ReadinessLevel.DEEP
    else:
        level = ReadinessLevel.STANDARD

    return IntelligenceReadiness(
        level=level,
        score=score,
        missing_required_categories=missing,
        stale_categories=stale,
        conflicted_claim_keys=conflicted,
        warnings=tuple(warnings),
    )


def _fingerprint_payload(
    target: MatchTarget,
    observations: tuple[Observation, ...],
    claims: tuple[VerifiedClaim, ...],
) -> str:
    payload = {
        "target": asdict(target),
        "observations": [asdict(item) for item in observations],
        "claims": [asdict(item) for item in claims],
    }

    def default(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if hasattr(value, "value"):
            return value.value
        raise TypeError(f"Unsupported fingerprint value: {type(value)!r}")

    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=default,
    )


def build_intelligence_bundle(
    target: MatchTarget,
    observations: tuple[Observation, ...],
    *,
    collected_at: datetime,
) -> IntelligenceBundle:
    """Build a frozen, deterministic intelligence bundle from observations."""

    if collected_at.tzinfo is None or collected_at.utcoffset() is None:
        raise ValueError("collected_at must be timezone-aware")
    ordered_observations = tuple(sorted(observations, key=lambda item: item.observation_id))
    if any(item.collected_at > collected_at for item in ordered_observations):
        raise ValueError("bundle collected_at cannot precede observation collection")
    claims = verify_observations(ordered_observations)
    assessments = _assess_categories(ordered_observations, claims)
    readiness = _readiness(assessments, claims)
    payload = _fingerprint_payload(target, ordered_observations, claims)
    fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return IntelligenceBundle(
        target=target,
        collected_at=collected_at,
        observations=ordered_observations,
        claims=claims,
        category_assessments=assessments,
        readiness=readiness,
        fingerprint=fingerprint,
    )

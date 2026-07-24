from datetime import datetime, timedelta, timezone

import pytest

from src.intelligence import (
    IntelligenceCategory,
    MatchTarget,
    Observation,
    ReadinessLevel,
    SourceRef,
    SourceType,
    VerificationStatus,
    build_intelligence_bundle,
    verify_observations,
)

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
KICKOFF = datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc)


def _target() -> MatchTarget:
    return MatchTarget(
        match_id="match-001",
        competition="Test League",
        kickoff=KICKOFF,
        home_team_id="home",
        home_team_name="Home FC",
        away_team_id="away",
        away_team_name="Away FC",
    )


def _source(source_id: str, source_type: SourceType) -> SourceRef:
    return SourceRef(source_id=source_id, source_type=source_type)


def _observation(
    observation_id: str,
    category: IntelligenceCategory,
    claim_key: str,
    value: object,
    source_type: SourceType,
    *,
    subject: str | None = None,
    age: timedelta = timedelta(hours=1),
    confidence: float | None = None,
) -> Observation:
    return Observation(
        observation_id=observation_id,
        category=category,
        claim_key=claim_key,
        value=value,
        source=_source(f"source-{observation_id}", source_type),
        observed_at=NOW - age,
        collected_at=NOW,
        subject=subject,
        confidence=confidence,
    )


def _required_observations() -> tuple[Observation, ...]:
    return (
        _observation(
            "strength-home",
            IntelligenceCategory.TEAM_STRENGTH,
            "elo_rating",
            1560,
            SourceType.PRIMARY_DATA,
            subject="home",
        ),
        _observation(
            "form-home",
            IntelligenceCategory.RECENT_FORM,
            "points_last_5",
            10,
            SourceType.PRIMARY_DATA,
            subject="home",
        ),
        _observation(
            "availability-home",
            IntelligenceCategory.AVAILABILITY,
            "missing_starters",
            1,
            SourceType.OFFICIAL,
            subject="home",
        ),
        _observation(
            "schedule-home",
            IntelligenceCategory.SCHEDULE,
            "rest_days",
            6,
            SourceType.PRIMARY_DATA,
            subject="home",
        ),
        _observation(
            "market-home",
            IntelligenceCategory.MARKET,
            "home_decimal_odds",
            1.85,
            SourceType.MARKET,
        ),
    )


def test_match_target_rejects_naive_kickoff_and_same_team() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        MatchTarget(
            match_id="match-001",
            competition="Test League",
            kickoff=datetime(2026, 7, 25, 18, 0),
            home_team_id="home",
            home_team_name="Home FC",
            away_team_id="away",
            away_team_name="Away FC",
        )

    with pytest.raises(ValueError, match="must differ"):
        MatchTarget(
            match_id="match-001",
            competition="Test League",
            kickoff=KICKOFF,
            home_team_id="same",
            home_team_name="Home FC",
            away_team_id="same",
            away_team_name="Away FC",
        )


def test_observation_rejects_invalid_confidence_and_non_json_value() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        _observation(
            "bad-confidence",
            IntelligenceCategory.MARKET,
            "odds",
            2.0,
            SourceType.MARKET,
            confidence=1.2,
        )

    with pytest.raises(ValueError, match="JSON-compatible"):
        _observation(
            "bad-value",
            IntelligenceCategory.MARKET,
            "odds",
            {1, 2},
            SourceType.MARKET,
        )


def test_high_authority_corroboration_defeats_weak_conflict() -> None:
    observations = (
        _observation(
            "official",
            IntelligenceCategory.AVAILABILITY,
            "striker_available",
            True,
            SourceType.OFFICIAL,
            subject="home",
        ),
        _observation(
            "primary",
            IntelligenceCategory.AVAILABILITY,
            "striker_available",
            True,
            SourceType.PRIMARY_DATA,
            subject="home",
        ),
        _observation(
            "community",
            IntelligenceCategory.AVAILABILITY,
            "striker_available",
            False,
            SourceType.COMMUNITY,
            subject="home",
        ),
    )

    claim = verify_observations(observations)[0]

    assert claim.status == VerificationStatus.VERIFIED
    assert claim.value is True
    assert claim.supporting_observation_ids == ("official", "primary")
    assert claim.conflicting_observation_ids == ("community",)


def test_close_strong_conflict_remains_unresolved() -> None:
    observations = (
        _observation(
            "official",
            IntelligenceCategory.LINEUP,
            "formation",
            "4-3-3",
            SourceType.OFFICIAL,
            subject="home",
        ),
        _observation(
            "primary",
            IntelligenceCategory.LINEUP,
            "formation",
            "3-4-2-1",
            SourceType.PRIMARY_DATA,
            subject="home",
        ),
    )

    claim = verify_observations(observations)[0]

    assert claim.status == VerificationStatus.CONFLICTED
    assert claim.value is None
    assert set(claim.supporting_observation_ids) | set(claim.conflicting_observation_ids) == {
        "official",
        "primary",
    }


def test_missing_required_category_downgrades_readiness_without_defaults() -> None:
    observations = tuple(
        item for item in _required_observations() if item.category != IntelligenceCategory.MARKET
    )

    bundle = build_intelligence_bundle(_target(), observations, collected_at=NOW)

    assert bundle.readiness.level == ReadinessLevel.LIMITED
    assert IntelligenceCategory.MARKET in bundle.readiness.missing_required_categories
    assert not any(claim.category == IntelligenceCategory.MARKET for claim in bundle.claims)


def test_stale_required_category_is_retained_and_penalized() -> None:
    observations = tuple(
        _observation(
            item.observation_id,
            item.category,
            item.claim_key,
            item.value,
            item.source.source_type,
            subject=item.subject,
            age=timedelta(hours=13)
            if item.category == IntelligenceCategory.MARKET
            else timedelta(hours=1),
        )
        for item in _required_observations()
    )

    bundle = build_intelligence_bundle(_target(), observations, collected_at=NOW)
    market = next(
        assessment
        for assessment in bundle.category_assessments
        if assessment.category == IntelligenceCategory.MARKET
    )

    assert market.covered is True
    assert market.stale is True
    assert IntelligenceCategory.MARKET in bundle.readiness.stale_categories
    assert bundle.readiness.level == ReadinessLevel.STANDARD


def test_only_identity_quality_rejects_bundle() -> None:
    bundle = build_intelligence_bundle(_target(), (), collected_at=NOW)

    assert bundle.readiness.level == ReadinessLevel.REJECTED
    assert IntelligenceCategory.TEAM_STRENGTH in bundle.readiness.missing_required_categories


def test_equivalent_input_order_produces_same_fingerprint() -> None:
    observations = _required_observations()

    first = build_intelligence_bundle(_target(), observations, collected_at=NOW)
    second = build_intelligence_bundle(_target(), tuple(reversed(observations)), collected_at=NOW)

    assert first.fingerprint == second.fingerprint
    assert first.claims == second.claims


def test_changed_fact_changes_fingerprint() -> None:
    observations = _required_observations()
    changed = tuple(
        _observation(
            item.observation_id,
            item.category,
            item.claim_key,
            1.95 if item.category == IntelligenceCategory.MARKET else item.value,
            item.source.source_type,
            subject=item.subject,
        )
        for item in observations
    )

    first = build_intelligence_bundle(_target(), observations, collected_at=NOW)
    second = build_intelligence_bundle(_target(), changed, collected_at=NOW)

    assert first.fingerprint != second.fingerprint

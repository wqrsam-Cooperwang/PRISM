from datetime import datetime, timedelta, timezone

from src.collection import CollectionGateDecision, evaluate_collection_readiness
from src.intelligence import (
    IntelligenceCategory,
    MatchTarget,
    Observation,
    SourceRef,
    SourceType,
    build_intelligence_bundle,
)

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
KICKOFF = datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc)


def _target() -> MatchTarget:
    return MatchTarget(
        match_id="readiness-001",
        competition="Test League",
        kickoff=KICKOFF,
        home_team_id="home-id",
        home_team_name="Home FC",
        away_team_id="away-id",
        away_team_name="Away FC",
    )


def _observation(
    observation_id: str,
    category: IntelligenceCategory,
    claim_key: str,
    value: object,
    source_id: str,
    source_type: SourceType,
    *,
    subject: str | None = None,
) -> Observation:
    return Observation(
        observation_id=observation_id,
        category=category,
        claim_key=claim_key,
        value=value,
        source=SourceRef(source_id=source_id, source_type=source_type),
        observed_at=NOW - timedelta(hours=1),
        collected_at=NOW,
        subject=subject,
    )


def _core_observations() -> tuple[Observation, ...]:
    return (
        _observation(
            "elo-home",
            IntelligenceCategory.TEAM_STRENGTH,
            "elo_rating",
            1620,
            "strength-provider",
            SourceType.PRIMARY_DATA,
            subject="home",
        ),
        _observation(
            "elo-away",
            IntelligenceCategory.TEAM_STRENGTH,
            "elo_rating",
            1540,
            "strength-provider",
            SourceType.PRIMARY_DATA,
            subject="away",
        ),
        _observation(
            "form-home",
            IntelligenceCategory.RECENT_FORM,
            "points_last_5",
            11,
            "strength-provider",
            SourceType.PRIMARY_DATA,
            subject="home",
        ),
        _observation(
            "form-away",
            IntelligenceCategory.RECENT_FORM,
            "points_last_5",
            6,
            "strength-provider",
            SourceType.PRIMARY_DATA,
            subject="away",
        ),
        _observation(
            "availability-home",
            IntelligenceCategory.AVAILABILITY,
            "missing_starters",
            1,
            "official-provider",
            SourceType.OFFICIAL,
            subject="home",
        ),
        _observation(
            "availability-away",
            IntelligenceCategory.AVAILABILITY,
            "missing_starters",
            3,
            "official-provider",
            SourceType.OFFICIAL,
            subject="away",
        ),
        _observation(
            "schedule-home",
            IntelligenceCategory.SCHEDULE,
            "rest_days",
            6,
            "official-provider",
            SourceType.OFFICIAL,
            subject="home",
        ),
        _observation(
            "schedule-away",
            IntelligenceCategory.SCHEDULE,
            "rest_days",
            4,
            "official-provider",
            SourceType.OFFICIAL,
            subject="away",
        ),
        _observation(
            "market-home",
            IntelligenceCategory.MARKET,
            "home_decimal_odds",
            1.95,
            "market-provider",
            SourceType.MARKET,
        ),
        _observation(
            "market-draw",
            IntelligenceCategory.MARKET,
            "draw_decimal_odds",
            3.4,
            "market-provider",
            SourceType.MARKET,
        ),
        _observation(
            "market-away",
            IntelligenceCategory.MARKET,
            "away_decimal_odds",
            4.2,
            "market-provider",
            SourceType.MARKET,
        ),
    )


def _bundle(observations: tuple[Observation, ...]):
    return build_intelligence_bundle(_target(), observations, collected_at=NOW)


def test_gate_marks_complete_core_collection_ready() -> None:
    result = evaluate_collection_readiness(_bundle(_core_observations()))

    assert result.decision == CollectionGateDecision.READY
    assert result.missing_core_categories == ()
    assert result.elo_baseline_available is True
    assert result.market_baseline_available is True
    assert result.reasons == ()


def test_gate_marks_baseline_capable_incomplete_collection_degraded() -> None:
    observations = tuple(
        item
        for item in _core_observations()
        if item.category
        not in {
            IntelligenceCategory.RECENT_FORM,
            IntelligenceCategory.AVAILABILITY,
            IntelligenceCategory.SCHEDULE,
        }
    )

    result = evaluate_collection_readiness(_bundle(observations))

    assert result.decision == CollectionGateDecision.DEGRADED
    assert result.elo_baseline_available is True
    assert result.market_baseline_available is True
    assert set(result.missing_core_categories) == {
        IntelligenceCategory.RECENT_FORM,
        IntelligenceCategory.AVAILABILITY,
        IntelligenceCategory.SCHEDULE,
    }
    assert "intelligence readiness is limited" in result.reasons


def test_gate_rejects_partial_market_even_when_market_category_is_covered() -> None:
    observations = tuple(
        item for item in _core_observations() if item.claim_key != "away_decimal_odds"
    )

    result = evaluate_collection_readiness(_bundle(observations))

    assert result.decision == CollectionGateDecision.REJECTED
    assert result.market_baseline_available is False
    assert "market baseline inputs are unavailable" in result.reasons


def test_gate_rejects_one_sided_elo_even_when_strength_category_is_covered() -> None:
    observations = tuple(item for item in _core_observations() if item.observation_id != "elo-away")

    result = evaluate_collection_readiness(_bundle(observations))

    assert result.decision == CollectionGateDecision.REJECTED
    assert result.elo_baseline_available is False
    assert "elo baseline inputs are unavailable" in result.reasons


def test_source_coverage_metadata_is_deterministic() -> None:
    first = evaluate_collection_readiness(_bundle(_core_observations()))
    second = evaluate_collection_readiness(_bundle(tuple(reversed(_core_observations()))))

    assert first.source_ids == (
        "market-provider",
        "official-provider",
        "strength-provider",
    )
    assert first.source_types == ("market", "official", "primary_data")
    assert first == second

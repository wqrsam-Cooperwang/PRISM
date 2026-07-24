from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from src.domain.models import ModelOutput
from src.intelligence import (
    IntelligenceCategory,
    Observation,
    SourceRef,
    SourceType,
    build_intelligence_bundle,
)
from src.intelligence.normalization import normalize_intelligence_bundle
from src.runtime.request import build_match_context

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
KICKOFF = datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc)


def _target():
    from src.intelligence import MatchTarget

    return MatchTarget(
        match_id="match-normalize-001",
        competition="Test League",
        kickoff=KICKOFF,
        home_team_id="home-id",
        home_team_name="Home FC",
        away_team_id="away-id",
        away_team_name="Away FC",
        season="2026",
        stage="Round 10",
        venue="Test Ground",
    )


def _model_outputs() -> tuple[ModelOutput, ...]:
    return (
        ModelOutput(
            model_id="test-model",
            model_version="1.0.0",
            home_probability=0.5,
            draw_probability=0.3,
            away_probability=0.2,
        ),
    )


def _observation(
    observation_id: str,
    category: IntelligenceCategory,
    claim_key: str,
    value: object,
    source_type: SourceType,
    *,
    subject: str | None = None,
) -> Observation:
    return Observation(
        observation_id=observation_id,
        category=category,
        claim_key=claim_key,
        value=value,
        source=SourceRef(
            source_id=f"source-{observation_id}",
            source_type=source_type,
        ),
        observed_at=NOW - timedelta(hours=1),
        collected_at=NOW,
        subject=subject,
    )


def _full_observations() -> tuple[Observation, ...]:
    return (
        _observation(
            "strength-home",
            IntelligenceCategory.TEAM_STRENGTH,
            "elo_rating",
            1610,
            SourceType.PRIMARY_DATA,
            subject="home",
        ),
        _observation(
            "strength-away",
            IntelligenceCategory.TEAM_STRENGTH,
            "elo_rating",
            1540,
            SourceType.PRIMARY_DATA,
            subject="away",
        ),
        _observation(
            "form-home",
            IntelligenceCategory.RECENT_FORM,
            "points_last_5",
            11,
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
            "market",
            IntelligenceCategory.MARKET,
            "home_decimal_odds",
            1.9,
            SourceType.MARKET,
        ),
        _observation(
            "lineup-home",
            IntelligenceCategory.LINEUP,
            "formation",
            "4-3-3",
            SourceType.OFFICIAL,
            subject="home",
        ),
        _observation(
            "weather",
            IntelligenceCategory.WEATHER,
            "temperature_c",
            18,
            SourceType.OFFICIAL,
        ),
        _observation(
            "tactical-home",
            IntelligenceCategory.TACTICAL,
            "pressing_style",
            "high",
            SourceType.OFFICIAL,
            subject="home",
        ),
        _observation(
            "h2h",
            IntelligenceCategory.HEAD_TO_HEAD,
            "meetings_last_5",
            5,
            SourceType.PRIMARY_DATA,
        ),
        _observation(
            "motivation-home",
            IntelligenceCategory.MOTIVATION_CONTEXT,
            "relegation_pressure",
            False,
            SourceType.OFFICIAL,
            subject="home",
        ),
    )


def test_normalization_maps_verified_intelligence_to_existing_runtime_inputs() -> None:
    bundle = build_intelligence_bundle(_target(), _full_observations(), collected_at=NOW)

    normalized = normalize_intelligence_bundle(bundle, _model_outputs())
    request = normalized.request

    assert request.home_elo_rating == 1610.0
    assert request.away_elo_rating == 1540.0
    assert request.lineups == {"home": {"formation": "4-3-3"}}
    assert request.injuries == {"home": {"missing_starters": 1}}
    assert request.market == {"home_decimal_odds": 1.9}
    assert request.weather == {"temperature_c": 18}
    assert request.schedule == {"home": {"rest_days": 6}}
    assert request.tactical == {"home": {"pressing_style": "high"}}
    assert normalized.intelligence_fingerprint == bundle.fingerprint
    assert normalized.readiness == bundle.readiness.level

    context = build_match_context(
        request,
        prism_version="test",
        session_id="normalization-test",
        created_at=NOW,
    )
    assert context.match.match_id == bundle.target.match_id
    assert context.home_team.elo_rating == 1610.0
    assert context.market["home_decimal_odds"] == 1.9


def test_all_usable_categories_remain_available_for_model_features() -> None:
    bundle = build_intelligence_bundle(_target(), _full_observations(), collected_at=NOW)

    normalized = normalize_intelligence_bundle(bundle, _model_outputs())

    assert normalized.model_feature_data["recent_form"] == {
        "home": {"points_last_5": 11}
    }
    assert normalized.model_feature_data["head_to_head"] == {"meetings_last_5": 5}
    assert normalized.model_feature_data["motivation_context"] == {
        "home": {"relegation_pressure": False}
    }


def test_evidence_completeness_translates_existing_evidence_contract() -> None:
    bundle = build_intelligence_bundle(_target(), _full_observations(), collected_at=NOW)

    completeness = normalize_intelligence_bundle(bundle, _model_outputs()).evidence_completeness

    assert completeness["lineup"] == pytest.approx(1.0)
    assert completeness["injuries"] == pytest.approx(1.0)
    assert completeness["odds"] == pytest.approx(0.9)
    assert completeness["market_data"] == pytest.approx(0.9)
    assert completeness["weather"] == pytest.approx(1.0)
    assert completeness["tactical_data"] == pytest.approx(1.0)
    assert completeness["motivation"] == pytest.approx(1.0)
    assert completeness["historical_data"] == pytest.approx((0.95 + 0.95 + 0.95) / 3)


def test_conflicted_claim_does_not_enter_runtime_facts() -> None:
    observations = _full_observations() + (
        _observation(
            "availability-conflict",
            IntelligenceCategory.AVAILABILITY,
            "missing_starters",
            2,
            SourceType.PRIMARY_DATA,
            subject="home",
        ),
    )
    bundle = build_intelligence_bundle(_target(), observations, collected_at=NOW)

    normalized = normalize_intelligence_bundle(bundle, _model_outputs())

    assert normalized.request.injuries == {}
    assert "availability" not in normalized.model_feature_data


def test_missing_category_stays_missing_without_defaults() -> None:
    observations = tuple(
        item for item in _full_observations() if item.category != IntelligenceCategory.WEATHER
    )
    bundle = build_intelligence_bundle(_target(), observations, collected_at=NOW)

    normalized = normalize_intelligence_bundle(bundle, _model_outputs())

    assert normalized.request.weather == {}
    assert "weather" not in normalized.model_feature_data
    assert normalized.evidence_completeness["weather"] == 0.0


def test_invalid_usable_elo_fails_closed() -> None:
    observations = tuple(
        item
        for item in _full_observations()
        if not (
            item.category == IntelligenceCategory.TEAM_STRENGTH
            and item.subject == "home"
        )
    ) + (
        _observation(
            "bad-elo",
            IntelligenceCategory.TEAM_STRENGTH,
            "elo_rating",
            "high",
            SourceType.OFFICIAL,
            subject="home",
        ),
    )
    bundle = build_intelligence_bundle(_target(), observations, collected_at=NOW)

    with pytest.raises(ValueError, match="elo_rating"):
        normalize_intelligence_bundle(bundle, _model_outputs())


def test_normalization_requires_prediction_model_output() -> None:
    bundle = build_intelligence_bundle(_target(), _full_observations(), collected_at=NOW)

    with pytest.raises(ValueError, match="at least one model output"):
        normalize_intelligence_bundle(bundle, ())


def test_duplicate_normalized_path_fails_closed() -> None:
    bundle = build_intelligence_bundle(_target(), _full_observations(), collected_at=NOW)
    lineup_claim = next(
        claim for claim in bundle.claims if claim.category == IntelligenceCategory.LINEUP
    )
    duplicated = replace(bundle, claims=bundle.claims + (lineup_claim,))

    with pytest.raises(ValueError, match="Duplicate normalized claim path"):
        normalize_intelligence_bundle(duplicated, _model_outputs())

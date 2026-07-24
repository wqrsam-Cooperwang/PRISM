from datetime import datetime, timedelta, timezone

import pytest

from src.intelligence import (
    IntelligenceCategory,
    MatchTarget,
    Observation,
    SourceRef,
    SourceType,
    build_intelligence_bundle,
)
from src.prediction import run_baseline_prediction_path

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
KICKOFF = datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc)


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
        source=SourceRef(source_id=f"source-{observation_id}", source_type=source_type),
        observed_at=NOW - timedelta(hours=1),
        collected_at=NOW,
        subject=subject,
    )


def _bundle():
    target = MatchTarget(
        match_id="e2e-match-001",
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
    observations = (
        _observation(
            "elo-home",
            IntelligenceCategory.TEAM_STRENGTH,
            "elo_rating",
            1620,
            SourceType.PRIMARY_DATA,
            subject="home",
        ),
        _observation(
            "elo-away",
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
            10,
            SourceType.PRIMARY_DATA,
            subject="home",
        ),
        _observation(
            "form-away",
            IntelligenceCategory.RECENT_FORM,
            "points_last_5",
            6,
            SourceType.PRIMARY_DATA,
            subject="away",
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
            "availability-away",
            IntelligenceCategory.AVAILABILITY,
            "missing_starters",
            2,
            SourceType.OFFICIAL,
            subject="away",
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
            "schedule-away",
            IntelligenceCategory.SCHEDULE,
            "rest_days",
            4,
            SourceType.PRIMARY_DATA,
            subject="away",
        ),
        _observation(
            "market-home",
            IntelligenceCategory.MARKET,
            "home_decimal_odds",
            1.95,
            SourceType.MARKET,
        ),
        _observation(
            "market-draw",
            IntelligenceCategory.MARKET,
            "draw_decimal_odds",
            3.40,
            SourceType.MARKET,
        ),
        _observation(
            "market-away",
            IntelligenceCategory.MARKET,
            "away_decimal_odds",
            4.10,
            SourceType.MARKET,
        ),
    )
    return build_intelligence_bundle(target, observations, collected_at=NOW)


def test_end_to_end_prediction_path_reaches_existing_consensus_engine() -> None:
    result = run_baseline_prediction_path(
        _bundle(),
        prism_version="test",
        session_id="e2e-session",
        created_at=NOW,
    )

    assert result.features.values["elo_difference"] == pytest.approx(80.0)
    assert tuple(output.model_id for output in result.model_outputs) == (
        "elo_probability",
        "market_probability",
    )
    assert result.context.consensus is not None
    assert result.context.consensus.model_ids == (
        "elo_probability",
        "market_probability",
    )
    total = (
        result.context.consensus.home_probability
        + result.context.consensus.draw_probability
        + result.context.consensus.away_probability
    )
    assert total == pytest.approx(1.0)
    for output in result.model_outputs:
        assert output.diagnostics["feature_fingerprint"] == result.features.fingerprint
        assert output.diagnostics["intelligence_fingerprint"] == _bundle().fingerprint


def test_end_to_end_prediction_path_is_deterministic_for_frozen_intelligence() -> None:
    bundle = _bundle()

    first = run_baseline_prediction_path(
        bundle,
        prism_version="test",
        session_id="e2e-session",
        created_at=NOW,
    )
    second = run_baseline_prediction_path(
        bundle,
        prism_version="test",
        session_id="e2e-session",
        created_at=NOW,
    )

    assert first.normalized_facts == second.normalized_facts
    assert first.features == second.features
    assert first.model_outputs == second.model_outputs
    assert first.context.consensus == second.context.consensus

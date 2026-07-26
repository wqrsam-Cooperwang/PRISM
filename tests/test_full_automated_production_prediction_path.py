from datetime import datetime, timezone

import pytest

from src.collection import (
    AvailabilityScheduleAdapter,
    FixtureObservationAdapter,
    MarketOdds1X2Adapter,
    SourceEnvelope,
    TeamStrengthFormAdapter,
    WeatherLineupAdapter,
)
from src.intelligence import MatchTarget, SourceRef, SourceType
from src.prediction import run_full_automated_prediction_path

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
KICKOFF = datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc)


def _target() -> MatchTarget:
    return MatchTarget(
        match_id="full-production-001",
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


def _ready_adapters():
    return (
        MarketOdds1X2Adapter(),
        TeamStrengthFormAdapter(),
        AvailabilityScheduleAdapter(),
        WeatherLineupAdapter(),
    )


def _market_envelope() -> SourceEnvelope:
    return SourceEnvelope(
        adapter_id="market_odds_1x2",
        source=SourceRef(source_id="market-provider", source_type=SourceType.MARKET),
        retrieved_at=NOW,
        payload={
            "observed_at": "2026-07-24T11:30:00+00:00",
            "home_team_id": "home-id",
            "away_team_id": "away-id",
            "home_decimal_odds": 1.95,
            "draw_decimal_odds": 3.4,
            "away_decimal_odds": 4.2,
        },
    )


def _strength_envelope() -> SourceEnvelope:
    return SourceEnvelope(
        adapter_id="team_strength_form",
        source=SourceRef(
            source_id="strength-provider",
            source_type=SourceType.PRIMARY_DATA,
        ),
        retrieved_at=NOW,
        payload={
            "observed_at": "2026-07-24T11:00:00+00:00",
            "home_team_id": "home-id",
            "away_team_id": "away-id",
            "home": {"elo_rating": 1620, "points_last_5": 11},
            "away": {"elo_rating": 1540, "points_last_5": 6},
        },
    )


def _availability_envelope() -> SourceEnvelope:
    return SourceEnvelope(
        adapter_id="availability_schedule",
        source=SourceRef(
            source_id="availability-provider",
            source_type=SourceType.OFFICIAL,
        ),
        retrieved_at=NOW,
        payload={
            "observed_at": "2026-07-24T10:45:00+00:00",
            "home_team_id": "home-id",
            "away_team_id": "away-id",
            "home": {"missing_starters": 1, "rest_days": 6},
            "away": {"missing_starters": 3, "rest_days": 4},
        },
    )


def _weather_envelope() -> SourceEnvelope:
    return SourceEnvelope(
        adapter_id="weather_lineup",
        source=SourceRef(
            source_id="weather-lineup-provider",
            source_type=SourceType.OFFICIAL,
        ),
        retrieved_at=NOW,
        payload={
            "observed_at": "2026-07-24T11:15:00+00:00",
            "home_team_id": "home-id",
            "away_team_id": "away-id",
            "weather": {"temperature_c": 18.5},
            "home": {"formation": "4-3-3"},
            "away": {"formation": "4-2-3-1"},
        },
    )


def _ready_envelopes() -> tuple[SourceEnvelope, ...]:
    return (
        _market_envelope(),
        _strength_envelope(),
        _availability_envelope(),
        _weather_envelope(),
    )


def test_ready_provider_inputs_run_through_final_report() -> None:
    result = run_full_automated_prediction_path(
        _target(),
        _ready_adapters(),
        _ready_envelopes(),
        collected_at=NOW,
        prism_version="test",
        session_id="full-production-test",
        created_at=NOW,
        git_commit="test-commit",
        data_version="fixture-v1",
    )

    assert result.collection_gate.decision.value == "ready"
    assert len(result.observations) == 14
    assert result.features.values["elo_difference"] == pytest.approx(80.0)

    runtime = result.runtime_result
    assert tuple(item.name for item in runtime.engine_trace) == (
        "evidence",
        "consensus",
        "confidence",
        "rules",
        "adjustment",
        "decision",
    )
    assert runtime.context.consensus is not None
    assert runtime.context.confidence is not None
    assert runtime.context.adjustment is not None
    assert runtime.context.decision is not None
    assert runtime.scoreline is not None

    report = result.report
    assert report.consensus is not None
    assert report.confidence is not None
    assert report.evidence is not None
    assert report.adjustment is not None
    assert report.decision is not None
    assert report.scoreline is not None
    assert report.provenance.git_commit == "test-commit"
    assert report.provenance.data_version == "fixture-v1"


def _degraded_envelope() -> SourceEnvelope:
    rows = (
        {
            "observation_id": "elo-home",
            "category": "team_strength",
            "subject": "home",
            "claim_key": "elo_rating",
            "value": 1620,
            "observed_at": "2026-07-24T11:00:00+00:00",
        },
        {
            "observation_id": "elo-away",
            "category": "team_strength",
            "subject": "away",
            "claim_key": "elo_rating",
            "value": 1540,
            "observed_at": "2026-07-24T11:00:00+00:00",
        },
    )
    return SourceEnvelope(
        adapter_id="fixture_observations",
        source=SourceRef(source_id="elo-fixture", source_type=SourceType.PRIMARY_DATA),
        retrieved_at=NOW,
        payload={"observations": rows},
    )


def test_degraded_collection_restriction_reaches_final_runtime_and_report() -> None:
    result = run_full_automated_prediction_path(
        _target(),
        (FixtureObservationAdapter(), MarketOdds1X2Adapter()),
        (_degraded_envelope(), _market_envelope()),
        collected_at=NOW,
        prism_version="test",
        session_id="degraded-production-test",
        created_at=NOW,
    )

    assert result.collection_gate.decision.value == "degraded"
    adjustment = result.runtime_result.context.adjustment
    assert adjustment is not None
    assert "restrict_high_confidence_action" in adjustment.observed_effects
    assert result.report.adjustment is not None
    assert "restrict_high_confidence_action" in result.report.adjustment.observed_effects


def test_rejected_collection_stops_before_runtime_and_report() -> None:
    with pytest.raises(ValueError, match="Collection readiness gate rejected prediction"):
        run_full_automated_prediction_path(
            _target(),
            (MarketOdds1X2Adapter(),),
            (_market_envelope(),),
            collected_at=NOW,
            prism_version="test",
            created_at=NOW,
        )

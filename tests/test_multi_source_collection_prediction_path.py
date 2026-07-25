from datetime import datetime, timezone

import pytest

from src.collection import (
    AvailabilityScheduleAdapter,
    MarketOdds1X2Adapter,
    SourceEnvelope,
    TeamStrengthFormAdapter,
    WeatherLineupAdapter,
)
from src.intelligence import MatchTarget, SourceRef, SourceType
from src.prediction import run_collected_prediction_path

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
KICKOFF = datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc)


def _target() -> MatchTarget:
    return MatchTarget(
        match_id="multi-source-001",
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


def _envelopes() -> tuple[SourceEnvelope, ...]:
    return (
        SourceEnvelope(
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
        ),
        SourceEnvelope(
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
        ),
        SourceEnvelope(
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
        ),
        SourceEnvelope(
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
        ),
    )


def _adapters():
    return (
        MarketOdds1X2Adapter(),
        TeamStrengthFormAdapter(),
        AvailabilityScheduleAdapter(),
        WeatherLineupAdapter(),
    )


def test_multi_source_collection_runs_to_consensus() -> None:
    result = run_collected_prediction_path(
        _target(),
        _adapters(),
        _envelopes(),
        collected_at=NOW,
        prism_version="test",
        session_id="multi-source-test",
        created_at=NOW,
    )

    assert len(result.observations) == 14
    assert result.intelligence_bundle.readiness.level.value in {"standard", "deep"}

    features = result.prediction.features.values
    assert features["elo_difference"] == pytest.approx(80.0)
    assert features["recent_points_difference"] == pytest.approx(5.0)
    assert features["missing_starters_difference"] == pytest.approx(-2.0)
    assert features["rest_days_difference"] == pytest.approx(2.0)
    assert features["temperature_c"] == pytest.approx(18.5)
    assert "market_home_implied_probability" in features
    assert "market_draw_implied_probability" in features
    assert "market_away_implied_probability" in features

    assert tuple(output.model_id for output in result.prediction.model_outputs) == (
        "elo_probability",
        "market_probability",
    )
    consensus = result.prediction.context.consensus
    assert consensus is not None
    total = consensus.home_probability + consensus.draw_probability + consensus.away_probability
    assert total == pytest.approx(1.0)


def test_multi_source_path_is_deterministic_across_envelope_order() -> None:
    target = _target()
    adapters = _adapters()
    envelopes = _envelopes()

    first = run_collected_prediction_path(
        target,
        adapters,
        envelopes,
        collected_at=NOW,
        prism_version="test",
        session_id="deterministic-test",
        created_at=NOW,
    )
    second = run_collected_prediction_path(
        target,
        reversed(adapters),
        reversed(envelopes),
        collected_at=NOW,
        prism_version="test",
        session_id="deterministic-test",
        created_at=NOW,
    )

    assert first.observations == second.observations
    assert first.intelligence_bundle.fingerprint == second.intelligence_bundle.fingerprint
    assert first.prediction.features.fingerprint == second.prediction.features.fingerprint
    assert first.prediction.model_outputs == second.prediction.model_outputs
    assert first.prediction.context.consensus == second.prediction.context.consensus


def test_collection_timestamp_cannot_precede_provider_retrieval() -> None:
    with pytest.raises(ValueError, match="cannot precede observation collection"):
        run_collected_prediction_path(
            _target(),
            _adapters(),
            _envelopes(),
            collected_at=datetime(2026, 7, 24, 11, 59, tzinfo=timezone.utc),
            prism_version="test",
            created_at=NOW,
        )

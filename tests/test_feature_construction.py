from datetime import datetime, timezone

import pytest

from src.domain.models import ModelOutput
from src.features import build_feature_vector
from src.intelligence import MatchTarget, ReadinessLevel
from src.intelligence.normalization import NormalizedMatchInput
from src.runtime.request import MatchRequest

KICKOFF = datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc)


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


def _request() -> MatchRequest:
    target = MatchTarget(
        match_id="feature-match-001",
        competition="Test League",
        kickoff=KICKOFF,
        home_team_id="home-id",
        home_team_name="Home FC",
        away_team_id="away-id",
        away_team_name="Away FC",
    )
    return MatchRequest(
        match_id=target.match_id,
        competition=target.competition,
        kickoff=target.kickoff,
        home_team_id=target.home_team_id,
        home_team_name=target.home_team_name,
        away_team_id=target.away_team_id,
        away_team_name=target.away_team_name,
        model_outputs=_model_outputs(),
    )


def _normalized(
    feature_data=None,
    *,
    evidence=None,
    fingerprint: str = "intelligence-fingerprint",
    readiness: ReadinessLevel = ReadinessLevel.DEEP,
) -> NormalizedMatchInput:
    if feature_data is None:
        feature_data = {
            "team_strength": {
                "home": {"elo_rating": 1610},
                "away": {"elo_rating": 1540},
            },
            "recent_form": {
                "home": {"points_last_5": 11},
                "away": {"points_last_5": 6},
            },
            "availability": {
                "home": {"missing_starters": 1},
                "away": {"missing_starters": 3},
            },
            "schedule": {
                "home": {"rest_days": 6},
                "away": {"rest_days": 4},
            },
            "market": {
                "home_decimal_odds": 1.9,
                "draw_decimal_odds": 3.5,
                "away_decimal_odds": 4.2,
            },
            "weather": {"temperature_c": 18},
        }
    if evidence is None:
        evidence = {
            "lineup": 1.0,
            "injuries": 0.9,
            "odds": 0.95,
            "weather": 0.8,
            "tactical_data": 0.7,
            "historical_data": 0.85,
            "market_data": 0.95,
            "motivation": 0.6,
        }
    return NormalizedMatchInput(
        request=_request(),
        evidence_completeness=evidence,
        model_feature_data=feature_data,
        intelligence_fingerprint=fingerprint,
        readiness=readiness,
    )


def test_builds_core_relative_and_market_features() -> None:
    vector = build_feature_vector(_normalized())

    assert vector.values["elo_difference"] == pytest.approx(70.0)
    assert vector.values["recent_points_difference"] == pytest.approx(5.0)
    assert vector.values["missing_starters_difference"] == pytest.approx(-2.0)
    assert vector.values["rest_days_difference"] == pytest.approx(2.0)
    assert vector.values["temperature_c"] == pytest.approx(18.0)

    home_raw = 1 / 1.9
    draw_raw = 1 / 3.5
    away_raw = 1 / 4.2
    total = home_raw + draw_raw + away_raw
    assert vector.values["market_home_implied_probability"] == pytest.approx(home_raw / total)
    assert vector.values["market_draw_implied_probability"] == pytest.approx(draw_raw / total)
    assert vector.values["market_away_implied_probability"] == pytest.approx(away_raw / total)
    assert vector.values["market_overround"] == pytest.approx(total - 1.0)
    assert vector.missing_features == ()


def test_quality_metadata_is_numeric_and_explicit() -> None:
    vector = build_feature_vector(_normalized(readiness=ReadinessLevel.STANDARD))

    assert vector.values["intelligence_readiness_score"] == pytest.approx(2 / 3)
    assert vector.values["evidence_lineup"] == pytest.approx(1.0)
    assert vector.values["evidence_historical_data"] == pytest.approx(0.85)


def test_missing_pair_does_not_become_zero_difference() -> None:
    data = {
        "team_strength": {"home": {"elo_rating": 1610}},
        "recent_form": {
            "home": {"points_last_5": 7},
            "away": {"points_last_5": 7},
        },
    }
    vector = build_feature_vector(_normalized(data))

    assert "elo_difference" not in vector.values
    assert "elo_difference" in vector.missing_features
    assert vector.values["recent_points_difference"] == 0.0
    assert "recent_points_difference" not in vector.missing_features


def test_partial_market_odds_produce_no_market_features() -> None:
    data = {
        "market": {
            "home_decimal_odds": 1.9,
            "draw_decimal_odds": 3.5,
        }
    }
    vector = build_feature_vector(_normalized(data))

    market_features = {
        "market_home_implied_probability",
        "market_draw_implied_probability",
        "market_away_implied_probability",
        "market_overround",
    }
    assert market_features.issubset(vector.missing_features)
    assert market_features.isdisjoint(vector.values)


def test_invalid_decimal_odds_fail_closed() -> None:
    data = {
        "market": {
            "home_decimal_odds": 1.0,
            "draw_decimal_odds": 3.5,
            "away_decimal_odds": 4.2,
        }
    }
    with pytest.raises(ValueError, match="greater than 1.0"):
        build_feature_vector(_normalized(data))


def test_boolean_numeric_fact_fails_closed() -> None:
    data = {
        "availability": {
            "home": {"missing_starters": True},
            "away": {"missing_starters": 1},
        }
    }
    with pytest.raises(ValueError, match="finite numeric value"):
        build_feature_vector(_normalized(data))


def test_feature_fingerprint_is_deterministic_and_tracks_intelligence() -> None:
    first = build_feature_vector(_normalized())
    reordered_data = {
        "weather": {"temperature_c": 18},
        "market": {
            "away_decimal_odds": 4.2,
            "draw_decimal_odds": 3.5,
            "home_decimal_odds": 1.9,
        },
        "schedule": {
            "away": {"rest_days": 4},
            "home": {"rest_days": 6},
        },
        "availability": {
            "away": {"missing_starters": 3},
            "home": {"missing_starters": 1},
        },
        "recent_form": {
            "away": {"points_last_5": 6},
            "home": {"points_last_5": 11},
        },
        "team_strength": {
            "away": {"elo_rating": 1540},
            "home": {"elo_rating": 1610},
        },
    }
    second = build_feature_vector(_normalized(reordered_data))
    changed_source = build_feature_vector(_normalized(fingerprint="different-intelligence"))

    assert first.values == second.values
    assert first.missing_features == second.missing_features
    assert first.fingerprint == second.fingerprint
    assert first.fingerprint != changed_source.fingerprint

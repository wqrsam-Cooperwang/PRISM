from datetime import datetime, timezone

import pytest

from src.collection import SourceEnvelope, TeamStrengthFormAdapter, collect_observations
from src.features import build_feature_vector
from src.intelligence import MatchTarget, SourceRef, SourceType, build_intelligence_bundle
from src.intelligence.normalization import normalize_intelligence_facts
from src.prediction import EloProbabilityModel, run_prediction_model

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)


def _target() -> MatchTarget:
    return MatchTarget(
        match_id="strength-form-001",
        competition="Test League",
        kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        home_team_id="home-id",
        home_team_name="Home FC",
        away_team_id="away-id",
        away_team_name="Away FC",
    )


def _envelope(payload: dict[str, object]) -> SourceEnvelope:
    return SourceEnvelope(
        adapter_id="team_strength_form",
        source=SourceRef(source_id="strength-provider", source_type=SourceType.PRIMARY_DATA),
        retrieved_at=NOW,
        payload=payload,
    )


def _payload() -> dict[str, object]:
    return {
        "observed_at": "2026-07-24T11:00:00+00:00",
        "home_team_id": "home-id",
        "away_team_id": "away-id",
        "home": {"elo_rating": 1620, "points_last_5": 11},
        "away": {"elo_rating": 1540, "points_last_5": 6},
    }


def test_adapter_emits_strength_and_form_observations() -> None:
    observations = TeamStrengthFormAdapter().adapt(_target(), _envelope(_payload()))

    assert len(observations) == 4
    by_key = {(item.category.value, item.subject, item.claim_key): item for item in observations}
    assert by_key[("team_strength", "home", "elo_rating")].value == 1620.0
    assert by_key[("team_strength", "away", "elo_rating")].value == 1540.0
    assert by_key[("recent_form", "home", "points_last_5")].value == 11
    assert by_key[("recent_form", "away", "points_last_5")].value == 6
    assert all(item.source.source_id == "strength-provider" for item in observations)
    assert all(item.collected_at == NOW for item in observations)


def test_strength_form_adapter_drives_existing_elo_feature_and_model() -> None:
    target = _target()
    observations = collect_observations(
        target,
        (TeamStrengthFormAdapter(),),
        (_envelope(_payload()),),
    )
    bundle = build_intelligence_bundle(target, observations, collected_at=NOW)
    features = build_feature_vector(normalize_intelligence_facts(bundle))

    assert features.values["elo_difference"] == pytest.approx(80.0)
    assert features.values["recent_points_difference"] == pytest.approx(5.0)

    output = run_prediction_model(EloProbabilityModel(), features)
    assert output.home_probability > output.away_probability
    assert output.diagnostics["feature_fingerprint"] == features.fingerprint


def test_missing_required_team_value_fails_closed() -> None:
    payload = _payload()
    payload["away"] = {"elo_rating": 1540}

    with pytest.raises(ValueError, match="away.points_last_5"):
        TeamStrengthFormAdapter().adapt(_target(), _envelope(payload))


def test_invalid_points_last_5_fails_closed() -> None:
    payload = _payload()
    payload["home"] = {"elo_rating": 1620, "points_last_5": 16}

    with pytest.raises(ValueError, match="home.points_last_5"):
        TeamStrengthFormAdapter().adapt(_target(), _envelope(payload))


def test_boolean_elo_is_not_accepted_as_numeric() -> None:
    payload = _payload()
    payload["home"] = {"elo_rating": True, "points_last_5": 11}

    with pytest.raises(ValueError, match="home.elo_rating"):
        TeamStrengthFormAdapter().adapt(_target(), _envelope(payload))


def test_provider_team_identity_mismatch_fails_closed() -> None:
    payload = _payload()
    payload["away_team_id"] = "wrong-away"

    with pytest.raises(ValueError, match="away_team_id"):
        TeamStrengthFormAdapter().adapt(_target(), _envelope(payload))

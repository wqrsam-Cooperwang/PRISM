from datetime import datetime, timezone

import pytest

from src.collection import SourceEnvelope, WeatherLineupAdapter, collect_observations
from src.features import build_feature_vector
from src.intelligence import MatchTarget, SourceRef, SourceType, build_intelligence_bundle
from src.intelligence.normalization import normalize_intelligence_facts

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)


def _target() -> MatchTarget:
    return MatchTarget(
        match_id="weather-lineup-001",
        competition="Test League",
        kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        home_team_id="home-id",
        home_team_name="Home FC",
        away_team_id="away-id",
        away_team_name="Away FC",
    )


def _payload() -> dict[str, object]:
    return {
        "observed_at": "2026-07-24T11:00:00+00:00",
        "home_team_id": "home-id",
        "away_team_id": "away-id",
        "weather": {"temperature_c": 18.5},
        "home": {"formation": "4-3-3"},
        "away": {"formation": "4-2-3-1"},
    }


def _envelope(payload: dict[str, object]) -> SourceEnvelope:
    return SourceEnvelope(
        adapter_id="weather_lineup",
        source=SourceRef(
            source_id="weather-lineup-provider",
            source_type=SourceType.OFFICIAL,
        ),
        retrieved_at=NOW,
        payload=payload,
    )


def test_adapter_emits_weather_and_lineup_observations() -> None:
    observations = WeatherLineupAdapter().adapt(_target(), _envelope(_payload()))

    assert len(observations) == 3
    by_key = {(item.category.value, item.subject, item.claim_key): item for item in observations}
    assert by_key[("weather", None, "temperature_c")].value == pytest.approx(18.5)
    assert by_key[("lineup", "home", "formation")].value == "4-3-3"
    assert by_key[("lineup", "away", "formation")].value == "4-2-3-1"
    assert all(item.collected_at == NOW for item in observations)


def test_weather_lineup_adapter_drives_existing_feature_and_runtime_context() -> None:
    target = _target()
    observations = collect_observations(
        target,
        (WeatherLineupAdapter(),),
        (_envelope(_payload()),),
    )
    bundle = build_intelligence_bundle(target, observations, collected_at=NOW)
    facts = normalize_intelligence_facts(bundle)
    features = build_feature_vector(facts)

    assert features.values["temperature_c"] == pytest.approx(18.5)
    assert facts.model_feature_data["lineup"] == {
        "away": {"formation": "4-2-3-1"},
        "home": {"formation": "4-3-3"},
    }


def test_invalid_temperature_fails_closed() -> None:
    payload = _payload()
    payload["weather"] = {"temperature_c": True}

    with pytest.raises(ValueError, match="weather.temperature_c"):
        WeatherLineupAdapter().adapt(_target(), _envelope(payload))


def test_missing_formation_fails_closed() -> None:
    payload = _payload()
    payload["away"] = {}

    with pytest.raises(ValueError, match="away.formation"):
        WeatherLineupAdapter().adapt(_target(), _envelope(payload))


def test_provider_team_identity_mismatch_fails_closed() -> None:
    payload = _payload()
    payload["home_team_id"] = "wrong-home"

    with pytest.raises(ValueError, match="home_team_id"):
        WeatherLineupAdapter().adapt(_target(), _envelope(payload))

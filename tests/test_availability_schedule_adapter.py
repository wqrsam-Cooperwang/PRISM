from datetime import datetime, timezone

import pytest

from src.collection import AvailabilityScheduleAdapter, SourceEnvelope, collect_observations
from src.features import build_feature_vector
from src.intelligence import MatchTarget, SourceRef, SourceType, build_intelligence_bundle
from src.intelligence.normalization import normalize_intelligence_facts

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)


def _target() -> MatchTarget:
    return MatchTarget(
        match_id="availability-schedule-001",
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
        "home": {"missing_starters": 1, "rest_days": 6},
        "away": {"missing_starters": 3, "rest_days": 4},
    }


def _envelope(payload: dict[str, object]) -> SourceEnvelope:
    return SourceEnvelope(
        adapter_id="availability_schedule",
        source=SourceRef(source_id="availability-provider", source_type=SourceType.OFFICIAL),
        retrieved_at=NOW,
        payload=payload,
    )


def test_adapter_emits_availability_and_schedule_observations() -> None:
    observations = AvailabilityScheduleAdapter().adapt(_target(), _envelope(_payload()))

    assert len(observations) == 4
    by_key = {(item.category.value, item.subject, item.claim_key): item for item in observations}
    assert by_key[("availability", "home", "missing_starters")].value == 1
    assert by_key[("availability", "away", "missing_starters")].value == 3
    assert by_key[("schedule", "home", "rest_days")].value == 6
    assert by_key[("schedule", "away", "rest_days")].value == 4
    assert all(item.source.source_id == "availability-provider" for item in observations)
    assert all(item.collected_at == NOW for item in observations)


def test_adapter_drives_existing_availability_and_schedule_features() -> None:
    target = _target()
    observations = collect_observations(
        target,
        (AvailabilityScheduleAdapter(),),
        (_envelope(_payload()),),
    )
    bundle = build_intelligence_bundle(target, observations, collected_at=NOW)
    features = build_feature_vector(normalize_intelligence_facts(bundle))

    assert features.values["missing_starters_difference"] == pytest.approx(-2.0)
    assert features.values["rest_days_difference"] == pytest.approx(2.0)


def test_missing_required_availability_value_fails_closed() -> None:
    payload = _payload()
    payload["away"] = {"rest_days": 4}

    with pytest.raises(ValueError, match="away.missing_starters"):
        AvailabilityScheduleAdapter().adapt(_target(), _envelope(payload))


def test_missing_starters_out_of_range_fails_closed() -> None:
    payload = _payload()
    payload["home"] = {"missing_starters": 12, "rest_days": 6}

    with pytest.raises(ValueError, match="home.missing_starters"):
        AvailabilityScheduleAdapter().adapt(_target(), _envelope(payload))


def test_negative_rest_days_fail_closed() -> None:
    payload = _payload()
    payload["away"] = {"missing_starters": 3, "rest_days": -1}

    with pytest.raises(ValueError, match="away.rest_days"):
        AvailabilityScheduleAdapter().adapt(_target(), _envelope(payload))


def test_boolean_values_are_not_accepted_as_counts() -> None:
    payload = _payload()
    payload["home"] = {"missing_starters": True, "rest_days": 6}

    with pytest.raises(ValueError, match="home.missing_starters"):
        AvailabilityScheduleAdapter().adapt(_target(), _envelope(payload))


def test_provider_team_identity_mismatch_fails_closed() -> None:
    payload = _payload()
    payload["home_team_id"] = "wrong-home"

    with pytest.raises(ValueError, match="home_team_id"):
        AvailabilityScheduleAdapter().adapt(_target(), _envelope(payload))

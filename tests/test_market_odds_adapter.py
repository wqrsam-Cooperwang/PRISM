from datetime import datetime, timezone

import pytest

from src.collection import MarketOdds1X2Adapter, SourceEnvelope, collect_observations
from src.features import build_feature_vector
from src.intelligence import (
    MatchTarget,
    SourceRef,
    SourceType,
    build_intelligence_bundle,
    normalize_intelligence_facts,
)
from src.prediction import MarketProbabilityModel, run_prediction_model

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
OBSERVED = datetime(2026, 7, 24, 11, 45, tzinfo=timezone.utc)
KICKOFF = datetime(2026, 7, 24, 18, 0, tzinfo=timezone.utc)


def _target() -> MatchTarget:
    return MatchTarget(
        match_id="market-match-001",
        competition="Test League",
        kickoff=KICKOFF,
        home_team_id="home-id",
        home_team_name="Home FC",
        away_team_id="away-id",
        away_team_name="Away FC",
    )


def _envelope(**overrides: object) -> SourceEnvelope:
    payload: dict[str, object] = {
        "observed_at": OBSERVED.isoformat(),
        "home_decimal_odds": 2.0,
        "draw_decimal_odds": 4.0,
        "away_decimal_odds": 5.0,
        "home_team_id": "home-id",
        "away_team_id": "away-id",
        "provider_event_id": "provider-event-123",
    }
    payload.update(overrides)
    return SourceEnvelope(
        adapter_id="market_odds_1x2",
        source=SourceRef(
            source_id="provider-market",
            source_type=SourceType.MARKET,
            publisher="Test Provider",
        ),
        retrieved_at=NOW,
        payload=payload,
        request_id="request-123",
    )


def test_market_odds_adapter_emits_three_existing_market_claims() -> None:
    observations = collect_observations(
        _target(),
        (MarketOdds1X2Adapter(),),
        (_envelope(),),
    )

    assert tuple(item.claim_key for item in observations) == (
        "away_decimal_odds",
        "draw_decimal_odds",
        "home_decimal_odds",
    )
    assert {item.value for item in observations} == {2.0, 4.0, 5.0}
    assert all(item.source.source_id == "provider-market" for item in observations)
    assert all(item.observed_at == OBSERVED for item in observations)
    assert all(item.collected_at == NOW for item in observations)


def test_market_odds_adapter_connects_to_feature_and_market_model_path() -> None:
    target = _target()
    observations = collect_observations(
        target,
        (MarketOdds1X2Adapter(),),
        (_envelope(),),
    )
    bundle = build_intelligence_bundle(target, observations, collected_at=NOW)
    facts = normalize_intelligence_facts(bundle)
    features = build_feature_vector(facts)
    output = run_prediction_model(MarketProbabilityModel(), features)

    raw_home = 1.0 / 2.0
    raw_draw = 1.0 / 4.0
    raw_away = 1.0 / 5.0
    total = raw_home + raw_draw + raw_away
    assert output.home_probability == pytest.approx(raw_home / total)
    assert output.draw_probability == pytest.approx(raw_draw / total)
    assert output.away_probability == pytest.approx(raw_away / total)
    assert output.diagnostics["feature_fingerprint"] == features.fingerprint


def test_market_odds_adapter_is_deterministic() -> None:
    target = _target()
    adapter = MarketOdds1X2Adapter()
    first = collect_observations(target, (adapter,), (_envelope(),))
    second = collect_observations(target, (adapter,), (_envelope(),))

    assert first == second


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    (
        ("home_decimal_odds", 1.0),
        ("draw_decimal_odds", 0.0),
        ("away_decimal_odds", float("inf")),
        ("home_decimal_odds", "2.0"),
        ("draw_decimal_odds", None),
    ),
)
def test_market_odds_adapter_rejects_invalid_or_missing_prices(
    field_name: str,
    invalid_value: object,
) -> None:
    with pytest.raises(ValueError, match=field_name):
        collect_observations(
            _target(),
            (MarketOdds1X2Adapter(),),
            (_envelope(**{field_name: invalid_value}),),
        )


def test_market_odds_adapter_rejects_team_identity_mismatch() -> None:
    with pytest.raises(ValueError, match="home_team_id"):
        collect_observations(
            _target(),
            (MarketOdds1X2Adapter(),),
            (_envelope(home_team_id="different-home"),),
        )


def test_market_odds_adapter_rejects_wrong_adapter_id() -> None:
    envelope = SourceEnvelope(
        adapter_id="fixture_observations",
        source=_envelope().source,
        retrieved_at=NOW,
        payload=_envelope().payload,
    )
    with pytest.raises(ValueError, match="No collection adapter configured"):
        collect_observations(
            _target(),
            (MarketOdds1X2Adapter(),),
            (envelope,),
        )

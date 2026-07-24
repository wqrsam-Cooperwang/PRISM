import pytest

from src.features import FeatureVector
from src.intelligence import ReadinessLevel
from src.prediction import (
    EloProbabilityModel,
    MarketProbabilityModel,
    run_model_suite,
    run_prediction_model,
)


def _features(**values: float) -> FeatureVector:
    return FeatureVector(
        values=values,
        missing_features=(),
        intelligence_fingerprint="intelligence-fingerprint",
        readiness=ReadinessLevel.STANDARD,
        fingerprint="feature-fingerprint",
    )


def test_market_model_returns_governed_market_probabilities_exactly() -> None:
    features = _features(
        market_home_implied_probability=0.52,
        market_draw_implied_probability=0.28,
        market_away_implied_probability=0.20,
    )

    output = MarketProbabilityModel().predict(features)

    assert output.home_probability == pytest.approx(0.52)
    assert output.draw_probability == pytest.approx(0.28)
    assert output.away_probability == pytest.approx(0.20)
    assert output.diagnostics["method"] == "de_vigged_market_identity"


def test_elo_model_is_deterministic_and_probabilities_sum_to_one() -> None:
    features = _features(elo_difference=80.0)
    model = EloProbabilityModel()

    first = model.predict(features)
    second = model.predict(features)

    assert first == second
    total_probability = first.home_probability + first.draw_probability + first.away_probability
    assert total_probability == pytest.approx(1.0)
    assert 0.0 <= first.home_probability <= 1.0
    assert 0.0 <= first.draw_probability <= 1.0
    assert 0.0 <= first.away_probability <= 1.0


def test_increasing_elo_difference_moves_probability_toward_home() -> None:
    model = EloProbabilityModel(home_advantage_elo=0.0)

    weaker_home = model.predict(_features(elo_difference=-100.0))
    even = model.predict(_features(elo_difference=0.0))
    stronger_home = model.predict(_features(elo_difference=100.0))

    assert weaker_home.home_probability < even.home_probability < stronger_home.home_probability
    assert weaker_home.away_probability > even.away_probability > stronger_home.away_probability


def test_home_advantage_moves_equal_elo_match_toward_home() -> None:
    features = _features(elo_difference=0.0)

    neutral = EloProbabilityModel(home_advantage_elo=0.0).predict(features)
    home_advantaged = EloProbabilityModel(home_advantage_elo=60.0).predict(features)

    assert neutral.home_probability == pytest.approx(neutral.away_probability)
    assert home_advantaged.home_probability > home_advantaged.away_probability
    assert home_advantaged.home_probability > neutral.home_probability


def test_invalid_elo_configuration_fails_closed() -> None:
    with pytest.raises(ValueError, match="draw_scale"):
        EloProbabilityModel(draw_scale=-0.1)

    with pytest.raises(ValueError, match="home_advantage_elo"):
        EloProbabilityModel(home_advantage_elo=float("inf"))


def test_baselines_execute_through_governed_runner_with_provenance() -> None:
    features = _features(
        elo_difference=50.0,
        market_home_implied_probability=0.48,
        market_draw_implied_probability=0.30,
        market_away_implied_probability=0.22,
    )

    output = run_prediction_model(EloProbabilityModel(), features)

    assert output.diagnostics["feature_fingerprint"] == features.fingerprint
    assert output.diagnostics["intelligence_fingerprint"] == features.intelligence_fingerprint
    assert output.diagnostics["feature_schema_version"] == features.schema_version


def test_baseline_suite_produces_two_independent_model_outputs() -> None:
    features = _features(
        elo_difference=50.0,
        market_home_implied_probability=0.48,
        market_draw_implied_probability=0.30,
        market_away_implied_probability=0.22,
    )

    outputs = run_model_suite(
        (MarketProbabilityModel(), EloProbabilityModel()),
        features,
    )
    assert tuple(output.model_id for output in outputs) == (
        "elo_probability",
        "market_probability",
    )
    assert outputs[0].diagnostics["feature_fingerprint"] == features.fingerprint
    assert outputs[1].diagnostics["feature_fingerprint"] == features.fingerprint


def test_market_model_missing_feature_is_blocked_by_runner() -> None:
    features = FeatureVector(
        values={
            "market_home_implied_probability": 0.52,
            "market_draw_implied_probability": 0.28,
        },
        missing_features=("market_away_implied_probability",),
        intelligence_fingerprint="intelligence-fingerprint",
        readiness=ReadinessLevel.LIMITED,
        fingerprint="feature-fingerprint",
    )

    with pytest.raises(ValueError, match="market_away_implied_probability"):
        run_prediction_model(MarketProbabilityModel(), features)

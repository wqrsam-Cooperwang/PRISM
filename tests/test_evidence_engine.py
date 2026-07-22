import math

import pytest

from src.evidence.engine import CATEGORY_WEIGHTS, evaluate_evidence


def complete_payload():
    return {category: 1.0 for category in CATEGORY_WEIGHTS}


def test_complete_payload_scores_100_and_allows_deep_analysis():
    result = evaluate_evidence(complete_payload())

    assert result.score == 100
    assert result.raw_score == 100.0
    assert result.gate == "deep"
    assert result.missing_categories == ()
    assert result.critical_caps_applied == ()


def test_empty_payload_is_rejected():
    result = evaluate_evidence({})

    assert result.score == 0
    assert result.gate == "rejected"
    assert len(result.missing_categories) == len(CATEGORY_WEIGHTS)


def test_category_contributions_sum_to_raw_score():
    payload = complete_payload()
    payload["weather"] = 0.5
    payload["motivation"] = 0.2

    result = evaluate_evidence(payload)

    assert sum(result.category_scores.values()) == result.raw_score


@pytest.mark.parametrize(
    ("target_score", "expected_gate"),
    [
        (85, "deep"),
        (84, "standard"),
        (70, "standard"),
        (69, "limited"),
        (45, "limited"),
        (44, "rejected"),
    ],
)
def test_quality_gate_boundaries(target_score, expected_gate):
    payload = {category: target_score / 100 for category in CATEGORY_WEIGHTS}
    result = evaluate_evidence(payload)

    assert result.score == target_score
    assert result.gate == expected_gate


def test_missing_odds_caps_high_score_at_limited():
    payload = complete_payload()
    payload["odds"] = 0.0

    result = evaluate_evidence(payload)

    assert result.score == 85
    assert result.gate == "limited"
    assert "odds_missing" in result.critical_caps_applied


def test_critically_incomplete_lineup_caps_gate_at_limited():
    payload = complete_payload()
    payload["lineup"] = 0.2

    result = evaluate_evidence(payload)

    assert result.score == 84
    assert result.gate == "limited"
    assert "lineup_below_0.25" in result.critical_caps_applied


def test_missing_lineup_and_injuries_forces_rejection():
    payload = complete_payload()
    payload["lineup"] = 0.0
    payload["injuries"] = 0.0

    result = evaluate_evidence(payload)

    assert result.score == 70
    assert result.gate == "rejected"
    assert "lineup_and_injuries_missing" in result.critical_caps_applied


def test_three_missing_categories_cap_gate_at_limited():
    payload = complete_payload()
    payload["weather"] = 0.0
    payload["market_data"] = 0.0
    payload["motivation"] = 0.0

    result = evaluate_evidence(payload)

    assert result.score == 75
    assert result.gate == "limited"
    assert "three_or_more_categories_missing" in result.critical_caps_applied


def test_omitted_category_is_treated_as_zero():
    payload = complete_payload()
    del payload["weather"]

    result = evaluate_evidence(payload)

    assert result.category_scores["weather"] == 0
    assert "weather" in result.missing_categories


def test_result_can_be_serialized_to_plain_dictionary():
    result = evaluate_evidence(complete_payload())
    serialized = result.to_dict()

    assert serialized["score"] == 100
    assert isinstance(serialized["category_scores"], dict)
    assert isinstance(serialized["warnings"], list)


def test_non_mapping_payload_raises_type_error():
    with pytest.raises(TypeError):
        evaluate_evidence([])


def test_unknown_category_raises_value_error():
    with pytest.raises(ValueError, match="Unknown evidence categories"):
        evaluate_evidence({"rumours": 1.0})


@pytest.mark.parametrize("invalid_value", [-0.01, 1.01, math.nan, math.inf, -math.inf])
def test_invalid_numeric_values_raise_value_error(invalid_value):
    with pytest.raises(ValueError):
        evaluate_evidence({"lineup": invalid_value})


@pytest.mark.parametrize("invalid_value", [True, False, "1.0", None])
def test_non_numeric_and_boolean_values_raise_value_error(invalid_value):
    with pytest.raises(ValueError):
        evaluate_evidence({"lineup": invalid_value})


def test_same_input_always_produces_same_output():
    payload = {
        "lineup": 0.75,
        "injuries": 0.8,
        "odds": 1.0,
        "weather": 0.5,
        "tactical_data": 0.9,
        "historical_data": 1.0,
        "market_data": 0.7,
        "motivation": 0.6,
    }

    first = evaluate_evidence(payload).to_dict()
    second = evaluate_evidence(payload).to_dict()

    assert first == second

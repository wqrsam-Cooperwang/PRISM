"""Canonical governed V2.2 promotion decision tests."""

from __future__ import annotations

import pytest

from src.regression import governed_promotion
from src.regression.shadow_outcome import FrozenShadowSummary
from src.regression.v22_ab import V22ScorelineABSummary
from src.regression.v22_promotion import V22PromotionPolicy


def _scoreline_summary(
    *,
    case_count: int = 30,
    v21_primary_hits: int = 4,
    v22_primary_hits: int = 5,
    v21_dual_hits: int = 7,
    v22_dual_hits: int = 8,
    v21_mean_minimum_distance: float = 1.4,
    v22_mean_minimum_distance: float = 1.2,
    v21_shared_story_pairs: int = 10,
    v22_shared_story_pairs: int = 9,
) -> V22ScorelineABSummary:
    return V22ScorelineABSummary(
        case_count=case_count,
        v21_primary_hits=v21_primary_hits,
        v22_primary_hits=v22_primary_hits,
        v21_dual_hits=v21_dual_hits,
        v22_dual_hits=v22_dual_hits,
        v21_mean_minimum_distance=v21_mean_minimum_distance,
        v22_mean_minimum_distance=v22_mean_minimum_distance,
        v21_shared_story_pairs=v21_shared_story_pairs,
        v22_shared_story_pairs=v22_shared_story_pairs,
        v22_distance_improved_cases=12,
        v22_distance_worsened_cases=8,
        distance_tied_cases=10,
    )


def _shadow_summary(
    *,
    case_count: int = 30,
    v21_primary_hits: int = 4,
    v22_primary_hits: int = 5,
    v21_dual_hits: int = 7,
    v22_dual_hits: int = 8,
    v21_mean_minimum_distance: float = 1.4,
    v22_mean_minimum_distance: float = 1.2,
    v21_shared_story_pairs: int = 10,
    v22_shared_story_pairs: int = 9,
) -> FrozenShadowSummary:
    return FrozenShadowSummary(
        case_count=case_count,
        v21_primary_hits=v21_primary_hits,
        v22_primary_hits=v22_primary_hits,
        v21_dual_hits=v21_dual_hits,
        v22_dual_hits=v22_dual_hits,
        v21_mean_minimum_distance=v21_mean_minimum_distance,
        v22_mean_minimum_distance=v22_mean_minimum_distance,
        v21_shared_story_pairs=v21_shared_story_pairs,
        v22_shared_story_pairs=v22_shared_story_pairs,
        v22_distance_improved_cases=12,
        v22_distance_worsened_cases=8,
        distance_tied_cases=10,
    )


def _wire_summaries(monkeypatch, scoreline_summary, shadow_summary) -> None:
    monkeypatch.setattr(
        governed_promotion,
        "load_governed_settled_ledger_pairs",
        lambda *_args: ((object(), object()),),
    )
    monkeypatch.setattr(
        governed_promotion,
        "load_governed_ledger_regression_dataset",
        lambda *_args: (object(),),
    )
    monkeypatch.setattr(
        governed_promotion,
        "compare_v21_v22_scoreline_case",
        lambda _case: object(),
    )
    monkeypatch.setattr(
        governed_promotion,
        "compare_frozen_shadow_outcome",
        lambda _snapshot, _outcome: object(),
    )
    monkeypatch.setattr(
        governed_promotion,
        "summarize_v21_v22_scoreline_ab",
        lambda _items: scoreline_summary,
    )
    monkeypatch.setattr(
        governed_promotion,
        "summarize_frozen_shadow",
        lambda _items: shadow_summary,
    )


def test_no_governed_settled_cases_holds(monkeypatch):
    monkeypatch.setattr(
        governed_promotion,
        "load_governed_settled_ledger_pairs",
        lambda *_args: (),
    )

    result = governed_promotion.evaluate_governed_v22_promotion()

    assert result.decision == "hold"
    assert result.scoreline_case_count == 0
    assert result.full_stack_case_count == 0


def test_governed_cohort_count_mismatch_fails_closed(monkeypatch):
    monkeypatch.setattr(
        governed_promotion,
        "load_governed_settled_ledger_pairs",
        lambda *_args: ((object(), object()),),
    )
    monkeypatch.setattr(
        governed_promotion,
        "load_governed_ledger_regression_dataset",
        lambda *_args: (),
    )

    with pytest.raises(ValueError, match="identical case counts"):
        governed_promotion.evaluate_governed_v22_promotion()


def test_governed_promotion_rejects_scoreline_regression(monkeypatch):
    _wire_summaries(
        monkeypatch,
        _scoreline_summary(v22_dual_hits=6),
        _shadow_summary(),
    )

    result = governed_promotion.evaluate_governed_v22_promotion()

    assert result.decision == "reject"
    assert "dual exact-score hits regressed" in result.reasons


def test_governed_promotion_holds_when_sample_is_below_policy(monkeypatch):
    _wire_summaries(
        monkeypatch,
        _scoreline_summary(case_count=10),
        _shadow_summary(case_count=10),
    )

    result = governed_promotion.evaluate_governed_v22_promotion()

    assert result.decision == "hold"
    assert result.scoreline_case_count == 10
    assert result.full_stack_case_count == 10


def test_governed_promotion_promotes_only_with_full_stack_improvement(monkeypatch):
    _wire_summaries(monkeypatch, _scoreline_summary(), _shadow_summary())

    result = governed_promotion.evaluate_governed_v22_promotion(
        policy=V22PromotionPolicy(
            minimum_scoreline_case_count=30,
            minimum_full_stack_case_count=30,
        )
    )

    assert result.decision == "promote"
    assert result.scoreline_layer_passed is True
    assert result.full_stack_validation_passed is True

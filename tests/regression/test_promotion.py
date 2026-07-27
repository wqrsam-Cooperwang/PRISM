"""V2.2 promotion evidence policy tests."""

from __future__ import annotations

import pytest

from src.regression import promotion
from src.regression.shadow_evaluation import ShadowScorelineEvaluation


def _evaluation(
    *,
    case_count: int = 30,
    production_primary_hits: int = 4,
    production_dual_hits: int = 7,
    shadow_primary_hits: int = 4,
    shadow_dual_hits: int = 7,
) -> ShadowScorelineEvaluation:
    return ShadowScorelineEvaluation(
        case_count=case_count,
        production_primary_hits=production_primary_hits,
        production_dual_hits=production_dual_hits,
        shadow_primary_hits=shadow_primary_hits,
        shadow_dual_hits=shadow_dual_hits,
    )


def test_promotion_review_is_eligible_at_minimum_non_regressing_evidence(monkeypatch):
    monkeypatch.setattr(
        promotion,
        "evaluate_governed_v22_shadow",
        lambda *_args, **_kwargs: _evaluation(),
    )

    evidence = promotion.build_v22_promotion_evidence(minimum_cases=30)

    assert evidence.eligible is True
    assert evidence.reasons == ()


def test_promotion_review_rejects_insufficient_governed_cases(monkeypatch):
    monkeypatch.setattr(
        promotion,
        "evaluate_governed_v22_shadow",
        lambda *_args, **_kwargs: _evaluation(case_count=29),
    )

    evidence = promotion.build_v22_promotion_evidence(minimum_cases=30)

    assert evidence.eligible is False
    assert evidence.reasons == ("insufficient governed cases: 29 < 30",)


def test_promotion_review_rejects_dual_score_regression(monkeypatch):
    monkeypatch.setattr(
        promotion,
        "evaluate_governed_v22_shadow",
        lambda *_args, **_kwargs: _evaluation(shadow_dual_hits=6),
    )

    evidence = promotion.build_v22_promotion_evidence()

    assert evidence.eligible is False
    assert "V2.2 shadow dual-score exact hits regress production" in evidence.reasons


def test_promotion_review_rejects_primary_score_regression(monkeypatch):
    monkeypatch.setattr(
        promotion,
        "evaluate_governed_v22_shadow",
        lambda *_args, **_kwargs: _evaluation(shadow_primary_hits=3),
    )

    evidence = promotion.build_v22_promotion_evidence()

    assert evidence.eligible is False
    assert "V2.2 shadow primary exact hits regress production" in evidence.reasons


def test_minimum_cases_must_be_positive():
    with pytest.raises(ValueError, match="minimum_cases must be positive"):
        promotion.build_v22_promotion_evidence(minimum_cases=0)

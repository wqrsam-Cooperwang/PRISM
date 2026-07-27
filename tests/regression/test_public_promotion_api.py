"""Public API governance for V2.2 promotion decisions."""

from __future__ import annotations

import src.regression as regression


def test_public_promotion_api_exposes_only_governed_decision_path() -> None:
    assert callable(regression.evaluate_governed_v22_promotion)
    assert not hasattr(regression, "evaluate_v22_promotion")
    assert not hasattr(regression, "evaluate_v22_promotion_with_shadow")

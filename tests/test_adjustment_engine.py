from dataclasses import replace
from datetime import datetime, timezone

import pytest

from src.adjustment.engine import AdjustmentEngine
from src.domain.models import (
    AnalysisSession,
    ConfidenceBand,
    ConfidenceOutput,
    MatchContext,
    MatchInfo,
    TeamInfo,
)


def build_context(overall: float = 0.90) -> MatchContext:
    return MatchContext(
        session=AnalysisSession(
            session_id="adjustment-session",
            created_at=datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
            prism_version="3.2.0-alpha1",
        ),
        match=MatchInfo(
            match_id="adjustment-match",
            competition="Test League",
            kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        ),
        home_team=TeamInfo(team_id="home", name="Home FC"),
        away_team=TeamInfo(team_id="away", name="Away FC"),
        confidence=ConfidenceOutput(
            evidence=0.9,
            model=0.9,
            context=0.9,
            consensus=0.9,
            overall=overall,
            band=ConfidenceBand.VERY_HIGH if overall >= 0.85 else ConfidenceBand.HIGH,
        ),
    )


def governed_output(*effects: str) -> dict[str, object]:
    return {
        "rule_id": "TEST-RULE",
        "version": "1.0.0",
        "severity": "warning",
        "priority": 50,
        "effects": effects,
        "effective_effects": effects,
        "suppressed_effects": (),
        "status": "active",
        "ruleset_version": "1.2.0",
    }


def test_requires_confidence() -> None:
    context = replace(build_context(), confidence=None)
    with pytest.raises(ValueError, match="requires confidence"):
        AdjustmentEngine().run(context)


def test_no_rules_preserves_base_confidence() -> None:
    result = AdjustmentEngine().run(build_context(0.90))
    assert result.adjustment is not None
    assert result.adjustment.base_confidence == 0.90
    assert result.adjustment.adjusted_confidence == 0.90
    assert result.adjustment.confidence_cap is None
    assert result.adjustment.decision_blocked is False


def test_high_confidence_restriction_caps_at_point_69() -> None:
    context = replace(
        build_context(0.90),
        rule_outputs=(governed_output("restrict_high_confidence_action"),),
    )
    result = AdjustmentEngine().run(context)
    assert result.adjustment is not None
    assert result.adjustment.adjusted_confidence == 0.69
    assert result.adjustment.confidence_cap == 0.69


def test_active_decision_restriction_caps_at_point_49() -> None:
    context = replace(
        build_context(0.80),
        rule_outputs=(governed_output("restrict_active_decision"),),
    )
    result = AdjustmentEngine().run(context)
    assert result.adjustment is not None
    assert result.adjustment.adjusted_confidence == 0.49


def test_block_effect_is_strictest_and_blocks_decision() -> None:
    context = replace(
        build_context(0.95),
        rule_outputs=(
            governed_output("restrict_high_confidence_action"),
            governed_output("block_active_decision"),
        ),
    )
    result = AdjustmentEngine().run(context)
    assert result.adjustment is not None
    assert result.adjustment.adjusted_confidence == 0.34
    assert result.adjustment.confidence_cap == 0.34
    assert result.adjustment.decision_blocked is True


def test_adjustment_never_increases_lower_base_confidence() -> None:
    context = replace(
        build_context(0.30),
        rule_outputs=(governed_output("restrict_active_decision"),),
    )
    result = AdjustmentEngine().run(context)
    assert result.adjustment is not None
    assert result.adjustment.adjusted_confidence == 0.30


def test_informational_effect_is_observed_but_not_numeric() -> None:
    context = replace(
        build_context(0.88),
        rule_outputs=(governed_output("flag_market_movement"),),
    )
    result = AdjustmentEngine().run(context)
    assert result.adjustment is not None
    assert result.adjustment.adjusted_confidence == 0.88
    assert result.adjustment.applied_effects == ()
    assert result.adjustment.observed_effects == ("flag_market_movement",)


def test_suppressed_effects_do_not_influence_adjustment() -> None:
    output = governed_output("flag_model_disagreement")
    output["suppressed_effects"] = ("restrict_active_decision",)
    context = replace(build_context(0.90), rule_outputs=(output,))
    result = AdjustmentEngine().run(context)
    assert result.adjustment is not None
    assert result.adjustment.confidence_cap is None
    assert result.adjustment.adjusted_confidence == 0.90


def test_duplicate_effects_are_deduplicated_in_first_seen_order() -> None:
    context = replace(
        build_context(0.90),
        rule_outputs=(
            governed_output("flag_market_movement", "restrict_high_confidence_action"),
            governed_output("flag_market_movement", "require_market_rationale"),
        ),
    )
    result = AdjustmentEngine().run(context)
    assert result.adjustment is not None
    assert result.adjustment.observed_effects == (
        "flag_market_movement",
        "restrict_high_confidence_action",
        "require_market_rationale",
    )


def test_engine_is_immutable() -> None:
    original = replace(
        build_context(),
        rule_outputs=(governed_output("restrict_high_confidence_action"),),
    )
    result = AdjustmentEngine().run(original)
    assert original.adjustment is None
    assert result.adjustment is not None
    assert result is not original

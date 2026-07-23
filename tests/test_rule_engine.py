from dataclasses import replace
from datetime import datetime, timezone

import pytest

from src.domain.models import (
    AnalysisSession,
    ConfidenceBand,
    ConfidenceOutput,
    EvidenceGate,
    EvidenceOutput,
    MatchContext,
    MatchInfo,
    ModelOutput,
    TeamInfo,
)
from src.rules.engine import DEFAULT_RULES, RuleEngine


def build_context() -> MatchContext:
    return MatchContext(
        session=AnalysisSession(
            session_id="rule-session",
            created_at=datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
            prism_version="3.2.0-alpha1",
        ),
        match=MatchInfo(
            match_id="rule-match",
            competition="Test League",
            kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        ),
        home_team=TeamInfo(team_id="home", name="Home FC"),
        away_team=TeamInfo(team_id="away", name="Away FC"),
    )


def confidence(band: ConfidenceBand) -> ConfidenceOutput:
    return ConfidenceOutput(
        evidence=0.5,
        model=0.5,
        context=0.5,
        consensus=0.5,
        overall=0.5,
        band=band,
    )


def model(model_id: str, home: float, draw: float, away: float) -> ModelOutput:
    return ModelOutput(
        model_id=model_id,
        model_version="1.0.0",
        home_probability=home,
        draw_probability=draw,
        away_probability=away,
    )


def rule_ids(context: MatchContext) -> tuple[object, ...]:
    return tuple(output["rule_id"] for output in context.rule_outputs)


def test_no_rules_fire_for_neutral_context() -> None:
    result = RuleEngine().run(build_context())
    assert result.rule_outputs == ()


def test_rejected_evidence_activates_critical_lock() -> None:
    context = replace(
        build_context(),
        evidence=EvidenceOutput(20, 20.0, EvidenceGate.REJECTED),
    )
    result = RuleEngine().run(context)
    assert rule_ids(result) == ("RULE-E001",)
    assert result.rule_outputs[0]["severity"] == "critical"


def test_limited_evidence_and_low_confidence_both_activate() -> None:
    context = replace(
        build_context(),
        evidence=EvidenceOutput(60, 60.0, EvidenceGate.LIMITED),
        confidence=confidence(ConfidenceBand.LOW),
    )
    result = RuleEngine().run(context)
    assert rule_ids(result) == ("RULE-E002", "RULE-C001")


def test_material_model_disagreement_activates() -> None:
    context = replace(
        build_context(),
        model_outputs=(
            model("a", 0.75, 0.15, 0.10),
            model("b", 0.30, 0.30, 0.40),
        ),
    )
    result = RuleEngine().run(context)
    assert rule_ids(result) == ("RULE-M001",)


def test_model_disagreement_requires_two_models() -> None:
    context = replace(
        build_context(),
        model_outputs=(model("a", 0.75, 0.15, 0.10),),
    )
    assert RuleEngine().run(context).rule_outputs == ()


def test_short_turnaround_uses_explicit_schedule_data() -> None:
    context = replace(build_context(), schedule={"home_rest_days": 3})
    result = RuleEngine().run(context)
    assert rule_ids(result) == ("RULE-S001",)


def test_boolean_schedule_value_does_not_count_as_rest_days() -> None:
    context = replace(build_context(), schedule={"home_rest_days": True})
    assert RuleEngine().run(context).rule_outputs == ()


def test_engine_is_immutable() -> None:
    original = replace(build_context(), schedule={"away_rest_days": 2})
    result = RuleEngine().run(original)
    assert original.rule_outputs == ()
    assert result is not original
    assert rule_ids(result) == ("RULE-S001",)


def test_duplicate_rule_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate rule ids"):
        RuleEngine((DEFAULT_RULES[0], DEFAULT_RULES[0]))

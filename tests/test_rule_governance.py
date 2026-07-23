from datetime import datetime, timezone

import pytest

from src.domain.models import AnalysisSession, MatchContext, MatchInfo, TeamInfo
from src.rules.engine import RuleEngine
from src.rules.models import Rule


def build_context() -> MatchContext:
    return MatchContext(
        session=AnalysisSession(
            session_id="governance-session",
            created_at=datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
            prism_version="3.2.0-alpha1",
        ),
        match=MatchInfo(
            match_id="governance-match",
            competition="Test League",
            kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        ),
        home_team=TeamInfo(team_id="home", name="Home FC"),
        away_team=TeamInfo(team_id="away", name="Away FC"),
    )


def always_rule(
    rule_id: str,
    effect: str,
    *,
    priority: int,
    severity: str = "warning",
) -> Rule:
    return Rule(
        rule_id=rule_id,
        version="1.0.0",
        severity=severity,
        effects=(effect,),
        predicate=lambda _: True,
        rationale=lambda _: f"{rule_id} fired",
        priority=priority,
    )


def test_priority_order_is_independent_of_registry_order() -> None:
    low = always_rule("RULE-LOW", "low_flag", priority=10)
    high = always_rule("RULE-HIGH", "high_flag", priority=90)
    result = RuleEngine((low, high)).run(build_context())
    assert tuple(item["rule_id"] for item in result.rule_outputs) == (
        "RULE-HIGH",
        "RULE-LOW",
    )


def test_strongest_decision_restriction_dominates_even_at_lower_priority() -> None:
    weak = always_rule(
        "RULE-WEAK",
        "restrict_high_confidence_action",
        priority=100,
    )
    strong = always_rule(
        "RULE-STRONG",
        "block_active_decision",
        priority=10,
        severity="critical",
    )
    result = RuleEngine((weak, strong)).run(build_context())
    weak_output, strong_output = result.rule_outputs
    assert weak_output["effective_effects"] == ()
    assert weak_output["suppressed_effects"] == ("restrict_high_confidence_action",)
    assert weak_output["status"] == "suppressed"
    assert strong_output["effective_effects"] == ("block_active_decision",)
    assert strong_output["status"] == "active"


def test_duplicate_effect_is_owned_by_highest_ranked_rule() -> None:
    high = always_rule("RULE-A", "require_market_rationale", priority=90)
    low = always_rule("RULE-B", "require_market_rationale", priority=20)
    result = RuleEngine((low, high)).run(build_context())
    assert result.rule_outputs[0]["effective_effects"] == ("require_market_rationale",)
    assert result.rule_outputs[1]["effective_effects"] == ()
    assert result.rule_outputs[1]["suppressed_effects"] == ("require_market_rationale",)


def test_additive_effects_survive_resolution() -> None:
    first = always_rule("RULE-A", "flag_market_movement", priority=80)
    second = always_rule("RULE-B", "require_schedule_rationale", priority=70)
    result = RuleEngine((first, second)).run(build_context())
    assert result.rule_outputs[0]["effective_effects"] == ("flag_market_movement",)
    assert result.rule_outputs[1]["effective_effects"] == ("require_schedule_rationale",)


def test_ruleset_version_is_recorded_on_every_activation() -> None:
    rule = always_rule("RULE-VERSION", "audit_flag", priority=50)
    result = RuleEngine((rule,), ruleset_version="2.3.4").run(build_context())
    assert result.rule_outputs[0]["version"] == "1.0.0"
    assert result.rule_outputs[0]["ruleset_version"] == "2.3.4"


def test_invalid_ruleset_version_is_rejected() -> None:
    rule = always_rule("RULE-VERSION", "audit_flag", priority=50)
    with pytest.raises(ValueError, match="ruleset_version"):
        RuleEngine((rule,), ruleset_version="v2")


@pytest.mark.parametrize(
    ("version", "severity", "priority", "message"),
    [
        ("1", "warning", 50, "version"),
        ("1.0.0", "urgent", 50, "severity"),
        ("1.0.0", "warning", 101, "priority"),
        ("1.0.0", "warning", -1, "priority"),
    ],
)
def test_invalid_rule_governance_metadata_is_rejected(
    version: str,
    severity: str,
    priority: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        Rule(
            rule_id="RULE-BAD",
            version=version,
            severity=severity,
            effects=("audit_flag",),
            predicate=lambda _: True,
            rationale=lambda _: "bad rule",
            priority=priority,
        )

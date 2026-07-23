from dataclasses import replace
from datetime import datetime, timezone

from src.domain.models import AnalysisSession, MatchContext, MatchInfo, TeamInfo
from src.rules.engine import RuleEngine


def build_context(stage: str | None = None) -> MatchContext:
    return MatchContext(
        session=AnalysisSession(
            session_id="football-rule-session",
            created_at=datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
            prism_version="3.2.0-alpha1",
        ),
        match=MatchInfo(
            match_id="football-rule-match",
            competition="Test League",
            kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
            stage=stage,
        ),
        home_team=TeamInfo(team_id="home", name="Home FC"),
        away_team=TeamInfo(team_id="away", name="Away FC"),
    )


def rule_ids(context: MatchContext) -> tuple[object, ...]:
    return tuple(output["rule_id"] for output in context.rule_outputs)


def test_first_leg_rule_normalizes_stage_text() -> None:
    result = RuleEngine().run(build_context("First Leg"))
    assert rule_ids(result) == ("RULE-F001",)


def test_unconfirmed_lineup_rule_requires_explicit_false() -> None:
    missing = RuleEngine().run(build_context())
    unconfirmed = RuleEngine().run(replace(build_context(), lineups={"confirmed": False}))
    confirmed = RuleEngine().run(replace(build_context(), lineups={"confirmed": True}))
    assert "RULE-L001" not in rule_ids(missing)
    assert "RULE-L001" in rule_ids(unconfirmed)
    assert "RULE-L001" not in rule_ids(confirmed)


def test_material_market_movement_uses_absolute_threshold() -> None:
    below = RuleEngine().run(
        replace(build_context(), market={"home_odds_move_pct": -0.119})
    )
    at_threshold = RuleEngine().run(
        replace(build_context(), market={"away_odds_move_pct": 0.12})
    )
    assert "RULE-MKT001" not in rule_ids(below)
    assert "RULE-MKT001" in rule_ids(at_threshold)


def test_boolean_market_movement_is_ignored() -> None:
    result = RuleEngine().run(replace(build_context(), market={"home_odds_move_pct": True}))
    assert "RULE-MKT001" not in rule_ids(result)


def test_preseason_and_early_season_rules_activate() -> None:
    preseason = RuleEngine().run(build_context("preseason"))
    early = RuleEngine().run(build_context("early-season"))
    assert "RULE-P001" in rule_ids(preseason)
    assert "RULE-P001" in rule_ids(early)


def test_rest_disparity_requires_both_numeric_values() -> None:
    missing = RuleEngine().run(replace(build_context(), schedule={"home_rest_days": 7}))
    balanced = RuleEngine().run(
        replace(build_context(), schedule={"home_rest_days": 6, "away_rest_days": 4})
    )
    large_gap = RuleEngine().run(
        replace(build_context(), schedule={"home_rest_days": 8, "away_rest_days": 3})
    )
    assert "RULE-S002" not in rule_ids(missing)
    assert "RULE-S002" not in rule_ids(balanced)
    assert "RULE-S002" in rule_ids(large_gap)


def test_boolean_rest_day_values_are_ignored_for_disparity() -> None:
    result = RuleEngine().run(
        replace(build_context(), schedule={"home_rest_days": True, "away_rest_days": 7})
    )
    assert "RULE-S002" not in rule_ids(result)


def test_multiple_football_rules_accumulate_deterministically() -> None:
    context = replace(
        build_context("first_leg"),
        lineups={"confirmed": False},
        market={"draw_odds_move_pct": -0.20},
        schedule={"home_rest_days": 8, "away_rest_days": 3},
    )
    result = RuleEngine().run(context)
    ids = rule_ids(result)
    assert ids == ("RULE-S001", "RULE-F001", "RULE-L001", "RULE-MKT001", "RULE-S002")

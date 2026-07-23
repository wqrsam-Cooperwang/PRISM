"""Football-specific deterministic rules for PRISM."""

from __future__ import annotations

from src.domain.models import MatchContext
from src.rules.models import Rule

_MARKET_MOVE_KEYS = (
    "home_odds_move_pct",
    "draw_odds_move_pct",
    "away_odds_move_pct",
)


def _normalized_stage(context: MatchContext) -> str:
    stage = context.match.stage
    if stage is None:
        return ""
    return stage.strip().lower().replace("-", "_").replace(" ", "_")


def _first_leg(context: MatchContext) -> bool:
    return _normalized_stage(context) == "first_leg"


def _lineup_unconfirmed(context: MatchContext) -> bool:
    return context.lineups.get("confirmed") is False


def _material_market_move(context: MatchContext) -> bool:
    for key in _MARKET_MOVE_KEYS:
        value = context.market.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and abs(float(value)) >= 0.12:
            return True
    return False


def _preseason_or_early(context: MatchContext) -> bool:
    return _normalized_stage(context) in {"preseason", "early_season"}


def _rest_disparity(context: MatchContext) -> bool:
    home = context.schedule.get("home_rest_days")
    away = context.schedule.get("away_rest_days")
    if isinstance(home, bool) or isinstance(away, bool):
        return False
    if not isinstance(home, (int, float)) or not isinstance(away, (int, float)):
        return False
    return abs(float(home) - float(away)) >= 4.0


FOOTBALL_RULES = (
    Rule(
        "RULE-F001",
        "1.0.0",
        "info",
        ("apply_first_leg_caution", "avoid_overconfident_game_state_assumption"),
        _first_leg,
        lambda _: "Match stage is first leg; downstream analysis must acknowledge leg context.",
    ),
    Rule(
        "RULE-L001",
        "1.0.0",
        "warning",
        ("require_lineup_confirmation", "restrict_high_confidence_action"),
        _lineup_unconfirmed,
        lambda _: "Lineups are explicitly marked as unconfirmed.",
    ),
    Rule(
        "RULE-MKT001",
        "1.0.0",
        "warning",
        ("flag_market_movement", "require_market_rationale"),
        _material_market_move,
        lambda _: "At least one supported odds movement is 12% or greater in absolute terms.",
    ),
    Rule(
        "RULE-P001",
        "1.0.0",
        "warning",
        ("apply_season_phase_caution", "downweight_historical_form_confidence"),
        _preseason_or_early,
        lambda _: "Match is explicitly marked as preseason or early season.",
    ),
    Rule(
        "RULE-S002",
        "1.0.0",
        "info",
        ("flag_rest_disparity", "require_schedule_rationale"),
        _rest_disparity,
        lambda _: "The explicit rest-day difference between teams is at least four days.",
    ),
)

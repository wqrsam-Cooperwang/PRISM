# PRISM Football Rule Pack V1

## Purpose

This rule pack adds football-specific caution signals on top of the generic
Rule Engine. Rules consume only explicit structured MatchContext fields and
produce auditable effects. They do not predict scores or make final decisions.

## Input conventions

### Match stage

`MatchInfo.stage` may use canonical values such as:

- `first_leg`
- `second_leg`
- `preseason`
- `early_season`

For compatibility, spaces and hyphens are normalized to underscores.

### Lineups

`context.lineups["confirmed"]` is used only when it is explicitly boolean.
Missing information does not trigger the lineup rule.

### Market movement

The rule pack reads any numeric values present under:

- `home_odds_move_pct`
- `draw_odds_move_pct`
- `away_odds_move_pct`

Values are signed decimal percentages; for example `-0.15` means a 15% move.

### Schedule

`home_rest_days` and `away_rest_days` must both be explicit numeric values for
rest-disparity evaluation.

## Rules

### RULE-F001 — First-Leg Caution

Trigger: normalized stage equals `first_leg`.

Severity: info.

Effects:
- `apply_first_leg_caution`
- `avoid_overconfident_game_state_assumption`

Rationale: first legs often leave strategic flexibility for the return leg, so
downstream components should explicitly acknowledge leg context.

### RULE-L001 — Lineup Not Confirmed

Trigger: `lineups.confirmed is False`.

Severity: warning.

Effects:
- `require_lineup_confirmation`
- `restrict_high_confidence_action`

### RULE-MKT001 — Material Odds Movement

Trigger: absolute value of any supported odds movement is at least 0.12.

Severity: warning.

Effects:
- `flag_market_movement`
- `require_market_rationale`

The threshold is a V1 governance constant and must be versioned when changed.

### RULE-P001 — Preseason / Early-Season Caution

Trigger: normalized stage is `preseason` or `early_season`.

Severity: warning.

Effects:
- `apply_season_phase_caution`
- `downweight_historical_form_confidence`

### RULE-S002 — Rest-Day Disparity

Trigger: both rest-day values are explicit numeric values and the absolute
difference is at least 4 days.

Severity: info.

Effects:
- `flag_rest_disparity`
- `require_schedule_rationale`

## Non-goals

- No inferred lineup status from free text.
- No inferred competition phase from web data.
- No odds scraping.
- No competition-specific tactical assumptions.
- No final betting action.

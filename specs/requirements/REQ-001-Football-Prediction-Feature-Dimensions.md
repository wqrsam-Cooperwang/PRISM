# REQ-001: Football Prediction Feature Dimensions

## Status

Accepted raw requirement for engineering decomposition under PRISM Enterprise 2026.1.

## Requirement

The following football-match prediction feature set MUST be incorporated into the PRISM API Data Pipeline and Feature Engineering modules.

The implementation MUST distinguish static indicators from dynamic/time-decayed metrics and MUST document which observations can be collected at T-24h, T-12h, and which are late/live parameters.

## 1. Performance & xG Data

- Home/away recent xG, xGA, and xPTS.
- Box shots, shot-on-target rate, Big Chances Created, and Big Chances Conceded.
- Possession, pass-completion rate, and PPDA.
- Five-match and ten-match rolling points and goal difference.
- Recent-form metrics must apply time-decay weighting so newer matches have greater influence.

## 2. Roster, Lineup & Availability

### Injuries and suspensions

- Missing-player importance must be weighted rather than treated as a simple player count.
- The system must distinguish the impact of a starting striker, centre-back, goalkeeper, substitute, and other positional roles.
- Missing-player effects must be separated into attacking and defensive weakening coefficients.

### Squad rotation and fatigue

- Accumulated minutes for core players under congested scheduling.
- Bench depth and substitution quality.

### Transfers and regime breaks

- New-manager window and coaching-style change.
- Registration status and integration level of key new signings.

## 3. Market Implied Data

- Opening and subsequent 1X2, Asian handicap, and totals prices.
- De-vigged implied probabilities after bookmaker margin removal.
- Market heat, price/line direction, and divergence from fundamentals.
- Market anomalies may be used to identify excessive popularity or suspicious movement, but must not be interpreted as certain evidence of manipulation.

## 4. Context, Schedule & Motivation

### Tournament priority

- Match importance within the season, including relegation, qualification, title, dead-rubber, and lower-priority cup contexts.

### Fixture congestion

- Previous and next high-intensity fixtures, European matches, derbies, and cup ties.

### Aggregate score and round logic

- First-leg score and aggregate state.
- Competition rules including away-goal rules where historically applicable, extra time, and penalties.
- Incentive effects such as a team protecting a large first-leg lead.

### Tactical matchup

- Possession versus counterattack.
- Crossing/aerial play versus small or ground-oriented defensive structures.
- Set-piece attacking and defending strength, including corners and set-piece goals for/against.

## 5. Environment & Geography

### Travel and logistics

- Travel distance and time-zone displacement.
- Rest-days difference.

### Weather impact

- Rainfall and snowfall.
- Temperature extremes.
- Wind speed.

### Geography and pitch

- Altitude.
- Natural grass versus artificial turf.
- Pitch dimensions and relevant tactical effects.

## 6. Referee, Discipline & Home Advantage

### Home advantage

- Historical home performance.
- Attendance and intense home-atmosphere indicators.

### Referee profile

- Yellow cards, red cards, penalties, and relevant intervention tendencies.

### Team discipline

- Fouls, accumulated cards, and suspension-risk status for key players.

## Timing classification requirement

Each engineered feature MUST be assigned one of the timing classes below:

- `Season-static`
- `T-7d`
- `T-72h`
- `T-24h`
- `T-12h`
- `T-6h`
- `T-3h`
- `T-60m`
- `Post-match-only`

Expected lineups, projected rotation, projected injuries, and projected tactical changes are uncertain events. They MUST be represented using confidence-weighted scenarios rather than being treated as confirmed events.

Official starting lineups and true closing prices are late parameters and MUST NOT leak into an earlier production prediction cutoff. They may be retained for Shadow evaluation and post-match comparison.

## Engineering outputs

This requirement is decomposed into:

1. `SPEC-001-Feature-Registry.md` — governance and schema.
2. `catalog.csv` — canonical feature definitions.
3. `api_mapping.csv` — source and collection mapping.
4. Future pipeline adapters, feature transforms, validation tests, and confidence logic.

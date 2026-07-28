# SPEC-001: Feature Registry Specification

## Status

Draft — PRISM Enterprise 2026.1

## Purpose

This specification defines the mandatory schema, governance rules, lifecycle, timing controls, and validation requirements for every predictive feature used by PRISM Enterprise.

GitHub is the single source of truth. A feature may not enter production merely because it appeared in a conversation, report, notebook, or model experiment.

## Required feature schema

Every feature MUST define:

- `feature_id`: stable unique identifier.
- `name`: human-readable name.
- `layer`: exactly one of L1–L9.
- `category`: functional grouping.
- `metric_type`: `Static`, `Dynamic`, `Time-Decayed`, `Event`, or `Derived`.
- `description`: precise definition and unit.
- `data_source`: provider or derivation method.
- `earliest_available`: first legitimate pre-match availability window.
- `update_frequency`: expected refresh cadence.
- `decay_method`: none, EWMA, half-life, rolling window, or scenario mixture.
- `target_engine`: model component affected.
- `confidence_default`: default reliability in [0,1].
- `correlation_group`: evidence family used for double-counting control.
- `lifecycle`: Draft, Experimental, Shadow, Candidate, Production, Deprecated, or Retired.
- `version_introduced`: product version.
- `owner`: responsible module or team.

## Layer model

- **L1 Static Strength** — long-run team, squad, coach, and venue strength.
- **L2 Time-Decayed Performance** — recent xG, shot quality, pressing, possession, and form.
- **L3 Squad & Availability** — injuries, suspensions, fatigue, depth, registration, and regime breaks.
- **L4 Market Intelligence** — de-vigged probabilities, price movement, and market anomalies.
- **L5 Match Context** — competition priority, motivation, congestion, and two-leg incentives.
- **L6 Environment & Geography** — travel, rest, weather, altitude, pitch, and logistics.
- **L7 Referee, Discipline & Home Advantage** — referee profile, cards, penalties, attendance, and home atmosphere.
- **L8 Tactical Matchup** — style interaction, set pieces, pressing, transitions, and aerial/ground mismatch.
- **L9 Confidence & Data Quality** — source consensus, uncertainty, missingness, and prediction confidence.

## Timing and leakage rules

Allowed registry timing values:

- `Season-static`
- `T-7d`
- `T-72h`
- `T-24h`
- `T-12h`
- `T-6h`
- `T-3h`
- `T-60m`
- `Post-match-only`

The official production prediction profile MUST declare its cutoff. Data first available after that cutoff is prohibited from production inference.

Official starting lineups and true closing prices are normally `T-60m` or later and therefore belong to Shadow evaluation unless the selected prediction profile explicitly permits them.

## Static vs dynamic metrics

- **Static**: changes slowly and is refreshed weekly, monthly, or after a structural event.
- **Dynamic**: changes match by match or intraday.
- **Time-Decayed**: dynamic historical observations weighted toward recent matches.
- **Event**: discrete information such as a suspension, registration, or coach change.
- **Derived**: computed from registered inputs.

Time-decayed performance features SHOULD use EWMA or an explicitly documented half-life. Simple unweighted last-N averages require justification.

## Confidence and consensus

Reliability is attached to the observation, not merely to the feature definition.

When multiple sources disagree, the Data Consensus Engine MUST:

1. record source identities and timestamps;
2. score source authority and agreement;
3. produce a consensus value and confidence;
4. avoid a deterministic lambda adjustment when confidence is below the configured threshold;
5. widen scenario variance or use probabilistic scenario mixing instead.

## Double-counting control

Features sharing a `correlation_group` MUST NOT be treated as independent evidence by default.

Examples:

- ELO, SPI, 1X2, Asian handicap, and favourite status may all express latent team strength.
- xG, shots, shots on target, and big chances may overlap as attacking-process evidence.
- injuries, predicted lineups, and player-importance loss may describe the same personnel event.

The consuming engine MUST document whether it selects, blends, residualises, or caps correlated evidence.

## Lifecycle

`Draft → Experimental → Shadow → Candidate → Production → Deprecated → Retired`

Promotion requires reproducible validation, leakage checks, calibration review, and evidence that the feature adds value beyond correlated existing features.

## Acceptance checklist

A feature cannot be merged into production unless:

- its ID is unique;
- its layer and lifecycle are valid;
- source, timing, decay, confidence, and target engine are defined;
- its correlation group is declared;
- tests verify schema validity;
- historical evaluation is leakage-safe;
- promotion criteria are satisfied.

## Canonical files

- `specs/feature-registry/catalog.csv`
- `specs/feature-registry/api_mapping.csv`
- `specs/requirements/REQ-001-Football-Prediction-Feature-Dimensions.md`

These files jointly define the initial PRISM Enterprise 2026.1 feature and data-pipeline baseline.

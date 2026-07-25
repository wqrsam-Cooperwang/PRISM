# PRISM Collection Readiness / Source Coverage Gate V1

## Objective

Decide whether a verified multi-source intelligence bundle is sufficiently complete to enter the baseline prediction path.

The gate consumes existing verification output. It does not re-verify claims, create features, or alter model probabilities.

## Decisions

- `READY`: all core pre-match intelligence categories are covered and the existing intelligence readiness is `STANDARD` or `DEEP`.
- `DEGRADED`: both baseline prediction families remain runnable, but one or more contextual core categories are missing or the existing intelligence readiness is `LIMITED`.
- `REJECTED`: the minimum inputs needed to run both baseline models are not simultaneously available, or the existing intelligence readiness is `REJECTED`.

## Core category coverage

V1 core categories are:

- `TEAM_STRENGTH`
- `RECENT_FORM`
- `AVAILABILITY`
- `SCHEDULE`
- `MARKET`

`LINEUP` and `WEATHER` are tracked as optional contextual coverage in V1.

## Baseline minimum

The current baseline prediction suite contains:

- Elo probability model, requiring usable `TEAM_STRENGTH` data for both sides;
- Market probability model, requiring usable `MARKET` 1X2 data.

The gate therefore rejects a bundle unless both baseline families can be supported.

## Source coverage

The decision records deterministic source coverage metadata:

- covered and missing core categories;
- covered optional categories;
- distinct source identifiers;
- distinct source types;
- whether Elo and Market baseline inputs are available;
- gate reasons.

Source count alone never upgrades a decision. Multiple weak or duplicate sources do not substitute for category coverage.

## Governance

1. Missing data is never imputed by the gate.
2. Conflicted claims only count as covered when the existing verification/category assessment marks the category covered via another usable claim.
3. Gate output is deterministic for the same frozen `IntelligenceBundle`.
4. Prediction orchestration may enforce the gate, but the gate itself does not execute models.

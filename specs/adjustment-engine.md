# PRISM Adjustment Engine V1 Specification

## Purpose

The Adjustment Engine converts governed Rule Engine effects into operational,
auditable confidence constraints without mutating raw model probabilities or
rewriting the original ConfidenceOutput.

It sits after Rule Engine and before downstream consensus/decision logic.

## Scientific constraint

V1 MUST NOT invent uncalibrated additive or multiplicative penalties for every
football warning. Only effects with an explicit governance meaning may alter
confidence numerically. Informational football effects remain auditable but do
not receive arbitrary weights until historical validation supports them.

## Inputs

- `MatchContext.confidence` must exist.
- `MatchContext.rule_outputs` may be empty.
- Only `effective_effects` from governed rule outputs are consumed. Suppressed
  effects MUST NOT alter the adjustment result.

## Output

`MatchContext.adjustment` contains:

- `base_confidence`: original confidence overall score.
- `adjusted_confidence`: final score after the strongest applicable ceiling.
- `confidence_cap`: applied ceiling or `null` when no ceiling applies.
- `decision_blocked`: true only when `block_active_decision` is effective.
- `applied_effects`: unique effective decision-restriction effects used.
- `observed_effects`: all unique effective rule effects seen by the engine.
- `rationale`: deterministic audit strings.

The original `ConfidenceOutput` remains unchanged.

## V1 calibrated governance mapping

The following ceilings encode the already-defined semantic meaning of governed
restriction effects rather than empirical football-performance weights:

- `block_active_decision` -> confidence cap `0.34`, decision blocked.
- `restrict_active_decision` -> confidence cap `0.49`.
- `restrict_high_confidence_action` -> confidence cap `0.69`.

When multiple restriction effects are present, the strictest (lowest) cap wins.

## Non-numeric effects

Examples such as `flag_market_movement`, `apply_first_leg_caution`,
`require_schedule_rationale`, and `downweight_historical_form_confidence` are
recorded in `observed_effects` but do not change confidence numerically in V1.
A future calibrated version may promote selected effects into numeric mappings
only after backtesting and an ADR/spec change.

## Constraints

- Deterministic and immutable.
- No modification of `ModelOutput` probabilities.
- No modification of `ConfidenceOutput`.
- Suppressed rule effects are ignored numerically.
- Duplicate effective effects are deduplicated while preserving first-seen
  order.
- Missing confidence raises `ValueError`.

## Acceptance criteria

1. No rules -> adjusted confidence equals base confidence.
2. Strongest restriction cap wins regardless of rule order.
3. A blocked decision produces `decision_blocked=True` and cap `0.34`.
4. Suppressed restrictions cannot influence adjustment.
5. Informational effects are observed but not numerically penalized.
6. Input MatchContext remains unchanged.
7. Evidence -> Confidence -> Rule -> Adjustment pipeline is integration tested.

# PRISM Rule Governance V1 Specification

## Purpose

Rule Governance defines how activated rules are ordered, resolved, versioned,
and exposed to downstream engines. It extends deterministic rule evaluation
without turning the Rule Engine into a Decision Engine.

## Principles

1. Explicit priority, never implicit file order.
2. Stronger restrictions dominate weaker restrictions in the same effect family.
3. Independent warnings and evidence requirements remain additive.
4. Every activation records both its rule version and the registry/ruleset version.
5. Resolution is deterministic and auditable.
6. No activated rule is deleted from the audit trail; suppressed effects remain visible.

## Rule metadata

Every Rule has:

- `rule_id`: stable identifier.
- `version`: semantic rule version (`MAJOR.MINOR.PATCH`).
- `severity`: `info`, `warning`, or `critical`.
- `priority`: integer from 0 to 100; higher executes first.
- `effects`: machine-readable downstream effects.
- predicate and rationale callables.

## Activation output

Each activated rule output contains:

- `rule_id`
- `version`
- `ruleset_version`
- `severity`
- `priority`
- `rationale`
- `effects`: original declared effects
- `effective_effects`: effects that survive conflict resolution
- `suppressed_effects`: effects superseded by stronger/higher-priority effects
- `status`: `active` or `partially_suppressed` or `suppressed`

## Ordering

Activated rules are sorted by:

1. priority descending
2. severity rank descending (`critical > warning > info`)
3. rule id ascending

This removes dependence on registry/file order.

## Conflict resolution V1

### Decision restriction family

The following effects belong to one dominance family:

1. `block_active_decision` — strongest
2. `restrict_active_decision`
3. `restrict_high_confidence_action` — weakest

When multiple effects from this family activate, only the strongest surviving
restriction remains effective. Weaker effects are retained in the activation's
`suppressed_effects` for auditability.

### Duplicate effects

If the exact same effect is emitted by multiple rules, the highest-ranked rule
owns the effective effect. Lower-ranked duplicates are suppressed.

### Additive effects

Effects outside a declared dominance family are additive and remain effective.
Examples include evidence requirements, uncertainty rationale requirements,
market flags, first-leg caution, season-phase caution, and schedule flags.

## Versioning

- Rule versions use semantic version strings.
- Rule Engine exposes a `ruleset_version` representing the registry composition
  and conflict policy used for the run.
- Every activation records `ruleset_version` so historical analyses can identify
  exactly which governance contract produced them.
- Changing rule logic requires incrementing that rule's version.
- Changing registry composition or conflict policy requires incrementing
  `ruleset_version`.

## Validation

The registry rejects:

- duplicate rule ids
- invalid severity values
- priorities outside 0..100
- non-semantic rule versions
- non-semantic ruleset versions

## Non-goals

- Final bet/no-bet selection.
- Market expected-value calculation.
- Confidence score mutation.
- Hidden probabilistic arbitration between rules.

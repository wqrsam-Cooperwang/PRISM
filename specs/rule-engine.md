# PRISM Rule Engine V1 Specification

## Purpose

The Rule Engine converts explicit match-state conditions into deterministic,
auditable rule activations. It must not make betting decisions or silently
change model probabilities. Its job is to record which PRISM rules fired, why
they fired, their severity, and what downstream constraint they imply.

## Design principles

1. Deterministic: identical MatchContext input produces identical outputs.
2. Auditable: every activation includes rule id, version, severity, rationale,
   and effects.
3. Conservative: evidence and confidence gates can restrict downstream action.
4. Immutable: the engine returns a new MatchContext.
5. Extensible: rules live in a registry and can be added without changing the
   evaluation loop.
6. No hidden inference: V1 rules consume explicit structured context fields.

## Rule output schema

Each activated rule is stored in `MatchContext.rule_outputs` as a mapping with:

- `rule_id`: stable identifier.
- `version`: rule version.
- `severity`: info, warning, critical.
- `rationale`: human-readable reason.
- `effects`: tuple of machine-readable downstream effects.

## V1 rules

### RULE-E001 — Rejected Evidence Lock

Trigger: `context.evidence.gate == rejected`.

Severity: critical.

Effects:
- `block_active_decision`
- `require_more_evidence`

### RULE-E002 — Limited Evidence Constraint

Trigger: `context.evidence.gate == limited`.

Severity: warning.

Effects:
- `restrict_high_confidence_action`
- `require_evidence_warning`

### RULE-C001 — Low Confidence Constraint

Trigger: confidence exists and `confidence.band` is `very_low` or `low`.

Severity: warning.

Effects:
- `restrict_active_decision`

### RULE-M001 — Material Model Disagreement

Trigger: at least two model outputs exist and the maximum range across home,
draw, or away probabilities is >= 0.30.

Severity: warning.

Effects:
- `flag_model_disagreement`
- `require_uncertainty_rationale`

### RULE-S001 — Short Turnaround

Trigger: explicit `home_rest_days` or `away_rest_days` in `context.schedule` is
numeric and <= 3.

Severity: info.

Effects:
- `apply_schedule_caution`

## Evaluation and conflict policy

- All rules are evaluated independently in registry order.
- Only activated rules are emitted.
- Duplicate rule ids are forbidden in the registry.
- Effects are additive; the Rule Engine does not resolve them into a final
  DecisionOutput. Decision Engine owns that responsibility.
- Critical restrictions dominate downstream warning/info effects.

## Non-goals for V1

- No odds/value calculation.
- No final score prediction.
- No free-text tactical inference.
- No automatic mutation of confidence/model outputs.
- No competition-specific rules until their input contracts are explicit.

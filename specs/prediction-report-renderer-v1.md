# PRISM Prediction Report Renderer V1

## Purpose

The renderer converts an immutable `PredictionReport` into a human-readable Markdown document.
It is presentation-only. It must not invoke engines, recalculate analytical values, or change report semantics.

## Input

`PredictionReport`

## Output

A deterministic UTF-8 Markdown string.

## Required sections and order

1. Title
2. Match
3. 1X2 Consensus
4. Confidence and Evidence
5. Decision
6. Top 3 Scorelines
7. Rules and Adjustment
8. Provenance

## Formatting rules

- Probabilities and confidence values are displayed as percentages with one decimal place.
- Expected value is displayed as a signed percentage with one decimal place when present.
- Expected goals are displayed with two decimal places when present.
- Exact-score probabilities are displayed as percentages with one decimal place.
- Missing optional values are rendered as `N/A`.
- Empty warning, penalty, rule, and rationale collections render as `None`.
- The renderer must preserve the existing order of scorelines, rule outputs, penalties, warnings, rationale, and engine trace.
- Datetimes use ISO-8601 representation from the report model.

## Decision semantics

The renderer displays the canonical decision action exactly as provided by the report. It must not upgrade or downgrade `no_decision`, `watch`, `no_bet`, or `candidate`.

## Scoreline semantics

When scoreline output is unavailable, the renderer displays `Unavailable` and must not fabricate exact scores.

## Governance invariants

1. Read-only and deterministic.
2. No analytical engine calls.
3. No probability normalization or recomputation.
4. No inferred risk labels or market recommendations.
5. No replacement of missing values with guessed values.
6. No hidden filtering of warnings, rules, rationale, or provenance.

## V1 API

```python
render_prediction_report_markdown(report: PredictionReport) -> str
```

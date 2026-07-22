# Evidence Engine Specification

Version: 0.1.0
Status: Experimental
Target release: PRISM 3.1

## 1. Purpose

The Evidence Engine is the first analytical gate in PRISM. It evaluates whether the available match information is sufficiently complete, current, and reliable to support deeper analysis.

It does not predict match outcomes.

## 2. Responsibilities

The engine must:

- Validate the evidence payload.
- Score each evidence category independently.
- Calculate a reproducible total Evidence Score from 0 to 100.
- Record missing and invalid categories.
- Apply critical-data caps.
- Assign a quality gate.
- Return a structured audit result.

The engine must not:

- Infer missing facts.
- Invent sources or timestamps.
- Call external AI systems.
- Modify model probabilities.
- Produce betting recommendations.

## 3. Inputs

The MVP accepts a mapping where each supported category has a completeness value from `0.0` to `1.0`.

Supported categories and weights:

| Category | Weight |
|---|---:|
| lineup | 20 |
| injuries | 10 |
| odds | 15 |
| weather | 10 |
| tactical_data | 15 |
| historical_data | 15 |
| market_data | 10 |
| motivation | 5 |
| **Total** | **100** |

Example:

```python
{
    "lineup": 1.0,
    "injuries": 0.8,
    "odds": 1.0,
    "weather": 0.5,
    "tactical_data": 0.9,
    "historical_data": 1.0,
    "market_data": 0.7,
    "motivation": 0.6,
}
```

### Input Rules

- Unknown categories are rejected.
- Values must be numeric.
- Boolean values are rejected even though Python treats them as integers.
- Values must remain within `0.0 <= value <= 1.0`.
- Missing categories are treated as zero completeness and reported.

## 4. Outputs

The result must contain:

- `score`: integer from 0 to 100.
- `raw_score`: unrounded weighted score.
- `gate`: `deep`, `standard`, `limited`, or `rejected`.
- `category_scores`: weighted contribution by category.
- `missing_categories`: categories omitted or scored zero.
- `warnings`: human-readable audit warnings.
- `critical_caps_applied`: any caps that changed the gate.

## 5. Processing Flow

1. Validate input type.
2. Reject unsupported category names.
3. Validate every supplied completeness value.
4. Fill omitted categories with zero.
5. Multiply each completeness value by its category weight.
6. Sum category scores.
7. Round the displayed score to the nearest integer.
8. Determine the numerical gate.
9. Apply critical-data caps.
10. Return the immutable audit result.

## 6. Quality Gate Thresholds

| Score | Gate |
|---:|---|
| 85–100 | `deep` |
| 70–84 | `standard` |
| 45–69 | `limited` |
| 0–44 | `rejected` |

## 7. Critical-Data Caps

The MVP applies these safeguards:

- `lineup < 0.25`: maximum gate is `limited`.
- `odds == 0`: maximum gate is `limited`.
- both `lineup == 0` and `injuries == 0`: gate is `rejected`.
- three or more zero-completeness categories: maximum gate is `limited`.

A cap may lower a gate but never raise it.

## 8. Error Handling

The engine raises:

- `TypeError` when the top-level payload is not a mapping.
- `ValueError` for unknown categories, booleans, non-numeric values, NaN, infinity, or values outside the valid range.

Missing supported categories are not exceptions. They are scored as zero and included in warnings.

## 9. Acceptance Criteria

The MVP is accepted when:

- The same valid input always produces the same result.
- Category contributions sum to the raw score.
- A complete payload produces score 100 and gate `deep`.
- An empty payload produces score 0 and gate `rejected`.
- Missing odds prevents `deep` or `standard` output.
- Missing lineup and injuries forces rejection.
- Invalid values are rejected explicitly.
- Unit tests cover all thresholds and critical caps.

## 10. Future Extensions

Later versions may add:

- Source reliability.
- Recency decay.
- Cross-source agreement.
- Competition-specific weights.
- Confirmed versus expected lineup distinction.
- Provenance and timestamp validation.
- Learned calibration based on post-match performance.

These extensions must preserve deterministic auditability and require a specification update before implementation.

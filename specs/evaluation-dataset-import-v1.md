# PRISM Dataset Import / Benchmark Loader V1

## Purpose

Load previously exported PRISM evaluation datasets into validated immutable records and derive read-only benchmark summaries without re-running prediction engines.

## Inputs

Supported payload formats:

- JSON Lines (`jsonl`) emitted by Calibration Dataset Export V1
- CSV emitted by Calibration Dataset Export V1

Optional input:

- `DatasetManifest` emitted alongside the payload

## Dataset import invariants

1. Import must never invoke PRISM analytical engines.
2. Every row must contain exactly the V1 `EvaluationRecord` field set.
3. `dataset_schema_version` must equal the currently supported schema version (`1.0.0`).
4. JSONL rows must be JSON objects.
5. CSV headers must exactly match the canonical export header order.
6. Numeric fields must parse to their canonical Python numeric types.
7. Boolean fields must use canonical `true` / `false` values.
8. Nullable boolean and string fields may be empty in CSV and `null` in JSONL.
9. Imported records preserve source row order.
10. Empty datasets are rejected.

## Manifest verification

When a `DatasetManifest` is supplied, import must verify before records are accepted:

- manifest dataset schema version matches the supported schema version
- manifest format matches the import function
- `record_count` matches parsed records
- SHA-256 equals the exact UTF-8 payload bytes
- manifest PRISM-version set matches imported records
- manifest Git-commit set matches imported records

Any mismatch fails closed with `ValueError`.

## Benchmark Loader

`BenchmarkSummary` is a read-only aggregation over imported historical `EvaluationRecord` objects.

Required V1 metrics:

- record count
- mean Brier score
- mean log loss
- Top-1 accuracy
- scoreline available count
- Top-3 scoreline hit rate among available scoreline observations
- candidate count
- candidate accuracy among candidate observations
- mean overall confidence
- PRISM versions present
- runtime versions present
- Git commits present
- competitions present

## Governance

The benchmark loader is descriptive only.

V1 MUST NOT:

- retrain or recalibrate models
- change rules
- change confidence thresholds
- change decision thresholds
- infer missing values
- treat benchmark results as new prediction inputs

## Public API

```python
import_evaluation_jsonl(payload: str, manifest: DatasetManifest | None = None) -> tuple[EvaluationRecord, ...]
import_evaluation_csv(payload: str, manifest: DatasetManifest | None = None) -> tuple[EvaluationRecord, ...]
load_benchmark(records: Iterable[EvaluationRecord]) -> BenchmarkSummary
```

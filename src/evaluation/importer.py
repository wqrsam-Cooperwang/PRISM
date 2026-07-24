"""Strict calibration dataset import and read-only benchmark aggregation."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from src.evaluation.dataset import DATASET_SCHEMA_VERSION, DatasetManifest, EvaluationRecord

_RECORD_FIELDS = tuple(EvaluationRecord.__dataclass_fields__)
_INT_FIELDS = {"actual_home_goals", "actual_away_goals"}
_FLOAT_FIELDS = {
    "home_probability",
    "draw_probability",
    "away_probability",
    "leading_probability",
    "brier_score",
    "log_loss",
    "overall_confidence",
}
_BOOL_FIELDS = {"top1_correct"}
_NULLABLE_BOOL_FIELDS = {"scoreline_top3_hit", "candidate_correct"}
_NULLABLE_STRING_FIELDS = {
    "selected_market",
    "git_commit",
    "data_version",
    "rule_version",
    "model_version",
    "prompt_version",
}


@dataclass(frozen=True)
class BenchmarkSummary:
    record_count: int
    mean_brier_score: float
    mean_log_loss: float
    top1_accuracy: float
    scoreline_available_count: int
    scoreline_top3_hit_rate: float | None
    candidate_count: int
    candidate_accuracy: float | None
    mean_overall_confidence: float
    prism_versions: tuple[str, ...]
    runtime_versions: tuple[str, ...]
    git_commits: tuple[str, ...]
    competitions: tuple[str, ...]


def _parse_bool(value: Any, name: str, *, nullable: bool = False) -> bool | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if nullable and normalized == "":
            return None
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    raise ValueError(f"{name} must be true or false")


def _parse_record(raw: Mapping[str, Any]) -> EvaluationRecord:
    keys = tuple(raw.keys())
    if set(keys) != set(_RECORD_FIELDS):
        missing = sorted(set(_RECORD_FIELDS) - set(keys))
        extra = sorted(set(keys) - set(_RECORD_FIELDS))
        raise ValueError(f"evaluation record fields mismatch: missing={missing}, extra={extra}")

    values: dict[str, Any] = {}
    for field_name in _RECORD_FIELDS:
        value = raw[field_name]
        if field_name in _INT_FIELDS:
            try:
                values[field_name] = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{field_name} must be an integer") from exc
        elif field_name in _FLOAT_FIELDS:
            try:
                values[field_name] = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{field_name} must be numeric") from exc
        elif field_name in _BOOL_FIELDS:
            values[field_name] = _parse_bool(value, field_name)
        elif field_name in _NULLABLE_BOOL_FIELDS:
            values[field_name] = _parse_bool(value, field_name, nullable=True)
        elif field_name in _NULLABLE_STRING_FIELDS:
            values[field_name] = None if value is None or value == "" else str(value)
        else:
            if value is None:
                raise ValueError(f"{field_name} must not be null")
            values[field_name] = str(value)

    if values["dataset_schema_version"] != DATASET_SCHEMA_VERSION:
        raise ValueError(
            "unsupported dataset_schema_version: "
            f"{values['dataset_schema_version']}"
        )
    return EvaluationRecord(**values)


def _verify_manifest(
    payload: str,
    records: tuple[EvaluationRecord, ...],
    manifest: DatasetManifest | None,
    *,
    format_name: Literal["jsonl", "csv"],
) -> None:
    if manifest is None:
        return
    if manifest.dataset_schema_version != DATASET_SCHEMA_VERSION:
        raise ValueError("manifest dataset schema version mismatch")
    if manifest.format != format_name:
        raise ValueError("manifest format mismatch")
    if manifest.record_count != len(records):
        raise ValueError("manifest record count mismatch")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if manifest.content_sha256 != digest:
        raise ValueError("manifest SHA-256 mismatch")
    prism_versions = tuple(sorted({record.prism_version for record in records}))
    if manifest.prism_versions != prism_versions:
        raise ValueError("manifest PRISM versions mismatch")
    git_commits = tuple(sorted({record.git_commit for record in records if record.git_commit}))
    if manifest.git_commits != git_commits:
        raise ValueError("manifest Git commits mismatch")


def import_evaluation_jsonl(
    payload: str,
    manifest: DatasetManifest | None = None,
) -> tuple[EvaluationRecord, ...]:
    """Load a strict V1 JSONL calibration dataset."""

    records: list[EvaluationRecord] = []
    for line_number, line in enumerate(payload.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at line {line_number}") from exc
        if not isinstance(raw, dict):
            raise ValueError(f"JSONL line {line_number} must be an object")
        records.append(_parse_record(raw))
    result = tuple(records)
    if not result:
        raise ValueError("evaluation dataset must contain at least one record")
    _verify_manifest(payload, result, manifest, format_name="jsonl")
    return result


def import_evaluation_csv(
    payload: str,
    manifest: DatasetManifest | None = None,
) -> tuple[EvaluationRecord, ...]:
    """Load a strict V1 CSV calibration dataset."""

    reader = csv.DictReader(io.StringIO(payload))
    if tuple(reader.fieldnames or ()) != _RECORD_FIELDS:
        raise ValueError("CSV header does not match canonical EvaluationRecord order")
    result = tuple(_parse_record(row) for row in reader)
    if not result:
        raise ValueError("evaluation dataset must contain at least one record")
    _verify_manifest(payload, result, manifest, format_name="csv")
    return result


def load_benchmark(records: Iterable[EvaluationRecord]) -> BenchmarkSummary:
    """Aggregate imported historical evaluation records without re-running PRISM."""

    items = tuple(records)
    if not items:
        raise ValueError("benchmark must contain at least one record")

    scoreline_results = tuple(
        record.scoreline_top3_hit
        for record in items
        if record.scoreline_top3_hit is not None
    )
    candidate_results = tuple(
        record.candidate_correct
        for record in items
        if record.candidate_correct is not None
    )
    count = len(items)
    return BenchmarkSummary(
        record_count=count,
        mean_brier_score=sum(record.brier_score for record in items) / count,
        mean_log_loss=sum(record.log_loss for record in items) / count,
        top1_accuracy=sum(record.top1_correct for record in items) / count,
        scoreline_available_count=len(scoreline_results),
        scoreline_top3_hit_rate=(
            None if not scoreline_results else sum(scoreline_results) / len(scoreline_results)
        ),
        candidate_count=len(candidate_results),
        candidate_accuracy=(
            None if not candidate_results else sum(candidate_results) / len(candidate_results)
        ),
        mean_overall_confidence=sum(record.overall_confidence for record in items) / count,
        prism_versions=tuple(sorted({record.prism_version for record in items})),
        runtime_versions=tuple(sorted({record.runtime_version for record in items})),
        git_commits=tuple(sorted({record.git_commit for record in items if record.git_commit})),
        competitions=tuple(sorted({record.competition for record in items})),
    )

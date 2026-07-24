"""Versioned calibration dataset records and deterministic exporters."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from src.evaluation.models import EvaluationResult, EvaluationSummary

DATASET_SCHEMA_VERSION = "1.0.0"
EXPORT_VERSION = "1.0.0"


@dataclass(frozen=True)
class EvaluationRecord:
    dataset_schema_version: str
    case_id: str
    match_id: str
    competition: str
    kickoff: str
    home_team: str
    away_team: str
    actual_home_goals: int
    actual_away_goals: int
    actual_outcome: str
    home_probability: float
    draw_probability: float
    away_probability: float
    leading_outcome: str
    leading_probability: float
    brier_score: float
    log_loss: float
    top1_correct: bool
    scoreline_top3_hit: bool | None
    decision_action: str
    selected_market: str | None
    candidate_correct: bool | None
    overall_confidence: float
    evidence_gate: str
    prism_version: str
    runtime_version: str
    git_commit: str | None
    data_version: str | None
    rule_version: str | None
    model_version: str | None
    prompt_version: str | None
    session_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DatasetManifest:
    dataset_schema_version: str
    export_version: str
    generated_at: str
    record_count: int
    content_sha256: str
    format: Literal["jsonl", "csv"]
    prism_versions: tuple[str, ...]
    git_commits: tuple[str, ...]


@dataclass(frozen=True)
class DatasetExport:
    payload: str
    manifest: DatasetManifest


def _record_from_result(result: EvaluationResult) -> EvaluationRecord:
    report = result.report
    return EvaluationRecord(
        dataset_schema_version=DATASET_SCHEMA_VERSION,
        case_id=result.case_id,
        match_id=result.match_id,
        competition=report.match.competition,
        kickoff=report.match.kickoff.isoformat(),
        home_team=report.match.home_team,
        away_team=report.match.away_team,
        actual_home_goals=result.actual_home_goals,
        actual_away_goals=result.actual_away_goals,
        actual_outcome=result.actual_outcome,
        home_probability=result.home_probability,
        draw_probability=result.draw_probability,
        away_probability=result.away_probability,
        leading_outcome=result.leading_outcome,
        leading_probability=result.leading_probability,
        brier_score=result.brier_score,
        log_loss=result.log_loss,
        top1_correct=result.top1_correct,
        scoreline_top3_hit=result.scoreline_top3_hit,
        decision_action=result.decision_action,
        selected_market=result.selected_market,
        candidate_correct=result.candidate_correct,
        overall_confidence=result.overall_confidence,
        evidence_gate=result.evidence_gate,
        prism_version=report.provenance.prism_version,
        runtime_version=report.provenance.runtime_version,
        git_commit=report.provenance.git_commit,
        data_version=report.provenance.data_version,
        rule_version=report.provenance.rule_version,
        model_version=report.provenance.model_version,
        prompt_version=report.provenance.prompt_version,
        session_id=report.provenance.session_id,
    )


def records_from_summary(summary: EvaluationSummary) -> tuple[EvaluationRecord, ...]:
    return tuple(_record_from_result(result) for result in summary.results)


def _manifest(
    payload: str,
    records: tuple[EvaluationRecord, ...],
    *,
    format_name: Literal["jsonl", "csv"],
    generated_at: datetime | None,
) -> DatasetManifest:
    moment = generated_at or datetime.now(timezone.utc)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    prism_versions = tuple(sorted({record.prism_version for record in records}))
    git_commits = tuple(sorted({record.git_commit for record in records if record.git_commit}))
    return DatasetManifest(
        dataset_schema_version=DATASET_SCHEMA_VERSION,
        export_version=EXPORT_VERSION,
        generated_at=moment.isoformat(),
        record_count=len(records),
        content_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        format=format_name,
        prism_versions=prism_versions,
        git_commits=git_commits,
    )


def export_evaluation_jsonl(
    summary: EvaluationSummary,
    *,
    generated_at: datetime | None = None,
) -> DatasetExport:
    records = records_from_summary(summary)
    payload = "".join(
        json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
        for record in records
    )
    return DatasetExport(
        payload=payload,
        manifest=_manifest(payload, records, format_name="jsonl", generated_at=generated_at),
    )


_CSV_FIELDS = tuple(EvaluationRecord.__dataclass_fields__)


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def export_evaluation_csv(
    summary: EvaluationSummary,
    *,
    generated_at: datetime | None = None,
) -> DatasetExport:
    records = records_from_summary(summary)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=_CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for record in records:
        writer.writerow({key: _csv_value(value) for key, value in record.to_dict().items()})
    payload = buffer.getvalue()
    return DatasetExport(
        payload=payload,
        manifest=_manifest(payload, records, format_name="csv", generated_at=generated_at),
    )

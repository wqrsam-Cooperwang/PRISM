"""Prediction archive: durable, append-only projection of production predictions.

Design notes:
- Generic archive record independent of any particular snapshot structure. Use
  from_dict/from_mapping builders to adapt inputs from various engines.
- Enforce UTC timezone for all timestamps; reject naive datetimes.
- Include schema_version for future migrations.
- Persist only references for large objects (feature_snapshot_ref).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

ARCHIVE_SCHEMA_VERSION = "1.0.0"


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware (UTC required)")
    return dt.astimezone(timezone.utc)


def _isoformat_utc(dt: datetime) -> str:
    # produce a compact ISO 8601 with Z for UTC
    return _ensure_utc(dt).isoformat().replace("+00:00", "Z")


def _parse_iso_to_utc(value: str) -> datetime:
    # Accept ISO strings with Z or offset; normalize to UTC
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return _ensure_utc(datetime.fromisoformat(value))


@dataclass(frozen=True)
class PredictionArchiveRecord:
    schema_version: str
    prediction_id: str
    match_id: str
    competition: str
    season: str
    kickoff_time: datetime
    prediction_timestamp: datetime
    home_team: str
    away_team: str
    model_version: str
    expected_home_goals: float
    expected_away_goals: float
    home_probability: float
    draw_probability: float
    away_probability: float
    exact_score_probabilities: dict[str, float]
    confidence: float
    feature_snapshot_ref: str

    def __post_init__(self) -> None:
        if self.schema_version != ARCHIVE_SCHEMA_VERSION:
            raise ValueError(f"unsupported schema_version: {self.schema_version}")
        if not self.prediction_id.strip():
            raise ValueError("prediction_id must not be blank")
        if not self.match_id.strip():
            raise ValueError("match_id must not be blank")
        if not self.competition.strip():
            raise ValueError("competition must not be blank")
        if not self.home_team.strip() or not self.away_team.strip():
            raise ValueError("team names must not be blank")
        # Ensure timezone-aware and normalized to UTC
        _ensure_utc(self.kickoff_time)
        _ensure_utc(self.prediction_timestamp)
        # Numeric validations
        for value in (
            self.expected_home_goals,
            self.expected_away_goals,
            self.home_probability,
            self.draw_probability,
            self.away_probability,
            self.confidence,
        ):
            if not isinstance(value, (int, float)):
                raise ValueError("numeric fields must be int/float")
        for prob in (self.home_probability, self.draw_probability, self.away_probability, self.confidence):
            if not (0.0 <= prob <= 1.0):
                raise ValueError("probabilities and confidence must be within [0, 1]")
        if not isinstance(self.exact_score_probabilities, dict):
            raise ValueError("exact_score_probabilities must be a mapping of score->probability")
        for k, v in self.exact_score_probabilities.items():
            if not isinstance(k, str) or not isinstance(v, (int, float)):
                raise ValueError("exact_score_probabilities must map string->number")
            if v < 0 or v > 1:
                raise ValueError("exact score probabilities must be within [0,1]")
        if not isinstance(self.feature_snapshot_ref, str) or not self.feature_snapshot_ref.strip():
            raise ValueError("feature_snapshot_ref must be a non-empty string")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prediction_id": self.prediction_id,
            "match_id": self.match_id,
            "competition": self.competition,
            "season": self.season,
            "kickoff_time": _isoformat_utc(self.kickoff_time),
            "prediction_timestamp": _isoformat_utc(self.prediction_timestamp),
            "home_team": self.home_team,
            "away_team": self.away_team,
            "model_version": self.model_version,
            "expected_home_goals": float(self.expected_home_goals),
            "expected_away_goals": float(self.expected_away_goals),
            "home_probability": float(self.home_probability),
            "draw_probability": float(self.draw_probability),
            "away_probability": float(self.away_probability),
            "exact_score_probabilities": dict(self.exact_score_probabilities),
            "confidence": float(self.confidence),
            "feature_snapshot_ref": self.feature_snapshot_ref,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PredictionArchiveRecord":
        schema = data.get("schema_version")
        if schema != ARCHIVE_SCHEMA_VERSION:
            raise ValueError(f"unsupported schema_version: {schema}")
        kickoff_raw = data.get("kickoff_time")
        pred_ts_raw = data.get("prediction_timestamp")
        kickoff = _parse_iso_to_utc(kickoff_raw) if isinstance(kickoff_raw, str) else _ensure_utc(kickoff_raw)
        pred_ts = _parse_iso_to_utc(pred_ts_raw) if isinstance(pred_ts_raw, str) else _ensure_utc(pred_ts_raw)
        return cls(
            schema_version=schema,
            prediction_id=str(data.get("prediction_id", "")),
            match_id=str(data.get("match_id", "")),
            competition=str(data.get("competition", "")),
            season=str(data.get("season", "")),
            kickoff_time=kickoff,
            prediction_timestamp=pred_ts,
            home_team=str(data.get("home_team", "")),
            away_team=str(data.get("away_team", "")),
            model_version=str(data.get("model_version", "")),
            expected_home_goals=float(data.get("expected_home_goals", 0.0)),
            expected_away_goals=float(data.get("expected_away_goals", 0.0)),
            home_probability=float(data.get("home_probability", 0.0)),
            draw_probability=float(data.get("draw_probability", 0.0)),
            away_probability=float(data.get("away_probability", 0.0)),
            exact_score_probabilities=dict(data.get("exact_score_probabilities", {})),
            confidence=float(data.get("confidence", 0.0)),
            feature_snapshot_ref=str(data.get("feature_snapshot_ref", "")),
        )


class FileSystemPredictionArchiveStore:
    """Persist one immutable prediction archive record under a deterministic root.

    Uses atomic write semantics and prevents duplicate entries.
    """

    def __init__(self, root: Path | str = "data/prediction-archive") -> None:
        self.root = Path(root)

    def persist(self, record: PredictionArchiveRecord) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        destination = self.root / f"{record.prediction_id}.json"
        if destination.exists():
            raise FileExistsError(f"Prediction archive entry already exists: {record.prediction_id}")
        encoded = json.dumps(record.to_dict(), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(encoded + "\n", encoding="utf-8")
        temporary.replace(destination)
        return destination


def build_archive_from_mapping(mapping: Mapping[str, Any]) -> PredictionArchiveRecord:
    """Build a PredictionArchiveRecord from a flexible mapping.

    This helper is intentionally generic: it accepts a mapping produced by any
    prediction engine or snapshot builder, attempting to extract well-known
    fields. It does not require a PredictionLedgerSnapshot instance.
    """
    # Direct expected fields if available
    schema = mapping.get("schema_version", ARCHIVE_SCHEMA_VERSION)
    prediction_id = mapping.get("prediction_id") or mapping.get("prediction_id") or ""
    match_id = mapping.get("match_id") or mapping.get("match", {}).get("match_id", "")
    competition = mapping.get("competition") or mapping.get("match", {}).get("competition", "")
    season = mapping.get("season") or mapping.get("match", {}).get("season", "")
    kickoff_raw = mapping.get("kickoff_time") or mapping.get("match", {}).get("kickoff")
    prediction_ts_raw = mapping.get("prediction_timestamp") or mapping.get("frozen_at")
    home_team = mapping.get("home_team") or mapping.get("match", {}).get("home_team", "")
    away_team = mapping.get("away_team") or mapping.get("match", {}).get("away_team", "")
    model_version = mapping.get("model_version") or mapping.get("provenance", {}).get("model_version", "")

    # Outputs
    expected_home = mapping.get("expected_home_goals")
    expected_away = mapping.get("expected_away_goals")
    home_prob = mapping.get("home_probability")
    draw_prob = mapping.get("draw_probability")
    away_prob = mapping.get("away_probability")
    exact_scores = mapping.get("exact_score_probabilities") or mapping.get("shadow_predictions", {}).get("exact_score_probabilities") or {}
    confidence = mapping.get("confidence") or (mapping.get("report", {}).get("confidence", {}).get("overall") if mapping.get("report") else None)
    feature_ref = mapping.get("feature_snapshot_ref") or mapping.get("features", {}).get("fingerprint") or mapping.get("features", {}).get("intelligence_fingerprint") or ""

    # Normalize timestamps
    kickoff = _parse_iso_to_utc(kickoff_raw) if isinstance(kickoff_raw, str) else _ensure_utc(kickoff_raw) if kickoff_raw is not None else _ensure_utc(datetime.now(timezone.utc))
    pred_ts = _parse_iso_to_utc(prediction_ts_raw) if isinstance(prediction_ts_raw, str) else _ensure_utc(prediction_ts_raw) if prediction_ts_raw is not None else _ensure_utc(datetime.now(timezone.utc))

    # Fallbacks for outputs if missing
    expected_home = float(expected_home) if expected_home is not None else float(mapping.get("scoreline", {}).get("expected_home_goals", 0.0))
    expected_away = float(expected_away) if expected_away is not None else float(mapping.get("scoreline", {}).get("expected_away_goals", 0.0))
    home_prob = float(home_prob) if home_prob is not None else float(mapping.get("consensus", {}).get("home_probability", 0.0))
    draw_prob = float(draw_prob) if draw_prob is not None else float(mapping.get("consensus", {}).get("draw_probability", 0.0))
    away_prob = float(away_prob) if away_prob is not None else float(mapping.get("consensus", {}).get("away_probability", 0.0))
    confidence = float(confidence) if confidence is not None else 0.0

    return PredictionArchiveRecord(
        schema_version=schema,
        prediction_id=str(prediction_id),
        match_id=str(match_id),
        competition=str(competition),
        season=str(season),
        kickoff_time=kickoff,
        prediction_timestamp=pred_ts,
        home_team=str(home_team),
        away_team=str(away_team),
        model_version=str(model_version),
        expected_home_goals=float(expected_home),
        expected_away_goals=float(expected_away),
        home_probability=float(home_prob),
        draw_probability=float(draw_prob),
        away_probability=float(away_prob),
        exact_score_probabilities=dict(exact_scores),
        confidence=float(confidence),
        feature_snapshot_ref=str(feature_ref),
    )

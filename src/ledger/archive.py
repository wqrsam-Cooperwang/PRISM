"""Prediction archive: durable, append-only projection of production predictions.

This module follows existing ledger patterns (models + filesystem stores) and
provides a small builder to create archive records from a previously-built
PredictionLedgerSnapshot. The archive record intentionally duplicates only the
fields required for downstream reporting/analytics and keeps the full immutable
snapshot in the performance-ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class PredictionArchiveRecord:
    prediction_id: str
    match_id: str
    competition: str
    kickoff: datetime
    home_team: str
    away_team: str
    model_version: str
    prediction_timestamp: datetime
    expected_home_goals: float
    expected_away_goals: float
    home_probability: float
    draw_probability: float
    away_probability: float
    exact_score_probabilities: dict[str, float]
    confidence: float
    feature_snapshot_ref: str

    def __post_init__(self) -> None:
        # Basic validations mirroring ledger/outcomes style
        if not self.prediction_id.strip():
            raise ValueError("prediction_id must not be blank")
        if not self.match_id.strip():
            raise ValueError("match_id must not be blank")
        if not self.competition.strip():
            raise ValueError("competition must not be blank")
        if not self.home_team.strip() or not self.away_team.strip():
            raise ValueError("team names must not be blank")
        if self.kickoff.tzinfo is None or self.kickoff.utcoffset() is None:
            raise ValueError("kickoff must be timezone-aware")
        if self.prediction_timestamp.tzinfo is None or self.prediction_timestamp.utcoffset() is None:
            raise ValueError("prediction_timestamp must be timezone-aware")
        for value in (self.expected_home_goals, self.expected_away_goals, self.home_probability, self.draw_probability, self.away_probability, self.confidence):
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
            "prediction_id": self.prediction_id,
            "match_id": self.match_id,
            "competition": self.competition,
            "kickoff": self.kickoff.isoformat(),
            "home_team": self.home_team,
            "away_team": self.away_team,
            "model_version": self.model_version,
            "prediction_timestamp": self.prediction_timestamp.isoformat(),
            "expected_home_goals": self.expected_home_goals,
            "expected_away_goals": self.expected_away_goals,
            "home_probability": self.home_probability,
            "draw_probability": self.draw_probability,
            "away_probability": self.away_probability,
            "exact_score_probabilities": dict(self.exact_score_probabilities),
            "confidence": self.confidence,
            "feature_snapshot_ref": self.feature_snapshot_ref,
        }


class FileSystemPredictionArchiveStore:
    """Persist one immutable prediction archive record under a deterministic root.

    Behavior mirrors other filesystem ledger stores in the repository: create
    directory if needed, write to a temporary file, then atomically replace to
    the final JSON file. Existing records are protected (FileExistsError).
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


# Helper to project the existing PredictionLedgerSnapshot payload into the archive record
def build_archive_from_snapshot(snapshot: Any) -> PredictionArchiveRecord:
    """Create a PredictionArchiveRecord from a PredictionLedgerSnapshot-like object.

    The function expects the snapshot.payload to contain a report (report.to_dict())
    and features/model_outputs or report.scoreline. It prefers the report's
    consensus and scoreline where available, and falls back to the first
    model_output entry for expected goals/probabilities.
    """
    payload = snapshot.payload
    report = payload.get("report", {})
    match = report.get("match", {})
    provenance = report.get("provenance", {})
    consensus = report.get("consensus") or {}
    scoreline = report.get("scoreline") or {}

    # Primary extraction points
    home_prob = consensus.get("home_probability")
    draw_prob = consensus.get("draw_probability")
    away_prob = consensus.get("away_probability")

    expected_home = scoreline.get("expected_home_goals")
    expected_away = scoreline.get("expected_away_goals")

    # fallbacks to model_outputs if primary absent
    if (home_prob is None or draw_prob is None or away_prob is None) and payload.get("model_outputs"):
        first = payload.get("model_outputs")[0]
        home_prob = home_prob if home_prob is not None else first.get("home_probability")
        draw_prob = draw_prob if draw_prob is not None else first.get("draw_probability")
        away_prob = away_prob if away_prob is not None else first.get("away_probability")
        expected_home = expected_home if expected_home is not None else first.get("expected_home_goals")
        expected_away = expected_away if expected_away is not None else first.get("expected_away_goals")

    # exact score probabilities may be in shadow_predictions or scoreline recommended list.
    exact_probs = payload.get("shadow_predictions", {}).get("exact_score_probabilities") or {}
    # confidence from report
    confidence = None
    if report.get("confidence"):
        confidence = report["confidence"].get("overall")

    # features fingerprint or reference
    feature_ref = payload.get("features", {}).get("fingerprint") or payload.get("features", {}).get("intelligence_fingerprint") or ""

    return PredictionArchiveRecord(
        prediction_id=snapshot.prediction_id,
        match_id=snapshot.match_id,
        competition=match.get("competition", ""),
        kickoff=datetime.fromisoformat(match.get("kickoff")) if isinstance(match.get("kickoff"), str) else match.get("kickoff"),
        home_team=match.get("home_team", ""),
        away_team=match.get("away_team", ""),
        model_version=provenance.get("model_version", ""),
        prediction_timestamp=datetime.fromisoformat(snapshot.frozen_at.isoformat()),
        expected_home_goals=float(expected_home) if expected_home is not None else 0.0,
        expected_away_goals=float(expected_away) if expected_away is not None else 0.0,
        home_probability=float(home_prob) if home_prob is not None else 0.0,
        draw_probability=float(draw_prob) if draw_prob is not None else 0.0,
        away_probability=float(away_prob) if away_prob is not None else 0.0,
        exact_score_probabilities=dict(exact_probs),
        confidence=float(confidence) if confidence is not None else 0.0,
        feature_snapshot_ref=str(feature_ref),
    )

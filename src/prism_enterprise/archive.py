"""SQLite-backed prediction and result archive for PRISM Enterprise V3.1."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS predictions (
    prediction_id TEXT PRIMARY KEY,
    match_id TEXT NOT NULL,
    competition TEXT NOT NULL,
    kickoff_utc TEXT NOT NULL,
    prediction_time_utc TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    model_version TEXT NOT NULL,
    lambda_home REAL NOT NULL CHECK (lambda_home >= 0),
    lambda_away REAL NOT NULL CHECK (lambda_away >= 0),
    outcome_home REAL NOT NULL,
    outcome_draw REAL NOT NULL,
    outcome_away REAL NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    primary_score_home INTEGER NOT NULL CHECK (primary_score_home >= 0),
    primary_score_away INTEGER NOT NULL CHECK (primary_score_away >= 0),
    alternate_scores_json TEXT NOT NULL,
    rationale_json TEXT NOT NULL,
    created_at_utc TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_predictions_match_id
ON predictions(match_id);

CREATE TABLE IF NOT EXISTS feature_snapshots (
    prediction_id TEXT NOT NULL,
    feature_id TEXT NOT NULL,
    feature_value_json TEXT NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    observed_at_utc TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'confirmed',
    PRIMARY KEY (prediction_id, feature_id),
    FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS match_results (
    match_id TEXT PRIMARY KEY,
    home_goals INTEGER NOT NULL CHECK (home_goals >= 0),
    away_goals INTEGER NOT NULL CHECK (away_goals >= 0),
    half_time_home_goals INTEGER,
    half_time_away_goals INTEGER,
    home_xg REAL,
    away_xg REAL,
    home_red_cards INTEGER NOT NULL DEFAULT 0,
    away_red_cards INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL,
    result_source TEXT NOT NULL,
    observed_at_utc TEXT NOT NULL,
    created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    prediction_id TEXT PRIMARY KEY,
    match_id TEXT NOT NULL,
    outcome_correct INTEGER NOT NULL,
    exact_score_correct INTEGER NOT NULL,
    btts_correct INTEGER NOT NULL,
    total_goals_error REAL NOT NULL,
    home_goal_error REAL NOT NULL,
    away_goal_error REAL NOT NULL,
    brier_score REAL NOT NULL,
    anomaly_flags_json TEXT NOT NULL,
    attribution_json TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id) ON DELETE CASCADE,
    FOREIGN KEY (match_id) REFERENCES match_results(match_id) ON DELETE CASCADE
);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class PredictionRecord:
    prediction_id: str
    match_id: str
    competition: str
    kickoff_utc: str
    prediction_time_utc: str
    home_team: str
    away_team: str
    model_version: str
    lambda_home: float
    lambda_away: float
    outcome_home: float
    outcome_draw: float
    outcome_away: float
    confidence: float
    primary_score_home: int
    primary_score_away: int
    alternate_scores: Sequence[tuple[int, int]] = ()
    rationale: Mapping[str, Any] | None = None

    def validate(self) -> None:
        probability_sum = self.outcome_home + self.outcome_draw + self.outcome_away
        if abs(probability_sum - 1.0) > 1e-6:
            raise ValueError("Outcome probabilities must sum to 1.0")
        if self.lambda_home < 0 or self.lambda_away < 0:
            raise ValueError("Expected goals must be non-negative")
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        if self.primary_score_home < 0 or self.primary_score_away < 0:
            raise ValueError("Predicted scores must be non-negative")


@dataclass(frozen=True)
class MatchResult:
    match_id: str
    home_goals: int
    away_goals: int
    result_source: str
    observed_at_utc: str
    half_time_home_goals: int | None = None
    half_time_away_goals: int | None = None
    home_xg: float | None = None
    away_xg: float | None = None
    home_red_cards: int = 0
    away_red_cards: int = 0
    metadata: Mapping[str, Any] | None = None


class PredictionRepository:
    """Persistence boundary for predictions, features, results and reviews."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def save_prediction(
        self,
        prediction: PredictionRecord,
        feature_snapshot: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> None:
        prediction.validate()
        created_at = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO predictions VALUES (
                    :prediction_id, :match_id, :competition, :kickoff_utc,
                    :prediction_time_utc, :home_team, :away_team, :model_version,
                    :lambda_home, :lambda_away, :outcome_home, :outcome_draw,
                    :outcome_away, :confidence, :primary_score_home,
                    :primary_score_away, :alternate_scores_json,
                    :rationale_json, :created_at_utc
                )
                """,
                {
                    **asdict(prediction),
                    "alternate_scores_json": json.dumps(list(prediction.alternate_scores)),
                    "rationale_json": json.dumps(prediction.rationale or {}, sort_keys=True),
                    "created_at_utc": created_at,
                },
            )
            for feature_id, payload in (feature_snapshot or {}).items():
                connection.execute(
                    """
                    INSERT INTO feature_snapshots (
                        prediction_id, feature_id, feature_value_json, confidence,
                        observed_at_utc, source, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        prediction.prediction_id,
                        feature_id,
                        json.dumps(payload.get("value"), sort_keys=True),
                        float(payload.get("confidence", 1.0)),
                        str(payload.get("observed_at_utc", prediction.prediction_time_utc)),
                        str(payload.get("source", "unknown")),
                        str(payload.get("status", "confirmed")),
                    ),
                )

    def save_result(self, result: MatchResult) -> None:
        if result.home_goals < 0 or result.away_goals < 0:
            raise ValueError("Result scores must be non-negative")
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO match_results VALUES (
                    :match_id, :home_goals, :away_goals,
                    :half_time_home_goals, :half_time_away_goals,
                    :home_xg, :away_xg, :home_red_cards, :away_red_cards,
                    :metadata_json, :result_source, :observed_at_utc, :created_at_utc
                )
                """,
                {
                    **asdict(result),
                    "metadata_json": json.dumps(result.metadata or {}, sort_keys=True),
                    "created_at_utc": utc_now(),
                },
            )

    def get_prediction(self, prediction_id: str) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM predictions WHERE prediction_id = ?", (prediction_id,)
            ).fetchone()

    def get_result(self, match_id: str) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM match_results WHERE match_id = ?", (match_id,)
            ).fetchone()

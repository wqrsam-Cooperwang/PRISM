"""Build pre-match V2.2 shadow outputs without changing production decisions."""

from __future__ import annotations

from typing import Any

from src.consensus import DirectionCalibrator
from src.domain.models import MatchContext
from src.scoreline import V22CandidateScorelineEngine
from src.scoreline.models import ScorelineCandidate, ScorelineOutput

V22_SHADOW_SCHEMA_VERSION = "1.0.0"


def _candidate_dict(candidate: ScorelineCandidate) -> dict[str, Any]:
    return {
        "home_goals": candidate.home_goals,
        "away_goals": candidate.away_goals,
        "probability": candidate.probability,
    }


def _scoreline_dict(output: ScorelineOutput) -> dict[str, Any]:
    return {
        "available": output.available,
        "method": output.method,
        "source_model_ids": list(output.source_model_ids),
        "expected_home_goals": output.expected_home_goals,
        "expected_away_goals": output.expected_away_goals,
        "top_scorelines": [_candidate_dict(item) for item in output.top_scorelines],
        "recommended_scorelines": [
            _candidate_dict(item) for item in output.recommended_scorelines
        ],
        "grid_probability_mass": output.grid_probability_mass,
        "tail_mass": output.tail_mass,
        "rationale": list(output.rationale),
    }


def build_v22_shadow_payload(context: MatchContext) -> dict[str, Any]:
    """Return a frozen V2.2 shadow payload from the same pre-match runtime state.

    Shadow generation never changes the production V2.1 report or decision. Missing
    Consensus/Evidence is recorded as unavailable instead of breaking production.
    """

    consensus = getattr(context, "consensus", None)
    evidence = getattr(context, "evidence", None)
    if consensus is None or evidence is None:
        return {
            "schema_version": V22_SHADOW_SCHEMA_VERSION,
            "candidate_version": V22CandidateScorelineEngine.version,
            "status": "unavailable",
            "reason": "consensus and evidence are required for full-stack V2.2 shadowing",
        }

    direction = DirectionCalibrator().run(consensus, evidence)
    scoreline = V22CandidateScorelineEngine().run_with_direction(context, direction)
    return {
        "schema_version": V22_SHADOW_SCHEMA_VERSION,
        "candidate_version": V22CandidateScorelineEngine.version,
        "status": "available" if scoreline.available else "scoreline_unavailable",
        "direction_calibration": {
            "home_probability": direction.home_probability,
            "draw_probability": direction.draw_probability,
            "away_probability": direction.away_probability,
            "reliability": direction.reliability,
            "raw_leading_probability": direction.raw_leading_probability,
            "calibrated_leading_probability": direction.calibrated_leading_probability,
            "method": direction.method,
        },
        "scoreline": _scoreline_dict(scoreline),
    }

"""Governed read-only prediction reporting for PRISM."""

from src.report.application import analyze_match_report, analyze_match_report_dict
from src.report.builder import build_prediction_report, build_prediction_report_dict
from src.report.models import (
    AdjustmentReport,
    ConfidenceReport,
    ConsensusReport,
    DecisionReport,
    EngineTraceReport,
    EvidenceReport,
    MatchReport,
    PredictionReport,
    ProvenanceReport,
    ScorelineCandidateReport,
    ScorelineReport,
)
from src.report.renderer import render_prediction_report_markdown

__all__ = [
    "AdjustmentReport",
    "ConfidenceReport",
    "ConsensusReport",
    "DecisionReport",
    "EngineTraceReport",
    "EvidenceReport",
    "MatchReport",
    "PredictionReport",
    "ProvenanceReport",
    "ScorelineCandidateReport",
    "ScorelineReport",
    "analyze_match_report",
    "analyze_match_report_dict",
    "build_prediction_report",
    "build_prediction_report_dict",
    "render_prediction_report_markdown",
]

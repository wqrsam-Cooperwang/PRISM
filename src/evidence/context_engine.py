"""MatchContext adapter for the Evidence Engine."""

from __future__ import annotations

from dataclasses import replace
from typing import Mapping

from src.domain.models import EvidenceOutput, MatchContext
from src.evidence.engine import evaluate_evidence


class EvidenceEngine:
    """Attach evidence quality output to a new MatchContext."""

    name = "evidence"
    version = "1.0.0"

    def __init__(self, completeness: Mapping[str, float]) -> None:
        self._completeness = dict(completeness)

    def run(self, context: MatchContext) -> MatchContext:
        result = evaluate_evidence(self._completeness)
        output = EvidenceOutput(
            score=result.score,
            raw_score=result.raw_score,
            gate=result.gate,
            category_scores=result.category_scores,
            missing_categories=result.missing_categories,
            warnings=result.warnings,
            critical_caps_applied=result.critical_caps_applied,
        )
        return replace(context, evidence=output)

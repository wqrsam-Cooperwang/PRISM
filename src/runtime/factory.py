"""Production assembly helpers for the PRISM runtime."""

from __future__ import annotations

from collections.abc import Mapping

from src.decision.engine import DecisionEngine
from src.evidence.context_engine import EvidenceEngine
from src.runtime.orchestrator import PrismOrchestrator


def build_runtime(
    completeness: Mapping[str, float],
    *,
    decision_engine: DecisionEngine | None = None,
) -> PrismOrchestrator:
    """Build the canonical PRISM runtime from application-level inputs.

    The factory owns concrete engine assembly so callers do not need to know
    the canonical engine graph or instantiate individual runtime components.
    """

    evidence_engine = EvidenceEngine(completeness)
    return PrismOrchestrator.standard(
        evidence_engine,
        decision_engine=decision_engine,
    )

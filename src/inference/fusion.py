from __future__ import annotations

"""EvidenceFusionEngine stub.

This module provides the EvidenceFusionEngine interface and a minimal stub
implementation that is importable. The full implementation will be added in
later phases following the approved Architecture Freeze.
"""

from typing import Iterable

from src.evidence.models import EvidenceResult
from src.inference.models import PosteriorMatchState


class EvidenceFusionEngine:
    """Collect and fuse evidence into a PosteriorMatchState.

    The full fusion algorithm (dependency-aware, aging, deduplication) will be
    implemented in Phase C. This stub exists so the rest of the codebase can
    import and run lightweight unit tests.
    """

    def __init__(self) -> None:
        # configuration, priors, and dependency matrix will be injected here
        self._configured = False

    def configure(self, *args: object, **kwargs: object) -> None:
        """Configure engine (priors, dependency matrix, governance hooks)."""
        self._configured = True

    def fuse(self, evidence: Iterable[EvidenceResult], prior: object | None = None) -> PosteriorMatchState:
        """Fuse evidence and return PosteriorMatchState.

        This stub raises NotImplementedError until Phase C implementation.
        """
        raise NotImplementedError("EvidenceFusionEngine.fuse is not implemented yet")

    def explain(self, posterior: PosteriorMatchState) -> Mapping[str, object]:
        """Return an explainability summary for the posterior."""
        raise NotImplementedError("EvidenceFusionEngine.explain is not implemented yet")

from __future__ import annotations

"""Explainability engine stub for PRISM Enterprise.

Provides the ExplainabilityEngine interface. Implementation is deferred to
Phase F after evidence fusion and posterior generation are in place.
"""

from typing import Mapping

from src.inference.models import PosteriorMatchState


class ExplainabilityEngine:
    def __init__(self) -> None:
        pass

    def decompose(self, posterior: PosteriorMatchState) -> Mapping[str, object]:
        raise NotImplementedError("ExplainabilityEngine.decompose is not implemented yet")

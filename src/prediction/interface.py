"""Prediction model protocol for deterministic PRISM model execution."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain.models import ModelOutput
from src.features.models import FeatureVector


@runtime_checkable
class PredictionModel(Protocol):
    """Contract implemented by every independent PRISM prediction model."""

    model_id: str
    version: str
    required_features: tuple[str, ...]

    def predict(self, features: FeatureVector) -> ModelOutput:
        """Return one governed model output for the supplied feature vector."""
        ...

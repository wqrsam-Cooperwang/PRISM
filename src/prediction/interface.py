"""Prediction model protocol for deterministic PRISM model execution."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain.models import ModelOutput
from src.features.models import FeatureVector


@runtime_checkable
class PredictionModel(Protocol):
    """Contract implemented by every independent PRISM prediction model."""

    @property
    def model_id(self) -> str:
        """Stable identifier for the independent prediction model."""
        ...

    @property
    def version(self) -> str:
        """Version of the prediction model implementation and parameters."""
        ...

    @property
    def required_features(self) -> tuple[str, ...]:
        """Feature names that must be present before model execution."""
        ...

    def predict(self, features: FeatureVector) -> ModelOutput:
        """Return one governed model output for the supplied feature vector."""
        ...

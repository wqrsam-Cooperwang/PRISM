"""Governed execution helpers for independent PRISM prediction models."""

from __future__ import annotations

from collections.abc import Iterable

from src.domain.models import ModelOutput
from src.features.models import FeatureVector
from src.prediction.interface import PredictionModel

_RESERVED_DIAGNOSTIC_KEYS = {
    "feature_fingerprint",
    "feature_schema_version",
    "intelligence_fingerprint",
    "intelligence_readiness",
}


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _validated_required_features(model: PredictionModel) -> tuple[str, ...]:
    required = tuple(_require_text(item, "required_feature") for item in model.required_features)
    if len(set(required)) != len(required):
        raise ValueError(f"Model {model.model_id} required_features must be unique")
    return required


def _validate_model(model: PredictionModel) -> tuple[str, str, tuple[str, ...]]:
    model_id = _require_text(model.model_id, "model_id")
    version = _require_text(model.version, "model_version")
    required = _validated_required_features(model)
    return model_id, version, required


def _validate_feature_availability(
    model_id: str,
    required_features: tuple[str, ...],
    features: FeatureVector,
) -> None:
    missing = tuple(
        name
        for name in required_features
        if name in features.missing_features or name not in features.values
    )
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Model {model_id} is missing required features: {joined}")


def _attach_provenance(output: ModelOutput, features: FeatureVector) -> ModelOutput:
    conflicts = sorted(_RESERVED_DIAGNOSTIC_KEYS.intersection(output.diagnostics))
    if conflicts:
        joined = ", ".join(conflicts)
        raise ValueError(f"Model diagnostics use reserved provenance keys: {joined}")

    diagnostics = dict(output.diagnostics)
    diagnostics.update(
        {
            "feature_fingerprint": features.fingerprint,
            "feature_schema_version": features.schema_version,
            "intelligence_fingerprint": features.intelligence_fingerprint,
            "intelligence_readiness": features.readiness.value,
        }
    )
    return ModelOutput(
        model_id=output.model_id,
        model_version=output.model_version,
        home_probability=output.home_probability,
        draw_probability=output.draw_probability,
        away_probability=output.away_probability,
        expected_home_goals=output.expected_home_goals,
        expected_away_goals=output.expected_away_goals,
        diagnostics=diagnostics,
    )


def run_prediction_model(
    model: PredictionModel,
    features: FeatureVector,
) -> ModelOutput:
    """Validate, execute, and provenance-stamp one prediction model."""

    model_id, version, required = _validate_model(model)
    _validate_feature_availability(model_id, required, features)
    output = model.predict(features)
    if output.model_id != model_id:
        raise ValueError("ModelOutput model_id must match the prediction model declaration")
    if output.model_version != version:
        raise ValueError("ModelOutput model_version must match the prediction model declaration")
    return _attach_provenance(output, features)


def run_model_suite(
    models: Iterable[PredictionModel],
    features: FeatureVector,
) -> tuple[ModelOutput, ...]:
    """Execute a deterministic suite of independent prediction models."""

    configured = tuple(models)
    identities = tuple(_validate_model(model)[0] for model in configured)
    if len(set(identities)) != len(identities):
        raise ValueError("Prediction model identifiers must be unique")

    ordered = sorted(configured, key=lambda model: model.model_id)
    return tuple(run_prediction_model(model, features) for model in ordered)

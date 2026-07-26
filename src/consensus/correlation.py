"""Correlated-evidence governance for PRISM model aggregation."""

from __future__ import annotations

from collections import Counter

from src.domain.models import ModelOutput


def evidence_family(model: ModelOutput) -> str:
    """Return a deterministic evidence family for one model output."""

    declared = model.diagnostics.get("evidence_family")
    if isinstance(declared, str) and declared.strip():
        return declared.strip().casefold()

    model_id = model.model_id.casefold()
    if "market" in model_id or "odds" in model_id:
        return "market"
    if "elo" in model_id:
        return "team_strength"
    if "team_statistics" in model_id or "team-stats" in model_id:
        return "team_strength"
    return f"model:{model.model_id}"


def assumption_family(model: ModelOutput) -> str:
    """Return the latent-assumption family used for xG combination."""

    declared = model.diagnostics.get("assumption_family")
    if isinstance(declared, str) and declared.strip():
        return declared.strip().casefold()
    return evidence_family(model)


def family_capped_weights(
    models: tuple[ModelOutput, ...],
    *,
    use_assumption_family: bool = False,
) -> tuple[float, ...]:
    """Assign equal family mass, divided among models inside each family."""

    if not models:
        raise ValueError("family_capped_weights requires at least one model")

    family_for = assumption_family if use_assumption_family else evidence_family
    families = tuple(family_for(model) for model in models)
    counts = Counter(families)
    raw = tuple(1.0 / counts[family] for family in families)
    total = sum(raw)
    return tuple(weight / total for weight in raw)


def weighted_probability_mean(
    models: tuple[ModelOutput, ...],
    weights: tuple[float, ...],
) -> tuple[float, float, float]:
    """Return a normalized weighted 1X2 probability mean."""

    if len(models) != len(weights):
        raise ValueError("models and weights must have equal length")
    if not models:
        raise ValueError("weighted_probability_mean requires at least one model")

    home = sum(model.home_probability * weight for model, weight in zip(models, weights))
    draw = sum(model.draw_probability * weight for model, weight in zip(models, weights))
    away = sum(model.away_probability * weight for model, weight in zip(models, weights))
    total = home + draw + away
    if total <= 0.0:
        raise ValueError("weighted probability total must be positive")
    return home / total, draw / total, away / total

import pytest

from src.consensus.correlation import (
    assumption_family,
    evidence_family,
    family_capped_weights,
    weighted_probability_mean,
)
from src.domain.models import ModelOutput


def _model(model_id: str, diagnostics=None) -> ModelOutput:
    return ModelOutput(
        model_id=model_id,
        model_version="1.0.0",
        home_probability=0.5,
        draw_probability=0.3,
        away_probability=0.2,
        diagnostics={} if diagnostics is None else diagnostics,
    )


def test_evidence_family_prefers_explicit_declaration() -> None:
    assert evidence_family(_model("anything", {"evidence_family": " Market "})) == "market"


def test_evidence_family_has_deterministic_model_id_fallbacks() -> None:
    assert evidence_family(_model("closing-odds-model")) == "market"
    assert evidence_family(_model("elo-baseline")) == "team_strength"
    assert evidence_family(_model("team_statistics_baseline")) == "team_strength"
    assert evidence_family(_model("independent-model")) == "model:independent-model"


def test_assumption_family_prefers_explicit_then_evidence_family() -> None:
    explicit = _model("market-model", {"assumption_family": " Shared-XG "})
    fallback = _model("market-model")

    assert assumption_family(explicit) == "shared-xg"
    assert assumption_family(fallback) == "market"


def test_family_capped_weights_rejects_empty_inputs() -> None:
    with pytest.raises(ValueError, match="at least one model"):
        family_capped_weights(())


def test_weighted_probability_mean_validates_shape_and_inputs() -> None:
    model = _model("one")

    with pytest.raises(ValueError, match="equal length"):
        weighted_probability_mean((model,), ())
    with pytest.raises(ValueError, match="at least one model"):
        weighted_probability_mean((), ())
    with pytest.raises(ValueError, match="must be positive"):
        weighted_probability_mean((model,), (0.0,))


def test_weighted_probability_mean_normalizes_weighted_distribution() -> None:
    first = ModelOutput("a", "1", 0.6, 0.3, 0.1)
    second = ModelOutput("b", "1", 0.2, 0.3, 0.5)

    home, draw, away = weighted_probability_mean((first, second), (0.75, 0.25))

    assert home == pytest.approx(0.5)
    assert draw == pytest.approx(0.3)
    assert away == pytest.approx(0.2)

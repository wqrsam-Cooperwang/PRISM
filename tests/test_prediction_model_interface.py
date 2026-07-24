from dataclasses import dataclass

import pytest

from src.domain.models import ModelOutput
from src.features.models import FeatureVector
from src.intelligence.models import ReadinessLevel
from src.prediction import run_model_suite, run_prediction_model


def _features(
    *,
    values: dict[str, float] | None = None,
    missing: tuple[str, ...] = (),
) -> FeatureVector:
    return FeatureVector(
        values=values or {"elo_difference": 75.0, "rest_days_difference": 2.0},
        missing_features=missing,
        intelligence_fingerprint="intel-fingerprint",
        readiness=ReadinessLevel.STANDARD,
        fingerprint="feature-fingerprint",
    )


@dataclass
class DummyModel:
    model_id: str = "dummy"
    version: str = "1.0.0"
    required_features: tuple[str, ...] = ("elo_difference",)
    called: bool = False

    def predict(self, features: FeatureVector) -> ModelOutput:
        self.called = True
        return ModelOutput(
            model_id=self.model_id,
            model_version=self.version,
            home_probability=0.55,
            draw_probability=0.25,
            away_probability=0.20,
            expected_home_goals=1.6,
            expected_away_goals=1.0,
            diagnostics={"raw_signal": features.values["elo_difference"]},
        )


def test_runner_preserves_output_and_adds_feature_provenance() -> None:
    features = _features()
    model = DummyModel()

    output = run_prediction_model(model, features)

    assert output.home_probability == pytest.approx(0.55)
    assert output.draw_probability == pytest.approx(0.25)
    assert output.away_probability == pytest.approx(0.20)
    assert output.expected_home_goals == pytest.approx(1.6)
    assert output.expected_away_goals == pytest.approx(1.0)
    assert output.diagnostics["raw_signal"] == 75.0
    assert output.diagnostics["feature_fingerprint"] == features.fingerprint
    assert output.diagnostics["feature_schema_version"] == features.schema_version
    assert output.diagnostics["intelligence_fingerprint"] == "intel-fingerprint"
    assert output.diagnostics["intelligence_readiness"] == "standard"


def test_missing_required_feature_fails_before_model_execution() -> None:
    features = _features(values={"rest_days_difference": 2.0}, missing=("elo_difference",))
    model = DummyModel()

    with pytest.raises(ValueError, match="missing required features: elo_difference"):
        run_prediction_model(model, features)

    assert model.called is False


def test_absent_required_feature_also_fails_closed() -> None:
    features = _features(values={"rest_days_difference": 2.0})

    with pytest.raises(ValueError, match="missing required features: elo_difference"):
        run_prediction_model(DummyModel(), features)


def test_model_output_identity_must_match_declaration() -> None:
    class WrongIdentityModel(DummyModel):
        def predict(self, features: FeatureVector) -> ModelOutput:
            return ModelOutput(
                model_id="wrong",
                model_version=self.version,
                home_probability=0.4,
                draw_probability=0.3,
                away_probability=0.3,
            )

    with pytest.raises(ValueError, match="model_id must match"):
        run_prediction_model(WrongIdentityModel(), _features())


def test_model_output_version_must_match_declaration() -> None:
    class WrongVersionModel(DummyModel):
        def predict(self, features: FeatureVector) -> ModelOutput:
            return ModelOutput(
                model_id=self.model_id,
                model_version="other",
                home_probability=0.4,
                draw_probability=0.3,
                away_probability=0.3,
            )

    with pytest.raises(ValueError, match="model_version must match"):
        run_prediction_model(WrongVersionModel(), _features())


def test_reserved_provenance_diagnostic_keys_fail_closed() -> None:
    class ReservedDiagnosticModel(DummyModel):
        def predict(self, features: FeatureVector) -> ModelOutput:
            return ModelOutput(
                model_id=self.model_id,
                model_version=self.version,
                home_probability=0.4,
                draw_probability=0.3,
                away_probability=0.3,
                diagnostics={"feature_fingerprint": "spoofed"},
            )

    with pytest.raises(ValueError, match="reserved provenance keys"):
        run_prediction_model(ReservedDiagnosticModel(), _features())


def test_model_suite_is_sorted_by_model_id_independent_of_registration_order() -> None:
    model_b = DummyModel(model_id="model-b")
    model_a = DummyModel(model_id="model-a")

    outputs = run_model_suite((model_b, model_a), _features())

    assert tuple(output.model_id for output in outputs) == ("model-a", "model-b")


def test_model_suite_rejects_duplicate_model_ids() -> None:
    first = DummyModel(model_id="duplicate", version="1.0.0")
    second = DummyModel(model_id="duplicate", version="2.0.0")

    with pytest.raises(ValueError, match="identifiers must be unique"):
        run_model_suite((first, second), _features())


def test_required_feature_names_must_be_unique() -> None:
    model = DummyModel(required_features=("elo_difference", "elo_difference"))

    with pytest.raises(ValueError, match="required_features must be unique"):
        run_prediction_model(model, _features())

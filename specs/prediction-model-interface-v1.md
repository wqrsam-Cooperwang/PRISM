# PRISM Prediction Model Interface V1

## Purpose

Define one deterministic contract between PRISM feature construction and all independent prediction models.

The interface must not change the existing `ModelOutput`, Consensus Engine, Orchestrator, or governance layers.

## Pipeline position

`FeatureVector -> PredictionModel -> ModelOutput -> Consensus Engine`

## Model contract

Every prediction model must expose:

- `model_id`: stable non-empty identifier;
- `version`: stable non-empty model version;
- `required_features`: tuple of feature names required for prediction;
- `predict(features)`: deterministic conversion of one `FeatureVector` into one existing `ModelOutput`.

A model may use only a subset of the feature vector.

## Runner contract

The V1 runner is responsible for governance around model execution.

Before prediction it must:

1. validate non-empty and unique model identifiers;
2. validate non-empty model versions;
3. validate required feature names;
4. fail closed when a required feature is explicitly missing or absent from the feature vector.

After prediction it must:

1. require the returned `ModelOutput.model_id` to equal the model declaration;
2. require the returned `ModelOutput.model_version` to equal the model declaration;
3. preserve the model probabilities and expected-goal outputs unchanged;
4. enrich diagnostics with immutable provenance metadata for the consumed feature vector.

Required provenance diagnostics:

- `feature_fingerprint`;
- `feature_schema_version`;
- `intelligence_fingerprint`;
- `intelligence_readiness`.

If a model already returns a diagnostic key reserved for provenance, execution must fail closed rather than silently overwrite it.

## Multi-model execution

A model suite accepts multiple independent models and returns a tuple of `ModelOutput` objects sorted by `model_id`.

This deterministic ordering prevents caller registration order from changing downstream serialization or fingerprints.

Duplicate model identifiers are invalid.

## Missing data

Missing features are never replaced by zero or inferred defaults by the interface layer.

A model that can operate without a feature must not declare it as required.

A model that requires an unavailable feature must fail closed before its prediction method is called.

## Boundaries

V1 defines execution and provenance only. It does not define:

- model mathematics;
- model weights;
- calibration;
- training procedures;
- feature imputation;
- consensus weighting;
- promotion policy.

Those remain independent layers and can evolve without changing this interface.

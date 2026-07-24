# End-to-End Prediction Path V1

## Purpose

Connect the existing PRISM intelligence, feature, prediction-model and consensus modules into one deterministic pre-match prediction path without changing the existing Consensus Engine contract.

## Pipeline

1. `IntelligenceBundle`
2. pre-model fact normalization
3. `FeatureVector`
4. governed independent model execution
5. `ModelOutput` tuple
6. existing runtime `MatchRequest` / `MatchContext`
7. existing `ConsensusEngine`
8. final `ConsensusOutput`

## Two-phase normalization

The current `normalize_intelligence_bundle(bundle, model_outputs)` API remains supported for runtime callers. End-to-end prediction additionally requires a pre-model normalization phase because model outputs depend on features, while features depend on normalized intelligence.

V1 therefore introduces `normalize_intelligence_facts(bundle) -> NormalizedIntelligenceFacts`.

`NormalizedIntelligenceFacts` contains only pre-model data:

- `evidence_completeness`
- `model_feature_data`
- `intelligence_fingerprint`
- `readiness`

It contains no `MatchRequest` and no model outputs.

`normalize_intelligence_bundle` composes the same pre-model facts with the supplied model outputs to build the existing runtime request. This preserves backwards compatibility and avoids duplicate normalization logic.

## V1 baseline model suite

The initial end-to-end path uses:

- `EloProbabilityModel`
- `MarketProbabilityModel`

Both must execute through `run_model_suite` so required-feature validation and provenance stamping remain enforced.

## Consensus

The resulting model outputs are inserted into the existing `MatchRequest`, converted with the existing `build_match_context`, and passed unchanged to the existing `ConsensusEngine`.

No new consensus arithmetic is introduced in V1.

## Acceptance requirements

An end-to-end integration test must prove that:

- one frozen intelligence bundle can produce pre-model normalized facts;
- the facts produce a deterministic feature vector;
- Elo and market models produce governed outputs with feature/intelligence provenance;
- the original runtime request is built from those real model outputs;
- the existing Consensus Engine receives both model outputs;
- final Home/Draw/Away probabilities sum to 1;
- model identifiers remain deterministic;
- repeated execution of the same frozen intelligence produces the same feature fingerprint, model outputs and consensus output;
- no placeholder or synthetic model output is required to construct model features.

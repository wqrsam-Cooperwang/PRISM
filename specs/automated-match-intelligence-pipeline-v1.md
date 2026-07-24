# PRISM Automated Match Intelligence Pipeline V1

Status: Draft implementation contract

## 1. Purpose

The Automated Match Intelligence Pipeline (AMIP) is the governed ingestion layer in front of the existing PRISM runtime. It turns a minimal future-match target plus independently collected observations into a verified, reproducible intelligence bundle that can be normalized into the existing canonical `MatchRequest` / `MatchContext` flow.

AMIP does not replace the Canonical Data Model, Evidence Engine, model engines, Consensus Engine, Decision Engine, report generation, evaluation, benchmark, or promotion governance. It supplies them with traceable pre-match inputs.

## 2. V1 boundaries

V1 defines and implements:

1. a minimal `MatchTarget` identity contract;
2. typed source provenance and observation records;
3. source authority ranking;
4. freshness handling relative to kickoff and collection time;
5. deterministic cross-source verification and conflict detection;
6. required vs optional intelligence categories;
7. category coverage and readiness assessment;
8. a frozen `IntelligenceBundle` suitable for later normalization into `MatchRequest`;
9. explicit degradation when evidence is missing, stale, or conflicting.

V1 does not perform network fetching. Provider/API/web adapters are a later layer and must emit the same observation contract. V1 therefore remains deterministic and testable without external services.

## 3. Pipeline

```text
MatchTarget
  -> observations from adapters
  -> validation
  -> source/freshness weighting
  -> claim grouping
  -> verification/conflict resolution
  -> category coverage
  -> IntelligenceBundle
  -> MatchRequest normalization (next increment)
  -> existing PRISM runtime
```

## 4. MatchTarget

A match target is the minimum identity required before collection starts.

Required:

- `match_id`
- `competition`
- timezone-aware `kickoff`
- `home_team_id`
- `home_team_name`
- `away_team_id`
- `away_team_name`

Optional:

- `season`
- `stage`
- `venue`

No predictive values belong in `MatchTarget`.

## 5. Observation contract

Every externally acquired fact must enter AMIP as an immutable `Observation`.

Required fields:

- `observation_id`: unique within the collection run;
- `category`: governed intelligence category;
- `claim_key`: normalized semantic key used to group competing claims;
- `value`: JSON-compatible observed value;
- `source`: `SourceRef` provenance;
- `observed_at`: when the source says the fact was observed/published, timezone-aware;
- `collected_at`: when PRISM acquired it, timezone-aware.

Optional fields:

- `subject`: team/player/match identifier the claim concerns;
- `confidence`: provider-specific confidence in `[0, 1]` when available;
- `notes`: non-executable diagnostic text.

Unknown information must be absent or `null`; adapters must not invent defaults.

## 6. SourceRef and authority

`SourceRef` contains:

- `source_id`
- `source_type`
- optional `uri`
- optional `publisher`

Governed source types, from strongest to weakest default authority:

1. `official` — club, league, federation, competition organizer;
2. `primary_data` — licensed/first-party structured data provider;
3. `market` — bookmaker/exchange market feed for market claims;
4. `reputable_media` — established news/reporting source;
5. `specialist` — specialist statistics or injury/lineup source;
6. `aggregator` — secondary aggregator;
7. `community` — crowd/social/community claim.

Authority is contextual. For example, `market` is high authority for quoted odds but not for an injury claim. V1 therefore combines a default source-type weight with category-specific caps.

## 7. Governed intelligence categories

### Required for a normal pre-match run

- `identity`
- `team_strength`
- `recent_form`
- `availability`
- `schedule`
- `market`

### Optional but valuable

- `lineup`
- `weather`
- `tactical`
- `head_to_head`
- `motivation_context`

Required means required for a `standard` or `deep` intelligence readiness level. Missing required categories do not cause values to be fabricated; they degrade readiness.

## 8. Verification

Observations sharing `(category, subject, claim_key)` form one claim group.

For each group V1 must:

1. reject structurally invalid observations;
2. calculate deterministic effective weight from source authority, freshness, and optional provider confidence;
3. group semantically equal values;
4. select the value with the strongest aggregate support when dominance is sufficient;
5. preserve all supporting and conflicting observation IDs;
6. mark unresolved conflicts instead of guessing when competing support is too close.

A `VerifiedClaim` contains:

- category / subject / claim key;
- selected value or `None` when unresolved;
- verification status: `verified`, `provisional`, `conflicted`, or `unsupported`;
- confidence in `[0, 1]`;
- supporting observation IDs;
- conflicting observation IDs;
- latest source timestamp.

No LLM judgement is required for V1 conflict resolution. Deterministic rules make ingestion reproducible and benchmarkable.

## 9. Freshness

Freshness is evaluated against collection time and, where relevant, kickoff.

V1 categories use governed maximum ages rather than one global threshold. Illustrative defaults:

- lineup: 12 hours;
- availability: 72 hours;
- market: 6 hours;
- weather: 12 hours;
- recent form / team strength: 14 days;
- schedule: 7 days;
- tactical / motivation context: 7 days.

Stale observations remain auditable but their effective weight is reduced. Extremely stale observations may become ineligible for verification.

Future provider adapters may refresh categories on different cadences without changing the bundle contract.

## 10. Readiness assessment

AMIP produces an `IntelligenceReadiness` independent from the downstream canonical Evidence Engine.

Levels:

- `deep`: all required categories covered by verified claims, strong source quality, low unresolved conflict, and meaningful optional coverage;
- `standard`: all required categories covered, but some claims are provisional or optional coverage is thin;
- `limited`: one or more required categories missing/stale/conflicted, but enough verified material remains to run in a degraded mode;
- `rejected`: match identity is invalid or ingestion quality is too poor to safely construct a prediction input.

The downstream Evidence Engine remains authoritative for its existing evidence gate. AMIP readiness is an ingestion-quality input, not a replacement for that engine.

## 11. IntelligenceBundle

A frozen bundle contains:

- schema version;
- `MatchTarget`;
- collection timestamp;
- all accepted observations;
- all verified claims;
- category assessments;
- readiness level and numeric score;
- missing required categories;
- stale categories;
- conflicted claim keys;
- warnings;
- deterministic bundle fingerprint.

The fingerprint must change when accepted factual inputs or their provenance change and must be stable for equivalent ordered content. It can later populate/derive `data_version` for `AnalysisSession`.

## 12. Integration with existing PRISM runtime

AMIP sits before `src.runtime.request.MatchRequest`.

Existing runtime ownership remains unchanged. The next implementation increment will add a normalizer that maps verified claims into the existing input sections:

- team ratings / strength -> team fields/model inputs;
- lineup -> `lineups`;
- availability -> `injuries`;
- market -> `market`;
- weather -> `weather`;
- schedule -> `schedule`;
- tactical -> `tactical`.

AMIP must not create downstream `decision`, `consensus`, `confidence`, or evaluation outputs.

The current `MatchRequest.model_outputs` field remains untouched in V1. Automated model generation is a subsequent pipeline stage after intelligence normalization.

## 13. Failure rules

- naive timestamps are invalid;
- empty IDs/category/claim keys are invalid;
- confidence outside `[0, 1]` is invalid;
- unsupported/non-JSON-compatible observation values are invalid;
- contradictory strong sources must not be silently collapsed;
- missing categories must not receive synthetic values;
- unresolved conflicts must remain visible in the bundle;
- collection must not mutate caller observations.

## 14. Acceptance criteria

V1 is accepted when:

1. immutable typed models exist for `MatchTarget`, `SourceRef`, `Observation`, `VerifiedClaim`, category assessment, readiness, and `IntelligenceBundle`;
2. observations can be deterministically verified into claims;
3. higher-authority/fresher corroborated evidence defeats weaker conflicting evidence when dominance rules are met;
4. close strong conflicts remain unresolved;
5. stale evidence is retained for audit but penalized;
6. required-category gaps downgrade readiness without invented defaults;
7. invalid identity or unusable evidence can produce `rejected` readiness;
8. equivalent bundle content produces the same fingerprint;
9. tests cover validation, provenance, verification, conflict, staleness, readiness, immutability, and fingerprint stability;
10. ordinary repository CI remains green.

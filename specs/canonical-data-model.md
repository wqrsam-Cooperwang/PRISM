# PRISM Canonical Data Model Specification

Status: Draft for V3.1 Sprint 2

## 1. Purpose

The Canonical Data Model (CDM) defines the single shared language used by every PRISM engine. It prevents engines from exchanging unstructured and incompatible dictionaries and makes each analysis reproducible, serializable, testable, and auditable.

The CDM does not predict outcomes. It carries verified inputs, engine outputs, provenance, and version metadata through the analysis pipeline.

## 2. Design Principles

1. **Single canonical structure** — all engines receive and return `MatchContext`.
2. **Immutability** — domain objects are frozen; an engine returns a new context instead of mutating the existing one.
3. **Engine ownership** — each engine may write only to its assigned output field.
4. **Explicit uncertainty** — unknown values are represented by `None`, never invented defaults.
5. **Reproducibility** — each run contains an `AnalysisSession` with source and version metadata.
6. **Serialization** — every object must convert to JSON-compatible primitives.
7. **Backward compatibility** — breaking schema changes require a new schema version.

## 3. Root Objects

### 3.1 MatchContext

`MatchContext` is the root aggregate passed through the PRISM pipeline.

Required sections:

- `schema_version`
- `session`
- `match`
- `home_team`
- `away_team`

Optional/input sections:

- `lineups`
- `injuries`
- `market`
- `weather`
- `schedule`
- `tactical`

Engine-owned output sections:

- `evidence`
- `rule_outputs`
- `model_outputs`
- `confidence`
- `consensus`
- `decision`

### 3.2 AnalysisSession

An `AnalysisSession` identifies one reproducible analysis run.

Required fields:

- `session_id`: globally unique identifier
- `created_at`: timezone-aware ISO-8601 timestamp
- `prism_version`: PRISM release version
- `schema_version`: CDM schema version

Optional provenance fields:

- `git_commit`
- `data_version`
- `rule_version`
- `model_version`
- `prompt_version`
- `operator`
- `ai_models`

## 4. Core Entities

### MatchInfo

- `match_id`
- `competition`
- `kickoff`
- `venue`
- `season`
- `stage`

`kickoff` must be timezone-aware.

### TeamInfo

- `team_id`
- `name`
- `country`
- `elo_rating`

### LineupData

- expected and confirmed starting players for both teams
- status: `unknown`, `expected`, or `confirmed`
- source references

### InjuryData

Contains unavailable, suspended, and questionable player records. Each player record may include confidence and source metadata.

### MarketData

May contain:

- 1X2 odds
- Asian handicap
- totals
- both-teams-to-score
- opening and current snapshots
- bookmaker/source timestamp

### WeatherData

May contain temperature, humidity, wind, precipitation, pitch condition, source, and observation/forecast time.

### ScheduleData

May contain rest days, previous and next match timestamps, travel distance, timezone shift, and congestion indicators.

### TacticalData

May contain formations, pressing intensity, possession style, transition characteristics, set-piece strength, and analyst/source notes.

## 5. Engine Output Contracts

### EvidenceOutput

Owned by the Evidence Engine.

- `score`: integer 0–100
- `raw_score`: numeric 0–100
- `gate`: `deep`, `standard`, `limited`, or `rejected`
- `category_scores`
- `missing_categories`
- `warnings`
- `critical_caps_applied`

### RuleOutput

Owned by the Rule Engine.

Each rule result contains:

- `rule_id`
- `status`
- `impact`
- `confidence`
- `rationale`
- `evidence_refs`

### ModelOutput

Owned by one model implementation.

- `model_id`
- `model_version`
- home/draw/away probabilities
- optional expected goals
- diagnostics

Probabilities must be finite, between 0 and 1, and sum to 1 within tolerance.

### ConfidenceOutput

Owned by the Confidence Engine.

- evidence confidence
- model confidence
- context confidence
- consensus confidence
- overall confidence
- confidence band
- penalties and rationale

### ConsensusOutput

Owned by the Consensus Engine.

- source probabilities
- consensus probabilities
- agreement score
- conflicts
- outliers

### DecisionOutput

Owned by the Decision Engine.

- action: `no_decision`, `watch`, `no_bet`, or `candidate`
- selected market
- expected value
- risk level
- rationale

A decision must not exist when the evidence gate is `rejected`.

## 6. Engine Interface

Every engine must implement the conceptual interface:

```python
class Engine(Protocol):
    engine_id: str
    engine_version: str

    def run(self, context: MatchContext) -> MatchContext: ...
```

Rules:

1. Input context must remain unchanged.
2. The returned context must preserve all fields not owned by the engine.
3. The engine must not silently remove provenance.
4. Validation errors must be explicit.
5. Re-running a deterministic engine with identical input must produce equivalent output.

## 7. Serialization and Versioning

- JSON field names use `snake_case`.
- Datetimes use ISO-8601 with timezone offsets.
- Tuples serialize as JSON arrays.
- Enums serialize as lowercase strings.
- Unknown values serialize as `null`.
- `schema_version` uses semantic versioning.
- Additive optional fields are backward-compatible.
- Renaming/removing fields or changing meaning is a breaking change.

## 8. Ownership Matrix

| Component | May read | May write |
|---|---|---|
| Evidence Engine | input evidence sections | `evidence` |
| Rule Engine | inputs and evidence | `rule_outputs` |
| Model Engine | inputs and eligible rule outputs | its entry in `model_outputs` |
| Confidence Engine | evidence, models, rules, context | `confidence` |
| Consensus Engine | model and AI outputs | `consensus` |
| Decision Engine | evidence, confidence, consensus, market | `decision` |
| Report Engine | all fields | none |

## 9. Constraints

- Empty identifiers and names are invalid.
- Scores and probabilities cannot be NaN or infinite.
- Confidence values must be in `[0, 1]`.
- Match and session schema versions must agree.
- `created_at` and `kickoff` must include timezone information.
- Mapping fields exposed by immutable objects must not be externally mutable.
- The CDM must not contain executable prompts or hidden model state.

## 10. Acceptance Criteria

The Sprint 2 CDM is accepted when:

1. Immutable Python domain objects exist for `MatchContext` and `AnalysisSession`.
2. A minimal valid context can be created and serialized to JSON.
3. Invalid identifiers, naive datetimes, invalid probabilities, and schema mismatches are rejected.
4. `dataclasses.replace` can produce an updated context without mutating the original.
5. Engine-owned outputs can be attached independently.
6. A JSON Schema documents the minimum external interchange format.
7. Automated tests cover construction, validation, serialization, immutability, and replacement behavior.

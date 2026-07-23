# PRISM Decision Engine V1 Specification

## Purpose

The Decision Engine converts consensus probabilities, market odds, and governed
confidence constraints into a final PRISM action. It is the only engine allowed
to populate `MatchContext.decision`.

V1 is deliberately conservative. It identifies analytical candidates; it does
not claim that any threshold is empirically proven to generate profit.

## Inputs

Required upstream outputs:

- `MatchContext.consensus`
- `MatchContext.adjustment`

Supported market inputs:

- `home_odds`
- `draw_odds`
- `away_odds`

All odds must be finite decimal odds strictly greater than 1.0.

## Actions

### NO_DECISION

Returned when upstream governance explicitly blocks active decisions.

### WATCH

Returned when the analysis is structurally valid but complete supported market
odds are unavailable.

### NO_BET

Returned when market data exists but the candidate does not pass the configured
policy thresholds.

### CANDIDATE

Returned only when all V1 policy conditions are satisfied.

## Expected value

For each supported 1X2 outcome:

`EV = consensus_probability * decimal_odds - 1`

The engine selects the outcome with the highest EV before applying policy gates.

This is arithmetic expected value under the supplied consensus probability. It
must not be described as a validated market edge unless later backtesting and
calibration provide evidence for that claim.

## V1 policy parameters

Defaults are explicit governance policy, not learned constants:

- minimum adjusted confidence: `0.70`
- minimum expected value: `0.03`
- minimum consensus margin: `0.05`

The engine constructor may override these values for research experiments.
Overrides must remain within valid numeric ranges.

## Decision order

1. Require ConsensusOutput and AdjustmentOutput.
2. If `decision_blocked` is true -> `NO_DECISION`.
3. Validate complete supported 1X2 odds.
4. If odds are incomplete -> `WATCH`.
5. Compute EV for home/draw/away.
6. Select the highest-EV outcome deterministically.
7. Apply adjusted-confidence, EV, and consensus-margin policy gates.
8. If every gate passes -> `CANDIDATE`; otherwise -> `NO_BET`.

## Tie policy

EV ties within floating-point tolerance are resolved deterministically in this
order:

`home -> draw -> away`

The rationale must record the candidate probability, odds, EV, adjusted
confidence, consensus margin, and policy thresholds.

## Risk level

V1 produces a descriptive risk label from adjusted confidence only:

- `low`: >= 0.85
- `medium`: >= 0.70 and < 0.85
- `high`: < 0.70

This label is descriptive and is not a staking recommendation.

## Constraints

- Immutable: return a new MatchContext.
- No mutation of consensus, confidence, adjustment, rules, or market data.
- No unsupported market types.
- No staking or bankroll sizing.
- No Kelly criterion in V1.
- No hidden model weighting.
- No candidate when governance blocks active decisions.

## Acceptance criteria

- blocked adjustment always yields NO_DECISION
- missing complete odds yields WATCH
- invalid decimal odds are rejected
- positive EV alone is insufficient for CANDIDATE
- all policy gates must pass for CANDIDATE
- highest EV market is selected deterministically
- input MatchContext remains unchanged
- CI passes Ruff, MyPy, tests, and coverage

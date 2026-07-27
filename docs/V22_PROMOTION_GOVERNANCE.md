# PRISM Exact Score V2.2 Promotion Governance

## Status

V2.2 is a candidate architecture. Production remains V2.1 until this gate returns `PROMOTE`.

## Evidence layers

### Layer A — scoreline replay

Historical replay may use frozen pre-match xG/model outputs to compare the V2.1 and V2.2 scoreline layers.

Minimum requirements:

- at least 30 replayable cases;
- V2.2 primary exact hits must not regress;
- V2.2 dual exact hits must not regress;
- mean minimum score distance must not regress;
- shared-story pair count must not regress;
- at least one of those metrics must materially improve.

### Layer B — full-stack validation

Direction Calibration may only be validated with genuinely frozen pre-match Consensus and Evidence outputs. Missing historical values must never be reconstructed from post-match outcomes.

Minimum requirements:

- at least 30 full-stack frozen cases;
- full-stack validation must pass its governed benchmark.

## Decisions

### PROMOTE

Both Layer A and Layer B satisfy the policy.

### HOLD

No material regression is present, but evidence is incomplete or sample size is below the governed threshold.

### REJECT

Any protected scoreline metric regresses against V2.1.

## Current July 2026 evidence

The recovered replay cohort contains 12 scoreline-replayable cases.

Observed V2.1 versus V2.2 candidate scoreline-layer results:

| Metric | V2.1 | V2.2 candidate |
| --- | ---: | ---: |
| Primary exact hits | 0 | 0 |
| Dual exact hits | 1 | 2 |
| Mean minimum score distance | 1.083333 | 1.000000 |
| Shared-story pairs | 2 | 2 |

Case movement:

- improved distance: 1;
- worsened distance: 0;
- tied distance: 11.

This is a positive candidate signal, not sufficient production evidence.

**Current governed decision: HOLD.**

Reasons:

1. 12 replayable cases are below the 30-case scoreline threshold.
2. Historical cases do not contain sufficient frozen Consensus/Evidence inputs to validate Direction Calibration.
3. V2.1 remains production until both evidence layers pass.

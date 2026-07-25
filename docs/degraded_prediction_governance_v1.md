# PRISM Degraded Prediction Governance V1

## Objective

Ensure collection-readiness degradation constrains downstream decision confidence without changing model probabilities, consensus mathematics, or the existing adjustment/decision engine thresholds.

## Policy

Collection readiness is translated into existing governed rule effects:

- `READY` -> no additional restriction;
- `DEGRADED` -> `restrict_high_confidence_action`;
- `REJECTED` -> `block_active_decision`.

The existing Adjustment Engine remains the sole owner of confidence ceilings. Under its V1 policy, `restrict_high_confidence_action` caps adjusted confidence at `0.69`. The existing Decision Engine requires at least `0.70` adjusted confidence for a `CANDIDATE`, so degraded collection data cannot produce an active candidate recommendation.

## Principles

1. Model probabilities and Consensus output are never rewritten by collection governance.
2. Governance is expressed through the existing rule-effect contract rather than a parallel confidence system.
3. READY inputs add no synthetic restriction.
4. DEGRADED inputs remain analytically observable but cannot escalate to a high-confidence active candidate.
5. REJECTED inputs remain fail-closed and should normally be stopped before model execution by the Collection Readiness Gate.
6. The injected governance record must be deterministic and auditable.
7. Existing stricter rule effects must remain effective; collection governance never relaxes another restriction.

## Pipeline position

```text
Collection Readiness Gate
        ↓
Collection Governance Effect
        ↓
Existing Rule Outputs
        ↓
Adjustment Engine
        ↓
Decision Engine
```

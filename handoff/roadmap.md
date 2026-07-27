# PRISM Roadmap

Generated: 2026-07-28

## Completed / established

- Canonical prediction architecture and Exact Score V2.x evolution.
- Formal prediction contract and immutable performance ledger.
- Verified outcome ledger and governed regression dataset.
- V2.1 vs V2.2 scoreline/full-stack evaluation layers.
- Shadow evaluation and governed promotion policy.
- Promotion CLI with PROMOTE/HOLD/REJECT exit semantics.
- CI workflow enforcement and decision artifact upload.
- Versioned promotion artifact provenance.
- Deterministic ledger fingerprints.
- Governed promotion cohort manifest and cohort identity tests.

## Active phase

**Forward-testing evidence integrity and governed V2.2 promotion.**

The system must accumulate real frozen cases, settle them only from verified outcomes, evaluate production vs candidate on the same cohort, and prevent promotion until evidence thresholds and quality gates pass.

## Near-term

1. Harden cohort manifest provenance and reproducibility.
2. Ensure frozen prediction IDs, settled outcomes and cohort membership form a traceable chain.
3. Persist the two newly frozen live predictions as governed forward-test samples using the formal contract.
4. After final results, ingest verified outcomes and run automatic post-match error attribution.
5. Continue accumulating the governed minimum cohort without cherry-picking.
6. Run V2.1 vs V2.2 scoreline and full-stack shadow evaluation.
7. Permit PROMOTE only through the governed CI release gate.

## Medium-term

- Expand error taxonomy and calibration diagnostics from genuine forward cases.
- Use recurring failure modes to drive V2.2.x changes, each protected by regression tests.
- Improve operational automation around prediction freeze, outcome verification, review generation and ledger persistence.

## Long-term

A continuously governed PRISM Enterprise loop where prediction, immutable evidence, verified outcomes, review, model revision and promotion are reproducible and auditable end to end.
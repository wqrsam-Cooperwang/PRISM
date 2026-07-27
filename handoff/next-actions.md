# PRISM Next Actions

Generated: 2026-07-28

Priority order:

1. Inspect current `main` and CI after the handoff documentation commits; do not assume an older SHA is still HEAD.
2. Continue governed promotion cohort manifest hardening from the existing implementation and identity tests.
3. Persist the two accepted 2026-07-28 frozen match predictions through the formal prediction contract/ledger without changing their values.
4. Preserve stable IDs so later verified outcomes can settle exactly those frozen records.
5. When the user says the two matches have ended, independently verify results, write verified outcome records, run automatic post-match review/error attribution, and persist all evidence.
6. Keep accumulating genuine forward-test cases until governed minimum sample requirements are satisfied.
7. Evaluate V2.1 production vs V2.2 candidate on the identical governed cohort.
8. Let CI make the final PROMOTE/HOLD/REJECT release decision; never bypass the governed gate.

Engineering discipline for every step: small commit -> Ruff lint/format -> MyPy -> tests/coverage -> report commit SHA -> react to CI result -> continue automatically when green.
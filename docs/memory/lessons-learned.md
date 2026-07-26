# PRISM Lessons Learned

Updated: 2026-07-26

## L-001 — Manual assistant persistence is unreliable
Repeated Airtable workflows showed that persistence depending on the assistant remembering Base IDs or being reminded to write records creates unacceptable communication cost and missing history.

Response: persistence must be triggered by the formal prediction pipeline itself. Airtable may be a dashboard or mirror, never the sole ledger.

## L-002 — Conversation memory is not durable project state
Important decisions made tens or hundreds of matches earlier can disappear from active conversation context. A single `project-memory.md` that depends on discretionary updates is insufficient.

Response: maintain structured durable memory, decision register, lessons, roadmap, current state, and dated handoffs in GitHub. Treat chat changeover as an explicit checkpoint operation.

## L-003 — CI style failures should not consume development cycles
Several implementation commits were functionally correct but failed only Ruff formatting or strict MyPy narrowing.

Response: proactively keep code formatter-compatible, use explicit typing where strict MyPy cannot narrow `Any`, and preserve the existing quality gate rather than weakening it.

## L-004 — Live success must not weaken evidence gates
The first real odds API connection succeeded, but market data alone does not justify a formal prediction.

Response: retain fail-closed collection readiness. Add independent real football data instead of fabricating missing team-strength or form inputs.

## L-005 — Accuracy is not profitability
A month of real-world use did not produce profit and incurred meaningful losses despite apparently useful predictions.

Response: separate probability quality from betting value. Measure exact-score EV, ROI/yield, drawdown, calibration, CLV where available, and out-of-sample stability. Do not infer edge from short winning streaks or headline hit rate.

## L-006 — Raw provider data and model logic must stay separated
Provider connectors should report facts and provenance. De-vigging, feature engineering, model weighting, consensus, scoreline inference, and governance belong inside PRISM.

Response: keep connectors deterministic, auditable, and provider-specific while preserving canonical observations downstream.

## L-007 — Secrets must never become research data
API credentials are operational configuration, not model inputs or provenance payloads.

Response: inject secrets at runtime, hide them from repr/logs, and prohibit them from reports, fixtures, artifacts, and performance-ledger snapshots.

# PRISM Roadmap

Updated: 2026-07-26

## Now
1. Complete Autonomous Performance Ledger V1 repository persistence and automatic commit workflow.
2. Add a second real football-data provider for fixtures, standings, recent results/form, team strength baseline inputs, and schedule context.
3. Run the first fully real formal PRISM prediction with immutable pre-match persistence.

## Next
4. Add automatic post-match settlement: final score, exact-score hit/top-N coverage, model evaluation, and hypothetical/actual P&L fields.
5. Add correct-score market acquisition and normalization so Exact Score probabilities can be compared with market prices and EV.
6. Add closing-price capture where a suitable source is available and calculate CLV.
7. Add availability/injury/lineup sources and weather, with independent verification and freshness rules.
8. Build shadow/paper performance reporting by league, model version, confidence, edge bucket, and scoreline price range.

## Later
9. Automate optional Airtable/dashboard sync from the canonical ledger rather than manual entry.
10. Configure periodic Mac/local Codex repository archive.
11. Generate immutable season-end datasets, manifests, and whole-season scientific reviews.
12. Evaluate paid providers only through controlled incremental-value tests against the free-first baseline.
13. Add independent AI intelligence review only if it measurably improves factual coverage/conflict detection.

## Product objective
The desired user experience is: the user names a match; PRISM identifies it, acquires and verifies real data, runs calibrated models and Exact Score inference, applies governance, persists the frozen prediction automatically, later settles and reviews the match automatically, and accumulates reproducible long-run evidence about whether a real market edge exists.

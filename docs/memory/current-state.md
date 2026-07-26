# PRISM Current State

Updated: 2026-07-26

## Product direction

PRISM is an evidence-governed football prediction and research system. European competitions are the primary research scope; leagues such as K League may be analyzed occasionally. Exact Score is the primary profitability research target. 1X2 remains a calibration, market-context, and model-input layer rather than the sole commercial target.

## Core production path

Provider data -> acquisition -> source envelopes -> adapters -> observations -> verification -> collection readiness -> features -> model suite -> consensus -> confidence/evidence -> governance rules -> adjustment -> decision -> scoreline -> prediction report.

The collection gate is fail-closed. Real market data alone is insufficient for a formal prediction; Elo/team-strength baseline and market baseline must both exist.

## Real provider status

The Odds API V4 market connector is implemented and live smoke tested successfully with GitHub Actions and repository secret `THE_ODDS_API_KEY`. API secrets must not enter logs, reports, fixtures, or ledger records.

Live market -> full production integration is implemented. A second real football-data provider is still required for team strength/recent form/schedule and related inputs before the first fully real formal prediction can be produced without fixtures.

## Performance ledger

Autonomous Performance Ledger V1 is being implemented. Formal predictions must persist an immutable pre-match snapshot before they are considered published. V1 source of truth is `data/performance-ledger/` in GitHub. Airtable is optional dashboard/sync only and must not be required for persistence.

Ledger snapshots contain PredictionReport, normalized observations/source metadata, collection gate, feature vector, scoreline candidates, model/version provenance, and later post-match settlement/review. Pre-match data is immutable after kickoff. Persistence failure must fail the formal prediction.

## Durable project memory

PRISM uses `docs/memory/` as structured durable memory across ChatGPT conversation limits and local Codex sessions. Before changing chat conversations, create a handoff checkpoint. The next conversation must read current state, decisions, roadmap, lessons, and the newest handoff before continuing work.

## Cost policy

Free-first architecture. Paid data sources may be considered only when measured incremental predictive/economic value exceeds cost. No recurring paid service should become required without explicit user approval.

## Profitability research

Recent real-world betting has not yet demonstrated profitability and has produced meaningful losses. PRISM must not assume prediction accuracy implies betting profitability. Future evaluation must prioritize exact-score probability quality, correct-score market edge/EV, closing-line value where available, ROI/yield, drawdown, calibration, and out-of-sample stability. Shadow/paper evaluation remains appropriate until measurable edge is established.

## Immediate next steps

1. Make the Performance Ledger implementation pass CI and complete automatic repository persistence.
2. Add post-match settlement/review automation.
3. Connect a second real football-data provider for team strength, recent form, standings/home-away form, and schedule inputs.
4. Run the first fully real formal PRISM prediction with automatic frozen ledger persistence.
5. Later configure periodic Mac/local Codex repository archive and season-end frozen datasets.

# PRISM Autonomous Performance Ledger V1

## Purpose

PRISM must persist every formal pre-match prediction and every post-match review without relying on a human or conversational assistant to remember to write to Airtable or any other external system.

## Source-of-truth rule

For V1, the PRISM GitHub repository is the durable source of truth for the performance ledger. Airtable is optional projection/synchronization only and must never be required for prediction persistence.

The production prediction workflow must write the ledger record as part of the same governed run that produces the formal prediction. A formal prediction is not considered published until its immutable pre-match snapshot has been persisted successfully.

## Storage layout

Append-only records are stored under `data/performance-ledger/` using deterministic match/prediction identifiers. Records are machine-readable JSON. Large raw provider payloads are not committed; the ledger stores normalized observations, source metadata, hashes/references, model outputs, market snapshots and governance decisions.

## Pre-match frozen snapshot

Each formal prediction record must include at least:

- stable prediction id and match id
- competition, home team, away team, kickoff
- prediction creation timestamp and freeze timestamp
- PRISM code/model version (Git commit SHA where available)
- data-readiness state and evidence state
- normalized source observations and source timestamps
- 1X2 model/consensus probabilities
- expected-goal parameters when available
- exact-score probability distribution or governed retained scoreline set
- ranked exact-score candidates and their probabilities
- observed correct-score market prices when available
- fair probabilities, edge and expected value when available
- confidence and governance decision
- actual wager metadata only when explicitly supplied by the user/system

After kickoff, pre-match fields are immutable. Post-match processing may only add settlement/review data.

## Post-match settlement and review

A scheduled/result-ingestion workflow will later enrich the frozen record with:

- full-time and half-time score where available
- closing market prices where available
- exact-score Top-1 / Top-N hit indicators
- probability scoring/calibration metrics
- closing-line value where measurable
- hypothetical governed-strategy P/L
- actual P/L only for explicitly recorded real wagers
- model/version cohort metrics
- review timestamp and result-source metadata

## Automation invariant

Persistence must be system-driven, not assistant-driven:

1. production prediction is generated;
2. ledger snapshot is validated;
3. ledger snapshot is persisted automatically;
4. only then may the run be treated as a formal PRISM prediction;
5. post-match workflow later settles the same record automatically.

If persistence fails, the workflow fails closed. It must not silently publish an untracked formal prediction.

## Airtable policy

Airtable may be used as a convenient dashboard or synchronized view. Missing Airtable credentials, Base ID, table configuration or Airtable availability must not cause loss of the canonical PRISM record. No user should need to repeat Base IDs or ask an assistant multiple times to save a prediction.

## Cost and migration policy

V1 uses GitHub-native storage and the existing GitHub Actions environment so it requires no new database subscription. If scale, concurrency or commercial product requirements outgrow repository-backed records, the ledger can migrate to a database such as PostgreSQL while preserving the same record schema and append-only/frozen-snapshot invariants.

## Exact-score priority

The performance ledger is designed around exact-score research. 1X2 remains an important calibration and market-context signal, but exact-score probability quality, correct-score market edge, settlement and long-run profitability are first-class evaluation targets.

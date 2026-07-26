# PRISM Project Memory & Continuity Ledger V1

## Purpose

PRISM development, prediction research, governance decisions, model lessons, and product strategy must survive ChatGPT conversation rollover. Long-term project continuity must not depend on any single chat window or conversational memory.

## Source-of-truth rule

GitHub is the canonical long-term project memory for PRISM. Chat conversations are working sessions, not the durable source of truth.

Important decisions, lessons, unresolved questions, experiment outcomes, and handoff state must be persisted under `docs/project-memory/`.

## Layout

```text
docs/project-memory/
├── CURRENT_STATE.md
├── DECISIONS.md
├── LESSONS.md
└── handoffs/
```

### CURRENT_STATE.md

The concise, current operating state of PRISM. A new development conversation should read this first. It should contain:

- current development stage;
- last known green commit;
- active architecture;
- provider/data status;
- ledger/performance status;
- immediate next steps;
- known blockers.

### DECISIONS.md

Append-only record of durable design and product decisions, including rationale and date. Examples:

- exact-score research is first-class;
- 1X2 is a calibration/market signal, not the sole product;
- prediction persistence is system-driven and fail-closed;
- GitHub ledger is canonical in V1;
- free-first data-source policy;
- paid providers require measurable incremental value;
- European leagues are the primary operating scope.

A decision may later be superseded, but the old decision and reason must remain visible.

### LESSONS.md

Append-only record of empirical lessons and failed assumptions, including:

- model weaknesses;
- live-provider failures;
- calibration findings;
- betting-performance findings;
- CI/integration incidents that reveal architectural issues;
- ideas tested and rejected;
- conditions under which a method works or fails.

This file is intended to prevent PRISM from rediscovering the same lesson hundreds of matches later.

### handoffs/

At conversation rollover or major milestones, create a dated handoff document containing:

- what was completed in the session;
- important commits and CI state;
- new durable decisions;
- new lessons/evidence;
- rejected directions and reasons;
- unresolved questions;
- exact next development sequence;
- any user operating preferences relevant to PRISM.

A handoff is not intended to reproduce the full raw transcript. It is a structured high-signal continuity artifact.

## Conversation rollover protocol

When the user indicates that a PRISM conversation is nearing its limit:

1. summarize the session into a new `handoffs/YYYY-MM-DD-<sequence>.md` file;
2. update `CURRENT_STATE.md`;
3. append durable decisions to `DECISIONS.md`;
4. append empirical lessons to `LESSONS.md`;
5. commit the continuity update to GitHub;
6. start the next chat by reading these files before continuing work.

The user should not need to reconstruct previous context manually.

## Raw transcript policy

Full conversation transcripts may be retained separately as archival material when available, but they are not the primary project-memory mechanism because a coding agent does not automatically have access to ChatGPT conversation history.

If the user later wants raw transcript archives on a local Mac, a separate export/sync mechanism may be configured. Those archives supplement, but do not replace, the structured GitHub continuity ledger.

## Local Mac continuity

A local clone of the PRISM repository provides a natural local copy of all project-memory files, prediction ledgers, settlement data, and code history. Periodic `git pull` or an automated local sync can mirror the canonical GitHub state without requiring manual copying through a coding agent.

## Season-scale research

At season end, Codex or another coding agent may use the local repository and performance ledger to run large-scale analysis. It should combine:

- frozen prediction records;
- settlement/review records;
- model/version history;
- DECISIONS and LESSONS history;
- experiment and promotion results.

This allows a later PRISM version to understand not only what happened over hundreds or thousands of matches, but why earlier design choices were made and which prior hypotheses failed.
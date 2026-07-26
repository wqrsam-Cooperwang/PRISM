# PRISM Durable Project Memory Protocol V1

## Purpose

PRISM must preserve long-horizon project knowledge across ChatGPT conversation limits, local Codex sessions, model upgrades, and multi-season research. The system must not depend on an assistant remembering to update one monolithic memory file.

## Source of truth

GitHub is the durable shared source for project memory. Local Codex and local repositories consume the same memory files through normal Git synchronization. Raw chat transcripts may be archived separately, but PRISM development must rely on structured durable memory rather than raw transcript recall.

## Memory layers

- `current-state.md`: canonical current architecture, active phase, latest stable commits, unresolved blockers, and immediate next steps.
- `decision-register.md`: append-only record of material product, architecture, governance, data, modeling, cost, and commercial decisions, including rationale.
- `research-principles.md`: durable scientific and product principles that must survive many seasons.
- `roadmap.md`: active development sequence and deferred work.
- `lessons-learned.md`: mistakes, failed approaches, CI incidents, provider limitations, and evidence from real prediction performance.
- `handoffs/`: one immutable checkpoint per conversation transition, summarizing what changed in that conversation and what the next conversation must read first.

## Conversation transition protocol

When the user says the conversation is nearly full or requests a PRISM handoff:

1. update `current-state.md`;
2. append material decisions to `decision-register.md`;
3. update `roadmap.md` and `lessons-learned.md` where needed;
4. create a new immutable file under `docs/memory/handoffs/`;
5. include the latest relevant commit SHAs and CI state;
6. record unresolved questions and exact next actions;
7. commit the memory checkpoint to GitHub before switching conversation.

The next PRISM conversation must read the latest `current-state.md`, `decision-register.md`, `roadmap.md`, and newest handoff before changing architecture or continuing implementation.

## Raw transcript policy

A full verbatim ChatGPT transcript is useful as archival evidence but is not the canonical operating memory. The assistant cannot guarantee automatic verbatim export of an entire ChatGPT conversation into the user's Mac. If the user exports or saves the raw transcript, it can be stored locally or attached to an archive. Structured memory remains the authoritative continuation layer.

## Local Codex integration

Codex does not need a special chat-memory channel. A local PRISM checkout can obtain the durable memory by pulling GitHub. Periodic local archive jobs may copy the repository or memory/ledger directories to a dated local archive. Season-end analysis may then use the complete local repository plus performance ledger.

## Enforcement principle

Material PRISM decisions are not considered durable until they are represented in repository memory. A single `project-memory.md` is insufficient because it mixes volatile status, permanent decisions, lessons, and roadmap into one file and is easy to neglect.

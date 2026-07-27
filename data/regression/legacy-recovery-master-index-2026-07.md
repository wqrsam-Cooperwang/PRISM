# PRISM Legacy Recovery Master Index — 2026-07

## Purpose

This file records the recovery boundary reached for historical PRISM football predictions and reviews through 2026-07-27. It is a provenance index, not a claim that every recovered scoreline is a replayable model sample.

## Persistent stores

### GitHub

Primary recovery artifacts:

- `data/regression/legacy-airtable-2026-07.json` — 12 scoreline-replay cases with frozen aggregate xG and regulation-time outcomes.
- `data/regression/legacy-recovery-audit-2026-07.md` — recovery rules, quarantines, and missing-data audit.
- `data/regression/legacy-chat-recovery-2026-06-27_2026-07-26.json` — recovered PRISM/chat prediction corpus.
- `data/regression/recovery-index-from-screenshots-2026-07.json` — user screenshot selections, kept separate from model provenance.
- `data/regression/screenshot-index-verified-outcomes-2026-07.json` — verified outcomes for screenshot-indexed matches.

### Airtable

Base: `PRISM Enterprise Database v3.0 — MASTER`

Recovery table: `Legacy Recovery Corpus`

Table ID: `tblmJJt7I01HC4LLf`

At the latest reconciliation the table contained **87 provenance records**. This is intentionally not a unique-match count: separate PRISM, screenshot, conflicting-version, and quarantine records may exist for the same fixture.

The Airtable recovery table preserves:

- team/date identity where known;
- PRISM score recommendations;
- screenshot selections separately;
- frozen pre-match xG where genuinely available;
- final score;
- recovery status;
- provenance;
- review notes;
- verification flag;
- conflict/quarantine explanation.

## Formal replay cohort

The current historical scoreline replay cohort contains 12 cases with frozen aggregate pre-match xG plus an unambiguous regulation-time outcome. These cases may be used for V1-vs-V2.1 scoreline-engine replay, but they do **not** reconstruct underlying model evidence weights unless those model outputs were separately frozen.

## Additional outcome-only corpus recovered

A materially larger set of historical PRISM predictions now has prediction scores plus actual results but no trustworthy pre-match aggregate xG. These are retained for historical exact-score hit/miss analysis, error taxonomy, and qualitative review, but never promoted into xG replay by inference.

Recovered FIFA knockout history includes verified outcomes for the earlier PRISM predictions:

- Brazil 2-1 Japan — PRISM candidate set `2-0 / 1-0 / 2-1`; third candidate exact.
- Germany 1-1 Paraguay — PRISM `2-0 / 3-0 / 2-1`; Paraguay advanced on penalties.
- Netherlands 1-1 Morocco — PRISM `1-1 / 1-0 / 2-1`; primary exact; Morocco advanced on penalties.
- Côte d’Ivoire 1-2 Norway — frozen PRISM `1-2`; exact.
- France 3-0 Sweden — frozen PRISM `2-0`.
- Mexico 2-0 Ecuador — frozen PRISM `1-1`.
- England 2-1 DR Congo — frozen PRISM `2-0`.
- Belgium 2-2 Senegal at 90 minutes, Belgium 3-2 AET — frozen PRISM `2-1`.
- USA 2-0 Bosnia — frozen PRISM `2-0`; exact.
- Spain 3-0 Austria — PRISM `2-0`.
- Portugal 2-1 Croatia — PRISM `2-1`; exact.
- Switzerland 2-0 Algeria — PRISM `2-1`.
- Australia 1-1 Egypt — PRISM `1-1 / 1-2 / 1-0`; primary exact; Egypt advanced on penalties.
- Argentina 1-1 Cabo Verde at 90 minutes, Argentina 3-2 AET — PRISM `2-0 / 3-0 / 2-1`.
- Colombia 1-0 Ghana — PRISM `2-1 / 1-0 / 1-1`; second candidate exact.

Other recovered historical/reviewed fixtures include Scandinavian leagues, UEFA qualifying/friendly fixtures, MLS and K League cases indexed in the recovery artifacts and Airtable corpus.

## Screenshot policy

User-supplied screenshots supplied a high-value match checklist and score-selection history, especially for 2026-07-19 through 2026-07-26. Screenshot selections are never silently relabeled as PRISM model outputs.

Where independent PRISM provenance exists, the fields are stored separately and any disagreement is marked `conflict`. Examples include Jaro–SJK, Västerås–Örgryte, Hammarby–Anderlecht, St Gallen–Benfica, Besiktas–Midtjylland, and Twente–Ferencváros.

## Key post-match lessons preserved

Recovered reviews reinforce several PRISM V2.1 governance lessons:

- correlated evidence cannot vote twice;
- paper strength/market direction must not become excessive certainty;
- weak-side scoring tails cannot be truncated too aggressively;
- early red cards and other path-changing events must be tagged rather than credited to the pre-match model;
- late-game cascades can invalidate a single static match-state assumption;
- a strong win direction does not automatically imply a high-total score;
- leading-game management can suppress the upper score tail;
- home/away regime and actual chance-quality structure matter more than generic season reputation.

## Known unresolved / quarantine items

The following remain unresolved because the missing information is genuinely not available in the currently accessible sources and must not be invented:

- `PR-LEG-20260712-KFU-BOD`: final 0-2 is known, but the original frozen exact-score recommendation and pre-match xG remain unrecovered.
- `P-UCL-20260716-ATE-KLA-V3.2`: frozen prediction/xG exists, but match identity conflicts with public 2026 UEFA pairing information; it remains quarantined.
- Several screenshot-indexed matches have verified outcomes but no independently recovered PRISM prediction provenance. They remain `screenshot-index` rather than model history.
- Some screenshot rows are visibly clipped or contain multiple historical versions; uncertainty is retained explicitly.
- Missing pre-match xG for outcome-only records is never reconstructed from post-match xG, final score, odds or hindsight.

## Exhaustion checks performed

The recovery pass used all currently accessible sources:

1. Original Airtable Predictions, Reviews, Match Statistics, Matches and available analyses.
2. Existing GitHub PRISM memory, regression, handoff and recovery artifacts.
3. Recoverable project/context history available to the current conversation.
4. User-supplied screenshot match indexes.
5. File Library match artifacts when retrieval succeeded.
6. Authoritative public result sources for final-score verification only.

Direct historical-chat retrieval was also attempted through available personal-context search and returned no additional old-chat records. File Library semantic retrieval was retried for missing knockout cases but repeatedly returned retrieval-service errors. GitHub searches for the remaining World Cup knockout fixture names produced no stored prediction artifacts.

## Recovery boundary

**The currently accessible recovery sources are exhausted.**

This does not mean unknowable historical fields have been manufactured. It means every match or artifact currently discoverable has been either:

- persisted with recoverable PRISM provenance;
- persisted as screenshot-index provenance;
- classified as outcome-only/prediction-only;
- marked conflict;
- or quarantined with an explicit reason.

A historical record may be promoted later only if an original pre-kickoff artifact becomes newly accessible.

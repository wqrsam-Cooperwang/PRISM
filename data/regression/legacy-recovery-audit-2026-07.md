# PRISM Legacy Recovery Audit — July 2026

## Scope

Recovery sources exhausted in this pass:

- Airtable `PRISM Enterprise Database v3.0 — MASTER`: Predictions, Reviews, AI Analyses, Match Statistics, Matches.
- Recoverable project/conversation context for the old `世界杯比赛预测` workflow.
- File Library searches for historical match material where retrievable.
- Authoritative public result verification only for final scores; never for reconstructing missing pre-match xG.

## Recovery rules

1. Never infer missing pre-match xG/lambda from the final score or post-match xG.
2. A scoreline-regression case requires frozen pre-match aggregate xG plus an unambiguous regulation-time final score.
3. Outcome-only samples may preserve historical predicted scores and final scores, but they do not enter V1 vs V2.1 xG replay.
4. Conflicting historical prediction versions are preserved as conflicts rather than silently resolved.
5. AET results use 90-minute score only when the historical evidence makes it unambiguous.
6. Identity mismatches are quarantined.

## Airtable inventory reconciliation

- Frozen/legacy Prediction records inspected: 25.
- Replayable scoreline cases after recovery: 12.
- Remaining unique recovery/quarantine items: 12.
- One additional Prediction record is an older France–Spain version superseded by the later frozen L2 record and is not counted as a separate match case.

## Newly recovered replayable cases

### England vs Argentina — `P-WC-2026-SF-ENG-ARG-V3.2`

- Frozen xG: England 1.43, Argentina 0.91.
- Frozen scores in Airtable: 1-0 / 1-1.
- Historical project context also preserves an earlier 1-1 frozen recommendation, so version provenance must be retained.
- Regulation-time final: England 1-2 Argentina, verified from FIFA match report.

### Sutjeska vs Kairat — `P-UCL-20260716-SUT-KAI-V3.2`

- Frozen xG: 0.95 / 1.82.
- Frozen scores: 1-2 / 0-2.
- Final: 0-2, verified from completed UEFA match reporting.

### Kristiansund vs Sarpsborg 08 — `PRED-20260718-KRI-SAR-FINAL`

- Frozen xG: 1.02 / 1.34.
- Frozen scores: 1-2 / 0-1.
- Final: 0-0, verified from Sarpsborg 08 official results.

### Spain vs Argentina — `PRED-20260719-M01-LOCKED`

- Frozen xG: 1.0 / 0.0.
- Frozen scores: 1-0; alternatives 1-1 / 2-0.
- Review records final as 1-0 AET and explicitly states the winning goal arrived in extra time.
- Regulation-time score is therefore unambiguously 0-0.

## Outcome-only historical recoveries

### Malmö vs Göteborg — `PR-LEG-20260712-MAL-GOT`

- Recovered old-chat prediction: primary 2-1; secondary 2-0; defensive 1-1.
- Historical confidence: PRISM 74/100.
- Final frozen in Airtable: 4-0.
- No numeric pre-match xG/lambda recovered. Outcome-only.

### Hammarby vs Kalmar — `PR-LEG-20260712-HAM-KAL`

- Recovered old-chat prediction: primary 3-1; alternatives 2-0 / 3-0 / 2-1.
- Historical confidence: PRISM 88/100.
- Final frozen in Airtable: 2-0.
- No numeric pre-match xG/lambda recovered. Outcome-only.

### Västerås vs Degerfors — `PR-LEG-20260712-VAS-DEG`

- Recovered old-chat prediction: primary 2-1; secondary 2-0; defensive 1-1.
- Historical confidence: PRISM 76/100.
- Final frozen in Airtable: 2-0.
- No numeric pre-match xG/lambda recovered. Outcome-only.

### Djurgårdens IF vs Halmstads BK — `P-SWE-ALL-20260714-DIF-HBK-V3.2`

- Final: 3-0.
- Historical records conflict: an earlier frozen workflow preserved 2-0, while Airtable later preserved 3-1 / 2-1; another historical context preserves 3-1 as the frozen record.
- No numeric pre-match xG/lambda exists in recoverable context.
- Preserve as version-conflicted outcome-only sample; do not force into xG replay.

## Remaining non-replayable cases

- `P-2026-0717-001` Botafogo vs Santos: final 2-1; frozen score exists; no pre-match aggregate xG recovered.
- `P-2026-0717-002` CF Montréal vs Toronto: final 0-0; frozen score exists; no pre-match aggregate xG recovered.
- `P-2026-0717-004` St Louis vs Sporting KC: final 3-2; frozen score exists; no pre-match aggregate xG recovered.
- `PRED-20260718-GAN-GIM-FINAL` Gangwon vs Gimcheon: final 2-0; frozen score exists; no pre-match aggregate xG recovered.
- `PRED-20260718-DAE-ULS-FINAL` Daejeon vs Ulsan: final 2-2; frozen score exists; no pre-match aggregate xG recovered.
- `PRED-20260718-INC-JEO-FINAL` Incheon vs Jeonbuk: final 1-0; frozen score exists; no pre-match aggregate xG recovered.
- `PR-LEG-20260712-KFU-BOD`: final 0-2; original exact-score prediction and xG remain unrecovered.

## Quarantine

### `P-UCL-20260716-ATE-KLA-V3.2`

Airtable links the match ID to Atlètic Club d'Escaldes vs KÍ Klaksvík. Public 2026 UEFA first-round records show those clubs were not paired with each other in that round. This is an identity/data-integrity conflict. The case remains quarantined even though frozen xG exists; attaching a result would contaminate regression data.

## Recovery boundary reached

All currently accessible structured PRISM records have been reconciled. Searches of recoverable conversation context produced additional exact-score history for the July 12 legacy matches and exposed the Djurgårdens version conflict. Searches for missing numeric pre-match xG/lambda for the remaining outcome-only samples did not produce values. File Library retrieval was also attempted; no trustworthy missing pre-match xG values were recovered.

The unrecovered fields above are therefore **known missing historical data**, not pending values to be guessed. They may only be promoted later if an original pre-kickoff artifact becomes accessible.

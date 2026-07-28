# PRISM Enterprise V3.1 — Implementation Roadmap

Status: Active planning

## Phase 1 — Data contracts and storage

- define prediction record schema;
- define feature snapshot schema;
- define result and event schema;
- define source provenance and confidence schema;
- implement immutable prediction archive;
- implement Prediction Memory storage.

Exit gate: one historical match can be reconstructed end to end from stored data.

## Phase 2 — Result collection and automatic review

- implement result-source adapters;
- reconcile conflicting sources;
- calculate post-match metrics;
- generate probabilistic error attribution;
- persist review reports.

Exit gate: completed matches are reviewed automatically without manual transcription.

## Phase 3 — Exact Score Engine V2

- implement baseline score matrix;
- add Dixon-Coles correction;
- add scenario mixtures;
- enforce matrix consistency tests;
- benchmark against current production baseline.

Exit gate: candidate engine passes calibration and reproducibility tests.

## Phase 4 — Football intelligence engines

Implement in priority order:

1. League Reliability;
2. Player Impact V2;
3. Goalkeeper Engine;
4. Team DNA;
5. Coach DNA;
6. Set-Piece Engine;
7. Tactical Matchup;
8. Aggregate Incentive;
9. Competition Priority;
10. Anomaly Detection.

Exit gate: every engine has registered features, tests, provenance and ablation results.

## Phase 5 — Learning and drift

- feature contribution scoring;
- league-specific calibration;
- drift detection;
- candidate weight proposals;
- candidate model training;
- production-versus-candidate reports.

Exit gate: the system creates a candidate model package automatically but cannot self-promote.

## Phase 6 — Controlled model promotion

- locked validation datasets;
- leakage tests;
- regression tests by league and metric;
- approval workflow;
- rollback package;
- release notes and version tagging.

Exit gate: V3.1 can complete a controlled production upgrade.

## Implementation priority

Accuracy-critical first:

1. Prediction Archive and Result Collector;
2. Auto Review Engine;
3. Exact Score Engine V2;
4. Player/Goalkeeper availability;
5. Aggregate Incentive and Competition Priority;
6. League-specific calibration;
7. Learning and drift;
8. remaining specialised engines.

## Definition of done for every module

A module is not complete until it has:

- specification;
- registered features;
- source mapping;
- implementation;
- unit tests;
- leakage tests;
- reproducible example;
- validation report;
- changelog entry.

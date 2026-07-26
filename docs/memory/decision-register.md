# PRISM Decision Register

Updated: 2026-07-26

This file records durable product, research, architecture, and operating decisions. New chat sessions must read it before changing direction.

## D-001 — Evidence-governed system
PRISM is an evidence-governed football prediction and research system, not a conversational tip generator. Data quality, provenance, calibration, governance, and reproducibility take priority over producing a prediction for every match.

## D-002 — Exact Score is the primary profitability target
Exact Score is the primary profitability research target. 1X2 remains an important calibration, market-context, consensus, and feature layer, but is not the sole commercial objective.

## D-003 — European competitions are primary
European competitions are the primary research scope. Other leagues, including K League, may be analyzed opportunistically.

## D-004 — Fail closed on insufficient evidence
Formal predictions must fail closed when required evidence is unavailable. Market odds alone are insufficient; PRISM must not invent Elo, team strength, availability, form, or other missing inputs merely to produce a report.

## D-005 — Free-first cost governance
Development and initial validation use free tools, free APIs, and free quotas wherever practical. A paid source may be adopted only after its incremental predictive or economic value can be measured and reasonably exceeds its cost. No recurring paid dependency is introduced without explicit user approval.

## D-006 — Autonomous persistence, not assistant memory
A formal prediction is not complete until its immutable pre-match snapshot has been persisted automatically. Airtable is not the source of truth and manual assistant-driven entry is not an acceptable dependency.

## D-007 — GitHub-native ledger first
V1 prediction and review history uses the repository ledger under `data/performance-ledger/`. GitHub is the cloud source of truth for early research. A production database may replace the storage backend later without changing ledger semantics.

## D-008 — Immutable pre-match record
The pre-match prediction snapshot is frozen before kickoff and cannot be rewritten after kickoff. Post-match facts and evaluation are appended separately to prevent hindsight bias.

## D-009 — Profitability must be demonstrated
Recent real-world betting has produced meaningful losses. PRISM must not equate prediction accuracy with profitability. Evaluation must include exact-score probability quality, correct-score market edge/EV, ROI/yield, drawdown, calibration, out-of-sample stability, and closing-line value when available. Shadow/paper evaluation is preferred until measurable edge exists.

## D-010 — Durable project memory
Long-term project knowledge must not depend on ChatGPT conversation context or an assistant remembering to update a single memory file. `docs/memory/` is the durable cross-session memory layer. Before changing chat conversations, create a handoff checkpoint; the next session must read the memory pack before continuing.

## D-011 — Local archive and season freeze
GitHub remains the early cloud source of truth, while the user's Mac should later maintain periodic repository archives. At season end, create an immutable season research dataset and manifest for whole-season review and model comparison.

## D-012 — Multi-source evidence
The Odds API is the first real market provider, not the sole football data source. PRISM should progressively use independent providers and official/reputable sources for team strength, form, schedule, availability, lineups, weather, and other relevant evidence. Provider outputs must remain auditable and separable.

## D-013 — External AI is optional reviewer, not authority
Gemini or another LLM is not required for the core prediction engine. If added later, it should primarily serve as an independent intelligence reviewer/conflict detector rather than directly overriding calibrated model probabilities.

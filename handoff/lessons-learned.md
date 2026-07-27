# PRISM Lessons Learned

Generated: 2026-07-28

## Modeling lessons

- Overall season numbers can hide decisive home/away regime differences.
- Readiness is not equivalent to nominal team strength; preseason, competitive rhythm and schedule context can materially alter performance.
- Correlated market signals create false confidence if counted as separate evidence.
- Forecast injuries/rotation/tactics should enter as probability-weighted scenarios until confirmed.
- Personnel changes can create regime breaks where older form becomes less representative.
- Exact-score selection benefits from governed candidate generation, regime conditioning and portfolio thinking rather than simply taking the top two raw Poisson cells.

## Governance lessons

- A prediction is useful research evidence only if it was frozen before the result.
- Outcome verification and prediction storage must remain separate to prevent hindsight contamination.
- Candidate superiority must be demonstrated on the same governed cohort as production.
- HOLD is a valid and necessary outcome when evidence is insufficient.
- Dataset identity matters: recording only a directory path is insufficient, hence file counts, SHA-256 fingerprints and cohort manifests.

## Engineering lessons

- Small CI failures have repeatedly come from Ruff formatting, line length, MyPy return typing, stale exports and tests lagging behind schema changes.
- After changing a schema, update its contract tests in the same change whenever possible.
- Run/anticipate Ruff format, Ruff lint, MyPy and the relevant tests before considering a change complete.
- CI should test not only implementation behaviour but also workflow contracts so enforcement cannot silently disappear.
- Promotion artifacts should be self-describing enough to audit a historical decision without reconstructing chat context.
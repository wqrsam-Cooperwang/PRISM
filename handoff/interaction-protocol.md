# PRISM Interaction Protocol

Generated: 2026-07-28

This file records how the user and ChatGPT should collaborate across new chat windows so the working style does not reset.

## User communication preference

- The user is not a software engineer and does not want implementation tutorials, code-level repair instructions, or explanations of how to edit files manually.
- When a CI result is GREEN and the user says "绿了", continue automatically to the next planned PRISM development step. Do not stop merely to restate that CI passed.
- When a CI result is RED and the user provides a screenshot/log, use that concrete failure evidence and repair it directly. Do not speculate about unseen errors before the screenshot is provided.
- After a repair, report only the new short commit SHA and ask for the next CI result. Use the same short-SHA style GitHub displays (normally 7 characters) unless a full SHA is materially necessary.
- Do not require the user to choose routine engineering actions. Make the engineering decision and execute it unless a genuine business/model-governance decision requires user judgment.
- Keep Production PRISM Exact Score V2.1 unchanged unless governed promotion explicitly approves a candidate.

## Development rhythm

1. Read current GitHub `main` as the source of truth.
2. Make one small governed change.
3. Push the commit.
4. User reports CI status.
5. GREEN -> immediately continue to the next planned step.
6. RED -> user supplies the failing CI screenshot/log; repair exactly that observed failure and push a new commit.
7. Never bypass Ruff, format, MyPy, tests/coverage, or promotion governance just to make progress appear faster.

## Match prediction workflow

- A prediction is only a formal forward-test case after durable performance-ledger persistence succeeds.
- Frozen values must never be rewritten after kickoff.
- Once a match ends, independently verify the result before writing the outcome ledger.
- Run automatic post-match review and error attribution on every settled case, including very poor predictions.
- Poor results are evidence, not exceptions: preserve them and use them to improve governance/model design.

## Conversation continuity

At the start of a new PRISM development chat, read this file together with the current handoff/roadmap files before taking action. Preserve this interaction style unless the user explicitly changes it.

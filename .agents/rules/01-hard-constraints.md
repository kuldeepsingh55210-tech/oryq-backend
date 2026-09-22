---
name: hard-constraints
description: Always-on rule. Non-negotiable constraints that apply to every task regardless of what is being built.
---

# Hard Constraints — ORYQ (apply to every task, no exceptions)

## Pinned versions — never change without testing full dependency resolution
- Python **3.11.9** on Render (`.python-version`) — 3.14 breaks pydantic-core on this deploy target.
- pydantic **>= 2.11.7** in `requirements.txt` — earlier versions cause `ResolutionImpossible` on
  Render (`supabase==2.31.0` → `realtime==2.31.0` → `pydantic>=2.11.7`).
- `websockets==15.0` pinned — Render dependency resolution.

## Zero-tolerance rules
- **Never fabricate data shown to a user.** If real data isn't available, show an honest
  pending/empty state. This project has already shipped fabricated metrics to paying-customer
  screens nine times — see `.agents/skills/known-bugs/SKILL.md`. Not a style preference.
- **Never let an all-provider LLM failure render as a confident empty success state** (the
  `0 of 0` bug class). Any ratio/percentage computed from LLM results needs a visible-error path
  for the total-failure case, not a silent zero. See `.agents/skills/ai-llm-system/SKILL.md`.
- **Never include run/build/test commands** (`npm run dev`, `uvicorn ...`, etc.) in
  implementation output — the founder tests everything manually via Antigravity and reports back.

## Requires explicit human approval before touching (do not do these autonomously)
- Enabling/disabling Row-Level Security
- The JWT/auth flow
- `scorer.py` / the AI Visibility Score formula
- Which LLM providers are in the scan rotation
- Any destructive database migration
- Adding Celery/Redis, GPU inference, pgvector, or Neo4j (deliberately deferred — see
  `.agents/skills/technical-debt/SKILL.md`)
- Adding payment/billing code

## Always true
- Preserve existing API response fields when adding new ones.
- One problem at a time — don't fold an unrelated refactor into a bug fix.
- "Code compiles" ≠ "feature works." For scan/auth changes specifically, verify against a live
  provider/database at least once before declaring done — see `.agents/skills/testing-strategy/SKILL.md`.
- If information about this project is unknown, say `[UNKNOWN]`. Never invent a fact about ORYQ.
- After any non-trivial change, update the relevant Skill file (see
  `.agents/workflows/update-context-after-change.md`).

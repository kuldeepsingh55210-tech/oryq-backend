---
name: source-of-truth
description: Always-on rule. Governs which document wins when project docs disagree.
---

# Source-of-Truth Hierarchy — ORYQ

This project has two kinds of history that conflict in places. When they conflict, **lower
number always wins**:

1. **Live code in the repo right now** — highest authority
2. `.agents/skills/known-bugs/SKILL.md` and `.agents/skills/current-state-and-roadmap/SKILL.md`
   (from the Sept 16 2026 live-audited handoff — most recent ground truth)
3. `.agents/skills/security-context/SKILL.md`
4. `.agents/skills/decisions-log/SKILL.md`
5. PRD v2.0 / TRD v2.0 / Backend Schema v2.0 / Implementation Plan v2.0 / Design Brief v2.0 /
   AppFlow v2.0 — **these describe an ambitious FUNDED vision (56-week, 2–7 engineers,
   self-hosted GPU, Celery/Redis, pgvector). Most of it was never built.** Treat every claim
   from these six documents as ASPIRATIONAL unless `.agents/skills/technical-debt/SKILL.md` or
   the current code confirms it exists.
6. Anything you infer or assume — lowest authority

**Golden rule:** if a Skill says something exists and you can't find it in the actual repo, the
repo wins. Flag the Skill as stale and correct it — don't assume the doc is right.

For task-type routing (which Skill to load for which kind of work), see
`.agents/skills/context-index/SKILL.md`.

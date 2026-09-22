# AGENTS.md — ORYQ

This project's AI context lives under `.agents/`, structured for Google Antigravity's native
Rules / Skills / Workflows system (also readable by Claude Code, Cursor, and other tools that
honor the AGENTS.md convention).

- `.agents/rules/` — always-loaded, every task. Read these first, every time.
- `.agents/skills/` — load conditionally, only what's relevant to the current task. Start with
  `.agents/skills/context-index/SKILL.md` if unsure which one you need.
- `.agents/workflows/` — step-by-step procedures for common task types (fixing a bug, adding a
  feature, touching security or the scan pipeline, keeping this system updated).

**Before any task:** read `.agents/rules/00-source-of-truth.md` and
`.agents/rules/01-hard-constraints.md`, then consult `.agents/skills/context-index/SKILL.md`
to see what else to load.

**After any non-trivial task:** run `.agents/workflows/update-context-after-change.md`.

Full reasoning for why this structure exists, and an evidence-based audit of the actual project
state as of Sept 16 2026, is inside the Skills — this file is deliberately just a pointer.

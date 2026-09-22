---
name: update-context-after-change
description: Run at the end of any non-trivial task to keep the .agents/ context system accurate.
---

# Workflow: Update Context After a Change

A stale context file is worse than no context file — it creates false confidence. Run this
checklist before considering any non-trivial task finished:

1. Did you fix or reproduce a bug? → Update `.agents/skills/known-bugs/SKILL.md`
   (move between CONFIRMED / FIXED / NOT REPRODUCED, add the date).
2. Did you complete or change a roadmap item? → Update
   `.agents/skills/current-state-and-roadmap/SKILL.md`.
3. Did you make a non-obvious technical choice (pin a version, choose a library, defer
   something)? → Add an entry to `.agents/skills/decisions-log/SKILL.md`.
4. Did you change the architecture, add a real (non-deferred) piece of infrastructure, or change
   which providers/services are active? → Update `.agents/skills/architecture-context/SKILL.md`
   and/or `.agents/skills/ai-llm-system/SKILL.md`.
5. Did you resolve one of the flagged `[CONFLICT — NEEDS VERIFICATION]` or `[UNKNOWN]` items in
   any Skill file? → Replace the tag with the confirmed fact and remove the flag.
6. Did you discover a new fact that contradicts something in `.agents/skills/technical-debt/SKILL.md`
   (e.g. something assumed "not implemented" actually exists)? → Correct it there.

Never leave this for "later" — do it in the same session, as the last step before reporting done.

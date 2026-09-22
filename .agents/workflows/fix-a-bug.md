---
name: fix-a-bug
description: Standard procedure for fixing any reported ORYQ bug.
---

# Workflow: Fix a Bug

1. Load Skill `known-bugs` — is this already logged? What status?
2. **Reproduce** — confirm the exact action, expected vs. actual behavior. Do not skip this even
   if the report seems obvious.
3. **Identify the layer** — frontend / API / backend / database / auth / LLM provider / infra.
   Load the matching Skill from `context-index` for that layer.
4. **Find root cause** — do not stop at the first plausible symptom. If this touches the scan
   pipeline, check specifically whether it's the `0/0`-silent-failure bug class (see
   `ai-llm-system` Skill).
5. **Minimal fix** — smallest safe, reversible change. State the plan before writing code.
6. **Verify live** — for scan/auth/database changes, this means running it against a real
   provider/database once, not just a clean compile (see `testing-strategy` Skill).
7. **Regression check** — could this fix break anything else that depends on the same code path?
8. **Update context** — move the bug's entry in `known-bugs` Skill from CONFIRMED to FIXED, with
   the date and what changed. If the fix reveals a new decision worth remembering, add it to
   `decisions-log`.
9. **Report plainly** — what changed, what was verified vs. assumed, what (if anything) is still open.

---
name: security-sensitive-change
description: Required gate before touching auth, RLS, RBAC, CORS, or any endpoint's auth requirements.
---

# Workflow: Security-Sensitive Change

Trigger this whenever a task touches: JWT/auth flow, Row-Level Security, RBAC roles, CORS
config, an unauthenticated endpoint, or secrets/env vars.

1. Load `security-context` Skill in full — read the findings register, not just the summary.
2. State explicitly: is this one of the items requiring human approval before proceeding
   (see `hard-constraints` rule)? If yes, stop and ask before writing code.
3. If not gated, still state the security impact of the change before implementing:
   - Does it change who can access what data?
   - Does it change token lifetime, storage, or transmission?
   - Does it add a new endpoint that needs auth/rate-limiting?
4. Never reintroduce a hardcoded secret default — this project already had a critical
   auth-bypass from exactly that mistake.
5. If the change relates to RLS: do not enable/modify policies without confirming first whether
   Supabase's PostgREST API is even publicly reachable for this project (this determines true
   urgency — see `security-context` Skill).
6. After implementing, update the findings register in `security-context` Skill with the new
   status and date.

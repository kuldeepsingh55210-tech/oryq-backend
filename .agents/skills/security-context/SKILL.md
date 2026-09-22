---
name: security-context
description: Load before touching auth, JWT, RBAC, RLS, CORS, rate limiting, or any endpoint's authentication requirements.
---

## Auth architecture (implemented — this contradicts the original PRD/TRD, which described auth as a future task)

- Password hashing: bcrypt via Passlib.
- Access tokens: HS256 JWT, 15-minute expiry.
- Refresh tokens: cryptographically random, hashed in `refresh_tokens` table, 30-day expiry,
  **rotated** (old token revoked) on every use.
- RBAC roles: `owner`, `admin`, `analyst`, `viewer`.
- Frontend session handling: React Context (`AuthContext`) with `authenticatedFetch()` — auto-
  retries once on a 401 by silently refreshing the token. **Any page that doesn't use this
  shared helper will silently break every 15 minutes** (this already happened — see Finding below).

## Findings register

| Severity | Finding | Status |
|---|---|---|
| CRITICAL | Hardcoded JWT signing secret shipped as a static fallback default in `config.py`. If the env var was ever unset, the app would silently sign tokens with a publicly-known string — full auth bypass. | **FIXED** (Sept session). Default removed, app now fails fast unless a real secret ≥32 chars is supplied. Both local `.env` and live Render env var rotated. |
| CRITICAL | RLS disabled on every table. No app-layer org/tenant filter enforced at the DB level — anyone with the Supabase key used by this backend can theoretically read/write any row via PostgREST, bypassing FastAPI entirely. | **NOT FIXED** — deliberately deferred pending a real policy design, not rushed. Key confirmed publishable/anon-class (not service-role), which lowers but does not remove risk. **P0 on roadmap.** |
| HIGH | Access/refresh JWTs stored in `localStorage`, readable by any successful XSS payload. | **NOT FIXED** — documented as a known, accepted trade-off pending cookie-based migration. |
| HIGH | 7 frontend pages independently re-implemented manual token/localStorage handling instead of using the shared `authenticatedFetch()` helper — sessions never auto-refreshed, hard-failing every 15 minutes. Pages: sentiment/[scanJobId], revenue/[brandId], benchmark/[brandId], entity/[scanJobId], alerts/[brandId], workspaces, workspaces/[workspaceId]. | **FIXED** (Sept session) — all 7 migrated to `authenticatedFetch()`. |
| MEDIUM | Scan initiation and "fear hook" endpoints (competitor comparison, hallucination check) require **no authentication at all**. | **NOT FIXED** — recommend rate-limiting (e.g. SlowAPI) to prevent quota-draining abuse of the free scan. |
| MEDIUM | CORS configured with `allow_methods=["*"]` and `allow_headers=["*"]` alongside `allow_credentials=True`. | **NOT FIXED** — recommend restricting to actually-used methods/headers. |
| LOW | No raw SQL string concatenation found; all queries go through the parameterized Supabase/PostgREST client. | No action needed. |

## Rules for any AI agent touching security-adjacent code

1. Never reintroduce a hardcoded secret default. Startup must fail loudly if a secret is missing or too short.
2. Never enable RLS without a full policy design reviewed by a human — a half-done RLS rollout can be worse than none (silently blocking legitimate access) or give false confidence (policies that don't actually restrict anything).
3. Never assume the anon-key mitigation is sufficient — verify whether Supabase's auto-generated PostgREST API is even publicly reachable before treating RLS as lower priority than the roadmap states.
4. Any new unauthenticated endpoint needs an explicit justification (is it meant to be public, like the free-scan lead magnet?) and should be rate-limited.
5. If you add a new frontend page that makes authenticated calls, use `authenticatedFetch()` — do not hand-roll token handling again.

---
name: current-state-and-roadmap
description: Load when planning what to work on next, when asked for project status, or at the start/end of a work session.
---

**Last verified state: October 2026, live working session with direct browser/terminal/database checks.**
Update this file at the start/end of every real work session — it is the single most
time-sensitive file in this system.

## Quick-reference status

| Area | Status |
|---|---|
| Core scanning engine (Groq + Gemini) | ✅ Working — verified Zepto scan, 74/100, 36 real responses |
| Async scan & progress polling | ✅ Implemented & verified live Oct 2026 (deliberately-failed scan error render untested) |
| Authentication & RBAC | ✅ Implemented — JWT 15-min + 30-day rotating refresh, 4 roles |
| Row-Level Security | ✅ Enabled on all 23 tables (zero policies, deny-all); backend uses secret key (verified live Oct 2026) |
| Revenue Intelligence | ✅ Working — NameError fixed and verified live Oct 2026 |
| Payments / Billing (Razorpay) | ❌ Not implemented — zero code either repo |
| Frontend design-system migration | 🟡 Partial — 3 of 6 pages (Sentiment, Revenue, Benchmark done; Entity, Alerts, Agency pending) |
| Production deployment | ✅ Live — backend on Render, frontend on Vercel, both directly verified |

## Top risks (October 2026)

1. **Payments absent** — zero monetization path exists today, single biggest revenue blocker.
2. **Landing page claims Claude/ChatGPT coverage** — landing page claims coverage for models that are excluded from rotation (OpenAI) or never integrated (Claude).
3. **Unauthenticated scan endpoints** — scan initiation and "fear hook" endpoints require no authentication, exposing to quota-draining abuse.
4. **Permissive CORS** — configured with `allow_methods=["*"]` and `allow_headers=["*"]` alongside `allow_credentials=True`.
5. **Unaudited tenant isolation** — tenant isolation relies on FastAPI app-layer ownership checks, which have NOT been audited. The backend key bypasses RLS, so any endpoint missing an ownership check can expose cross-tenant data. Audit every endpoint that takes scan_job_id / brand_id / workspace_id for ownership checks.

## Prioritized roadmap

**P1 — next (monetization & core trust)**
- Audit every endpoint that takes scan_job_id / brand_id / workspace_id for ownership checks
- Razorpay integration — zero monetization path exists today, single biggest revenue blocker
- Reconcile landing page claims with actual provider integrations (ChatGPT excluded from rotation, Claude never integrated)
- Rate-limit unauthenticated scan / "fear hook" endpoints to protect LLM quota
- Restrict CORS methods and headers to actually-used set
- Complete frontend design-system migration (Entity, Alerts, Agency Workspace)

**P2**
- Wire real sentiment data into the Overview tab (currently an honest "Pending" state; a real Sentiment endpoint already exists — reuse it)
- Test/verify deliberately-failed scan error screen render in production
- Migrate refresh tokens to httpOnly cookies
- Fix ~35 ESLint warnings + React 19 set-state-in-effect violation (Bug 5)

**P3 — deferred until real usage volume justifies the cost**
- Celery/Redis task queue, self-hosted vLLM, pgvector semantic search (see `07-TECHNICAL-DEBT.md`)

## Recommended next-session order (engineering judgment, not from the source docs verbatim)

1. Razorpay integration — unblock monetization and revenue.
2. Reconcile landing page claims vs real integrations (align copy or integrate Claude).
3. Rate-limit unauthenticated scan and fear-hook endpoints (e.g. SlowAPI).
4. Restrict CORS methods and headers.
5. Finish frontend design system migration (Entity, Alerts, Agency Workspaces).

## Open questions requiring a human decision (do not resolve these silently)

- India-first (₹) vs. US-first ($) pricing — never explicitly decided, conflicts between PRD v2.0 and the handoffs (`01-PRODUCT.md`).
- Fix the "ChatGPT, Claude, and Gemini" landing-page claim vs. build the Claude integration — pick one (`01-PRODUCT.md`, `04-AI-LLM-SYSTEM.md`).
- GitHub repo visibility (was public as of Handoff v2.0 — re-verify current status).
- Render free-tier cold start: accept for MVP, or add UptimeRobot pinging?

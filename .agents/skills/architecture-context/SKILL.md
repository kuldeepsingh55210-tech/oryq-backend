---
name: architecture-context
description: Load when working on system architecture, hosting/deployment topology, the scan execution flow, frontend design-system migration, or when deciding whether to introduce new infrastructure.
---

> Everything in this file is from Handoff v3.0 (Sept 16 2026), which was produced by a live
> working session with direct browser/terminal/database verification. Treat it as current.
> The original TRD v2.0 six-layer/AWS/Celery/vLLM architecture is a **separate, mostly
> unbuilt, aspirational document** — see `07-TECHNICAL-DEBT.md` before assuming any of it exists.

## Verified stack

**Backend:** Python 3.11.9 (pinned via `.python-version` — required for Render; do not change),
FastAPI 0.115.0 + Uvicorn 0.30.0, Pydantic 2.11.7 (must stay ≥2.11.7 — see `10-DECISIONS-LOG.md`),
Supabase Python SDK 2.31.0, PyJWT 2.13.0 + Passlib 1.7.4 (bcrypt) + python-jose 3.3.0,
ReportLab 4.2.0 (PDF), Resend 2.0.0 (email), groq 0.9.0 / google-generativeai 0.7.0 / openai 1.35.0.

**Frontend:** Next.js 16 (App Router), React 19, TypeScript 5 strict (clean `tsc --noEmit`),
Tailwind CSS v4, custom dark design system, React Context (`AuthContext`) + `localStorage` for
session state (⚠️ see `05-SECURITY.md` — this is a known accepted XSS-surface trade-off), hand-built
inline SVG for charts (no Recharts/D3 in the verified live build, despite TRD/Design Brief
referencing them).

**Database:** PostgreSQL via Supabase (managed), same instance for local dev and production.

**Hosting (verified by direct login/browser check, not inferred):**
- Backend → **Render**, Free tier, Oregon region. Live at `https://oryq-backend.onrender.com`.
  `README-DEPLOY.md` in the repo still incorrectly documents Railway — **fix this doc**, it's stale.
- Frontend → **Vercel**, live, 13+ recorded production deployments.
- Async task queue → **none** (Celery/Redis not used). Scans run in-process as background jobs via FastAPI `BackgroundTasks`.

## System flow (verified, current)

```
User Browser
  ↓
Next.js 16 Frontend (Vercel) — fetch() via AuthContext.authenticatedFetch()
  ↓ Bearer JWT
FastAPI Backend (Render) — CORS + JWT verification
  ↓ Non-blocking 200 OK + scan_job_id (frontend polls GET /api/v1/scan/{scan_job_id})
Scan Execution Engine (FastAPI BackgroundTasks + asyncio.gather)
  ↓            ↓            ↓
Groq Cloud   Gemini    OpenAI (wired, excluded from scan rotation;
(active)    (active)    still used for hallucination cross-verification only)
  ↓            ↓
  └────────────┴──────────────────────────────────────────┐
                                                            ↓
Post-Scan Pipelines: Sentiment classification → Entity extraction →
Alert threshold checks → Revenue metric tracking (verified live Oct 2026 — NameError fixed)
                                                            ↓
Supabase PostgreSQL (RLS enabled on all 23 tables, zero policies, deny-all; backend uses Supabase secret key which bypasses RLS)
```

## Scan execution architecture & polling (verified live October 2026)

The scan-start endpoint previously ran synchronously with timeout risks (old Bug 3/4). This was
resolved by returning `200 OK` + `scan_job_id` (`POST /api/v1/scan/start`, status queued) immediately
and executing in the background via FastAPI `BackgroundTasks`, while the frontend polls real
progress (`completed_prompts`/`total_prompts`) via `GET /api/v1/scan/{scan_job_id}`.
This was verified live end-to-end in production in October 2026 (caveat: a deliberately-failed
scan's error screen render was NOT tested). Given current volume, this remains the right-sized
solution — Celery/Redis is not needed.

## Frontend design-system migration status

3 of 6 target pages migrated to the premium `PremiumCard`/`MetricStat`/`SeverityBadge` component
set: **Sentiment, Revenue, Benchmark**. Still on legacy styling: **Entity, Alerts, Agency
Workspaces**. When touching any of these three legacy pages, check whether the task should
include migrating them, but don't do it silently as a side effect of an unrelated fix.

---
name: current-state-and-roadmap
description: Load when planning what to work on next, when asked for project status, or at the start/end of a work session.
---

**Last verified state: Sept 16 2026, live working session with direct browser/terminal/database checks.**
Update this file at the start/end of every real work session — it is the single most
time-sensitive file in this system.

## Quick-reference status

| Area | Status |
|---|---|
| Core scanning engine (Groq + Gemini) | ✅ Working — fixed this session; verified Zepto scan, 74/100, 36 real responses |
| Authentication & RBAC | ✅ Implemented — JWT 15-min + 30-day rotating refresh, 4 roles |
| Payments / Billing (Razorpay) | ❌ Not implemented — zero code either repo |
| Row-Level Security | ❌ Disabled on all tables — top security risk |
| Frontend design-system migration | 🟡 Partial — 3 of 6 pages (Sentiment, Revenue, Benchmark done; Entity, Alerts, Agency pending) |
| Production deployment | ✅ Live — backend on Render, frontend on Vercel, both directly verified |

## Prioritized roadmap

**P0 — do first, both fire on real usage paths right now / block everything else**
- Fix Bug 1: revenue-tracking `NameError` crash on every scan (`06-KNOWN-BUGS.md`)
- Fix Bug 2: "Your Brand" placeholder leak into real API calls (`06-KNOWN-BUGS.md`)
- Design and enable Row-Level Security (`05-SECURITY.md`) — largest data-isolation risk before real customer data accumulates

**P1 — next**
- Razorpay integration — zero monetization path exists today, single biggest revenue blocker
- Migrate Entity, Alerts, Agency Workspace pages to the premium design system
- Fix Bug 4 (fake scan-progress animation) and Bug 3 (synchronous scan timeout risk) — both directly affect perceived reliability of the core loop; fix together via async scan + SSE/polling

**P2**
- Wire real sentiment data into the Overview tab (currently an honest "Pending" state; a real Sentiment endpoint already exists — reuse it)
- Migrate refresh tokens to httpOnly cookies
- Rate-limit unauthenticated scan / "fear hook" endpoints

**P3 — deferred until real usage volume justifies the cost**
- Celery/Redis task queue, self-hosted vLLM, pgvector semantic search (see `07-TECHNICAL-DEBT.md`)

## Recommended next-session order (engineering judgment, not from the source docs verbatim)

1. Fix Bug 1 — trivial, minutes of work, currently firing on every scan.
2. Fix Bug 2 — trivial, closes a real data leak.
3. Directly verify the RLS/anon-key exposure: check Supabase dashboard → API settings → is
   PostgREST publicly reachable? This 10-minute check tells you how urgent true P0 actually is.
4. Scan endpoint → async (`202 Accepted` + `scan_job_id`) + SSE/polling — fixes Bug 3 and Bug 4 in one pass.
5. RLS policy design proper.
6. Razorpay — only after 1–5. Shipping payments on top of an unfixed timeout risk and an open
   data-isolation gap is the wrong order.

## Open questions requiring a human decision (do not resolve these silently)

- India-first (₹) vs. US-first ($) pricing — never explicitly decided, conflicts between PRD v2.0 and the handoffs (`01-PRODUCT.md`).
- Fix the "ChatGPT, Claude, and Gemini" landing-page claim vs. build the Claude integration — pick one (`01-PRODUCT.md`, `04-AI-LLM-SYSTEM.md`).
- GitHub repo visibility (was public as of Handoff v2.0 — re-verify current status).
- Render free-tier cold start: accept for MVP, or add UptimeRobot pinging?

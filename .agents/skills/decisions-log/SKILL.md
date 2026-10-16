---
name: decisions-log
description: Load before changing anything that looks like a deliberate past trade-off (pinned dependency versions, RLS deny-all/secret key, no-Celery, provider choice) so you do not silently undo an intentional decision.
---

Record *why* things are built the way they are, so a future agent doesn't "helpfully" undo a
deliberate trade-off. Add a new entry whenever you make a non-obvious technical choice.

---

**Groq as primary LLM provider (not OpenAI-first)**
Reasoning: free tier, 6000 RPM, no billing setup needed. Tradeoff: Groq/Llama doesn't return web
URLs, which is why the Citation Gap Finder is inert (`04-AI-LLM-SYSTEM.md`).

**Supabase (PostgreSQL) over MongoDB**
Reasoning: ACID compliance, pgvector available for future embeddings, RLS available for future
multi-tenancy. Tradeoff: more setup than Mongo, judged correct for the long term.

**RLS disabled on all tables (temporary) — SUPERSEDED (October 2026)**
Reasoning: originally, MVP speed with no auth yet — RLS would have blocked everything.
Superseded in October 2026: Row-Level Security was enabled on all 23 public tables with zero policies (deny-all for anon/authenticated roles). Replaced by the secret-key + deny-all-RLS architecture below.

**Secret-key + deny-all-RLS architecture (October 2026)**
Reasoning: Eliminates exposure through Supabase's auto-generated PostgREST API without requiring complex RLS policy migrations or risking breaking backend queries.
Implementation:
- Row-Level Security is ENABLED on all 23 public tables with ZERO policies (deny-all for anon/authenticated roles).
- Backend now uses a Supabase secret key (`sb_secret_...`), which bypasses RLS, so the app works.
- Tenant isolation relies on FastAPI app-layer ownership checks, which have NOT been audited. The backend key bypasses RLS, so any endpoint missing an ownership check can expose cross-tenant data.
- Publishable key from outside now returns empty on `brands`/`scan_jobs`/`users`.
- The old default secret key was deleted. Legacy JWT keys (anon/service_role) were disabled in the Supabase dashboard.
Trade-off / standing rule: The secret key must NEVER be used in the frontend or any browser context. If the frontend ever talks to Supabase directly, a policy design review is required first.

**Always git push after a verified fix (October 2026)**
Reasoning: Once a code change or documentation fix has been verified live in production or tested locally, it must be committed and pushed (`git push`) immediately. Keeping unpushed changes leads to desynchronization between environments, risks regressions or lost work, and leaves context stale for future sessions.

**No Celery, async FastAPI only**
Reasoning: MVP simplicity, no Redis needed, free-tier friendly. Tradeoff: long scans can time out
— now a confirmed issue (`06-KNOWN-BUGS.md` Bug 3). Fix is `BackgroundTasks` + polling, not
adopting Celery.

**Render for backend (not Railway)**
Reasoning: Railway free tier was exhausted. Render gives 750 hrs/month free. Tradeoff: 15-min
sleep on inactivity → 30–50s cold start for the first request after idle. `README-DEPLOY.md`
still incorrectly documents Railway — needs correcting.

**Python pinned to 3.11.9 / pydantic pinned to ≥2.11.7 / websockets pinned to 15.0**
Reasoning: dependency-resolution failures on Render otherwise (`08-CODING-STANDARDS-AND-RULES.md`
has the exact chain: `supabase==2.31.0` → `realtime==2.31.0` → `pydantic>=2.11.7`; Python 3.14
breaks pydantic-core). Do not touch these without testing full resolution.

**Evidence-first UX — the Headline Evidence card**
Reasoning (founder's own insight, not spec-driven): "scores don't create urgency; quotes do."
Implementation: a full-width card below the score dial showing the actual AI quote proving the
problem. **This is the single most important product decision in the whole project — never
remove or bury it in a redesign.**

**No JWT auth deferred / SSE over WebSocket / rule-based sentiment pre-filter**
These TRD-level architectural choices (JWT strategy, SSE for one-directional scan progress,
2-stage sentiment to cut LLM cost) were kept even in the scoped-down solo build and are confirmed
live. Treat these as settled, not open questions.

**Fabricated-data fixes (Sept 2026 session)**
Reasoning: nine separate places were found showing fake/hardcoded numbers as if they were real
measured data, including to paying customers. Decision: replace every one with an honest
pending/empty state rather than any plausible-looking placeholder number, even temporarily.
This is now a standing rule (`08-CODING-STANDARDS-AND-RULES.md` §Hard constraints, item 5), not
a one-time cleanup.

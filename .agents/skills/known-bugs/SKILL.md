---
name: known-bugs
description: Load at the start of any bug-fix task to check if the bug is already known, and update this file at the end of every session (move items between CONFIRMED / FIXED / NOT REPRODUCED).
---

Classification per the Context Engineering protocol: `CONFIRMED` / `FIXED` / `NOT REPRODUCED` / `UNKNOWN`.
All entries below are dated to the Sept 14–16 2026 live working session unless noted. **When you
fix or reproduce any of these, move them to the correct status and note the date — don't leave
this file stale.**

## FIXED (verified via clean compile / clean boot / live scan during the Sept session)

| # | Bug | Fix |
|---|---|---|
| 1 | Hardcoded JWT signing secret in `config.py` | Default removed; app fails fast without a real ≥32-char secret. Rotated locally and on Render. |
| 2 | 7 frontend pages bypassed shared `authenticatedFetch()`, sessions hard-failed every 15 min | Migrated all 7 to the shared helper. |
| 3 | Sidebar nav fell back to a scan-job ID when no brand ID was cached, sending users to the wrong brand's data | Fallback removed; links disable with a tooltip until a real brand ID exists. |
| 4 | Fabricated static "94.2% accuracy" shown before any hallucination audit ran | Replaced with an honest "Pending Audit" state. |
| 5 | Fabricated static "Sentiment: Neutral / RISING" badge, always shown regardless of real data | Replaced with "Pending Audit" (⚠️ not yet wired to real live sentiment data — see roadmap P2). |
| 6 | `Math.random()` used to fabricate missing weekly trend points on the score chart | Removed; only real historical points are plotted now. |
| 7 | Two hardcoded static metric bars ("Social Mention Share: 42%", "Technical Accuracy: 89%") with no backing data source anywhere in the backend | Removed entirely rather than left as fake numbers. |
| 8 | History page showed a fake "+14.2%" growth figure and fake "89.4" score when a brand had no history | Both replaced with a neutral "—". |
| 9 | `discovery/generator.py` used `random.uniform()` to fabricate "estimated lift %" / "competitor visibility %" shown to paying customers as if measured; related hardcoded `15.0` fallback found in `opportunities.py` during the same fix | Replaced with an honest qualitative tier (High/Medium, explicitly labeled "Preliminary Estimate") and null placeholders. |
| 10 | Benchmark corpus "General" fallback industry persisted `brand_count: 1` instead of `0`, suppressing the frontend's own "limited sample size" disclaimer | Fixed to persist `0`. |
| 11 | Total scan failure across all 3 providers, silently surfaced as "0 of 0" instead of a visible error (deprecated Groq model, retired Gemini model, exhausted OpenAI billing, all at once) | Groq/Gemini model IDs updated to verified-live models; OpenAI cleanly excluded from rotation (not deleted) pending billing top-up. Verified end-to-end: Zepto scan, 74/100, 36 real AI responses, $0.0082. |
| 2 | Placeholder "Your Brand" could leak into real API calls | Backend now returns brand_name in the scan-status response (hoisted safely, defaults to None on any failure). Frontend regex-guesser deleted entirely; falls back to an honest "Unknown Brand" label if brand_name is ever missing. Verified live on September 25 2026. |
| 12 | RLS disabled on all tables | Row-Level Security is ENABLED on all 23 public tables, with ZERO policies (deny-all for anon/authenticated roles). Backend now uses a Supabase secret key (`sb_secret_...`), which bypasses RLS, so the app works. Tenant isolation relies on FastAPI app-layer ownership checks, which have NOT been audited. The backend key bypasses RLS, so any endpoint missing an ownership check can expose cross-tenant data. Publishable key from outside now returns empty on `brands`/`scan_jobs`/`users`. The old default secret key was deleted. Legacy JWT keys (anon/service_role) were disabled in the Supabase dashboard. Verified live October 2026. |
| 13 | Revenue Intelligence crashes on every completed scan (old Bug 1) | Fixed variable name mismatch (`revenue_per_point` vs `revenue_per_visibility_point` -> `NameError`). Verified live in production (October 2026). |
| 14 | Scan-start synchronous timeout risk & fake scan-progress animation (old Bug 3/4) | Scan-start (`POST /api/v1/scan/start`) returns `200 OK` with `scan_job_id` + `status: queued` immediately and runs in background via `BackgroundTasks`; frontend polls real scan progress (`completed_prompts`/`total_prompts`) via `GET /api/v1/scan/{scan_job_id}` and only references active providers. Verified live Oct 2026 end-to-end in production (deliberately-failed scan's error screen was NOT tested). |

## CONFIRMED — not yet fixed

| # | Bug | File(s) | Detail |
|---|---|---|---|
| 5 | ~35 ESLint warnings (unescaped JSX quotes) + a React 19 set-state-in-effect violation causing cascading re-renders | `OverviewTab.tsx`, `ActionPlanTab.tsx`, `workspaces/page.tsx`, `SidebarLayout.tsx` | Low priority — no runtime correctness impact, lint cleanliness only. |

## RESOLVED

RESOLVED — schema.sql has exactly 23 CREATE TABLE statements (verified September 22, 2026).

## UNKNOWN

| # | Item | Detail |
|---|---|---|
| 1 | Hallucination two-tier verification behavior when OpenAI is excluded | Not confirmed whether the OpenAI cross-verification step no-ops cleanly or errors when the provider is disabled. |

## NOT REPRODUCED
(none logged yet — populate this section as items are investigated and found to no longer apply)

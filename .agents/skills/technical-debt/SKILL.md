---
name: technical-debt
description: Load before proposing or evaluating new infrastructure (Celery, Redis, self-hosted GPU/vLLM, pgvector, Neo4j, payment processors) to check whether it is already deliberately deferred and why.
---

This file exists because the original planning suite (PRD v2.0 / TRD v2.0 / Implementation Plan
v2.0) describes a **56-week, funded, 5-7 engineer build**. The actual project is a solo,
non-funded MVP. Most of the TRD's infrastructure was **never built, on purpose** — that's not
technical debt in the "we messed up" sense, it's correct scoping for the current stage. Don't
"fix" any of these without being asked; do flag if a real feature request now genuinely needs one.

## Not implemented — confirmed absent from the live codebase

| Item | TRD/PRD reference | Why it's fine to not have it yet |
|---|---|---|
| Payments (Razorpay/Stripe) | PRD v2.0 §9 | Zero matches for razorpay/stripe/payment/billing/subscription across both repos. Test keys exist but were never wired. **This is the actual P1 blocker to revenue — not infra debt, a real gap.** |
| Celery + Redis task queue | TRD v2.0 §2.2 | Scans run in-process via `asyncio.gather`. Fine at current volume; creates the sync-timeout risk in `06-KNOWN-BUGS.md` Bug 3. Right-sized fix is FastAPI `BackgroundTasks`, not standing up Celery/Redis. |
| Self-hosted vLLM / Llama 3.1 70B on GPU | TRD v2.0 §6 | Entire "self-hosting cost moat" strategy. All inference is cloud API (Groq/Gemini/OpenAI). Correct call — GPU infra makes no sense before real paid usage volume. |
| pgvector semantic search / prompt dedup | TRD v2.0 §2.3, §7 | `schema.sql` does not enable the vector extension or store embeddings. No prompt-dedup problem exists yet at this scale. |
| Three-tier LLM cost-routing engine (`llm_router.py`, tier-gated dispatch, `llm_cost_log` budget gating) | TRD v2.0 §3 | Full tiered router with cost/budget gating per call was never built. Current cost control is just "use free/cheap providers." Revisit only once there's a real cost problem to solve. |
| Row-Level Security | Backend Schema v2.0 §Core Principles | **This one is NOT fine to leave deferred much longer** — see `05-SECURITY.md`, it's the top P0 risk, listed here only because it's a Supabase-level thing rather than an app-code gap. |
| Knowledge graph in Neo4j, GEO Agent autonomous content publishing, SAML SSO, multi-region, Enterprise API/SDK | TRD v2.0 / PRD v2.0 V2/V3 phases | None of the V2/V3 funded-roadmap features exist. Entity Intelligence (V1-equivalent, backend-only) does exist — see `02-ARCHITECTURE.md`. |

## Partially real vs. fully aspirational — don't confuse these

- **Agency Workspaces**: real, working backend + legacy-styled frontend. Not aspirational — just
  not yet migrated to the premium design system (`02-ARCHITECTURE.md`).
- **Advanced Alerts** (Slack/email/webhook): real, working backend + legacy-styled frontend. Same
  situation as Agency Workspaces.
- **Entity Intelligence / Knowledge Graph**: the V1-scoped version (6-category extraction, D3
  graph format, gap detection) is real. The Neo4j migration and fine-tuning pipeline from
  TRD v2.0 V2/V3 are not.
- **Citation Gap Finder**: code complete, but functionally inert because current providers don't
  return URLs — this is a real, shippable feature blocked on adding a web-grounded provider
  (Perplexity), not vaporware.

## Rule of thumb for any agent evaluating "should I build X from the TRD"

Ask: does this solve a problem ORYQ has *right now*, at solo-founder, free-tier scale? If the
answer is "this solves a problem we'd have at 500+ paying customers," it belongs in
`09-CURRENT-STATE-AND-ROADMAP.md`'s P3 bucket, not in this sprint.

---
name: database-schema
description: Load before writing a migration, adding a table/column, writing a new query, or doing any Row-Level Security work.
---

## Platform
PostgreSQL via **Supabase**, project used for both local dev and production (confirmed via
matching project ref/URL in local `.env` and startup logs). Schema lives in `schema.sql` in the
backend repo — **that file, not this document, is the source of truth for exact columns.**

## Table count

`schema.sql` has exactly **23** public tables (verified September 22, 2026; confirmed October 2026).

## RLS status — RESOLVED (October 2026, verified live)

**Row-Level Security is ENABLED on all 23 public tables, with ZERO policies (deny-all for anon/authenticated roles).**
- **Backend access:** The backend uses a Supabase secret key (`sb_secret_...`), which bypasses RLS, so the app works.
- **Tenant isolation:** Tenant isolation relies on FastAPI app-layer ownership checks, which have NOT been audited. The backend key bypasses RLS, so any endpoint missing an ownership check can expose cross-tenant data.
- **External exposure:** Publishable key from outside returns empty on `brands`, `scan_jobs`, `users`.
- **Key hygiene:** The old default secret key was deleted. Legacy JWT keys (anon/service_role) were disabled in the Supabase dashboard.
- **Standing rule:** RLS is ON with zero policies. Do not disable it. Do not add permissive policies. Never use the secret key in the frontend or any browser context. If the frontend ever talks to Supabase directly, a policy design review is required first.

## Known table groups (per Backend Schema v2.0 — verify against live schema.sql before trusting exact columns)

| Group | Tables (as originally designed) |
|---|---|
| Identity & Auth | organizations, users, refresh_tokens, email_verifications, oauth_accounts |
| Project Config | projects, prompts, competitors, alert_settings |
| Scan Execution | scan_jobs, llm_responses, llm_cost_log, scan_budgets |
| Parsed Results | visibility_results, citations, sentiment_results, competitor_mentions |
| Scoring & ROI | visibility_scores, score_translations |
| Actions & Ops | optimization_actions, alerts, audit_logs, api_keys |

**[INFERRED]** — this table list is from the TRD-aligned Backend Schema v2.0 document (the
funded/aspirational plan), not from a direct read of the live `schema.sql`. The actual live
schema may differ (e.g. Handoff v2.0 describes simpler tables: `brands`, `scan_jobs`,
`llm_responses`, `visibility_results`, `visibility_scores`, `llm_cost_log`, `competitors`,
`hallucination_results`). **Do not assume the full 22-table design exists** — confirm against
`schema.sql` before writing a migration or a query that depends on a specific table/column.

## Extensions

- **pgvector**: `07-TECHNICAL-DEBT.md` — NOT enabled. No `CREATE EXTENSION vector` or embedding
  columns confirmed in the live schema. Semantic prompt dedup described in TRD v2.0 does not exist.
- No other extensions confirmed.

## Rules when touching this schema
1. Never run a destructive migration without an explicit go-ahead and a stated rollback plan.
2. Any new table needs `org_id`/`project_id` for future RLS policy compatibility. Every new table must have RLS enabled at creation (`ALTER TABLE <table_name> ENABLE ROW LEVEL SECURITY;` with zero policies).
3. Confirm the real table count (23 tables) and full column list directly from `schema.sql` before this file is trusted for anything beyond orientation.

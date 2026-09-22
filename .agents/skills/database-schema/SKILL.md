---
name: database-schema
description: Load before writing a migration, adding a table/column, writing a new query, or doing any Row-Level Security work.
---

## Platform
PostgreSQL via **Supabase**, project used for both local dev and production (confirmed via
matching project ref/URL in local `.env` and startup logs). Schema lives in `schema.sql` in the
backend repo — **that file, not this document, is the source of truth for exact columns.**

## ⚠️ Unresolved conflict — table count

Two independent audit passes in the same live session (Sept 14–16 2026) reported **23** and
then **18** tables respectively when describing `schema.sql`. This was never resolved.
**[CONFLICT — NEEDS VERIFICATION]**

**Before relying on any table-count-based capacity or security plan, run:**
```
grep -c "CREATE TABLE" schema.sql
```
and update this file with the real number.

## RLS status — CRITICAL, see `05-SECURITY.md` for full detail

**Row-Level Security is disabled on every table.** Zero `ENABLE ROW LEVEL SECURITY` / `CREATE
POLICY` statements exist in `schema.sql` as of Sept 16 2026. The Supabase key currently in use
was confirmed to be **publishable/anon-class, not service-role**, which lowers but does not
remove the exposure risk — do not treat that as sufficient mitigation on its own. **Do not
enable RLS casually; it needs a proper auth-integrated policy design (P0 on the roadmap).**

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
2. Any new table needs `org_id`/`project_id` for future RLS policy compatibility, even while RLS is off — don't make the eventual RLS rollout harder.
3. Confirm the real table count and full column list directly from `schema.sql` before this file is trusted for anything beyond orientation.

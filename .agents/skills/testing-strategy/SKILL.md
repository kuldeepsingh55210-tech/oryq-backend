---
name: testing-strategy
description: Load when writing tests, deciding how to verify a change, or before declaring any scan-pipeline or auth change complete.
---

## Current state — `[UNKNOWN / LOW CONFIDENCE]`

No test suite, coverage report, or CI test-run was described or verified in any of the source
documents for this context system (PRD v2.0, TRD v2.0, Backend Schema v2.0, Implementation Plan
v2.0, Handoff v2.0, Handoff v3.0). The Sept 2026 live session's verification method was
**manual, live, end-to-end checks** (a real scan against a known brand, a clean `tsc --noEmit`,
a clean backend boot) — not an automated test suite. **Before assuming any automated tests
exist, check for a `tests/` directory or CI config in both repos.**

## Recommended approach, given solo-founder / free-tier constraints

Do not propose a TRD-v2.0-scale testing program (Playwright E2E fleet, VCR cassette LLM mocks,
Locust load testing, cost-regression suites) — that's funded-team scope. Right-sized for the
current stage:

1. **A handful of integration tests around the scan pipeline** — specifically targeting the bug
   class that already bit this project once: an all-provider-failure case must raise/return a
   visible error, never a silent `0/0` success. This is the highest-value test to write given
   the project's actual failure history.
2. **A smoke test for auth** — register → verify → login → refresh → logout, since this is a
   security-critical path with real users depending on it now.
3. **TypeScript strict mode is already doing real work** — `tsc --noEmit` clean compile was used
   as a verification gate this session. Keep relying on it; don't let type errors creep back in.
4. **Manual verification checklist for any scan-pipeline change**: run one real scan against a
   known brand (Zepto is the documented reference case, expect ~74/100, ~36 responses,
   ~$0.0082) and confirm the score, evidence card, and hallucination tracker all populate with
   real data — not just that the request returns 200.

## Rule for AI agents

"Code written" is not "feature complete" (`08-CODING-STANDARDS-AND-RULES.md` rule 9). For this
project specifically, that means: **do not declare a scan-pipeline or auth change done without
running it against a live provider/database at least once**, given the documented history of
changes that compiled cleanly but silently did nothing (the total-outage bug) or silently did
the wrong thing (the fabricated-metrics bugs). A clean compile is necessary, not sufficient.

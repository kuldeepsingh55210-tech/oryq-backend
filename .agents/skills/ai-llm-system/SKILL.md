---
name: ai-llm-system
description: Load before touching scan.py, any LLM provider client, the scoring formula, sentiment/hallucination detection, the citation gap finder, or anything that computes a ratio/percentage from LLM responses.
---

## ⚠️ Read this before touching anything scan/provider related

On Sept 14 2026, **all three configured LLM providers were silently failing simultaneously**:
Groq's model was deprecated by Groq on 17 June 2026; Gemini's model was retired by Google on
1 June 2026; OpenAI's account had zero billing credits. A code-level bug caused this **total
failure to render as an innocuous "0 out of 0" result instead of a visible error** — meaning the
product could appear to work (return a confident-looking empty report) while silently producing
no real data, for any brand, indefinitely. This was found only by a live end-to-end test, not
by reading logs or trusting prior status.

**Standing rule:** any place in this codebase that computes a ratio/percentage/count from LLM
call results (score components, sentiment breakdowns, hallucination rates, etc.) must be checked
for the same failure shape: does an all-failure case produce a *visible error*, or does it
silently produce `0/0` → a plausible-looking but fake result? Grep for this pattern before
declaring any scan-pipeline work complete.

## Verified current providers (as of Sept 16 2026 — confirm model IDs are still live before assuming this)

| Provider | Model | Role | Active in scan rotation? |
|---|---|---|---|
| Groq | `openai/gpt-oss-120b` | Primary scan runner, sentiment escalation, entity extraction, fix-content generation, prompt discovery | ✅ Yes |
| Google Gemini | `gemini-3.1-flash-lite` | Secondary scan runner (multi-model diversity) | ✅ Yes |
| OpenAI | `gpt-4o-mini` | Secondary hallucination-claim verification for HIGH/CRITICAL severity only | ❌ No — excluded from rotation (no billing credits as of Sept 2026). Code path preserved, commented out in `app/api/scan.py` ~lines 156–157 for easy re-enable once billing is resolved. |
| Anthropic / Claude | — | — | **Never integrated.** Landing page copy claims "ChatGPT, Claude, and Gemini" — this is a marketing/implementation mismatch, not a code bug. Either fix the copy or build the integration; don't leave the gap silent. |

LLM model identifiers drift as vendors deprecate/retire models (this is exactly what caused the
total outage above). **Before assuming a model ID is still valid, verify it's currently live**
rather than trusting this table indefinitely.

## Scoring & detection logic

- **Weighted composite score** with **dynamic re-normalization** if a provider is unavailable —
  a transient provider outage should not artificially crater a brand's score. (This mechanism
  existed but was masked by the silent-0/0 bug when *all* providers failed at once — partial
  failure and total failure are different code paths; make sure both are still correct.)
- **Brand mention detection** uses four cascading strategies: exact substring match, multi-word
  decomposition, regex word-boundary match (catches possessives/punctuation), alias matching.
- **Sentiment** is two-stage: free rule-based keyword scoring first, escalating only ambiguous
  responses to a live Groq call — estimated 60–70% of sentiment LLM cost avoided this way.
- **Citation Gap Finder**: code complete but functionally **inert** — Groq/Gemini responses
  rarely contain raw URLs to extract. Needs a web-grounded provider (Perplexity `sonar-pro` was
  the TRD's proposed fix) to actually activate. Do not spend time debugging it as if it's broken;
  it's working as designed against providers that don't return citations.
- **Hallucination detection**: two-tier — Groq flags candidates, OpenAI `gpt-4o-mini`
  cross-verifies HIGH/CRITICAL claims **only when OpenAI is enabled**. With OpenAI currently
  excluded, verify whether this tier silently no-ops or errors — not confirmed either way.
  **[UNKNOWN — NEEDS VERIFICATION]**

## Not implemented (do not assume these exist — see `07-TECHNICAL-DEBT.md`)

- Self-hosted vLLM / Llama 3.1 70B GPU inference (TRD v2.0 §6) — all inference is cloud API calls.
- Three-tier cost-routing engine (Tier 1/2/3 routing, `llm_router.py`, `llm_cost_log` cost-gating)
  as specified in TRD v2.0 §3 — **[UNKNOWN — NEEDS VERIFICATION whether any lightweight version
  of cost logging exists in the live code; do not assume the full tiered router does.]**
- pgvector-based semantic prompt deduplication.
- Batch API usage (OpenAI/Anthropic Batch API for scheduled scans).

## Cost reference point
A real verified scan (36 responses, 2 providers) cost **$0.0082**. Use this as a sanity check
when estimating cost impact of any change to prompt count, provider count, or output token limits.

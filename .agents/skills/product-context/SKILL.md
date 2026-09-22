---
name: product-context
description: Load when working on product features, pricing/monetization decisions, target users/ICP, competitive positioning claims, or any UI/landing copy that makes a claim about what ORYQ does or which providers it scans.
---

## What it is
ORYQ is a **Generative Engine Optimization (GEO)** platform — the AI-search equivalent of SEO.
It scans how a brand is mentioned, described, and recommended by LLMs (Groq-hosted open models
+ Google Gemini; OpenAI wired but currently excluded — see `04-AI-LLM-SYSTEM.md`), computes a
0–100 AI Visibility Score, detects factual hallucinations with the verbatim AI quote as evidence,
benchmarks against competitors and industry percentiles, and generates ready-to-use fix content
(About-page copy, Schema.org JSON-LD, FAQ content, LinkedIn drafts).

**One-line value prop (verbatim, keep this):**
> "See exactly what AI says about your brand, see where it's wrong, get the fix in the same tool."

## Founder / build model
Solo, non-funded founder, ~₹2,000 initial budget. This is a **deliberate scope-down** of the
funded PRD v2.0/TRD v2.0 vision, built entirely on free/near-free tiers: Groq, Gemini, Supabase,
Render, Vercel, Resend. **Do not propose infrastructure that assumes a funded team or budget**
unless explicitly asked to plan for that future state (see `07-TECHNICAL-DEBT.md`).

## Target users / ICP
- B2B SaaS founders (originally scoped Series A–B, $5M–$30M raised, per PRD v2.0 — but the actual
  monetization plan is India-first, see below, so treat the PRD's US-first ICP framing as
  **[CONFLICT — NEEDS VERIFICATION]** against actual go-to-market)
- Marketing managers at tech companies
- GEO/SEO specialists
- Digital marketing agencies (Agency workspace feature exists, backend + legacy-styled frontend)

## Customer problems being solved
1. No way to know if AI mentions their brand at all
2. No way to detect AI saying factually wrong things about their brand
3. No way to compare against competitors in AI-generated answers
4. Even if they knew the problem, no actionable fix content

## Competitive differentiation (status-checked)
| Claim | Verified? | Note |
|---|---|---|
| Evidence-first UX (real AI quotes, not just a score) | ✅ Yes | Headline Evidence card + Hallucination Tracker, verified in UI |
| Multi-LLM coverage | ⚠️ Partial | Only Groq + Gemini active. OpenAI excluded (no billing). **Anthropic/Claude has never been integrated**, despite landing-page copy claiming "ChatGPT, Claude, and Gemini." Fix the copy or build the integration — see `09-CURRENT-STATE-AND-ROADMAP.md`. |
| Ready-to-use fix content, not just advice | ✅ Yes | About-page copy, Schema.org, FAQ Q&As, LinkedIn drafts — all generated |
| Low cost structure | ✅ Yes | Verified: $0.0082 for a 36-response scan |

## Monetization plan
- **[CONFLICT — NEEDS VERIFICATION]**: PRD v2.0 specifies USD pricing ($149/$399/$299-per-client/
  $3,999+ Enterprise) for a US-first ICP. Handoff v2.0/v3.0 describe an **India-first** plan in ₹
  (Starter ₹2,999/mo, Growth ₹7,999/mo, Agency per-client). Razorpay test keys were obtained but
  **payment integration has never been built** (zero matches for razorpay/stripe/payment/billing
  in either repo as of Sept 16 2026). This currency/market decision needs to be made explicitly
  before billing is built — don't default to either without asking.
- Free lead magnet: one-time scan via landing page.

## What must never be lost when redesigning UI or copy
1. **Evidence over abstraction** — always show the actual AI quote, never just a score.
2. **Fix included** — every problem insight ships with actionable fix content.
3. **Cost transparency** — scan cost is shown to the user, framed as value not expense.
4. **Calm intelligence** — the UI is a precision instrument (Bloomberg-Terminal-meets-Linear),
   not a marketing dashboard. Red is reserved exclusively for genuine risk (hallucinations,
   score drops, critical failures) — never decorative.

Design language reference: Signal Blue `#1B4FD8`, Pulse Green `#0EA47A`, Alert Red `#DC2626`,
dark sidebar `#0F172A`. Typefaces: DM Serif Display (headlines/score moments), Inter (UI),
JetBrains Mono (all numbers — scores, costs, routes). Full detail in the original Design Brief
v2.0 if a new screen needs styling — treat its visual system as current even though most of its
*feature* assumptions (LLM Cost Dashboard, tier badges, GEO Agent) are aspirational.

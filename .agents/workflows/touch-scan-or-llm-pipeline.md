---
name: touch-scan-or-llm-pipeline
description: Required procedure before and after any change to scan.py, LLM provider clients, scoring, sentiment, or hallucination detection.
---

# Workflow: Touch the Scan / LLM Pipeline

This pipeline has already had a total silent failure once (all 3 providers down, rendered as a
confident "0 of 0" instead of an error). Treat every change here with extra suspicion.

1. Load `ai-llm-system` Skill in full.
2. Before changing anything, confirm which providers are currently active in the rotation
   (this drifts — models get deprecated/retired without warning).
3. If you're changing anything that computes a ratio, percentage, or count from LLM responses:
   explicitly verify what happens when **all** providers fail, not just one. It must produce a
   visible error, never a silently "successful" empty/zero result.
4. Do not touch `scorer.py` / the score formula without explicit approval (see `hard-constraints`).
5. After implementing, run one real scan end-to-end against the documented reference case
   (Zepto — expect ~74/100, ~36 responses, ~$0.0082 cost) and confirm the score, evidence card,
   and hallucination tracker all populate with real data. A clean compile is not sufficient
   verification for this pipeline specifically.
6. Update `ai-llm-system` Skill with any provider/model ID changes, and `known-bugs` if this was
   a bug fix.

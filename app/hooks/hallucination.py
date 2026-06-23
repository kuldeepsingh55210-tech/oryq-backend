"""
Hallucination Detector Hook — Phase 2 Feature 2

Uses Groq (free, fast) to fact-check AI responses that mention the brand.
Compares against known facts and identifies factual errors.
"""

import json
import logging
from typing import Dict, List, Optional

from app.database import get_supabase_client
from app.scanner.providers.groq_provider import call_groq

logger = logging.getLogger(__name__)

FACT_CHECK_SYSTEM_PROMPT = (
    "You are a fact-checker. Given known facts about a brand and an "
    "AI-generated response mentioning that brand, identify if the response "
    "contains any FACTUAL ERRORS about pricing, features, founding info, "
    "or category. Respond ONLY in valid JSON with no extra text: "
    '{{"has_error": true/false, "error_description": "string or null"}}'
)


async def check_hallucination(
    brand_name: str,
    response_text: str,
    provider_name: str,
    known_facts: Dict[str, str],
) -> Optional[Dict[str, str]]:
    """
    Fact-checks a single AI response against known brand facts using Groq.

    Args:
        brand_name: The brand being checked.
        response_text: The AI-generated response to fact-check.
        provider_name: Which provider generated the response.
        known_facts: Dict of known facts (e.g. {"pricing": "...", "founded": "2021"}).

    Returns:
        Hallucination dict if error found, None otherwise.
    """
    if not response_text or not known_facts:
        return None

    # Format the fact-check prompt
    facts_str = "\n".join(f"- {k}: {v}" for k, v in known_facts.items())
    prompt = (
        f"{FACT_CHECK_SYSTEM_PROMPT}\n\n"
        f"Brand: {brand_name}\n\n"
        f"Known Facts:\n{facts_str}\n\n"
        f"AI Response to fact-check:\n\"{response_text[:500]}\"\n\n"
        f"Respond ONLY in JSON:"
    )

    try:
        result_text, cost_usd, latency_ms = await call_groq(prompt)
    except Exception as e:
        logger.error(f"Groq call failed during hallucination check: {e}")
        return None

    # Skip error responses from provider
    if result_text.startswith("Error:"):
        logger.warning(f"Hallucination check provider returned error: {result_text[:200]}")
        return None

    # Parse JSON response from the fact-checker
    try:
        # Strip markdown code fences if present
        cleaned = result_text.strip()
        if cleaned.startswith("```"):
            # Remove ```json ... ``` wrappers
            lines = cleaned.split("\n")
            cleaned = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            )
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(
            f"Failed to parse fact-check JSON response: {e}\n"
            f"Raw response: {result_text[:300]}"
        )
        return None

    has_error = parsed.get("has_error", False)
    error_description = parsed.get("error_description")

    if has_error and error_description:
        return {
            "claim": error_description,
            "source_response": response_text[:300],
            "provider": provider_name,
            "severity": "high",
        }

    return None


async def scan_for_hallucinations(
    scan_job_id: str,
    brand_name: str,
    brand_id: str,
    known_facts: Dict[str, str],
) -> List[Dict]:
    """
    Fetches all scan_results where brand_mentioned=True for a given scan_job_id,
    runs hallucination checks on each, and saves findings to the hallucinations table.

    Returns:
        List of hallucination dicts found.
    """
    client = get_supabase_client()

    # 1. Fetch results where brand was mentioned
    try:
        query = (
            client.table("scan_results")
            .select("*")
            .eq("scan_job_id", str(scan_job_id))
            .eq("brand_mentioned", True)
            .execute()
        )
        mentioned_results = query.data or []
    except Exception as e:
        logger.error(f"Failed to fetch scan results for hallucination check: {e}")
        return []

    if not mentioned_results:
        logger.info(f"No brand mentions found for scan job {scan_job_id} — skipping hallucination check.")
        return []

    logger.info(
        f"Running hallucination check on {len(mentioned_results)} brand-mentioned responses "
        f"for scan job {scan_job_id}"
    )

    # 2. Run hallucination checks concurrently
    async def _check_one(result: Dict) -> Optional[Dict]:
        return await check_hallucination(
            brand_name=brand_name,
            response_text=result.get("response_text", ""),
            provider_name=result.get("provider", "unknown"),
            known_facts=known_facts,
        )

    tasks = [_check_one(r) for r in mentioned_results]
    raw_results = await asyncio.gather(*tasks)
    hallucinations = [h for h in raw_results if h is not None]

    # 3. Save to hallucinations table
    for h in hallucinations:
        try:
            client.table("hallucinations").insert({
                "scan_job_id": str(scan_job_id),
                "brand_id": str(brand_id),
                "claim": h["claim"],
                "source_response": h["source_response"],
                "provider": h["provider"],
                "severity": h["severity"],
                "status": "unresolved",
            }).execute()
        except Exception as db_err:
            logger.error(f"Failed to save hallucination to DB: {db_err}")

    logger.info(f"Hallucination scan complete: found {len(hallucinations)} issues for scan job {scan_job_id}")
    return hallucinations


# Required import at module level (placed here to avoid circular issues)
import asyncio

# DONE - hallucination.py

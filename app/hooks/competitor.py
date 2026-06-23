"""
Competitor Comparison Hook — Phase 2 Feature 1

Runs the same 20 prompts for the main brand AND each competitor,
computes independent scores, and returns a ranked comparison.
Reuses existing provider call functions, detect_mention, and scorer.
"""

import asyncio
import logging
from typing import List, Dict, Any

from app.scanner.providers.groq_provider import call_groq
from app.scanner.providers.gemini_provider import call_gemini
from app.scanner.providers.openai_provider import call_openai
from app.scanner.engine import detect_mention
from app.scanner.scorer import compute_score
from app.scanner.prompts import get_prompts_for_brand

logger = logging.getLogger(__name__)

# Provider dispatch map
PROVIDER_CALLERS = {
    "groq": call_groq,
    "gemini": call_gemini,
    "openai": call_openai,
}


async def _run_brand_check(
    brand_name: str,
    industry: str,
    providers: List[str],
) -> Dict[str, Any]:
    """
    Lightweight scan for a single brand — no DB tracking.
    Generates prompts, calls providers, detects mentions, computes score.
    Returns: {"name": str, "score": float, "mentions": int, "total": int, "results": list}
    """
    prompts = get_prompts_for_brand(brand_name, industry)

    async def _check_single(prompt_text: str, provider: str) -> Dict[str, Any]:
        caller = PROVIDER_CALLERS.get(provider)
        if not caller:
            logger.warning(f"Unknown provider '{provider}' — skipping.")
            return None

        try:
            response_text, cost_usd, latency_ms = await caller(prompt_text)
        except Exception as e:
            logger.error(f"Provider {provider} failed for brand '{brand_name}': {e}")
            return None

        # Skip error responses
        if response_text.startswith("Error:"):
            logger.warning(f"[{provider}] Error response for brand '{brand_name}': {response_text[:150]}")
            return None

        mentioned = detect_mention(response_text, brand_name)
        return {
            "provider": provider,
            "brand_mentioned": mentioned,
            "prompt_text": prompt_text,
            "response_snippet": response_text[:200],
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
        }

    # Build concurrent tasks for all prompt × provider combinations
    tasks = []
    for prompt_text in prompts:
        for provider in providers:
            tasks.append(_check_single(prompt_text, provider))

    raw_results = await asyncio.gather(*tasks)
    results = [r for r in raw_results if r is not None]

    # Compute score using the existing scorer (works with dicts)
    score, breakdown = compute_score(results)
    mentions = sum(1 for r in results if r["brand_mentioned"])

    return {
        "name": brand_name,
        "score": score,
        "mentions": mentions,
        "total": len(results),
        "breakdown": breakdown,
    }


async def run_competitor_scan(
    brand_name: str,
    competitor_names: List[str],
    industry: str,
    providers: List[str] = None,
) -> Dict[str, Any]:
    """
    Runs the same 20 prompts for the main brand AND each competitor (max 2).
    Computes independent scores and returns a ranked comparison.

    Args:
        brand_name: The main brand to analyze.
        competitor_names: Up to 2 competitor brand names.
        industry: Industry context for prompt generation.
        providers: LLM providers to use. Defaults to ["groq"].

    Returns:
        Comparison dict with main_brand, competitors, rank, and gap_to_leader.
    """
    if providers is None:
        providers = ["groq"]

    # Cap at 2 competitors for free tier
    competitors = competitor_names[:2]
    all_brands = [brand_name] + competitors

    logger.info(
        f"Starting competitor scan: main='{brand_name}', "
        f"competitors={competitors}, providers={providers}"
    )

    # Run all brand checks concurrently
    tasks = [_run_brand_check(name, industry, providers) for name in all_brands]
    results = await asyncio.gather(*tasks)

    # Sort by score descending to determine ranking
    sorted_results = sorted(results, key=lambda r: r["score"], reverse=True)
    leader_score = sorted_results[0]["score"] if sorted_results else 0.0

    # Find main brand's result and rank
    main_result = results[0]  # first result is always the main brand
    main_rank = next(
        (i + 1 for i, r in enumerate(sorted_results) if r["name"] == brand_name),
        len(sorted_results),
    )

    competitor_results = [
        {
            "name": r["name"],
            "score": r["score"],
            "mentions": r["mentions"],
        }
        for r in results[1:]  # skip first (main brand)
    ]

    gap_to_leader = round(leader_score - main_result["score"], 2)

    comparison = {
        "main_brand": {
            "name": main_result["name"],
            "score": main_result["score"],
            "mentions": main_result["mentions"],
        },
        "competitors": competitor_results,
        "rank": main_rank,
        "gap_to_leader": gap_to_leader,
    }

    logger.info(
        f"Competitor scan complete: {brand_name} ranked #{main_rank} "
        f"with score {main_result['score']}, gap_to_leader={gap_to_leader}"
    )

    return comparison

# DONE - competitor.py

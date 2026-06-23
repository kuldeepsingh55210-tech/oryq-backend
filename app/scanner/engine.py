import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID
from typing import List, Dict, Any, Optional

from app.database import get_supabase_client
from app.scanner.providers.groq_provider import call_groq
from app.scanner.providers.gemini_provider import call_gemini
from app.scanner.providers.openai_provider import call_openai
from app.scanner.scorer import compute_score
from app.models.scan import FullScanResult

logger = logging.getLogger(__name__)

# Lock to serialize database updates to completed_prompts to avoid race conditions
db_lock = asyncio.Lock()

import re

def detect_mention(response_text: str, brand_name: str, aliases: List[str] = None) -> bool:
    """
    Checks if the brand name or any aliases appear in the response.
    Uses multiple detection strategies:
      1. Case-insensitive exact substring match
      2. Individual word matching (for multi-word brands)
      3. Regex word-boundary match to catch possessives and punctuation variants
         e.g. "Zepto" matches "Zepto's", "ZEPTO", "zepto,", "zepto."
    """
    if not response_text or not brand_name:
        return False

    # Skip error responses from providers
    if response_text.startswith("Error:"):
        return False

    resp_lower = response_text.lower()
    brand_lower = brand_name.strip().lower()

    # Strategy 1: Direct case-insensitive substring match
    if brand_lower in resp_lower:
        return True

    # Strategy 2: Individual word matching (for multi-word brand names)
    brand_words = brand_lower.split()
    if len(brand_words) > 1:
        # If every individual word of the brand appears in the response
        if all(word in resp_lower for word in brand_words):
            return True

    # Strategy 3: Regex word-boundary match (catches "zepto's", "zepto,", etc.)
    try:
        pattern = re.compile(re.escape(brand_lower), re.IGNORECASE)
        if pattern.search(response_text):
            return True
    except re.error:
        pass

    # Strategy 4: Check aliases
    if aliases:
        for alias in aliases:
            if not alias or not alias.strip():
                continue
            alias_lower = alias.strip().lower()
            if alias_lower in resp_lower:
                return True
            try:
                alias_pattern = re.compile(re.escape(alias_lower), re.IGNORECASE)
                if alias_pattern.search(response_text):
                    return True
            except re.error:
                pass

    return False

def estimate_tokens(cost_usd: float, provider: str, prompt_len: int, resp_len: int) -> tuple[int, int]:
    """
    Estimates token input/output counts based on cost and character lengths.
    """
    if cost_usd <= 0:
        return 0, 0

    # Derive total tokens from billing rates
    if provider == "groq":
        total_tokens = int(cost_usd / 0.0000008)
    elif provider == "gemini":
        total_tokens = int(cost_usd / 0.000000075)
    elif provider == "openai":
        total_tokens = int(cost_usd / 0.00000015)
    else:
        total_tokens = (prompt_len + resp_len) // 4

    total_len = prompt_len + resp_len
    if total_len > 0:
        tokens_in = int(total_tokens * (prompt_len / total_len))
        tokens_out = max(0, total_tokens - tokens_in)
        return tokens_in, tokens_out
    return 0, 0

async def process_single_prompt(
    scan_job_id: UUID,
    brand_name: str,
    brand_aliases: List[str],
    prompt_dict: Dict[str, Any],
    provider: str
) -> Optional[FullScanResult]:
    """
    Processes a single prompt with a single provider, performs brand detection,
    logs results and costs to the database, and increments progress.
    Returns None if the provider call fails (e.g. quota exceeded) so the
    result is excluded from scoring.
    """
    prompt_text = prompt_dict["text"]
    
    # Call the appropriate provider API
    if provider == "groq":
        model_name = "llama-3.3-70b-versatile"
        response_text, cost_usd, latency_ms = await call_groq(prompt_text)
    elif provider == "gemini":
        model_name = "gemini-2.0-flash"
        response_text, cost_usd, latency_ms = await call_gemini(prompt_text)
    elif provider == "openai":
        model_name = "gpt-4o-mini"
        response_text, cost_usd, latency_ms = await call_openai(prompt_text)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    # Debug logging — show first 200 chars of each provider response
    logger.info(
        f"[{provider}] brand='{brand_name}' | prompt='{prompt_text[:80]}...' | "
        f"response_preview='{response_text[:200]}'"
    )

    # Skip failed provider responses entirely (e.g. quota exceeded, API errors)
    if response_text.startswith("Error:"):
        logger.warning(
            f"[{provider}] Provider returned error — skipping this result. "
            f"Error: {response_text[:200]}"
        )
        return None

    # Brand mention detection
    brand_mentioned = detect_mention(response_text, brand_name, brand_aliases)
    logger.info(
        f"[{provider}] brand_mentioned={brand_mentioned} for '{brand_name}' "
        f"(response_len={len(response_text)})"
    )

    # Snippet stored is first 500 chars (per storage cost rule)
    db_snippet = response_text[:500]
    
    # Snippet for frontend response model is first 200 chars
    response_snippet_200 = response_text[:200]

    client = get_supabase_client()

    # Log to llm_cost_log and scan_results, and update job progress inside DB lock
    try:
        tokens_in, tokens_out = estimate_tokens(cost_usd, provider, len(prompt_text), len(response_text))

        # Insert LLM Cost Log
        client.table("llm_cost_log").insert({
            "scan_job_id": str(scan_job_id),
            "provider": provider,
            "model": model_name,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost_usd
        }).execute()

        # Insert Scan Result
        client.table("scan_results").insert({
            "scan_job_id": str(scan_job_id),
            "prompt_text": prompt_text,
            "provider": provider,
            "brand_mentioned": brand_mentioned,
            "response_text": db_snippet,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms
        }).execute()

        # Safely increment completed_prompts
        async with db_lock:
            job_data = client.table("scan_jobs").select("completed_prompts").eq("id", str(scan_job_id)).execute()
            current_completed = job_data.data[0]["completed_prompts"] if job_data.data else 0
            client.table("scan_jobs").update({
                "completed_prompts": current_completed + 1
            }).eq("id", str(scan_job_id)).execute()

    except Exception as db_err:
        logger.error(f"Database logging failed for scan job {scan_job_id}, provider {provider}: {db_err}")

    return FullScanResult(
        prompt_text=prompt_text,
        provider=provider,
        brand_mentioned=brand_mentioned,
        response_snippet=response_snippet_200,
        cost_usd=cost_usd,
        latency_ms=latency_ms
    )

async def run_scan(
    scan_job_id: UUID,
    brand_name: str,
    brand_aliases: List[str],
    industry: str,
    prompts: List[Dict[str, Any]],
    providers: List[str]
) -> List[FullScanResult]:
    """
    Orchestrates the prompt evaluation across active providers concurrently.
    Updates scan job status throughout execution.
    Failed provider calls return None and are excluded from scoring.
    """
    client = get_supabase_client()
    
    # 1. Update status to 'running'
    try:
        client.table("scan_jobs").update({
            "status": "running",
            "total_prompts": len(prompts) * len(providers),
            "completed_prompts": 0
        }).eq("id", str(scan_job_id)).execute()
    except Exception as e:
        logger.error(f"Failed to update scan job {scan_job_id} to running status: {e}")

    # 2. Build task list for concurrent execution
    tasks = []
    for prompt_dict in prompts:
        for provider in providers:
            tasks.append(
                process_single_prompt(
                    scan_job_id=scan_job_id,
                    brand_name=brand_name,
                    brand_aliases=brand_aliases,
                    prompt_dict=prompt_dict,
                    provider=provider
                )
            )

    results: List[FullScanResult] = []
    try:
        # Run concurrently — return_exceptions=False so we get None for failed calls
        raw_results = await asyncio.gather(*tasks)
        
        # Filter out None results (failed provider calls like OpenAI quota exceeded)
        results = [r for r in raw_results if r is not None]
        failed_count = len(raw_results) - len(results)
        if failed_count > 0:
            logger.warning(
                f"Scan job {scan_job_id}: {failed_count} provider calls failed and were excluded from scoring."
            )
        
        # 3. Compute final scores (only from successful results)
        score, _ = compute_score(results)
        total_cost = sum(r.cost_usd for r in results)

        # 4. Update status to 'completed' with actual successful prompt count
        client.table("scan_jobs").update({
            "status": "completed",
            "visibility_score": score,
            "total_cost_usd": total_cost,
            "total_prompts": len(results),
            "completed_prompts": len(results),
            "completed_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", str(scan_job_id)).execute()

    except Exception as run_err:
        logger.error(f"Scan execution failed for job {scan_job_id}: {run_err}")
        # Update status to 'failed'
        try:
            client.table("scan_jobs").update({
                "status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", str(scan_job_id)).execute()
        except Exception as update_err:
            logger.error(f"Failed to set status to failed for job {scan_job_id}: {update_err}")
        raise run_err

    return results

# DONE - engine.py

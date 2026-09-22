import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from app.database import get_supabase_client

logger = logging.getLogger(__name__)

# Memory cache for benchmark results (6 hours TTL)
_BENCHMARK_CACHE: Dict[str, Any] = {
    "cached_at": None,
    "industries": {}
}

CACHE_TTL_HOURS = 6

def compute_percentiles(scores: List[float]) -> Dict[str, float]:
    """
    Computes avg, p25, p50, p75, p90 for a list of numerical scores.
    Handles small sample sizes gracefully.
    """
    if not scores:
        return {"avg": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "p90": 0.0}

    sorted_scores = sorted(scores)
    n = len(sorted_scores)

    def get_percentile(p: float) -> float:
        if n == 1:
            return round(float(sorted_scores[0]), 2)
        idx = (n - 1) * (p / 100.0)
        lower = math.floor(idx)
        upper = math.ceil(idx)
        if lower == upper:
            return round(float(sorted_scores[int(idx)]), 2)
        weight = idx - lower
        val = sorted_scores[lower] * (1 - weight) + sorted_scores[upper] * weight
        return round(float(val), 2)

    avg_val = round(float(sum(sorted_scores) / n), 2)
    p25_val = get_percentile(25)
    p50_val = get_percentile(50)
    p75_val = get_percentile(75)
    p90_val = get_percentile(90)

    return {
        "avg": avg_val,
        "p25": p25_val,
        "p50": p50_val,
        "p75": p75_val,
        "p90": p90_val
    }

async def recompute_benchmark_corpus() -> Dict[str, Any]:
    """
    Aggregates scan_jobs scores across industries anonymized (no brand names).
    Computes avg, p25, p50, p75, p90 and persists to `benchmark_data` table.
    Updates memory cache.
    """
    client = get_supabase_client()
    now_utc = datetime.now(timezone.utc)

    # 1. Fetch completed scan_jobs with brand details
    try:
        jobs_res = client.table("scan_jobs").select("brand_id, visibility_score, status").eq("status", "completed").execute()
        jobs = jobs_res.data or []

        brands_res = client.table("brands").select("id, industry").execute()
        brands = {b["id"]: b.get("industry") or "General" for b in (brands_res.data or [])}
    except Exception as e:
        logger.error(f"Error fetching data for benchmark aggregation: {e}")
        return {"status": "error", "error": str(e), "industries_updated": 0}

    # 2. Group scores per brand (taking latest or average score per brand) then by industry
    brand_scores: Dict[str, List[float]] = {}
    for job in jobs:
        brand_id = job.get("brand_id")
        score = job.get("visibility_score")
        if brand_id and score is not None:
            brand_scores.setdefault(brand_id, []).append(float(score))

    industry_scores: Dict[str, List[float]] = {}
    for brand_id, scores in brand_scores.items():
        ind = brands.get(brand_id, "General").strip() or "General"
        # Representative score per brand is average of completed scan jobs
        rep_score = sum(scores) / len(scores)
        industry_scores.setdefault(ind, []).append(rep_score)

    # Default fallback industry if empty dataset
    is_fallback = False
    if not industry_scores:
        industry_scores["General"] = [50.0]
        is_fallback = True

    updated_count = 0
    cache_data = {}

    for industry, scores in industry_scores.items():
        stats = compute_percentiles(scores)
        brand_count = 0 if is_fallback and industry == "General" else len(scores)
        computed_at_str = now_utc.isoformat()

        record = {
            "industry": industry,
            "avg_visibility_score": stats["avg"],
            "p25": stats["p25"],
            "p50": stats["p50"],
            "p75": stats["p75"],
            "p90": stats["p90"],
            "brand_count": brand_count,
            "computed_at": computed_at_str
        }

        try:
            # Check if record for industry already exists
            existing = client.table("benchmark_data").select("id").eq("industry", industry).execute()
            if existing.data and len(existing.data) > 0:
                client.table("benchmark_data").update(record).eq("industry", industry).execute()
            else:
                client.table("benchmark_data").insert(record).execute()
            updated_count += 1
        except Exception as e:
            logger.error(f"Failed to write benchmark_data for industry {industry}: {e}")

        cache_data[industry] = record

    # Update in-memory cache
    _BENCHMARK_CACHE["cached_at"] = now_utc
    _BENCHMARK_CACHE["industries"] = cache_data

    logger.info(f"Recomputed benchmark corpus for {updated_count} industries.")
    return {
        "status": "recomputed",
        "industries_updated": updated_count,
        "computed_at": now_utc.isoformat()
    }

async def get_industry_benchmark(industry: str) -> Dict[str, Any]:
    """
    Retrieves benchmark stats for a given industry from 6-hr memory cache or DB.
    """
    now_utc = datetime.now(timezone.utc)
    industry_key = industry.strip() if industry else "General"

    # Check memory cache validity
    cached_at = _BENCHMARK_CACHE.get("cached_at")
    if cached_at and (now_utc - cached_at) < timedelta(hours=CACHE_TTL_HOURS):
        if industry_key in _BENCHMARK_CACHE["industries"]:
            return _BENCHMARK_CACHE["industries"][industry_key]
        if "General" in _BENCHMARK_CACHE["industries"]:
            return _BENCHMARK_CACHE["industries"]["General"]

    # Cache miss or expired: fetch from DB
    client = get_supabase_client()
    try:
        res = client.table("benchmark_data").select("*").eq("industry", industry_key).execute()
        if res.data and len(res.data) > 0:
            data = res.data[0]
            _BENCHMARK_CACHE["industries"][industry_key] = data
            return data
        
        # Fallback to General industry benchmark
        gen_res = client.table("benchmark_data").select("*").eq("industry", "General").execute()
        if gen_res.data and len(gen_res.data) > 0:
            return gen_res.data[0]
    except Exception as e:
        logger.error(f"Database query error in get_industry_benchmark: {e}")

    # Fallback standard response if DB empty
    return {
        "industry": industry_key,
        "avg_visibility_score": 60.0,
        "p25": 45.0,
        "p50": 60.0,
        "p75": 75.0,
        "p90": 85.0,
        "brand_count": 0,
        "computed_at": now_utc.isoformat()
    }

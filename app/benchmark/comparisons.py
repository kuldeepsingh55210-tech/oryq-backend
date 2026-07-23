import logging
from typing import Dict, Any, List
from app.database import get_supabase_client
from app.benchmark.corpus import get_industry_benchmark
from app.benchmark.percentile import compute_brand_percentile

logger = logging.getLogger(__name__)

async def compare_brand_with_industry(brand_id: str) -> Dict[str, Any]:
    """
    Performs benchmark comparison, gap analysis, and trend calculation for a given brand.
    """
    client = get_supabase_client()

    # 1. Fetch brand info
    brand_res = client.table("brands").select("id, name, industry").eq("id", brand_id).execute()
    if not brand_res.data:
        raise ValueError("Brand not found")
    brand = brand_res.data[0]
    industry = brand.get("industry") or "General"

    # 2. Fetch completed scan_jobs for the brand ordered by completed_at desc
    jobs_res = client.table("scan_jobs").select("id, visibility_score, completed_at, created_at").eq("brand_id", brand_id).eq("status", "completed").order("created_at", desc=True).limit(10).execute()
    jobs = jobs_res.data or []

    current_score = 0.0
    previous_score: float | None = None
    if jobs:
        current_score = float(jobs[0].get("visibility_score") or 0.0)
        if len(jobs) > 1:
            previous_score = float(jobs[1].get("visibility_score") or 0.0)

    # 3. Get percentile & industry benchmark
    perc_info = await compute_brand_percentile(current_score, industry)
    bench = perc_info["industry_stats"]
    industry_avg = float(bench.get("avg_visibility_score", 60.0))

    # 4. Peer comparison message
    diff = round(current_score - industry_avg, 1)
    if diff > 0:
        peer_comparison = f"{diff} points above industry average"
    elif diff < 0:
        peer_comparison = f"{abs(diff)} points below industry average"
    else:
        peer_comparison = "Equal to industry average"

    # 5. Gap analysis per component/milestone
    gap_to_p50 = round(float(bench.get("p50", 60.0)) - current_score, 1)
    gap_to_p75 = round(float(bench.get("p75", 75.0)) - current_score, 1)
    gap_to_p90 = round(float(bench.get("p90", 85.0)) - current_score, 1)

    component_gaps = {
        "gap_to_median": max(0.0, gap_to_p50),
        "gap_to_top_25": max(0.0, gap_to_p75),
        "gap_to_top_10": max(0.0, gap_to_p90),
        "difference_from_avg": diff
    }

    # 6. Trend calculation
    trend_summary = "Score is stable with industry baseline."
    if previous_score is not None:
        score_change = round(current_score - previous_score, 1)
        if score_change > 0:
            trend_summary = f"Your score improved faster than industry avg (+{score_change} pts in latest scan)."
        elif score_change < 0:
            trend_summary = f"Your score decreased by {abs(score_change)} pts compared to previous scan."

    return {
        "brand_id": brand_id,
        "brand_name": brand.get("name"),
        "brand_score": current_score,
        "industry": industry,
        "percentile": perc_info["percentile"],
        "top_percentage": perc_info["top_percentage"],
        "message": perc_info["message"],
        "threshold_translation": perc_info["threshold_translation"],
        "industry_avg": industry_avg,
        "industry_p75": float(bench.get("p75", 75.0)),
        "industry_p90": float(bench.get("p90", 85.0)),
        "peer_comparison": peer_comparison,
        "gap_analysis": component_gaps,
        "trend_summary": trend_summary
    }

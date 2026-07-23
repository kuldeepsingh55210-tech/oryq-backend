import logging
from typing import Dict, Any
from app.benchmark.corpus import get_industry_benchmark

logger = logging.getLogger(__name__)

def calculate_percentile_rank_from_stats(score: float, stats: Dict[str, Any]) -> int:
    """
    Interpolates brand score against industry percentile markers (p25, p50, p75, p90).
    Returns an integer rank between 0 and 100.
    """
    p25 = float(stats.get("p25", 45.0))
    p50 = float(stats.get("p50", 60.0))
    p75 = float(stats.get("p75", 75.0))
    p90 = float(stats.get("p90", 85.0))

    score = max(0.0, min(100.0, float(score)))

    if score <= p25:
        if p25 == 0:
            rank = 25
        else:
            rank = (score / p25) * 25
    elif score <= p50:
        rank = 25 + ((score - p25) / max(1.0, (p50 - p25))) * 25
    elif score <= p75:
        rank = 50 + ((score - p50) / max(1.0, (p75 - p50))) * 25
    elif score <= p90:
        rank = 75 + ((score - p75) / max(1.0, (p90 - p75))) * 15
    else:
        rank = 90 + ((score - p90) / max(1.0, (100.0 - p90))) * 10

    return max(0, min(100, int(round(rank))))

async def compute_brand_percentile(brand_score: float, industry: str) -> Dict[str, Any]:
    """
    Computes percentile rank, top X% message, and threshold translations.
    """
    benchmark = await get_industry_benchmark(industry)
    percentile_rank = calculate_percentile_rank_from_stats(brand_score, benchmark)

    top_pct = max(1, 100 - percentile_rank)
    industry_name = benchmark.get("industry", industry or "General")

    message = f"You are in top {top_pct}% of {industry_name} companies"
    p75_val = benchmark.get("p75", 75.0)
    translation = f"Top 25% companies score {int(p75_val) if isinstance(p75_val, (int, float)) and float(p75_val).is_integer() else p75_val}+"

    return {
        "percentile": percentile_rank,
        "top_percentage": top_pct,
        "message": message,
        "threshold_translation": translation,
        "industry_stats": benchmark
    }

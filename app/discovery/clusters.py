import logging
from typing import List, Dict, Any
from app.database import get_supabase_client

logger = logging.getLogger(__name__)

DISCOVERY_KEYWORDS = ["what is", "tell me about", "who is", "overview", "definition", "explain"]
COMPARISON_KEYWORDS = ["vs", "versus", "alternative", "compared to", "difference", "instead of"]
EVALUATION_KEYWORDS = ["is good", "review", "pricing", "cost", "pros and cons", "worth it", "rating"]
RECOMMENDATION_KEYWORDS = ["best", "recommend", "top", "leading", "choice for", "suggestion"]

def classify_prompt_cluster(prompt_text: str, brand_name: str = "") -> str:
    """
    Classifies a search query into one of the 4 intent clusters:
    - Discovery
    - Comparison
    - Evaluation
    - Recommendation
    """
    p_lower = prompt_text.lower()

    for kw in COMPARISON_KEYWORDS:
        if kw in p_lower:
            return "Comparison"

    for kw in EVALUATION_KEYWORDS:
        if kw in p_lower:
            return "Evaluation"

    for kw in RECOMMENDATION_KEYWORDS:
        if kw in p_lower:
            return "Recommendation"

    for kw in DISCOVERY_KEYWORDS:
        if kw in p_lower:
            return "Discovery"

    # Fallback default cluster based on brand mention
    if brand_name and brand_name.lower() in p_lower:
        return "Discovery"
    return "Recommendation"

async def compute_cluster_overview(brand_id: str) -> List[Dict[str, Any]]:
    """
    Calculates prompt count, avg visibility %, gap score, and fill_gap_cta per cluster for brand_id.
    """
    client = get_supabase_client()
    clusters = ["Discovery", "Comparison", "Evaluation", "Recommendation"]

    try:
        # Fetch suggestions for brand
        s_query = client.table("prompt_suggestions").select("*").eq("brand_id", brand_id).execute()
        suggestions = s_query.data or []

        cluster_data: Dict[str, Dict[str, Any]] = {
            c: {"count": 0, "total_lift": 0.0, "total_comp": 0.0} for c in clusters
        }

        for s in suggestions:
            c_name = s.get("cluster", "Discovery")
            if c_name not in cluster_data:
                c_name = "Discovery"
            cluster_data[c_name]["count"] += 1
            cluster_data[c_name]["total_lift"] += float(s.get("estimated_lift_pct") or 15.0)
            cluster_data[c_name]["total_comp"] += float(s.get("competitor_visibility") or 50.0)

        total_prompts = sum(data["count"] for data in cluster_data.values())

        overview = []
        for c_name in clusters:
            cnt = cluster_data[c_name]["count"]
            coverage_pct = round((cnt / max(total_prompts, 1)) * 100, 2)
            avg_vis = round((cluster_data[c_name]["total_comp"] / max(cnt, 1)), 2)
            gap_score = round(max(0.0, 100.0 - coverage_pct), 2)

            fill_gap_cta = f"Generate more {c_name} prompts" if coverage_pct < 20.0 else f"Optimize {c_name} prompt coverage"

            overview.append({
                "cluster_name": c_name,
                "prompt_count": cnt,
                "avg_visibility_pct": avg_vis,
                "gap_score": gap_score,
                "coverage_pct": coverage_pct,
                "fill_gap_cta": fill_gap_cta
            })

        return overview
    except Exception as e:
        logger.error(f"Error computing cluster overview for brand_id {brand_id}: {e}")
        return []

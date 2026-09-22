import logging
from typing import List, Dict, Any
from app.database import get_supabase_client

logger = logging.getLogger(__name__)

TIER_PRIORITY = {
    "High Impact (Preliminary Estimate)": 3,
    "Medium Impact (Preliminary Estimate)": 2,
    "Preliminary Estimate": 1
}

async def get_opportunity_rankings(brand_id: str) -> List[Dict[str, Any]]:
    """
    Scores and ranks prompt suggestions for brand_id based on impact_tier
    and cluster-derived difficulty.
    Ranks opportunities DESC by estimated_lift_label priority.
    """
    client = get_supabase_client()
    try:
        s_query = client.table("prompt_suggestions").select("*").eq("brand_id", brand_id).execute()
        suggestions = s_query.data or []

        opportunities = []
        for s in suggestions:
            cluster = s.get("cluster", "Discovery")
            cluster_lower = (cluster or "").lower()

            # Determine impact_tier label
            impact_tier = s.get("impact_tier")
            if not impact_tier:
                if cluster_lower in ("discovery", "recommendation"):
                    impact_tier = "High Impact (Preliminary Estimate)"
                elif cluster_lower in ("comparison", "evaluation"):
                    impact_tier = "Medium Impact (Preliminary Estimate)"
                else:
                    impact_tier = "Preliminary Estimate"

            # Determine difficulty based on cluster type
            if cluster_lower == "comparison":
                difficulty = "high"
            elif cluster_lower == "evaluation":
                difficulty = "medium"
            else:
                difficulty = "low"

            opportunities.append({
                "id": s.get("id"),
                "prompt_text": s.get("prompt_text"),
                "cluster": cluster,
                "estimated_lift_label": impact_tier,
                "competitor_visibility": None,
                "difficulty": difficulty,
                "status": s.get("status", "pending"),
                "created_at": s.get("created_at")
            })

        # Rank by estimated_lift_label priority DESC
        return sorted(opportunities, key=lambda x: TIER_PRIORITY.get(x["estimated_lift_label"], 0), reverse=True)
    except Exception as e:
        logger.error(f"Error fetching opportunity rankings for brand_id {brand_id}: {e}")
        return []

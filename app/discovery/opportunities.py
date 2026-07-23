import logging
from typing import List, Dict, Any
from app.database import get_supabase_client

logger = logging.getLogger(__name__)

async def get_opportunity_rankings(brand_id: str) -> List[Dict[str, Any]]:
    """
    Scores and ranks prompt suggestions for brand_id based on estimated_lift_pct,
    competitor_visibility, and difficulty.
    Ranks opportunities DESC by estimated_lift_pct.
    """
    client = get_supabase_client()
    try:
        s_query = client.table("prompt_suggestions").select("*").eq("brand_id", brand_id).execute()
        suggestions = s_query.data or []

        opportunities = []
        for s in suggestions:
            lift = float(s.get("estimated_lift_pct") or 15.0)
            comp_vis = float(s.get("competitor_visibility") or 50.0)
            cluster = s.get("cluster", "Discovery")

            # Determine difficulty based on competitor visibility and cluster type
            if comp_vis > 70.0 or cluster == "Comparison":
                difficulty = "high"
            elif comp_vis > 45.0 or cluster == "Evaluation":
                difficulty = "medium"
            else:
                difficulty = "low"

            opportunities.append({
                "id": s.get("id"),
                "prompt_text": s.get("prompt_text"),
                "cluster": cluster,
                "estimated_lift_pct": round(lift, 2),
                "competitor_visibility": round(comp_vis, 2),
                "difficulty": difficulty,
                "status": s.get("status", "pending"),
                "created_at": s.get("created_at")
            })

        # Rank by estimated_lift_pct DESC
        return sorted(opportunities, key=lambda x: x["estimated_lift_pct"], reverse=True)
    except Exception as e:
        logger.error(f"Error fetching opportunity rankings for brand_id {brand_id}: {e}")
        return []

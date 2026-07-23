import logging
from typing import List, Dict, Any
from app.database import get_supabase_client

logger = logging.getLogger(__name__)

IMPACT_WEIGHTS = {
    "product": 90.0,
    "differentiator": 85.0,
    "technology": 75.0,
    "person": 65.0,
    "award": 55.0,
    "location": 45.0
}

def generate_fix_recommendation(entity_name: str, entity_type: str) -> str:
    """
    Generates actionable SEO/LLMO fix recommendation based on entity type.
    """
    etype = entity_type.lower()
    if etype == "product":
        return f"Add product '{entity_name}' to your FAQ and main Product documentation page with detailed feature bullet points."
    elif etype == "person":
        return f"Create or update your Team/About page mentioning '{entity_name}' with bio, role, and social schema links."
    elif etype == "differentiator":
        return f"Add schema markup and dedicated landing page sections highlighting '{entity_name}' as a core value proposition."
    elif etype == "technology":
        return f"Publish an Integration & Tech Stack page documenting compatibility with '{entity_name}'."
    elif etype == "award":
        return f"Feature certification and award badge for '{entity_name}' on your homepage footer and press release section."
    elif etype == "location":
        return f"Add Organization schema location markup and contact page address for '{entity_name}'."
    else:
        return f"Include clear textual mentions of '{entity_name}' across high-authority indexed site pages."

async def detect_entity_gaps(brand_id: str) -> List[Dict[str, Any]]:
    """
    Identifies missing entities (catalog entities unmentioned or low coverage in AI responses).
    Ranks gaps by impact score (highest impact first).
    """
    client = get_supabase_client()
    try:
        query = client.table("brand_entities").select("*").eq("brand_id", brand_id).execute()
        entities = query.data or []

        gaps = []
        for ent in entities:
            is_known = bool(ent.get("is_known_to_ai", False))
            coverage = float(ent.get("coverage_pct") or 0.0)

            if not is_known or coverage < 25.0:
                name = ent.get("entity_name", "Unknown Entity")
                etype = ent.get("entity_type", "product")
                
                base_impact = IMPACT_WEIGHTS.get(etype, 50.0)
                # Lower coverage yields higher gap impact
                gap_deficit = (100.0 - coverage) / 100.0
                impact_score = round(base_impact * gap_deficit, 1)

                effort = "low" if etype in ["product", "differentiator"] else "medium"

                gaps.append({
                    "entity_name": name,
                    "entity_type": etype,
                    "impact_score": impact_score,
                    "coverage_pct": coverage,
                    "recommended_fix": generate_fix_recommendation(name, etype),
                    "effort": effort
                })

        # Rank gaps by impact_score DESC
        return sorted(gaps, key=lambda x: x["impact_score"], reverse=True)
    except Exception as e:
        logger.error(f"Error detecting entity gaps for brand_id {brand_id}: {e}")
        return []

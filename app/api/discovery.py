import logging
from uuid import UUID
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status

from app.database import get_supabase_client
from app.discovery.generator import generate_prompt_variations
from app.discovery.clusters import compute_cluster_overview
from app.discovery.opportunities import get_opportunity_rankings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/discovery", tags=["Prompt Discovery Engine"])

@router.post("/{brand_id}/generate")
async def trigger_prompt_generation(brand_id: UUID):
    """
    Triggers Groq AI prompt generation for brand_id.
    Generates 20 prompt variations across 4 intent clusters, deduplicates against existing records,
    and inserts new suggestions into prompt_suggestions table.
    """
    brand_id_str = str(brand_id)
    client = get_supabase_client()

    # Fetch brand
    brand_query = client.table("brands").select("*").eq("id", brand_id_str).execute()
    if not brand_query.data:
        raise HTTPException(status_code=404, detail="Brand not found")
    brand = brand_query.data[0]

    brand_name = brand.get("name", "Brand")
    industry = brand.get("industry") or "software"

    try:
        res = await generate_prompt_variations(brand_id_str, brand_name, industry)
        return res
    except Exception as e:
        logger.error(f"Error executing prompt generation for brand {brand_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")

@router.get("/{brand_id}/suggestions")
async def get_prompt_suggestions(
    brand_id: UUID,
    cluster: Optional[str] = Query(None, description="Filter by cluster: Discovery | Comparison | Evaluation | Recommendation"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: pending | approved | rejected | added"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    Returns list of generated prompt suggestions for brand_id, filterable by cluster and status.
    """
    brand_id_str = str(brand_id)
    client = get_supabase_client()

    try:
        q = client.table("prompt_suggestions").select("*").eq("brand_id", brand_id_str)
        if cluster:
            q = q.eq("cluster", cluster)
        if status_filter:
            q = q.eq("status", status_filter)

        res = q.order("created_at", desc=True).execute()
        items = res.data or []

        paginated = items[offset : offset + limit]
        return {
            "total": len(items),
            "limit": limit,
            "offset": offset,
            "suggestions": paginated
        }
    except Exception as e:
        logger.error(f"Error fetching prompt suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")

@router.get("/{brand_id}/clusters")
async def get_prompt_clusters_overview(brand_id: UUID):
    """
    Returns prompt cluster overview for brand_id: prompt count, average visibility %,
    gap score, and fill-gap call to action per cluster.
    """
    brand_id_str = str(brand_id)
    client = get_supabase_client()

    # Ensure brand exists
    brand_query = client.table("brands").select("id").eq("id", brand_id_str).execute()
    if not brand_query.data:
        raise HTTPException(status_code=404, detail="Brand not found")

    clusters_summary = await compute_cluster_overview(brand_id_str)
    return clusters_summary

@router.get("/{brand_id}/opportunities")
async def get_prompt_opportunities(brand_id: UUID):
    """
    Returns ranked search query opportunities sorted DESC by estimated_lift_pct
    with competitor visibility and difficulty levels (low|medium|high).
    """
    brand_id_str = str(brand_id)
    client = get_supabase_client()

    # Ensure brand exists
    brand_query = client.table("brands").select("id").eq("id", brand_id_str).execute()
    if not brand_query.data:
        raise HTTPException(status_code=404, detail="Brand not found")

    opportunities = await get_opportunity_rankings(brand_id_str)
    return opportunities

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends, status

from app.database import get_supabase_client
from app.auth.middleware import get_current_user
from app.revenue.intelligence import get_revenue_settings, update_revenue_settings, calculate_revenue_intelligence
from app.revenue.tracker import get_revenue_history, track_scan_revenue_metrics
from app.revenue.correlation import compute_revenue_correlation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/revenue", tags=["Revenue Intelligence"])

class RevenueSettingsPayload(BaseModel):
    avg_deal_value: Optional[float] = None
    monthly_website_traffic: Optional[int] = None
    ai_traffic_percentage: Optional[float] = None
    conversion_rate: Optional[float] = None
    currency: Optional[str] = None

class RevenueIntelligenceResponse(BaseModel):
    estimated_ai_revenue: float
    missed_revenue: float
    competitor_deals_lost: int
    revenue_per_visibility_point: float
    insight_text: str
    current_visibility_score: float
    currency: str

@router.get("/{brand_id}/intelligence", response_model=RevenueIntelligenceResponse)
async def get_brand_revenue_intelligence(brand_id: str):
    """
    Returns revenue intelligence breakdown (estimated AI revenue, missed revenue, competitor deals lost, insight).
    """
    client = get_supabase_client()
    try:
        # Fetch latest completed scan score for brand
        job_res = client.table("scan_jobs").select("id, visibility_score").eq("brand_id", brand_id).eq("status", "completed").order("created_at", desc=True).limit(1).execute()
        score = 0.0
        comp_count = 0
        if job_res.data:
            score = float(job_res.data[0].get("visibility_score") or 0.0)
            scan_id = job_res.data[0]["id"]
            res_res = client.table("scan_results").select("id").eq("scan_job_id", scan_id).eq("brand_mentioned", False).execute()
            comp_count = len(res_res.data or [])

        settings = await get_revenue_settings(brand_id)
        intel = calculate_revenue_intelligence(score, settings, comp_count)

        return RevenueIntelligenceResponse(
            estimated_ai_revenue=intel["estimated_ai_revenue"],
            missed_revenue=intel["missed_revenue"],
            competitor_deals_lost=intel["competitor_deals_lost"],
            revenue_per_visibility_point=intel["revenue_per_visibility_point"],
            insight_text=intel["insight_text"],
            current_visibility_score=intel["current_visibility_score"],
            currency=intel["currency"]
        )
    except Exception as e:
        logger.error(f"Error fetching revenue intelligence for brand {brand_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch revenue intelligence")

@router.get("/{brand_id}/history")
async def get_brand_revenue_history(brand_id: str):
    """
    Returns historical revenue metrics for the last 12 months/scans.
    """
    try:
        history = await get_revenue_history(brand_id, limit_months=12)
        return history
    except Exception as e:
        logger.error(f"Error fetching revenue history for brand {brand_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch revenue history")

@router.get("/{brand_id}/settings")
async def get_brand_revenue_settings_endpoint(brand_id: str):
    """
    Returns current revenue settings configured for a brand.
    """
    try:
        settings = await get_revenue_settings(brand_id)
        return settings
    except Exception as e:
        logger.error(f"Error fetching revenue settings for brand {brand_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch revenue settings")

@router.patch("/{brand_id}/settings")
async def update_brand_revenue_settings_endpoint(
    brand_id: str,
    payload: RevenueSettingsPayload,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Updates revenue settings (deal value, traffic, conversion rate, currency) and returns updated settings with recalculated estimates.
    """
    try:
        updated_settings = await update_revenue_settings(brand_id, payload.model_dump(exclude_unset=True))
        
        # Calculate updated intelligence with new settings
        client = get_supabase_client()
        job_res = client.table("scan_jobs").select("visibility_score").eq("brand_id", brand_id).eq("status", "completed").order("created_at", desc=True).limit(1).execute()
        score = float(job_res.data[0].get("visibility_score") or 0.0) if job_res.data else 0.0

        recalculated = calculate_revenue_intelligence(score, updated_settings)
        return {
            "settings": updated_settings,
            "recalculated_estimates": recalculated
        }
    except Exception as e:
        logger.error(f"Error updating revenue settings for brand {brand_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update revenue settings")

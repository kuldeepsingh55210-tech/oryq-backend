import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from app.database import get_supabase_client
from app.revenue.intelligence import get_revenue_settings, calculate_revenue_intelligence, format_currency_amount

logger = logging.getLogger(__name__)

async def track_scan_revenue_metrics(scan_job_id: str, brand_id: str) -> Dict[str, Any]:
    """
    Computes and records revenue metrics for a completed scan job into `revenue_metrics` table.
    """
    client = get_supabase_client()

    # 1. Fetch scan job visibility score
    job_res = client.table("scan_jobs").select("visibility_score").eq("id", scan_job_id).execute()
    if not job_res.data:
        raise ValueError(f"Scan job {scan_job_id} not found")
    
    score = float(job_res.data[0].get("visibility_score") or 0.0)

    # 2. Fetch revenue settings for brand
    settings = await get_revenue_settings(brand_id)

    # 3. Count competitor mentions in scan_results
    comp_mentions_count = 0
    try:
        res_res = client.table("scan_results").select("id").eq("scan_job_id", scan_job_id).eq("brand_mentioned", False).execute()
        comp_mentions_count = len(res_res.data or [])
    except Exception:
        pass

    # 4. Calculate intelligence values
    intel = calculate_revenue_intelligence(score, settings, comp_mentions_count)

    record = {
        "brand_id": brand_id,
        "scan_job_id": scan_job_id,
        "estimated_ai_revenue": intel["estimated_ai_revenue"],
        "missed_revenue": intel["missed_revenue"],
        "competitor_deals_lost": intel["competitor_deals_lost"],
        "visibility_score": score,
        "revenue_per_visibility_point": intel["revenue_per_visibility_point"],
        "avg_deal_value": float(settings.get("avg_deal_value", 50000.0)),
        "monthly_ai_leads": intel["monthly_ai_leads"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        ins_res = client.table("revenue_metrics").insert(record).execute()
        if ins_res.data:
            return ins_res.data[0]
        return record
    except Exception as e:
        logger.error(f"Error persisting revenue metrics for scan {scan_job_id}: {e}")
        return record

async def get_revenue_history(brand_id: str, limit_months: int = 12) -> List[Dict[str, Any]]:
    """
    Returns historical revenue metrics records for a brand for chart trends.
    Formatted as: [{ month, estimated_ai_revenue, missed_revenue, visibility_score, created_at }]
    """
    client = get_supabase_client()
    try:
        res = client.table("revenue_metrics").select("*").eq("brand_id", brand_id).order("created_at", desc=True).limit(limit_months).execute()
        raw_list = res.data or []

        formatted = []
        for r in reversed(raw_list):
            dt_str = r.get("created_at", "")
            month_label = "Current"
            if dt_str:
                try:
                    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                    month_label = dt.strftime("%b %Y")
                except Exception:
                    pass

            formatted.append({
                "month": month_label,
                "estimated_ai_revenue": float(r.get("estimated_ai_revenue") or 0.0),
                "missed_revenue": float(r.get("missed_revenue") or 0.0),
                "visibility_score": float(r.get("visibility_score") or 0.0),
                "created_at": dt_str
            })

        return formatted
    except Exception as e:
        logger.error(f"Error fetching revenue history for brand {brand_id}: {e}")
        return []

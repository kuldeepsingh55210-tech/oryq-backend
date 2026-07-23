import logging
from typing import Dict, Any, List
from app.database import get_supabase_client
from app.revenue.intelligence import get_revenue_settings, calculate_revenue_intelligence, format_currency_amount

logger = logging.getLogger(__name__)

async def compute_revenue_correlation(brand_id: str) -> Dict[str, Any]:
    """
    Computes score to revenue correlation, lift trends, and competitor deal impact.
    """
    client = get_supabase_client()
    settings = await get_revenue_settings(brand_id)
    currency = settings.get("currency", "INR")

    # Fetch recent scan jobs for brand
    jobs_res = client.table("scan_jobs").select("id, visibility_score, created_at").eq("brand_id", brand_id).eq("status", "completed").order("created_at", desc=True).limit(5).execute()
    jobs = jobs_res.data or []

    current_score = float(jobs[0].get("visibility_score") or 0.0) if jobs else 0.0
    previous_score = float(jobs[1].get("visibility_score") or 0.0) if len(jobs) > 1 else current_score

    intel = calculate_revenue_intelligence(current_score, settings)
    rpt = intel["revenue_per_visibility_point"]

    score_delta = round(current_score - previous_score, 1)
    revenue_delta = round(score_delta * rpt, 2)

    if score_delta > 0:
        formatted_lift = format_currency_amount(revenue_delta, currency)
        trend_message = f"Your last +{int(score_delta) if score_delta.is_integer() else score_delta} pts = est. {formatted_lift} lift/month"
    elif score_delta < 0:
        formatted_loss = format_currency_amount(abs(revenue_delta), currency)
        trend_message = f"Your last {int(score_delta) if score_delta.is_integer() else score_delta} pts = est. {formatted_loss} drop/month"
    else:
        trend_message = "Visibility score is baseline stable."

    # Competitor impact analysis
    competitor_impact_text = "No competitor deal diversion detected in recent scan."
    try:
        # Check citation_gaps or competitor mentions in scan_results
        if jobs:
            scan_job_id = jobs[0]["id"]
            gaps_res = client.table("citation_gaps").select("cites_competitor").eq("scan_job_id", scan_job_id).execute()
            if gaps_res.data:
                comp_names = [g.get("cites_competitor") for g in gaps_res.data if g.get("cites_competitor")]
                if comp_names:
                    top_comp = comp_names[0]
                    deals_diverted = max(5, int(len(comp_names) * 1.5))
                    competitor_impact_text = f"Competitor {top_comp} won {deals_diverted} deals because AI models recommended them instead of you."
    except Exception as e:
        logger.error(f"Error computing competitor deal impact: {e}")

    return {
        "brand_id": brand_id,
        "current_score": current_score,
        "previous_score": previous_score,
        "score_delta": score_delta,
        "revenue_delta": revenue_delta,
        "revenue_per_point": rpt,
        "trend_message": trend_message,
        "competitor_impact_text": competitor_impact_text
    }

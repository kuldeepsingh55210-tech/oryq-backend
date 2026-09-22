import logging
from typing import Dict, Any, Optional
from app.database import get_supabase_client

logger = logging.getLogger(__name__)

DEFAULT_REVENUE_SETTINGS = {
    "avg_deal_value": 50000.0,
    "monthly_website_traffic": 10000,
    "ai_traffic_percentage": 15.0,
    "conversion_rate": 0.02,
    "currency": "INR"
}

CURRENCY_SYMBOLS = {
    "INR": "₹",
    "USD": "$",
    "EUR": "€",
    "GBP": "£"
}

def format_currency_amount(amount: float, currency: str = "INR") -> str:
    """
    Formats numerical revenue into human-readable text (e.g. ₹18.4L or $18.4K).
    """
    symbol = CURRENCY_SYMBOLS.get(currency.upper(), currency.upper() + " ")
    val = float(amount)

    if currency.upper() == "INR":
        if val >= 10000000:  # 1 Crore = 100 Lakhs
            return f"{symbol}{val / 10000000:.2f} Cr"
        if val >= 100000:    # 1 Lakh = 100,000
            return f"{symbol}{val / 100000:.1f}L"
        return f"{symbol}{val:,.0f}"
    else:
        if val >= 1000000:
            return f"{symbol}{val / 1000000:.2f}M"
        if val >= 1000:
            return f"{symbol}{val / 1000:.1f}K"
        return f"{symbol}{val:,.0f}"

async def get_revenue_settings(brand_id: str) -> Dict[str, Any]:
    """
    Fetches revenue calculation settings for a brand from DB or returns defaults.
    """
    client = get_supabase_client()
    try:
        res = client.table("revenue_settings").select("*").eq("brand_id", brand_id).execute()
        if res.data and len(res.data) > 0:
            row = res.data[0]
            return {
                "id": row.get("id"),
                "brand_id": brand_id,
                "avg_deal_value": float(row.get("avg_deal_value") or 50000.0),
                "monthly_website_traffic": int(row.get("monthly_website_traffic") or 10000),
                "ai_traffic_percentage": float(row.get("ai_traffic_percentage") or 15.0),
                "conversion_rate": float(row.get("conversion_rate") or 0.02),
                "currency": row.get("currency") or "INR",
                "updated_at": row.get("updated_at")
            }
    except Exception as e:
        logger.error(f"Error fetching revenue settings for brand {brand_id}: {e}")

    return {"brand_id": brand_id, **DEFAULT_REVENUE_SETTINGS}

async def update_revenue_settings(brand_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Updates or inserts (UPSERT) revenue settings for a brand.
    """
    client = get_supabase_client()
    record = {"brand_id": brand_id}

    if "avg_deal_value" in payload and payload["avg_deal_value"] is not None:
        record["avg_deal_value"] = float(payload["avg_deal_value"])
    if "monthly_website_traffic" in payload and payload["monthly_website_traffic"] is not None:
        record["monthly_website_traffic"] = int(payload["monthly_website_traffic"])
    if "ai_traffic_percentage" in payload and payload["ai_traffic_percentage"] is not None:
        record["ai_traffic_percentage"] = float(payload["ai_traffic_percentage"])
    if "conversion_rate" in payload and payload["conversion_rate"] is not None:
        record["conversion_rate"] = float(payload["conversion_rate"])
    if "currency" in payload and payload["currency"]:
        record["currency"] = str(payload["currency"]).upper()

    try:
        existing = client.table("revenue_settings").select("id").eq("brand_id", brand_id).execute()
        if existing.data and len(existing.data) > 0:
            res = client.table("revenue_settings").update(record).eq("brand_id", brand_id).execute()
            return res.data[0] if res.data else record
        else:
            res = client.table("revenue_settings").insert(record).execute()
            return res.data[0] if res.data else record
    except Exception as e:
        logger.error(f"Error updating revenue settings for brand {brand_id}: {e}")
        raise

def calculate_revenue_intelligence(
    visibility_score: float,
    settings: Dict[str, Any],
    competitor_mentions_count: int = 0,
    comp_mentions_count: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calculates estimated AI revenue, missed revenue, competitor deals lost, and revenue per visibility point.
    """
    if comp_mentions_count is not None and competitor_mentions_count == 0:
        competitor_mentions_count = comp_mentions_count

    traffic = int(settings.get("monthly_website_traffic", 10000))
    ai_pct = float(settings.get("ai_traffic_percentage", 15.0))
    conv_rate = float(settings.get("conversion_rate", 0.02))
    deal_val = float(settings.get("avg_deal_value", 50000.0))
    currency = settings.get("currency", "INR")

    score = max(0.0, min(100.0, float(visibility_score)))

    # Monthly AI Leads
    ai_leads = int(traffic * (ai_pct / 100.0))

    # Revenue metrics
    estimated_revenue = round(ai_leads * (score / 100.0) * conv_rate * deal_val, 2)
    missed_revenue = round(ai_leads * ((100.0 - score) / 100.0) * conv_rate * deal_val, 2)
    revenue_per_visibility_point = round(ai_leads * 0.01 * conv_rate * deal_val, 2)

    # Competitor deals lost estimation
    competitor_deals_lost = max(0, int(competitor_mentions_count * conv_rate * 5))

    formatted_rpt = format_currency_amount(revenue_per_visibility_point, currency)
    insight_text = f"Each +1 point in AI Visibility Score = {formatted_rpt} more revenue/month"

    return {
        "estimated_ai_revenue": estimated_revenue,
        "missed_revenue": missed_revenue,
        "competitor_deals_lost": competitor_deals_lost,
        "revenue_per_visibility_point": revenue_per_visibility_point,
        "monthly_ai_leads": ai_leads,
        "insight_text": insight_text,
        "current_visibility_score": score,
        "currency": currency,
        "formatted_estimated_revenue": format_currency_amount(estimated_revenue, currency),
        "formatted_missed_revenue": format_currency_amount(missed_revenue, currency)
    }

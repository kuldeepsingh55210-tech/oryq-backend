import logging
from typing import Dict, Any, List
from app.scanner.providers.groq_provider import call_groq
from app.database import get_supabase_client

logger = logging.getLogger(__name__)

def compute_reputation_metrics(sentiment_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes reputation score (0-100), positive %, negative %, neutral %, and risk level.
    """
    total = len(sentiment_items)
    if total == 0:
        return {
            "reputation_score": 50.00,
            "positive_pct": 0.0,
            "negative_pct": 0.0,
            "neutral_pct": 100.0,
            "risk_level": "low"
        }

    pos_count = sum(1 for item in sentiment_items if item.get("sentiment") == "positive")
    neg_count = sum(1 for item in sentiment_items if item.get("sentiment") == "negative")
    neu_count = sum(1 for item in sentiment_items if item.get("sentiment") == "neutral")

    pos_pct = round((pos_count / total) * 100, 2)
    neg_pct = round((neg_count / total) * 100, 2)
    neu_pct = round((neu_count / total) * 100, 2)

    # Reputation score formula: 100 * (positive% * 1.0 + neutral% * 0.5) / 100
    reputation_score = round(pos_pct * 1.0 + neu_pct * 0.5, 2)

    # Check hallucinations
    has_critical_h = any(item.get("risk_level") == "critical" or item.get("severity") == "critical" for item in sentiment_items)
    has_high_h = any(item.get("risk_level") == "high" or item.get("severity") == "high" for item in sentiment_items)

    if neg_pct > 40.0 or has_critical_h:
        risk_level = "critical"
    elif neg_pct > 25.0 or has_high_h:
        risk_level = "high"
    elif neg_pct > 10.0:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "reputation_score": reputation_score,
        "positive_pct": pos_pct,
        "negative_pct": neg_pct,
        "neutral_pct": neu_pct,
        "risk_level": risk_level
    }

async def generate_narrative_summary(brand_name: str, metrics: Dict[str, Any]) -> str:
    """
    Generates an executive 2-sentence narrative summary of brand perception using Groq.
    """
    prompt = f"""You are a CTO & PR intelligence engine. Generate a concise 2-sentence executive summary describing how top AI models perceive the brand '{brand_name}'.

Data:
- Reputation Score: {metrics['reputation_score']}/100
- Positive sentiment: {metrics['positive_pct']}%
- Negative sentiment: {metrics['negative_pct']}%
- Neutral sentiment: {metrics['neutral_pct']}%
- Risk Level: {metrics['risk_level']}

Respond with ONLY the 2-sentence narrative summary."""

    try:
        summary, _, _ = await call_groq(prompt, temperature=0.3, max_tokens=150)
        return summary.strip()
    except Exception as e:
        logger.error(f"Error generating narrative summary: {e}")
        return f"{brand_name} maintains an AI reputation score of {metrics['reputation_score']}/100 with a {metrics['risk_level']} overall risk rating across AI providers."

async def get_brand_narrative_drift(brand_id: str) -> List[Dict[str, Any]]:
    """
    Tracks narrative drift and reputation score history across the last 10 completed scans for a brand.
    """
    client = get_supabase_client()
    try:
        query = (
            client.table("reputation_scores")
            .select("*")
            .eq("brand_id", brand_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        scores = query.data or []
        # Return in chronological order
        return sorted(scores, key=lambda x: x.get("created_at", ""))
    except Exception as e:
        logger.error(f"Error fetching narrative drift: {e}")
        return []

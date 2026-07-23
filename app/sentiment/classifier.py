import re
import json
import logging
from typing import Dict, Any, Optional

from app.scanner.providers.groq_provider import call_groq
from app.database import get_supabase_client

logger = logging.getLogger(__name__)

POSITIVE_KEYWORDS = [
    "recommend", "best", "leading", "top", 
    "excellent", "trusted", "reliable", "great"
]

NEGATIVE_KEYWORDS = [
    "avoid", "poor", "unreliable", "scam", 
    "worst", "problematic", "fake", "fraud"
]

def stage_one_rule_based(text: str) -> Optional[Dict[str, Any]]:
    """
    Stage 1: High-speed rule-based classification using exact keyword count.
    Returns result dict if unambiguous, or None if ambiguous (escalates to Stage 2).
    """
    text_lower = text.lower()
    
    pos_count = sum(len(re.findall(rf"\b{kw}\b", text_lower)) for kw in POSITIVE_KEYWORDS)
    neg_count = sum(len(re.findall(rf"\b{kw}\b", text_lower)) for kw in NEGATIVE_KEYWORDS)

    if pos_count >= 2 and neg_count == 0:
        return {
            "sentiment": "positive",
            "sentiment_score": 0.800,
            "classification_method": "rule_based",
            "reasoning": f"Matched {pos_count} positive keywords, 0 negative keywords."
        }
    elif neg_count >= 2 and pos_count == 0:
        return {
            "sentiment": "negative",
            "sentiment_score": -0.800,
            "classification_method": "rule_based",
            "reasoning": f"Matched {neg_count} negative keywords, 0 positive keywords."
        }
    elif pos_count == 0 and neg_count == 0:
        return {
            "sentiment": "neutral",
            "sentiment_score": 0.000,
            "classification_method": "rule_based",
            "reasoning": "Matched 0 positive and 0 negative keywords."
        }
    
    # Ambiguous case (e.g. 1 positive keyword, 1 negative keyword, or mixed)
    return None

async def stage_two_llm(
    text: str,
    brand_name: str,
    scan_job_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Stage 2: LLM sentiment evaluation using Groq API for ambiguous responses.
    Logs cost to llm_cost_log in Supabase database.
    """
    prompt = f"""You are a brand sentiment analysis system. Analyze the following AI model response regarding the brand '{brand_name}'.
Classify the sentiment strictly as 'positive', 'neutral', or 'negative'.
Provide a numerical sentiment_score between -1.0 (extremely negative) and +1.0 (extremely positive).

Text to analyze:
\"\"\"
{text}
\"\"\"

Respond STRICTLY with valid JSON in this exact structure:
{{
  "sentiment": "positive" | "neutral" | "negative",
  "score": float,
  "reasoning": "short explanation"
}}
"""

    response_text, cost_usd, latency_ms = await call_groq(prompt, temperature=0.0, max_tokens=300)
    
    # Log cost to DB if scan_job_id provided
    if scan_job_id and cost_usd > 0:
        try:
            client = get_supabase_client()
            client.table("llm_cost_log").insert({
                "scan_job_id": scan_job_id,
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "cost_usd": cost_usd
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to log LLM cost for sentiment stage 2: {e}")

    # Parse JSON output safely
    try:
        clean_json = response_text.strip()
        if "```json" in clean_json:
            clean_json = clean_json.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_json:
            clean_json = clean_json.split("```")[1].split("```")[0].strip()
            
        data = json.loads(clean_json)
        sentiment = str(data.get("sentiment", "neutral")).lower()
        if sentiment not in ["positive", "neutral", "negative"]:
            sentiment = "neutral"
            
        raw_score = float(data.get("score", 0.0))
        score = max(-1.0, min(1.0, raw_score))
        reasoning = data.get("reasoning", "LLM classified sentiment.")

        return {
            "sentiment": sentiment,
            "sentiment_score": round(score, 3),
            "classification_method": "llm",
            "reasoning": reasoning
        }
    except Exception as e:
        logger.error(f"Error parsing Groq sentiment LLM response: {e}. Fallback to neutral.")
        return {
            "sentiment": "neutral",
            "sentiment_score": 0.000,
            "classification_method": "llm",
            "reasoning": "LLM output parsing fallback."
        }

async def classify_response_sentiment(
    text: str,
    brand_name: str,
    scan_job_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    2-Stage Sentiment Classifier entrypoint.
    Executes Stage 1 (Rule-based, 60%+ cases). If ambiguous, executes Stage 2 (Groq LLM).
    """
    if not text:
        return {
            "sentiment": "neutral",
            "sentiment_score": 0.000,
            "classification_method": "rule_based",
            "reasoning": "Empty response text."
        }

    rule_result = stage_one_rule_based(text)
    if rule_result is not None:
        return rule_result

    # Fallback to Stage 2 LLM
    return await stage_two_llm(text, brand_name, scan_job_id=scan_job_id)

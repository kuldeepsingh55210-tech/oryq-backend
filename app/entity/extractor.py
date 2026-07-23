import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.scanner.providers.groq_provider import call_groq
from app.database import get_supabase_client

logger = logging.getLogger(__name__)

VALID_ENTITY_TYPES = {"product", "person", "differentiator", "technology", "award", "location"}

async def extract_entities_from_response(
    response_text: str,
    brand_name: str,
    scan_job_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Extracts brand entities from an AI response text using Groq.
    Cost: ~$0.00008 per execution.
    """
    if not response_text or len(response_text.strip()) < 15:
        return []

    prompt = f"""You are an entity intelligence extractor for brand analysis.
Extract all entity mentions about brand '{brand_name}' from the following AI model response.
Classify each entity strictly as one of these types: 'product', 'person', 'differentiator', 'technology', 'award', or 'location'.

AI Response:
\"\"\"
{response_text}
\"\"\"

Respond STRICTLY with valid JSON array of objects in this exact format:
[
  {{"name": "Entity Name", "type": "product|person|differentiator|technology|award|location", "mentioned": true}}
]
"""

    response_str, cost_usd, latency_ms = await call_groq(prompt, temperature=0.0, max_tokens=400)

    # Log cost if scan_job_id provided
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
            logger.warning(f"Error logging LLM cost in entity extractor: {e}")

    try:
        clean_json = response_str.strip()
        if "```json" in clean_json:
            clean_json = clean_json.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_json:
            clean_json = clean_json.split("```")[1].split("```")[0].strip()

        data = json.loads(clean_json)
        if not isinstance(data, list):
            return []

        extracted = []
        for item in data:
            name = str(item.get("name", "")).strip()
            etype = str(item.get("type", "")).strip().lower()
            if name and etype in VALID_ENTITY_TYPES:
                extracted.append({
                    "name": name,
                    "type": etype,
                    "mentioned": bool(item.get("mentioned", True))
                })
        return extracted
    except Exception as e:
        logger.error(f"Error parsing entity extraction output: {e}")
        return []

async def sync_brand_entities_with_scan(
    brand_id: str,
    scan_job_id: str,
    extracted_entities: List[Dict[str, Any]],
    total_prompts: int
) -> None:
    """
    Updates or inserts brand entities in Supabase database and computes coverage_pct and is_known_to_ai.
    """
    if not brand_id:
        return

    client = get_supabase_client()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Aggregate extracted mentions count per entity
    mention_counts: Dict[str, Dict[str, Any]] = {}
    for e in extracted_entities:
        key = e["name"].lower()
        if key not in mention_counts:
            mention_counts[key] = {"name": e["name"], "type": e["type"], "count": 1}
        else:
            mention_counts[key]["count"] += 1

    # Fetch existing entities for brand
    try:
        existing_query = client.table("brand_entities").select("*").eq("brand_id", brand_id).execute()
        existing_map = {row["entity_name"].lower(): row for row in (existing_query.data or [])}

        for key, info in mention_counts.items():
            cnt = info["count"]
            coverage_pct = round((cnt / max(total_prompts, 1)) * 100, 2)
            is_known = cnt > 0

            if key in existing_map:
                ent_id = existing_map[key]["id"]
                client.table("brand_entities").update({
                    "is_known_to_ai": is_known or existing_map[key].get("is_known_to_ai", False),
                    "coverage_pct": max(coverage_pct, float(existing_map[key].get("coverage_pct") or 0)),
                    "last_seen_at": now_iso
                }).eq("id", ent_id).execute()
            else:
                client.table("brand_entities").insert({
                    "brand_id": brand_id,
                    "entity_name": info["name"],
                    "entity_type": info["type"],
                    "is_known_to_ai": is_known,
                    "coverage_pct": coverage_pct,
                    "last_seen_at": now_iso
                }).execute()
    except Exception as e:
        logger.error(f"Error syncing brand entities for brand_id {brand_id}: {e}")

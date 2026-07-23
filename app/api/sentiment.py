import logging
from uuid import UUID
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query, status

from app.database import get_supabase_client
from app.sentiment.classifier import classify_response_sentiment
from app.sentiment.hallucination import detect_hallucinations
from app.sentiment.reputation import compute_reputation_metrics, generate_narrative_summary, get_brand_narrative_drift

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Sentiment & Reputation"])

class HallucinationStatusUpdate(BaseModel):
    status: str  # confirmed | resolved | false_positive

async def ensure_sentiment_analyzed(scan_job_id: str) -> List[Dict[str, Any]]:
    """
    Ensures scan results for a job have been classified and analyzed.
    If sentiment_results do not exist in DB, runs classifier and detector and saves records.
    """
    client = get_supabase_client()
    
    # 1. Check existing sentiment_results
    existing = client.table("sentiment_results").select("*").eq("scan_job_id", scan_job_id).execute()
    if existing.data and len(existing.data) > 0:
        return existing.data

    # 2. Fetch scan job details and results
    job_query = client.table("scan_jobs").select("*").eq("id", scan_job_id).execute()
    if not job_query.data:
        raise HTTPException(status_code=404, detail="Scan job not found")
    job = job_query.data[0]
    brand_id = job.get("brand_id")

    brand_name = "Brand"
    if brand_id:
        b_query = client.table("brands").select("name").eq("id", brand_id).execute()
        if b_query.data:
            brand_name = b_query.data[0].get("name", "Brand")

    results_query = client.table("scan_results").select("*").eq("scan_job_id", scan_job_id).execute()
    results = results_query.data or []

    # 3. Analyze each result
    sentiment_records = []
    for r in results:
        text = r.get("response_text", "")
        provider = r.get("provider", "groq")
        result_id = r.get("id")

        # Classify sentiment
        cls = await classify_response_sentiment(text, brand_name, scan_job_id=scan_job_id)
        # Detect hallucinations
        hal = await detect_hallucinations(text, brand_name, provider)

        record = {
            "scan_job_id": scan_job_id,
            "scan_result_id": result_id,
            "sentiment": cls["sentiment"],
            "sentiment_score": cls["sentiment_score"],
            "classification_method": cls["classification_method"],
            "has_hallucination": hal["has_hallucination"],
            "hallucination_text": hal["hallucination_text"],
            "hallucination_status": hal["status"],
            "risk_level": hal["severity"]
        }
        
        try:
            ins = client.table("sentiment_results").insert(record).execute()
            if ins.data:
                sentiment_records.append(ins.data[0])
            else:
                sentiment_records.append(record)
        except Exception as e:
            logger.error(f"Error inserting sentiment_result: {e}")
            sentiment_records.append(record)

    # 4. Compute and insert reputation score summary
    metrics = compute_reputation_metrics(sentiment_records)
    summary_text = await generate_narrative_summary(brand_name, metrics)
    
    if brand_id:
        try:
            rep_record = {
                "brand_id": brand_id,
                "scan_job_id": scan_job_id,
                "reputation_score": metrics["reputation_score"],
                "positive_pct": metrics["positive_pct"],
                "negative_pct": metrics["negative_pct"],
                "neutral_pct": metrics["neutral_pct"],
                "risk_level": metrics["risk_level"],
                "narrative_summary": summary_text
            }
            client.table("reputation_scores").insert(rep_record).execute()
        except Exception as e:
            logger.error(f"Error inserting reputation_score record: {e}")

    return sentiment_records

@router.get("/api/v1/sentiment/{scan_job_id}")
async def get_scan_job_sentiment(scan_job_id: UUID):
    """
    Returns aggregated sentiment, classification breakdown (rule_based vs LLM),
    hallucination counts, and reputation score for a scan job.
    """
    scan_id_str = str(scan_job_id)
    records = await ensure_sentiment_analyzed(scan_id_str)
    
    pos_cnt = sum(1 for r in records if r.get("sentiment") == "positive")
    neg_cnt = sum(1 for r in records if r.get("sentiment") == "negative")
    neu_cnt = sum(1 for r in records if r.get("sentiment") == "neutral")

    rule_cnt = sum(1 for r in records if r.get("classification_method") == "rule_based")
    llm_cnt = sum(1 for r in records if r.get("classification_method") == "llm")

    h_cnt = sum(1 for r in records if r.get("has_hallucination"))

    metrics = compute_reputation_metrics(records)
    
    # Calculate overall sentiment
    if pos_cnt >= neg_cnt and pos_cnt >= neu_cnt:
        overall_sentiment = "positive"
    elif neg_cnt >= pos_cnt and neg_cnt >= neu_cnt:
        overall_sentiment = "negative"
    else:
        overall_sentiment = "neutral"

    avg_score = round(sum(float(r.get("sentiment_score") or 0.0) for r in records) / max(len(records), 1), 3)

    return {
        "scan_job_id": scan_job_id,
        "overall_sentiment": overall_sentiment,
        "sentiment_score": avg_score,
        "positive_count": pos_cnt,
        "negative_count": neg_cnt,
        "neutral_count": neu_cnt,
        "classification_breakdown": {
            "rule_based": rule_cnt,
            "llm": llm_cnt
        },
        "hallucination_count": h_cnt,
        "risk_level": metrics["risk_level"],
        "reputation_score": metrics["reputation_score"]
    }

@router.get("/api/v1/sentiment/{scan_job_id}/feed")
async def get_sentiment_feed(
    scan_job_id: UUID,
    sentiment: Optional[str] = Query(None, description="Filter by: positive | neutral | negative"),
    has_hallucination: Optional[bool] = Query(None, description="Filter by hallucination presence"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Returns list of AI responses with sentiment tags, filterable and paginated.
    """
    scan_id_str = str(scan_job_id)
    records = await ensure_sentiment_analyzed(scan_id_str)

    client = get_supabase_client()
    res_query = client.table("scan_results").select("*").eq("scan_job_id", scan_id_str).execute()
    results_map = {r["id"]: r for r in (res_query.data or [])}

    filtered = []
    for s in records:
        if sentiment and s.get("sentiment") != sentiment.lower():
            continue
        if has_hallucination is not None and s.get("has_hallucination") != has_hallucination:
            continue
            
        result_info = results_map.get(s.get("scan_result_id"), {})
        filtered.append({
            "sentiment_id": s.get("id"),
            "scan_result_id": s.get("scan_result_id"),
            "prompt_text": result_info.get("prompt_text"),
            "provider": result_info.get("provider"),
            "response_text": result_info.get("response_text"),
            "sentiment": s.get("sentiment"),
            "sentiment_score": float(s.get("sentiment_score") or 0.0),
            "classification_method": s.get("classification_method"),
            "has_hallucination": s.get("has_hallucination"),
            "hallucination_text": s.get("hallucination_text"),
            "hallucination_status": s.get("hallucination_status"),
            "risk_level": s.get("risk_level"),
            "created_at": s.get("created_at")
        })

    paginated = filtered[offset : offset + limit]
    return {
        "total": len(filtered),
        "limit": limit,
        "offset": offset,
        "results": paginated
    }

@router.get("/api/v1/sentiment/{scan_job_id}/hallucinations")
async def get_scan_hallucinations(scan_job_id: UUID):
    """
    Returns all detected hallucinations for this scan with claim, severity, status, and provider.
    """
    scan_id_str = str(scan_job_id)
    records = await ensure_sentiment_analyzed(scan_id_str)

    client = get_supabase_client()
    res_query = client.table("scan_results").select("*").eq("scan_job_id", scan_id_str).execute()
    results_map = {r["id"]: r for r in (res_query.data or [])}

    hallucinations = []
    for s in records:
        if s.get("has_hallucination"):
            result_info = results_map.get(s.get("scan_result_id"), {})
            hallucinations.append({
                "id": s.get("id"),
                "scan_job_id": scan_job_id,
                "scan_result_id": s.get("scan_result_id"),
                "claim": s.get("hallucination_text"),
                "severity": s.get("risk_level", "medium"),
                "status": s.get("hallucination_status", "unreviewed"),
                "provider": result_info.get("provider", "unknown"),
                "response_snippet": result_info.get("response_text", "")[:300] if result_info.get("response_text") else ""
            })

    return hallucinations

@router.patch("/api/v1/sentiment/hallucinations/{id}")
async def update_hallucination_status(id: UUID, request: HallucinationStatusUpdate):
    """
    Updates status of a hallucination record to 'confirmed', 'resolved', or 'false_positive'.
    """
    status_clean = request.status.strip().lower()
    if status_clean not in ["confirmed", "resolved", "false_positive", "unreviewed"]:
        raise HTTPException(status_code=400, detail="Invalid status option")

    client = get_supabase_client()
    try:
        upd = (
            client.table("sentiment_results")
            .update({"hallucination_status": status_clean})
            .eq("id", str(id))
            .execute()
        )
        if not upd.data:
            raise HTTPException(status_code=404, detail="Hallucination record not found")
        return {"success": True, "id": str(id), "status": status_clean}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating hallucination status: {e}")
        raise HTTPException(status_code=500, detail=f"Database update error: {str(e)}")

@router.get("/api/v1/reputation/{brand_id}")
async def get_brand_reputation_dashboard(brand_id: UUID):
    """
    Returns reputation dashboard data for brand_id including narrative drift over the last 10 scans.
    """
    brand_id_str = str(brand_id)
    client = get_supabase_client()

    # Fetch brand
    brand_query = client.table("brands").select("*").eq("id", brand_id_str).execute()
    if not brand_query.data:
        raise HTTPException(status_code=404, detail="Brand not found")
    brand = brand_query.data[0]

    # Fetch narrative drift (last 10 reputation_scores)
    drift = await get_brand_narrative_drift(brand_id_str)
    
    latest_score = drift[-1] if drift else {}

    return {
        "brand_id": brand_id,
        "brand_name": brand.get("name"),
        "current_reputation_score": float(latest_score.get("reputation_score") or 50.0),
        "risk_level": latest_score.get("risk_level", "low"),
        "positive_pct": float(latest_score.get("positive_pct") or 0.0),
        "negative_pct": float(latest_score.get("negative_pct") or 0.0),
        "neutral_pct": float(latest_score.get("neutral_pct") or 100.0),
        "narrative_summary": latest_score.get("narrative_summary", "No narrative data collected yet."),
        "narrative_drift_last_10_scans": drift
    }

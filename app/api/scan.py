from fastapi import APIRouter, HTTPException, Depends, Response
from uuid import UUID
from typing import List, Dict, Any
from pydantic import BaseModel, EmailStr

from app.database import get_supabase_client
from app.config import settings
from app.models.scan import ScanStartRequest, ScanStartResponse, ProviderSummary, FullScanResult
from app.scanner.prompts import get_prompts_with_categories
from app.scanner.engine import run_scan
from app.scanner.scorer import compute_score
from app.reports import generate_scan_pdf
from app.email import send_scan_report_email
from app.recommendations import generate_recommendations

router = APIRouter(prefix="/api/v1/scan", tags=["Scan"])

class PromptBreakdown(BaseModel):
    prompt_text: str
    provider: str
    brand_mentioned: bool
    response_snippet: str

class EmailReportRequest(BaseModel):
    email: EmailStr

async def fetch_scan_details(scan_job_id: UUID) -> Dict[str, Any]:
    client = get_supabase_client()
    # 1. Fetch scan job
    job_query = client.table("scan_jobs").select("*").eq("id", str(scan_job_id)).execute()
    if not job_query.data:
        raise HTTPException(status_code=404, detail="Scan job not found")
    job = job_query.data[0]
    brand_id = job.get("brand_id")

    # 2. Fetch brand details
    if not brand_id:
        raise HTTPException(status_code=404, detail="Brand not associated with scan job")
    brand_query = client.table("brands").select("*").eq("id", brand_id).execute()
    if not brand_query.data:
        raise HTTPException(status_code=404, detail="Brand not found")
    brand = brand_query.data[0]

    # 3. Fetch scan results
    results_query = client.table("scan_results").select("*").eq("scan_job_id", str(scan_job_id)).execute()
    results_db = results_query.data or []

    # 4. Fetch hallucinations
    hallucinations_query = client.table("hallucinations").select("*").eq("scan_job_id", str(scan_job_id)).execute()
    hallucinations_db = hallucinations_query.data or []

    return {
        "job": job,
        "brand": brand,
        "results": results_db,
        "hallucinations": hallucinations_db
    }

@router.post("/start", response_model=ScanStartResponse)
async def start_scan(request: ScanStartRequest):
    """
    Initializes a scan job for the given brand.
    1. Creates/resolves the brand in the database.
    2. Creates a queued scan job.
    3. Triggers the scan execution synchronously.
    4. Computes score and returns results.
    """
    client = get_supabase_client()
    brand_name = request.brand_name.strip()
    website_url = request.website_url.strip() if request.website_url else None
    industry = request.industry.strip() if request.industry else None

    if not brand_name:
        raise HTTPException(status_code=400, detail="Brand name cannot be empty")

    # 1. Create or fetch brand
    try:
        brand_query = client.table("brands").select("*").eq("name", brand_name).execute()
        if brand_query.data:
            brand = brand_query.data[0]
            brand_id = brand["id"]
            brand_aliases = brand.get("aliases") or []
        else:
            new_brand = {
                "name": brand_name,
                "website_url": website_url,
                "industry": industry,
                "aliases": []
            }
            insert_query = client.table("brands").insert(new_brand).execute()
            if not insert_query.data:
                raise HTTPException(status_code=500, detail="Failed to create brand record")
            brand = insert_query.data[0]
            brand_id = brand["id"]
            brand_aliases = []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error resolving brand: {str(e)}")

    # 2. Determine which providers to run
    providers = []
    if settings.GROQ_API_KEY:
        providers.append("groq")
    if settings.GEMINI_API_KEY:
        providers.append("gemini")
    if settings.OPENAI_API_KEY:
        providers.append("openai")

    if not providers:
        raise HTTPException(status_code=400, detail="No active LLM providers configured on the backend.")

    if not request.run_all_providers:
        # Run only the primary provider (groq) if configured, otherwise fallback to first available
        if "groq" in providers:
            providers = ["groq"]
        else:
            providers = [providers[0]]

    # 3. Create scan job in status=queued
    try:
        new_job = {
            "brand_id": brand_id,
            "status": "queued",
            "total_prompts": 0,
            "completed_prompts": 0,
            "total_cost_usd": 0.0
        }
        job_query = client.table("scan_jobs").insert(new_job).execute()
        if not job_query.data:
            raise HTTPException(status_code=500, detail="Failed to create scan job")
        scan_job_id = job_query.data[0]["id"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error initializing scan job: {str(e)}")

    # 4. Format prompts and run the scan
    prompts = get_prompts_with_categories(brand_name, industry or "general")
    
    try:
        results = await run_scan(
            scan_job_id=scan_job_id,
            brand_name=brand_name,
            brand_aliases=brand_aliases,
            industry=industry or "general",
            prompts=prompts,
            providers=providers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan execution error: {str(e)}")

    # 5. Compute the final scores and response formatting
    overall_score, breakdown = compute_score(results)
    total_cost = sum(r.cost_usd for r in results)
    brand_mentioned_count = sum(1 for r in results if r.brand_mentioned)

    results_summary = [
        ProviderSummary(
            provider=p,
            score=data["score"],
            mentions=data["mentions"],
            total=data["total"]
        )
        for p, data in breakdown.items() if data["total"] > 0
    ]

    return ScanStartResponse(
        scan_job_id=scan_job_id,
        status="completed",
        score=overall_score,
        total_prompts_run=len(results),
        brand_mentioned_count=brand_mentioned_count,
        total_cost_usd=total_cost,
        results_summary=results_summary
    )
@router.get("/{scan_job_id}")
async def get_scan_job_status(scan_job_id: UUID):
    """
    Returns scan job status + high-level results.
    """
    client = get_supabase_client()
    try:
        job_query = client.table("scan_jobs").select("*").eq("id", str(scan_job_id)).execute()
        if not job_query.data:
            raise HTTPException(status_code=404, detail="Scan job not found")
        job = job_query.data[0]

        results_query = client.table("scan_results").select("*").eq("scan_job_id", str(scan_job_id)).execute()
        results_db = results_query.data or []

        results = [
            FullScanResult(
                prompt_text=r["prompt_text"],
                provider=r["provider"],
                brand_mentioned=r["brand_mentioned"],
                response_snippet=r["response_text"][:200] if r["response_text"] else "",
                cost_usd=float(r["cost_usd"]) if r["cost_usd"] is not None else 0.0,
                latency_ms=r["latency_ms"] if r["latency_ms"] is not None else 0
            )
            for r in results_db
        ]        # Fetch hallucinations to compute headline_evidence
        hallucinations_query = client.table("hallucinations").select("*").eq("scan_job_id", str(scan_job_id)).execute()
        hallucinations_db = hallucinations_query.data or []

        headline_evidence = None
        if hallucinations_db:
            # Sort by severity high first
            h_sorted = sorted(hallucinations_db, key=lambda x: 1 if x.get("severity") == "high" else 2)
            h = h_sorted[0]
            headline_evidence = {
                "type": "hallucination",
                "prompt_text": None,
                "ai_response_snippet": h.get("source_response")[:200] if h.get("source_response") else "",
                "provider": h.get("provider", "Unknown"),
                "claim": h.get("claim", "")
            }
        else:
            missed = [r for r in results_db if not r.get("brand_mentioned")]
            if missed:
                m = missed[0]
                headline_evidence = {
                    "type": "missed_mention",
                    "prompt_text": m.get("prompt_text"),
                    "ai_response_snippet": m.get("response_text")[:200] if m.get("response_text") else "",
                    "provider": m.get("provider", "Unknown"),
                    "claim": None
                }
            else:
                headline_evidence = {
                    "type": "none",
                    "prompt_text": None,
                    "ai_response_snippet": None,
                    "provider": None,
                    "claim": None
                }

        # Fetch previous completed scan to compute trend
        brand_id = job.get("brand_id")
        trend = {
            "has_previous": False,
            "change_percent": None,
            "direction": None
        }
        if brand_id:
            try:
                # 1. Resolve brand name for the current brand_id
                brand_query = client.table("brands").select("name").eq("id", brand_id).execute()
                if brand_query.data:
                    brand_name = brand_query.data[0].get("name")
                    if brand_name:
                        # 2. Get all brand IDs that match this brand_name
                        brands_matching = client.table("brands").select("id").eq("name", brand_name).execute()
                        brand_ids = [b["id"] for b in brands_matching.data] if brands_matching.data else [brand_id]
                        
                        # 3. Query for previous completed scan excluding current scan_job_id
                        prev_scan_query = (
                            client.table("scan_jobs")
                            .select("*")
                            .in_("brand_id", brand_ids)
                            .eq("status", "completed")
                            .neq("id", str(scan_job_id))
                            .order("created_at", desc=True)
                            .limit(1)
                            .execute()
                        )
                        prev_scan_db = prev_scan_query.data
                        if prev_scan_db:
                            prev_scan = prev_scan_db[0]
                            prev_score = prev_scan.get("visibility_score")
                            current_score = job.get("visibility_score")
                            if prev_score is not None and current_score is not None:
                                prev_score = float(prev_score)
                                current_score = float(current_score)
                                
                                if prev_score == 0:
                                    change_percent = 0.0
                                else:
                                    delta = current_score - prev_score
                                    change_percent = round((delta / prev_score) * 100, 1)
                                
                                delta = current_score - prev_score
                                direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
                                
                                trend = {
                                    "has_previous": True,
                                    "change_percent": change_percent,
                                    "direction": direction
                                }
            except Exception:
                # Graceful fallback: default to has_previous: false (never crash)
                trend = {
                    "has_previous": False,
                    "change_percent": None,
                    "direction": None
                }

        return {
            "scan_job_id": scan_job_id,
            "status": job["status"],
            "score": float(job["visibility_score"]) if job.get("visibility_score") is not None else 0.0,
            "total_cost_usd": float(job["total_cost_usd"]) if job.get("total_cost_usd") is not None else 0.0,
            "results": results,
            "headline_evidence": headline_evidence,
            "trend": trend
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error fetching scan job: {str(e)}")

@router.get("/{scan_job_id}/results", response_model=List[PromptBreakdown])
async def get_scan_job_results_breakdown(scan_job_id: UUID):
    """
    Full results with per-prompt breakdown.
    """
    client = get_supabase_client()
    try:
        job_query = client.table("scan_jobs").select("id").eq("id", str(scan_job_id)).execute()
        if not job_query.data:
            raise HTTPException(status_code=404, detail="Scan job not found")

        results_query = client.table("scan_results").select("*").eq("scan_job_id", str(scan_job_id)).execute()
        results_db = results_query.data or []

        return [
            PromptBreakdown(
                prompt_text=r["prompt_text"],
                provider=r["provider"],
                brand_mentioned=r["brand_mentioned"],
                response_snippet=r["response_text"][:200] if r["response_text"] else ""
            )
            for r in results_db
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error fetching scan results: {str(e)}")

from datetime import datetime

class BrandHistoryItem(BaseModel):
    scan_job_id: UUID
    score: float
    created_at: datetime
    total_prompts_run: int

@router.get("/brands/{brand_name}/history", response_model=List[BrandHistoryItem])
async def get_brand_history(brand_name: str):
    """
    Returns scan history for a given brand name.
    """
    client = get_supabase_client()
    brand_name_clean = brand_name.strip()
    if not brand_name_clean:
        raise HTTPException(status_code=400, detail="Brand name cannot be empty")
        
    try:
        # 1. Fetch brand by name case-insensitively using ilike
        brand_query = client.table("brands").select("id").ilike("name", brand_name_clean).execute()
        if not brand_query.data:
            return []
            
        brand_id = brand_query.data[0]["id"]
        
        # 2. Fetch last 20 completed scans for this brand_id
        jobs_query = (
            client.table("scan_jobs")
            .select("id, visibility_score, created_at, completed_prompts")
            .eq("brand_id", brand_id)
            .eq("status", "completed")
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        
        jobs_db = jobs_query.data or []
        
        return [
            BrandHistoryItem(
                scan_job_id=job["id"],
                score=float(job["visibility_score"]) if job.get("visibility_score") is not None else 0.0,
                created_at=job["created_at"],
                total_prompts_run=job["completed_prompts"] or 0
            )
            for job in jobs_db
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error fetching history: {str(e)}")

@router.get("/{scan_job_id}/report.pdf")
async def get_scan_report_pdf(scan_job_id: UUID):
    """
    Generates and returns a branded PDF report for the scan.
    """
    try:
        details = await fetch_scan_details(scan_job_id)
        job = details["job"]
        brand = details["brand"]
        results_db = details["results"]
        hallucinations_db = details["hallucinations"]

        brand_name = brand.get("name", "Unknown")
        website_url = brand.get("website_url", "Unknown")
        industry = brand.get("industry") or "general"

        overall_score, breakdown = compute_score(results_db)
        total_prompts_run = len(results_db)
        brand_mentioned_count = sum(1 for r in results_db if r.get("brand_mentioned"))

        results_summary = [
            {
                "provider": p,
                "score": data["score"],
                "mentions": data["mentions"],
                "total": data["total"]
            }
            for p, data in breakdown.items() if data["total"] > 0
        ]

        competitor_data = None

        # Fetch missed prompts: where brand_mentioned = False, limit 5, order by created_at
        client = get_supabase_client()
        missed_query = (
            client.table("scan_results")
            .select("*")
            .eq("scan_job_id", str(scan_job_id))
            .eq("brand_mentioned", False)
            .order("created_at")
            .limit(5)
            .execute()
        )
        missed_prompts = missed_query.data or []

        # Call recommendations generator (LLM cached engine)
        recommendations = await generate_recommendations(
            brand_name=brand_name,
            industry=industry,
            score=overall_score,
            hallucinations=hallucinations_db,
            scan_job_id=scan_job_id
        )

        # Format scan date
        created_at_str = job.get("created_at")
        scan_date = "N/A"
        if created_at_str:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                scan_date = dt.strftime("%B %d, %Y")
            except Exception:
                scan_date = created_at_str[:10]

        pdf_bytes = generate_scan_pdf(
            brand_name=brand_name,
            website_url=website_url,
            score=overall_score,
            total_prompts_run=total_prompts_run,
            brand_mentioned_count=brand_mentioned_count,
            results_summary=results_summary,
            competitor_data=competitor_data,
            hallucinations=hallucinations_db,
            scan_date=scan_date,
            missed_prompts=missed_prompts,
            recommendations=recommendations
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=oryq-report-{brand_name}.pdf"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF report: {str(e)}")

@router.post("/{scan_job_id}/email")
async def send_scan_report_email_endpoint(scan_job_id: UUID, request: EmailReportRequest):
    """
    Generates a branded PDF report for the scan and emails it using Resend.
    """
    try:
        details = await fetch_scan_details(scan_job_id)
        job = details["job"]
        brand = details["brand"]
        results_db = details["results"]
        hallucinations_db = details["hallucinations"]

        brand_name = brand.get("name", "Unknown")
        website_url = brand.get("website_url", "Unknown")
        industry = brand.get("industry") or "general"

        overall_score, breakdown = compute_score(results_db)
        total_prompts_run = len(results_db)
        brand_mentioned_count = sum(1 for r in results_db if r.get("brand_mentioned"))

        results_summary = [
            {
                "provider": p,
                "score": data["score"],
                "mentions": data["mentions"],
                "total": data["total"]
            }
            for p, data in breakdown.items() if data["total"] > 0
        ]

        competitor_data = None

        # Fetch missed prompts: where brand_mentioned = False, limit 5, order by created_at
        client = get_supabase_client()
        missed_query = (
            client.table("scan_results")
            .select("*")
            .eq("scan_job_id", str(scan_job_id))
            .eq("brand_mentioned", False)
            .order("created_at")
            .limit(5)
            .execute()
        )
        missed_prompts = missed_query.data or []

        # Call recommendations generator (LLM cached engine)
        recommendations = await generate_recommendations(
            brand_name=brand_name,
            industry=industry,
            score=overall_score,
            hallucinations=hallucinations_db,
            scan_job_id=scan_job_id
        )

        # Format scan date
        created_at_str = job.get("created_at")
        scan_date = "N/A"
        if created_at_str:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                scan_date = dt.strftime("%B %d, %Y")
            except Exception:
                scan_date = created_at_str[:10]

        pdf_bytes = generate_scan_pdf(
            brand_name=brand_name,
            website_url=website_url,
            score=overall_score,
            total_prompts_run=total_prompts_run,
            brand_mentioned_count=brand_mentioned_count,
            results_summary=results_summary,
            competitor_data=competitor_data,
            hallucinations=hallucinations_db,
            scan_date=scan_date,
            missed_prompts=missed_prompts,
            recommendations=recommendations
        )

        dashboard_url = f"{settings.FRONTEND_URL}/scan/{scan_job_id}"

        to_email = request.email.strip()
        res = await send_scan_report_email(
            to_email=to_email,
            brand_name=brand_name,
            score=overall_score,
            brand_mentioned_count=brand_mentioned_count,
            total_prompts_run=total_prompts_run,
            scan_job_id=str(scan_job_id),
            dashboard_url=dashboard_url,
            pdf_bytes=pdf_bytes
        )

        if not res.get("success"):
            raise HTTPException(status_code=500, detail=res.get("error") or "Failed to send email.")

        return {
            "success": True,
            "message": f"Report successfully emailed to {to_email}."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error emailing scan report: {str(e)}")

@router.get("/{scan_job_id}/recommendations")
async def get_scan_recommendations(scan_job_id: UUID):
    """
    Returns action recommendations based on scan results/hallucinations.
    """
    try:
        details = await fetch_scan_details(scan_job_id)
        job = details["job"]
        brand = details["brand"]
        results_db = details["results"]
        hallucinations_db = details["hallucinations"]

        brand_name = brand.get("name", "Unknown")
        industry = brand.get("industry") or "general"

        overall_score, _ = compute_score(results_db)

        recommendations = await generate_recommendations(
            brand_name=brand_name,
            industry=industry,
            score=overall_score,
            hallucinations=hallucinations_db,
            scan_job_id=scan_job_id
        )

        return recommendations
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")

# DONE - scan.py

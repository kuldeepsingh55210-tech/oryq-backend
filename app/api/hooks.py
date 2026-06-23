"""
Fear Hooks API Router — Phase 2 Endpoints

Provides competitor comparison, hallucination detection,
and citation gap analysis endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from uuid import UUID
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.database import get_supabase_client
from app.hooks.competitor import run_competitor_scan
from app.hooks.hallucination import scan_for_hallucinations
from app.hooks.citations import find_citation_gaps

router = APIRouter(prefix="/api/v1/scan", tags=["Hooks"])


# === Request / Response Models ===

class CompetitorRequest(BaseModel):
    competitor_names: List[str] = Field(..., max_length=2, description="Up to 2 competitor names")

class CompetitorBrand(BaseModel):
    name: str
    score: float
    mentions: int

class CompetitorResponse(BaseModel):
    main_brand: CompetitorBrand
    competitors: List[CompetitorBrand]
    rank: int
    gap_to_leader: float

class HallucinationRequest(BaseModel):
    known_facts: Dict[str, str] = Field(
        ...,
        description="Known facts about the brand, e.g. {'pricing': 'free delivery above ₹99', 'founded': '2021'}"
    )

class HallucinationItem(BaseModel):
    claim: str
    source_response: str
    provider: str
    severity: str

class CitationGapItem(BaseModel):
    domain: str
    cites_competitor: str
    cites_brand: bool


# === Endpoints ===

@router.post("/{scan_job_id}/competitors", response_model=CompetitorResponse)
async def competitor_comparison(scan_job_id: UUID, request: CompetitorRequest):
    """
    Runs a competitor comparison scan.
    Generates the same 20 prompts for the main brand and each competitor,
    computes independent scores, and returns a ranked comparison.
    """
    client = get_supabase_client()

    # 1. Fetch the scan job to get brand info
    try:
        job_query = client.table("scan_jobs").select("*").eq("id", str(scan_job_id)).execute()
        if not job_query.data:
            raise HTTPException(status_code=404, detail="Scan job not found")
        job = job_query.data[0]

        brand_query = client.table("brands").select("*").eq("id", job["brand_id"]).execute()
        if not brand_query.data:
            raise HTTPException(status_code=404, detail="Brand not found for this scan job")
        brand = brand_query.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    brand_name = brand["name"]
    industry = brand.get("industry") or "general"
    competitors = request.competitor_names[:2]  # Cap at 2

    if not competitors:
        raise HTTPException(status_code=400, detail="At least one competitor name is required")

    # 2. Run the competitor scan (defaults to Groq-only)
    try:
        result = await run_competitor_scan(
            brand_name=brand_name,
            competitor_names=competitors,
            industry=industry,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Competitor scan failed: {str(e)}")

    return CompetitorResponse(
        main_brand=CompetitorBrand(**result["main_brand"]),
        competitors=[CompetitorBrand(**c) for c in result["competitors"]],
        rank=result["rank"],
        gap_to_leader=result["gap_to_leader"],
    )


@router.post("/{scan_job_id}/hallucinations", response_model=List[HallucinationItem])
async def hallucination_check(scan_job_id: UUID, request: HallucinationRequest):
    """
    Runs hallucination detection on existing scan results.
    Fact-checks AI responses that mentioned the brand against known facts.
    Saves findings to the hallucinations table.
    """
    client = get_supabase_client()

    # 1. Fetch scan job and brand info
    try:
        job_query = client.table("scan_jobs").select("*").eq("id", str(scan_job_id)).execute()
        if not job_query.data:
            raise HTTPException(status_code=404, detail="Scan job not found")
        job = job_query.data[0]

        brand_query = client.table("brands").select("*").eq("id", job["brand_id"]).execute()
        if not brand_query.data:
            raise HTTPException(status_code=404, detail="Brand not found for this scan job")
        brand = brand_query.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    if not request.known_facts:
        raise HTTPException(status_code=400, detail="known_facts must contain at least one fact")

    # 2. Run hallucination scan
    try:
        hallucinations = await scan_for_hallucinations(
            scan_job_id=str(scan_job_id),
            brand_name=brand["name"],
            brand_id=brand["id"],
            known_facts=request.known_facts,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hallucination scan failed: {str(e)}")

    return [HallucinationItem(**h) for h in hallucinations]


@router.get("/{scan_job_id}/citation-gaps", response_model=List[CitationGapItem])
async def citation_gap_analysis(
    scan_job_id: UUID,
    competitor_names: str = Query(..., description="Comma-separated competitor names"),
):
    """
    Runs citation gap analysis on existing scan results.
    Finds domains that cite competitors but not the main brand.
    Returns top 3 gaps and saves to the citation_gaps table.
    """
    client = get_supabase_client()

    # 1. Fetch scan job and brand info
    try:
        job_query = client.table("scan_jobs").select("*").eq("id", str(scan_job_id)).execute()
        if not job_query.data:
            raise HTTPException(status_code=404, detail="Scan job not found")
        job = job_query.data[0]

        brand_query = client.table("brands").select("*").eq("id", job["brand_id"]).execute()
        if not brand_query.data:
            raise HTTPException(status_code=404, detail="Brand not found for this scan job")
        brand = brand_query.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # Parse comma-separated competitor names
    competitors = [name.strip() for name in competitor_names.split(",") if name.strip()]
    if not competitors:
        raise HTTPException(status_code=400, detail="At least one competitor name is required")

    # 2. Run citation gap analysis
    try:
        gaps = await find_citation_gaps(
            scan_job_id=str(scan_job_id),
            brand_name=brand["name"],
            brand_id=brand["id"],
            competitor_names=competitors,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Citation gap analysis failed: {str(e)}")

    return [CitationGapItem(**g) for g in gaps]

# DONE - hooks.py

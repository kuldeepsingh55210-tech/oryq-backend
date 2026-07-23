import logging
from uuid import UUID
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status

from app.database import get_supabase_client
from app.entity.extractor import extract_entities_from_response, sync_brand_entities_with_scan
from app.entity.knowledge_graph import get_graph, add_entity
from app.entity.gaps import detect_entity_gaps

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entity", tags=["Entity Intelligence"])

class AddEntityRequest(BaseModel):
    entity_name: str
    entity_type: str  # product | person | differentiator | technology | award | location

async def ensure_entities_processed(scan_job_id: str) -> tuple[str, List[Dict[str, Any]]]:
    """
    Resolves scan job and brand_id, extracts entities from scan_results if needed,
    and returns (brand_id, brand_entities).
    """
    client = get_supabase_client()
    
    # 1. Fetch scan job
    job_query = client.table("scan_jobs").select("*").eq("id", scan_job_id).execute()
    if not job_query.data:
        raise HTTPException(status_code=404, detail="Scan job not found")
    job = job_query.data[0]
    brand_id = job.get("brand_id")

    if not brand_id:
        raise HTTPException(status_code=404, detail="Brand not associated with scan job")

    # 2. Fetch brand details
    b_query = client.table("brands").select("name").eq("id", brand_id).execute()
    brand_name = b_query.data[0].get("name", "Brand") if b_query.data else "Brand"

    # 3. Check existing brand entities
    ent_query = client.table("brand_entities").select("*").eq("brand_id", brand_id).execute()
    entities = ent_query.data or []

    # If no entities exist for brand, run extraction over scan results
    if not entities:
        results_query = client.table("scan_results").select("*").eq("scan_job_id", scan_job_id).execute()
        results = results_query.data or []
        
        all_extracted = []
        for r in results:
            text = r.get("response_text", "")
            ext = await extract_entities_from_response(text, brand_name, scan_job_id=scan_job_id)
            all_extracted.extend(ext)

        await sync_brand_entities_with_scan(
            brand_id=brand_id,
            scan_job_id=scan_job_id,
            extracted_entities=all_extracted,
            total_prompts=len(results)
        )

        ent_query = client.table("brand_entities").select("*").eq("brand_id", brand_id).execute()
        entities = ent_query.data or []

    return brand_id, entities

@router.get("/{scan_job_id}/overview")
async def get_entity_overview(scan_job_id: UUID):
    """
    Returns entity intelligence overview: coverage score, total entity count,
    AI-known count, and breakdown by entity type.
    """
    scan_id_str = str(scan_job_id)
    brand_id, entities = await ensure_entities_processed(scan_id_str)

    total_cnt = len(entities)
    known_cnt = sum(1 for e in entities if e.get("is_known_to_ai"))
    
    coverage_score = round((known_cnt / max(total_cnt, 1)) * 100, 1)

    by_type: Dict[str, Dict[str, int]] = {
        "product": {"total": 0, "known": 0},
        "person": {"total": 0, "known": 0},
        "differentiator": {"total": 0, "known": 0},
        "technology": {"total": 0, "known": 0},
        "award": {"total": 0, "known": 0},
        "location": {"total": 0, "known": 0}
    }

    for e in entities:
        etype = str(e.get("entity_type", "product")).lower()
        if etype not in by_type:
            by_type[etype] = {"total": 0, "known": 0}
        by_type[etype]["total"] += 1
        if e.get("is_known_to_ai"):
            by_type[etype]["known"] += 1

    return {
        "coverage_score": coverage_score,
        "total_entities": total_cnt,
        "known_to_ai": known_cnt,
        "by_type": by_type
    }

@router.get("/{scan_job_id}/graph")
async def get_entity_graph(scan_job_id: UUID):
    """
    Returns knowledge graph adjacency list (nodes + edges) formatted for D3 visualization.
    """
    scan_id_str = str(scan_job_id)
    brand_id, _ = await ensure_entities_processed(scan_id_str)
    graph_data = await get_graph(brand_id)
    return graph_data

@router.get("/{scan_job_id}/gaps")
async def get_entity_gaps(scan_job_id: UUID):
    """
    Returns entity gaps ranked by impact score with recommended fixes and effort level.
    """
    scan_id_str = str(scan_job_id)
    brand_id, _ = await ensure_entities_processed(scan_id_str)
    gaps = await detect_entity_gaps(brand_id)
    return gaps

@router.post("/{brand_id}/add", status_code=status.HTTP_201_CREATED)
async def add_manual_entity(brand_id: UUID, request: AddEntityRequest):
    """
    Manually registers a brand entity for tracking.
    """
    brand_id_str = str(brand_id)
    clean_type = request.entity_type.strip().lower()
    valid_types = {"product", "person", "differentiator", "technology", "award", "location"}
    if clean_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid entity_type. Must be one of {valid_types}")

    try:
        res = await add_entity(brand_id_str, request.entity_name, clean_type)
        return {
            "success": True,
            "entity": res
        }
    except Exception as e:
        logger.error(f"Error adding manual entity: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

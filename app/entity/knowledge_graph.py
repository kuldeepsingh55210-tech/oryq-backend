import logging
from typing import Dict, Any, List, Optional
from app.database import get_supabase_client

logger = logging.getLogger(__name__)

async def add_entity(brand_id: str, entity_name: str, entity_type: str) -> Dict[str, Any]:
    """
    Adds a new entity record for a brand in PostgreSQL database.
    """
    client = get_supabase_client()
    clean_name = entity_name.strip()
    clean_type = entity_type.strip().lower()

    # Check existing
    existing = client.table("brand_entities").select("*").eq("brand_id", brand_id).ilike("entity_name", clean_name).execute()
    if existing.data:
        return existing.data[0]

    record = {
        "brand_id": brand_id,
        "entity_name": clean_name,
        "entity_type": clean_type,
        "is_known_to_ai": False,
        "coverage_pct": 0.00
    }
    insert_res = client.table("brand_entities").insert(record).execute()
    if insert_res.data:
        return insert_res.data[0]
    raise Exception("Failed to insert brand entity record")

async def add_relationship(
    source_entity_id: str,
    target_entity_id: str,
    relationship_type: str = "relates_to",
    strength: float = 0.5
) -> Dict[str, Any]:
    """
    Creates or updates an edge in entity_relationships between source and target entity.
    """
    client = get_supabase_client()
    existing = (
        client.table("entity_relationships")
        .select("*")
        .eq("source_entity_id", source_entity_id)
        .eq("target_entity_id", target_entity_id)
        .execute()
    )
    if existing.data:
        return existing.data[0]

    record = {
        "source_entity_id": source_entity_id,
        "target_entity_id": target_entity_id,
        "relationship_type": relationship_type,
        "strength": round(max(0.0, min(1.0, strength)), 3)
    }
    insert_res = client.table("entity_relationships").insert(record).execute()
    if insert_res.data:
        return insert_res.data[0]
    raise Exception("Failed to insert entity relationship")

async def get_graph(brand_id: str) -> Dict[str, Any]:
    """
    Fetches nodes and edges for brand_id formatted for D3 graph visualization.
    """
    client = get_supabase_client()
    
    # Fetch nodes
    nodes_res = client.table("brand_entities").select("*").eq("brand_id", brand_id).execute()
    raw_nodes = nodes_res.data or []
    node_ids = {n["id"] for n in raw_nodes}

    nodes = [
        {
            "id": n["id"],
            "name": n["entity_name"],
            "type": n["entity_type"],
            "is_known": bool(n.get("is_known_to_ai", False)),
            "coverage_pct": float(n.get("coverage_pct") or 0.0)
        }
        for n in raw_nodes
    ]

    if not node_ids:
        return {"nodes": [], "edges": []}

    # Fetch edges matching nodes
    edges_res = client.table("entity_relationships").select("*").in_("source_entity_id", list(node_ids)).execute()
    raw_edges = edges_res.data or []

    edges = [
        {
            "source": e["source_entity_id"],
            "target": e["target_entity_id"],
            "relationship": e.get("relationship_type", "relates_to"),
            "strength": float(e.get("strength") or 0.5)
        }
        for e in raw_edges if e["target_entity_id"] in node_ids
    ]

    return {
        "nodes": nodes,
        "edges": edges
    }

async def get_connected_entities(entity_id: str) -> List[Dict[str, Any]]:
    """
    Returns all entities connected to the specified entity_id.
    """
    client = get_supabase_client()
    edges_res = (
        client.table("entity_relationships")
        .select("target_entity_id, relationship_type, strength")
        .eq("source_entity_id", entity_id)
        .execute()
    )
    return edges_res.data or []

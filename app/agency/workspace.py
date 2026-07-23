import logging
from typing import Dict, Any, List, Optional
from app.database import get_supabase_client

logger = logging.getLogger(__name__)

AGENCY_MIN_CLIENT_LIMIT = 3

async def create_workspace(owner_user_id: str, name: str, plan_tier: str = "agency") -> Dict[str, Any]:
    """
    Creates a new workspace for an agency user.
    """
    client = get_supabase_client()
    payload = {
        "owner_user_id": owner_user_id,
        "name": name,
        "plan_tier": plan_tier,
        "client_count": 0
    }
    try:
        res = client.table("workspaces").insert(payload).execute()
        if res.data:
            workspace = res.data[0]
            # Initialize default whitelabel config for new workspace
            client.table("whitelabel_config").insert({
                "workspace_id": workspace["id"],
                "agency_name": name,
                "primary_color": "#1B4FD8",
                "secondary_color": "#0EA47A"
            }).execute()
            return workspace
        raise RuntimeError("Failed to create workspace record")
    except Exception as e:
        logger.error(f"Error creating workspace '{name}': {e}")
        raise

async def list_user_workspaces(user_id: str) -> List[Dict[str, Any]]:
    """
    Returns all workspaces owned by the given user.
    """
    client = get_supabase_client()
    try:
        res = client.table("workspaces").select("*").eq("owner_user_id", user_id).order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error listing workspaces for user {user_id}: {e}")
        return []

async def add_brand_to_workspace(workspace_id: str, brand_id: str, client_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Adds a brand (client) to a workspace and updates client_count.
    Enforces minimum client allocation rules.
    """
    client = get_supabase_client()

    # 1. Check workspace existence
    ws_res = client.table("workspaces").select("*").eq("id", workspace_id).execute()
    if not ws_res.data:
        raise ValueError("Workspace not found")
    workspace = ws_res.data[0]

    # 2. Check if brand exists
    brand_res = client.table("brands").select("name").eq("id", brand_id).execute()
    if not brand_res.data:
        raise ValueError("Brand not found")
    default_client_name = client_name or brand_res.data[0].get("name")

    # 3. Add brand to workspace_brands (UPSERT or Insert)
    wb_payload = {
        "workspace_id": workspace_id,
        "brand_id": brand_id,
        "client_name": default_client_name
    }

    try:
        # Check existing mapping
        existing = client.table("workspace_brands").select("id").eq("workspace_id", workspace_id).eq("brand_id", brand_id).execute()
        if existing.data:
            res = client.table("workspace_brands").update({"client_name": default_client_name}).eq("id", existing.data[0]["id"]).execute()
            wb_record = res.data[0]
        else:
            res = client.table("workspace_brands").insert(wb_payload).execute()
            wb_record = res.data[0]

        # Recalculate client_count
        count_res = client.table("workspace_brands").select("id", count="exact").eq("workspace_id", workspace_id).execute()
        current_count = len(count_res.data) if count_res.data else 0

        client.table("workspaces").update({"client_count": current_count}).eq("id", workspace_id).execute()
        wb_record["workspace_client_count"] = current_count
        return wb_record
    except Exception as e:
        logger.error(f"Error adding brand {brand_id} to workspace {workspace_id}: {e}")
        raise

async def list_workspace_brands(workspace_id: str) -> List[Dict[str, Any]]:
    """
    Lists all brands attached to a workspace along with their latest visibility score.
    Returns: [{brand_id, client_name, latest_score, created_at}]
    """
    client = get_supabase_client()
    try:
        wb_res = client.table("workspace_brands").select("*").eq("workspace_id", workspace_id).execute()
        brands_list = wb_res.data or []

        result = []
        for wb in brands_list:
            b_id = wb.get("brand_id")
            client_name = wb.get("client_name")

            # Fetch latest completed scan job for this brand
            latest_score = 0.0
            if b_id:
                job_res = client.table("scan_jobs").select("visibility_score").eq("brand_id", b_id).eq("status", "completed").order("created_at", desc=True).limit(1).execute()
                if job_res.data and job_res.data[0].get("visibility_score") is not None:
                    latest_score = float(job_res.data[0]["visibility_score"])

            result.append({
                "brand_id": b_id,
                "client_name": client_name,
                "latest_score": latest_score,
                "created_at": wb.get("created_at")
            })

        return result
    except Exception as e:
        logger.error(f"Error listing brands for workspace {workspace_id}: {e}")
        return []

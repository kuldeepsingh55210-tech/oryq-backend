import logging
from typing import Dict, Any, Optional
from app.database import get_supabase_client

logger = logging.getLogger(__name__)

DEFAULT_WHITELABEL_CONFIG = {
    "agency_name": "ORYQ Partner Agency",
    "logo_url": None,
    "primary_color": "#1B4FD8",
    "secondary_color": "#0EA47A",
    "report_footer": "Confidential Executive Report — Powered by ORYQ Intelligence Engine"
}

async def get_whitelabel_config(workspace_id: str) -> Dict[str, Any]:
    """
    Fetches the white-label branding configuration for a specific workspace.
    Returns defaults if not explicitly configured.
    """
    client = get_supabase_client()
    try:
        res = client.table("whitelabel_config").select("*").eq("workspace_id", workspace_id).execute()
        if res.data and len(res.data) > 0:
            cfg = res.data[0]
            # Merge with defaults for missing fields
            return {
                "id": cfg.get("id"),
                "workspace_id": workspace_id,
                "agency_name": cfg.get("agency_name") or DEFAULT_WHITELABEL_CONFIG["agency_name"],
                "logo_url": cfg.get("logo_url"),
                "primary_color": cfg.get("primary_color") or DEFAULT_WHITELABEL_CONFIG["primary_color"],
                "secondary_color": cfg.get("secondary_color") or DEFAULT_WHITELABEL_CONFIG["secondary_color"],
                "report_footer": cfg.get("report_footer") or DEFAULT_WHITELABEL_CONFIG["report_footer"],
                "created_at": cfg.get("created_at")
            }
    except Exception as e:
        logger.error(f"Error fetching whitelabel config for workspace {workspace_id}: {e}")

    return {
        "workspace_id": workspace_id,
        **DEFAULT_WHITELABEL_CONFIG
    }

async def update_whitelabel_config(
    workspace_id: str,
    agency_name: Optional[str] = None,
    logo_url: Optional[str] = None,
    primary_color: Optional[str] = None,
    secondary_color: Optional[str] = None,
    report_footer: Optional[str] = None
) -> Dict[str, Any]:
    """
    Updates or inserts white-label branding configuration for a workspace.
    """
    client = get_supabase_client()

    update_fields = {}
    if agency_name is not None:
        update_fields["agency_name"] = agency_name
    if logo_url is not None:
        update_fields["logo_url"] = logo_url
    if primary_color is not None:
        update_fields["primary_color"] = primary_color
    if secondary_color is not None:
        update_fields["secondary_color"] = secondary_color
    if report_footer is not None:
        update_fields["report_footer"] = report_footer

    try:
        existing = client.table("whitelabel_config").select("id").eq("workspace_id", workspace_id).execute()
        if existing.data:
            res = client.table("whitelabel_config").update(update_fields).eq("workspace_id", workspace_id).execute()
            return res.data[0] if res.data else update_fields
        else:
            payload = {"workspace_id": workspace_id, **update_fields}
            res = client.table("whitelabel_config").insert(payload).execute()
            return res.data[0] if res.data else payload
    except Exception as e:
        logger.error(f"Error updating whitelabel config for workspace {workspace_id}: {e}")
        raise

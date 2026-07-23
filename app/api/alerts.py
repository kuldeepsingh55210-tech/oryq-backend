import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query, Depends, status

from app.database import get_supabase_client
from app.auth.middleware import get_current_user
from app.alerts.slack import test_slack_webhook

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/alerts", tags=["Advanced Alerts"])

class AlertSettingPayload(BaseModel):
    alert_type: str  # visibility_drop | competitor_surge | hallucination_detected | budget_cap
    enabled: bool = True
    threshold_pct: Optional[float] = None
    channels: Optional[List[str]] = ["email"]
    slack_webhook_url: Optional[str] = None
    custom_webhook_url: Optional[str] = None

class TestSlackPayload(BaseModel):
    webhook_url: str
    brand_name: Optional[str] = "Demo Brand"

@router.get("/{brand_id}")
async def get_brand_alerts(
    brand_id: str,
    alert_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    dismissed: Optional[bool] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Returns list of alerts (last 50) for a brand with optional filtering by type, severity, and dismissed status.
    """
    client = get_supabase_client()
    try:
        query = client.table("alerts").select("*").eq("brand_id", brand_id).order("created_at", desc=True).limit(50)
        if alert_type:
            query = query.eq("alert_type", alert_type)
        if severity:
            query = query.eq("severity", severity)
        
        res = query.execute()
        alerts = res.data or []

        # Apply dismissed filter in memory or query if provided
        if dismissed is not None:
            if dismissed:
                alerts = [a for a in alerts if a.get("dismissed_at") is not None]
            else:
                alerts = [a for a in alerts if a.get("dismissed_at") is None]

        return alerts
    except Exception as e:
        logger.error(f"Error fetching alerts for brand {brand_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch alerts")

@router.get("/{brand_id}/settings")
async def get_brand_alert_settings(
    brand_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Returns all alert settings configured for a brand.
    """
    client = get_supabase_client()
    try:
        res = client.table("alert_settings").select("*").eq("brand_id", brand_id).execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error fetching alert settings for brand {brand_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch alert settings")

@router.post("/{brand_id}/settings")
async def save_brand_alert_setting(
    brand_id: str,
    payload: AlertSettingPayload,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Creates or updates (UPSERT) alert settings for a specific brand and alert_type.
    """
    client = get_supabase_client()

    record = {
        "brand_id": brand_id,
        "alert_type": payload.alert_type,
        "enabled": payload.enabled,
        "threshold_pct": payload.threshold_pct,
        "channels": payload.channels or ["email"],
        "slack_webhook_url": payload.slack_webhook_url,
        "custom_webhook_url": payload.custom_webhook_url
    }

    try:
        existing = client.table("alert_settings").select("id").eq("brand_id", brand_id).eq("alert_type", payload.alert_type).execute()
        if existing.data and len(existing.data) > 0:
            upd_res = client.table("alert_settings").update(record).eq("id", existing.data[0]["id"]).execute()
            return upd_res.data[0] if upd_res.data else record
        else:
            ins_res = client.table("alert_settings").insert(record).execute()
            return ins_res.data[0] if ins_res.data else record
    except Exception as e:
        logger.error(f"Error saving alert setting for brand {brand_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save alert setting")

@router.patch("/{id}/dismiss")
async def dismiss_alert(
    id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Marks an alert as dismissed by setting dismissed_at timestamp.
    """
    client = get_supabase_client()
    now_utc = datetime.now(timezone.utc).isoformat()
    try:
        res = client.table("alerts").update({"dismissed_at": now_utc}).eq("id", id).execute()
        if not res.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error dismissing alert {id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to dismiss alert")

@router.post("/test/slack")
async def test_slack(
    payload: TestSlackPayload,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Dispatches a test message to the provided Slack webhook URL.
    """
    try:
        success = await test_slack_webhook(payload.webhook_url, payload.brand_name or "Demo Brand")
        return {"success": success, "message": "Test Slack message dispatched" if success else "Failed to deliver Slack message"}
    except Exception as e:
        logger.error(f"Error testing Slack webhook: {e}")
        return {"success": False, "error": str(e)}

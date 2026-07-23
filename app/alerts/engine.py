import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from app.database import get_supabase_client
from app.alerts.slack import send_slack_alert
from app.alerts.webhook import send_custom_webhook_alert
from app.alerts.email_alerts import send_email_alert

logger = logging.getLogger(__name__)

DEFAULT_ALERT_THRESHOLDS = {
    "visibility_drop": 10.0,      # score drops > 10%
    "competitor_surge": 15.0,    # competitor gains > 15%
    "hallucination_detected": 0.0, # trigger immediately
    "budget_cap": 80.0           # cost > 80% of budget
}

async def is_alert_deduplicated(brand_id: str, alert_type: str) -> bool:
    """
    Checks if an alert of the specified type has already been generated for this brand in the past 24 hours.
    """
    client = get_supabase_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    try:
        res = client.table("alerts").select("id").eq("brand_id", brand_id).eq("alert_type", alert_type).gte("created_at", cutoff).execute()
        if res.data and len(res.data) > 0:
            return True
    except Exception as e:
        logger.error(f"Error checking alert deduplication: {e}")
    return False

async def dispatch_alert(
    brand_id: str,
    alert_type: str,
    severity: str,
    title: str,
    body: str,
    data_json: Dict[str, Any],
    channels: List[str],
    slack_webhook_url: Optional[str] = None,
    custom_webhook_url: Optional[str] = None,
    recipient_email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Persists alert to DB and dispatches notification across configured delivery channels.
    """
    client = get_supabase_client()

    # 1. Fetch brand name
    brand_name = "Brand"
    try:
        b_res = client.table("brands").select("name").eq("id", brand_id).execute()
        if b_res.data:
            brand_name = b_res.data[0].get("name", "Brand")
    except Exception:
        pass

    now_utc = datetime.now(timezone.utc).isoformat()

    # 2. Insert record into `alerts` table
    alert_record = {
        "brand_id": brand_id,
        "alert_type": alert_type,
        "severity": severity,
        "title": title,
        "body": body,
        "data_json": data_json,
        "delivered_at": now_utc
    }

    try:
        ins_res = client.table("alerts").insert(alert_record).execute()
        if ins_res.data:
            alert_record["id"] = ins_res.data[0]["id"]
    except Exception as e:
        logger.error(f"Error inserting alert record: {e}")

    dispatch_payload = {
        "brand_id": brand_id,
        "brand_name": brand_name,
        "alert_type": alert_type,
        "severity": severity,
        "title": title,
        "body": body,
        "data_json": data_json
    }

    # 3. Deliver via enabled channels
    for ch in channels:
        ch_lower = ch.lower().strip()
        if ch_lower == "slack" and slack_webhook_url:
            await send_slack_alert(slack_webhook_url, dispatch_payload)
        elif ch_lower == "webhook" and custom_webhook_url:
            await send_custom_webhook_alert(custom_webhook_url, dispatch_payload)
        elif ch_lower == "email" and recipient_email:
            await send_email_alert(
                to_email=recipient_email,
                brand_name=brand_name,
                alert_title=title,
                body=body,
                severity=severity,
                data_json=data_json
            )

    return alert_record

async def evaluate_scan_alerts(scan_job_id: str, recipient_email: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Evaluates scan job results against alert thresholds after a scan completes.
    Checks visibility_drop, competitor_surge, hallucination_detected, and budget_cap.
    """
    client = get_supabase_client()

    # 1. Fetch current scan job details
    job_res = client.table("scan_jobs").select("*").eq("id", scan_job_id).execute()
    if not job_res.data:
        return []
    job = job_res.data[0]
    brand_id = job.get("brand_id")
    if not brand_id:
        return []

    current_score = float(job.get("visibility_score") or 0.0)
    current_cost = float(job.get("total_cost_usd") or 0.0)

    # 2. Fetch alert settings for this brand
    settings_res = client.table("alert_settings").select("*").eq("brand_id", brand_id).execute()
    configs = {cfg["alert_type"]: cfg for cfg in (settings_res.data or [])}

    generated_alerts = []

    # 3. Fetch previous completed scan job for threshold comparison
    prev_job_res = client.table("scan_jobs").select("*").eq("brand_id", brand_id).eq("status", "completed").neq("id", scan_job_id).order("created_at", desc=True).limit(1).execute()
    prev_score = float(prev_job_res.data[0].get("visibility_score") or 0.0) if prev_job_res.data else None

    # --- ALERT TYPE 1: VISIBILITY DROP ---
    vis_cfg = configs.get("visibility_drop", {"enabled": True, "threshold_pct": 10.0, "channels": ["email"]})
    if vis_cfg.get("enabled", True) and prev_score is not None and prev_score > 0:
        threshold = float(vis_cfg.get("threshold_pct") or 10.0)
        drop_pct = ((prev_score - current_score) / prev_score) * 100.0
        if drop_pct >= threshold:
            if not await is_alert_deduplicated(brand_id, "visibility_drop"):
                alert = await dispatch_alert(
                    brand_id=brand_id,
                    alert_type="visibility_drop",
                    severity="high",
                    title="Significant Visibility Drop Detected",
                    body=f"Your visibility score dropped by {drop_pct:.1f}% (from {prev_score:.1f} to {current_score:.1f}), breaching your {threshold}% threshold.",
                    data_json={"previous_score": prev_score, "current_score": current_score, "drop_pct": drop_pct},
                    channels=vis_cfg.get("channels", ["email"]),
                    slack_webhook_url=vis_cfg.get("slack_webhook_url"),
                    custom_webhook_url=vis_cfg.get("custom_webhook_url"),
                    recipient_email=recipient_email
                )
                generated_alerts.append(alert)

    # --- ALERT TYPE 2: HALLUCINATION DETECTED ---
    hal_cfg = configs.get("hallucination_detected", {"enabled": True, "threshold_pct": 0.0, "channels": ["email"]})
    if hal_cfg.get("enabled", True):
        # Query sentiment_results or hallucinations table for scan
        hal_res = client.table("sentiment_results").select("*").eq("scan_job_id", scan_job_id).eq("has_hallucination", True).execute()
        if hal_res.data and len(hal_res.data) > 0:
            if not await is_alert_deduplicated(brand_id, "hallucination_detected"):
                count = len(hal_res.data)
                sample_claim = hal_res.data[0].get("hallucination_text") or "False claim identified"
                alert = await dispatch_alert(
                    brand_id=brand_id,
                    alert_type="hallucination_detected",
                    severity="critical",
                    title="LLM Hallucination Detected",
                    body=f"Detected {count} hallucinated claim(s) in AI responses. Sample claim: '{sample_claim[:120]}...'",
                    data_json={"hallucination_count": count, "sample": sample_claim},
                    channels=hal_cfg.get("channels", ["email"]),
                    slack_webhook_url=hal_cfg.get("slack_webhook_url"),
                    custom_webhook_url=hal_cfg.get("custom_webhook_url"),
                    recipient_email=recipient_email
                )
                generated_alerts.append(alert)

    # --- ALERT TYPE 3: BUDGET CAP ---
    bud_cfg = configs.get("budget_cap", {"enabled": True, "threshold_pct": 80.0, "channels": ["email"]})
    if bud_cfg.get("enabled", True):
        threshold_cap = float(bud_cfg.get("threshold_pct") or 80.0)
        # Default monthly budget target $50.00
        monthly_limit = 50.0
        pct_used = (current_cost / monthly_limit) * 100.0
        if pct_used >= threshold_cap:
            if not await is_alert_deduplicated(brand_id, "budget_cap"):
                alert = await dispatch_alert(
                    brand_id=brand_id,
                    alert_type="budget_cap",
                    severity="medium",
                    title="Scan Budget Threshold Approached",
                    body=f"Scan job expenditure reached ${current_cost:.4f} ({pct_used:.1f}% of target limit).",
                    data_json={"current_cost": current_cost, "pct_used": pct_used},
                    channels=bud_cfg.get("channels", ["email"]),
                    slack_webhook_url=bud_cfg.get("slack_webhook_url"),
                    custom_webhook_url=bud_cfg.get("custom_webhook_url"),
                    recipient_email=recipient_email
                )
                generated_alerts.append(alert)

    return generated_alerts

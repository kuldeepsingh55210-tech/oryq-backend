import logging
import httpx
from typing import Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

async def send_slack_alert(webhook_url: str, alert_data: Dict[str, Any]) -> bool:
    """
    Sends a formatted Slack Block Kit message to a Slack Webhook URL.
    """
    if not webhook_url or not webhook_url.startswith("https://hooks.slack.com/"):
        logger.warning(f"Invalid Slack webhook URL: {webhook_url}")
        return False

    brand_name = alert_data.get("brand_name", "Brand")
    alert_type = alert_data.get("alert_type", "Notification").replace("_", " ").upper()
    title = alert_data.get("title", "ORYQ Alert")
    body = alert_data.get("body", "")
    severity = alert_data.get("severity", "medium").upper()
    dashboard_url = alert_data.get("dashboard_url", f"{settings.FRONTEND_URL}/dashboard")

    severity_emoji = "🔴" if severity == "CRITICAL" or severity == "HIGH" else "⚠️"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{severity_emoji} ORYQ Alert: {title}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Brand:* {brand_name}"},
                {"type": "mrkdwn", "text": f"*Alert Type:* {alert_type}"},
                {"type": "mrkdwn", "text": f"*Severity:* {severity}"}
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": body
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View in Dashboard 🚀",
                        "emoji": True
                    },
                    "url": dashboard_url,
                    "style": "primary"
                }
            ]
        }
    ]

    payload = {"blocks": blocks}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=payload)
            if resp.status_code == 200:
                logger.info(f"Slack alert successfully dispatched to {brand_name}")
                return True
            else:
                logger.error(f"Slack webhook returned non-200 status {resp.status_code}: {resp.text}")
                return False
    except Exception as e:
        logger.error(f"Failed to send Slack alert to {webhook_url}: {e}")
        return False

async def test_slack_webhook(webhook_url: str, brand_name: str = "Demo Brand") -> bool:
    """
    Sends a test Slack message to verify webhook integration.
    """
    test_data = {
        "brand_name": brand_name,
        "alert_type": "test_connection",
        "title": f"Webhook Test Connection for {brand_name}",
        "body": "Congratulations! Your ORYQ Slack alert webhook is configured and working properly.",
        "severity": "low"
    }
    return await send_slack_alert(webhook_url, test_data)

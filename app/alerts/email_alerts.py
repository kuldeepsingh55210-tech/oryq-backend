import logging
import resend
from typing import Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

async def send_email_alert(
    to_email: str,
    brand_name: str,
    alert_title: str,
    body: str,
    severity: str = "medium",
    data_json: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """
    Sends an email alert notification via Resend with styled HTML template and dashboard CTA.
    """
    if not settings.RESEND_API_KEY:
        err = "RESEND_API_KEY is not configured on the server."
        logger.warning(err)
        return {"success": False, "error": err}

    resend.api_key = settings.RESEND_API_KEY

    # Severity accent color
    sev_color = "#dc2626" if severity.lower() in ["high", "critical"] else "#d97706"
    dashboard_url = f"{settings.FRONTEND_URL}/dashboard"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>ORYQ Alert: {alert_title}</title>
</head>
<body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 40px; color: #1e293b;">
  <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
    
    <!-- Header -->
    <div style="border-bottom: 2px solid {sev_color}; padding-bottom: 16px; margin-bottom: 24px;">
      <h2 style="margin: 0; font-size: 20px; color: #0f172a; font-weight: 700;">
        <span style="color: #3b82f6;">ORYQ Alert</span> &mdash; {alert_title}
      </h2>
      <p style="margin: 6px 0 0 0; font-size: 13px; color: #64748b;">
        Brand: <strong>{brand_name}</strong> | Severity: <strong style="color: {sev_color};">{severity.upper()}</strong>
      </p>
    </div>

    <!-- Alert Body -->
    <div style="background-color: #f1f5f9; padding: 20px; border-radius: 12px; margin-bottom: 24px;">
      <p style="margin: 0; font-size: 15px; line-height: 1.6; color: #334155;">
        {body}
      </p>
    </div>

    <!-- Call to Action -->
    <div style="text-align: center; margin-top: 32px;">
      <a href="{dashboard_url}" style="background-color: #1b4fd8; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
        Open ORYQ Dashboard
      </a>
    </div>

    <div style="margin-top: 32px; padding-top: 16px; border-top: 1px solid #e2e8f0; text-align: center; font-size: 12px; color: #94a3b8;">
      This is an automated notification from ORYQ Intelligence System.
    </div>
  </div>
</body>
</html>
"""

    try:
        params = {
            "from": settings.FROM_EMAIL,
            "to": [to_email],
            "subject": f"[{severity.upper()}] ORYQ Alert for {brand_name}: {alert_title}",
            "html": html_content,
        }
        response = resend.Emails.send(params)
        logger.info(f"Email alert sent successfully to {to_email}: {response}")
        return {"success": True, "resend_id": getattr(response, "id", None)}
    except Exception as e:
        logger.error(f"Failed to send email alert to {to_email}: {e}")
        return {"success": False, "error": str(e)}

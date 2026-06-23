import base64
import logging
import resend
from app.config import settings

logger = logging.getLogger(__name__)

async def send_scan_report_email(
    to_email: str,
    brand_name: str,
    score: float,
    brand_mentioned_count: int,
    total_prompts_run: int,
    scan_job_id: str,
    dashboard_url: str,
    pdf_bytes: bytes | None = None
) -> dict:
    """
    Sends a branded scan report email to the user using Resend.com.
    Optionally attaches the scan report PDF.
    """
    if not settings.RESEND_API_KEY:
        err = "RESEND_API_KEY is not configured on the server."
        logger.warning(err)
        return {"success": False, "error": err}

    # Color code score
    if score >= 70:
        score_color = "#16a34a"  # Green
    elif score >= 40:
        score_color = "#d97706"  # Amber
    else:
        score_color = "#dc2626"  # Red

    score_str = f"{int(score)}" if isinstance(score, (int, float)) and score.is_integer() else f"{score:.1f}"

    # Build HTML body with inline styling
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Your AI Visibility Report</title>
</head>
<body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 40px; color: #1e293b;">
  <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
    <!-- Header -->
    <div style="border-bottom: 1px solid #e2e8f0; padding-bottom: 20px; margin-bottom: 24px;">
      <h2 style="margin: 0; font-size: 20px; color: #0f172a; font-weight: 700;">
        <span style="color: #3b82f6;">ORYQ</span> &mdash; Your AI Visibility Report is Ready
      </h2>
    </div>
    
    <!-- Score Display -->
    <div style="text-align: center; margin-bottom: 32px; padding: 24px; background-color: #f1f5f9; border-radius: 12px;">
      <p style="margin: 0 0 8px 0; font-size: 10px; font-weight: 800; color: #64748b; letter-spacing: 0.05em; text-transform: uppercase;">Visibility Score</p>
      <div style="color: {score_color}; font-size: 48px; font-weight: bold; line-height: 1;">
        {score_str}/100
      </div>
      <p style="margin: 16px 0 0 0; font-size: 14px; color: #334155; line-height: 1.5;">
        <strong>{brand_mentioned_count} out of {total_prompts_run}</strong> AI responses mentioned <strong>{brand_name}</strong>.
      </p>
    </div>
    
    <!-- CTA Button -->
    <div style="text-align: center; margin-bottom: 32px;">
      <a href="{dashboard_url}" target="_blank" style="display: inline-block; background-color: #3b82f6; color: #ffffff; text-decoration: none; padding: 12px 24px; font-size: 14px; font-weight: 600; border-radius: 8px; box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);">
        View Full Dashboard
      </a>
    </div>
    
    <!-- Footer -->
    <div style="border-top: 1px solid #e2e8f0; padding-top: 20px; text-align: center; font-size: 12px; color: #64748b;">
      <p style="margin: 0 0 4px 0;">Sent by <strong>ORYQ</strong> &mdash; AI Visibility Intelligence</p>
      <p style="margin: 0;">Evaluating how top AI models perceive your brand.</p>
    </div>
  </div>
</body>
</html>
"""

    attachments = []
    if pdf_bytes:
        # Encode bytes to base64 string
        base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        attachments.append({
            "filename": f"oryq-report-{brand_name.lower().replace(' ', '-')}.pdf",
            "content": base64_pdf
        })

    try:
        resend.api_key = settings.RESEND_API_KEY
        
        email_params = {
            "from": settings.FROM_EMAIL,
            "to": to_email,
            "subject": f"Your AI Visibility Score for {brand_name}: {score_str}/100",
            "html": html_content,
        }
        
        if attachments:
            email_params["attachments"] = attachments
            
        # Send email via Resend SDK
        response = resend.Emails.send(email_params)
        logger.info(f"Email sent successfully: {response}")
        return {"success": True, "error": None}
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to send email via Resend: {error_msg}", exc_info=True)
        return {"success": False, "error": error_msg}

import io
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.database import get_supabase_client
from app.agency.whitelabel import get_whitelabel_config
from app.reports.pdf_generator import escape_for_paragraph

logger = logging.getLogger(__name__)

def draw_whitelabel_footer(canvas, doc, footer_text: str, primary_color_hex: str):
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    try:
        canvas.setFillColor(colors.HexColor(primary_color_hex))
    except Exception:
        canvas.setFillColor(colors.HexColor("#1B4FD8"))
    
    # Left aligned custom agency footer
    canvas.drawString(54, 36, footer_text[:80])
    
    # Right aligned page number
    page_num = f"Page {doc.page}"
    canvas.drawRightString(doc.pagesize[0] - 54, 36, page_num)
    canvas.restoreState()

async def generate_whitelabel_pdf(workspace_id: str, brand_id: str) -> bytes:
    """
    Generates a white-labeled PDF scan report for a brand using workspace branding config.
    """
    client = get_supabase_client()

    # 1. Fetch whitelabel configuration
    whitelabel = await get_whitelabel_config(workspace_id)
    agency_name = whitelabel.get("agency_name", "Agency Partner")
    primary_color_hex = whitelabel.get("primary_color", "#1B4FD8")
    secondary_color_hex = whitelabel.get("secondary_color", "#0EA47A")
    footer_text = whitelabel.get("report_footer", f"Report by {agency_name}")

    try:
        primary_col = colors.HexColor(primary_color_hex)
    except Exception:
        primary_col = colors.HexColor("#1B4FD8")

    try:
        secondary_col = colors.HexColor(secondary_color_hex)
    except Exception:
        secondary_col = colors.HexColor("#0EA47A")

    # 2. Fetch Brand Info
    brand_res = client.table("brands").select("*").eq("id", brand_id).execute()
    if not brand_res.data:
        raise ValueError("Brand not found")
    brand = brand_res.data[0]
    brand_name = brand.get("name", "Client Brand")
    website_url = brand.get("website_url", "N/A")

    # 3. Fetch Latest Completed Scan Job for Brand
    job_res = client.table("scan_jobs").select("*").eq("brand_id", brand_id).eq("status", "completed").order("created_at", desc=True).limit(1).execute()
    
    score = 0.0
    total_prompts = 0
    completed_prompts = 0
    scan_date = datetime.now(timezone.utc).strftime("%B %d, %Y")
    scan_job_id = None

    if job_res.data:
        job = job_res.data[0]
        scan_job_id = job.get("id")
        score = float(job.get("visibility_score") or 0.0)
        total_prompts = job.get("total_prompts", 0)
        completed_prompts = job.get("completed_prompts", 0)
        if job.get("completed_at"):
            try:
                dt = datetime.fromisoformat(job["completed_at"].replace("Z", "+00:00"))
                scan_date = dt.strftime("%B %d, %Y")
            except Exception:
                pass

    # 4. Fetch Scan Results
    results = []
    brand_mentioned_count = 0
    if scan_job_id:
        r_res = client.table("scan_results").select("*").eq("scan_job_id", scan_job_id).execute()
        results = r_res.data or []
        brand_mentioned_count = sum(1 for r in results if r.get("brand_mentioned"))

    # 5. ReportLab Document Construction
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    agency_header_style = ParagraphStyle(
        'AgencyHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=primary_col
    )

    sub_header_style = ParagraphStyle(
        'SubHeader',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#475569")
    )

    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=primary_col,
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155")
    )

    story = []

    # Header section
    story.append(Paragraph(escape_for_paragraph(f"{agency_name.upper()} — AI Visibility Audit"), agency_header_style))
    story.append(Spacer(1, 4))
    sub_text = f"<b>Client Brand:</b> {escape_for_paragraph(brand_name)} &nbsp;|&nbsp; <b>Website:</b> {escape_for_paragraph(website_url)} &nbsp;|&nbsp; <b>Audit Date:</b> {scan_date}"
    story.append(Paragraph(sub_text, sub_header_style))
    story.append(Spacer(1, 10))

    # Divider line using primary agency color
    line_table = Table([['']], colWidths=[504])
    line_table.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), 2, primary_col),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(line_table)
    story.append(Spacer(1, 15))

    # Score Box
    score_p_style = ParagraphStyle(
        'ScoreP', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=26, leading=30, alignment=TA_CENTER, textColor=primary_col
    )
    score_lbl_style = ParagraphStyle(
        'ScoreLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=TA_CENTER, textColor=secondary_col
    )

    score_p = Paragraph(f"{int(score)}/100", score_p_style)
    score_lbl = Paragraph("VISIBILITY SCORE", score_lbl_style)

    score_box = Table([[score_p], [score_lbl]], colWidths=[140])
    score_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1.5, secondary_col),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))

    summary_text = (
        f"<b>Executive Summary for {escape_for_paragraph(brand_name)}</b><br/><br/>"
        f"During this audit, <b>{brand_mentioned_count} out of {total_prompts or len(results)}</b> benchmark AI prompts "
        f"generated a direct brand mention. Your AI visibility score is calculated at <b>{score:.1f}/100</b>.<br/><br/>"
        f"Prepared exclusively by <b>{escape_for_paragraph(agency_name)}</b>."
    )
    summary_p = Paragraph(summary_text, body_style)

    summary_table = Table([[score_box, summary_p]], colWidths=[150, 354])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (1,0), (1,0), 12),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))

    # Audit Results Table
    story.append(Paragraph("Detailed Prompt Audit Breakdown", heading_style))
    story.append(Spacer(1, 6))

    table_data = [
        [Paragraph("<b>Prompt Category / Text</b>", body_style), Paragraph("<b>Provider</b>", body_style), Paragraph("<b>Status</b>", body_style)]
    ]

    for r in results[:15]:
        p_text = r.get("prompt_text", "Prompt")
        provider = r.get("provider", "LLM").upper()
        mentioned = r.get("brand_mentioned", False)
        status_str = "<font color='#16a34a'><b>MENTIONED</b></font>" if mentioned else "<font color='#dc2626'>MISSED</font>"

        table_data.append([
            Paragraph(escape_for_paragraph(p_text[:75] + ("..." if len(p_text)>75 else "")), body_style),
            Paragraph(provider, body_style),
            Paragraph(status_str, body_style)
        ])

    if len(table_data) == 1:
        table_data.append([Paragraph("No prompt data recorded.", body_style), Paragraph("-", body_style), Paragraph("-", body_style)])

    res_table = Table(table_data, colWidths=[320, 94, 90])
    res_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(res_table)

    def on_page(canvas, document):
        draw_whitelabel_footer(canvas, document, footer_text, primary_color_hex)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    buffer.seek(0)
    return buffer.getvalue()

import asyncio
from uuid import UUID
from app.reports.pdf_generator import generate_scan_pdf
from app.api.scan import fetch_scan_details
from app.scanner.scorer import compute_score
from app.recommendations import generate_recommendations
from app.database import get_supabase_client

async def main():
    scan_job_id = UUID('7d78482b-caec-4cff-8df2-234f6cf46c6a')
    details = await fetch_scan_details(scan_job_id)
    job = details["job"]
    brand = details["brand"]
    results_db = details["results"]
    hallucinations_db = details["hallucinations"]

    brand_name = brand.get("name", "Unknown")
    website_url = brand.get("website_url", "Unknown")
    industry = brand.get("industry") or "general"

    overall_score, breakdown = compute_score(results_db)
    total_prompts_run = len(results_db)
    brand_mentioned_count = sum(1 for r in results_db if r.get("brand_mentioned"))

    results_summary = [
        {
            "provider": p,
            "score": data["score"],
            "mentions": data["mentions"],
            "total": data["total"]
        }
        for p, data in breakdown.items() if data["total"] > 0
    ]

    competitor_data = None

    client = get_supabase_client()
    missed_query = (
        client.table("scan_results")
        .select("*")
        .eq("scan_job_id", str(scan_job_id))
        .eq("brand_mentioned", False)
        .order("created_at")
        .limit(5)
        .execute()
    )
    missed_prompts = missed_query.data or []

    recommendations = await generate_recommendations(
        brand_name=brand_name,
        industry=industry,
        score=overall_score,
        hallucinations=hallucinations_db,
        scan_job_id=scan_job_id
    )

    created_at_str = job.get("created_at")
    scan_date = "N/A"
    if created_at_str:
        from datetime import datetime
        dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        scan_date = dt.strftime("%B %d, %Y")

    pdf_bytes = generate_scan_pdf(
        brand_name=brand_name,
        website_url=website_url,
        score=overall_score,
        total_prompts_run=total_prompts_run,
        brand_mentioned_count=brand_mentioned_count,
        results_summary=results_summary,
        competitor_data=competitor_data,
        hallucinations=hallucinations_db,
        scan_date=scan_date,
        missed_prompts=missed_prompts,
        recommendations=recommendations
    )

    with open("test_report.pdf", "wb") as f:
        f.write(pdf_bytes)
    print("PDF written successfully!")

if __name__ == "__main__":
    asyncio.run(main())

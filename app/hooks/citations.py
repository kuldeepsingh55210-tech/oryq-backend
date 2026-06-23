"""
Citation Gap Finder Hook — Phase 2 Feature 3

Analyzes scan results to find domains/sources that cite competitors
but not the main brand, revealing SEO/visibility gaps.
"""

import re
import logging
from typing import List, Dict, Optional
from urllib.parse import urlparse

from app.database import get_supabase_client

logger = logging.getLogger(__name__)

# Regex to extract URLs from text
URL_PATTERN = re.compile(r'https?://[^\s\)\]\,\"\']+', re.IGNORECASE)


def extract_urls(text: str) -> List[str]:
    """
    Extracts all URLs from text using regex.
    Cleans trailing punctuation (periods, commas, parentheses).
    """
    if not text:
        return []

    raw_urls = URL_PATTERN.findall(text)
    cleaned = []
    for url in raw_urls:
        # Strip trailing punctuation that regex might capture
        url = url.rstrip(".,;:!?)>]}")
        if url and len(url) > 10:  # Minimum plausible URL length
            cleaned.append(url)
    return cleaned


def extract_domain(url: str) -> str:
    """
    Extracts just the domain from a URL.
    e.g. "https://www.g2.com/reviews/zepto" -> "g2.com"
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split("/")[0]
        # Remove www. prefix for cleaner comparison
        if domain.startswith("www."):
            domain = domain[4:]
        return domain.lower()
    except Exception:
        return ""


async def find_citation_gaps(
    scan_job_id: str,
    brand_name: str,
    brand_id: str,
    competitor_names: List[str],
) -> List[Dict]:
    """
    Analyzes scan results to find domains that cite competitors but not the brand.

    Logic:
    1. Fetch all scan_results for the scan_job_id.
    2. For each result, extract URLs/domains.
    3. Build domain sets: which domains appear in brand-mentioning responses
       vs competitor-mentioning responses.
    4. Find domains where a competitor is referenced but the brand is NOT.
    5. Return top 3 gaps and save to the citation_gaps table.
    """
    client = get_supabase_client()

    # 1. Fetch all scan results
    try:
        query = (
            client.table("scan_results")
            .select("*")
            .eq("scan_job_id", str(scan_job_id))
            .execute()
        )
        all_results = query.data or []
    except Exception as e:
        logger.error(f"Failed to fetch scan results for citation gap analysis: {e}")
        return []

    if not all_results:
        logger.info(f"No scan results found for scan job {scan_job_id}")
        return []

    brand_lower = brand_name.strip().lower()
    competitor_lowers = [c.strip().lower() for c in competitor_names if c.strip()]

    # 2. Build domain → context maps
    # domains_with_brand: domains that appeared in responses mentioning the brand
    # domains_with_competitor: {domain: competitor_name} for competitor mentions
    domains_with_brand = set()
    domains_with_competitor: Dict[str, str] = {}  # domain -> first competitor found

    for result in all_results:
        response_text = result.get("response_text", "") or ""
        resp_lower = response_text.lower()
        urls = extract_urls(response_text)
        domains = set(extract_domain(url) for url in urls if extract_domain(url))

        # Check if brand is mentioned in this response
        brand_in_response = brand_lower in resp_lower

        # Check which competitors are mentioned in this response
        competitors_in_response = [
            c for c in competitor_names
            if c.strip().lower() in resp_lower
        ]

        if brand_in_response:
            domains_with_brand.update(domains)

        for comp in competitors_in_response:
            for domain in domains:
                if domain not in domains_with_competitor:
                    domains_with_competitor[domain] = comp

    # 3. Find gaps: domains that cite competitor but NOT brand
    gaps = []
    for domain, competitor in domains_with_competitor.items():
        if domain not in domains_with_brand:
            gaps.append({
                "domain": domain,
                "cites_competitor": competitor,
                "cites_brand": False,
            })

    # Sort by domain name for determinism, take top 3
    gaps = sorted(gaps, key=lambda g: g["domain"])[:3]

    # 4. Save to citation_gaps table
    for gap in gaps:
        try:
            client.table("citation_gaps").insert({
                "scan_job_id": str(scan_job_id),
                "brand_id": str(brand_id),
                "domain": gap["domain"],
                "cites_competitor": gap["cites_competitor"],
                "cites_brand": gap["cites_brand"],
            }).execute()
        except Exception as db_err:
            logger.error(f"Failed to save citation gap to DB: {db_err}")

    logger.info(
        f"Citation gap analysis complete for scan job {scan_job_id}: "
        f"found {len(gaps)} gaps out of {len(domains_with_competitor)} competitor-cited domains"
    )

    return gaps

# DONE - citations.py

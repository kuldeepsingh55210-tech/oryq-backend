import sys
import os

# Ensure backend directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.hooks.citations import extract_urls, extract_domain

mock_results = [
    {
        "response_text": ("Zepto is a quick commerce app. According to "
                         "https://www.g2.com/products/zepto/reviews, it has good ratings. "
                         "Competitors include Blinkit, see https://www.capterra.com/p/blinkit"),
        "brand_mentioned": True
    },
    {
        "response_text": ("Blinkit is popular, check https://www.g2.com/products/blinkit "
                         "and https://www.trustpilot.com/review/blinkit.com for reviews"),
        "brand_mentioned": False  
    },
    {
        "response_text": ("For quick commerce, see https://www.producthunt.com/products/swiggy-instamart\n"
                         "No mention of other brands here."),
        "brand_mentioned": False
    }
]

print("--- Testing URL Extraction & Domain Extraction ---")
for idx, result in enumerate(mock_results, 1):
    text = result["response_text"]
    urls = extract_urls(text)
    print(f"\nResponse {idx}:")
    print(f"  Text: {text!r}")
    print(f"  Extracted URLs: {urls}")
    for url in urls:
        domain = extract_domain(url)
        print(f"    URL: {url} -> Domain: {domain}")

def mock_find_citation_gaps(
    all_results,
    brand_name: str,
    competitor_names: list[str],
) -> list[dict]:
    brand_lower = brand_name.strip().lower()
    competitor_lowers = [c.strip().lower() for c in competitor_names if c.strip()]

    domains_with_brand = set()
    domains_with_competitor = {}  # domain -> first competitor found

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

    print("\n--- Intermediate State ---")
    print(f"domains_with_brand: {domains_with_brand}")
    print(f"domains_with_competitor: {domains_with_competitor}")

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
    return gaps

print("\n--- Testing find_citation_gaps logic ---")
gaps = mock_find_citation_gaps(mock_results, "Zepto", ["Blinkit"])
print(f"Gaps found: {gaps}")


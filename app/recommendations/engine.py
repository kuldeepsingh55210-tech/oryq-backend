import logging

logger = logging.getLogger(__name__)

RECOMMENDATION_TEMPLATES = {
    "category_confusion": {
        "title": "Clarify your brand category online",
        "action": "AI models are confusing {brand_name} with an unrelated product/company. Update your website's About page, meta description, and Google Business Profile to clearly state: '{brand_name} is a [{category}] company.' Also consider adding structured data (Schema.org Organization markup) to your homepage.",
        "effort": "30 minutes",
        "impact": "High — fixes fundamental brand identity confusion"
    },
    "pricing_error": {
        "title": "Publish clear pricing information",
        "action": "AI doesn't have accurate pricing info for {brand_name}. Add a dedicated, crawlable pricing page on your website with specific numbers (not just 'contact us'). AI models learn from publicly available, structured content.",
        "effort": "1 hour",
        "impact": "Medium — improves accuracy of AI-generated pricing claims"
    },
    "founding_date_error": {
        "title": "Add company history to your About page",
        "action": "AI has incorrect or missing founding information for {brand_name}. Add a clear 'Founded in [Year]' or company history section to your website's About page or company profile so crawlers can easily parse it.",
        "effort": "15 minutes",
        "impact": "Low — resolves historical metadata accuracy"
    },
    "missing_info": {
        "title": "Publish comprehensive brand documentation",
        "action": "AI models report a lack of details about {brand_name}. Publish an FAQ section, detailed product features, or documentation on your site to give search crawlers more reference material.",
        "effort": "1 hour",
        "impact": "Medium — resolves information gaps in search models"
    },
    "generic": {
        "title": "Optimize site documentation for AI indexing",
        "action": "AI models generated inaccurate details about {brand_name}. Review your site's copy for factual clarity, ensure key messages are written in plain text, and update your meta titles/descriptions.",
        "effort": "30 minutes",
        "impact": "Medium — improves overall accuracy of AI-generated claims"
    },
    "low_score": {
        "title": "Boost brand citations and web presence",
        "action": "Your brand visibility score is {score}/100. AI models are not mentioning {brand_name} consistently. To increase visibility, focus on building external citations: publish PR articles, request listings on major directories (e.g. G2, Capterra), and seed discussions on Product Hunt.",
        "effort": "3-5 hours / Ongoing",
        "impact": "High — directly increases AI mention rate"
    }
}

from app.scanner.providers.groq_provider import call_groq
from app.database import get_supabase_client
from app.scanner.engine import estimate_tokens

async def log_llm_cost(
    scan_job_id: str | None,
    provider: str,
    model: str,
    cost_usd: float,
    prompt_text: str,
    response_text: str
):
    if not scan_job_id:
        return
    try:
        client = get_supabase_client()
        tokens_in, tokens_out = estimate_tokens(cost_usd, provider, len(prompt_text), len(response_text))
        client.table("llm_cost_log").insert({
            "scan_job_id": str(scan_job_id),
            "provider": provider,
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost_usd
        }).execute()
    except Exception as e:
        logger.error(f"Error logging LLM cost for recommendations: {e}")

async def generate_fix_content(
    category: str,
    brand_name: str,
    industry: str,
    hallucination_claim: str | None = None,
    scan_job_id: str | None = None
) -> dict | None:
    """
    Generates actual fix copy/code based on the recommendation category.
    Calls Groq once per category (or twice for category_confusion).
    Uses temperature=0.3 and max_tokens=500.
    """
    text_prompt = ""
    code_prompt = ""
    content_type = ""
    instructions = ""
    
    if category == "category_confusion":
        text_prompt = (
            f"Write a clear, professional 'About Us' paragraph (3-4 sentences) "
            f"for a company called '{brand_name}' in the '{industry}' industry. "
            f"The paragraph must unambiguously state what category of company "
            f"this is, since AI models have been confusing this brand's name "
            f"with an unrelated product. Make the category crystal clear in "
            f"the first sentence. Write ONLY the paragraph, no preamble."
        )
        code_prompt = (
            f"Generate a valid Schema.org JSON-LD script tag for an "
            f"Organization named '{brand_name}' in the '{industry}' industry. "
            f"Include name, description (one sentence stating the category "
            f"clearly), and @type. Return ONLY the JSON-LD code block, no "
            f"explanation."
        )
        content_type = "about_page_copy"
        instructions = "Copy the paragraph below into your website's About page. Then add the code snippet to your homepage's <head> section."
        
    elif category == "pricing_error":
        text_prompt = (
            f"Write a short, clear pricing page intro paragraph (2-3 sentences) "
            f"for '{brand_name}', a {industry} company. The paragraph should be "
            f"structured so AI models can easily extract accurate pricing information. "
            f"Use a format like: 'X starts at [PRICE_PLACEHOLDER]/month with "
            f"[KEY_FEATURE_PLACEHOLDER].' Use bracketed placeholders since we don't "
            f"know their actual pricing - they should fill these in. Write ONLY the paragraph."
        )
        content_type = "pricing_page_copy"
        instructions = "Fill in the bracketed placeholders with your actual pricing, then add this to a dedicated pricing page on your website."
        
    elif category == "founding_date_error":
        text_prompt = (
            f"Write a brief 'Our Story' paragraph (2-3 sentences) for "
            f"'{brand_name}', a {industry} company. Use [FOUNDING_YEAR] as a "
            f"placeholder for when they started. Write ONLY the paragraph."
        )
        content_type = "about_story_copy"
        instructions = "Fill in your actual founding year, then add this to your About page."
        
    elif category == "missing_info":
        text_prompt = (
            f"Generate 4 frequently asked questions WITH answers for "
            f"'{brand_name}', a {industry} company. Cover: delivery/service "
            f"area, key features, how it compares to competitors, and pricing "
            f"approach. Use [PLACEHOLDER] for any specific facts you don't "
            f"know. Format as Q: / A: pairs. Write ONLY the FAQ content."
        )
        content_type = "faq_copy"
        instructions = "Review and fill in placeholders, then publish this as an FAQ page or section."
        
    elif category in ["generic", "low_score"]:
        text_prompt = (
            f"Write a short LinkedIn post (3-4 sentences) announcing that "
            f"'{brand_name}' is now listed/comparing favorably in the "
            f"{industry} space. Make it sound natural and shareable, not "
            f"salesy. Write ONLY the post text."
        )
        content_type = "social_post_copy"
        instructions = "Use this as a starting point for a LinkedIn post highlighting your category leadership."
    
    else:
        return None

    generated_text = ""
    generated_code = ""

    if text_prompt:
        try:
            response, cost, latency = await call_groq(text_prompt, temperature=0.3, max_tokens=500)
            if response and not response.startswith("Error:"):
                generated_text = response.strip()
                await log_llm_cost(scan_job_id, "groq", "llama-3.3-70b-versatile", cost, text_prompt, response)
        except Exception as e:
            logger.error(f"Error calling Groq for text generation in recommendations: {e}")
            return None

    if code_prompt:
        try:
            response, cost, latency = await call_groq(code_prompt, temperature=0.3, max_tokens=500)
            if response and not response.startswith("Error:"):
                generated_code = response.strip()
                await log_llm_cost(scan_job_id, "groq", "llama-3.3-70b-versatile", cost, code_prompt, response)
        except Exception as e:
            logger.error(f"Error calling Groq for code generation in recommendations: {e}")

    if not generated_text:
        return None

    res = {
        "content_type": content_type,
        "generated_text": generated_text,
        "instructions": instructions
    }
    if generated_code:
        res["generated_code"] = generated_code

    return res

def categorize_hallucination(claim: str) -> str:
    """
    Categorizes the hallucination claim by scanning for keyword patterns.
    """
    claim_lower = claim.lower()
    
    # 1. Category Confusion
    if any(kw in claim_lower for kw in ["incorrectly described", "javascript library", "different company", "confused with"]):
        return "category_confusion"
    
    # 2. Pricing Error
    if any(kw in claim_lower for kw in ["pricing", "price", "cost", "fee", "delivery charge"]):
        return "pricing_error"
    
    # 3. Founding Date Error
    if any(kw in claim_lower for kw in ["founded", "founding year", "established"]):
        return "founding_date_error"
    
    # 4. Missing Info
    if any(kw in claim_lower for kw in ["does not mention", "doesn't mention", "lacks information"]):
        return "missing_info"
        
    return "generic"

async def generate_recommendations(
    brand_name: str,
    industry: str,
    score: float,
    hallucinations: list[dict],
    scan_job_id: str | None = None
) -> list[dict]:
    """
    Processes scan facts (hallucinations and visibility score) and yields
    a list of unique actionable recommendations with LLM-generated deployable copy.
    """
    recommendations = []
    seen_categories = set()
    
    # Get industry category text or fallback
    cat_text = industry.strip() if industry and industry.strip() else "brand category"
    score_str = f"{int(score)}" if isinstance(score, (int, float)) and score.is_integer() else f"{score:.1f}"

    # 1. Evaluate hallucinations and extract corresponding templates
    for h in hallucinations:
        claim_text = h.get("claim", "")
        category = categorize_hallucination(claim_text)
        
        if category not in seen_categories:
            seen_categories.add(category)
            template = RECOMMENDATION_TEMPLATES.get(category)
            if template:
                # Format action instructions
                action_formatted = template["action"].format(
                    brand_name=brand_name,
                    category=cat_text
                )
                
                # Generate custom fix content using LLM
                generated_content = None
                try:
                    generated_content = await generate_fix_content(
                        category=category,
                        brand_name=brand_name,
                        industry=cat_text,
                        hallucination_claim=claim_text,
                        scan_job_id=scan_job_id
                    )
                except Exception as e:
                    logger.error(f"Error generating fix content for category {category}: {e}")

                recommendations.append({
                    "category": category,
                    "title": template["title"],
                    "action": action_formatted,
                    "effort": template["effort"],
                    "impact": template["impact"],
                    "generated_content": generated_content
                })

    # 2. Evaluate low visibility score
    if score < 70:
        category = "low_score"
        if category not in seen_categories:
            seen_categories.add(category)
            template = RECOMMENDATION_TEMPLATES.get(category)
            if template:
                action_formatted = template["action"].format(
                    brand_name=brand_name,
                    score=score_str
                )
                
                # Generate custom fix content using LLM
                generated_content = None
                try:
                    generated_content = await generate_fix_content(
                        category=category,
                        brand_name=brand_name,
                        industry=cat_text,
                        scan_job_id=scan_job_id
                    )
                except Exception as e:
                    logger.error(f"Error generating fix content for category {category}: {e}")

                recommendations.append({
                    "category": category,
                    "title": template["title"],
                    "action": action_formatted,
                    "effort": template["effort"],
                    "impact": template["impact"],
                    "generated_content": generated_content
                })

    return recommendations

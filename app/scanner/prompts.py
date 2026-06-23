STARTER_PROMPTS = {
    "discovery": [
        "What are the best {industry} tools for startups?",
        "Recommend top products in the {industry} space.",
        "What are the leading platforms for {industry}?",
        "List the most popular solutions for {industry} currently.",
        "Which {industry} services are trending today?"
    ],
    "comparison": [
        "Compare {brand} vs competitors in {industry}.",
        "How does {brand} stack up against other {industry} solutions?",
        "What is the difference between {brand} and its main rivals in {industry}?",
        "Show a comparison table of {brand} and other {industry} tools.",
        "Who are the top competitors of {brand} in {industry}?"
    ],
    "evaluation": [
        "Is {brand} recommended for small businesses?",
        "What are the pros and cons of using {brand} for {industry}?",
        "Read reviews on {brand} quality and reliability.",
        "Is {brand} worth the price for {industry}?",
        "What is the overall rating and feedback for {brand}?"
    ],
    "recommendation": [
        "What do people say about {brand}?",
        "Which {industry} tool do you recommend for scaling enterprises?",
        "Provide a recommended tech stack including {brand}.",
        "Why would you recommend {brand} over other options?",
        "Can you recommend a good {industry} solution, and is {brand} a good choice?"
    ]
}

def get_prompts_for_brand(brand_name: str, industry: str) -> list[str]:
    """
    Returns a list of 20 formatted prompt strings for a given brand name and industry.
    """
    formatted = []
    for category, prompt_list in STARTER_PROMPTS.items():
        for prompt in prompt_list:
            formatted.append(prompt.format(brand=brand_name, industry=industry))
    return formatted

def get_prompts_with_categories(brand_name: str, industry: str) -> list[dict]:
    """
    Returns a list of dictionaries with keys: 'text' (formatted) and 'category' (str).
    """
    results = []
    for category, prompt_list in STARTER_PROMPTS.items():
        for prompt in prompt_list:
            results.append({
                "text": prompt.format(brand=brand_name, industry=industry),
                "category": category
            })
    return results

# DONE - prompts.py

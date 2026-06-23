import logging
from typing import List, Dict, Tuple, Any

logger = logging.getLogger(__name__)

def compute_score(results: List[Any]) -> Tuple[float, Dict[str, Dict[str, Any]]]:
    """
    Computes visibility score and breakdown.
    Formula: (total_mentions / total_results) * 100
    Weighted by provider: Groq 33%, Gemini 33%, OpenAI 34%
    Re-normalizes weights if some providers are missing from results.
    Works correctly with 1, 2, or 3 providers — if OpenAI is unavailable,
    Groq and Gemini weights are re-normalized to sum to 100%.
    Returns: (overall_score, score_breakdown)
    """
    breakdown = {
        "groq": {"score": 0.0, "mentions": 0, "total": 0},
        "gemini": {"score": 0.0, "mentions": 0, "total": 0},
        "openai": {"score": 0.0, "mentions": 0, "total": 0}
    }

    if not results:
        return 0.0, breakdown

    # Tally results by provider
    for r in results:
        # Support both object attributes and dictionary keys
        if isinstance(r, dict):
            provider = r.get("provider", "").lower()
            brand_mentioned = bool(r.get("brand_mentioned", False))
        else:
            provider = getattr(r, "provider", "").lower()
            brand_mentioned = bool(getattr(r, "brand_mentioned", False))

        if provider in breakdown:
            breakdown[provider]["total"] += 1
            if brand_mentioned:
                breakdown[provider]["mentions"] += 1

    # Calculate individual provider scores
    for p in breakdown:
        total = breakdown[p]["total"]
        if total > 0:
            breakdown[p]["score"] = round((breakdown[p]["mentions"] / total) * 100, 2)

    # Static default weights
    base_weights = {
        "groq": 0.33,
        "gemini": 0.33,
        "openai": 0.34
    }

    # Determine which providers are active (have results)
    active_providers = [p for p in breakdown if breakdown[p]["total"] > 0]

    # Normalize weights based on active providers
    active_weight_sum = sum(base_weights[p] for p in active_providers)

    if len(active_providers) < 3:
        logger.info(
            f"Scoring with {len(active_providers)} provider(s): {active_providers}. "
            f"Weights re-normalized from base sum {active_weight_sum:.2f} to 1.0."
        )

    overall_score = 0.0
    if active_weight_sum > 0:
        for p in active_providers:
            # Re-normalized weight
            weight = base_weights[p] / active_weight_sum
            overall_score += breakdown[p]["score"] * weight
            logger.debug(
                f"  {p}: score={breakdown[p]['score']}% × weight={weight:.4f} "
                f"= contribution={breakdown[p]['score'] * weight:.2f}"
            )

    return round(overall_score, 2), breakdown

# DONE - scorer.py


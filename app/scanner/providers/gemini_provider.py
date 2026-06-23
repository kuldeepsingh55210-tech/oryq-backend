import time
import asyncio
import logging
import traceback
import google.generativeai as genai
from app.config import settings

logger = logging.getLogger(__name__)

# Model to use — gemini-2.0-flash is the current stable free-tier model.
# gemini-1.5-flash-002 was retired and returns 404.
GEMINI_MODEL = "gemini-2.0-flash"

_gemini_configured = False

def get_gemini_model() -> genai.GenerativeModel:
    """
    Returns the lazy-configured GenerativeModel.
    """
    global _gemini_configured
    if not _gemini_configured:
        if not settings.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY is not configured.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_configured = True
    return genai.GenerativeModel(GEMINI_MODEL)

async def call_gemini(prompt: str) -> tuple[str, float, int]:
    """
    Calls Gemini API using gemini-2.0-flash, with temperature 0.0 and max_tokens 400.
    Calculates cost_usd = $0.000000075 per token.
    Includes retry logic on exception with full traceback logging.
    Returns: (response_text, cost_usd, latency_ms)
    """
    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not configured.")
        return "Error: GEMINI_API_KEY is not configured.", 0.0, 0

    max_retries = 3
    base_delay = 1.0  # seconds

    for attempt in range(max_retries + 1):
        start_time = time.perf_counter()
        try:
            model = get_gemini_model()
            config = genai.types.GenerationConfig(
                max_output_tokens=400,
                temperature=0.0
            )
            response = await model.generate_content_async(prompt, generation_config=config)
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            # Safeguard text extraction if blocked or empty
            try:
                response_text = response.text or ""
            except Exception as text_err:
                logger.warning(f"Could not extract response text directly: {text_err}")
                try:
                    if response.candidates and len(response.candidates) > 0:
                        parts = response.candidates[0].content.parts
                        response_text = parts[0].text if parts else ""
                    else:
                        response_text = ""
                except Exception:
                    response_text = ""

            total_tokens = 0
            if response.usage_metadata:
                total_tokens = response.usage_metadata.total_token_count
            else:
                total_tokens = (len(prompt) + len(response_text)) // 4

            cost_usd = total_tokens * 0.000000075

            return response_text, cost_usd, latency_ms

        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            error_type = type(e).__name__
            error_msg = str(e)

            # Log the FULL traceback for debugging
            logger.error(
                f"Gemini API error on attempt {attempt + 1}/{max_retries + 1} "
                f"[{error_type}]: {error_msg}\n"
                f"Full traceback:\n{traceback.format_exc()}"
            )

            # Detect quota exhaustion — no point retrying
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
                logger.error(
                    f"Gemini API quota exhausted — skipping remaining retries. "
                    f"Check your billing at https://ai.google.dev/gemini-api/docs/rate-limits"
                )
                return f"Error: Gemini API quota exhausted. {error_msg[:300]}", 0.0, elapsed_ms

            if attempt == max_retries:
                return f"Error: Gemini API error after {max_retries + 1} attempts. [{error_type}] {error_msg[:300]}", 0.0, elapsed_ms

            delay = base_delay * (2 ** attempt)
            logger.warning(f"Retrying Gemini API call in {delay:.2f}s...")
            await asyncio.sleep(delay)

    return "Error: Unknown execution failure.", 0.0, 0

# DONE - gemini_provider.py

import time
import asyncio
import logging
from groq import AsyncGroq, RateLimitError, APIError
from app.config import settings

logger = logging.getLogger(__name__)

_groq_client: AsyncGroq = None

def get_groq_client() -> AsyncGroq:
    """
    Returns the singleton AsyncGroq client.
    """
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    return _groq_client

async def call_groq(prompt: str, temperature: float = 0.0, max_tokens: int = 400) -> tuple[str, float, int]:
    """
    Calls Groq API using Llama 3.3 70b, with optional temperature and max_tokens.
    Calculates cost_usd = $0.0000008 per token (input + output).
    Includes rate limit handling with exponential backoff.
    Returns: (response_text, cost_usd, latency_ms)
    """
    if not settings.GROQ_API_KEY:
        logger.error("GROQ_API_KEY is not configured.")
        return "Error: GROQ_API_KEY is not configured.", 0.0, 0

    client = get_groq_client()
    max_retries = 3
    base_delay = 1.0  # seconds

    for attempt in range(max_retries + 1):
        start_time = time.perf_counter()
        try:
            response = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            response_text = response.choices[0].message.content or ""

            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            completion_tokens = response.usage.completion_tokens if response.usage else 0
            total_tokens = prompt_tokens + completion_tokens
            cost_usd = total_tokens * 0.0000008

            return response_text, cost_usd, latency_ms

        except RateLimitError as e:
            if attempt == max_retries:
                logger.error(f"Groq API rate limit exceeded. Max retries ({max_retries}) reached. Error: {e}")
                return f"Error: Groq rate limit exceeded. {str(e)}", 0.0, int((time.perf_counter() - start_time) * 1000)
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Groq API rate limit error. Retrying in {delay:.2f}s... (Attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(delay)

        except APIError as e:
            logger.error(f"Groq API error on attempt {attempt + 1}: {e}")
            if attempt == max_retries:
                return f"Error: Groq API error. {str(e)}", 0.0, int((time.perf_counter() - start_time) * 1000)
            await asyncio.sleep(base_delay)

        except Exception as e:
            logger.error(f"Unexpected error calling Groq API: {e}")
            return f"Error: Unexpected exception. {str(e)}", 0.0, int((time.perf_counter() - start_time) * 1000)

    return "Error: Unknown execution failure.", 0.0, 0

# DONE - groq_provider.py

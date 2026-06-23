import time
import asyncio
import logging
from openai import AsyncOpenAI, RateLimitError, APIError
from app.config import settings

logger = logging.getLogger(__name__)

_openai_client: AsyncOpenAI = None

def get_openai_client() -> AsyncOpenAI:
    """
    Returns the singleton AsyncOpenAI client.
    """
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client

async def call_openai(prompt: str) -> tuple[str, float, int]:
    """
    Calls OpenAI API using gpt-4o-mini, with temperature 0.0 and max_tokens 400.
    Calculates cost_usd = usage.total_tokens * 0.00000015.
    Includes retry logic on exception.
    Returns: (response_text, cost_usd, latency_ms)
    """
    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY is not configured.")
        return "Error: OPENAI_API_KEY is not configured.", 0.0, 0

    client = get_openai_client()
    max_retries = 3
    base_delay = 1.0  # seconds

    for attempt in range(max_retries + 1):
        start_time = time.perf_counter()
        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.0
            )
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            response_text = response.choices[0].message.content or ""

            total_tokens = response.usage.total_tokens if response.usage else 0
            cost_usd = total_tokens * 0.00000015

            return response_text, cost_usd, latency_ms

        except RateLimitError as e:
            if attempt == max_retries:
                logger.error(f"OpenAI API rate limit exceeded. Max retries ({max_retries}) reached. Error: {e}")
                return f"Error: OpenAI rate limit. {str(e)}", 0.0, int((time.perf_counter() - start_time) * 1000)
            delay = base_delay * (2 ** attempt)
            logger.warning(f"OpenAI API rate limit error. Retrying in {delay:.2f}s... (Attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(delay)

        except APIError as e:
            logger.error(f"OpenAI API error on attempt {attempt + 1}: {e}")
            if attempt == max_retries:
                return f"Error: OpenAI API error. {str(e)}", 0.0, int((time.perf_counter() - start_time) * 1000)
            await asyncio.sleep(base_delay)

        except Exception as e:
            logger.error(f"Unexpected error calling OpenAI API: {e}")
            return f"Error: Unexpected exception. {str(e)}", 0.0, int((time.perf_counter() - start_time) * 1000)

    return "Error: Unknown execution failure.", 0.0, 0

# DONE - openai_provider.py

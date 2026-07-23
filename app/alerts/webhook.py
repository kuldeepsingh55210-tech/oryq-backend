import json
import hmac
import hashlib
import asyncio
import logging
import httpx
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def generate_hmac_signature(payload_bytes: bytes, secret: str) -> str:
    """
    Computes HMAC-SHA256 signature for custom webhook payload.
    """
    key = secret.encode("utf-8")
    sig = hmac.new(key, payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={sig}"

async def send_custom_webhook_alert(webhook_url: str, payload: Dict[str, Any], secret: str = "oryq-webhook-secret") -> bool:
    """
    Posts JSON alert payload to a custom webhook URL with HMAC signature header `X-ORYQ-Signature`.
    Retries up to 3 times with exponential backoff (1s, 2s, 4s).
    """
    if not webhook_url or not (webhook_url.startswith("http://") or webhook_url.startswith("https://")):
        logger.warning(f"Invalid custom webhook URL: {webhook_url}")
        return False

    json_data = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    signature = generate_hmac_signature(json_data, secret)

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "ORYQ-Webhook-Notifier/2.0",
        "X-ORYQ-Signature": signature
    }

    backoffs = [1.0, 2.0, 4.0]

    for attempt, delay in enumerate(backoffs, start=1):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(webhook_url, content=json_data, headers=headers)
                if 200 <= resp.status_code < 300:
                    logger.info(f"Custom webhook delivered on attempt {attempt} to {webhook_url}")
                    return True
                else:
                    logger.warning(f"Attempt {attempt}: Custom webhook returned HTTP {resp.status_code}")
        except Exception as e:
            logger.warning(f"Attempt {attempt}: Custom webhook error for {webhook_url}: {e}")

        if attempt < len(backoffs):
            await asyncio.sleep(delay)

    logger.error(f"Failed to deliver custom webhook to {webhook_url} after 3 attempts.")
    return False

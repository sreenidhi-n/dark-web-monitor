import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_webhook_alert(payload: dict, webhook_url: str = None) -> bool:
    url = webhook_url or settings.alert_webhook_url
    if not url:
        logger.warning("Alert webhook not configured — skipping webhook alert")
        return False

    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json=payload, timeout=10)
            r.raise_for_status()
        logger.info("Webhook alert delivered to %s", url)
        return True
    except Exception as exc:
        logger.error("Failed to deliver webhook alert to %s: %s", url, exc)
        return False

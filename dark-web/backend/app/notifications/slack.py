import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_slack_alert(text: str, webhook_url: str = None) -> bool:
    url = webhook_url or settings.slack_webhook_url
    if not url:
        logger.warning("Slack webhook not configured — skipping Slack alert")
        return False

    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json={"text": text}, timeout=10)
            r.raise_for_status()
        logger.info("Slack alert delivered")
        return True
    except Exception as exc:
        logger.error("Failed to send Slack alert: %s", exc)
        return False

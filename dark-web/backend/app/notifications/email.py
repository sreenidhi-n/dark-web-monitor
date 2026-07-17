import logging

import aiosmtplib
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


async def send_alert_email(to: str, subject: str, body: str) -> bool:
    if not settings.smtp_host:
        logger.warning("SMTP not configured — skipping email alert")
        return False

    message = MIMEText(body, "plain")
    message["From"] = settings.smtp_from
    message["To"] = to
    message["Subject"] = subject

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=True,
        )
        logger.info("Alert email sent to %s", to)
        return True
    except Exception as exc:
        logger.error("Failed to send alert email to %s: %s", to, exc)
        return False

"""
Phase 6 bonus: plain SMTP email delivery for the daily digest job
(services/digest.py). If SMTP_HOST is unset (e.g. a reviewer's clone-and-run,
or CI), logs the rendered email instead of sending - so the scheduled job
never crashes a demo for lack of mail credentials, and the feature is still
visibly exercised.
"""

import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        logger.info(
            "SMTP not configured - logging email instead of sending. to=%s subject=%r\n%s",
            to,
            subject,
            body,
        )
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = (
        settings.digest_from_email or settings.smtp_user or "smartreco@localhost"
    )
    message["To"] = to
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        # A local dev catcher like MailHog has no auth/TLS - only do both
        # when real credentials are actually configured (a real relay).
        if settings.smtp_user and settings.smtp_password:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)
    logger.info("Email sent to=%s subject=%r", to, subject)

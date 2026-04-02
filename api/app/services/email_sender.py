"""
Thin Resend SDK wrapper for sending emails.
"""

import logging

import resend

from app.config import settings

logger = logging.getLogger(__name__)


def send_email(from_addr: str, to: str, subject: str, html: str) -> bool:
    """Send email via Resend SDK. Returns True on success, False on failure."""
    if not settings.resend_api_key:
        logger.error("RESEND_API_KEY not configured")
        return False

    resend.api_key = settings.resend_api_key
    try:
        resend.Emails.send(
            {"from": from_addr, "to": to, "subject": subject, "html": html}
        )
        return True
    except Exception:
        logger.exception("Resend send failed")
        return False

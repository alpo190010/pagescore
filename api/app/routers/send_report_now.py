"""POST /send-report-now — build full report email and send via Resend."""

import logging
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.email_sender import send_email
from app.services.email_templates import build_full_report

from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class SendReportNowBody(BaseModel):
    email: str
    url: str | None = None
    score: int | float | None = 0
    tips: list | None = None
    categories: dict | None = None


@router.post("/send-report-now")
@limiter.limit("5/minute")
def send_report_now(request: Request, body: SendReportNowBody):
    email = (body.email or "").strip()

    # Validate email
    if not email or not _EMAIL_RE.match(email):
        return JSONResponse(
            status_code=400, content={"error": "Invalid email"}
        )

    # Clamp score 0-100
    safe_score = min(100, max(0, int(body.score or 0)))

    # Safe tips: max 20, each max 300 chars
    raw_tips = body.tips if isinstance(body.tips, list) else []
    safe_tips = [str(t)[:300] for t in raw_tips][:20]

    # Safe categories
    safe_cats = body.categories if isinstance(body.categories, dict) else {}

    # Build HTML email
    html = build_full_report(safe_score, safe_tips, safe_cats)

    # Send via Resend
    subject = (
        f"Your product page scored {safe_score}/100 "
        "\u2014 full report with all 20 dimensions"
    )
    ok = send_email(
        from_addr="alpo.ai <noreply@alpo.ai>",
        to=email,
        subject=subject,
        html=html,
    )

    if not ok:
        return JSONResponse(
            status_code=500, content={"error": "Failed to send"}
        )

    return {"success": True}

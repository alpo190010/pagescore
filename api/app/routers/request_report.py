"""POST /request-report — persist report + subscriber to DB (no email sent)."""

import logging
import re

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Report, Subscriber

from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class RequestReportBody(BaseModel):
    email: str
    url: str
    score: int | float | None = 0
    summary: str | None = None
    tips: list | None = None
    categories: dict | None = None
    competitorName: str | None = None


@router.post("/request-report")
@limiter.limit("5/minute")
def request_report(request: Request, body: RequestReportBody, db: Session = Depends(get_db)):
    email = (body.email or "").strip()
    url = body.url or ""

    # Validate email
    if not email or not _EMAIL_RE.match(email) or len(email) > 254:
        return JSONResponse(
            status_code=400,
            content={"error": "Please enter a valid email address."},
        )

    # Validate URL
    if not url or not isinstance(url, str):
        return JSONResponse(status_code=400, content={"error": "URL is required"})
    if len(url) > 2048:
        return JSONResponse(status_code=400, content={"error": "URL is too long"})

    # Clamp score 0-100
    safe_score = min(100, max(0, int(body.score or 0)))

    # Safe tips: max 7, each max 300 chars
    raw_tips = body.tips if isinstance(body.tips, list) else []
    safe_tips = [str(t)[:300] for t in raw_tips][:7]

    # Merge competitorName into categories
    categories = body.categories or {}
    competitor_name = (
        body.competitorName.strip()
        if isinstance(body.competitorName, str) and body.competitorName.strip()
        else None
    )
    merged_categories = (
        {**categories, "_competitorName": competitor_name}
        if competitor_name
        else categories or None
    )

    # Insert report (fire-and-forget — errors logged, not propagated)
    try:
        db.add(
            Report(
                email=email,
                url=url,
                score=safe_score,
                summary=str(body.summary)[:500] if body.summary else None,
                tips=safe_tips or None,
                categories=merged_categories,
            )
        )
        db.commit()
    except Exception:
        logger.exception("Failed to insert report")
        db.rollback()

    # Insert subscriber (upsert — ignore conflict on unique email)
    try:
        stmt = (
            pg_insert(Subscriber)
            .values(
                email=email,
                first_scan_url=url,
                first_scan_score=safe_score,
            )
            .on_conflict_do_nothing(index_elements=["email"])
        )
        db.execute(stmt)
        db.commit()
    except Exception:
        logger.exception("Failed to insert subscriber")
        db.rollback()

    return {"success": True}

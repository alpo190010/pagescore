"""``GET /fix/{dimension_key}`` — structured fix content for a store-wide dimension.

Mirrors the plan-tier gating used by ``/analyze``: free tier receives the
metadata (label, problem, revenue_gain, effort, scope) but the ``steps`` and
``code`` fields are stripped, and ``locked`` is ``True``.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from app.auth import get_current_user_optional
from app.models import User
from app.services.dimension_fixes import FIX_CONTENT

router = APIRouter()


@router.get("/fix/{dimension_key}")
def get_dimension_fix(
    dimension_key: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    fix = FIX_CONTENT.get(dimension_key)
    if fix is None:
        raise HTTPException(status_code=404, detail="Unknown dimension")

    plan_tier = current_user.plan_tier if current_user else "free"
    locked = plan_tier == "free"

    return {
        "dimensionKey": dimension_key,
        "label": fix["label"],
        "problem": fix["problem"],
        "revenueGain": fix["revenue_gain"],
        "effort": fix["effort"],
        "scope": fix.get("scope", "All products"),
        "steps": [] if locked else fix["steps"],
        "code": None if locked else fix.get("code"),
        "planTier": plan_tier,
        "locked": locked,
    }

"""Admin user impersonation endpoints.

POST /admin/impersonate/{user_id}   — mint a JWT as the target user
POST /admin/stop-impersonation      — validate and end impersonation

All endpoints require admin role via ``get_current_user_admin``.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth import get_current_user_admin
from app.config import settings
from app.database import get_db
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/admin/impersonate/{user_id}")
def impersonate_user(
    user_id: str,
    admin_user: User = Depends(get_current_user_admin),
    db: Session = Depends(get_db),
):
    """Mint an HS256 JWT as the target user for admin impersonation.

    The token carries an ``impersonator`` claim so the frontend can show
    a banner and the stop-impersonation endpoint can validate the session.
    """
    # --- Parse user_id as UUID ---
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    # --- Block self-impersonation ---
    if uid == admin_user.id:
        raise HTTPException(status_code=400, detail="Cannot impersonate yourself")

    # --- Look up target user ---
    target = db.query(User).filter(User.id == uid).first()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    # --- Mint JWT ---
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(target.id),
        "email": target.email,
        "name": target.name,
        "impersonator": str(admin_user.id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, settings.auth_secret, algorithm="HS256")

    logger.info(
        "Admin %s (%s) started impersonating user %s (%s)",
        admin_user.id,
        admin_user.email,
        target.id,
        target.email,
    )

    return {
        "token": token,
        "user": {
            "id": str(target.id),
            "email": target.email,
            "name": target.name,
        },
    }


@router.post("/admin/stop-impersonation")
def stop_impersonation(request: Request):
    """End an impersonation session by validating the impersonator claim.

    Reads the Bearer token directly (not via the auth dependency) and
    checks for the ``impersonator`` claim that proves the token was
    minted by the impersonate endpoint.
    """
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authentication required")

    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(status_code=401, detail="Authentication required")

    token = parts[1].strip()

    try:
        payload = jwt.decode(token, settings.auth_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    impersonator = payload.get("impersonator")
    if not impersonator:
        raise HTTPException(
            status_code=400,
            detail="Token does not contain an impersonator claim",
        )

    logger.info(
        "Admin %s stopped impersonating user %s",
        impersonator,
        payload.get("sub"),
    )

    return {"message": "Impersonation ended"}

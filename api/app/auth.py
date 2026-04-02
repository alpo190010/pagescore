"""JWT authentication dependencies for FastAPI.

Verifies Auth.js-issued JWTs using PyJWT and resolves the user from
the `sub` claim (google_sub) in the database.
"""

from __future__ import annotations

import logging
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

logger = logging.getLogger(__name__)


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Extract and verify a Bearer JWT from the Authorization header.

    Returns the matching User row if the token is valid and the user exists,
    otherwise returns None.  **Never raises** — any error path returns None so
    that anonymous access remains possible.
    """
    # Guard: if auth_secret is not configured, auth is disabled.
    if not settings.auth_secret:
        return None

    auth_header = request.headers.get("authorization")
    if not auth_header:
        return None

    # Expect "Bearer <token>"
    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        return None

    token = parts[1].strip()

    try:
        payload = jwt.decode(
            token,
            settings.auth_secret,
            algorithms=["HS256"],
        )
    except jwt.PyJWTError:
        logger.debug("JWT decode failed", exc_info=True)
        return None

    sub: str | None = payload.get("sub")
    if not sub:
        return None

    user = db.query(User).filter(User.google_sub == sub).first()
    return user


def get_current_user_required(
    user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    """Require an authenticated user — raises 401 if absent."""
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

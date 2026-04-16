"""POST /user/waitlist -- record Pro waitlist interest for the authenticated user."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user_required
from app.database import get_db
from app.models import User

router = APIRouter()


@router.post("/user/waitlist", status_code=200)
def join_waitlist(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Record the authenticated user's Pro waitlist interest.

    Idempotent: safe to call multiple times (handles React Strict Mode double-invoke).
    """
    if not current_user.pro_waitlist:
        current_user.pro_waitlist = True
        db.commit()
    return {"waitlisted": True}

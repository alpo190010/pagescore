"""GET /user/scans — return authenticated user's scan history."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user_required
from app.database import get_db
from app.models import Scan, User

router = APIRouter()


@router.get("/user/scans")
def user_scans(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Return the authenticated user's most recent scans (up to 50)."""
    rows = (
        db.query(Scan)
        .filter(Scan.user_id == current_user.id)
        .order_by(Scan.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": str(row.id),
            "url": row.url,
            "score": row.score,
            "productCategory": row.product_category,
            "createdAt": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]

"""GET /store/{domain} — return store, products, and analyses for a domain.

Also exposes POST /store/{domain}/refresh-analysis to manually re-run the
store-wide dimension scan, bypassing the 7-day cache.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.auth import get_current_user_optional, get_current_user_required
from app.database import get_db
from app.models import ProductAnalysis, Store, StoreAnalysis, StoreProduct, User
from app.rate_limit import limiter
from app.routers.discover_products import _run_store_wide_analysis

logger = logging.getLogger(__name__)

router = APIRouter()

PRODUCT_ANALYSIS_TTL = timedelta(hours=24)


def _is_fresh(row, now: datetime) -> bool:
    updated = row.updated_at
    if updated is None:
        return False
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return (now - updated) < PRODUCT_ANALYSIS_TTL


@router.get("/store/{domain}")
def get_store(
    domain: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    if not domain:
        return JSONResponse(
            status_code=400, content={"error": "Domain is required"}
        )

    try:
        store = db.query(Store).filter(Store.domain == domain).first()
        if not store:
            return JSONResponse(
                status_code=404, content={"error": "Store not found"}
            )

        products = (
            db.query(StoreProduct)
            .filter(StoreProduct.store_id == store.id)
            .order_by(asc(StoreProduct.created_at))
            .all()
        )

        if current_user is not None:
            analysis_rows = (
                db.query(ProductAnalysis)
                .filter(ProductAnalysis.store_domain == domain)
                .filter(ProductAnalysis.user_id == current_user.id)
                .all()
            )
            store_analysis_row = (
                db.query(StoreAnalysis)
                .filter(StoreAnalysis.store_domain == domain)
                .filter(StoreAnalysis.user_id == current_user.id)
                .first()
            )
        else:
            analysis_rows = []
            store_analysis_row = None

        # Build analyses dict keyed by productUrl (fresh rows only)
        now = datetime.now(timezone.utc)
        analyses: dict = {}
        for row in analysis_rows:
            if not _is_fresh(row, now):
                continue
            analyses[row.product_url] = {
                "id": str(row.id),
                "score": row.score,
                "summary": row.summary,
                "tips": row.tips,
                "categories": row.categories,
                "productPrice": (
                    str(row.product_price)
                    if row.product_price is not None
                    else None
                ),
                "productCategory": row.product_category,
                "signals": row.signals,
                "updatedAt": (
                    row.updated_at.isoformat() if row.updated_at else None
                ),
            }

        return {
            "store": {
                "id": str(store.id),
                "domain": store.domain,
                "name": store.name,
                "updatedAt": (
                    store.updated_at.isoformat() if store.updated_at else None
                ),
            },
            "products": [
                {
                    "id": str(p.id),
                    "url": p.url,
                    "slug": p.slug,
                    "image": p.image,
                }
                for p in products
            ],
            "analyses": analyses,
            "storeAnalysis": {
                "score": store_analysis_row.score,
                "categories": store_analysis_row.categories,
                "tips": store_analysis_row.tips,
                "signals": store_analysis_row.signals,
                "analyzedUrl": store_analysis_row.analyzed_url,
                "updatedAt": (
                    store_analysis_row.updated_at.isoformat()
                    if store_analysis_row.updated_at
                    else None
                ),
            }
            if store_analysis_row
            else None,
        }
    except Exception:
        logger.exception("Failed to fetch store data")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to fetch store data"},
        )


@router.post("/store/{domain}/refresh-analysis")
@limiter.limit("1/minute")
async def refresh_store_analysis(
    request: Request,
    domain: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    """Force a fresh store-wide analysis, bypassing the 7-day cache.

    Picks a representative product page (first StoreProduct for the domain, or
    falls back to the last analyzed_url on the existing StoreAnalysis row). Runs
    the 7 store-wide detectors + external API calls (axe, PSI, AI discoverability)
    and upserts the StoreAnalysis row.

    Rate-limited to 1/minute per IP to prevent abuse.
    """
    if not domain:
        return JSONResponse(
            status_code=400, content={"error": "Domain is required"}
        )

    try:
        store = db.query(Store).filter(Store.domain == domain).first()
        if not store:
            return JSONResponse(
                status_code=404, content={"error": "Store not found"}
            )

        # Pick a product URL to analyze as the storefront sample.
        first_product = (
            db.query(StoreProduct)
            .filter(StoreProduct.store_id == store.id)
            .order_by(asc(StoreProduct.created_at))
            .first()
        )
        product_url: str | None = first_product.url if first_product else None

        # Fallback: reuse the URL from the previous StoreAnalysis run.
        if product_url is None:
            existing = (
                db.query(StoreAnalysis)
                .filter(StoreAnalysis.store_domain == domain)
                .filter(StoreAnalysis.user_id == current_user.id)
                .first()
            )
            if existing is not None:
                product_url = existing.analyzed_url

        if product_url is None:
            return JSONResponse(
                status_code=404,
                content={"error": "No products found for this store to analyze"},
            )

        result = await _run_store_wide_analysis(
            domain, product_url, current_user.id, db, force=True
        )
        if result is None:
            return JSONResponse(
                status_code=502,
                content={"error": "Store-wide analysis failed — please try again"},
            )
        return result

    except Exception:
        logger.exception(
            "refresh-analysis failed for domain=%s user_id=%s", domain, current_user.id
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to refresh store analysis"},
        )

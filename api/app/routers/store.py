"""GET /store/{domain} — return store, products, and analyses for a domain."""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ProductAnalysis, Store, StoreProduct

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/store/{domain}")
def get_store(domain: str, db: Session = Depends(get_db)):
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

        analysis_rows = (
            db.query(ProductAnalysis)
            .filter(ProductAnalysis.store_domain == domain)
            .all()
        )

        # Build analyses dict keyed by productUrl
        analyses: dict = {}
        for row in analysis_rows:
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
                "estimatedMonthlyVisitors": row.estimated_monthly_visitors,
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
        }
    except Exception:
        logger.exception("Failed to fetch store data")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to fetch store data"},
        )

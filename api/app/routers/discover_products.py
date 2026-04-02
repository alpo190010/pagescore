"""POST /discover-products — find products on a store via Shopify JSON or HTML scraping."""

import logging
import re
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.database import get_db
from app.models import Store, StoreProduct

logger = logging.getLogger(__name__)

router = APIRouter()

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _parse_url(raw: str) -> tuple[str, str]:
    """Normalise URL, return (origin, domain). Raises ValueError on bad input."""
    url = raw if raw.startswith("http") else f"https://{raw}"
    parsed = urlparse(url)
    if not parsed.hostname:
        raise ValueError("bad url")
    origin = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        origin += f":{parsed.port}"
    return origin, parsed.hostname


# ---------------------------------------------------------------------------
# Strategy 1: Shopify /products.json
# ---------------------------------------------------------------------------

_CDN_RE = re.compile(r"(\.(jpg|jpeg|png|webp|avif))", re.IGNORECASE)


def _thumb(src: str) -> str:
    """Apply Shopify CDN 180-px thumbnail suffix and ensure https prefix."""
    img = src
    if img and "cdn.shopify.com" in img:
        img = _CDN_RE.sub(r"_180x\1", img, count=1)
    if img.startswith("//"):
        img = f"https:{img}"
    return img


async def _try_shopify_json(
    origin: str,
) -> list[dict]:
    """Fetch /products.json and return list of {url, slug, image}."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{origin}/products.json?limit=20",
                headers={
                    "User-Agent": _USER_AGENT,
                    "Accept": "application/json",
                },
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
    except Exception:
        return []

    products_raw = data.get("products") or []
    results: list[dict] = []
    for p in products_raw:
        handle = p.get("handle")
        title = p.get("title")
        if not handle or not title:
            continue
        images = p.get("images") or []
        image = _thumb(images[0]["src"]) if images else ""
        results.append(
            {"url": f"{origin}/products/{handle}", "slug": title, "image": image}
        )
    return results


async def _fetch_page_title(origin: str) -> str:
    """Fetch the origin's <title> for a store name."""
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(
                origin,
                headers={"User-Agent": _USER_AGENT, "Accept": "text/html"},
            )
            html = resp.text
        match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        if match:
            return re.split(r"[–—|]", match.group(1).strip())[0].strip()
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# Strategy 2: HTML scraping fallback
# ---------------------------------------------------------------------------

_PRODUCT_HREF_RE = re.compile(
    r"""href=["']((?:https?://[^"']*)?/products/([^"'#?]+))["']""",
    re.IGNORECASE,
)
_IMG_RE = re.compile(
    r"""(?:src|data-src)=["']((?:https?:)?//[^"'\s]+?\.(?:jpg|jpeg|png|webp|avif)[^"'\s]*)""",
    re.IGNORECASE,
)


async def _try_html_scraping(
    origin: str, original_url: str
) -> dict:
    """Return {products, storeName, isProductPage} from HTML scraping."""
    url_to_fetch = original_url if original_url.startswith("http") else f"https://{original_url}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            url_to_fetch,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        if resp.status_code != 200:
            return {"products": [], "storeName": "", "isProductPage": False}

    html = resp.text

    # Store name from <title>
    title_m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    store_name = ""
    if title_m:
        store_name = re.split(r"[–—|]", title_m.group(1).strip())[0].strip()

    # Detect product page
    parsed = urlparse(url_to_fetch)
    is_product_page = bool(re.search(r"/products/[^/]+", parsed.path))
    if not is_product_page:
        has_products_ref = "/products/" in html
        has_cart_signals = bool(re.search(r"add.to.cart|AddToCart|product-form", html, re.IGNORECASE))
        few_product_links = len(re.findall(r"/products/", html)) <= 5
        if has_products_ref and has_cart_signals and few_product_links:
            is_product_page = True

    # Extract product links
    seen: set[str] = set()
    products: list[dict] = []
    for m in _PRODUCT_HREF_RE.finditer(html):
        if len(products) >= 20:
            break
        href = m.group(1)
        raw_slug = m.group(2)
        if href.startswith("/"):
            href = f"{origin}{href}"
        try:
            p = urlparse(href)
            clean = f"{p.scheme}://{p.hostname}{p.path.rstrip('/')}"
            if p.port:
                clean = f"{p.scheme}://{p.hostname}:{p.port}{p.path.rstrip('/')}"
        except Exception:
            continue
        if clean in seen:
            continue
        seen.add(clean)

        slug = raw_slug.replace("-", " ").replace("/", "").strip()
        if not slug:
            continue

        # Find nearby image (±1500 chars)
        pos = m.start()
        neighbourhood = html[max(0, pos - 1500): pos + 1500]
        img_m = _IMG_RE.search(neighbourhood)
        image = ""
        if img_m:
            image = img_m.group(1)
            if image.startswith("//"):
                image = f"https:{image}"

        products.append({"url": clean, "slug": slug, "image": image})

    return {"products": products, "storeName": store_name, "isProductPage": is_product_page}


# ---------------------------------------------------------------------------
# DB persistence
# ---------------------------------------------------------------------------


def _persist_store_and_products(
    db: Session,
    domain: str,
    store_name: str,
    products: list[dict],
) -> str | None:
    """Upsert store, replace products, return storeId or None on failure."""
    try:
        stmt = (
            pg_insert(Store)
            .values(domain=domain, name=store_name or None)
            .on_conflict_do_update(
                index_elements=["domain"],
                set_={"name": store_name or None, "updated_at": func.now()},
            )
            .returning(Store.id)
        )
        row = db.execute(stmt).fetchone()
        db.commit()
        store_id = row[0]

        # Delete existing products, then bulk-insert
        db.query(StoreProduct).filter(StoreProduct.store_id == store_id).delete()
        if products:
            db.bulk_insert_mappings(
                StoreProduct,
                [
                    {
                        "store_id": store_id,
                        "url": p["url"],
                        "slug": p["slug"],
                        "image": p.get("image") or None,
                    }
                    for p in products
                ],
            )
        db.commit()
        return str(store_id)
    except Exception:
        logger.exception("DB store persist error")
        try:
            db.rollback()
        except Exception:
            pass
        return None


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


@router.post("/discover-products")
async def discover_products(request: dict, db: Session = Depends(get_db)):
    try:
        url = request.get("url") if isinstance(request, dict) else None
        if not url or not isinstance(url, str) or not url.strip():
            return JSONResponse(
                status_code=400, content={"error": "URL is required"}
            )

        url = url.strip()
        origin, domain = _parse_url(url)

        # Strategy 1: Shopify JSON
        json_products = await _try_shopify_json(origin)
        if json_products:
            store_name = await _fetch_page_title(origin)
            store_id = _persist_store_and_products(db, domain, store_name, json_products)
            return {
                "products": json_products[:20],
                "storeName": store_name,
                "isProductPage": False,
                "storeId": store_id,
            }

        # Strategy 2: HTML scraping fallback
        html_result = await _try_html_scraping(origin, url)
        store_id = _persist_store_and_products(
            db, domain, html_result["storeName"], html_result["products"]
        )
        return {**html_result, "storeId": store_id}

    except Exception:
        logger.exception("Discover products error")
        return JSONResponse(
            status_code=400,
            content={"error": "Could not fetch that URL. Make sure it's accessible."},
        )

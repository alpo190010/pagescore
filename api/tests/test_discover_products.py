"""Tests for POST /discover-products endpoint."""

import json
from unittest.mock import MagicMock, patch, AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app


# ---- helpers ---------------------------------------------------------------

def _mock_db():
    """Return a MagicMock that simulates a SQLAlchemy Session."""
    session = MagicMock()
    row = MagicMock()
    row.__getitem__ = MagicMock(return_value="fake-store-uuid")
    session.execute.return_value.fetchone.return_value = row
    return session


def _get_client(db_override=None):
    if db_override is not None:
        app.dependency_overrides[get_db] = lambda: db_override
    else:
        app.dependency_overrides[get_db] = lambda: _mock_db()
    return TestClient(app)


def _shopify_json_response(products=None):
    """Build a fake Shopify /products.json payload."""
    if products is None:
        products = [
            {
                "title": "Cool T-Shirt",
                "handle": "cool-t-shirt",
                "images": [{"src": "https://cdn.shopify.com/img/cool.jpg"}],
            },
            {
                "title": "Nice Pants",
                "handle": "nice-pants",
                "images": [{"src": "//cdn.shopify.com/img/pants.png"}],
            },
        ]
    return httpx.Response(200, json={"products": products})


def _html_page(title="Test Store – Home", product_links=None, has_cart=False):
    """Build a fake HTML page with optional product links."""
    links_html = ""
    if product_links:
        for href, img in product_links:
            img_tag = f'<img src="{img}" />' if img else ""
            links_html += f'{img_tag}<a href="{href}">Product</a>\n'
    cart = '<form class="product-form">add to cart</form>' if has_cart else ""
    return f"<html><head><title>{title}</title></head><body>{links_html}{cart}</body></html>"


# ---- validation tests -------------------------------------------------------


def test_missing_url():
    client = _get_client()
    resp = client.post("/discover-products", json={})
    assert resp.status_code == 400
    assert "URL is required" in resp.json()["error"]
    app.dependency_overrides.clear()


def test_empty_url():
    client = _get_client()
    resp = client.post("/discover-products", json={"url": ""})
    assert resp.status_code == 400
    assert "URL is required" in resp.json()["error"]
    app.dependency_overrides.clear()


def test_non_string_url():
    client = _get_client()
    resp = client.post("/discover-products", json={"url": 123})
    assert resp.status_code == 400
    assert "URL is required" in resp.json()["error"]
    app.dependency_overrides.clear()


# ---- Shopify JSON strategy --------------------------------------------------


@patch("app.routers.discover_products._fetch_page_title", new_callable=AsyncMock)
@patch("app.routers.discover_products._try_shopify_json", new_callable=AsyncMock)
def test_shopify_json_success(mock_shopify, mock_title):
    """Shopify JSON returns products → response uses those products."""
    mock_shopify.return_value = [
        {
            "url": "https://example.com/products/cool-t-shirt",
            "slug": "Cool T-Shirt",
            "image": "https://cdn.shopify.com/img/cool_180x.jpg",
        },
        {
            "url": "https://example.com/products/nice-pants",
            "slug": "Nice Pants",
            "image": "https://cdn.shopify.com/img/pants_180x.png",
        },
    ]
    mock_title.return_value = "Test Store"

    mock_session = _mock_db()
    client = _get_client(db_override=mock_session)
    resp = client.post("/discover-products", json={"url": "https://example.com"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["storeName"] == "Test Store"
    assert data["isProductPage"] is False
    assert len(data["products"]) == 2
    assert data["products"][0]["slug"] == "Cool T-Shirt"
    # storeId present (from DB mock)
    assert data["storeId"] is not None
    # DB was used
    assert mock_session.execute.called

    app.dependency_overrides.clear()


def test_shopify_cdn_thumbnail_suffix():
    """Shopify CDN images get _180x thumbnail suffix."""
    from app.routers.discover_products import _thumb

    assert "_180x.jpg" in _thumb("https://cdn.shopify.com/img/product.jpg")
    assert "_180x.png" in _thumb("https://cdn.shopify.com/img/product.png")
    assert "_180x.webp" in _thumb("https://cdn.shopify.com/img/product.webp")
    # Non-Shopify CDN left alone
    assert "_180x" not in _thumb("https://other.com/img/product.jpg")


def test_double_slash_prefix_fixed():
    """Images starting with // get https: prefix."""
    from app.routers.discover_products import _thumb

    result = _thumb("//cdn.shopify.com/img/product.jpg")
    assert result.startswith("https:")
    assert not result.startswith("//")


# ---- HTML scraping fallback --------------------------------------------------


@patch("app.routers.discover_products._try_html_scraping", new_callable=AsyncMock)
@patch("app.routers.discover_products._try_shopify_json", new_callable=AsyncMock)
def test_html_fallback_when_shopify_empty(mock_shopify, mock_html):
    """When Shopify JSON returns empty, fall back to HTML scraping."""
    mock_shopify.return_value = []
    mock_html.return_value = {
        "products": [
            {
                "url": "https://example.com/products/widget",
                "slug": "widget",
                "image": "https://example.com/img/widget.jpg",
            }
        ],
        "storeName": "Widget Store",
        "isProductPage": False,
    }

    client = _get_client()
    resp = client.post("/discover-products", json={"url": "https://example.com"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["storeName"] == "Widget Store"
    assert len(data["products"]) == 1
    assert data["products"][0]["slug"] == "widget"
    assert "storeId" in data

    app.dependency_overrides.clear()


@patch("app.routers.discover_products._try_html_scraping", new_callable=AsyncMock)
@patch("app.routers.discover_products._try_shopify_json", new_callable=AsyncMock)
def test_is_product_page_detected(mock_shopify, mock_html):
    """HTML scraping detects product page correctly."""
    mock_shopify.return_value = []
    mock_html.return_value = {
        "products": [],
        "storeName": "Some Store",
        "isProductPage": True,
    }

    client = _get_client()
    resp = client.post(
        "/discover-products",
        json={"url": "https://example.com/products/some-item"},
    )

    assert resp.status_code == 200
    assert resp.json()["isProductPage"] is True

    app.dependency_overrides.clear()


# ---- URL parsing / scheme prepend -------------------------------------------


def test_url_without_scheme():
    """URLs without http(s) get https:// prepended."""
    from app.routers.discover_products import _parse_url

    origin, domain = _parse_url("example.com/shop")
    assert origin == "https://example.com"
    assert domain == "example.com"


def test_url_with_scheme():
    from app.routers.discover_products import _parse_url

    origin, domain = _parse_url("https://mystore.io")
    assert origin == "https://mystore.io"
    assert domain == "mystore.io"


# ---- fetch failure -----------------------------------------------------------


@patch("app.routers.discover_products._try_html_scraping", new_callable=AsyncMock)
@patch("app.routers.discover_products._try_shopify_json", new_callable=AsyncMock)
def test_fetch_failure_returns_400(mock_shopify, mock_html):
    """When both strategies raise, return 400."""
    mock_shopify.return_value = []
    mock_html.side_effect = Exception("connection refused")

    client = _get_client()
    resp = client.post("/discover-products", json={"url": "https://example.com"})

    assert resp.status_code == 400
    assert "Could not fetch" in resp.json()["error"]

    app.dependency_overrides.clear()


# ---- DB persistence failure --------------------------------------------------


@patch("app.routers.discover_products._try_shopify_json", new_callable=AsyncMock)
@patch("app.routers.discover_products._fetch_page_title", new_callable=AsyncMock)
def test_db_failure_returns_null_store_id(mock_title, mock_shopify):
    """When DB upsert fails, storeId is None but response still returns."""
    mock_shopify.return_value = [
        {
            "url": "https://example.com/products/item",
            "slug": "Item",
            "image": "",
        }
    ]
    mock_title.return_value = "Shop"

    broken_session = MagicMock()
    broken_session.execute.side_effect = Exception("DB down")
    broken_session.rollback = MagicMock()

    client = _get_client(db_override=broken_session)
    resp = client.post("/discover-products", json={"url": "https://example.com"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["storeId"] is None
    assert len(data["products"]) == 1

    app.dependency_overrides.clear()


# ---- camelCase response keys ------------------------------------------------


@patch("app.routers.discover_products._try_shopify_json", new_callable=AsyncMock)
@patch("app.routers.discover_products._fetch_page_title", new_callable=AsyncMock)
def test_response_keys_are_camel_case(mock_title, mock_shopify):
    mock_shopify.return_value = [
        {"url": "https://x.com/products/a", "slug": "A", "image": ""}
    ]
    mock_title.return_value = "Store"

    client = _get_client()
    resp = client.post("/discover-products", json={"url": "https://x.com"})

    data = resp.json()
    assert "storeName" in data
    assert "isProductPage" in data
    assert "storeId" in data
    assert "products" in data

    app.dependency_overrides.clear()

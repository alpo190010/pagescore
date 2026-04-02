"""Tests for GET /store/{domain} endpoint."""

import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, PropertyMock

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app


# ---- helpers ---------------------------------------------------------------


def _make_store(
    id_=None,
    domain="example.com",
    name="Example Store",
    updated_at=None,
):
    store = MagicMock()
    store.id = id_ or uuid.uuid4()
    store.domain = domain
    store.name = name
    store.updated_at = updated_at or datetime(2025, 6, 15, 12, 0, 0)
    store.created_at = datetime(2025, 1, 1)
    return store


def _make_product(store_id, url, slug, image=None, id_=None):
    p = MagicMock()
    p.id = id_ or uuid.uuid4()
    p.store_id = store_id
    p.url = url
    p.slug = slug
    p.image = image
    p.created_at = datetime(2025, 6, 15)
    return p


def _make_analysis(
    product_url,
    store_domain="example.com",
    score=42,
    summary="Needs work",
    tips=None,
    categories=None,
    product_price=None,
    product_category="fashion",
    estimated_monthly_visitors=1000,
    id_=None,
    updated_at=None,
):
    a = MagicMock()
    a.id = id_ or uuid.uuid4()
    a.product_url = product_url
    a.store_domain = store_domain
    a.score = score
    a.summary = summary
    a.tips = tips or ["tip1", "tip2"]
    a.categories = categories or {"pageSpeed": 60}
    a.product_price = product_price
    a.product_category = product_category
    a.estimated_monthly_visitors = estimated_monthly_visitors
    a.updated_at = updated_at or datetime(2025, 6, 16, 10, 0, 0)
    return a


def _mock_db_with_data(store=None, products=None, analyses=None):
    """Build a MagicMock session that chains filter/order_by correctly."""
    session = MagicMock()

    # We need to handle three sequential db.query(...) calls:
    # 1. Store lookup  2. Products lookup  3. Analyses lookup
    store_query = MagicMock()
    store_query.filter.return_value.first.return_value = store

    products_query = MagicMock()
    products_query.filter.return_value.order_by.return_value.all.return_value = (
        products or []
    )

    analyses_query = MagicMock()
    analyses_query.filter.return_value.all.return_value = analyses or []

    session.query.side_effect = [store_query, products_query, analyses_query]
    return session


def _get_client(db_override):
    app.dependency_overrides[get_db] = lambda: db_override
    return TestClient(app)


# ---- tests -------------------------------------------------------------------


def test_store_not_found():
    session = _mock_db_with_data(store=None)
    client = _get_client(session)
    resp = client.get("/store/nonexistent.com")
    assert resp.status_code == 404
    assert resp.json()["error"] == "Store not found"
    app.dependency_overrides.clear()


def test_store_found_full_response():
    """Full happy-path: store + products + analyses with correct shape."""
    store_id = uuid.uuid4()
    store = _make_store(id_=store_id, domain="shop.io", name="Best Shop")
    prod1 = _make_product(
        store_id,
        url="https://shop.io/products/widget",
        slug="widget",
        image="https://cdn.shopify.com/img/w.jpg",
    )
    prod2 = _make_product(
        store_id,
        url="https://shop.io/products/gadget",
        slug="gadget",
        image=None,
    )
    analysis1 = _make_analysis(
        product_url="https://shop.io/products/widget",
        store_domain="shop.io",
        score=55,
        product_price=Decimal("29.99"),
        product_category="electronics",
        estimated_monthly_visitors=2000,
    )

    session = _mock_db_with_data(
        store=store,
        products=[prod1, prod2],
        analyses=[analysis1],
    )
    client = _get_client(session)
    resp = client.get("/store/shop.io")

    assert resp.status_code == 200
    data = resp.json()

    # ---- store shape ----
    assert data["store"]["id"] == str(store_id)
    assert data["store"]["domain"] == "shop.io"
    assert data["store"]["name"] == "Best Shop"
    assert "updatedAt" in data["store"]
    assert data["store"]["updatedAt"] is not None

    # ---- products shape ----
    assert len(data["products"]) == 2
    p1 = data["products"][0]
    assert "id" in p1
    assert p1["url"] == "https://shop.io/products/widget"
    assert p1["slug"] == "widget"
    assert p1["image"] == "https://cdn.shopify.com/img/w.jpg"

    # ---- analyses shape: dict keyed by productUrl ----
    assert isinstance(data["analyses"], dict)
    assert "https://shop.io/products/widget" in data["analyses"]
    a = data["analyses"]["https://shop.io/products/widget"]
    assert a["score"] == 55
    assert a["productPrice"] == "29.99"
    assert a["productCategory"] == "electronics"
    assert a["estimatedMonthlyVisitors"] == 2000
    assert "updatedAt" in a
    assert a["tips"] == ["tip1", "tip2"]
    assert a["categories"] == {"pageSpeed": 60}

    app.dependency_overrides.clear()


def test_store_camel_case_keys():
    """Verify all response keys are camelCase, not snake_case."""
    store = _make_store()
    session = _mock_db_with_data(store=store, products=[], analyses=[])
    client = _get_client(session)
    resp = client.get("/store/example.com")

    data = resp.json()
    # Store keys
    assert "updatedAt" in data["store"]
    assert "updated_at" not in data["store"]

    app.dependency_overrides.clear()


def test_analyses_keyed_by_product_url():
    """analyses dict must be keyed by the full product URL, not by id."""
    store = _make_store()
    analysis = _make_analysis(product_url="https://example.com/products/foo")
    session = _mock_db_with_data(store=store, products=[], analyses=[analysis])
    client = _get_client(session)
    resp = client.get("/store/example.com")

    analyses = resp.json()["analyses"]
    assert "https://example.com/products/foo" in analyses

    app.dependency_overrides.clear()


def test_product_price_serialized_as_string():
    """Numeric product_price is serialized as string."""
    store = _make_store()
    analysis = _make_analysis(
        product_url="https://example.com/products/x",
        product_price=Decimal("19.50"),
    )
    session = _mock_db_with_data(store=store, products=[], analyses=[analysis])
    client = _get_client(session)
    resp = client.get("/store/example.com")

    a = resp.json()["analyses"]["https://example.com/products/x"]
    assert a["productPrice"] == "19.50"

    app.dependency_overrides.clear()


def test_product_price_none_when_null():
    """Null product_price serialized as None/null."""
    store = _make_store()
    analysis = _make_analysis(
        product_url="https://example.com/products/y",
        product_price=None,
    )
    session = _mock_db_with_data(store=store, products=[], analyses=[analysis])
    client = _get_client(session)
    resp = client.get("/store/example.com")

    a = resp.json()["analyses"]["https://example.com/products/y"]
    assert a["productPrice"] is None

    app.dependency_overrides.clear()


def test_uuid_serialized_as_string():
    """UUIDs must come back as strings, not as UUID objects."""
    store_id = uuid.uuid4()
    store = _make_store(id_=store_id)
    session = _mock_db_with_data(store=store, products=[], analyses=[])
    client = _get_client(session)
    resp = client.get("/store/example.com")

    data = resp.json()
    assert isinstance(data["store"]["id"], str)
    assert data["store"]["id"] == str(store_id)

    app.dependency_overrides.clear()


def test_store_empty_products_and_analyses():
    """Store exists but has no products or analyses."""
    store = _make_store()
    session = _mock_db_with_data(store=store, products=[], analyses=[])
    client = _get_client(session)
    resp = client.get("/store/example.com")

    data = resp.json()
    assert data["products"] == []
    assert data["analyses"] == {}

    app.dependency_overrides.clear()

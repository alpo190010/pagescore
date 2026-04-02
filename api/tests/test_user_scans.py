"""Tests for GET /user/scans endpoint."""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user_optional, get_current_user_required
from app.database import get_db
from app.main import app
from app.models import Scan, User


# -- Helpers ----------------------------------------------------------------


def _make_user() -> User:
    """Build a User ORM instance without touching a real DB."""
    user = User()
    user.id = uuid.uuid4()
    user.google_sub = "google-sub-test"
    user.email = "test@example.com"
    user.name = "Test User"
    user.picture = None
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


def _make_scan(
    user_id: uuid.UUID,
    url: str = "https://example.com/product",
    score: int = 72,
    product_category: str = "fashion",
    created_at: datetime | None = None,
) -> MagicMock:
    """Build a mock Scan ORM instance."""
    scan = MagicMock(spec=Scan)
    scan.id = uuid.uuid4()
    scan.url = url
    scan.score = score
    scan.product_category = product_category
    scan.user_id = user_id
    scan.created_at = created_at or datetime.now(timezone.utc)
    return scan


def _mock_db_with_scans(scans: list) -> MagicMock:
    """Return a mock Session whose query chain returns the given scans."""
    session = MagicMock()
    chain = session.query.return_value
    chain = chain.filter.return_value
    chain = chain.order_by.return_value
    chain.limit.return_value.all.return_value = scans
    return session


# -- Tests ------------------------------------------------------------------


class TestGetUserScans:
    """Integration tests for GET /user/scans."""

    def test_returns_user_scans_with_correct_shape(self):
        """Authenticated user with scans → returns list with expected keys."""
        user = _make_user()
        scan = _make_scan(user.id, url="https://shop.com/tee", score=85)

        db = _mock_db_with_scans([scan])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user_required] = lambda: user

        client = TestClient(app)
        resp = client.get("/user/scans")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        item = data[0]
        assert item["id"] == str(scan.id)
        assert item["url"] == "https://shop.com/tee"
        assert item["score"] == 85
        assert item["productCategory"] == "fashion"
        assert "createdAt" in item

        app.dependency_overrides.clear()

    def test_no_auth_returns_401(self):
        """No auth header → 401."""
        # Don't override get_current_user_required — let it hit the real
        # dependency chain, which calls get_current_user_optional → None → 401.
        # We need to override get_db so it doesn't try to connect to a real DB.
        db = MagicMock()
        app.dependency_overrides[get_db] = lambda: db
        # Override the optional dep to return None (simulating no auth header)
        app.dependency_overrides[get_current_user_optional] = lambda: None

        client = TestClient(app)
        resp = client.get("/user/scans")

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Authentication required"

        app.dependency_overrides.clear()

    def test_returns_scans_in_desc_order(self):
        """Scans are returned with newest first (order_by created_at desc)."""
        user = _make_user()
        now = datetime.now(timezone.utc)
        old_scan = _make_scan(
            user.id, url="https://shop.com/old", score=60,
            created_at=now - timedelta(hours=2),
        )
        new_scan = _make_scan(
            user.id, url="https://shop.com/new", score=90,
            created_at=now,
        )
        # DB returns in desc order (mock mirrors what the query would produce)
        db = _mock_db_with_scans([new_scan, old_scan])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user_required] = lambda: user

        client = TestClient(app)
        resp = client.get("/user/scans")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["url"] == "https://shop.com/new"
        assert data[1]["url"] == "https://shop.com/old"

        app.dependency_overrides.clear()

    def test_no_scans_returns_empty_list(self):
        """Authenticated user with no scans → empty list."""
        user = _make_user()
        db = _mock_db_with_scans([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user_required] = lambda: user

        client = TestClient(app)
        resp = client.get("/user/scans")

        assert resp.status_code == 200
        assert resp.json() == []

        app.dependency_overrides.clear()

    def test_scan_id_is_string(self):
        """Scan IDs are returned as strings, not UUID objects."""
        user = _make_user()
        scan = _make_scan(user.id)
        db = _mock_db_with_scans([scan])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user_required] = lambda: user

        client = TestClient(app)
        resp = client.get("/user/scans")

        data = resp.json()
        assert isinstance(data[0]["id"], str)

        app.dependency_overrides.clear()

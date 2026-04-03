"""Tests for admin user impersonation API endpoints.

Covers:
  POST /admin/impersonate/{user_id}   — mint JWT as target user
  POST /admin/stop-impersonation      — validate & end impersonation

Follows the same MagicMock + dependency_overrides pattern as test_admin_users.py.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user_admin, get_current_user_optional, get_current_user_required
from app.config import settings
from app.database import get_db
from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_SECRET = "test-secret-for-jwt-impersonation-32bytes!"


def _make_user(**overrides):
    """Build a mock user with default fields."""
    defaults = {
        "id": uuid.uuid4(),
        "email": "user@example.com",
        "name": "Test User",
        "role": "user",
        "plan_tier": "free",
        "credits_used": 0,
        "email_verified": False,
        "password_hash": "hashed_pw_123",
        "picture": None,
        "google_sub": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)

    user = MagicMock()
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _make_admin(**overrides):
    """Convenience: admin user for auth dependency."""
    defaults = {"role": "admin", "email": "admin@example.com", "name": "Admin User"}
    defaults.update(overrides)
    return _make_user(**defaults)


def _mock_db_for_detail(user):
    """Mock DB session that returns a single user from .first()."""
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = user
    return mock_db


# ---------------------------------------------------------------------------
# POST /admin/impersonate/{user_id}
# ---------------------------------------------------------------------------


class TestImpersonate:
    """Tests for POST /admin/impersonate/{user_id}."""

    def setup_method(self):
        app.dependency_overrides.clear()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_impersonate_success_returns_jwt_and_user(self):
        """Success: returns a JWT token and the target user info."""
        target_id = uuid.uuid4()
        target = _make_user(id=target_id, email="target@example.com", name="Target User")
        admin = _make_admin()

        app.dependency_overrides[get_db] = lambda: _mock_db_for_detail(target)
        app.dependency_overrides[get_current_user_admin] = lambda: admin

        with patch.object(settings, "auth_secret", TEST_SECRET):
            client = TestClient(app)
            resp = client.post(f"/admin/impersonate/{target_id}")

        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["user"]["id"] == str(target_id)
        assert data["user"]["email"] == "target@example.com"
        assert data["user"]["name"] == "Target User"

    def test_impersonate_jwt_has_correct_claims(self):
        """Returned JWT is decodable and carries sub, impersonator, email, name, exp."""
        target_id = uuid.uuid4()
        admin_id = uuid.uuid4()
        target = _make_user(id=target_id, email="target@example.com", name="Target User")
        admin = _make_admin(id=admin_id)

        app.dependency_overrides[get_db] = lambda: _mock_db_for_detail(target)
        app.dependency_overrides[get_current_user_admin] = lambda: admin

        with patch.object(settings, "auth_secret", TEST_SECRET):
            client = TestClient(app)
            resp = client.post(f"/admin/impersonate/{target_id}")

        assert resp.status_code == 200
        token = resp.json()["token"]

        decoded = jwt.decode(token, TEST_SECRET, algorithms=["HS256"])
        assert decoded["sub"] == str(target_id)
        assert decoded["impersonator"] == str(admin_id)
        assert decoded["email"] == "target@example.com"
        assert decoded["name"] == "Target User"
        # 1h expiry: exp - iat should be ~3600s
        assert decoded["exp"] - decoded["iat"] == 3600

    def test_impersonate_target_not_found(self):
        """Non-existent target user → 404."""
        target_id = uuid.uuid4()
        admin = _make_admin()

        app.dependency_overrides[get_db] = lambda: _mock_db_for_detail(None)
        app.dependency_overrides[get_current_user_admin] = lambda: admin

        client = TestClient(app)
        resp = client.post(f"/admin/impersonate/{target_id}")

        assert resp.status_code == 404
        assert resp.json()["detail"] == "User not found"

    def test_impersonate_invalid_uuid(self):
        """Invalid UUID path param → 400."""
        admin = _make_admin()

        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[get_current_user_admin] = lambda: admin

        client = TestClient(app)
        resp = client.post("/admin/impersonate/not-a-uuid")

        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid user ID format"

    def test_impersonate_self_blocked(self):
        """Admin cannot impersonate themselves → 400."""
        admin_id = uuid.uuid4()
        admin = _make_admin(id=admin_id)

        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[get_current_user_admin] = lambda: admin

        client = TestClient(app)
        resp = client.post(f"/admin/impersonate/{admin_id}")

        assert resp.status_code == 400
        assert resp.json()["detail"] == "Cannot impersonate yourself"

    def test_impersonate_non_admin_forbidden(self):
        """Non-admin user → 403 via get_current_user_admin."""
        non_admin = _make_user(role="user")

        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[get_current_user_required] = lambda: non_admin

        client = TestClient(app)
        resp = client.post(f"/admin/impersonate/{uuid.uuid4()}")

        assert resp.status_code == 403
        assert resp.json()["detail"] == "Admin access required"

    def test_impersonate_unauthenticated(self):
        """No auth → 401 via get_current_user_required."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[get_current_user_optional] = lambda: None

        client = TestClient(app)
        resp = client.post(f"/admin/impersonate/{uuid.uuid4()}")

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Authentication required"


# ---------------------------------------------------------------------------
# POST /admin/stop-impersonation
# ---------------------------------------------------------------------------


class TestStopImpersonation:
    """Tests for POST /admin/stop-impersonation."""

    def setup_method(self):
        app.dependency_overrides.clear()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_stop_impersonation_success(self):
        """Valid impersonation token → 200 with acknowledgment."""
        admin_id = uuid.uuid4()
        target_id = uuid.uuid4()
        token = jwt.encode(
            {
                "sub": str(target_id),
                "impersonator": str(admin_id),
                "email": "target@example.com",
                "name": "Target User",
            },
            TEST_SECRET,
            algorithm="HS256",
        )

        with patch.object(settings, "auth_secret", TEST_SECRET):
            client = TestClient(app)
            resp = client.post(
                "/admin/stop-impersonation",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        assert resp.json()["message"] == "Impersonation ended"

    def test_stop_impersonation_missing_impersonator_claim(self):
        """Token without impersonator claim → 400."""
        token = jwt.encode(
            {"sub": str(uuid.uuid4()), "email": "user@example.com"},
            TEST_SECRET,
            algorithm="HS256",
        )

        with patch.object(settings, "auth_secret", TEST_SECRET):
            client = TestClient(app)
            resp = client.post(
                "/admin/stop-impersonation",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 400
        assert "impersonator" in resp.json()["detail"].lower()

    def test_stop_impersonation_unauthenticated(self):
        """No auth header → 401."""
        client = TestClient(app)
        resp = client.post("/admin/stop-impersonation")

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Authentication required"

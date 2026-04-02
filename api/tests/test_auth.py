"""Tests for JWT authentication dependencies."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.models import User

# -- Helpers ----------------------------------------------------------------

TEST_SECRET = "test-auth-secret-for-unit-tests"
TEST_GOOGLE_SUB = "google-sub-12345"


def _make_user(google_sub: str = TEST_GOOGLE_SUB) -> User:
    """Build a User ORM instance without touching a real DB."""
    user = User()
    user.id = uuid.uuid4()
    user.google_sub = google_sub
    user.email = "test@example.com"
    user.name = "Test User"
    user.picture = None
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


def _encode_jwt(
    payload: dict,
    secret: str = TEST_SECRET,
    algorithm: str = "HS256",
) -> str:
    return jwt.encode(payload, secret, algorithm=algorithm)


def _make_valid_token(
    sub: str = TEST_GOOGLE_SUB,
    exp_delta: timedelta | None = None,
) -> str:
    """Create a valid (or expired) JWT token."""
    payload: dict = {"sub": sub}
    if exp_delta is not None:
        payload["exp"] = datetime.now(timezone.utc) + exp_delta
    else:
        # Default: expires in 1 hour
        payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=1)
    return _encode_jwt(payload)


def _make_request(authorization: str | None = None) -> MagicMock:
    """Simulate a FastAPI Request with optional Authorization header."""
    request = MagicMock()
    headers: dict[str, str] = {}
    if authorization is not None:
        headers["authorization"] = authorization
    request.headers = headers
    return request


def _make_db_session(user: User | None = None) -> MagicMock:
    """Simulate a SQLAlchemy Session.query(...).filter(...).first() chain."""
    session = MagicMock()
    query = session.query.return_value
    query.filter.return_value.first.return_value = user
    return session


# -- get_current_user_optional tests ----------------------------------------


class TestGetCurrentUserOptional:
    """Test the optional auth dependency — must never raise."""

    @patch("app.auth.settings")
    def test_valid_jwt_known_user(self, mock_settings):
        """Valid JWT with a matching user in DB → returns User."""
        from app.auth import get_current_user_optional

        mock_settings.auth_secret = TEST_SECRET
        user = _make_user()
        token = _make_valid_token()
        request = _make_request(f"Bearer {token}")
        db = _make_db_session(user)

        result = get_current_user_optional(request, db)

        assert result is user
        db.query.assert_called_once_with(User)

    @patch("app.auth.settings")
    def test_valid_jwt_unknown_sub(self, mock_settings):
        """Valid JWT but google_sub not in DB → returns None."""
        from app.auth import get_current_user_optional

        mock_settings.auth_secret = TEST_SECRET
        token = _make_valid_token(sub="unknown-sub-99999")
        request = _make_request(f"Bearer {token}")
        db = _make_db_session(user=None)

        result = get_current_user_optional(request, db)

        assert result is None

    @patch("app.auth.settings")
    def test_expired_jwt(self, mock_settings):
        """Expired JWT → returns None."""
        from app.auth import get_current_user_optional

        mock_settings.auth_secret = TEST_SECRET
        token = _make_valid_token(exp_delta=timedelta(hours=-1))
        request = _make_request(f"Bearer {token}")
        db = _make_db_session()

        result = get_current_user_optional(request, db)

        assert result is None

    @patch("app.auth.settings")
    def test_malformed_jwt(self, mock_settings):
        """Completely invalid token string → returns None."""
        from app.auth import get_current_user_optional

        mock_settings.auth_secret = TEST_SECRET
        request = _make_request("Bearer not-a-real-jwt")
        db = _make_db_session()

        result = get_current_user_optional(request, db)

        assert result is None

    @patch("app.auth.settings")
    def test_empty_string_token(self, mock_settings):
        """Bearer prefix followed by empty string → returns None."""
        from app.auth import get_current_user_optional

        mock_settings.auth_secret = TEST_SECRET
        request = _make_request("Bearer ")
        db = _make_db_session()

        result = get_current_user_optional(request, db)

        assert result is None

    @patch("app.auth.settings")
    def test_jwt_signed_with_wrong_key(self, mock_settings):
        """JWT signed with a different secret → returns None."""
        from app.auth import get_current_user_optional

        mock_settings.auth_secret = TEST_SECRET
        token = _encode_jwt(
            {"sub": TEST_GOOGLE_SUB, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            secret="completely-different-secret",
        )
        request = _make_request(f"Bearer {token}")
        db = _make_db_session()

        result = get_current_user_optional(request, db)

        assert result is None

    @patch("app.auth.settings")
    def test_missing_authorization_header(self, mock_settings):
        """No Authorization header → returns None."""
        from app.auth import get_current_user_optional

        mock_settings.auth_secret = TEST_SECRET
        request = _make_request(authorization=None)
        db = _make_db_session()

        result = get_current_user_optional(request, db)

        assert result is None

    @patch("app.auth.settings")
    def test_empty_auth_secret(self, mock_settings):
        """auth_secret is empty string → returns None immediately."""
        from app.auth import get_current_user_optional

        mock_settings.auth_secret = ""
        token = _make_valid_token()
        request = _make_request(f"Bearer {token}")
        db = _make_db_session(_make_user())

        result = get_current_user_optional(request, db)

        assert result is None
        # Should not even touch the DB
        db.query.assert_not_called()

    @patch("app.auth.settings")
    def test_authorization_without_bearer_prefix(self, mock_settings):
        """Authorization header without 'Bearer' prefix → returns None."""
        from app.auth import get_current_user_optional

        mock_settings.auth_secret = TEST_SECRET
        token = _make_valid_token()
        request = _make_request(f"Token {token}")
        db = _make_db_session()

        result = get_current_user_optional(request, db)

        assert result is None

    @patch("app.auth.settings")
    def test_bearer_prefix_no_token(self, mock_settings):
        """Just 'Bearer' with no token after it → returns None."""
        from app.auth import get_current_user_optional

        mock_settings.auth_secret = TEST_SECRET
        request = _make_request("Bearer")
        db = _make_db_session()

        result = get_current_user_optional(request, db)

        assert result is None

    @patch("app.auth.settings")
    def test_jwt_missing_sub_claim(self, mock_settings):
        """Valid JWT structure but no 'sub' claim → returns None."""
        from app.auth import get_current_user_optional

        mock_settings.auth_secret = TEST_SECRET
        token = _encode_jwt(
            {"email": "test@example.com", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        )
        request = _make_request(f"Bearer {token}")
        db = _make_db_session()

        result = get_current_user_optional(request, db)

        assert result is None


# -- get_current_user_required tests ----------------------------------------


class TestGetCurrentUserRequired:
    """Test the required auth dependency — must raise 401 when no user."""

    def test_returns_user_when_provided(self):
        """When user is not None → returns the user."""
        from app.auth import get_current_user_required

        user = _make_user()
        result = get_current_user_required(user)

        assert result is user

    def test_raises_401_when_none(self):
        """When user is None → raises HTTPException 401."""
        from app.auth import get_current_user_required

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_required(None)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Authentication required"

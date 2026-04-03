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
TEST_USER_UUID = uuid.UUID("d4f8a2b1-c3e5-4a6b-9d7f-8e2c1a3b5d6e")


def _make_user(
    google_sub: str = TEST_GOOGLE_SUB,
    user_id: uuid.UUID = TEST_USER_UUID,
    role: str = "user",
) -> User:
    """Build a User ORM instance without touching a real DB."""
    user = User()
    user.id = user_id
    user.google_sub = google_sub
    user.email = "test@example.com"
    user.name = "Test User"
    user.picture = None
    user.role = role
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
    sub: str = str(TEST_USER_UUID),
    exp_delta: timedelta | None = None,
) -> str:
    """Create a valid (or expired) JWT token.

    Default sub is now the Postgres UUID string so that tests exercise the
    UUID-first resolution path by default.
    """
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


def _make_db_session(*filter_results: User | None) -> MagicMock:
    """Simulate a SQLAlchemy Session supporting sequential filter().first() calls.

    Each positional argument corresponds to the return value of one
    ``db.query(User).filter(...).first()`` call, in the order they happen
    at runtime:

    * ``_make_db_session(user)``       — first (only) filter call returns *user*
    * ``_make_db_session(None, user)``  — first returns None, second returns *user*
    * ``_make_db_session(None, None)``  — both miss
    * ``_make_db_session()``           — no filter calls expected (safe fallback)
    """
    session = MagicMock()
    query_mock = session.query.return_value

    if filter_results:
        filters = []
        for result in filter_results:
            f = MagicMock()
            f.first.return_value = result
            filters.append(f)
        query_mock.filter.side_effect = filters
    else:
        # Safe fallback for tests that never exercise the DB path.
        query_mock.filter.return_value.first.return_value = None

    return session


# -- get_current_user_optional tests ----------------------------------------


class TestGetCurrentUserOptional:
    """Test the optional auth dependency — must never raise."""

    @patch("app.auth.settings")
    def test_valid_jwt_known_user(self, mock_settings):
        """Valid JWT with UUID sub matching a user in DB → returns User."""
        from app.auth import get_current_user_optional

        mock_settings.auth_secret = TEST_SECRET
        user = _make_user()
        token = _make_valid_token()  # sub = str(TEST_USER_UUID)
        request = _make_request(f"Bearer {token}")
        db = _make_db_session(user)  # UUID hit on first filter

        result = get_current_user_optional(request, db)

        assert result is user
        db.query.assert_called_once_with(User)

    @patch("app.auth.settings")
    def test_valid_jwt_unknown_sub(self, mock_settings):
        """Valid JWT but sub (UUID) not in DB and no google_sub match → returns None."""
        from app.auth import get_current_user_optional

        mock_settings.auth_secret = TEST_SECRET
        unknown_uuid = str(uuid.uuid4())
        token = _make_valid_token(sub=unknown_uuid)
        request = _make_request(f"Bearer {token}")
        db = _make_db_session(None, None)  # UUID miss, google_sub miss

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
        db = _make_db_session(_make_user())  # would match, but DB never hit

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

    # -- UUID-first / google_sub-fallback tests ---

    @patch("app.auth.settings")
    def test_legacy_google_sub_fallback(self, mock_settings):
        """Non-UUID sub (legacy Google session) falls through to google_sub lookup."""
        from app.auth import get_current_user_optional

        mock_settings.auth_secret = TEST_SECRET
        user = _make_user(google_sub="117893425672834")
        token = _make_valid_token(sub="117893425672834")
        request = _make_request(f"Bearer {token}")
        # UUID parse fails → only google_sub filter runs → returns user
        db = _make_db_session(user)

        result = get_current_user_optional(request, db)

        assert result is user

    @patch("app.auth.settings")
    def test_uuid_sub_not_in_db_no_fallback(self, mock_settings):
        """Valid UUID sub not in DB, no google_sub match either → returns None."""
        from app.auth import get_current_user_optional

        mock_settings.auth_secret = TEST_SECRET
        nonexistent_uuid = str(uuid.uuid4())
        token = _make_valid_token(sub=nonexistent_uuid)
        request = _make_request(f"Bearer {token}")
        db = _make_db_session(None, None)  # UUID miss, google_sub miss

        result = get_current_user_optional(request, db)

        assert result is None

    @patch("app.auth.settings")
    def test_malformed_sub_no_match(self, mock_settings):
        """Arbitrary non-UUID, non-google_sub string → returns None."""
        from app.auth import get_current_user_optional

        mock_settings.auth_secret = TEST_SECRET
        token = _make_valid_token(sub="random-garbage-string")
        request = _make_request(f"Bearer {token}")
        db = _make_db_session(None)  # only google_sub filter runs → miss

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


# -- get_current_user_admin tests -------------------------------------------


class TestGetCurrentUserAdmin:
    """Test the admin auth dependency — must raise 403 for non-admins."""

    def test_returns_admin_user(self):
        """Admin user passes through → returns the user."""
        from app.auth import get_current_user_admin

        user = _make_user(role="admin")
        result = get_current_user_admin(user)

        assert result is user

    def test_raises_403_for_non_admin(self):
        """User with role='user' → raises HTTPException 403."""
        from app.auth import get_current_user_admin

        user = _make_user(role="user")

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_admin(user)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Admin access required"

    def test_raises_401_when_no_user(self):
        """Unauthenticated (None from upstream) → raises 401 from required dep."""
        from app.auth import get_current_user_required

        with pytest.raises(HTTPException) as exc_info:
            # Simulating the dependency chain: required dep raises before admin dep runs
            get_current_user_required(None)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Authentication required"

"""Tests for all auth endpoints (original 6 POST + 3 account-management)."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.auth import get_current_user_required
from app.main import app
from app.models import User


# -- Helpers ----------------------------------------------------------------


def _make_user(
    *,
    email: str = "test@example.com",
    name: str = "Test User",
    password_hash: str | None = "$2b$12$hashedpassword",
    email_verified: bool = True,
    google_sub: str | None = None,
    verification_token: str | None = None,
    verification_token_expires_at: datetime | None = None,
    reset_token: str | None = None,
    reset_token_expires_at: datetime | None = None,
    picture: str | None = None,
    role: str = "user",
) -> User:
    """Build a User ORM instance without touching a real DB."""
    user = User()
    user.id = uuid.uuid4()
    user.email = email
    user.name = name
    user.password_hash = password_hash
    user.email_verified = email_verified
    user.google_sub = google_sub
    user.picture = picture
    user.role = role
    user.verification_token = verification_token
    user.verification_token_expires_at = verification_token_expires_at
    user.reset_token = reset_token
    user.reset_token_expires_at = reset_token_expires_at
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


def _mock_session() -> MagicMock:
    """Return a mock DB session with query/add/commit/refresh stubs."""
    session = MagicMock()
    # Default: query().filter().first() returns None
    session.query.return_value.filter.return_value.first.return_value = None
    return session


def _client_with_db(session: MagicMock) -> TestClient:
    """Create a TestClient with the given mock session as get_db override."""
    app.dependency_overrides[get_db] = lambda: session
    return TestClient(app)


def _cleanup():
    app.dependency_overrides.clear()


# -- Signup tests -----------------------------------------------------------


class TestSignup:
    """POST /auth/signup"""

    def teardown_method(self):
        _cleanup()

    @patch("app.routers.auth_routes.send_email", return_value=True)
    @patch("app.routers.auth_routes.hash_password", return_value="$2b$12$hashed")
    @patch("app.routers.auth_routes.generate_token", return_value="test-token-123")
    def test_successful_signup(self, mock_token, mock_hash, mock_email):
        db = _mock_session()
        client = _client_with_db(db)

        resp = client.post(
            "/auth/signup",
            json={"email": "new@example.com", "password": "Secure123"},
        )

        assert resp.status_code == 201
        assert resp.json() == {
            "message": "Check your email to verify your account"
        }
        db.add.assert_called_once()
        db.commit.assert_called_once()
        mock_email.assert_called_once()
        # Verify the email was sent to the right address
        assert mock_email.call_args[0][1] == "new@example.com"

    @patch("app.routers.auth_routes.send_email", return_value=True)
    @patch("app.routers.auth_routes.hash_password", return_value="$2b$12$hashed")
    @patch("app.routers.auth_routes.generate_token", return_value="test-token-123")
    def test_signup_with_name(self, mock_token, mock_hash, mock_email):
        db = _mock_session()
        client = _client_with_db(db)

        resp = client.post(
            "/auth/signup",
            json={
                "email": "named@example.com",
                "password": "Secure123",
                "name": "Alice",
            },
        )

        assert resp.status_code == 201
        assert resp.json()["message"] == "Check your email to verify your account"
        # Verify the user object was created with name
        added_user = db.add.call_args[0][0]
        assert added_user.name == "Alice"

    def test_signup_duplicate_email(self):
        db = _mock_session()
        existing = _make_user(email="dup@example.com")
        db.query.return_value.filter.return_value.first.return_value = existing
        client = _client_with_db(db)

        resp = client.post(
            "/auth/signup",
            json={"email": "dup@example.com", "password": "Secure123"},
        )

        assert resp.status_code == 409
        assert resp.json()["detail"] == "An account with this email already exists"

    def test_signup_password_too_short(self):
        db = _mock_session()
        client = _client_with_db(db)

        resp = client.post(
            "/auth/signup",
            json={"email": "new@example.com", "password": "Sh0rt"},
        )

        assert resp.status_code == 400
        assert "8 characters" in resp.json()["detail"]

    def test_signup_password_no_letter(self):
        db = _mock_session()
        client = _client_with_db(db)

        resp = client.post(
            "/auth/signup",
            json={"email": "new@example.com", "password": "12345678"},
        )

        assert resp.status_code == 400
        assert "letter" in resp.json()["detail"]

    def test_signup_password_no_number(self):
        db = _mock_session()
        client = _client_with_db(db)

        resp = client.post(
            "/auth/signup",
            json={"email": "new@example.com", "password": "abcdefgh"},
        )

        assert resp.status_code == 400
        assert "number" in resp.json()["detail"]

    @patch("app.routers.auth_routes.send_email", return_value=False)
    @patch("app.routers.auth_routes.hash_password", return_value="$2b$12$hashed")
    @patch("app.routers.auth_routes.generate_token", return_value="test-token-123")
    def test_signup_email_failure_still_succeeds(
        self, mock_token, mock_hash, mock_email
    ):
        """Signup returns 201 even when email send fails (per failure modes)."""
        db = _mock_session()
        client = _client_with_db(db)

        resp = client.post(
            "/auth/signup",
            json={"email": "new@example.com", "password": "Secure123"},
        )

        assert resp.status_code == 201
        db.add.assert_called_once()
        db.commit.assert_called_once()


# -- Login tests ------------------------------------------------------------


class TestLogin:
    """POST /auth/login"""

    def teardown_method(self):
        _cleanup()

    @patch("app.routers.auth_routes.verify_password", return_value=True)
    def test_successful_login(self, mock_verify):
        user = _make_user(
            email="user@example.com",
            name="Jane",
            email_verified=True,
            picture="https://img.example.com/jane.jpg",
        )
        db = _mock_session()
        db.query.return_value.filter.return_value.first.return_value = user
        client = _client_with_db(db)

        resp = client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "Secure123"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(user.id)
        assert data["email"] == "user@example.com"
        assert data["name"] == "Jane"
        assert data["picture"] == "https://img.example.com/jane.jpg"
        assert data["email_verified"] is True
        assert data["role"] == "user"

    def test_login_wrong_password(self):
        user = _make_user()
        db = _mock_session()
        db.query.return_value.filter.return_value.first.return_value = user
        client = _client_with_db(db)

        with patch(
            "app.routers.auth_routes.verify_password", return_value=False
        ):
            resp = client.post(
                "/auth/login",
                json={"email": "test@example.com", "password": "WrongPass1"},
            )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid email or password"

    def test_login_nonexistent_email(self):
        db = _mock_session()
        client = _client_with_db(db)

        resp = client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "Whatever1"},
        )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid email or password"

    def test_login_unverified_user(self):
        user = _make_user(email_verified=False)
        db = _mock_session()
        db.query.return_value.filter.return_value.first.return_value = user
        client = _client_with_db(db)

        with patch(
            "app.routers.auth_routes.verify_password", return_value=True
        ):
            resp = client.post(
                "/auth/login",
                json={"email": "test@example.com", "password": "Secure123"},
            )

        assert resp.status_code == 403
        assert resp.json()["detail"] == "Please verify your email before signing in"

    def test_login_google_only_user_no_password(self):
        """Google user with no password_hash → 401 (not 500)."""
        user = _make_user(
            password_hash=None,
            google_sub="google-123",
            email_verified=True,
        )
        db = _mock_session()
        db.query.return_value.filter.return_value.first.return_value = user
        client = _client_with_db(db)

        resp = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "Anything1"},
        )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid email or password"


# -- Verify-email tests -----------------------------------------------------


class TestVerifyEmail:
    """POST /auth/verify-email"""

    def teardown_method(self):
        _cleanup()

    def test_valid_token(self):
        user = _make_user(
            email_verified=False,
            verification_token="valid-token",
            verification_token_expires_at=datetime.now(timezone.utc)
            + timedelta(hours=12),
        )
        db = _mock_session()
        db.query.return_value.filter.return_value.first.return_value = user
        client = _client_with_db(db)

        resp = client.post(
            "/auth/verify-email", json={"token": "valid-token"}
        )

        assert resp.status_code == 200
        assert resp.json() == {"message": "Email verified successfully"}
        assert user.email_verified is True
        assert user.verification_token is None
        assert user.verification_token_expires_at is None
        db.commit.assert_called_once()

    def test_expired_token(self):
        user = _make_user(
            email_verified=False,
            verification_token="expired-token",
            verification_token_expires_at=datetime.now(timezone.utc)
            - timedelta(hours=1),
        )
        db = _mock_session()
        db.query.return_value.filter.return_value.first.return_value = user
        client = _client_with_db(db)

        resp = client.post(
            "/auth/verify-email", json={"token": "expired-token"}
        )

        assert resp.status_code == 400
        assert resp.json()["detail"] == "Verification token has expired"

    def test_invalid_token(self):
        db = _mock_session()
        client = _client_with_db(db)

        resp = client.post(
            "/auth/verify-email", json={"token": "nonexistent-token"}
        )

        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid verification token"


# -- Forgot-password tests --------------------------------------------------


class TestForgotPassword:
    """POST /auth/forgot-password"""

    def teardown_method(self):
        _cleanup()

    @patch("app.routers.auth_routes.send_email", return_value=True)
    @patch("app.routers.auth_routes.generate_token", return_value="reset-tok-abc")
    def test_existing_email(self, mock_token, mock_email):
        user = _make_user(email="found@example.com")
        db = _mock_session()
        db.query.return_value.filter.return_value.first.return_value = user
        client = _client_with_db(db)

        resp = client.post(
            "/auth/forgot-password", json={"email": "found@example.com"}
        )

        assert resp.status_code == 200
        assert (
            resp.json()["message"]
            == "If an account exists with that email, we've sent a password reset link"
        )
        mock_email.assert_called_once()
        assert user.reset_token == "reset-tok-abc"
        db.commit.assert_called_once()

    @patch("app.routers.auth_routes.send_email", return_value=True)
    def test_nonexistent_email_same_response(self, mock_email):
        """Don't leak whether email exists — same 200 response."""
        db = _mock_session()
        client = _client_with_db(db)

        resp = client.post(
            "/auth/forgot-password", json={"email": "ghost@example.com"}
        )

        assert resp.status_code == 200
        assert (
            resp.json()["message"]
            == "If an account exists with that email, we've sent a password reset link"
        )
        mock_email.assert_not_called()


# -- Reset-password tests ---------------------------------------------------


class TestResetPassword:
    """POST /auth/reset-password"""

    def teardown_method(self):
        _cleanup()

    @patch("app.routers.auth_routes.hash_password", return_value="$2b$12$newhash")
    def test_valid_reset(self, mock_hash):
        user = _make_user(
            reset_token="reset-tok",
            reset_token_expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=30),
        )
        db = _mock_session()
        db.query.return_value.filter.return_value.first.return_value = user
        client = _client_with_db(db)

        resp = client.post(
            "/auth/reset-password",
            json={"token": "reset-tok", "password": "NewPass1!"},
        )

        assert resp.status_code == 200
        assert resp.json() == {"message": "Password reset successfully"}
        assert user.password_hash == "$2b$12$newhash"
        assert user.reset_token is None
        assert user.reset_token_expires_at is None
        db.commit.assert_called_once()

    def test_expired_token(self):
        user = _make_user(
            reset_token="old-tok",
            reset_token_expires_at=datetime.now(timezone.utc)
            - timedelta(hours=2),
        )
        db = _mock_session()
        db.query.return_value.filter.return_value.first.return_value = user
        client = _client_with_db(db)

        resp = client.post(
            "/auth/reset-password",
            json={"token": "old-tok", "password": "NewPass1!"},
        )

        assert resp.status_code == 400
        assert resp.json()["detail"] == "Reset token has expired"

    def test_invalid_token(self):
        db = _mock_session()
        client = _client_with_db(db)

        resp = client.post(
            "/auth/reset-password",
            json={"token": "bad-tok", "password": "NewPass1!"},
        )

        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid reset token"

    def test_invalid_new_password(self):
        user = _make_user(
            reset_token="valid-tok",
            reset_token_expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=30),
        )
        db = _mock_session()
        db.query.return_value.filter.return_value.first.return_value = user
        client = _client_with_db(db)

        resp = client.post(
            "/auth/reset-password",
            json={"token": "valid-tok", "password": "short"},
        )

        assert resp.status_code == 400
        assert "8 characters" in resp.json()["detail"]


# -- Google-signin tests ----------------------------------------------------


class TestGoogleSignin:
    """POST /auth/google-signin"""

    def teardown_method(self):
        _cleanup()

    def test_existing_google_user(self):
        user = _make_user(
            google_sub="google-abc",
            email="guser@example.com",
            name="Google User",
            picture="https://img.google.com/pic.jpg",
        )
        db = _mock_session()
        # First query (by google_sub) finds user
        db.query.return_value.filter.return_value.first.return_value = user
        client = _client_with_db(db)

        resp = client.post(
            "/auth/google-signin",
            json={
                "google_sub": "google-abc",
                "email": "guser@example.com",
                "name": "Google User",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(user.id)
        assert data["email"] == "guser@example.com"
        assert data["google_sub"] == "google-abc"
        assert data["email_verified"] is True
        assert data["role"] == "user"

    def test_email_linking(self):
        """Existing email/password user signs in via Google → link accounts."""
        user = _make_user(
            email="link@example.com",
            google_sub=None,
            email_verified=False,
        )
        db = _mock_session()
        # First query (by google_sub) → None, second (by email) → user
        db.query.return_value.filter.return_value.first.side_effect = [
            None,
            user,
        ]
        client = _client_with_db(db)

        resp = client.post(
            "/auth/google-signin",
            json={
                "google_sub": "google-new-sub",
                "email": "link@example.com",
                "name": "Linked",
                "picture": "https://img.google.com/link.jpg",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["google_sub"] == "google-new-sub"
        assert data["email_verified"] is True
        assert data["role"] == "user"
        assert user.google_sub == "google-new-sub"
        assert user.name == "Linked"
        assert user.picture == "https://img.google.com/link.jpg"
        db.commit.assert_called_once()

    def test_brand_new_google_user(self):
        """No existing user at all → create new one."""
        db = _mock_session()
        # Both queries return None
        db.query.return_value.filter.return_value.first.side_effect = [
            None,
            None,
        ]
        client = _client_with_db(db)

        resp = client.post(
            "/auth/google-signin",
            json={
                "google_sub": "google-brand-new",
                "email": "brand@example.com",
                "name": "Newbie",
                "picture": "https://img.google.com/new.jpg",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "brand@example.com"
        assert data["google_sub"] == "google-brand-new"
        assert data["email_verified"] is True
        assert data["role"] == "user"
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_email_linking_without_optional_fields(self):
        """Email linking when name/picture not provided doesn't overwrite."""
        user = _make_user(
            email="keep@example.com",
            name="Original Name",
            picture="https://original.jpg",
            google_sub=None,
        )
        db = _mock_session()
        db.query.return_value.filter.return_value.first.side_effect = [
            None,
            user,
        ]
        client = _client_with_db(db)

        resp = client.post(
            "/auth/google-signin",
            json={
                "google_sub": "google-link",
                "email": "keep@example.com",
            },
        )

        assert resp.status_code == 200
        # name and picture should remain unchanged
        assert user.name == "Original Name"
        assert user.picture == "https://original.jpg"


# -- Helper for authenticated test clients ---------------------------------


def _client_with_user(
    db: MagicMock, user: User
) -> TestClient:
    """Create a TestClient with DB + authenticated user overrides."""
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user_required] = lambda: user
    return TestClient(app)


# -- GET /auth/me tests ----------------------------------------------------


class TestMe:
    """GET /auth/me"""

    def teardown_method(self):
        _cleanup()

    def test_returns_profile_with_password(self):
        user = _make_user(
            email="me@example.com",
            name="Me",
            picture="https://img.example.com/me.jpg",
            password_hash="$2b$12$hashed",
            google_sub=None,
            email_verified=True,
        )
        db = _mock_session()
        client = _client_with_user(db, user)

        resp = client.get("/auth/me")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(user.id)
        assert data["email"] == "me@example.com"
        assert data["name"] == "Me"
        assert data["picture"] == "https://img.example.com/me.jpg"
        assert data["has_password"] is True
        assert data["google_linked"] is False
        assert data["email_verified"] is True

    def test_returns_profile_google_only(self):
        user = _make_user(
            email="google@example.com",
            name="Google User",
            password_hash=None,
            google_sub="google-sub-123",
            email_verified=True,
        )
        db = _mock_session()
        client = _client_with_user(db, user)

        resp = client.get("/auth/me")

        assert resp.status_code == 200
        data = resp.json()
        assert data["has_password"] is False
        assert data["google_linked"] is True

    def test_returns_401_without_auth(self):
        db = _mock_session()
        client = _client_with_db(db)

        resp = client.get("/auth/me")

        assert resp.status_code == 401


# -- POST /auth/set-password tests -----------------------------------------


class TestSetPassword:
    """POST /auth/set-password"""

    def teardown_method(self):
        _cleanup()

    @patch("app.routers.auth_routes.hash_password", return_value="$2b$12$newhash")
    def test_success_google_only_user(self, mock_hash):
        user = _make_user(
            password_hash=None,
            google_sub="google-sub-456",
            email_verified=True,
        )
        db = _mock_session()
        client = _client_with_user(db, user)

        resp = client.post(
            "/auth/set-password",
            json={"password": "NewSecure1"},
        )

        assert resp.status_code == 200
        assert resp.json() == {"message": "Password set successfully"}
        assert user.password_hash == "$2b$12$newhash"
        assert user.email_verified is True
        db.commit.assert_called_once()

    def test_fails_if_password_already_set(self):
        user = _make_user(password_hash="$2b$12$existing")
        db = _mock_session()
        client = _client_with_user(db, user)

        resp = client.post(
            "/auth/set-password",
            json={"password": "NewSecure1"},
        )

        assert resp.status_code == 400
        assert "already set" in resp.json()["detail"]

    def test_fails_weak_password_too_short(self):
        user = _make_user(password_hash=None, google_sub="g-123")
        db = _mock_session()
        client = _client_with_user(db, user)

        resp = client.post(
            "/auth/set-password",
            json={"password": "Sh0rt"},
        )

        assert resp.status_code == 400
        assert "8 characters" in resp.json()["detail"]

    def test_fails_weak_password_no_number(self):
        user = _make_user(password_hash=None, google_sub="g-123")
        db = _mock_session()
        client = _client_with_user(db, user)

        resp = client.post(
            "/auth/set-password",
            json={"password": "abcdefgh"},
        )

        assert resp.status_code == 400
        assert "number" in resp.json()["detail"]

    def test_fails_weak_password_no_letter(self):
        user = _make_user(password_hash=None, google_sub="g-123")
        db = _mock_session()
        client = _client_with_user(db, user)

        resp = client.post(
            "/auth/set-password",
            json={"password": "12345678"},
        )

        assert resp.status_code == 400
        assert "letter" in resp.json()["detail"]

    def test_returns_401_without_auth(self):
        db = _mock_session()
        client = _client_with_db(db)

        resp = client.post(
            "/auth/set-password",
            json={"password": "Secure123"},
        )

        assert resp.status_code == 401

    def test_returns_422_missing_field(self):
        user = _make_user(password_hash=None, google_sub="g-123")
        db = _mock_session()
        client = _client_with_user(db, user)

        resp = client.post("/auth/set-password", json={})

        assert resp.status_code == 422


# -- POST /auth/change-password tests --------------------------------------


class TestChangePassword:
    """POST /auth/change-password"""

    def teardown_method(self):
        _cleanup()

    @patch("app.routers.auth_routes.hash_password", return_value="$2b$12$changed")
    @patch("app.routers.auth_routes.verify_password", return_value=True)
    def test_success(self, mock_verify, mock_hash):
        user = _make_user(password_hash="$2b$12$oldhash")
        db = _mock_session()
        client = _client_with_user(db, user)

        resp = client.post(
            "/auth/change-password",
            json={
                "current_password": "OldPass1",
                "new_password": "NewPass1",
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {"message": "Password changed successfully"}
        assert user.password_hash == "$2b$12$changed"
        db.commit.assert_called_once()

    def test_wrong_current_password(self):
        user = _make_user(password_hash="$2b$12$oldhash")
        db = _mock_session()
        client = _client_with_user(db, user)

        with patch(
            "app.routers.auth_routes.verify_password", return_value=False
        ):
            resp = client.post(
                "/auth/change-password",
                json={
                    "current_password": "WrongPass1",
                    "new_password": "NewPass1",
                },
            )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Incorrect current password"

    def test_fails_no_password_set(self):
        user = _make_user(password_hash=None, google_sub="google-789")
        db = _mock_session()
        client = _client_with_user(db, user)

        resp = client.post(
            "/auth/change-password",
            json={
                "current_password": "Anything1",
                "new_password": "NewPass1",
            },
        )

        assert resp.status_code == 400
        assert "No password set" in resp.json()["detail"]

    @patch("app.routers.auth_routes.verify_password", return_value=True)
    def test_fails_weak_new_password(self, mock_verify):
        user = _make_user(password_hash="$2b$12$oldhash")
        db = _mock_session()
        client = _client_with_user(db, user)

        resp = client.post(
            "/auth/change-password",
            json={
                "current_password": "OldPass1",
                "new_password": "short",
            },
        )

        assert resp.status_code == 400
        assert "8 characters" in resp.json()["detail"]

    def test_returns_401_without_auth(self):
        db = _mock_session()
        client = _client_with_db(db)

        resp = client.post(
            "/auth/change-password",
            json={
                "current_password": "Old1pass",
                "new_password": "New1pass",
            },
        )

        assert resp.status_code == 401

    def test_returns_422_missing_fields(self):
        user = _make_user(password_hash="$2b$12$hash")
        db = _mock_session()
        client = _client_with_user(db, user)

        resp = client.post("/auth/change-password", json={})

        assert resp.status_code == 422

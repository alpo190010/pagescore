"""
Auth service utilities: password hashing, token generation, password validation.

Uses bcrypt for password hashing (12 rounds) and secrets for URL-safe tokens.
"""

import re
import secrets

import bcrypt


def hash_password(password: str) -> str:
    """Hash a password with bcrypt (12 rounds).

    Returns the hash as a UTF-8 string (starts with ``$2b$``).
    """
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Check *password* against a bcrypt *password_hash*.

    Returns ``True`` when the password matches, ``False`` otherwise.
    """
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


def generate_token() -> str:
    """Generate a cryptographically secure URL-safe token (43 chars)."""
    return secrets.token_urlsafe(32)


def validate_password(password: str) -> str | None:
    """Validate password strength.

    Requirements:
    - At least 8 characters
    - Contains at least one letter (a-z, A-Z)
    - Contains at least one digit (0-9)

    Returns ``None`` if the password is valid, or a descriptive error
    message string explaining why the password is too weak.
    """
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[a-zA-Z]", password):
        return "Password must contain at least one letter."
    if not re.search(r"[0-9]", password):
        return "Password must contain at least one number."
    return None

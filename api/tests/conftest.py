"""Shared fixtures for all API tests."""

import pytest

from app.rate_limit import limiter


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset slowapi rate-limit counters before every test.

    Without this, rate limits from one test can bleed into others since
    the in-memory storage is shared across the process.
    """
    limiter.reset()
    yield
    limiter.reset()

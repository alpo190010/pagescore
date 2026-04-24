"""Shared fixtures for all API tests."""

from unittest.mock import patch

import pytest

from app.rate_limit import limiter
from app.services.checkout_flow_simulator import FlowResult
from app.services.checkout_page_parser import unreached


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset slowapi rate-limit counters before every test.

    Without this, rate limits from one test can bleed into others since
    the in-memory storage is shared across the process.
    """
    limiter.reset()
    yield
    limiter.reset()


async def _mock_simulate_checkout_flow(*_args, **_kwargs) -> FlowResult:
    """Replacement for ``simulate_checkout_flow`` during unit tests.

    Returns an immediately-resolved ``unreached()`` result so tests
    don't attempt to launch Playwright/Chromium.
    """
    return FlowResult(
        signals=unreached("disabled_in_tests"),
        final_url=None,
        duration_ms=0,
        variant_id=None,
    )


@pytest.fixture(autouse=True)
def _mock_checkout_flow_simulator():
    """Prevent the checkout flow simulator from launching Playwright during
    unit tests.

    The simulator is autouse-patched at both its module-level name and
    its router-level re-imports, because analyze.py and
    discover_products.py each have their own ``from ... import
    simulate_checkout_flow`` that resolves at import time.

    Integration tests that intentionally want the real simulator
    (``test_checkout_flow.py::test_live_allbirds_reaches_checkout``)
    call ``simulate_checkout_flow`` directly from the service module and
    bypass the router imports, so they aren't affected.
    """
    with patch(
        "app.routers.analyze.simulate_checkout_flow",
        side_effect=_mock_simulate_checkout_flow,
    ), patch(
        "app.routers.discover_products.simulate_checkout_flow",
        side_effect=_mock_simulate_checkout_flow,
    ):
        yield

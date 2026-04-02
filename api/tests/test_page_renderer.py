"""Unit tests for page_renderer — all Playwright internals are mocked."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.page_renderer import render_page


# ---------------------------------------------------------------------------
# Helpers — build the full mock chain once so every test starts clean
# ---------------------------------------------------------------------------

def _build_playwright_mocks(*, page_html: str = "<html><body>OK</body></html>"):
    """Return (mock_async_playwright_ctx, page, browser) wired together.

    The context manager returned by ``async_playwright()`` yields a
    ``playwright`` object whose chain is:
        playwright.chromium.launch()  →  browser
        browser.new_page()            →  page
        page.goto(…)                  →  None
        page.content()                →  html string
        browser.close()               →  None
    """
    page = AsyncMock()
    page.goto = AsyncMock(return_value=None)
    page.content = AsyncMock(return_value=page_html)

    browser = AsyncMock()
    browser.new_page = AsyncMock(return_value=page)
    browser.close = AsyncMock(return_value=None)

    chromium = AsyncMock()
    chromium.launch = AsyncMock(return_value=browser)

    pw = MagicMock()
    pw.chromium = chromium

    # async_playwright() returns an async context-manager that yields `pw`
    ctx_manager = AsyncMock()
    ctx_manager.__aenter__ = AsyncMock(return_value=pw)
    ctx_manager.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock(return_value=ctx_manager)

    return factory, page, browser


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

PATCH_TARGET = "app.services.page_renderer.async_playwright"


@pytest.mark.asyncio
async def test_render_page_happy_path():
    """render_page returns the fully rendered HTML from page.content()."""
    expected_html = "<html><body><div>Rendered</div></body></html>"
    factory, page, browser = _build_playwright_mocks(page_html=expected_html)

    with patch(PATCH_TARGET, factory):
        result = await render_page("https://example.com")

    assert result == expected_html
    page.goto.assert_awaited_once()
    # Verify networkidle wait strategy and that content was read
    call_kwargs = page.goto.call_args
    assert call_kwargs[1]["wait_until"] == "networkidle"
    page.content.assert_awaited_once()


@pytest.mark.asyncio
async def test_render_page_passes_chromium_args():
    """Chromium is launched with --disable-dev-shm-usage, --no-sandbox, --disable-gpu."""
    factory, _page, browser = _build_playwright_mocks()

    with patch(PATCH_TARGET, factory):
        await render_page("https://example.com")

    # Inspect the launch call via the factory chain
    pw = factory.return_value.__aenter__.return_value
    pw.chromium.launch.assert_awaited_once()
    args = pw.chromium.launch.call_args
    assert args[1]["headless"] is True
    launched_args = args[1]["args"]
    assert "--disable-dev-shm-usage" in launched_args
    assert "--no-sandbox" in launched_args
    assert "--disable-gpu" in launched_args


@pytest.mark.asyncio
async def test_render_page_timeout_raises():
    """TimeoutError from page.goto is re-raised with a descriptive message."""
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError

    factory, page, _browser = _build_playwright_mocks()
    page.goto = AsyncMock(side_effect=PlaywrightTimeoutError("Timeout 30000ms exceeded"))

    with patch(PATCH_TARGET, factory):
        with pytest.raises(PlaywrightTimeoutError, match="timed out"):
            await render_page("https://slow-site.example.com", timeout_ms=5000)


@pytest.mark.asyncio
async def test_render_page_chromium_crash_raises_runtime_error():
    """A Playwright Error (e.g. Chromium crash) is wrapped as RuntimeError."""
    from playwright.async_api import Error as PlaywrightError

    factory, _page, browser = _build_playwright_mocks()
    browser.new_page = AsyncMock(side_effect=PlaywrightError("Browser closed unexpectedly"))

    with patch(PATCH_TARGET, factory):
        with pytest.raises(RuntimeError, match="Chromium failed"):
            await render_page("https://example.com")


@pytest.mark.asyncio
async def test_browser_closed_on_success():
    """browser.close() is called after a successful render."""
    factory, _page, browser = _build_playwright_mocks()

    with patch(PATCH_TARGET, factory):
        await render_page("https://example.com")

    browser.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_browser_closed_on_timeout():
    """browser.close() is called even when navigation times out."""
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError

    factory, page, browser = _build_playwright_mocks()
    page.goto = AsyncMock(side_effect=PlaywrightTimeoutError("Timeout"))

    with patch(PATCH_TARGET, factory):
        with pytest.raises(PlaywrightTimeoutError):
            await render_page("https://example.com")

    browser.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_browser_closed_on_chromium_error():
    """browser.close() is called even when Chromium crashes during page creation."""
    from playwright.async_api import Error as PlaywrightError

    factory, _page, browser = _build_playwright_mocks()
    browser.new_page = AsyncMock(side_effect=PlaywrightError("Crash"))

    with patch(PATCH_TARGET, factory):
        with pytest.raises(RuntimeError):
            await render_page("https://example.com")

    browser.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_render_page_custom_timeout():
    """The timeout_ms argument is forwarded to page.goto."""
    factory, page, _browser = _build_playwright_mocks()

    with patch(PATCH_TARGET, factory):
        await render_page("https://example.com", timeout_ms=60_000)

    call_kwargs = page.goto.call_args
    assert call_kwargs[1]["timeout"] == 60_000

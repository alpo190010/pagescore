"""Playwright-based headless Chromium page renderer.

Launches a headless Chromium instance, navigates to a URL, waits for
network-idle, and returns the fully rendered DOM HTML including
JS-loaded content (e.g. review widgets on Shopify pages).
"""

import logging
import time

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

_CHROMIUM_ARGS: list[str] = [
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-gpu",
]


async def render_page(url: str, timeout_ms: int = 30_000) -> str:
    """Render a page with headless Chromium and return the full DOM HTML.

    Navigates with ``networkidle`` wait, but if the page never reaches
    network-idle (common with heavy analytics/tracking scripts), falls
    back to ``domcontentloaded`` + a short settle delay so we still
    capture JS-rendered content like review widgets.

    Args:
        url: The URL to navigate to and render.
        timeout_ms: Maximum time in milliseconds to wait for navigation
            (including networkidle). Defaults to 30 000 ms.

    Returns:
        The fully rendered DOM HTML as a string.

    Raises:
        PlaywrightTimeoutError: If even the fallback navigation fails.
        RuntimeError: If Chromium crashes or cannot start.
    """
    browser = None
    start = time.monotonic()

    async with async_playwright() as pw:
        try:
            browser = await pw.chromium.launch(
                headless=True,
                args=_CHROMIUM_ARGS,
            )
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            except PlaywrightTimeoutError:
                # networkidle never settled (common with analytics-heavy
                # e-commerce pages). The page is already loaded and JS has
                # been running — just give widgets a moment to paint.
                elapsed_ms = (time.monotonic() - start) * 1_000
                logger.warning(
                    "networkidle timed out for %s after %.0f ms — "
                    "capturing current content after settle delay",
                    url,
                    elapsed_ms,
                )
                await page.wait_for_timeout(3_000)

            html = await page.content()

            elapsed_ms = (time.monotonic() - start) * 1_000
            logger.info(
                "Rendered %s in %.0f ms (%d chars)",
                url,
                elapsed_ms,
                len(html),
            )
            return html

        except PlaywrightError as exc:
            elapsed_ms = (time.monotonic() - start) * 1_000
            logger.error(
                "Chromium error rendering %s after %.0f ms: %s",
                url,
                elapsed_ms,
                exc,
            )
            raise RuntimeError(
                f"Chromium failed to render {url}: {exc}"
            ) from exc

        finally:
            if browser is not None:
                await browser.close()

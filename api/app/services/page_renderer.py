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

    Args:
        url: The URL to navigate to and render.
        timeout_ms: Maximum time in milliseconds to wait for navigation
            (including networkidle). Defaults to 30 000 ms.

    Returns:
        The fully rendered DOM HTML as a string.

    Raises:
        PlaywrightTimeoutError: If navigation exceeds *timeout_ms*, re-raised
            with a descriptive message including the URL.
        RuntimeError: If Chromium crashes or cannot start, wrapping the
            underlying Playwright error with context.
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
            await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            html = await page.content()

            elapsed_ms = (time.monotonic() - start) * 1_000
            logger.info(
                "Rendered %s in %.0f ms (%d chars)",
                url,
                elapsed_ms,
                len(html),
            )
            return html

        except PlaywrightTimeoutError:
            elapsed_ms = (time.monotonic() - start) * 1_000
            logger.warning(
                "Timeout rendering %s after %.0f ms", url, elapsed_ms
            )
            raise PlaywrightTimeoutError(
                f"Page render timed out after {timeout_ms} ms for URL: {url}"
            )

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

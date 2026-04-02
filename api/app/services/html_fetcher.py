"""Async HTML fetcher with browser-like headers and page validation."""

import httpx

BROWSER_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

_INVALID_MARKERS = (
    "<title>404",
    "page not found",
    "access denied",
    "403 forbidden",
    "just a moment",
)


async def fetch_page_html(url: str) -> str:
    """Fetch a page's HTML with browser-like headers. Truncates to 15 000 chars."""
    async with httpx.AsyncClient(
        timeout=10.0, follow_redirects=True
    ) as client:
        response = await client.get(url, headers=BROWSER_HEADERS)
        response.raise_for_status()
        return response.text[:15_000]


async def validate_page_html(url: str) -> str | None:
    """Fetch and validate a page. Returns None for errors, short pages, or blocked pages."""
    try:
        html = await fetch_page_html(url)
    except Exception:
        return None

    if len(html) < 500:
        return None

    lower = html.lower()
    for marker in _INVALID_MARKERS:
        if marker in lower:
            return None

    return html

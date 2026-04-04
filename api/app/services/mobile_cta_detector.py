"""Mobile CTA signal detector for Shopify product pages.

Detects add-to-cart buttons via a Shopify-specific CSS selector
cascade, viewport meta tags, sticky CTA class hints, sticky ATC
app fingerprints (Vitals, Cartimize, GSM), and optionally enriches
signals with Playwright-based measurements (bounding box, sticky
scroll check, thumb-zone position).

Layer 1 (HTML / BeautifulSoup) provides baseline signals that score
up to ~65/100.  Layer 2 (Playwright measurements dict) unlocks the
full 100/100 ceiling by confirming rendered dimensions, above-fold
status, sticky behaviour after scroll, and thumb-zone placement.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signals dataclass
# ---------------------------------------------------------------------------


@dataclass
class MobileCtaSignals:
    """Mobile CTA & UX signals extracted from a product page.

    16 fields total:
      - 4 CTA presence fields
      - 2 mobile meta fields
      - 2 HTML-detectable sticky hints
      - 8 Playwright measurement fields (None when unavailable)
    """

    # --- CTA presence (4) ---
    cta_found: bool = False
    """Whether any add-to-cart button was found on the page."""

    cta_text: str | None = None
    """Visible text content of the primary CTA button."""

    cta_count: int = 0
    """Number of add-to-cart buttons found on the page."""

    cta_selector_matched: str | None = None
    """CSS selector pattern that matched the primary CTA."""

    # --- Mobile meta (2) ---
    has_viewport_meta: bool = False
    """``<meta name="viewport" ...>`` tag present."""

    has_responsive_meta: bool = False
    """Viewport meta includes ``width=device-width``."""

    # --- HTML-detectable sticky hints (2) ---
    has_sticky_class: bool = False
    """CSS class names suggesting sticky/fixed positioning for ATC."""

    has_sticky_app: str | None = None
    """Detected sticky ATC app name (e.g. "vitals", "cartimize")."""

    # --- Playwright measurements (8, None when unavailable) ---
    button_width_px: float | None = None
    """Rendered button width in CSS pixels."""

    button_height_px: float | None = None
    """Rendered button height in CSS pixels."""

    meets_min_44px: bool | None = None
    """Button meets 44×44 px minimum (Apple HIG / WCAG 2.5.5)."""

    meets_optimal_60_72px: bool | None = None
    """Button height is in the 60-72 px sweet spot."""

    above_fold: bool | None = None
    """CTA is visible without scrolling on mobile viewport."""

    is_sticky: bool | None = None
    """CTA stays visible after scrolling 600 px (fixed/sticky)."""

    in_thumb_zone: bool | None = None
    """CTA is in the bottom 40 % of the viewport."""

    is_full_width: bool | None = None
    """CTA button width >= 90 % of the viewport width."""


# ---------------------------------------------------------------------------
# CTA selector cascade (Shopify-specific, ordered by specificity)
# ---------------------------------------------------------------------------

# Each entry: (human-readable label, callable that returns Tag | None)
_CTA_SELECTORS: list[tuple[str, object]] = [
    (
        'form[action*="/cart/add"] button[type="submit"]',
        lambda s: s.select_one('form[action*="/cart/add"] button[type="submit"]'),
    ),
    (
        ".product-form__submit",
        lambda s: s.find(class_="product-form__submit"),
    ),
    (
        'button[name="add"]',
        lambda s: s.find("button", attrs={"name": "add"}),
    ),
    (
        "[data-add-to-cart]",
        lambda s: s.find(attrs={"data-add-to-cart": True}),
    ),
    (
        "#AddToCart",
        lambda s: s.find(id="AddToCart"),
    ),
    (
        ".btn--add-to-cart",
        lambda s: s.find(class_="btn--add-to-cart"),
    ),
    (
        ".btn-add-to-cart",
        lambda s: s.find(class_="btn-add-to-cart"),
    ),
    (
        ".add-to-cart",
        lambda s: s.find(class_="add-to-cart"),
    ),
]

# Compiled once — text-content fallback
_ATC_TEXT_RE = re.compile(r"add\s*to\s*cart|buy\s*now", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Sticky class patterns
# ---------------------------------------------------------------------------

_STICKY_CLASS_PATTERNS: list[str] = [
    "sticky-add-to-cart",
    "sticky-atc",
    "sticky-checkout",
    "sticky-buy",
    "fixed-add-to-cart",
    "fixed-atc",
    "sticky-cart-button",
    "mobile-sticky",
    "sticky-bar",
    "fixed-bar",
]

_STICKY_CLASS_RE = re.compile(
    "|".join(re.escape(p) for p in _STICKY_CLASS_PATTERNS),
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Sticky ATC app fingerprints
# ---------------------------------------------------------------------------

# (app_name, css_class_fragments, script_url_fragments)
_STICKY_ATC_APPS: list[tuple[str, list[str], list[str]]] = [
    ("vitals", ["vitals-sticky", "vt-sticky"], ["vitals.co"]),
    ("cartimize", ["cartimize-sticky"], ["cartimize.com"]),
    ("sticky-add-to-cart-bar", ["sticky-atc-bar", "sticky-add-to-cart-bar"], []),
    ("gsm-sticky", ["gsm-sticky"], ["gsm.co"]),
    ("easybar", ["easybar-sticky"], ["easybar"]),
]


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------


def _find_primary_cta(soup: BeautifulSoup) -> tuple[Tag | None, str | None, int]:
    """Find the primary CTA button and count all ATC buttons.

    Returns (primary_tag, selector_label, total_count).
    """
    primary: Tag | None = None
    selector_label: str | None = None
    all_cta_tags: list[Tag] = []

    # Try each selector in priority order
    for label, finder in _CTA_SELECTORS:
        tag = finder(soup)
        if tag is not None:
            if primary is None:
                primary = tag
                selector_label = label
            if tag not in all_cta_tags:
                all_cta_tags.append(tag)

    # Text-content fallback
    for btn in soup.find_all("button"):
        text = btn.get_text(strip=True)
        if _ATC_TEXT_RE.search(text):
            if primary is None:
                primary = btn
                selector_label = "text:add-to-cart"
            if btn not in all_cta_tags:
                all_cta_tags.append(btn)

    # Also check <input type="submit"> inside cart forms
    for inp in soup.select('form[action*="/cart/add"] input[type="submit"]'):
        if primary is None:
            primary = inp
            selector_label = 'form[action*="/cart/add"] input[type="submit"]'
        if inp not in all_cta_tags:
            all_cta_tags.append(inp)

    return primary, selector_label, len(all_cta_tags)


def _detect_viewport_meta(soup: BeautifulSoup) -> tuple[bool, bool]:
    """Detect viewport meta tag and whether it's responsive.

    Returns (has_viewport_meta, has_responsive_meta).
    """
    meta = soup.find("meta", attrs={"name": "viewport"})
    if meta is None:
        return False, False

    content = (meta.get("content") or "").lower()
    responsive = "width=device-width" in content
    return True, responsive


def _detect_sticky_class(soup: BeautifulSoup) -> bool:
    """Check for CSS class names suggesting sticky/fixed ATC positioning."""
    # Check all elements with class attributes
    for tag in soup.find_all(True, class_=True):
        classes = " ".join(tag.get("class", []))
        if _STICKY_CLASS_RE.search(classes):
            return True

    # Check inline styles for position: fixed/sticky on elements near ATC
    for tag in soup.find_all(True, style=True):
        style = (tag.get("style") or "").lower()
        if "position:" in style and ("fixed" in style or "sticky" in style):
            # Only count if it looks like it could be a CTA container
            text = tag.get_text(strip=True).lower()
            if any(kw in text for kw in ("add to cart", "buy now", "add to bag")):
                return True

    return False


def _detect_sticky_app(soup: BeautifulSoup) -> str | None:
    """Detect known sticky ATC Shopify apps via class names or script URLs."""
    # Check classes
    page_classes = " ".join(
        " ".join(tag.get("class", []))
        for tag in soup.find_all(True, class_=True)
    ).lower()

    for app_name, class_fragments, _script_fragments in _STICKY_ATC_APPS:
        for frag in class_fragments:
            if frag in page_classes:
                return app_name

    # Check script URLs
    for script in soup.find_all("script", src=True):
        src = (script.get("src") or "").lower()
        for app_name, _class_fragments, script_fragments in _STICKY_ATC_APPS:
            for frag in script_fragments:
                if frag in src:
                    return app_name

    return None


def _inject_measurements(signals: MobileCtaSignals, measurements: dict) -> None:
    """Populate Playwright measurement fields from a dict."""
    signals.button_width_px = measurements.get("button_width_px")
    signals.button_height_px = measurements.get("button_height_px")
    signals.meets_min_44px = measurements.get("meets_min_44px")
    signals.meets_optimal_60_72px = measurements.get("meets_optimal_60_72px")
    signals.above_fold = measurements.get("above_fold")
    signals.is_sticky = measurements.get("is_sticky")
    signals.in_thumb_zone = measurements.get("in_thumb_zone")
    signals.is_full_width = measurements.get("is_full_width")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_mobile_cta(
    html: str,
    measurements: dict | None = None,
) -> MobileCtaSignals:
    """Extract mobile CTA signals from rendered HTML.

    Args:
        html: Fully rendered DOM HTML string.
        measurements: Optional dict of Playwright-based CTA measurements
            (from :func:`page_renderer.measure_mobile_cta`).  When provided,
            the 8 measurement fields are populated; otherwise they stay None.

    Returns:
        Populated :class:`MobileCtaSignals` instance.
    """
    signals = MobileCtaSignals()
    soup = BeautifulSoup(html, "html.parser")

    # --- CTA detection ---
    primary, selector_label, count = _find_primary_cta(soup)
    signals.cta_found = primary is not None
    signals.cta_count = count
    signals.cta_selector_matched = selector_label

    if primary is not None:
        # Extract text — handle both <button> and <input type="submit">
        if primary.name == "input":
            signals.cta_text = (primary.get("value") or "").strip() or None
        else:
            signals.cta_text = primary.get_text(strip=True) or None

    # --- Viewport meta ---
    signals.has_viewport_meta, signals.has_responsive_meta = _detect_viewport_meta(soup)

    # --- Sticky hints from HTML ---
    signals.has_sticky_class = _detect_sticky_class(soup)
    signals.has_sticky_app = _detect_sticky_app(soup)

    # --- Playwright measurements (optional enrichment) ---
    if measurements is not None and isinstance(measurements, dict):
        _inject_measurements(signals, measurements)

    return signals

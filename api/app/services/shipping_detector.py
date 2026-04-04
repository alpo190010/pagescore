"""Shipping transparency signal detector for Shopify product pages.

Detects free shipping messaging, estimated delivery dates (specific and
vague), EDD app blocks (Synctrack, AfterShip, EDDer), shipping cost
transparency, structured data shippingDetails, shipping policy links,
and returns/refund messaging.

Detection uses 5 cascading extraction layers:
  1. JSON-LD structured data (shippingDetails on Product/Offer)
  2. EDD app block fingerprints (CSS selectors + script URLs)
  3. Shopify theme CSS selectors (Dawn and common themes)
  4. Text pattern matching (regex on visible text, excluding <h1>/<title>)
  5. Link/anchor detection (shipping policy pages)

All signals use standard BeautifulSoup DOM inspection consistent with
:pymod:`social_proof_detector` and :pymod:`checkout_detector`.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signals dataclass
# ---------------------------------------------------------------------------


@dataclass
class ShippingSignals:
    """Shipping transparency signals extracted from a product page.

    10 fields total:
      • 3 free shipping messaging flags
      • 3 estimated delivery date flags
      • 2 shipping cost transparency flags
      • 2 shipping policy accessibility flags
    """

    # --- Free shipping messaging (3) ------------------------------------
    has_free_shipping: bool = False
    """'Free shipping' text, ``.free-shipping-bar``, or equivalent messaging
    detected outside of ``<h1>`` / ``<title>``."""

    has_free_shipping_threshold: bool = False
    """Conditional free shipping with a spend threshold detected
    (e.g. 'Free shipping on orders over $50')."""

    free_shipping_threshold_value: float | None = None
    """Extracted dollar threshold for free shipping, or ``None``."""

    # --- Estimated delivery date (3) ------------------------------------
    has_delivery_date: bool = False
    """Specific delivery date detected ('Arrives by Thu, Feb 12',
    'Get it by March 5')."""

    has_delivery_estimate: bool = False
    """Vague business-day estimate detected ('Ships in 3-5 business days',
    'Delivery in 5-7 days')."""

    has_edd_app: bool = False
    """EDD app block detected (Synctrack, AfterShip EDD, EDDer, or
    similar delivery-date widget)."""

    # --- Shipping cost transparency (2) ---------------------------------
    has_shipping_cost_shown: bool = False
    """Explicit shipping cost or 'calculated at checkout' messaging."""

    has_shipping_in_structured_data: bool = False
    """``shippingDetails`` present in Product/Offer JSON-LD schema."""

    # --- Shipping policy accessibility (2) ------------------------------
    has_shipping_policy_link: bool = False
    """Link to shipping policy page detected."""

    has_returns_mentioned: bool = False
    """Return policy or free returns messaging detected near shipping info."""


# ---------------------------------------------------------------------------
# Constants — fingerprints & patterns
# ---------------------------------------------------------------------------

# EDD app fingerprints: (css_selectors, script_patterns)
_EDD_APP_SELECTORS: list[str] = [
    # Synctrack
    ".synctrack-delivery", "[data-synctrack]", "synctrack-edd",
    # AfterShip EDD
    ".aftership-edd", "[data-aftership-edd]", ".aftership-delivery-date",
    ".aftership-estimated-delivery",
    # EDDer
    ".edder-widget", "[data-edder]", ".edd-widget",
    # OrderlyEmails / Estamate
    ".estamate-delivery", ".orderly-delivery",
]

_EDD_APP_CLASS_FRAGMENTS: list[str] = [
    "delivery-date", "estimated-delivery", "edd-widget", "shipping-eta",
    "delivery-estimate", "estimated-arrival",
]

_EDD_SCRIPT_PATTERNS: list[str] = [
    "synctrack", "aftership", "edder", "estamate",
]

# Shopify theme shipping selectors
_SHIPPING_CSS_SELECTORS: list[str] = [
    ".free-shipping-bar", ".free-shipping", "[data-free-shipping]",
    ".shipping-message", ".product__shipping", ".delivery-info",
    ".product-shipping", ".shipping-info", ".product-delivery",
    "[data-shipping]", ".product__shipping-message",
    ".shipping__information", ".shipping-notice",
    ".announcement-bar",
]

# Compiled regex patterns
_RE_FREE_SHIPPING = re.compile(r"free\s+shipping", re.IGNORECASE)

_RE_THRESHOLD = re.compile(
    r"free\s+shipping\s+(?:on\s+)?(?:orders?\s+)?(?:over|above|for\s+orders?\s+over)\s*"
    r"\$?\s*([\d,]+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)

_RE_SPECIFIC_DATE = re.compile(
    r"(?:arrives?\s+by|get\s+it\s+by|delivery\s+by|delivered\s+by|"
    r"estimated\s+delivery[:\s]+|order\s+.*?get\s+it\s+by)\s*"
    r"(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*[,.]?\s*)?"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}",
    re.IGNORECASE,
)

_RE_SPECIFIC_DATE_ALT = re.compile(
    r"(?:arrives?\s+by|get\s+it\s+by|delivery\s+by|delivered\s+by)\s+"
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)",
    re.IGNORECASE,
)

_RE_VAGUE_ESTIMATE = re.compile(
    r"(?:ships?\s+in|delivery\s+in|shipping\s+takes?|estimated\s+\d|"
    r"ready\s+in|dispatched\s+in)\s*"
    r"\d[\d\s\-\u2013to]+\s*(?:business\s+)?days?",
    re.IGNORECASE,
)

_RE_SHIPPING_COST = re.compile(
    r"(?:shipping[:\s]+\$[\d,.]+|flat[\s-]rate\s+shipping|"
    r"\$[\d,.]+\s+shipping|calculated\s+at\s+checkout|"
    r"shipping\s+calculated|shipping\s+(?:fee|cost)[:\s]+\$[\d,.]+)",
    re.IGNORECASE,
)

_RE_RETURNS = re.compile(
    r"(?:free\s+returns?|easy\s+returns?|hassle[\s-]free\s+returns?|"
    r"\d+[\s-]day\s+return|return\s+policy|money[\s-]back|"
    r"free\s+exchanges?|\d+[\s-]day\s+(?:money[\s-]back|refund))",
    re.IGNORECASE,
)

_SHIPPING_POLICY_HREF_PATTERNS: list[str] = [
    "/policies/shipping",
    "/shipping-policy",
    "/pages/shipping",
    "/shipping-information",
    "/delivery-information",
    "/pages/delivery",
]

_SHIPPING_LINK_TEXT_PATTERNS = re.compile(
    r"shipping\s+(?:policy|info|information|details)|"
    r"delivery\s+(?:policy|info|information)|"
    r"see\s+shipping",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_float(val: object) -> float | None:
    """Convert to float or return None. Never raises."""
    if val is None:
        return None
    try:
        cleaned = str(val).replace(",", "").replace("$", "").strip()
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def _get_visible_text(soup: BeautifulSoup) -> str:
    """Get visible text excluding <h1>, <title>, and <script>/<style> tags."""
    excluded_tags = {"h1", "title", "script", "style", "noscript"}
    parts: list[str] = []
    for element in soup.descendants:
        if isinstance(element, str) and element.parent and hasattr(element.parent, "name"):
            if element.parent.name not in excluded_tags:
                text = element.strip()
                if text:
                    parts.append(text)
    return " ".join(parts)


def _has_class_fragment(tag: Tag, fragments: list[str]) -> bool:
    """Check if any of the tag's CSS classes contain any of the fragments."""
    classes = tag.get("class", [])
    if isinstance(classes, str):
        classes = [classes]
    class_str = " ".join(classes).lower()
    return any(frag in class_str for frag in fragments)


# ---------------------------------------------------------------------------
# Layer 1: JSON-LD structured data
# ---------------------------------------------------------------------------


def _extract_jsonld_shipping(soup: BeautifulSoup, signals: ShippingSignals) -> None:
    """Parse JSON-LD for shippingDetails on Product/Offer."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            _check_jsonld_item(item, signals)
            # Check @graph
            for graph_item in item.get("@graph", []):
                if isinstance(graph_item, dict):
                    _check_jsonld_item(graph_item, signals)


def _check_jsonld_item(item: dict, signals: ShippingSignals) -> None:
    """Check a single JSON-LD item for shipping details."""
    item_type = item.get("@type", "")
    if isinstance(item_type, list):
        item_type = " ".join(item_type)

    if "Product" in str(item_type) or "Offer" in str(item_type):
        if "shippingDetails" in item:
            signals.has_shipping_in_structured_data = True

        # Check offers within Product
        offers = item.get("offers", {})
        if isinstance(offers, dict):
            offers = [offers]
        if isinstance(offers, list):
            for offer in offers:
                if isinstance(offer, dict) and "shippingDetails" in offer:
                    signals.has_shipping_in_structured_data = True


# ---------------------------------------------------------------------------
# Layer 2: EDD app block detection
# ---------------------------------------------------------------------------


def _detect_edd_apps(soup: BeautifulSoup, signals: ShippingSignals) -> None:
    """Detect EDD app blocks by CSS selectors and script URLs."""
    # Check CSS selectors
    for selector in _EDD_APP_SELECTORS:
        if soup.select_one(selector):
            signals.has_edd_app = True
            return

    # Check class name fragments across all elements
    for tag in soup.find_all(True):
        if _has_class_fragment(tag, _EDD_APP_CLASS_FRAGMENTS):
            signals.has_edd_app = True
            return

    # Check script src URLs
    for script in soup.find_all("script", src=True):
        src = str(script.get("src", "")).lower()
        if any(pat in src for pat in _EDD_SCRIPT_PATTERNS):
            signals.has_edd_app = True
            return


# ---------------------------------------------------------------------------
# Layer 3: Shopify theme selectors
# ---------------------------------------------------------------------------


def _detect_theme_shipping(soup: BeautifulSoup, signals: ShippingSignals) -> None:
    """Detect shipping messaging via Shopify theme CSS selectors."""
    for selector in _SHIPPING_CSS_SELECTORS:
        elements = soup.select(selector)
        for el in elements:
            text = el.get_text(strip=True).lower()
            if not text:
                continue

            if _RE_FREE_SHIPPING.search(text):
                signals.has_free_shipping = True
                m = _RE_THRESHOLD.search(text)
                if m:
                    signals.has_free_shipping_threshold = True
                    signals.free_shipping_threshold_value = (
                        _safe_float(m.group(1))
                        or signals.free_shipping_threshold_value
                    )


# ---------------------------------------------------------------------------
# Layer 4: Text pattern matching
# ---------------------------------------------------------------------------


def _detect_text_patterns(soup: BeautifulSoup, signals: ShippingSignals) -> None:
    """Detect shipping signals via regex on visible text (excluding h1/title)."""
    visible_text = _get_visible_text(soup)

    # Free shipping (only if not already found by theme selectors)
    if not signals.has_free_shipping and _RE_FREE_SHIPPING.search(visible_text):
        signals.has_free_shipping = True

    # Free shipping threshold
    if not signals.has_free_shipping_threshold:
        m = _RE_THRESHOLD.search(visible_text)
        if m:
            signals.has_free_shipping = True
            signals.has_free_shipping_threshold = True
            signals.free_shipping_threshold_value = (
                _safe_float(m.group(1))
                or signals.free_shipping_threshold_value
            )

    # Specific delivery date
    if _RE_SPECIFIC_DATE.search(visible_text) or _RE_SPECIFIC_DATE_ALT.search(visible_text):
        signals.has_delivery_date = True

    # Vague delivery estimate
    if not signals.has_delivery_date and _RE_VAGUE_ESTIMATE.search(visible_text):
        signals.has_delivery_estimate = True

    # Shipping cost shown
    if _RE_SHIPPING_COST.search(visible_text):
        signals.has_shipping_cost_shown = True

    # Returns mentioned
    if _RE_RETURNS.search(visible_text):
        signals.has_returns_mentioned = True


# ---------------------------------------------------------------------------
# Layer 5: Link/anchor detection
# ---------------------------------------------------------------------------


def _detect_shipping_links(soup: BeautifulSoup, signals: ShippingSignals) -> None:
    """Detect shipping policy links."""
    for a in soup.find_all("a", href=True):
        href = str(a["href"]).lower()
        if any(pat in href for pat in _SHIPPING_POLICY_HREF_PATTERNS):
            signals.has_shipping_policy_link = True
            return

        text = a.get_text(strip=True)
        if text and _SHIPPING_LINK_TEXT_PATTERNS.search(text):
            signals.has_shipping_policy_link = True
            return


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_shipping(html: str) -> ShippingSignals:
    """Detect shipping transparency signals from rendered product page HTML.

    Scans for free shipping messaging, estimated delivery dates, EDD app
    blocks, shipping cost transparency, structured data, shipping policy
    links, and returns messaging using BeautifulSoup DOM inspection.

    Args:
        html: Rendered HTML string from the product page.

    Returns:
        Populated :class:`ShippingSignals` instance (never raises).
    """
    signals = ShippingSignals()

    if not html:
        return signals

    soup = BeautifulSoup(html, "html.parser")

    # Layer 1: JSON-LD structured data (most reliable)
    _extract_jsonld_shipping(soup, signals)

    # Layer 2: EDD app block detection
    _detect_edd_apps(soup, signals)

    # Layer 3: Shopify theme CSS selectors
    _detect_theme_shipping(soup, signals)

    # Layer 4: Text pattern matching (regex on visible text)
    _detect_text_patterns(soup, signals)

    # Layer 5: Link/anchor detection
    _detect_shipping_links(soup, signals)

    logger.info(
        "shipping signals: free=%s threshold=%s(%s) date=%s estimate=%s "
        "edd_app=%s cost=%s schema=%s policy=%s returns=%s",
        signals.has_free_shipping,
        signals.has_free_shipping_threshold,
        signals.free_shipping_threshold_value,
        signals.has_delivery_date,
        signals.has_delivery_estimate,
        signals.has_edd_app,
        signals.has_shipping_cost_shown,
        signals.has_shipping_in_structured_data,
        signals.has_shipping_policy_link,
        signals.has_returns_mentioned,
    )

    return signals

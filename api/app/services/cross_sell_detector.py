"""Cross-sell & upsell signal detector for Shopify product pages.

Detects cross-sell widgets (Rebuy, Frequently Bought Together / Code
Black Belt, Selleasy, ReConvert, Zipify OCU, Bold Upsell), Shopify
native recommendations, bundle pricing, checkbox selection, "Add all
to cart" CTAs, bundle discounts, and cross-sell proximity to the Add
to Cart button.

All detection uses standard BeautifulSoup DOM inspection and compiled
regex patterns, consistent with the other detectors in this package.
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
class CrossSellSignals:
    """Cross-sell & upsell signals extracted from a product page.

    10 fields total:
      - 1 app detection field
      - 1 section presence field
      - 1 widget type classification field
      - 1 product count field
      - 4 bundle feature fields
      - 1 proximity field
      - 1 optimal count field
    """

    # --- App detection (1) ---
    cross_sell_app: str | None = None
    """Detected cross-sell app name, e.g. "rebuy", "fbt-cbb",
    "selleasy", "reconvert", "zipify", "bold", "shopify-native",
    or None."""

    # --- Section presence (1) ---
    has_cross_sell_section: bool = False
    """Any cross-sell or recommendation section detected on page."""

    # --- Widget type (1) ---
    widget_type: str | None = None
    """Classification: "fbt_bundle" | "simple_recommendation" |
    "bundle_discount" | None."""

    # --- Product count (1) ---
    product_count: int = 0
    """Number of recommended/cross-sell products visible."""

    # --- Bundle features (4) ---
    has_bundle_pricing: bool = False
    """Combined pricing element visible for bundle."""

    has_checkbox_selection: bool = False
    """FBT-style checkboxes for selecting bundle items."""

    has_add_all_to_cart: bool = False
    """"Add all to cart" or "Add bundle to cart" CTA present."""

    has_discount_on_bundle: bool = False
    """Strikethrough original + discounted bundle price visible."""

    # --- Proximity (1) ---
    near_buy_button: bool = False
    """Cross-sell section within proximity of main Add to Cart button."""

    # --- Optimal count (1) ---
    recommendation_count_optimal: bool = False
    """Product count is in the 3-4 sweet spot (avoids paradox of choice)."""


# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

_CROSS_SELL_TEXT_RE = re.compile(
    r"frequently\s+bought\s+together|you\s+may\s+also\s+like|"
    r"customers?\s+also\s+bought|complete\s+the\s+look|"
    r"pair\s+it\s+with|goes?\s+great\s+with|"
    r"recommended\s+for\s+you|related\s+products?|"
    r"bundle\s+(?:and|&)\s+save|buy\s+together|"
    r"you\s+might\s+also\s+like|people\s+also\s+bought|"
    r"more\s+from\s+this\s+collection",
    re.IGNORECASE,
)

_ADD_ALL_RE = re.compile(
    r"add\s+all\s+to\s+cart|add\s+bundle|add\s+(?:selected|these)\s+to\s+cart|"
    r"buy\s+(?:all|bundle)|add\s+\d+\s+items?\s+to\s+cart",
    re.IGNORECASE,
)

_BUNDLE_PRICE_RE = re.compile(
    r"total\s*(?:price|cost)|bundle\s*price|combined\s*price|"
    r"together\s*(?:for|price)|save\s+\$?\d|"
    r"you\s+save|discount|package\s+(?:price|deal)",
    re.IGNORECASE,
)

_STRIKETHROUGH_CLASSES = re.compile(
    r"compare|original|was-price|old-price|line-through|"
    r"price--compare|price-compare|regular-price|strikethrough",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Cross-sell app detection
# ---------------------------------------------------------------------------

# (app_name, css_class_patterns, data_attr_patterns, script_url_patterns)
_CROSS_SELL_APPS: list[tuple[str, list[str], list[str], list[str]]] = [
    (
        "rebuy",
        ["rebuy-widget", "rebuy-product-grid", "rebuy-smart-cart"],
        ["data-rebuy-id"],
        ["rebuyengine.com"],
    ),
    (
        "fbt-cbb",
        ["cbb-frequently-bought-together"],
        [],
        ["codeblackbelt.com"],
    ),
    (
        "selleasy",
        [],
        [],
        ["logbase"],
    ),
    (
        "reconvert",
        ["reconvert"],
        [],
        ["reconvert", "upsell.com"],
    ),
    (
        "zipify",
        ["zipify"],
        [],
        ["zipify"],
    ),
    (
        "bold",
        ["bsub-"],
        [],
        ["boldcommerce.com", "bold-upsell"],
    ),
    (
        "shopify-native",
        ["product-recommendations"],
        ["data-section-type"],
        [],
    ),
]


def _detect_cross_sell_app(soup: BeautifulSoup) -> str | None:
    """Detect known cross-sell app by CSS classes, data attrs, or script URLs."""
    page_str = str(soup).lower()

    for app_name, class_patterns, data_attrs, script_patterns in _CROSS_SELL_APPS:
        # Check CSS classes
        for pattern in class_patterns:
            if soup.find(class_=lambda c: c and any(
                pattern in cls for cls in (c if isinstance(c, list) else [c])
            )):
                return app_name

        # Check data attributes
        for attr in data_attrs:
            if soup.find(attrs={attr: True}):
                # For shopify-native, verify data-section-type="product-recommendations"
                if app_name == "shopify-native":
                    el = soup.find(attrs={attr: "product-recommendations"})
                    if el:
                        return app_name
                else:
                    return app_name

        # Check script URL patterns
        for pattern in script_patterns:
            if pattern in page_str:
                return app_name

    return None


# ---------------------------------------------------------------------------
# Cross-sell section detection
# ---------------------------------------------------------------------------

_SECTION_SELECTORS: list[tuple[str, dict]] = [
    # Rebuy
    ("div", {"attrs": {"data-rebuy-id": True}}),
    # Shopify native
    ("div", {"class_": "product-recommendations"}),
    # Generic section with recommendation-like class
    ("section", {"class_": lambda c: c and any(
        any(kw in cls.lower() for kw in [
            "cross-sell", "upsell", "frequently", "fbt",
            "recommendation", "also-like", "bought-together",
            "related-product", "bundle",
        ]) for cls in (c if isinstance(c, list) else [c])
    )}),
    ("div", {"class_": lambda c: c and any(
        any(kw in cls.lower() for kw in [
            "cross-sell", "upsell", "frequently", "fbt",
            "recommendation", "also-like", "bought-together",
            "related-product", "bundle", "rebuy", "cbb-",
        ]) for cls in (c if isinstance(c, list) else [c])
    )}),
]


def _detect_cross_sell_section(soup: BeautifulSoup) -> Tag | None:
    """Find the cross-sell/recommendation container element.

    Returns the first matching container or None.
    """
    # Priority 1: Known selectors
    for tag_name, attrs in _SECTION_SELECTORS:
        el = soup.find(tag_name, **attrs)
        if el and isinstance(el, Tag):
            return el

    # Priority 2: Sections/divs containing cross-sell heading text
    for heading_tag in ("h2", "h3", "h4", "h5"):
        for heading in soup.find_all(heading_tag):
            text = heading.get_text(strip=True)
            if _CROSS_SELL_TEXT_RE.search(text):
                # Return the parent section/div
                parent = heading.parent
                if parent and isinstance(parent, Tag):
                    return parent

    # Priority 3: Any element with cross-sell text in a heading-like context
    for el in soup.find_all(["section", "div"]):
        if not isinstance(el, Tag):
            continue
        # Only check direct text children or headings, not deeply nested text
        for child in el.children:
            if isinstance(child, Tag) and child.name in ("h2", "h3", "h4", "h5", "p", "span"):
                if _CROSS_SELL_TEXT_RE.search(child.get_text(strip=True)):
                    return el

    return None


# ---------------------------------------------------------------------------
# Product count within cross-sell section
# ---------------------------------------------------------------------------


def _count_recommended_products(section: Tag) -> int:
    """Count product cards/items within the cross-sell container.

    Looks for product links, product card elements, or images that
    represent individual recommended products.
    """
    count = 0
    seen_hrefs: set[str] = set()

    # Strategy 1: Product card elements with known class patterns
    # Use word-boundary matching to avoid container classes like "rebuy-product-grid"
    _CARD_KEYWORDS = [
        "product-card", "product-item", "grid-item",
        "recommendation-item", "fbt-item", "bundle-item",
        "cross-sell-item", "rebuy-product-block",
        "rebuy-product-info",
    ]
    product_cards = section.find_all(class_=lambda c: c and any(
        any(cls.lower() == kw or cls.lower().startswith(kw + "-")
            or cls.lower().endswith("-" + kw)
            for kw in _CARD_KEYWORDS)
        for cls in (c if isinstance(c, list) else [c])
    ))
    if product_cards:
        return min(len(product_cards), 20)

    # Strategy 2: Links to /products/ pages
    for a in section.find_all("a", href=True):
        href = (a.get("href") or "").lower()
        if "/products/" in href and href not in seen_hrefs:
            seen_hrefs.add(href)
            count += 1

    if count > 0:
        return min(count, 20)

    # Strategy 3: Product images (with product-related attributes)
    product_imgs = section.find_all("img", src=lambda s: s and (
        "products/" in s.lower() or "cdn.shopify" in s.lower()
    ))
    if product_imgs:
        return min(len(product_imgs), 20)

    # Strategy 4: List items that likely represent products
    list_items = section.find_all("li")
    if list_items and len(list_items) <= 12:
        # Only count if items contain links or images (not text-only lists)
        product_lis = [
            li for li in list_items
            if li.find("a") or li.find("img")
        ]
        if product_lis:
            return min(len(product_lis), 20)

    return count


# ---------------------------------------------------------------------------
# Bundle feature detection
# ---------------------------------------------------------------------------


def _detect_checkbox_selection(section: Tag) -> bool:
    """Detect FBT-style checkboxes for selecting bundle items."""
    # Checkbox inputs within the cross-sell section
    checkboxes = section.find_all("input", attrs={"type": "checkbox"})
    if len(checkboxes) >= 2:
        return True
    # Custom checkbox elements (CSS-styled)
    if section.find(class_=lambda c: c and any(
        "checkbox" in cls.lower()
        for cls in (c if isinstance(c, list) else [c])
    )):
        return True
    return False


def _detect_add_all_to_cart(section: Tag) -> bool:
    """Detect 'Add all to cart' or 'Add bundle' CTA button."""
    # Check button text
    for btn in section.find_all(["button", "a", "input"]):
        text = btn.get_text(strip=True)
        if _ADD_ALL_RE.search(text):
            return True
        # Check value attribute for input buttons
        val = btn.get("value", "")
        if isinstance(val, str) and _ADD_ALL_RE.search(val):
            return True

    return False


def _detect_bundle_pricing(section: Tag) -> bool:
    """Detect combined/total pricing element for bundles."""
    text = section.get_text()
    if _BUNDLE_PRICE_RE.search(text):
        return True

    # Check for multiple price elements grouped together
    price_elements = section.find_all(class_=lambda c: c and any(
        "price" in cls.lower()
        for cls in (c if isinstance(c, list) else [c])
    ))
    if len(price_elements) >= 2:
        return True

    return False


def _detect_discount_on_bundle(section: Tag) -> bool:
    """Detect strikethrough/compare price + discounted bundle price."""
    # Check for strikethrough styling (via class or <s>/<del> tags)
    if section.find(["s", "del"]):
        return True

    # Check for compare-at / strikethrough price classes
    if section.find(class_=lambda c: c and any(
        _STRIKETHROUGH_CLASSES.search(cls)
        for cls in (c if isinstance(c, list) else [c])
    )):
        return True

    # Check inline style line-through
    if section.find(style=lambda s: s and "line-through" in s):
        return True

    return False


# ---------------------------------------------------------------------------
# Cross-sell near Add to Cart proximity
# ---------------------------------------------------------------------------

_ATC_SELECTORS = [
    lambda s: s.find("button", attrs={"type": "submit", "name": "add"}),
    lambda s: s.find(class_="product-form__submit"),
    lambda s: s.find("button", attrs={"data-add-to-cart": True}),
    lambda s: s.find(id="AddToCart"),
    lambda s: s.find(class_="btn-add-to-cart"),
]

_CROSS_SELL_INDICATORS = re.compile(
    r"cross.?sell|upsell|frequentl|recommend|fbt|bundle|"
    r"also.?like|bought.?together|related.?product",
    re.IGNORECASE,
)


def _detect_near_buy_button(
    soup: BeautifulSoup, has_section: bool,
) -> bool:
    """Check if cross-sell elements exist within 4 parent levels of ATC."""
    if not has_section:
        return False

    atc_button = None
    for selector_fn in _ATC_SELECTORS:
        atc_button = selector_fn(soup)
        if atc_button:
            break
    if not atc_button:
        return False

    # Walk up to 4 parent levels and check descendants for cross-sell
    current = atc_button
    for _ in range(4):
        parent = current.parent
        if parent is None:
            break
        for descendant in parent.descendants:
            if not isinstance(descendant, Tag):
                continue
            # Check CSS classes for cross-sell indicators
            classes = descendant.get("class") or []
            class_str = " ".join(classes).lower() if classes else ""
            if _CROSS_SELL_INDICATORS.search(class_str):
                return True
            # Check data attributes
            for attr_name in descendant.attrs:
                if isinstance(attr_name, str) and "rebuy" in attr_name.lower():
                    return True
            # Check heading text
            if descendant.name in ("h2", "h3", "h4", "h5"):
                text = descendant.get_text(strip=True)
                if _CROSS_SELL_TEXT_RE.search(text):
                    return True
        current = parent

    return False


# ---------------------------------------------------------------------------
# Widget type classification
# ---------------------------------------------------------------------------


def _classify_widget_type(signals: CrossSellSignals) -> str | None:
    """Classify the cross-sell widget type based on detected features."""
    if not signals.has_cross_sell_section:
        return None

    # FBT bundle: has checkboxes and/or add-all-to-cart with bundle pricing
    if (signals.has_checkbox_selection or signals.has_add_all_to_cart) and (
        signals.has_bundle_pricing or signals.has_discount_on_bundle
    ):
        return "fbt_bundle"

    # Bundle discount: has visible discount/strikethrough on bundle
    if signals.has_discount_on_bundle:
        return "bundle_discount"

    # Default: simple recommendation
    return "simple_recommendation"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_cross_sell(html: str) -> CrossSellSignals:
    """Detect cross-sell & upsell signals from rendered product page HTML.

    Scans for cross-sell app widgets (Rebuy, FBT, Selleasy, ReConvert,
    Zipify, Bold), Shopify native recommendations, bundle pricing,
    checkbox selection, add-all CTAs, and bundle discounts using
    BeautifulSoup DOM inspection and compiled regex patterns.
    """
    signals = CrossSellSignals()

    if not html:
        return signals

    soup = BeautifulSoup(html, "html.parser")

    # --- App detection ---
    signals.cross_sell_app = _detect_cross_sell_app(soup)

    # --- Section detection ---
    section = _detect_cross_sell_section(soup)
    signals.has_cross_sell_section = section is not None

    # If app detected but no section found, still mark section as present
    if signals.cross_sell_app and not signals.has_cross_sell_section:
        signals.has_cross_sell_section = True

    # --- Features within the cross-sell section ---
    if section is not None:
        signals.product_count = _count_recommended_products(section)
        signals.has_checkbox_selection = _detect_checkbox_selection(section)
        signals.has_add_all_to_cart = _detect_add_all_to_cart(section)
        signals.has_bundle_pricing = _detect_bundle_pricing(section)
        signals.has_discount_on_bundle = _detect_discount_on_bundle(section)

    # --- Optimal count (3-4 items) ---
    signals.recommendation_count_optimal = signals.product_count in (3, 4)

    # --- Widget type classification (depends on other signals) ---
    signals.widget_type = _classify_widget_type(signals)

    # --- ATC proximity ---
    signals.near_buy_button = _detect_near_buy_button(
        soup, signals.has_cross_sell_section,
    )

    logger.info(
        "Cross-sell detected: app=%s section=%s type=%s count=%d "
        "bundle_pricing=%s checkbox=%s add_all=%s discount=%s "
        "near_atc=%s optimal=%s",
        signals.cross_sell_app,
        signals.has_cross_sell_section,
        signals.widget_type,
        signals.product_count,
        signals.has_bundle_pricing,
        signals.has_checkbox_selection,
        signals.has_add_all_to_cart,
        signals.has_discount_on_bundle,
        signals.near_buy_button,
        signals.recommendation_count_optimal,
    )

    return signals

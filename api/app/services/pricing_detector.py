"""Pricing psychology signal detector for Shopify product pages.

Detects compare-at/anchoring (strikethrough pricing), charm pricing (.99/.95
endings), urgency and scarcity messaging (countdown timers, stock levels), and
BNPL installment messaging (Klarna, Afterpay, Shop Pay Installments).

Detection follows the same BeautifulSoup DOM inspection approach used by
:pymod:`checkout_detector` and :pymod:`social_proof_detector`.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signals dataclass
# ---------------------------------------------------------------------------


@dataclass
class PricingSignals:
    """Pricing psychology signals extracted from a product page.

    12 fields total:
      • 2 compare-at / anchoring flags
      • 3 charm pricing fields (1 float + 2 bools)
      • 3 urgency / scarcity flags
      • 4 BNPL installment flags
    """

    # --- Compare-at / anchoring (2) -----------------------------------
    has_compare_at_price: bool = False
    """``price--on-sale`` class on any price container, OR ``compare_at_price``
    key found in a Shopify JSON data blob or inline script."""

    has_strikethrough_price: bool = False
    """``.price-item--regular`` element present (Dawn theme strikethrough
    pattern), OR any element with ``text-decoration: line-through`` in its
    inline style attribute."""

    # --- Charm pricing (3) -------------------------------------------
    price_value: Optional[float] = None
    """Extracted numeric price (currency symbols stripped).  ``None`` when
    no recognisable price element is found."""

    has_charm_pricing: bool = False
    """Price ends in ``.99`` or ``.95`` (e.g. $49.99, $199.95)."""

    is_round_price: bool = False
    """Price is a whole-dollar amount (e.g. $50.00 or $50)."""

    # --- Urgency / scarcity (3) --------------------------------------
    has_countdown_timer: bool = False
    """``countdown-timer`` custom element, ``data-countdown`` attribute, or
    JS countdown pattern detected in inline ``<script>`` tags."""

    has_scarcity_messaging: bool = False
    """Scarcity text detected: "only N left", "N in stock", "low stock", or
    "selling fast"."""

    has_fake_timer_risk: bool = False
    """Countdown timer detected but no verifiable ``data-end-time`` anchor
    and no numeric stock-level scarcity text — timer may be fake (Princeton
    2023: ~40% of e-commerce countdown timers are artificial)."""

    # --- BNPL installment messaging (4) -----------------------------
    has_klarna_placement: bool = False
    """``<klarna-placement>`` element present anywhere on the page."""

    has_afterpay_badge: bool = False
    """Afterpay badge, ``<square-placement>``, afterpay script, or afterpay
    text present near the price area."""

    has_shop_pay_installments: bool = False
    """``<shop-pay-installment-details>`` element or "shop pay installments"
    text detected."""

    has_bnpl_near_price: bool = False
    """Any BNPL installment messaging (Klarna, Afterpay, or Shop Pay
    Installments) present on the page."""


# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

_CURRENCY_RE = re.compile(r"[$€£¥₹₩฿₫₪₺₴₦]|USD|EUR|GBP|CAD|AUD")
_PRICE_NUM_RE = re.compile(r"\d{1,6}(?:,\d{3})*(?:\.\d{1,2})?")
_ONLY_N_LEFT_RE = re.compile(r"only\s+\d+\s+(?:left|remaining)", re.IGNORECASE)
_N_IN_STOCK_RE = re.compile(r"\d+\s+(?:in\s+stock|left)\b", re.IGNORECASE)
_LOW_STOCK_RE = re.compile(r"\blow\s*stock\b", re.IGNORECASE)
_SELLING_FAST_RE = re.compile(r"\bselling\s+fast\b", re.IGNORECASE)
_JS_COUNTDOWN_RE = re.compile(
    r"count\s*[–\-]?\s*down|countdown|timeLeft|timer.*second|setInterval.*\d+",
    re.IGNORECASE,
)

# DOM attributes/classes tried in order for price extraction
_PRICE_ATTRS = [
    {"class": "price-item--sale"},
    {"class": "price__current"},
    {"class": "product__price"},
    {"data-product-price": True},
]


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------


def _detect_compare_at_price(soup: BeautifulSoup) -> bool:
    """Detect compare-at / sale-price anchoring signals."""
    # Dawn theme: .price--on-sale on the price container
    if soup.find(class_="price--on-sale"):
        return True
    # Shopify product JSON blob or inline script with compare_at_price key
    for script in soup.find_all("script"):
        text = script.string or ""
        if "compare_at_price" in text:
            return True
    return False


def _detect_strikethrough_price(soup: BeautifulSoup) -> bool:
    """Detect strikethrough / line-through price elements."""
    # Dawn theme: .price-item--regular is the original price shown struck-through
    if soup.find(class_="price-item--regular"):
        return True
    # Inline style: text-decoration: line-through
    for el in soup.find_all(style=True):
        style = el.get("style", "")
        if "line-through" in style.lower():
            return True
    return False


def _extract_price_value(soup: BeautifulSoup) -> Optional[float]:
    """Extract the main numeric sale price from the page.

    Tries DOM price elements first, then falls back to JSON-LD Product schema.
    Returns ``None`` when no price can be parsed.
    """
    # 1. Try known DOM selectors
    for attrs in _PRICE_ATTRS:
        el = soup.find(attrs=attrs)
        if el:
            raw = _CURRENCY_RE.sub("", el.get_text(separator=" ")).strip()
            m = _PRICE_NUM_RE.search(raw.replace(",", ""))
            if m:
                try:
                    return float(m.group())
                except ValueError:
                    pass

    # 2. Fall back to JSON-LD Product schema
    for script in soup.find_all("script", type="application/ld+json"):
        text = script.string or ""
        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            continue
        # Handle @graph arrays or bare arrays
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("@type") != "Product":
                continue
            offers = item.get("offers", {})
            if isinstance(offers, list) and offers:
                offers = offers[0]
            price = offers.get("price") if isinstance(offers, dict) else None
            if price is not None:
                try:
                    return float(str(price).replace(",", ""))
                except ValueError:
                    pass

    return None


def _detect_countdown_timer(soup: BeautifulSoup) -> tuple[bool, bool]:
    """Detect countdown timer presence and fake-timer risk.

    Returns:
        ``(has_timer, has_fake_risk)`` where ``has_fake_risk`` is True when a
        timer is detected but there is no verifiable ``data-end-time`` anchor.
    """
    has_timer = False
    has_end_time = False

    # Custom element
    if soup.find("countdown-timer"):
        has_timer = True

    # data-countdown / data-end-time attributes
    if soup.find(attrs={"data-countdown": True}):
        has_timer = True
    if soup.find(attrs={"data-end-time": True}):
        has_timer = True
        has_end_time = True

    # CSS class names containing "countdown"
    for el in soup.find_all(class_=True):
        classes = " ".join(el.get("class", []))
        if "countdown" in classes.lower():
            has_timer = True
            break

    # Inline JS: setInterval / countdown variable patterns
    if not has_timer:
        for script in soup.find_all("script"):
            text = script.string or ""
            if _JS_COUNTDOWN_RE.search(text):
                has_timer = True
                break

    fake_risk = has_timer and not has_end_time
    return has_timer, fake_risk


def _detect_scarcity_messaging(soup: BeautifulSoup) -> bool:
    """Detect real-time stock / scarcity text on the page."""
    page_text = soup.get_text(separator=" ")
    return bool(
        _ONLY_N_LEFT_RE.search(page_text)
        or _N_IN_STOCK_RE.search(page_text)
        or _LOW_STOCK_RE.search(page_text)
        or _SELLING_FAST_RE.search(page_text)
    )


def _detect_klarna_placement(soup: BeautifulSoup) -> bool:
    """Detect ``<klarna-placement>`` custom element."""
    return soup.find("klarna-placement") is not None


def _detect_afterpay_badge(soup: BeautifulSoup) -> bool:
    """Detect Afterpay badge / element via multiple signals."""
    # Square placement (Afterpay's Shopify integration)
    if soup.find("square-placement"):
        return True
    # CSS class containing "afterpay"
    if soup.find(class_=lambda c: c and "afterpay" in " ".join(c).lower()):
        return True
    # Script src containing "afterpay"
    for script in soup.find_all("script", src=True):
        if "afterpay" in script["src"].lower():
            return True
    # Text content (badge may be rendered as text/img alt)
    page_text = soup.get_text().lower()
    if "afterpay" in page_text:
        return True
    return False


def _detect_shop_pay_installments(soup: BeautifulSoup) -> bool:
    """Detect Shop Pay Installments element or text."""
    if soup.find("shop-pay-installment-details"):
        return True
    if soup.find(class_=lambda c: c and "shop-pay-installment" in " ".join(c).lower()):
        return True
    page_text = soup.get_text().lower()
    if "shop pay installments" in page_text:
        return True
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_pricing(html: str) -> PricingSignals:
    """Detect pricing psychology signals from rendered product page HTML.

    Scans for compare-at anchoring, charm pricing, urgency/scarcity messaging,
    and BNPL installment widgets using BeautifulSoup DOM inspection.
    """
    signals = PricingSignals()

    if not html:
        return signals

    soup = BeautifulSoup(html, "html.parser")

    # --- Compare-at / anchoring ---
    signals.has_compare_at_price = _detect_compare_at_price(soup)
    signals.has_strikethrough_price = _detect_strikethrough_price(soup)

    # --- Charm pricing ---
    signals.price_value = _extract_price_value(soup)
    if signals.price_value is not None:
        frac = round(signals.price_value % 1, 2)
        signals.has_charm_pricing = frac in (0.99, 0.95)
        signals.is_round_price = frac == 0.0

    # --- Urgency / scarcity ---
    has_timer, has_fake_timer_raw = _detect_countdown_timer(soup)
    signals.has_countdown_timer = has_timer
    signals.has_scarcity_messaging = _detect_scarcity_messaging(soup)
    # Fake risk: timer present but no verifiable end-time anchor
    # AND no numeric stock scarcity text (which would confirm real inventory)
    signals.has_fake_timer_risk = has_fake_timer_raw and not signals.has_scarcity_messaging

    # --- BNPL installment messaging ---
    signals.has_klarna_placement = _detect_klarna_placement(soup)
    signals.has_afterpay_badge = _detect_afterpay_badge(soup)
    signals.has_shop_pay_installments = _detect_shop_pay_installments(soup)
    signals.has_bnpl_near_price = any([
        signals.has_klarna_placement,
        signals.has_afterpay_badge,
        signals.has_shop_pay_installments,
    ])

    logger.info(
        "Pricing detected: compare_at=%s strikethrough=%s "
        "price=%s charm=%s round=%s "
        "countdown=%s scarcity=%s fake_timer=%s "
        "klarna=%s afterpay=%s shop_pay=%s bnpl=%s",
        signals.has_compare_at_price,
        signals.has_strikethrough_price,
        signals.price_value,
        signals.has_charm_pricing,
        signals.is_round_price,
        signals.has_countdown_timer,
        signals.has_scarcity_messaging,
        signals.has_fake_timer_risk,
        signals.has_klarna_placement,
        signals.has_afterpay_badge,
        signals.has_shop_pay_installments,
        signals.has_bnpl_near_price,
    )

    return signals

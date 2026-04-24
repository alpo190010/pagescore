"""Checkout experience signal detector for Shopify product pages and checkout flow.

Detects express checkout options (Shop Pay, dynamic checkout buttons),
buy-now-pay-later providers (Klarna, Afterpay, Affirm, Sezzle), PayPal
presence, payment method diversity, and cart UX signals (drawer cart,
AJAX cart, sticky checkout).

Detection is presence-only for ``<shopify-accelerated-checkout>`` (closed
shadow DOM — D049).  All other signals use standard BeautifulSoup DOM
inspection consistent with :pymod:`social_proof_detector` and
:pymod:`structured_data_detector`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signals dataclass
# ---------------------------------------------------------------------------


@dataclass
class CheckoutSignals:
    """Checkout experience signals extracted from a product page.

    11 fields total:
      • 3 express checkout flags
      • 4 BNPL provider flags
      • 1 payment diversity counter
      • 3 cart experience flags
    """

    # --- Express checkout (3) ----------------------------------------
    has_accelerated_checkout: bool = False
    """``<shopify-accelerated-checkout>`` element detected (presence-only,
    closed shadow DOM)."""

    has_dynamic_checkout_button: bool = False
    """``.shopify-payment-button`` class or ``[data-shopify="payment-button"]``
    attribute detected."""

    has_paypal: bool = False
    """PayPal button container or ``paypal.com/sdk`` script detected."""

    # --- BNPL providers (4) ------------------------------------------
    has_klarna: bool = False
    """``<klarna-placement>`` element or ``klarnaservices.com`` script detected."""

    has_afterpay: bool = False
    """``<square-placement>`` element, ``afterpay`` in script URLs/classes,
    or ``afterpay_product`` in inline scripts."""

    has_affirm: bool = False
    """``.affirm-as-low-as`` class or ``affirm.js`` / ``affirm.com`` in
    script src."""

    has_sezzle: bool = False
    """``.sezzle-widget`` / ``[data-sezzle]`` elements or ``sezzle.com``
    in script src."""

    # --- Payment diversity (1) ---------------------------------------
    payment_method_count: int = 1
    """Estimated number of distinct payment methods available.

    Baseline of 1 (credit card, always assumed).  Incremented for:
    Shop Pay (+1 if accelerated checkout), PayPal (+1), Apple/Google Pay
    (+1 if accelerated checkout), and any BNPL provider (+1).
    Maximum 5.
    """

    # --- Cart experience (3) -----------------------------------------
    has_drawer_cart: bool = False
    """Drawer / slide-out cart element detected (e.g. ``.cart-drawer``,
    ``[data-cart-drawer]``, ``cart-drawer`` custom element)."""

    has_ajax_cart: bool = False
    """AJAX cart integration detected (``/cart/add.js`` reference or
    ``cart.js`` script)."""

    has_sticky_checkout: bool = False
    """Sticky / fixed add-to-cart or checkout button detected."""


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------


def _detect_accelerated_checkout(soup: BeautifulSoup) -> bool:
    """Detect ``<shopify-accelerated-checkout>`` custom element.

    Presence-only — the element uses a closed shadow DOM so we cannot
    inspect its children (D049).
    """
    return soup.find("shopify-accelerated-checkout") is not None


def _detect_dynamic_checkout_button(soup: BeautifulSoup) -> bool:
    """Detect Shopify dynamic checkout button."""
    if soup.find(class_="shopify-payment-button"):
        return True
    if soup.find(attrs={"data-shopify": "payment-button"}):
        return True
    return False


def _detect_paypal(soup: BeautifulSoup) -> bool:
    """Detect PayPal button container or SDK script."""
    if soup.find(class_="paypal-button-container"):
        return True
    for script in soup.find_all("script", src=True):
        if "paypal.com/sdk" in script["src"]:
            return True
    return False


def _detect_klarna(soup: BeautifulSoup) -> bool:
    """Detect Klarna placement element or services script."""
    if soup.find("klarna-placement"):
        return True
    for script in soup.find_all("script", src=True):
        if "klarnaservices.com" in script["src"]:
            return True
    return False


def _detect_afterpay(soup: BeautifulSoup) -> bool:
    """Detect Afterpay via Square placement, script URLs, or inline scripts."""
    if soup.find("square-placement"):
        return True
    for script in soup.find_all("script", src=True):
        if "afterpay" in script["src"].lower():
            return True
    # Check for afterpay CSS classes
    if soup.find(class_=lambda c: c and "afterpay" in c.lower()):
        return True
    # Check inline scripts for afterpay_product references
    for script in soup.find_all("script"):
        text = script.string or ""
        if "afterpay_product" in text:
            return True
    return False


def _detect_affirm(soup: BeautifulSoup) -> bool:
    """Detect Affirm widget class or script."""
    if soup.find(class_="affirm-as-low-as"):
        return True
    for script in soup.find_all("script", src=True):
        src = script["src"].lower()
        if "affirm.js" in src or "affirm.com" in src:
            return True
    return False


def _detect_sezzle(soup: BeautifulSoup) -> bool:
    """Detect Sezzle widget element or script."""
    if soup.find(class_="sezzle-widget"):
        return True
    if soup.find(attrs={"data-sezzle": True}):
        return True
    for script in soup.find_all("script", src=True):
        if "sezzle.com" in script["src"]:
            return True
    return False


def _detect_drawer_cart(soup: BeautifulSoup) -> bool:
    """Detect drawer / slide-out cart elements."""
    if soup.find(class_="cart-drawer"):
        return True
    if soup.find(attrs={"data-cart-drawer": True}):
        return True
    if soup.find(attrs={"data-drawer": "cart"}):
        return True
    if soup.find(class_="drawer--cart"):
        return True
    if soup.find("cart-drawer"):
        return True
    if soup.find(id="CartDrawer"):
        return True
    return False


def _detect_ajax_cart(soup: BeautifulSoup) -> bool:
    """Detect AJAX cart integration via ``/cart/add.js`` or ``cart.js`` script."""
    # Check full HTML text for /cart/add.js reference
    html_text = soup.get_text() if soup else ""
    # Also check raw HTML string for /cart/add.js in any attribute or script
    page_str = str(soup)
    if "/cart/add.js" in page_str:
        return True
    for script in soup.find_all("script", src=True):
        if "cart.js" in script["src"]:
            return True
    return False


def _detect_sticky_checkout(soup: BeautifulSoup) -> bool:
    """Detect sticky / fixed checkout or add-to-cart buttons."""
    if soup.find(class_="sticky-checkout"):
        return True
    if soup.find(attrs={"data-sticky-checkout": True}):
        return True
    if soup.find(class_="fixed-add-to-cart"):
        return True
    return False


def _compute_payment_method_count(
    *,
    has_accelerated_checkout: bool,
    has_paypal: bool,
    has_any_bnpl: bool,
) -> int:
    """Compute estimated payment method count.

    Baseline of 1 (credit card always assumed).  Accelerated checkout
    adds Shop Pay (+1) and Apple/Google Pay (+1).  PayPal and any BNPL
    provider each add +1.  Maximum is 5.
    """
    count = 1  # credit card
    if has_accelerated_checkout:
        count += 2  # Shop Pay + Apple/Google Pay
    if has_paypal:
        count += 1
    if has_any_bnpl:
        count += 1
    return count


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_checkout(html: str) -> CheckoutSignals:
    """Detect checkout experience signals from rendered product page HTML.

    Scans for express checkout options, BNPL providers, payment method
    diversity, and cart UX signals using BeautifulSoup DOM inspection.
    """
    signals = CheckoutSignals()

    if not html:
        return signals

    soup = BeautifulSoup(html, "html.parser")

    # --- Express checkout ---
    signals.has_accelerated_checkout = _detect_accelerated_checkout(soup)
    signals.has_dynamic_checkout_button = _detect_dynamic_checkout_button(soup)
    signals.has_paypal = _detect_paypal(soup)

    # --- BNPL providers ---
    signals.has_klarna = _detect_klarna(soup)
    signals.has_afterpay = _detect_afterpay(soup)
    signals.has_affirm = _detect_affirm(soup)
    signals.has_sezzle = _detect_sezzle(soup)

    # --- Cart experience ---
    signals.has_drawer_cart = _detect_drawer_cart(soup)
    signals.has_ajax_cart = _detect_ajax_cart(soup)
    signals.has_sticky_checkout = _detect_sticky_checkout(soup)

    # --- Payment diversity ---
    has_any_bnpl = any([
        signals.has_klarna,
        signals.has_afterpay,
        signals.has_affirm,
        signals.has_sezzle,
    ])
    signals.payment_method_count = _compute_payment_method_count(
        has_accelerated_checkout=signals.has_accelerated_checkout,
        has_paypal=signals.has_paypal,
        has_any_bnpl=has_any_bnpl,
    )

    logger.info(
        "Checkout detected: accelerated=%s dynamic=%s paypal=%s "
        "klarna=%s afterpay=%s affirm=%s sezzle=%s "
        "methods=%d drawer=%s ajax=%s sticky=%s",
        signals.has_accelerated_checkout,
        signals.has_dynamic_checkout_button,
        signals.has_paypal,
        signals.has_klarna,
        signals.has_afterpay,
        signals.has_affirm,
        signals.has_sezzle,
        signals.payment_method_count,
        signals.has_drawer_cart,
        signals.has_ajax_cart,
        signals.has_sticky_checkout,
    )

    return signals


# ---------------------------------------------------------------------------
# Merged signals — PDP-derived + rendered checkout page
# ---------------------------------------------------------------------------
#
# The PDP signals (above) tell us what payment-related markup was shipped
# in the product page HTML. The rendered checkout-page signals (from
# :mod:`checkout_page_parser`) tell us the ground truth about wallets,
# BNPL, cards, and guest-checkout on the actual form a buyer fills out.
#
# ``combine_signals`` glues them together so the rubric can score
# whichever data is most authoritative per check. When the flow couldn't
# reach checkout (``reached_checkout=False``), the PDP data is all we
# have and the rubric is capped to avoid claiming a high score for
# something we never verified.

from app.services.checkout_page_parser import (  # noqa: E402 — avoid cycle
    CheckoutPageSignals,
    unreached,
)


@dataclass(frozen=True)
class MergedCheckoutSignals:
    """Ground-truth-preferred view of a store's checkout experience.

    Combines the PDP-derived ``CheckoutSignals`` (what's in the product
    page HTML) with ``CheckoutPageSignals`` (what's in the rendered
    checkout). The rubric keys off ``checkout_page.reached_checkout`` to
    decide whether to trust the checkout-page data or fall back to PDP
    inference.
    """

    pdp: CheckoutSignals
    checkout_page: CheckoutPageSignals

    @property
    def reached_checkout(self) -> bool:
        return self.checkout_page.reached_checkout

    @property
    def failure_reason(self) -> str | None:
        return self.checkout_page.failure_reason


def combine_signals(
    pdp: CheckoutSignals,
    checkout_page: CheckoutPageSignals | None = None,
) -> MergedCheckoutSignals:
    """Combine PDP and checkout-page signals into a merged view.

    If ``checkout_page`` is None (the simulator was not run, e.g. during
    unit tests for discover_products), a synthetic ``unreached("not_run")``
    stand-in is used so downstream code doesn't need null checks.
    """
    if checkout_page is None:
        checkout_page = unreached("not_run")
    return MergedCheckoutSignals(pdp=pdp, checkout_page=checkout_page)

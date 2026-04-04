"""Trust & guarantee signal detector for Shopify product pages.

Detects trust badges (Hextom, Avada, Trust Badges Bear), money-back
guarantees, return policy visibility, security indicators (Norton,
McAfee, SSL), live chat widgets (Tidio, Gorgias, Zendesk, Intercom,
tawk.to, Crisp, Drift, Shopify Inbox), contact info, and trust
element proximity to the Add to Cart button.

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
class TrustSignals:
    """Trust & guarantee signals extracted from a product page.

    14 fields total:
      - 3 trust badge / app detection fields
      - 3 guarantee & return policy fields
      - 3 security indicator fields
      - 3 contact & live chat fields
      - 2 aggregate / proximity fields
    """

    # --- Trust badge app detection (3) ---
    trust_badge_app: str | None = None
    """Detected trust badge app name, e.g. "hextom", "avada",
    "trust-badges-bear", or None."""

    trust_badge_count: int = 0
    """Number of distinct trust/security badge images or elements
    found on page (capped at 5)."""

    has_payment_icons: bool = False
    """Payment method trust icons visible (Visa, Mastercard, Amex
    logos, etc.)."""

    # --- Guarantees & return policy (3) ---
    has_money_back_guarantee: bool = False
    """Text or image referencing "money-back guarantee" or
    "satisfaction guarantee"."""

    has_return_policy: bool = False
    """Return/refund policy text visible on page (e.g. "free returns",
    "30-day returns", "easy returns")."""

    has_free_shipping_badge: bool = False
    """Free shipping trust messaging visible (e.g. "free shipping",
    "free delivery")."""

    # --- Security indicators (3) ---
    has_secure_checkout_text: bool = False
    """Text like "secure checkout", "encrypted", "SSL", "256-bit"
    visible on page."""

    has_security_badge: bool = False
    """Known security badge detected: Norton, McAfee, Trustwave,
    Comodo, DigiCert images/elements."""

    has_safe_checkout_badge: bool = False
    """"Guaranteed Safe Checkout" badge with payment icons — very
    common Shopify pattern."""

    # --- Contact & live chat (3) ---
    has_live_chat: bool = False
    """Live chat widget detected (Tidio, Gorgias, Zendesk, Intercom,
    LiveChat, tawk.to, Shopify Inbox, Crisp, Drift)."""

    has_phone_number: bool = False
    """Phone number visible on page (tel: link or regex-matched
    telephone pattern)."""

    has_contact_email: bool = False
    """Contact email address visible on page (mailto: link)."""

    # --- Aggregate / proximity (2) ---
    has_trust_near_atc: bool = False
    """Any trust element (badge, guarantee, return policy) detected
    within proximity of Add to Cart button."""

    trust_element_count: int = 0
    """Total count of distinct trust signals found (sum of boolean
    fields that are True)."""


# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

_MONEY_BACK_RE = re.compile(
    r"money[\s-]*back\s*guarantee|satisfaction\s*guarante|"
    r"100%\s*guarante|full\s*refund\s*guarante|"
    r"no[\s-]*risk\s*guarante|risk[\s-]*free\s*guarante",
    re.IGNORECASE,
)

_RETURN_POLICY_RE = re.compile(
    r"free\s*returns?|easy\s*returns?|\d+[\s-]*day\s*returns?|"
    r"return\s*policy|hassle[\s-]*free\s*returns?|"
    r"no[\s-]*questions?\s*asked\s*returns?|"
    r"refund\s*policy|exchange\s*policy",
    re.IGNORECASE,
)

_FREE_SHIPPING_RE = re.compile(
    r"free\s*shipping|free\s*delivery|complimentary\s*shipping|"
    r"ships?\s*free|no\s*shipping\s*(?:cost|fee|charge)",
    re.IGNORECASE,
)

_SECURE_CHECKOUT_RE = re.compile(
    r"secure\s*checkout|encrypted\s*checkout|ssl\s*secured?|256[\s-]*bit|"
    r"securely\s*processed|secure\s*payment|"
    r"your\s*(?:data|info|information)\s*is\s*(?:safe|secure|protected)",
    re.IGNORECASE,
)

_SAFE_CHECKOUT_RE = re.compile(
    r"guaranteed?\s*safe\s*(?:(?:&amp;|and|&)\s*)?(?:secure?\s*)?checkout|"
    r"safe\s*(?:(?:&amp;|and|&)\s*)?(?:secure?\s*)?checkout",
    re.IGNORECASE,
)

_SECURITY_BADGE_KEYWORDS = [
    "norton", "mcafee", "trustwave", "comodo", "geotrust",
    "digicert", "lets-encrypt", "ssl-certificate", "secure-seal",
]

_BADGE_IMG_KEYWORDS = [
    "trust", "badge", "secure", "guarantee", "norton", "mcafee",
    "ssl", "verified", "safe-checkout",
]

_PAYMENT_BRANDS = [
    "visa", "mastercard", "amex", "american-express",
    "discover", "maestro", "diners",
]

_PHONE_RE = re.compile(
    r"\+?1?[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b|"
    r"\+\d{1,3}[\s.-]?\d{2,4}[\s.-]?\d{3,4}[\s.-]?\d{3,4}",
)


# ---------------------------------------------------------------------------
# Trust badge app detection
# ---------------------------------------------------------------------------

# (app_name, css_class_prefixes, script_url_patterns)
_TRUST_BADGE_APPS: list[tuple[str, list[str], list[str]]] = [
    ("hextom", ["usb-", "hextom-"], ["hextom.com"]),
    ("avada", ["avada-trust", "avada-"], ["aov.ai"]),
    ("trust-badges-bear", ["tbb-", "trust-badges-bear"], ["trustbadgesbear"]),
    ("ryviu", ["ryviu-trust"], ["ryviu.com"]),
    ("judge-me", ["jdgm-trust"], ["judge.me"]),
]


def _detect_trust_badge_app(soup: BeautifulSoup) -> str | None:
    """Detect known trust badge app by CSS class prefixes or script URLs."""
    page_str = str(soup).lower()
    for app_name, class_prefixes, script_patterns in _TRUST_BADGE_APPS:
        # Check CSS classes
        for prefix in class_prefixes:
            if soup.find(class_=lambda c: c and any(
                cls.startswith(prefix) for cls in (c if isinstance(c, list) else [c])
            )):
                return app_name
        # Check script URLs
        for pattern in script_patterns:
            if pattern in page_str:
                return app_name
    return None


def _count_trust_badges(soup: BeautifulSoup) -> int:
    """Count distinct trust/security badge images and elements (cap 5)."""
    count = 0
    seen_srcs: set[str] = set()
    for img in soup.find_all("img"):
        src = (img.get("src") or "").lower()
        alt = (img.get("alt") or "").lower()
        if any(kw in src or kw in alt for kw in _BADGE_IMG_KEYWORDS):
            if src not in seen_srcs:
                seen_srcs.add(src)
                count += 1
    # Check elements with trust-badge class patterns
    for el in soup.find_all(class_=lambda c: c and any(
        "trust-badge" in cls or "security-badge" in cls or "guarantee-badge" in cls
        for cls in (c if isinstance(c, list) else [c])
    )):
        count += 1
    return min(count, 5)


# ---------------------------------------------------------------------------
# Payment icons detection
# ---------------------------------------------------------------------------


def _detect_payment_icons(soup: BeautifulSoup) -> bool:
    """Detect payment brand logos (Visa, MC, Amex) in images or SVGs."""
    for img in soup.find_all("img"):
        src = (img.get("src") or "").lower()
        alt = (img.get("alt") or "").lower()
        if any(brand in src or brand in alt for brand in _PAYMENT_BRANDS):
            return True
    for svg in soup.find_all("svg"):
        title = svg.find("title")
        if title and any(
            brand in title.get_text().lower() for brand in _PAYMENT_BRANDS
        ):
            return True
    return False


# ---------------------------------------------------------------------------
# Guarantee & return policy detection
# ---------------------------------------------------------------------------


def _detect_money_back_guarantee(soup: BeautifulSoup) -> bool:
    """Detect money-back or satisfaction guarantee via text or image alt."""
    page_text = soup.get_text()
    if _MONEY_BACK_RE.search(page_text):
        return True
    for img in soup.find_all("img"):
        alt = (img.get("alt") or "").lower()
        src = (img.get("src") or "").lower()
        if "money-back" in alt or "money-back" in src:
            return True
        if "satisfaction-guarantee" in alt or "satisfaction-guarantee" in src:
            return True
    return False


def _detect_return_policy(soup: BeautifulSoup) -> bool:
    """Detect return/refund policy text on page."""
    return bool(_RETURN_POLICY_RE.search(soup.get_text()))


def _detect_free_shipping_badge(soup: BeautifulSoup) -> bool:
    """Detect free shipping messaging on page."""
    page_text = soup.get_text()
    if _FREE_SHIPPING_RE.search(page_text):
        return True
    for img in soup.find_all("img"):
        alt = (img.get("alt") or "").lower()
        src = (img.get("src") or "").lower()
        if "free-shipping" in alt or "free-shipping" in src:
            return True
    return False


# ---------------------------------------------------------------------------
# Security indicators
# ---------------------------------------------------------------------------


def _detect_secure_checkout_text(soup: BeautifulSoup) -> bool:
    """Detect 'secure checkout' / 'SSL' / 'encrypted' text on page."""
    return bool(_SECURE_CHECKOUT_RE.search(soup.get_text()))


def _detect_security_badge(soup: BeautifulSoup) -> bool:
    """Detect known security badge images or elements (Norton, McAfee, etc.)."""
    for img in soup.find_all("img"):
        src = (img.get("src") or "").lower()
        alt = (img.get("alt") or "").lower()
        if any(kw in src or kw in alt for kw in _SECURITY_BADGE_KEYWORDS):
            return True
    # Check elements with security-related classes
    for el in soup.find_all(class_=lambda c: c and any(
        any(kw in cls.lower() for kw in ["norton", "mcafee", "security-seal"])
        for cls in (c if isinstance(c, list) else [c])
    )):
        return True
    return False


def _detect_safe_checkout_badge(soup: BeautifulSoup) -> bool:
    """Detect 'Guaranteed Safe Checkout' badge pattern."""
    return bool(_SAFE_CHECKOUT_RE.search(soup.get_text()))


# ---------------------------------------------------------------------------
# Contact & live chat
# ---------------------------------------------------------------------------

# (app_name, css_selectors, script_url_patterns)
_CHAT_APPS: list[tuple[str, list[str], list[str]]] = [
    ("tidio", ["#tidio-chat", ".tidio-chat"], ["tidio.co"]),
    ("gorgias", ["#gorgias-chat-container", ".gorgias-chat"], ["gorgias.chat"]),
    ("zendesk", [".zEWidget", "#launcher"], ["zopim.com", "zendesk.com/embeddable"]),
    ("intercom", ["#intercom-container", ".intercom-launcher"], ["intercom.io"]),
    ("livechat", ["#chat-widget-container"], ["livechatinc.com"]),
    ("tawk", [".tawk-widget", "#tawkto"], ["tawk.to"]),
    ("shopify-inbox", ["shopify-chat"], ["shopifychat"]),
    ("crisp", ["#crisp-chatbox", ".crisp-client"], ["crisp.chat"]),
    ("drift", ["#drift-widget", ".drift-frame-controller"], ["drift.com"]),
]


def _detect_live_chat(soup: BeautifulSoup) -> bool:
    """Detect live chat widget from known providers."""
    page_str = str(soup).lower()
    for _name, selectors, script_patterns in _CHAT_APPS:
        for sel in selectors:
            # Handle both ID and class selectors
            if sel.startswith("#"):
                if soup.find(id=sel[1:]):
                    return True
            elif sel.startswith("."):
                if soup.find(class_=sel[1:]):
                    return True
            else:
                # Custom element name
                if soup.find(sel):
                    return True
        for pattern in script_patterns:
            if pattern in page_str:
                return True
    return False


def _detect_phone_number(soup: BeautifulSoup) -> bool:
    """Detect phone number via tel: links or regex pattern."""
    if soup.find("a", href=lambda h: h and h.startswith("tel:")):
        return True
    return bool(_PHONE_RE.search(soup.get_text()))


def _detect_contact_email(soup: BeautifulSoup) -> bool:
    """Detect contact email via mailto: links."""
    return soup.find("a", href=lambda h: h and h.startswith("mailto:")) is not None


# ---------------------------------------------------------------------------
# Trust near Add to Cart proximity
# ---------------------------------------------------------------------------

_ATC_SELECTORS = [
    lambda s: s.find("button", attrs={"type": "submit", "name": "add"}),
    lambda s: s.find(class_="product-form__submit"),
    lambda s: s.find("button", attrs={"data-add-to-cart": True}),
    lambda s: s.find(id="AddToCart"),
    lambda s: s.find(class_="btn-add-to-cart"),
]

_TRUST_TEXT_INDICATORS = re.compile(
    r"guarantee|money[\s-]*back|return\s*policy|free\s*returns?|"
    r"secure\s*checkout|safe\s*checkout|trust",
    re.IGNORECASE,
)


def _detect_trust_near_atc(soup: BeautifulSoup, has_any_trust: bool) -> bool:
    """Check if trust elements exist within 3 parent levels of ATC button."""
    if not has_any_trust:
        return False

    atc_button = None
    for selector_fn in _ATC_SELECTORS:
        atc_button = selector_fn(soup)
        if atc_button:
            break
    if not atc_button:
        return False

    # Walk up to 3 parent levels and check descendants for trust indicators
    current = atc_button
    for _ in range(3):
        parent = current.parent
        if parent is None:
            break
        for descendant in parent.descendants:
            if not isinstance(descendant, Tag):
                continue
            # Check for trust-related CSS classes
            classes = descendant.get("class") or []
            class_str = " ".join(classes).lower() if classes else ""
            if any(kw in class_str for kw in ["trust", "guarantee", "secure"]):
                return True
            # Check for trust badge images
            if descendant.name == "img":
                alt = (descendant.get("alt") or "").lower()
                src = (descendant.get("src") or "").lower()
                if any(kw in alt or kw in src for kw in ["trust", "guarantee", "secure", "badge"]):
                    return True
            # Check text content of small elements (avoid matching huge containers)
            if descendant.name in ("span", "p", "small", "div") and descendant.string:
                text = descendant.string.strip()
                if len(text) < 200 and _TRUST_TEXT_INDICATORS.search(text):
                    return True
        current = parent

    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_trust(html: str) -> TrustSignals:
    """Detect trust & guarantee signals from rendered product page HTML.

    Scans for trust badges, guarantees, return policies, security
    indicators, live chat widgets, and contact information using
    BeautifulSoup DOM inspection and compiled regex patterns.
    """
    signals = TrustSignals()

    if not html:
        return signals

    soup = BeautifulSoup(html, "html.parser")

    # --- Trust badge app & count ---
    signals.trust_badge_app = _detect_trust_badge_app(soup)
    signals.trust_badge_count = _count_trust_badges(soup)
    signals.has_payment_icons = _detect_payment_icons(soup)

    # --- Guarantees & return policy ---
    signals.has_money_back_guarantee = _detect_money_back_guarantee(soup)
    signals.has_return_policy = _detect_return_policy(soup)
    signals.has_free_shipping_badge = _detect_free_shipping_badge(soup)

    # --- Security indicators ---
    signals.has_secure_checkout_text = _detect_secure_checkout_text(soup)
    signals.has_security_badge = _detect_security_badge(soup)
    signals.has_safe_checkout_badge = _detect_safe_checkout_badge(soup)

    # --- Contact & live chat ---
    signals.has_live_chat = _detect_live_chat(soup)
    signals.has_phone_number = _detect_phone_number(soup)
    signals.has_contact_email = _detect_contact_email(soup)

    # --- Aggregate trust element count ---
    signals.trust_element_count = sum([
        signals.has_payment_icons,
        signals.has_money_back_guarantee,
        signals.has_return_policy,
        signals.has_free_shipping_badge,
        signals.has_secure_checkout_text,
        signals.has_security_badge,
        signals.has_safe_checkout_badge,
        signals.has_live_chat,
        signals.has_phone_number,
        signals.has_contact_email,
        signals.trust_badge_count >= 1,
    ])

    # --- Trust near ATC (needs aggregate check first) ---
    signals.has_trust_near_atc = _detect_trust_near_atc(
        soup, signals.trust_element_count > 0
    )

    logger.info(
        "Trust detected: app=%s badges=%d payment_icons=%s "
        "guarantee=%s return=%s shipping=%s "
        "secure_text=%s security_badge=%s safe_checkout=%s "
        "chat=%s phone=%s email=%s near_atc=%s elements=%d",
        signals.trust_badge_app,
        signals.trust_badge_count,
        signals.has_payment_icons,
        signals.has_money_back_guarantee,
        signals.has_return_policy,
        signals.has_free_shipping_badge,
        signals.has_secure_checkout_text,
        signals.has_security_badge,
        signals.has_safe_checkout_badge,
        signals.has_live_chat,
        signals.has_phone_number,
        signals.has_contact_email,
        signals.has_trust_near_atc,
        signals.trust_element_count,
    )

    return signals

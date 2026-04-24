"""Parser for Shopify checkout page HTML.

Runs against the HTML captured from ``/checkouts/c/<token>`` or
``/checkouts/cn/<token>`` after a successful add-to-cart flow. Extracts
ground-truth signals about available wallets, BNPL providers, card
networks, guest checkout, and UX details — the things PDP-only
detection cannot see.

Shopify rolled out the React One-Page Checkout ("onepage" flavor) in
2024 and migrated all stores by end of 2024. The parser targets that
flavor primarily. Classic Liquid checkout detection is kept as a
fallback for the small tail of stores that still render it.

Entry points:
    parse_checkout_page(html, final_url=...) -> CheckoutPageSignals
    unreached(failure_reason) -> CheckoutPageSignals
"""

from __future__ import annotations

import html as html_unescape_mod
import re
from dataclasses import dataclass


# --- Shopify wallet __typename markers -------------------------------
# These come from the GraphQL payload embedded in the React checkout
# HTML. The field ``name`` is an enum string; the ``__typename`` is the
# GraphQL type. Either is usable; ``__typename`` is more stable.
_WALLET_CONFIG_TYPENAMES = {
    "ShopPayWalletConfig": "shop_pay",
    "ApplePayWalletConfig": "apple_pay",
    "GooglePayWalletConfig": "google_pay",
    "PaypalWalletConfig": "paypal",
    "AmazonPayWalletConfig": "amazon_pay",
    "MetaPayWalletConfig": "meta_pay",
    "StripeLinkWalletConfig": "stripe_link",
    # Shopify Installments is technically a wallet config; we surface it
    # as a BNPL signal below as well.
    "ShopifyInstallmentsWalletConfig": "shop_pay_installments",
}

# Visible payment-method radio options on the first step. Keys are
# normalized aria-labels.
_PAYMENT_OPTION_LABELS = {
    "shop pay": "shop_pay",
    "apple pay": "apple_pay",
    "google pay": "google_pay",
    "paypal": "paypal",
    "amazon pay": "amazon_pay",
    "meta pay": "meta_pay",
    "klarna": "klarna",
    "afterpay": "afterpay",
    "clearpay": "clearpay",
    "affirm": "affirm",
    "sezzle": "sezzle",
    "zip": "zip",
    "cash app pay": "cashapppay",
}

# Fallback string-match patterns for classic checkouts and loose HTML.
_CLASSIC_PAYMENT_PATTERNS = {
    "klarna": (r"klarna", r"klarnaservices"),
    "afterpay": (r"afterpay", ),
    "clearpay": (r"clearpay", ),
    "affirm": (r"affirm\.js", r"\"affirm\"", r"affirm\.com"),
    "sezzle": (r"sezzle", ),
    "zip": (r"quadpay", r"zip\.co"),
    "shop_pay_installments": (r"shop[- _]?pay[- _]?installments", r"ShopifyInstallments"),
}

# Fields we expect to see on the first step of a real Shopify checkout.
# Used for guest-checkout detection, form-field count, and discount-code
# detection.
_EMAIL_FIELD_NAMES = {"email", "checkout[email]"}
_DISCOUNT_FIELD_NAMES = {"reductions", "checkout[reduction_code]", "discount"}
_GIFT_CARD_HINTS = ("gift_card", "gift-card", "giftcard")
_PASSWORD_FIELD_NAMES = {"customer[password]", "password"}

# Trust-signal keywords in alt/text near checkout badges.
_TRUST_KEYWORDS = (
    "secure", "ssl", "verified", "guarantee", "money-back", "money back",
    "satisfaction", "trustedsite", "norton", "mcafee",
)


@dataclass(frozen=True)
class CheckoutPageSignals:
    """Ground-truth signals extracted from a rendered Shopify checkout.

    Fields are zeroed / None / empty when ``reached_checkout`` is False;
    callers should branch on that flag before interpreting the rest.
    """

    reached_checkout: bool
    failure_reason: str | None  # e.g. "out_of_stock", "bot_wall", "timeout", "password_protected"
    checkout_flavor: str        # "onepage" | "classic" | "unknown"

    # Express-checkout wallets
    has_shop_pay: bool
    has_apple_pay: bool
    has_google_pay: bool
    has_paypal: bool
    has_amazon_pay: bool
    has_meta_pay: bool
    has_stripe_link: bool

    # BNPL providers visible in the payment section
    has_klarna: bool
    has_afterpay: bool
    has_clearpay: bool
    has_affirm: bool
    has_sezzle: bool
    has_shop_pay_installments: bool
    has_zip: bool

    # Card networks (ordered, normalized to lowercase, e.g. "visa", "mastercard")
    card_brands: tuple[str, ...]

    # Guest / account creation
    guest_checkout_available: bool
    forced_account_creation: bool

    # Checkout length & form
    checkout_step_count: int
    total_form_fields_step_one: int
    has_discount_code_field: bool
    has_gift_card_field: bool
    has_shipping_calculator: bool
    has_address_autocomplete: bool

    # Trust / misc
    trust_badge_count: int
    currency_code: str | None

    @property
    def wallet_count(self) -> int:
        return sum(
            1
            for v in (
                self.has_shop_pay,
                self.has_apple_pay,
                self.has_google_pay,
                self.has_paypal,
                self.has_amazon_pay,
                self.has_meta_pay,
                self.has_stripe_link,
            )
            if v
        )

    @property
    def bnpl_count(self) -> int:
        return sum(
            1
            for v in (
                self.has_klarna,
                self.has_afterpay,
                self.has_clearpay,
                self.has_affirm,
                self.has_sezzle,
                self.has_shop_pay_installments,
                self.has_zip,
            )
            if v
        )


def unreached(failure_reason: str) -> CheckoutPageSignals:
    """Return an empty signals object for a failed checkout flow."""
    return CheckoutPageSignals(
        reached_checkout=False,
        failure_reason=failure_reason,
        checkout_flavor="unknown",
        has_shop_pay=False,
        has_apple_pay=False,
        has_google_pay=False,
        has_paypal=False,
        has_amazon_pay=False,
        has_meta_pay=False,
        has_stripe_link=False,
        has_klarna=False,
        has_afterpay=False,
        has_clearpay=False,
        has_affirm=False,
        has_sezzle=False,
        has_shop_pay_installments=False,
        has_zip=False,
        card_brands=(),
        guest_checkout_available=False,
        forced_account_creation=False,
        checkout_step_count=0,
        total_form_fields_step_one=0,
        has_discount_code_field=False,
        has_gift_card_field=False,
        has_shipping_calculator=False,
        has_address_autocomplete=False,
        trust_badge_count=0,
        currency_code=None,
    )


def parse_checkout_page(html: str, final_url: str | None = None) -> CheckoutPageSignals:
    """Parse a rendered Shopify checkout HTML into a CheckoutPageSignals.

    The HTML is unescaped once (React embeds the GraphQL payload inside
    HTML attribute values, entity-encoded) and then interrogated with
    regex patterns. BeautifulSoup was considered but the target blobs
    are easier to find via string/regex than tree walking.

    Args:
        html: The rendered HTML captured from the checkout page.
        final_url: The page URL after navigation. Used to disambiguate
            whether we actually landed on a checkout URL.
    """
    if not html:
        return unreached("empty_html")

    u = html_unescape_mod.unescape(html)

    flavor = _detect_flavor(u)

    wallets = _detect_wallets(u)
    bnpl = _detect_bnpl(u, wallets)

    card_brands = _extract_card_brands(u)

    guest_available, forced_create = _detect_guest_checkout(u)
    step_count = _detect_step_count(u, flavor, final_url)
    form_field_count = _count_form_fields(u)
    has_discount = _has_discount_field(u)
    has_gift = _has_gift_card_field(u)
    has_shipping_calc = _has_shipping_calculator(u, flavor)
    has_autocomplete = _has_address_autocomplete(u)
    trust_count = _count_trust_badges(u)
    currency = _extract_currency(u)

    return CheckoutPageSignals(
        reached_checkout=True,
        failure_reason=None,
        checkout_flavor=flavor,
        has_shop_pay=wallets["shop_pay"],
        has_apple_pay=wallets["apple_pay"],
        has_google_pay=wallets["google_pay"],
        has_paypal=wallets["paypal"],
        has_amazon_pay=wallets["amazon_pay"],
        has_meta_pay=wallets["meta_pay"],
        has_stripe_link=wallets["stripe_link"],
        has_klarna=bnpl["klarna"],
        has_afterpay=bnpl["afterpay"],
        has_clearpay=bnpl["clearpay"],
        has_affirm=bnpl["affirm"],
        has_sezzle=bnpl["sezzle"],
        has_shop_pay_installments=bnpl["shop_pay_installments"],
        has_zip=bnpl["zip"],
        card_brands=card_brands,
        guest_checkout_available=guest_available,
        forced_account_creation=forced_create,
        checkout_step_count=step_count,
        total_form_fields_step_one=form_field_count,
        has_discount_code_field=has_discount,
        has_gift_card_field=has_gift,
        has_shipping_calculator=has_shipping_calc,
        has_address_autocomplete=has_autocomplete,
        trust_badge_count=trust_count,
        currency_code=currency,
    )


# ---------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------


def _detect_flavor(u: str) -> str:
    if 'data-testid="onepage-pay-button-cluster"' in u or "checkout-web/assets" in u:
        return "onepage"
    if 'data-step="contact_information"' in u or "checkout_one_page_accelerated_checkouts" in u:
        return "classic"
    if '<form data-payment-form' in u or '"paymentGateway"' in u:
        return "classic"
    return "unknown"


def _detect_wallets(u: str) -> dict[str, bool]:
    """Detect wallet availability from __typename markers + radio labels.

    We combine two sources because some wallets appear only in the
    GraphQL payload (express buttons) and others only in the radio
    button cluster (PayPal as a payment option).
    """
    found = {k: False for k in (
        "shop_pay", "apple_pay", "google_pay", "paypal",
        "amazon_pay", "meta_pay", "stripe_link",
    )}

    # 1) WalletConfig __typename markers in the React/GraphQL payload
    for typename, key in _WALLET_CONFIG_TYPENAMES.items():
        if typename == "ShopifyInstallmentsWalletConfig":
            continue  # handled in BNPL
        if f'"__typename":"{typename}"' in u:
            found[key] = True

    # 2) Visible radio aria-labels (covers wallets that also appear as a
    # first-step payment option, e.g. PayPal, Shop Pay).
    for match in re.finditer(
        r'<input[^>]+type="radio"[^>]+aria-label="([^"]+)"', u
    ):
        label = match.group(1).strip().lower()
        key = _PAYMENT_OPTION_LABELS.get(label)
        if key in found:
            found[key] = True

    # NOTE: we intentionally do NOT fall back to preloaded component
    # module references (e.g. "component-GooglePayButton" in link rel
    # preload tags). Shopify's checkout bundle preloads ALL wallet
    # components regardless of store configuration — so those markers
    # produce false positives. WalletConfig and radio aria-label are
    # the only trustworthy signals.

    return found


def _detect_bnpl(u: str, wallets: dict[str, bool]) -> dict[str, bool]:
    """Detect BNPL providers from radio labels, gateway names, and fallback strings."""
    found = {k: False for k in (
        "klarna", "afterpay", "clearpay", "affirm",
        "sezzle", "shop_pay_installments", "zip",
    )}

    # Shop Pay Installments comes through as a wallet config
    if '"__typename":"ShopifyInstallmentsWalletConfig"' in u:
        found["shop_pay_installments"] = True
    # Or as a string reference (older markup)
    if not found["shop_pay_installments"] and re.search(
        r"Shop[- _]?Pay[- _]?Installments", u, re.I
    ):
        found["shop_pay_installments"] = True

    # Radio aria-labels already normalized
    for match in re.finditer(
        r'<input[^>]+type="radio"[^>]+aria-label="([^"]+)"', u
    ):
        label = match.group(1).strip().lower()
        mapped = _PAYMENT_OPTION_LABELS.get(label)
        if mapped in found:
            found[mapped] = True

    # PaymentGateway / PaymentMethodProvider name hints
    for gateway_match in re.finditer(
        r'"name":"([^"]+)"[^}]*"__typename":"(PaymentGateway|PaymentMethodProvider)"',
        u,
    ):
        name = gateway_match.group(1).strip().lower()
        if "klarna" in name:
            found["klarna"] = True
        if "afterpay" in name:
            found["afterpay"] = True
        if "clearpay" in name:
            found["clearpay"] = True
        if "affirm" in name:
            found["affirm"] = True
        if "sezzle" in name:
            found["sezzle"] = True
        if "zip" in name or "quadpay" in name:
            found["zip"] = True

    # Defensive string-pattern fallback (classic / older checkouts)
    for key, patterns in _CLASSIC_PAYMENT_PATTERNS.items():
        if found.get(key):
            continue
        for pat in patterns:
            if re.search(pat, u, re.I):
                found[key] = True
                break

    return found


def _extract_card_brands(u: str) -> tuple[str, ...]:
    """Extract supported card networks from ApplePayWalletConfig.supportedNetworks.

    ApplePay's supportedNetworks array is typically the most complete
    enumeration of card brands the store accepts on checkout. Fallback:
    match brand names in alt-text of card icon images.
    """
    # Primary source
    m = re.search(
        r'ApplePayWalletConfig"[^}]+"supportedNetworks"\s*:\s*\[([^\]]+)\]', u
    )
    if m:
        raw = m.group(1)
        brands = [
            _normalize_card_brand(s.strip().strip('"'))
            for s in raw.split(",")
        ]
        brands = [b for b in brands if b]
        # Preserve order, dedupe
        seen: dict[str, None] = {}
        for b in brands:
            seen.setdefault(b, None)
        return tuple(seen.keys())

    # Fallback: scan alt text of card network imagery
    alt_brands: list[str] = []
    for alt in re.findall(r'<img[^>]+alt="([^"]+)"', u):
        brand = _normalize_card_brand(alt)
        if brand and brand not in alt_brands:
            alt_brands.append(brand)
    return tuple(alt_brands)


def _normalize_card_brand(s: str) -> str | None:
    s = s.lower()
    if s in {"visa", "mastercard", "mastercard®", "master", "amex",
             "americanexpress", "american express", "discover", "jcb",
             "diners", "dinersclub", "diners club", "unionpay",
             "union pay", "elo", "mastercard_card"}:
        return {
            "mastercard®": "mastercard",
            "master": "mastercard",
            "americanexpress": "amex",
            "american express": "amex",
            "dinersclub": "diners",
            "diners club": "diners",
            "union pay": "unionpay",
            "mastercard_card": "mastercard",
        }.get(s, s)
    # substring matches for alt text like "Visa credit card accepted"
    if "visa" in s:
        return "visa"
    if "master" in s:
        return "mastercard"
    if "amex" in s or "american express" in s:
        return "amex"
    if "discover" in s:
        return "discover"
    if "jcb" in s:
        return "jcb"
    if "diners" in s:
        return "diners"
    if "union" in s and "pay" in s:
        return "unionpay"
    if s == "elo" or s.startswith("elo "):
        return "elo"
    return None


def _detect_guest_checkout(u: str) -> tuple[bool, bool]:
    """Return (guest_checkout_available, forced_account_creation).

    Guest is available when an email input is present without a password
    field being required. Forced account is when a required password
    input appears on the first step.
    """
    # Required password on step 1 => forced account creation
    forced = False
    for name in _PASSWORD_FIELD_NAMES:
        # Look for <input name="password" ... required> (required can be anywhere in tag)
        pat = rf'<input[^>]+name="{re.escape(name)}"[^>]+required'
        if re.search(pat, u, re.I):
            forced = True
            break

    # Guest if we see an email field and we're not forcing account creation
    email_present = any(
        f'name="{n}"' in u for n in _EMAIL_FIELD_NAMES
    )
    guest = email_present and not forced
    return guest, forced


def _detect_step_count(u: str, flavor: str, final_url: str | None) -> int:
    if flavor == "onepage":
        return 1
    # Classic: URL carries ?step=X and DOM has specific step markers
    if final_url and "step=" in final_url:
        # The classic checkout renders one step per page; infer 3 from
        # the standard three-step flow.
        return 3
    if 'data-step="contact_information"' in u:
        return 3
    return 1 if flavor == "unknown" else 3


def _count_form_fields(u: str) -> int:
    """Count <input>/<select> name attributes on the first step.

    We exclude:
      - radio groups that share a name (we count each option as 1)
      - marketing opt-in checkboxes (not required for conversion)
      - hidden form tokens (authenticity_token, utf8, etc.)
      - the generic "basic" radio group name (Shopify's onepage
        checkout uses this as the payment-method radio group name)
    """
    names: list[str] = []
    for match in re.finditer(
        r'<(?:input|select)[^>]*\sname="([A-Za-z][A-Za-z0-9_\[\]-]*)"', u
    ):
        names.append(match.group(1))

    excluded = {
        "basic", "authenticity_token", "utf8", "form_key",
        "marketing_opt_in", "sms_marketing_opt_in",
    }
    relevant = [n for n in names if n not in excluded]
    return len(set(relevant))


def _has_discount_field(u: str) -> bool:
    return any(f'name="{n}"' in u for n in _DISCOUNT_FIELD_NAMES)


def _has_gift_card_field(u: str) -> bool:
    lower = u.lower()
    return any(h in lower for h in _GIFT_CARD_HINTS)


def _has_shipping_calculator(u: str, flavor: str) -> bool:
    # In the one-page checkout, shipping is rate-calculated based on
    # address automatically — always true when flavor is onepage.
    if flavor == "onepage":
        return True
    return (
        "shipping-rate" in u
        or "checkout[shipping_rate]" in u
        or "shipping_estimator" in u
    )


def _has_address_autocomplete(u: str) -> bool:
    # Shopify onepage has a built-in address autocomplete under the
    # first-name/address1 fields; it emits distinctive attributes.
    return (
        'data-shopify-autocomplete' in u
        or 'data-autocomplete-field' in u
        or 'google-places-api' in u
        or 'autocomplete="shipping"' in u.lower()
    )


def _count_trust_badges(u: str) -> int:
    """Count images / icons with alt/text matching trust keywords."""
    count = 0
    lower = u.lower()
    for kw in _TRUST_KEYWORDS:
        # Count distinct mentions in alt or adjacent text
        count += len(re.findall(
            rf'alt="[^"]*{re.escape(kw)}[^"]*"', lower
        ))
    return count


def _extract_currency(u: str) -> str | None:
    # GraphQL: "currencyCode":"USD"
    m = re.search(r'"currencyCode"\s*:\s*"([A-Z]{3})"', u)
    if m:
        return m.group(1)
    # Classic: <meta data-currency="USD">
    m = re.search(r'data-currency="([A-Z]{3})"', u)
    if m:
        return m.group(1)
    return None

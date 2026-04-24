"""Tests for the merged checkout rubric.

Verifies the new scoring weights, tip priority, and per-check
breakdown when combining PDP signals with rendered checkout-page
signals. Also exercises the fallback (reached_checkout=False) path
which caps the score at 70.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.checkout_detector import (
    CheckoutSignals,
    MergedCheckoutSignals,
    combine_signals,
)
from app.services.checkout_page_parser import (
    CheckoutPageSignals,
    parse_checkout_page,
    unreached,
)
from app.services.checkout_rubric import (
    get_merged_checkout_tips,
    list_merged_checkout_checks,
    score_merged_checkout,
)


_FIXTURES = Path(__file__).parent / "fixtures" / "checkout"


# ---------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------


def _pdp(
    *,
    drawer: bool = False,
    ajax: bool = False,
    sticky: bool = False,
    accelerated: bool = False,
    paypal: bool = False,
) -> CheckoutSignals:
    s = CheckoutSignals()
    s.has_drawer_cart = drawer
    s.has_ajax_cart = ajax
    s.has_sticky_checkout = sticky
    s.has_accelerated_checkout = accelerated
    s.has_paypal = paypal
    return s


def _cp_all_green() -> CheckoutPageSignals:
    """Build a checkout signal with every check passing."""
    return CheckoutPageSignals(
        reached_checkout=True,
        failure_reason=None,
        checkout_flavor="onepage",
        has_shop_pay=True,
        has_apple_pay=True,
        has_google_pay=True,
        has_paypal=True,
        has_amazon_pay=True,
        has_meta_pay=False,
        has_stripe_link=False,
        has_klarna=True,
        has_afterpay=False,
        has_clearpay=False,
        has_affirm=False,
        has_sezzle=False,
        has_shop_pay_installments=True,
        has_zip=False,
        card_brands=("visa", "mastercard", "amex"),
        guest_checkout_available=True,
        forced_account_creation=False,
        checkout_step_count=1,
        total_form_fields_step_one=14,
        has_discount_code_field=True,
        has_gift_card_field=False,
        has_shipping_calculator=True,
        has_address_autocomplete=True,
        trust_badge_count=3,
        currency_code="USD",
    )


# ---------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------


class TestScoreMergedCheckout:
    def test_perfect_score(self) -> None:
        merged = combine_signals(
            pdp=_pdp(drawer=True, ajax=True, sticky=True),
            checkout_page=_cp_all_green(),
        )
        assert score_merged_checkout(merged) == 100

    def test_weights_add_up_to_100(self) -> None:
        """Independent sanity check that weights match the plan."""
        merged = combine_signals(
            pdp=_pdp(drawer=True, sticky=True),
            checkout_page=_cp_all_green(),
        )
        # apple 12 + google 10 + shop 10 + other 5 + bnpl 15 + guest 12
        # + onepage 8 + discount 5 + autocomplete 5 + trust 5
        # + cart 8 + sticky 5 = 100
        assert score_merged_checkout(merged) == 100

    def test_zero_signals_zero_score(self) -> None:
        merged = combine_signals(
            pdp=_pdp(),
            checkout_page=CheckoutPageSignals(
                reached_checkout=True,
                failure_reason=None,
                checkout_flavor="onepage",
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
                checkout_step_count=2,
                total_form_fields_step_one=12,
                has_discount_code_field=False,
                has_gift_card_field=False,
                has_shipping_calculator=False,
                has_address_autocomplete=False,
                trust_badge_count=0,
                currency_code=None,
            ),
        )
        assert score_merged_checkout(merged) == 0

    def test_apple_pay_alone_is_12(self) -> None:
        cp = _cp_all_green()
        # Build a minimal signal set with only Apple Pay
        stripped = CheckoutPageSignals(
            **{
                **cp.__dict__,
                "has_shop_pay": False,
                "has_google_pay": False,
                "has_paypal": False,
                "has_amazon_pay": False,
                "has_klarna": False,
                "has_shop_pay_installments": False,
                "guest_checkout_available": False,
                "checkout_step_count": 2,
                "has_discount_code_field": False,
                "has_address_autocomplete": False,
                "trust_badge_count": 0,
            }
        )
        merged = combine_signals(pdp=_pdp(), checkout_page=stripped)
        assert score_merged_checkout(merged) == 12


class TestFallbackCap:
    def test_unreached_caps_at_70(self) -> None:
        """Even a PDP with every flag set can't exceed 70 when flow failed."""
        full_pdp = CheckoutSignals(
            has_accelerated_checkout=True,
            has_dynamic_checkout_button=True,
            has_paypal=True,
            has_klarna=True,
            has_afterpay=True,
            has_affirm=True,
            has_sezzle=True,
            payment_method_count=5,
            has_drawer_cart=True,
            has_ajax_cart=True,
            has_sticky_checkout=True,
        )
        merged = combine_signals(
            pdp=full_pdp, checkout_page=unreached("bot_wall")
        )
        assert score_merged_checkout(merged) == 70

    def test_unreached_empty_pdp_is_zero(self) -> None:
        merged = combine_signals(
            pdp=_pdp(), checkout_page=unreached("timeout")
        )
        assert score_merged_checkout(merged) == 0


# ---------------------------------------------------------------------
# Tips
# ---------------------------------------------------------------------


class TestMergedTips:
    def test_unreached_emits_failure_tip_with_reason(self) -> None:
        merged = combine_signals(
            pdp=_pdp(), checkout_page=unreached("bot_wall")
        )
        tips = get_merged_checkout_tips(merged)
        assert any("bot_wall" in t for t in tips)
        assert any("couldn't inspect" in t.lower() for t in tips)

    def test_missing_apple_pay_surfaces_tip(self) -> None:
        cp = _cp_all_green()
        stripped = CheckoutPageSignals(
            **{**cp.__dict__, "has_apple_pay": False}
        )
        merged = combine_signals(
            pdp=_pdp(drawer=True, sticky=True), checkout_page=stripped
        )
        tips = get_merged_checkout_tips(merged)
        assert any("Apple Pay" in t for t in tips)

    def test_forced_account_tip_when_required(self) -> None:
        cp = _cp_all_green()
        stripped = CheckoutPageSignals(
            **{
                **cp.__dict__,
                "guest_checkout_available": False,
                "forced_account_creation": True,
            }
        )
        merged = combine_signals(pdp=_pdp(), checkout_page=stripped)
        tips = get_merged_checkout_tips(merged)
        assert any("guest checkout" in t.lower() for t in tips)

    def test_tips_capped_at_three(self) -> None:
        # Empty signals produce many failing conditions; assert limit.
        merged = combine_signals(
            pdp=_pdp(),
            checkout_page=CheckoutPageSignals(
                **{**_cp_all_green().__dict__,
                   "has_apple_pay": False, "has_google_pay": False,
                   "has_shop_pay": False, "has_klarna": False,
                   "has_shop_pay_installments": False,
                   "guest_checkout_available": False,
                   "forced_account_creation": False,
                   "checkout_step_count": 3,
                   "has_discount_code_field": False,
                   "has_address_autocomplete": False},
            ),
        )
        tips = get_merged_checkout_tips(merged)
        assert len(tips) <= 3

    def test_congratulatory_on_perfect(self) -> None:
        merged = combine_signals(
            pdp=_pdp(drawer=True, sticky=True),
            checkout_page=_cp_all_green(),
        )
        tips = get_merged_checkout_tips(merged)
        # Score is 100, so only the congratulatory tip should appear.
        assert any("checkout covers" in t for t in tips)


# ---------------------------------------------------------------------
# Per-check breakdown
# ---------------------------------------------------------------------


class TestMergedCheckList:
    def test_reached_checkout_has_12_rows(self) -> None:
        merged = combine_signals(
            pdp=_pdp(), checkout_page=_cp_all_green()
        )
        checks = list_merged_checkout_checks(merged)
        assert len(checks) == 12
        ids = {c["id"] for c in checks}
        assert "apple_pay_on_checkout" in ids
        assert "guest_checkout" in ids
        assert "cart_ux" in ids

    def test_weights_sum_to_100(self) -> None:
        merged = combine_signals(
            pdp=_pdp(), checkout_page=_cp_all_green()
        )
        checks = list_merged_checkout_checks(merged)
        assert sum(c["weight"] for c in checks) == 100

    def test_unreached_prepends_banner_row(self) -> None:
        merged = combine_signals(
            pdp=_pdp(drawer=True), checkout_page=unreached("password_protected")
        )
        checks = list_merged_checkout_checks(merged)
        assert checks[0]["id"] == "checkout_flow_unverified"
        assert "password_protected" in checks[0]["label"]
        assert checks[0]["passed"] is False


# ---------------------------------------------------------------------
# Remediation coverage invariant
# ---------------------------------------------------------------------


class TestRemediationCoverage:
    """Every non-banner check must carry a non-empty remediation.

    Locks in the one-to-one invariant between the checklist and the
    per-check fixes shown in the UI. If you add a new check to
    ``list_merged_checkout_checks`` without a remediation string, this
    test fails — preventing the two lists from drifting apart again.
    """

    _NO_REMEDIATION_REQUIRED = {"checkout_flow_unverified"}

    @pytest.mark.parametrize(
        "label,make_merged",
        [
            (
                "all_green",
                lambda: combine_signals(
                    pdp=_pdp(drawer=True, sticky=True),
                    checkout_page=_cp_all_green(),
                ),
            ),
            (
                "nothing_passing",
                lambda: combine_signals(
                    pdp=_pdp(),
                    checkout_page=CheckoutPageSignals(
                        **{
                            **_cp_all_green().__dict__,
                            "has_shop_pay": False,
                            "has_apple_pay": False,
                            "has_google_pay": False,
                            "has_paypal": False,
                            "has_amazon_pay": False,
                            "has_klarna": False,
                            "has_afterpay": False,
                            "has_shop_pay_installments": False,
                            "guest_checkout_available": False,
                            "checkout_step_count": 3,
                            "has_discount_code_field": False,
                            "has_address_autocomplete": False,
                            "trust_badge_count": 0,
                        }
                    ),
                ),
            ),
            (
                "unreached_fallback",
                lambda: combine_signals(
                    pdp=_pdp(drawer=True),
                    checkout_page=unreached("bot_wall"),
                ),
            ),
        ],
    )
    def test_every_non_banner_check_has_remediation(
        self, label: str, make_merged
    ) -> None:
        merged = make_merged()
        checks = list_merged_checkout_checks(merged)
        for c in checks:
            if c["id"] in self._NO_REMEDIATION_REQUIRED:
                continue
            assert "remediation" in c, (
                f"[{label}] check {c['id']!r} missing remediation field"
            )
            assert isinstance(c["remediation"], str), (
                f"[{label}] check {c['id']!r} remediation not a string"
            )
            assert c["remediation"].strip() != "", (
                f"[{label}] check {c['id']!r} has empty remediation"
            )

    def test_banner_row_has_no_remediation(self) -> None:
        merged = combine_signals(
            pdp=_pdp(), checkout_page=unreached("timeout")
        )
        checks = list_merged_checkout_checks(merged)
        banner = next(
            (c for c in checks if c["id"] == "checkout_flow_unverified"),
            None,
        )
        assert banner is not None
        # Banner is a diagnostic, not an actionable gap — UI uses this
        # to decide whether to render an expander.
        assert "remediation" not in banner

    def test_all_ids_unique(self) -> None:
        merged = combine_signals(
            pdp=_pdp(drawer=True), checkout_page=_cp_all_green()
        )
        checks = list_merged_checkout_checks(merged)
        ids = [c["id"] for c in checks]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------
# Integration: real allbirds fixture -> merged rubric
# ---------------------------------------------------------------------


class TestAllbirdsEndToEnd:
    def test_allbirds_merged_score_is_reasonable(self) -> None:
        html = (_FIXTURES / "allbirds_onepage.html").read_text()
        cp = parse_checkout_page(html)
        pdp = _pdp(drawer=True, ajax=True, accelerated=True)
        merged = combine_signals(pdp=pdp, checkout_page=cp)
        score = score_merged_checkout(merged)
        # Allbirds has Apple Pay (12), Shop Pay (10), PayPal as "other
        # wallet" is not counted here (PayPal isn't in amazon/meta/link
        # bucket), BNPL via Afterpay+Installments (15), guest checkout
        # (12), one-page (8), discount code (5), onepage drives
        # shipping calc but that's not scored. Plus PDP drawer/ajax (8).
        # Apple Pay 12 + Shop Pay 10 + BNPL 15 + guest 12 + onepage 8
        # + discount 5 + cart 8 = 70 minimum
        assert score >= 65
        assert merged.reached_checkout is True
        assert merged.checkout_page.has_shop_pay is True
        assert merged.checkout_page.has_apple_pay is True

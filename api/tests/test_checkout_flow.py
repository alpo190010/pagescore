"""Tests for the checkout flow simulator.

The pure helpers (variant extraction, bot-wall / password-page
classification, origin parsing) are covered by unit tests. The
end-to-end Playwright flow is exercised by an integration test gated
behind ``ALPO_LIVE_CHECKOUT_TEST=1`` so CI doesn't hammer live
merchants on every run.
"""

from __future__ import annotations

import os

import pytest

from app.services.checkout_flow_simulator import (
    FlowResult,
    _extract_variant_id,
    _is_bot_wall,
    _is_password_page,
    _origin_of,
    simulate_checkout_flow,
)


# ---------------------------------------------------------------------
# _origin_of
# ---------------------------------------------------------------------


class TestOriginOf:
    def test_basic_https(self) -> None:
        assert _origin_of("https://www.allbirds.com/products/x") == "https://www.allbirds.com"

    def test_with_port(self) -> None:
        assert _origin_of("http://shop.test:8080/products/y") == "http://shop.test:8080"

    def test_invalid_url_raises(self) -> None:
        with pytest.raises(ValueError):
            _origin_of("not-a-url")


# ---------------------------------------------------------------------
# _extract_variant_id
# ---------------------------------------------------------------------


class TestExtractVariantId:
    def test_hidden_form_input(self) -> None:
        html = (
            '<form action="/cart/add">'
            '<input type="hidden" name="id" value="40196449337424">'
            '</form>'
        )
        assert _extract_variant_id(html) == 40196449337424

    def test_shopify_analytics_meta(self) -> None:
        html = (
            '<script>window.ShopifyAnalytics = {"meta":'
            '{"product":{"variants":[{"id":12345678,"title":"Default"}]}}};'
            '</script>'
        )
        assert _extract_variant_id(html) == 12345678

    def test_js_variant_id_pattern(self) -> None:
        html = '<script>var variantId = "99887766554";</script>'
        assert _extract_variant_id(html) == 99887766554

    def test_no_variant_returns_none(self) -> None:
        html = "<html><body>No product here</body></html>"
        assert _extract_variant_id(html) is None

    def test_short_numeric_strings_ignored(self) -> None:
        # Shopify variant ids are >= 8 digits; stray short numbers
        # like price="42" must not be mistaken for them.
        html = '<input name="id" value="42">'
        assert _extract_variant_id(html) is None


# ---------------------------------------------------------------------
# _is_password_page
# ---------------------------------------------------------------------


class TestPasswordPage:
    def test_password_path_in_url(self) -> None:
        assert _is_password_page(
            "<html></html>",
            final_url="https://shop.example.com/password",
            origin="https://shop.example.com",
        ) is True

    def test_shopify_password_page_markup(self) -> None:
        html = (
            '<html><body><form><input type="password" name="password">'
            '</form><script>Shopify.routes</script></body></html>'
        )
        assert _is_password_page(
            html,
            final_url="https://shop.example.com/",
            origin="https://shop.example.com",
        ) is True

    def test_normal_checkout_not_password(self) -> None:
        html = "<html><body>Regular checkout</body></html>"
        assert _is_password_page(
            html,
            final_url="https://shop.example.com/checkouts/cn/tok",
            origin="https://shop.example.com",
        ) is False


# ---------------------------------------------------------------------
# _is_bot_wall
# ---------------------------------------------------------------------


class TestBotWall:
    def test_cloudflare_challenge(self) -> None:
        html = '<html><body class="cf-challenge">Verify</body></html>'
        assert _is_bot_wall(html) is True

    def test_perimeterx(self) -> None:
        html = '<script src="_pxCaptcha"></script>'
        assert _is_bot_wall(html) is True

    def test_verify_human_phrase(self) -> None:
        html = "<html><body>Please verify you are a human</body></html>"
        assert _is_bot_wall(html) is True

    def test_clean_html_not_flagged(self) -> None:
        html = "<html><body>Normal checkout content here</body></html>"
        assert _is_bot_wall(html) is False


# ---------------------------------------------------------------------
# simulate_checkout_flow — error classification (no network)
# ---------------------------------------------------------------------


class TestSimulateCheckoutFlowErrorShape:
    @pytest.mark.asyncio
    async def test_invalid_url_returns_variant_not_found(self) -> None:
        """Domain that doesn't exist should yield a classified failure,
        not a raised exception."""
        # A .invalid TLD is RFC-reserved to never resolve, so Playwright
        # will get an ERR_NAME_NOT_RESOLVED and we should fall through
        # the error path.
        result = await simulate_checkout_flow(
            "https://this-domain-definitely-does-not-exist-123xyz.invalid/products/x",
            timeout_s=15.0,
        )
        assert isinstance(result, FlowResult)
        assert result.signals.reached_checkout is False
        # Network failure may surface as network_error or (if
        # Playwright takes too long) timeout. Either is acceptable.
        assert result.signals.failure_reason in {
            "network_error",
            "timeout",
            "variant_not_found",
        }


# ---------------------------------------------------------------------
# Integration test (env-gated)
# ---------------------------------------------------------------------


LIVE = os.environ.get("ALPO_LIVE_CHECKOUT_TEST") == "1"


@pytest.mark.skipif(not LIVE, reason="set ALPO_LIVE_CHECKOUT_TEST=1 to run")
@pytest.mark.asyncio
async def test_live_allbirds_reaches_checkout() -> None:
    """Drive the real allbirds.com flow and assert we land on /checkouts/*.

    Requires Playwright Chromium installed locally. Creates an
    abandoned cart on Allbirds — acceptable for a one-off verification
    but don't run this in CI.
    """
    result = await simulate_checkout_flow(
        "https://www.allbirds.com/products/trino-cozy-crew",
        timeout_s=60.0,
    )
    assert result.signals.reached_checkout is True, (
        f"expected success but got {result.signals.failure_reason}"
    )
    assert result.signals.checkout_flavor == "onepage"
    assert result.signals.has_shop_pay is True
    assert result.signals.has_apple_pay is True
    assert result.variant_id is not None
    assert result.final_url is not None
    assert "/checkouts/" in result.final_url

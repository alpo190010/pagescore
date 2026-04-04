"""Tests for shipping transparency detector, rubric, and tip selector."""

from app.services.shipping_detector import ShippingSignals, detect_shipping
from app.services.shipping_rubric import get_shipping_tips, score_shipping


# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------


def _empty_html() -> str:
    return "<html><body><h1>Product Title</h1><p>Some description.</p></body></html>"


def _free_shipping_html() -> str:
    return """<html><body>
    <h1>Premium Widget</h1>
    <div class="announcement-bar">Free Shipping on all orders!</div>
    <div class="product-form"><button>Add to Cart</button></div>
    </body></html>"""


def _free_shipping_threshold_html() -> str:
    return """<html><body>
    <h1>Premium Widget</h1>
    <div class="free-shipping-bar">Free shipping on orders over $75</div>
    <div class="product-form"><button>Add to Cart</button></div>
    </body></html>"""


def _delivery_date_html() -> str:
    return """<html><body>
    <h1>Premium Widget</h1>
    <div class="shipping-info">
        <p>Arrives by Thursday, Feb 12</p>
    </div>
    </body></html>"""


def _delivery_date_alt_html() -> str:
    return """<html><body>
    <h1>Premium Widget</h1>
    <div class="delivery-info">
        <p>Get it by Wednesday</p>
    </div>
    </body></html>"""


def _vague_estimate_html() -> str:
    return """<html><body>
    <h1>Premium Widget</h1>
    <div class="product__shipping">Ships in 3-5 business days</div>
    </body></html>"""


def _edd_app_html() -> str:
    return """<html><body>
    <h1>Premium Widget</h1>
    <div class="aftership-edd" data-aftership-edd="true">
        <span class="aftership-delivery-date">Arrives Feb 14-16</span>
    </div>
    </body></html>"""


def _synctrack_html() -> str:
    return """<html><body>
    <h1>Premium Widget</h1>
    <div class="synctrack-delivery">Estimated delivery: Feb 15</div>
    <script src="https://cdn.synctrack.com/edd.js"></script>
    </body></html>"""


def _shipping_cost_html() -> str:
    return """<html><body>
    <h1>Premium Widget</h1>
    <div class="shipping-message">Shipping: $5.99</div>
    </body></html>"""


def _calculated_at_checkout_html() -> str:
    return """<html><body>
    <h1>Premium Widget</h1>
    <p>Shipping calculated at checkout</p>
    </body></html>"""


def _jsonld_shipping_html() -> str:
    return """<html><head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Premium Widget",
        "offers": {
            "@type": "Offer",
            "price": "49.99",
            "priceCurrency": "USD",
            "shippingDetails": {
                "@type": "OfferShippingDetails",
                "shippingRate": {
                    "@type": "MonetaryAmount",
                    "value": "0",
                    "currency": "USD"
                }
            }
        }
    }
    </script>
    </head><body><h1>Premium Widget</h1></body></html>"""


def _shipping_policy_link_html() -> str:
    return """<html><body>
    <h1>Premium Widget</h1>
    <a href="/policies/shipping">Shipping Policy</a>
    </body></html>"""


def _returns_html() -> str:
    return """<html><body>
    <h1>Premium Widget</h1>
    <div class="shipping-info">
        <span>Free Returns within 30 days</span>
    </div>
    </body></html>"""


def _full_shipping_html() -> str:
    return """<html><head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Premium Widget",
        "offers": {
            "@type": "Offer",
            "price": "49.99",
            "shippingDetails": {
                "@type": "OfferShippingDetails"
            }
        }
    }
    </script>
    </head><body>
    <h1>Premium Widget</h1>
    <div class="free-shipping-bar">Free shipping on orders over $75</div>
    <div class="aftership-edd">
        <span>Arrives by Thursday, Feb 12</span>
    </div>
    <p>Shipping: $0.00</p>
    <a href="/policies/shipping">Shipping Policy</a>
    <span>Free Returns - 30 day money-back guarantee</span>
    </body></html>"""


def _all_true_signals() -> ShippingSignals:
    return ShippingSignals(
        has_free_shipping=True,
        has_free_shipping_threshold=True,
        free_shipping_threshold_value=75.0,
        has_delivery_date=True,
        has_delivery_estimate=False,
        has_edd_app=True,
        has_shipping_cost_shown=True,
        has_shipping_in_structured_data=True,
        has_shipping_policy_link=True,
        has_returns_mentioned=True,
    )


# ---------------------------------------------------------------------------
# Detection tests
# ---------------------------------------------------------------------------


class TestDetection:
    def test_empty_html(self):
        signals = detect_shipping(_empty_html())
        assert signals.has_free_shipping is False
        assert signals.has_delivery_date is False
        assert signals.has_edd_app is False
        assert signals.has_shipping_policy_link is False

    def test_empty_string(self):
        signals = detect_shipping("")
        assert signals == ShippingSignals()

    def test_free_shipping(self):
        signals = detect_shipping(_free_shipping_html())
        assert signals.has_free_shipping is True
        assert signals.has_free_shipping_threshold is False

    def test_free_shipping_threshold(self):
        signals = detect_shipping(_free_shipping_threshold_html())
        assert signals.has_free_shipping is True
        assert signals.has_free_shipping_threshold is True
        assert signals.free_shipping_threshold_value == 75.0

    def test_specific_delivery_date(self):
        signals = detect_shipping(_delivery_date_html())
        assert signals.has_delivery_date is True
        assert signals.has_delivery_estimate is False

    def test_specific_delivery_date_day_name(self):
        signals = detect_shipping(_delivery_date_alt_html())
        assert signals.has_delivery_date is True

    def test_vague_estimate(self):
        signals = detect_shipping(_vague_estimate_html())
        assert signals.has_delivery_estimate is True
        assert signals.has_delivery_date is False

    def test_aftership_edd_app(self):
        signals = detect_shipping(_edd_app_html())
        assert signals.has_edd_app is True

    def test_synctrack_edd_app(self):
        signals = detect_shipping(_synctrack_html())
        assert signals.has_edd_app is True

    def test_shipping_cost_dollar(self):
        signals = detect_shipping(_shipping_cost_html())
        assert signals.has_shipping_cost_shown is True

    def test_shipping_cost_calculated(self):
        signals = detect_shipping(_calculated_at_checkout_html())
        assert signals.has_shipping_cost_shown is True

    def test_jsonld_shipping(self):
        signals = detect_shipping(_jsonld_shipping_html())
        assert signals.has_shipping_in_structured_data is True

    def test_shipping_policy_link(self):
        signals = detect_shipping(_shipping_policy_link_html())
        assert signals.has_shipping_policy_link is True

    def test_returns_mentioned(self):
        signals = detect_shipping(_returns_html())
        assert signals.has_returns_mentioned is True

    def test_full_shipping(self):
        signals = detect_shipping(_full_shipping_html())
        assert signals.has_free_shipping is True
        assert signals.has_free_shipping_threshold is True
        assert signals.free_shipping_threshold_value == 75.0
        assert signals.has_delivery_date is True
        assert signals.has_edd_app is True
        assert signals.has_shipping_cost_shown is True
        assert signals.has_shipping_in_structured_data is True
        assert signals.has_shipping_policy_link is True
        assert signals.has_returns_mentioned is True

    def test_free_shipping_not_from_h1(self):
        """Free shipping text inside <h1> should not trigger detection."""
        html = "<html><body><h1>Free Shipping Widget</h1></body></html>"
        signals = detect_shipping(html)
        assert signals.has_free_shipping is False

    def test_edd_class_fragment(self):
        html = """<html><body>
        <div class="product-delivery-date-widget">Arrives soon</div>
        </body></html>"""
        signals = detect_shipping(html)
        assert signals.has_edd_app is True

    def test_shipping_link_text(self):
        html = """<html><body>
        <a href="/info">Shipping Information</a>
        </body></html>"""
        signals = detect_shipping(html)
        assert signals.has_shipping_policy_link is True


# ---------------------------------------------------------------------------
# Scoring tests
# ---------------------------------------------------------------------------


class TestScoring:
    def test_zero_score(self):
        assert score_shipping(ShippingSignals()) == 0

    def test_perfect_score(self):
        # Max is 95 when has_delivery_date=True (25 pts) — the 5-pt
        # vague/edd_app partial credit is mutually exclusive.
        assert score_shipping(_all_true_signals()) == 95

    def test_free_shipping_only(self):
        signals = ShippingSignals(has_free_shipping=True)
        assert score_shipping(signals) == 25

    def test_delivery_date_only(self):
        signals = ShippingSignals(has_delivery_date=True)
        assert score_shipping(signals) == 25

    def test_vague_estimate_partial_credit(self):
        signals = ShippingSignals(has_delivery_estimate=True)
        assert score_shipping(signals) == 5

    def test_edd_app_partial_credit(self):
        signals = ShippingSignals(has_edd_app=True)
        assert score_shipping(signals) == 5

    def test_specific_date_overrides_vague(self):
        """Specific date gets 25 pts, not 25+5."""
        signals = ShippingSignals(
            has_delivery_date=True,
            has_delivery_estimate=True,
        )
        assert score_shipping(signals) == 25

    def test_threshold_only(self):
        signals = ShippingSignals(
            has_free_shipping=True,
            has_free_shipping_threshold=True,
        )
        # 25 (free) + 15 (threshold) = 40
        assert score_shipping(signals) == 40

    def test_structured_data_only(self):
        signals = ShippingSignals(has_shipping_in_structured_data=True)
        assert score_shipping(signals) == 10

    def test_policy_link_only(self):
        signals = ShippingSignals(has_shipping_policy_link=True)
        assert score_shipping(signals) == 5

    def test_returns_only(self):
        signals = ShippingSignals(has_returns_mentioned=True)
        assert score_shipping(signals) == 5

    def test_combined_score(self):
        """Free shipping + threshold + cost shown + policy = 25+15+10+5 = 55."""
        signals = ShippingSignals(
            has_free_shipping=True,
            has_free_shipping_threshold=True,
            has_shipping_cost_shown=True,
            has_shipping_policy_link=True,
        )
        assert score_shipping(signals) == 55


# ---------------------------------------------------------------------------
# Tip tests
# ---------------------------------------------------------------------------


class TestTips:
    def test_no_signals_gives_tips(self):
        tips = get_shipping_tips(ShippingSignals())
        assert len(tips) > 0
        assert len(tips) <= 3

    def test_max_three_tips(self):
        tips = get_shipping_tips(ShippingSignals())
        assert len(tips) == 3

    def test_perfect_signals_congratulatory(self):
        tips = get_shipping_tips(_all_true_signals())
        assert len(tips) > 0
        assert "Strong shipping" in tips[0] or "shipping transparency" in tips[0].lower()

    def test_no_free_shipping_tip(self):
        tips = get_shipping_tips(ShippingSignals())
        assert any("free shipping" in t.lower() for t in tips)

    def test_no_delivery_date_tip(self):
        tips = get_shipping_tips(ShippingSignals())
        assert any("delivery" in t.lower() for t in tips)

    def test_vague_upgrade_tip(self):
        signals = ShippingSignals(
            has_free_shipping=True,
            has_delivery_estimate=True,
        )
        tips = get_shipping_tips(signals)
        assert any("specific" in t.lower() or "upgrade" in t.lower() for t in tips)

    def test_threshold_tip_when_free_but_no_threshold(self):
        signals = ShippingSignals(has_free_shipping=True)
        tips = get_shipping_tips(signals)
        assert any("threshold" in t.lower() for t in tips)

    def test_tips_have_citations(self):
        tips = get_shipping_tips(ShippingSignals())
        for tip in tips:
            assert "(" in tip, f"Tip missing citation: {tip}"


# ---------------------------------------------------------------------------
# Dataclass structure tests
# ---------------------------------------------------------------------------


class TestDataclass:
    def test_field_count(self):
        signals = ShippingSignals()
        fields = [f for f in signals.__dataclass_fields__]
        assert len(fields) == 10

    def test_defaults(self):
        signals = ShippingSignals()
        assert signals.has_free_shipping is False
        assert signals.has_free_shipping_threshold is False
        assert signals.free_shipping_threshold_value is None
        assert signals.has_delivery_date is False
        assert signals.has_delivery_estimate is False
        assert signals.has_edd_app is False
        assert signals.has_shipping_cost_shown is False
        assert signals.has_shipping_in_structured_data is False
        assert signals.has_shipping_policy_link is False
        assert signals.has_returns_mentioned is False

    def test_instantiation_with_kwargs(self):
        signals = ShippingSignals(
            has_free_shipping=True,
            free_shipping_threshold_value=50.0,
        )
        assert signals.has_free_shipping is True
        assert signals.free_shipping_threshold_value == 50.0


# ---------------------------------------------------------------------------
# End-to-end tests
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_full_pipeline(self):
        signals = detect_shipping(_full_shipping_html())
        score = score_shipping(signals)
        tips = get_shipping_tips(signals)
        # 25+25+15+10+10+5+5=95 (vague 5 pts excluded by specific date)
        assert score == 95
        assert len(tips) > 0

    def test_empty_pipeline(self):
        signals = detect_shipping(_empty_html())
        score = score_shipping(signals)
        tips = get_shipping_tips(signals)
        assert score == 0
        assert len(tips) == 3

    def test_partial_pipeline(self):
        signals = detect_shipping(_free_shipping_threshold_html())
        score = score_shipping(signals)
        tips = get_shipping_tips(signals)
        assert score == 40  # 25 (free) + 15 (threshold)
        assert len(tips) > 0
        assert len(tips) <= 3

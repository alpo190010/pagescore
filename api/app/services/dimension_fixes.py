"""Static structured fix content per store-wide dimension.

Mirrors the deterministic pattern of the per-dimension ``*_rubric.py`` files:
no LLM, no per-store personalization in v1. The sidebar's Store Health tab
exposes only the 7 store-wide dimensions, so only those keys are populated.

Shape:
    {
        "label": str,              # human-readable dimension name
        "problem": str,             # long-form diagnosis shown in the callout
        "revenue_gain": str,        # e.g. "+$520 per 1k visitors"
        "effort": str,              # e.g. "2 hours"
        "scope": str,               # e.g. "All products"
        "steps": list[str],         # numbered action items
        "code": str | None,         # optional copy-pasteable snippet
    }
"""

FIX_CONTENT: dict[str, dict] = {
    "pageSpeed": {
        "label": "Page Speed",
        "problem": (
            "Largest Contentful Paint often lands above 3s on mobile for Shopify "
            "stores that load Klaviyo, TrustPilot and ReCharge synchronously. "
            "Render-blocking scripts and missing preconnect hints mean hero images "
            "arrive after shoppers have already bounced."
        ),
        "revenue_gain": "+$520 per 1k visitors",
        "effort": "2 hours",
        "scope": "All products",
        "steps": [
            "Preconnect to cdn.shopify.com and fonts.gstatic.com in <head>",
            "Defer Klaviyo, TrustPilot and ReCharge until user interaction",
            "Swap hero image to responsive srcset with AVIF fallback",
            "Remove unused theme apps from the global layout",
        ],
        "code": (
            "<!-- Add to <head> -->\n"
            '<link rel="preconnect" href="https://cdn.shopify.com" crossorigin>\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link rel="preload" as="image" href="{{ product.featured_image | image_url }}">'
        ),
    },
    "checkout": {
        "label": "Checkout & Payments",
        "problem": (
            "Stores offering only card + PayPal miss the BNPL cohort: 44% of Gen Z "
            "shoppers prefer pay-later, and Shop Pay Express delivers 1.72x higher "
            "checkout conversion than guest checkout."
        ),
        "revenue_gain": "+$740 per 1k visitors",
        "effort": "30 minutes",
        "scope": "All products",
        "steps": [
            "Install Shop Pay, Klarna, and Afterpay in Payments settings",
            "Enable Shop Pay Express button on product and cart templates",
            'Add an installment callout ("4 payments of $X") under the price',
            "Verify Apple Pay shows on iOS Safari sessions",
        ],
        "code": (
            "{%- comment -%} Add Shop Pay Express above Add to Cart {%- endcomment -%}\n"
            "{% render 'shopify-pay-button', product: product %}\n\n"
            "<!-- Under price -->\n"
            '<div class="installments">\n'
            "  or 4 payments of {{ product.price | divided_by: 4 | money }} with\n"
            "  <span>Afterpay</span>\n"
            "</div>"
        ),
    },
    "aiDiscoverability": {
        "label": "AI Discoverability",
        "problem": (
            "ChatGPT, Perplexity, and Google AI Mode all need structured data to "
            "cite your store. Without it, AI-driven shopping traffic — which "
            "converts at 14.2% vs 2.8% from classic Google — routes to competitors."
        ),
        "revenue_gain": "+$390 per 1k visitors",
        "effort": "1 hour",
        "scope": "All products",
        "steps": [
            "Add Organization + WebSite JSON-LD to theme.liquid",
            "Add Product + Offer schema to product templates",
            "Publish /llms.txt with a product catalog summary",
            "Verify in Google Rich Results Test",
        ],
        "code": (
            '<script type="application/ld+json">\n'
            "{\n"
            '  "@context": "https://schema.org",\n'
            '  "@type": "Organization",\n'
            '  "name": "Your Store",\n'
            '  "url": "https://example.com",\n'
            '  "logo": "https://example.com/logo.png",\n'
            '  "sameAs": ["https://instagram.com/yourstore","https://tiktok.com/@yourstore"]\n'
            "}\n"
            "</script>"
        ),
    },
    "shipping": {
        "label": "Shipping Transparency",
        "problem": (
            '"3–5 business days" is vague. Specific delivery-date promises '
            '("Get it by Thursday, Oct 24") convert 24% better than estimates and '
            'reduce "where is my order" tickets by 31%.'
        ),
        "revenue_gain": "+$280 per 1k visitors",
        "effort": "45 minutes",
        "scope": "All products",
        "steps": [
            "Install Shopify Delivery Dates app or equivalent",
            'Display "Get it by [date]" above Add to Cart',
            "Show free-shipping threshold progress bar in cart",
            "Add return window to product page (not just footer)",
        ],
        "code": (
            "<!-- Above Add to Cart -->\n"
            '<div class="delivery-promise">\n'
            "  <svg>...</svg>\n"
            "  <span>Get it by <strong>{{ delivery_date }}</strong></span>\n"
            "  <small>Order within {{ cutoff_timer }}</small>\n"
            "</div>"
        ),
    },
    "trust": {
        "label": "Trust & Guarantees",
        "problem": (
            "81% of shoppers abandon when they can't verify a store's legitimacy. "
            "A missing return policy, phone number, or security badge near the "
            "Add to Cart button hemorrhages cart completions."
        ),
        "revenue_gain": "+$610 per 1k visitors",
        "effort": "2 hours",
        "scope": "All products",
        "steps": [
            'Publish a concrete return policy ("30-day, free returns")',
            "Add a phone number and live chat to header + footer",
            "Place SSL, BBB, and payment badges near Add to Cart",
            "Surface top 3 review snippets under product title",
        ],
        "code": None,
    },
    "socialCommerce": {
        "label": "Social Commerce",
        "problem": (
            "No TikTok Shop integration, no Pinterest Rich Pins, no shoppable "
            "Instagram embed. Social-driven shoppers bounce because there's no "
            "path from the feed to the cart."
        ),
        "revenue_gain": "+$320 per 1k visitors",
        "effort": "3 hours",
        "scope": "All products",
        "steps": [
            "Connect TikTok Shop via the Shopify channel",
            "Enable Pinterest Rich Pins through the Pinterest app",
            "Add an Instagram UGC gallery above the footer",
            "Submit product catalog to Meta Commerce Manager",
        ],
        "code": None,
    },
    "accessibility": {
        "label": "Accessibility",
        "problem": (
            "Color-contrast violations and unlabeled form inputs expose you to "
            "ADA lawsuits and reject conversion at the CSS level — 26% of US "
            "adults have a disability."
        ),
        "revenue_gain": "+$180 per 1k visitors",
        "effort": "90 minutes",
        "scope": "All products",
        "steps": [
            'Fix "Add to Cart" contrast (currently 3.2:1 — needs 4.5:1)',
            "Label all form inputs with <label for> or aria-label",
            "Add visible :focus-visible styles to all interactive elements",
            "Ensure all images have descriptive alt text",
        ],
        "code": None,
    },
}

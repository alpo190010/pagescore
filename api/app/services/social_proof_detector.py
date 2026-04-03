"""Social proof signal detector for Shopify product pages.

Extraction priority (most reliable → least):
  1. Schema.org JSON-LD  — standardised, vendor-agnostic, machine-readable
  2. Meta tags           — og/product rating metadata
  3. Vendor JSON blobs   — window.__YOTPO__, jdgm, stamped embedded data
  4. Data attributes     — data-score, data-rating, data-review-count
  5. Aria-labels         — screen-reader labels with rating text
  6. Vendor CSS widgets  — DOM scraping (original approach, now fallback)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import List, Tuple

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Signals dataclass
# ---------------------------------------------------------------------------


@dataclass
class SocialProofSignals:
    """Structured social proof signals extracted from a product page."""

    review_app: str | None = None
    """Detected vendor name, e.g. ``"judge.me"``, or ``None``."""

    star_rating: float | None = None
    """Average star rating 0.0–5.0, or ``None`` if not found."""

    review_count: int | None = None
    """Number of reviews, or ``None`` if not found."""

    has_photo_reviews: bool = False
    """True when photo containers are present inside review widgets."""

    has_video_reviews: bool = False
    """True when video elements are present inside review widgets."""

    star_rating_above_fold: bool = False
    """True when a star badge appears before the main review widget."""

    has_review_filtering: bool = False
    """True when filter/sort UI is present inside review containers."""


# ---------------------------------------------------------------------------
# Vendor fingerprints — (vendor_name, css_selectors, script_url_patterns)
# ---------------------------------------------------------------------------

_VendorFingerprint = Tuple[str, List[str], List[str]]

_VENDOR_FINGERPRINTS: list[_VendorFingerprint] = [
    (
        "judge.me",
        [".jdgm-widget", ".jdgm-rev", "#judgeme_product_reviews"],
        ["judge.me"],
    ),
    (
        "yotpo",
        [".yotpo", ".yotpo-main-widget"],
        ["staticw2.yotpo.com"],
    ),
    (
        "yotpo-v3",
        [".yotpo-widget-instance", "[data-yotpo-instance-id]"],
        ["cdn-widgetsrepository.yotpo.com"],
    ),
    (
        "loox",
        [".loox-rating", ".loox-reviews-default"],
        ["loox.io"],
    ),
    (
        "stamped.io",
        [".stamped-reviews-widget", ".stamped-summary"],
        ["stamped.io"],
    ),
    (
        "okendo",
        ["[data-oke-widget]", ".okeReviews"],
        ["okendo"],
    ),
    (
        "shopify-spr",
        ["#shopify-product-reviews", ".spr-container"],
        [],
    ),
    (
        "fera.ai",
        [".fera-productReviews", "[data-fera-widget]"],
        ["fera.ai"],
    ),
]

# ---------------------------------------------------------------------------
# Photo / video review selectors per vendor
# ---------------------------------------------------------------------------

_PHOTO_SELECTORS: list[str] = [
    ".jdgm-rev__photos",
    ".yotpo-review-images",
    ".loox-rating img",
    ".loox-reviews-default img",
    ".stamped-reviews-widget img.photo-review",
    ".okeReviews img",
    "[data-oke-widget] img",
    ".fera-productReviews img",
    "[data-fera-widget] img",
    ".spr-container img",
]

_REVIEW_WIDGET_SELECTORS: list[str] = [
    ".jdgm-widget",
    ".jdgm-rev",
    ".yotpo",
    ".yotpo-main-widget",
    ".yotpo-widget-instance",
    ".loox-reviews-default",
    ".stamped-reviews-widget",
    ".okeReviews",
    "[data-oke-widget]",
    ".fera-productReviews",
    "[data-fera-widget]",
    "#shopify-product-reviews",
    ".spr-container",
]

_FILTER_SELECTORS: list[str] = [
    ".jdgm-sort",
    ".yotpo-reviews-filters",
    ".yotpo-nav",
    ".loox-reviews-filter",
    ".stamped-reviews-filter",
    ".okeReviews-filter",
]


# ═══════════════════════════════════════════════════════════════════
# LAYER 1: Schema.org JSON-LD
# ═══════════════════════════════════════════════════════════════════


def _extract_jsonld(soup: BeautifulSoup) -> tuple[float | None, int | None]:
    """Extract star rating and review count from Product JSON-LD.

    Handles both single objects and ``@graph`` arrays. Looks for
    ``aggregateRating`` on any ``Product`` node.

    Returns (star_rating, review_count) — either or both may be None.
    """
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        items = _flatten_jsonld(data)
        for item in items:
            if not isinstance(item, dict):
                continue
            item_type = item.get("@type", "")
            # Handle both "Product" and ["Product", "SomeOtherType"]
            types = item_type if isinstance(item_type, list) else [item_type]
            if "Product" not in types:
                continue

            agg = item.get("aggregateRating")
            if not isinstance(agg, dict):
                continue

            rating = _safe_float(agg.get("ratingValue"))
            count = _safe_int(
                agg.get("reviewCount") or agg.get("ratingCount")
            )
            if rating is not None or count is not None:
                logger.debug(
                    "JSON-LD extracted: rating=%s count=%s", rating, count
                )
                return rating, count

    return None, None


def _flatten_jsonld(data: object) -> list[dict]:
    """Flatten JSON-LD into a list of typed objects.

    Handles plain objects, arrays, and ``@graph`` wrappers.
    """
    if isinstance(data, list):
        result: list[dict] = []
        for item in data:
            result.extend(_flatten_jsonld(item))
        return result
    if isinstance(data, dict):
        graph = data.get("@graph")
        if isinstance(graph, list):
            return _flatten_jsonld(graph)
        return [data]
    return []


# ═══════════════════════════════════════════════════════════════════
# LAYER 2: Meta tags
# ═══════════════════════════════════════════════════════════════════


def _extract_meta_tags(soup: BeautifulSoup) -> tuple[float | None, int | None]:
    """Extract rating and count from <meta> tags.

    Checks ``product:rating:average`` / ``product:rating:count`` (OGP)
    and ``rating`` / ``ratingCount`` name variants.
    """
    rating: float | None = None
    count: int | None = None

    for prop, target in [
        ("product:rating:average", "rating"),
        ("product:rating:value", "rating"),
        ("og:rating", "rating"),
        ("product:rating:count", "count"),
        ("product:review_count", "count"),
    ]:
        tag = soup.find("meta", attrs={"property": prop}) or soup.find(
            "meta", attrs={"name": prop}
        )
        if tag and tag.get("content"):
            if target == "rating" and rating is None:
                rating = _safe_float(tag["content"])
            elif target == "count" and count is None:
                count = _safe_int(tag["content"])

    if rating is not None or count is not None:
        logger.debug("Meta tags extracted: rating=%s count=%s", rating, count)

    return rating, count


# ═══════════════════════════════════════════════════════════════════
# LAYER 3: Vendor JSON blobs in <script> tags
# ═══════════════════════════════════════════════════════════════════

# Patterns: window.jdgm = {...}, __YOTPO_DATA__, StampedData
_VENDOR_JSON_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Judge.me: jdgm.settings or jdgm.productData
    ("judge.me", re.compile(r"jdgm\w*\s*=\s*(\{.+?\});", re.DOTALL)),
    # Yotpo: window.__oReviews or yotpo app key data
    ("yotpo", re.compile(r"__oReviews\s*=\s*(\{.+?\});", re.DOTALL)),
    # Stamped: StampedData or stampedSettings
    ("stamped.io", re.compile(r"Stamped\w+\s*=\s*(\{.+?\});", re.DOTALL)),
]


def _extract_vendor_json(
    soup: BeautifulSoup,
) -> tuple[float | None, int | None]:
    """Try to extract rating/count from vendor-specific embedded JSON."""
    for script in soup.find_all("script"):
        text = script.string or ""
        if len(text) < 20:
            continue

        for _vendor, pattern in _VENDOR_JSON_PATTERNS:
            m = pattern.search(text)
            if not m:
                continue
            try:
                blob = json.loads(m.group(1))
            except (json.JSONDecodeError, TypeError):
                continue

            # Walk common keys
            rating = _safe_float(
                blob.get("ratingValue")
                or blob.get("rating")
                or blob.get("average_score")
                or blob.get("averageRating")
            )
            count = _safe_int(
                blob.get("reviewCount")
                or blob.get("review_count")
                or blob.get("total_reviews")
                or blob.get("totalReviews")
            )
            if rating is not None or count is not None:
                logger.debug(
                    "Vendor JSON (%s) extracted: rating=%s count=%s",
                    _vendor,
                    rating,
                    count,
                )
                return rating, count

    return None, None


# ═══════════════════════════════════════════════════════════════════
# LAYER 4: Data attributes
# ═══════════════════════════════════════════════════════════════════


def _extract_data_attrs_rating(soup: BeautifulSoup) -> float | None:
    """Extract star rating from data-* attributes."""
    for attr in ("data-score", "data-average", "data-rating",
                 "data-loox-aggregate"):
        tag = soup.find(attrs={attr: True})
        if tag:
            val = _safe_float(tag[attr])
            if val is not None and 0.0 <= val <= 5.0:
                return val
    return None


def _extract_data_attrs_count(soup: BeautifulSoup) -> int | None:
    """Extract review count from data-* attributes."""
    for attr in ("data-number-of-reviews", "data-review-count",
                 "data-reviews-count"):
        tag = soup.find(attrs={attr: True})
        if tag:
            val = _safe_int(tag[attr])
            if val is not None:
                return val
    return None


# ═══════════════════════════════════════════════════════════════════
# LAYER 5: Aria-labels
# ═══════════════════════════════════════════════════════════════════


def _extract_aria_rating(soup: BeautifulSoup) -> float | None:
    """Extract star rating from aria-label attributes."""
    for el in soup.find_all(attrs={"aria-label": True}):
        label = el["aria-label"]
        # "4.5 out of 5" or "4.5 out 5" (Yotpo v3 omits "of")
        m = re.search(r"([\d.]+)\s*out\s+(?:of\s+)?5\b", label)
        if m:
            val = _safe_float(m.group(1))
            if val is not None and 0.0 <= val <= 5.0:
                return val
        # "4.5 stars rating"
        m = re.search(r"([\d.]+)\s*stars?\s*rating", label)
        if m:
            val = _safe_float(m.group(1))
            if val is not None and 0.0 <= val <= 5.0:
                return val
    return None


def _extract_aria_count(soup: BeautifulSoup) -> int | None:
    """Extract review count from aria-label attributes."""
    for el in soup.find_all(attrs={"aria-label": True}):
        # "in total 114 reviews" or "of 114 reviews"
        m = re.search(r"(?:total|of)\s+(\d+)\s*review", el["aria-label"])
        if m:
            val = _safe_int(m.group(1))
            if val is not None:
                return val
    return None


# ═══════════════════════════════════════════════════════════════════
# LAYER 6: DOM text heuristics (original fallback)
# ═══════════════════════════════════════════════════════════════════


def _extract_dom_rating(soup: BeautifulSoup) -> float | None:
    """Shopify SPR percentage-based star width trick."""
    spr_el = soup.select_one(".spr-starrating .spr-starratings-top")
    if spr_el and spr_el.get("style"):
        m = re.search(r"width:\s*([\d.]+)%", spr_el["style"])
        if m:
            pct = float(m.group(1))
            return round(pct / 100.0 * 5.0, 1)
    return None


def _extract_dom_count(soup: BeautifulSoup) -> int | None:
    """Extract review count from widget text patterns."""
    # .spr-badge-caption e.g. "42 reviews"
    badge = soup.select_one(".spr-badge-caption")
    if badge:
        m = re.search(r"(\d+)\s*review", badge.get_text())
        if m:
            return int(m.group(1))

    # Parenthesised count inside review widgets e.g. "(114)"
    for sel in _REVIEW_WIDGET_SELECTORS:
        widget = soup.select_one(sel)
        if widget:
            m = re.search(r"\((\d+)\)", widget.get_text())
            if m:
                val = _safe_int(m.group(1))
                if val is not None:
                    return val

    # Generic "N reviews" inside review widgets
    for sel in _REVIEW_WIDGET_SELECTORS:
        widget = soup.select_one(sel)
        if widget:
            m = re.search(r"(\d+)\s*review", widget.get_text())
            if m:
                return int(m.group(1))

    return None


# ═══════════════════════════════════════════════════════════════════
# Cascading extractors — try each layer in priority order
# ═══════════════════════════════════════════════════════════════════


def _extract_star_rating(soup: BeautifulSoup) -> float | None:
    """Extract star rating using cascading priority layers."""
    # Layer 1: JSON-LD (handled in caller to avoid double-parse)
    # Layer 4: Data attributes
    val = _extract_data_attrs_rating(soup)
    if val is not None:
        return val
    # Layer 5: Aria-labels
    val = _extract_aria_rating(soup)
    if val is not None:
        return val
    # Layer 6: DOM heuristics
    return _extract_dom_rating(soup)


def _extract_review_count(soup: BeautifulSoup) -> int | None:
    """Extract review count using cascading priority layers."""
    # Layer 1: JSON-LD (handled in caller to avoid double-parse)
    # Layer 4: Data attributes
    val = _extract_data_attrs_count(soup)
    if val is not None:
        return val
    # Layer 5: Aria-labels
    val = _extract_aria_count(soup)
    if val is not None:
        return val
    # Layer 6: DOM heuristics
    return _extract_dom_count(soup)


# ═══════════════════════════════════════════════════════════════════
# Visual signal helpers (unchanged)
# ═══════════════════════════════════════════════════════════════════


def _detect_vendor(soup: BeautifulSoup) -> str | None:
    """Return the first matching vendor name or ``None``."""
    for name, css_selectors, script_patterns in _VENDOR_FINGERPRINTS:
        for sel in css_selectors:
            if soup.select_one(sel):
                logger.debug("Vendor %s matched via CSS selector %s", name, sel)
                return name
        for pattern in script_patterns:
            for script_tag in soup.find_all("script", src=True):
                if pattern in script_tag["src"]:
                    logger.debug(
                        "Vendor %s matched via script src %s",
                        name,
                        script_tag["src"],
                    )
                    return name
    return None


def _has_photo_reviews(soup: BeautifulSoup) -> bool:
    """Check for photo containers inside review widgets."""
    for sel in _PHOTO_SELECTORS:
        if soup.select_one(sel):
            return True
    for sel in _REVIEW_WIDGET_SELECTORS:
        widget = soup.select_one(sel)
        if widget and widget.find("img"):
            return True
    return False


def _has_video_reviews(soup: BeautifulSoup) -> bool:
    """Check for <video> elements inside review widget containers."""
    for sel in _REVIEW_WIDGET_SELECTORS:
        widget = soup.select_one(sel)
        if widget and widget.find("video"):
            return True
    return False


def _star_rating_above_fold(soup: BeautifulSoup) -> bool:
    """Heuristic: a star badge element appears before the main review widget."""
    badge_selectors = [
        "[data-score]",
        "[data-average]",
        "[data-rating]",
        "[data-loox-aggregate]",
        ".spr-badge",
        ".jdgm-prev-badge",
        ".yotpo-bottomline",
        ".yotpo-sr-bottom-line-summary",
    ]

    first_badge_pos: int | None = None
    first_widget_pos: int | None = None

    all_tags = list(soup.descendants)

    for i, el in enumerate(all_tags):
        if not isinstance(el, Tag):
            continue

        if first_badge_pos is None:
            for sel in badge_selectors:
                if el.select_one(sel) is el or _matches_selector(el, sel):
                    first_badge_pos = i
                    break

        if first_widget_pos is None:
            for sel in _REVIEW_WIDGET_SELECTORS:
                if _matches_selector(el, sel):
                    first_widget_pos = i
                    break

        if first_badge_pos is not None and first_widget_pos is not None:
            break

    if first_badge_pos is not None and first_widget_pos is not None:
        return first_badge_pos < first_widget_pos

    return first_badge_pos is not None


def _matches_selector(tag: Tag, selector: str) -> bool:
    """Check if a single Tag matches a CSS selector."""
    try:
        matched = tag.parent.select(selector) if tag.parent else []
        return tag in matched
    except Exception:
        return False


def _has_review_filtering(soup: BeautifulSoup) -> bool:
    """Check for filter/sort UI inside review containers."""
    for sel in _FILTER_SELECTORS:
        if soup.select_one(sel):
            return True
    for sel in _REVIEW_WIDGET_SELECTORS:
        widget = soup.select_one(sel)
        if widget and widget.find("select"):
            return True
    return False


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════


def _safe_float(val: object) -> float | None:
    """Convert to float or return None. Never raises."""
    if val is None:
        return None
    try:
        f = float(val)
        return f if 0.0 <= f <= 5.0 else None
    except (ValueError, TypeError):
        return None


def _safe_int(val: object) -> int | None:
    """Convert to non-negative int or return None. Never raises."""
    if val is None:
        return None
    try:
        i = int(float(val))
        return i if i >= 0 else None
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_social_proof(html: str) -> SocialProofSignals:
    """Detect social proof signals from rendered product page HTML.

    Uses a cascading extraction strategy:
      1. Schema.org JSON-LD (most reliable)
      2. Meta tags
      3. Vendor-embedded JSON blobs
      4. Data attributes
      5. Aria-labels
      6. DOM text heuristics

    Each layer fills in only what previous layers missed, so the most
    reliable source always wins.
    """
    if not html:
        return SocialProofSignals()

    soup = BeautifulSoup(html, "html.parser")

    # --- Vendor detection (CSS / script fingerprinting) ---
    vendor = _detect_vendor(soup)

    # --- Rating + count: cascading extraction ---
    star_rating: float | None = None
    review_count: int | None = None

    # Layer 1: JSON-LD
    jl_rating, jl_count = _extract_jsonld(soup)
    if jl_rating is not None:
        star_rating = jl_rating
    if jl_count is not None:
        review_count = jl_count

    # Layer 2: Meta tags (fill gaps only)
    if star_rating is None or review_count is None:
        mt_rating, mt_count = _extract_meta_tags(soup)
        if star_rating is None and mt_rating is not None:
            star_rating = mt_rating
        if review_count is None and mt_count is not None:
            review_count = mt_count

    # Layer 3: Vendor JSON blobs (fill gaps only)
    if star_rating is None or review_count is None:
        vj_rating, vj_count = _extract_vendor_json(soup)
        if star_rating is None and vj_rating is not None:
            star_rating = vj_rating
        if review_count is None and vj_count is not None:
            review_count = vj_count

    # Layers 4-6: Data attrs → Aria → DOM (fill gaps only)
    if star_rating is None:
        star_rating = _extract_star_rating(soup)
    if review_count is None:
        review_count = _extract_review_count(soup)

    # --- Visual signals (CSS-based, unchanged) ---
    photo = _has_photo_reviews(soup)
    video = _has_video_reviews(soup)
    above_fold = _star_rating_above_fold(soup)
    filtering = _has_review_filtering(soup)

    signals = SocialProofSignals(
        review_app=vendor,
        star_rating=star_rating,
        review_count=review_count,
        has_photo_reviews=photo,
        has_video_reviews=video,
        star_rating_above_fold=above_fold,
        has_review_filtering=filtering,
    )

    logger.info(
        "Social proof detected: vendor=%s stars=%s count=%s photos=%s video=%s above_fold=%s filtering=%s",
        vendor,
        star_rating,
        review_count,
        photo,
        video,
        above_fold,
        filtering,
    )

    return signals

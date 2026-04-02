"""Social proof signal detector for Shopify product pages.

Parses rendered HTML to detect review-app vendors (Judge.me, Yotpo,
Loox, Stamped.io, Okendo, Shopify SPR, Fera.ai) and extract structured
signals: star rating, review count, photo/video reviews, above-fold
badge placement, and review filtering UI.
"""

from __future__ import annotations

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


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _detect_vendor(soup: BeautifulSoup) -> str | None:
    """Return the first matching vendor name or ``None``."""
    for name, css_selectors, script_patterns in _VENDOR_FINGERPRINTS:
        # Check CSS selectors
        for sel in css_selectors:
            if soup.select_one(sel):
                logger.debug("Vendor %s matched via CSS selector %s", name, sel)
                return name

        # Check script src patterns
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


def _extract_star_rating(soup: BeautifulSoup) -> float | None:
    """Extract average star rating from data attributes or text patterns."""
    # 1. data-score attribute (Judge.me, Loox)
    for attr in ("data-score", "data-average", "data-rating"):
        tag = soup.find(attrs={attr: True})
        if tag:
            try:
                val = float(tag[attr])
                if 0.0 <= val <= 5.0:
                    return val
            except (ValueError, TypeError):
                continue

    # 2. data-loox-aggregate (Loox variant)
    tag = soup.find(attrs={"data-loox-aggregate": True})
    if tag:
        try:
            val = float(tag["data-loox-aggregate"])
            if 0.0 <= val <= 5.0:
                return val
        except (ValueError, TypeError):
            pass

    # 3. aria-label star patterns  e.g. "4.5 out of 5 stars"
    for el in soup.find_all(attrs={"aria-label": True}):
        match = re.search(r"([\d.]+)\s*(?:out of\s*5|stars)", el["aria-label"])
        if match:
            try:
                val = float(match.group(1))
                if 0.0 <= val <= 5.0:
                    return val
            except (ValueError, TypeError):
                continue

    # 4. Shopify SPR starrating content (percentage-based width trick)
    spr_el = soup.select_one(".spr-starrating .spr-starratings-top")
    if spr_el and spr_el.get("style"):
        match = re.search(r"width:\s*([\d.]+)%", spr_el["style"])
        if match:
            pct = float(match.group(1))
            return round(pct / 100.0 * 5.0, 1)

    return None


def _extract_review_count(soup: BeautifulSoup) -> int | None:
    """Extract review count from data attributes or text patterns."""
    # 1. data-number-of-reviews attribute
    tag = soup.find(attrs={"data-number-of-reviews": True})
    if tag:
        try:
            return int(tag["data-number-of-reviews"])
        except (ValueError, TypeError):
            pass

    # 2. data-review-count attribute
    tag = soup.find(attrs={"data-review-count": True})
    if tag:
        try:
            return int(tag["data-review-count"])
        except (ValueError, TypeError):
            pass

    # 3. .spr-badge-caption text  e.g. "42 reviews"
    badge = soup.select_one(".spr-badge-caption")
    if badge:
        match = re.search(r"(\d+)\s*review", badge.get_text())
        if match:
            return int(match.group(1))

    # 4. Generic "N reviews" text within review widgets
    for sel in _REVIEW_WIDGET_SELECTORS:
        widget = soup.select_one(sel)
        if widget:
            match = re.search(r"(\d+)\s*review", widget.get_text())
            if match:
                return int(match.group(1))

    return None


def _has_photo_reviews(soup: BeautifulSoup) -> bool:
    """Check for photo containers inside review widgets."""
    for sel in _PHOTO_SELECTORS:
        if soup.select_one(sel):
            return True

    # Fallback: any <img> inside a known review widget
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
    """Heuristic: a star badge element appears before the main review widget.

    Identifies "above-fold" placement by checking if a compact badge
    (e.g. ``data-score``, ``aria-label`` with stars) precedes the
    first full review widget in DOM order.
    """
    # Collect all elements in DOM order
    badge_selectors = [
        "[data-score]",
        "[data-average]",
        "[data-rating]",
        "[data-loox-aggregate]",
        ".spr-badge",
        ".jdgm-prev-badge",
        ".yotpo-bottomline",
    ]

    first_badge_pos: int | None = None
    first_widget_pos: int | None = None

    all_tags = list(soup.descendants)

    for i, el in enumerate(all_tags):
        if not isinstance(el, Tag):
            continue

        # Check badge
        if first_badge_pos is None:
            for sel in badge_selectors:
                if el.select_one(sel) is el or _matches_selector(el, sel):
                    first_badge_pos = i
                    break

        # Check full widget
        if first_widget_pos is None:
            for sel in _REVIEW_WIDGET_SELECTORS:
                if _matches_selector(el, sel):
                    first_widget_pos = i
                    break

        if first_badge_pos is not None and first_widget_pos is not None:
            break

    if first_badge_pos is not None and first_widget_pos is not None:
        return first_badge_pos < first_widget_pos

    # If there's a badge but no main widget, the badge is above-fold
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

    # Fallback: <select> with sort-like options inside review widgets
    for sel in _REVIEW_WIDGET_SELECTORS:
        widget = soup.select_one(sel)
        if widget and widget.find("select"):
            return True

    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_social_proof(html: str) -> SocialProofSignals:
    """Detect social proof signals from rendered product page HTML.

    Parses *html* with BeautifulSoup, identifies the review-app vendor
    (if any), and extracts structured signals: star rating, review count,
    photo/video reviews, above-fold star badge, and filtering UI.

    Args:
        html: Fully rendered DOM HTML (e.g. from :func:`render_page`).

    Returns:
        A populated :class:`SocialProofSignals` instance.  Fields default
        to ``None`` / ``False`` when no signal is found — never raises on
        empty or malformed input.
    """
    if not html:
        return SocialProofSignals()

    soup = BeautifulSoup(html, "html.parser")

    vendor = _detect_vendor(soup)
    star_rating = _extract_star_rating(soup)
    review_count = _extract_review_count(soup)
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
        "Social proof detected: vendor=%s stars=%s count=%s photos=%s",
        vendor,
        star_rating,
        review_count,
        photo,
    )

    return signals

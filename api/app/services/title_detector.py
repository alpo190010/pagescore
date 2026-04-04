"""Title & SEO signal extraction from rendered product page HTML.

Detects H1 tag presence, meta title, brand name, keyword stuffing,
ALL CAPS abuse, promotional text, and title quality signals using
cascading DOM parsing with Shopify-specific selectors.
"""

import json
import logging
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TitleSignals dataclass
# ---------------------------------------------------------------------------

@dataclass
class TitleSignals:
    """Extracted title & SEO signals for a product page."""

    h1_text: str | None = None
    """Text content of the first H1 tag, or None if absent."""

    meta_title: str | None = None
    """Content of <title> tag or <meta property='og:title'>."""

    brand_name: str | None = None
    """Detected brand name from JSON-LD, og:site_name, or Shopify product JSON."""

    h1_count: int = 0
    """Total number of H1 tags on the page."""

    h1_length: int = 0
    """Character count of H1 text (0 if missing)."""

    meta_title_length: int = 0
    """Character count of meta title (0 if missing)."""

    has_h1: bool = False
    """At least one H1 tag is present and non-empty."""

    has_single_h1: bool = False
    """Exactly one H1 tag on the page."""

    has_brand_in_title: bool = False
    """Brand name appears in H1 text (case-insensitive)."""

    has_keyword_stuffing: bool = False
    """Title contains repeated words (3+), pipe-separated lists, or excessive commas."""

    is_all_caps: bool = False
    """H1 is ALL CAPS (excluding short acronyms <= 4 chars)."""

    has_promotional_text: bool = False
    """Title contains promotional language (Sale!, Free Shipping!, etc.)."""

    h1_meta_differ: bool = False
    """H1 and meta title are meaningfully different."""

    has_specifics: bool = False
    """Title contains product-specific terms (color, size, material, model)."""


# ---------------------------------------------------------------------------
# Known acronyms allowed in ALL CAPS
# ---------------------------------------------------------------------------

_COMMON_ACRONYMS = frozenset({
    "LED", "USB", "TV", "AC", "DC", "HD", "UK", "US", "EU",
    "UV", "GPS", "LCD", "DIY", "SPF", "CBD", "XL", "XXL", "XS",
    "BPA", "FDA", "ISO", "OLED", "HDMI", "RGB", "NFC", "SSD",
    "HDD", "RAM", "CPU", "GPU",
})


# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

_PIPE_RE = re.compile(r"\|")
_EXCESSIVE_COMMAS_RE = re.compile(r"(,.*){4,}")

_PROMO_PATTERNS = [
    re.compile(r"\bsale\s*!", re.IGNORECASE),
    re.compile(r"\bfree\s+shipping\s*!?", re.IGNORECASE),
    re.compile(r"\bbuy\s+now\s*!?", re.IGNORECASE),
    re.compile(r"\bbest\s+price\s*!?", re.IGNORECASE),
    re.compile(r"\blimited\s+time\s*!?", re.IGNORECASE),
    re.compile(r"\d+\s*%\s*off\b", re.IGNORECASE),
    re.compile(r"\bhot\s+deal\b", re.IGNORECASE),
    re.compile(r"\bclearance\b", re.IGNORECASE),
    re.compile(r"!{2,}"),
]

_SPECIFICS_RE = re.compile(
    r"\b("
    r"(?:small|medium|large|xl|xxl|xs|[0-9]+\s*(?:ml|oz|g|kg|lb|cm|mm|in|ft|pc|pack|ct))"
    r"|(?:black|white|red|blue|green|navy|grey|gray|pink|gold|silver|beige|brown|purple|orange|cream|yellow)"
    r"|(?:leather|cotton|silk|linen|wool|bamboo|titanium|steel|stainless|ceramic|wood|plastic|nylon|polyester|suede|velvet|denim|canvas)"
    r"|(?:v\d|mk\d|gen\s*\d|pro|max|plus|mini|lite|ultra)"
    r"|(?:\d+\s*(?:piece|set|pair|count))"
    r")\b",
    re.IGNORECASE,
)

_ALPHA_ONLY_RE = re.compile(r"[^a-zA-Z]")


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

def _extract_h1(soup: BeautifulSoup) -> tuple[str | None, int]:
    """Extract H1 text and count. Tries Shopify selectors first."""
    h1_tags = soup.find_all("h1")
    count = len(h1_tags)
    if not h1_tags:
        return None, 0

    # Priority: Shopify Dawn → Shopify older → first H1
    h1_el = (
        soup.select_one("h1.product__title")
        or soup.select_one("h1.product-single__title")
        or h1_tags[0]
    )
    raw = h1_el.get_text(strip=True)
    return (raw if raw else None), count


def _extract_meta_title(soup: BeautifulSoup) -> str | None:
    """Extract meta title from <title> or og:title."""
    title_tag = soup.find("title")
    if title_tag and title_tag.string and title_tag.string.strip():
        return title_tag.string.strip()

    og = soup.find("meta", property="og:title")
    if og and og.get("content", "").strip():
        return og["content"].strip()

    return None


def _flatten_jsonld(data) -> list[dict]:
    """Flatten JSON-LD data (handles @graph arrays and single objects)."""
    if isinstance(data, list):
        items = []
        for item in data:
            items.extend(_flatten_jsonld(item))
        return items
    if isinstance(data, dict):
        graph = data.get("@graph")
        if isinstance(graph, list):
            items = []
            for item in graph:
                items.extend(_flatten_jsonld(item))
            return items
        return [data]
    return []


def _has_product_type(item: dict) -> bool:
    """Check if a JSON-LD item is a Product."""
    t = item.get("@type", "")
    if isinstance(t, list):
        return "Product" in t
    return t == "Product"


def _extract_brand(soup: BeautifulSoup) -> str | None:
    """Detect brand name via cascading fallbacks."""

    # 1. JSON-LD Product schema: brand.name
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for item in _flatten_jsonld(data):
            if not _has_product_type(item):
                continue
            brand = item.get("brand")
            if isinstance(brand, dict):
                name = brand.get("name", "").strip()
                if name:
                    return name
            elif isinstance(brand, str) and brand.strip():
                return brand.strip()

    # 2. og:site_name
    og_site = soup.find("meta", property="og:site_name")
    if og_site and og_site.get("content", "").strip():
        return og_site["content"].strip()

    # 3. Shopify product JSON vendor
    product_json = soup.find("script", attrs={"type": "application/json", "data-product-json": True})
    if product_json:
        try:
            pdata = json.loads(product_json.string or "")
            vendor = pdata.get("vendor", "").strip()
            if vendor:
                return vendor
        except (json.JSONDecodeError, TypeError):
            pass

    return None


def _detect_keyword_stuffing(text: str) -> bool:
    """Detect keyword stuffing via three heuristics."""
    if not text:
        return False

    # Heuristic 1: Pipe-separated keyword lists (3+ segments)
    if len(_PIPE_RE.split(text)) >= 3:
        return True

    # Heuristic 2: Excessive comma-separated terms (4+ commas)
    if _EXCESSIVE_COMMAS_RE.search(text):
        return True

    # Heuristic 3: Same word repeated 3+ times
    words = re.findall(r"[a-zA-Z]+", text.lower())
    counts: dict[str, int] = {}
    for w in words:
        if len(w) < 3:
            continue
        counts[w] = counts.get(w, 0) + 1
    for count in counts.values():
        if count >= 3:
            return True

    return False


def _is_all_caps(text: str) -> bool:
    """Check if title is ALL CAPS, excluding known acronyms."""
    if not text:
        return False

    words = text.split()
    alpha_words = [w for w in words if any(c.isalpha() for c in w)]

    if len(alpha_words) < 2:
        return False

    caps_count = 0
    total = 0

    for word in alpha_words:
        clean = _ALPHA_ONLY_RE.sub("", word)
        if not clean:
            continue
        total += 1
        if clean.isupper():
            if clean in _COMMON_ACRONYMS:
                continue
            caps_count += 1

    if total == 0:
        return False

    return (caps_count / total) > 0.7


def _detect_promotional_text(text: str) -> bool:
    """Detect promotional language in title."""
    if not text:
        return False
    for pattern in _PROMO_PATTERNS:
        if pattern.search(text):
            return True
    return False


def _titles_meaningfully_differ(h1: str | None, meta: str | None) -> bool:
    """Check if H1 and meta title are meaningfully different."""
    if not h1 or not meta:
        return False

    h1_norm = re.sub(r"\s+", " ", h1.lower().strip())
    meta_norm = re.sub(r"\s+", " ", meta.lower().strip())

    # Strip common " - Brand" or " | Brand" suffixes from meta title
    meta_norm = re.sub(r"\s*[-–—|]\s*[^-–—|]+$", "", meta_norm).strip()

    return h1_norm != meta_norm


def _has_specifics(text: str) -> bool:
    """Check if title contains product-specific terms."""
    if not text:
        return False
    return bool(_SPECIFICS_RE.search(text))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_title(html: str) -> TitleSignals:
    """Extract title & SEO signals from rendered HTML."""
    soup = BeautifulSoup(html, "html.parser")
    sig = TitleSignals()

    # H1
    h1_text, h1_count = _extract_h1(soup)
    sig.h1_text = h1_text
    sig.h1_count = h1_count
    sig.has_h1 = h1_text is not None
    sig.has_single_h1 = h1_count == 1
    sig.h1_length = len(h1_text) if h1_text else 0

    # Meta title
    sig.meta_title = _extract_meta_title(soup)
    sig.meta_title_length = len(sig.meta_title) if sig.meta_title else 0

    # Brand
    sig.brand_name = _extract_brand(soup)
    if sig.brand_name and sig.h1_text:
        sig.has_brand_in_title = sig.brand_name.lower() in sig.h1_text.lower()

    # Quality flags (run on H1 text)
    sig.has_keyword_stuffing = _detect_keyword_stuffing(sig.h1_text or "")
    sig.is_all_caps = _is_all_caps(sig.h1_text or "")
    sig.has_promotional_text = _detect_promotional_text(sig.h1_text or "")

    # Derived
    sig.h1_meta_differ = _titles_meaningfully_differ(sig.h1_text, sig.meta_title)
    sig.has_specifics = _has_specifics(sig.h1_text or "")

    logger.debug(
        "title signals: has_h1=%s h1_count=%d h1_length=%d meta_len=%d brand=%s",
        sig.has_h1, sig.h1_count, sig.h1_length, sig.meta_title_length, sig.brand_name,
    )

    return sig

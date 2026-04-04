"""Product images and media signal detector for Shopify product pages.

Detects product image count (de-duplicated), video presence, 360-degree/spin
viewers, zoom/lightbox capability, lifestyle imagery, CDN hosting, modern image
formats (WebP/AVIF), high-resolution sources, and alt text quality.

Detection follows the same BeautifulSoup DOM inspection approach used by
:pymod:`pricing_detector` and :pymod:`social_proof_detector`.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse, urlencode, urlunparse

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signals dataclass
# ---------------------------------------------------------------------------


@dataclass
class ImageSignals:
    """Product image and media signals extracted from a product page.

    9 fields total:
      * 1 image count (de-duplicated)
      * 4 media capability bools (video, 360, zoom, lifestyle)
      * 2 optimisation bools (CDN, modern format)
      * 1 resolution bool (high-res)
      * 1 quality float (alt text score)
    """

    image_count: int = 0
    """De-duplicated product image count."""

    has_video: bool = False
    """Product video detected on page (native ``<video>``, YouTube/Vimeo
    iframe, or ``<model-viewer>`` element)."""

    has_360_view: bool = False
    """360-degree / spin viewer detected (``<model-viewer>``, spin classes,
    or ``data-spin`` attribute)."""

    has_zoom: bool = False
    """Zoom or magnify capability detected (Dawn modal opener, PhotoSwipe,
    Drift, EasyZoom, or ``data-zoom`` / ``cursor: zoom-in``)."""

    has_lifestyle_images: bool = False
    """Lifestyle / in-context product images detected via alt text or
    class name heuristics."""

    cdn_hosted: bool = False
    """Product images served from a CDN (Shopify CDN, Cloudinary, imgix,
    CloudFront)."""

    has_modern_format: bool = False
    """At least one image served in WebP or AVIF format."""

    has_high_res: bool = False
    """At least one image source with width >= 1000px (CDN param, srcset,
    or ``data-widths`` attribute)."""

    alt_text_score: float = 0.0
    """Composite alt text quality score across product images (0.0-1.0)."""


# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

_CDN_SIZING_PARAMS = {"width", "height", "crop", "v"}

_CDN_SHOPIFY_RE = re.compile(r"cdn\.shopify\.com/s/files/|/cdn/shop/files/", re.IGNORECASE)
_CDN_ANY_RE = re.compile(
    r"cdn\.shopify\.com|/cdn/shop/|cloudinary\.com|imgix\.net|cloudfront\.net",
    re.IGNORECASE,
)

_MODERN_FORMAT_EXT_RE = re.compile(r"\.(webp|avif)(\?|$)", re.IGNORECASE)
_MODERN_FORMAT_PARAM_RE = re.compile(r"format=(webp|avif)", re.IGNORECASE)

_SRCSET_HIGH_RES_RE = re.compile(r"(\d{4,})w")
_CDN_WIDTH_PARAM_RE = re.compile(r"width=(\d+)")

_FILENAME_PATTERN_RE = re.compile(
    r"^(IMG|DSC|DSCN|Photo|photo|image|img|screen|Screen|PXL)[-_]?\d"
)
_GENERIC_ALT_RE = re.compile(
    r"^(product|image|photo|picture)$", re.IGNORECASE
)

_LIFESTYLE_ALT_RE = re.compile(
    r"lifestyle|model\s+wearing|in\s+use|styled|outfit|room|kitchen|living"
    r"|worn\s+by|on\s+model|in\s+context",
    re.IGNORECASE,
)
_LIFESTYLE_CLASS_RE = re.compile(
    r"lifestyle|context|styled|model", re.IGNORECASE
)

_ICON_FILTER_RE = re.compile(r"logo|icon|nav|footer|header", re.IGNORECASE)

_SPIN_CLASS_RE = re.compile(r"360|spin|three-sixty|threesixty", re.IGNORECASE)
_SPIN_SCRIPT_RE = re.compile(r"SpinViewer|ThreeSixty", re.IGNORECASE)

_VIDEO_HOST_RE = re.compile(r"youtube\.com|youtu\.be|vimeo\.com", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_image_url(url: str) -> str:
    """Strip CDN sizing params for de-duplication.

    ``'/cdn/shop/files/photo.jpg?v=123&width=1946'``
    becomes ``'/cdn/shop/files/photo.jpg'``.
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    filtered = {k: v for k, v in params.items() if k.lower() not in _CDN_SIZING_PARAMS}
    new_query = urlencode(filtered, doseq=True) if filtered else ""
    return urlunparse(parsed._replace(query=new_query))


def _is_small_icon(img: Tag) -> bool:
    """Return True if the image is likely a small icon (< 50px)."""
    for attr in ("width", "height"):
        val = img.get(attr, "")
        if val:
            try:
                if int(str(val).replace("px", "")) < 50:
                    return True
            except (ValueError, TypeError):
                pass
    style = img.get("style", "")
    if style:
        for dim in ("width", "height"):
            match = re.search(rf"{dim}\s*:\s*(\d+)\s*px", style)
            if match and int(match.group(1)) < 50:
                return True
    return False


def _is_nav_or_logo(img: Tag) -> bool:
    """Return True if the image is likely navigation, logo, or footer chrome."""
    src = img.get("src", "") or img.get("data-src", "") or ""
    classes = " ".join(img.get("class", []))
    return bool(_ICON_FILTER_RE.search(src) or _ICON_FILTER_RE.search(classes))


def _get_image_src(img: Tag) -> str:
    """Return the best available src attribute for an img tag."""
    return img.get("src") or img.get("data-src") or img.get("data-srcset") or ""


def _score_alt_texts(product_images: list[Tag]) -> float:
    """Score alt text quality across product images. Returns 0.0-1.0.

    Per-image scoring (0-1 each):
      +0.2 if alt present and non-empty
      +0.2 if 10-125 characters
      +0.2 if NOT a filename pattern (IMG_1234, DSC0001, etc.)
      +0.2 if NOT generic ("product", "image", etc.)
      +0.2 if NOT keyword-stuffed (>4 commas or >20 words)

    Global: -0.1 per pair of duplicate alt texts.
    Clamp to 0.0-1.0. Return average.
    """
    if not product_images:
        return 0.0

    scores: list[float] = []
    alt_texts: list[str] = []

    for img in product_images:
        alt = (img.get("alt") or "").strip()
        img_score = 0.0

        # +0.2 present and non-empty
        if alt:
            img_score += 0.2
            alt_texts.append(alt.lower())
        else:
            scores.append(0.0)
            continue

        # +0.2 reasonable length (10-125 chars)
        if 10 <= len(alt) <= 125:
            img_score += 0.2

        # +0.2 not a filename pattern
        if not _FILENAME_PATTERN_RE.match(alt):
            img_score += 0.2

        # +0.2 not generic
        if not _GENERIC_ALT_RE.match(alt):
            img_score += 0.2

        # +0.2 not keyword-stuffed
        comma_count = alt.count(",")
        word_count = len(alt.split())
        if comma_count <= 4 and word_count <= 20:
            img_score += 0.2

        scores.append(img_score)

    if not scores:
        return 0.0

    avg = sum(scores) / len(scores)

    # Global penalty: -0.1 per pair of duplicate alt texts
    if alt_texts:
        seen: dict[str, int] = {}
        for text in alt_texts:
            seen[text] = seen.get(text, 0) + 1
        duplicate_pairs = sum(count // 2 for count in seen.values() if count > 1)
        avg -= 0.1 * duplicate_pairs

    return max(0.0, min(1.0, round(avg, 2)))


# ---------------------------------------------------------------------------
# Detection layers
# ---------------------------------------------------------------------------


def _collect_jsonld_images(soup: BeautifulSoup) -> list[str]:
    """Extract product image URLs from JSON-LD Product.image."""
    urls: list[str] = []
    for script in soup.find_all("script", type="application/ld+json"):
        text = script.string or ""
        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("@type") != "Product":
                continue
            images = item.get("image", [])
            if isinstance(images, str):
                images = [images]
            if isinstance(images, list):
                for img_url in images:
                    if isinstance(img_url, str) and img_url:
                        urls.append(img_url)
    return urls


def _collect_shopify_cdn_images(soup: BeautifulSoup) -> list[str]:
    """Collect image URLs from Shopify CDN img and source elements."""
    urls: list[str] = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if _CDN_SHOPIFY_RE.search(src):
            urls.append(src)
    for source in soup.find_all("source"):
        srcset = source.get("srcset", "")
        if _CDN_SHOPIFY_RE.search(srcset):
            # Extract first URL from srcset
            first_url = srcset.split(",")[0].strip().split(" ")[0]
            if first_url:
                urls.append(first_url)
    return urls


def _collect_dawn_theme_images(soup: BeautifulSoup) -> list[str]:
    """Collect images from Dawn theme slider-component galleries."""
    urls: list[str] = []
    for slider in soup.find_all("slider-component"):
        for container in slider.find_all(class_="product-media-container"):
            if container.get("data-media-id"):
                for img in container.find_all("img"):
                    src = _get_image_src(img)
                    if src:
                        urls.append(src)
    return urls


def _collect_generic_gallery_images(soup: BeautifulSoup) -> list[str]:
    """Collect images from common gallery patterns and slider libraries."""
    urls: list[str] = []
    gallery_selectors = [
        {"class_": "product-gallery"},
        {"class_": "product-images"},
        {"class_": "product-photos"},
        {"attrs": {"data-product-gallery": True}},
        # Slider libraries
        {"class_": "swiper-slide"},
        {"class_": "slick-slide"},
        {"class_": "flickity-slider"},
    ]
    for selector in gallery_selectors:
        for container in soup.find_all(**selector):
            for img in container.find_all("img"):
                src = _get_image_src(img)
                if src:
                    urls.append(src)
    return urls


def _collect_fallback_images(soup: BeautifulSoup) -> list[Tag]:
    """Collect all img tags, filtering out icons, logos, and nav images."""
    product_images: list[Tag] = []
    for img in soup.find_all("img"):
        if _is_small_icon(img) or _is_nav_or_logo(img):
            continue
        product_images.append(img)
    return product_images


def _detect_video(soup: BeautifulSoup) -> bool:
    """Detect product video on the page."""
    # Dawn theme media type classes
    if soup.find(class_="media-type-video") or soup.find(class_="media-type-external_video"):
        return True
    # <video> inside product media containers
    for container_cls in ("product-media-container", "product-gallery", "product-images"):
        for container in soup.find_all(class_=container_cls):
            if container.find("video"):
                return True
    # YouTube / Vimeo iframes
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src", "")
        if _VIDEO_HOST_RE.search(src):
            return True
    # model-viewer counts as video content
    if soup.find("model-viewer"):
        return True
    return False


def _detect_360_view(soup: BeautifulSoup) -> bool:
    """Detect 360-degree / spin viewer on the page."""
    # <model-viewer> custom element
    if soup.find("model-viewer"):
        return True
    # Classes containing 360, spin, three-sixty, threesixty
    for el in soup.find_all(class_=True):
        classes = " ".join(el.get("class", []))
        if _SPIN_CLASS_RE.search(classes):
            return True
    # data-spin attribute
    if soup.find(attrs={"data-spin": True}):
        return True
    # Scripts or elements matching SpinViewer, ThreeSixty
    for script in soup.find_all("script"):
        text = script.string or ""
        if _SPIN_SCRIPT_RE.search(text):
            return True
    return False


def _detect_zoom(soup: BeautifulSoup) -> bool:
    """Detect zoom / magnify / lightbox capability."""
    # Dawn theme modal opener
    if soup.find(class_="product__modal-opener"):
        return True
    # Known zoom library classes
    zoom_classes = (
        "image-magnify-lightbox", "drift-zoom", "easyzoom", "pswp",
    )
    for cls in zoom_classes:
        if soup.find(class_=cls):
            return True
    # Data attributes for zoom/lightbox
    zoom_attrs = ("data-zoom", "data-pswp", "data-lightbox")
    for attr in zoom_attrs:
        if soup.find(attrs={attr: True}):
            return True
    # Inline style: cursor: zoom-in
    for el in soup.find_all(style=True):
        style = el.get("style", "")
        if "zoom-in" in style.lower():
            return True
    return False


def _detect_lifestyle_images(product_img_tags: list[Tag], soup: BeautifulSoup) -> bool:
    """Detect lifestyle / in-context images via alt text and class heuristics."""
    for img in product_img_tags:
        alt = img.get("alt", "")
        if alt and _LIFESTYLE_ALT_RE.search(alt):
            return True
        classes = " ".join(img.get("class", []))
        if classes and _LIFESTYLE_CLASS_RE.search(classes):
            return True
    # Also check parent containers for lifestyle class names
    for el in soup.find_all(class_=True):
        classes = " ".join(el.get("class", []))
        if _LIFESTYLE_CLASS_RE.search(classes):
            if el.find("img"):
                return True
    return False


def _detect_cdn_hosted(all_urls: list[str]) -> bool:
    """Check if any product image is hosted on a CDN."""
    for url in all_urls:
        if _CDN_ANY_RE.search(url):
            return True
    return False


def _detect_modern_format(all_urls: list[str]) -> bool:
    """Check if any product image uses WebP or AVIF format."""
    for url in all_urls:
        if _MODERN_FORMAT_EXT_RE.search(url):
            return True
        if _MODERN_FORMAT_PARAM_RE.search(url):
            return True
    return False


def _detect_high_res(soup: BeautifulSoup) -> bool:
    """Check if any product image has width >= 1000px.

    Scans the DOM directly (img src, srcset, data-widths, source srcset)
    to avoid losing sizing information after URL de-duplication.
    """
    # CDN width param in img src/data-src
    for img in soup.find_all("img"):
        for attr in ("src", "data-src"):
            url = img.get(attr, "")
            if url:
                m = _CDN_WIDTH_PARAM_RE.search(url)
                if m and int(m.group(1)) >= 1000:
                    return True
        # srcset containing 1000w or higher
        srcset = img.get("srcset", "")
        for m in _SRCSET_HIGH_RES_RE.finditer(srcset):
            if int(m.group(1)) >= 1000:
                return True
    # <source> srcset
    for source in soup.find_all("source"):
        srcset = source.get("srcset", "")
        for m in _SRCSET_HIGH_RES_RE.finditer(srcset):
            if int(m.group(1)) >= 1000:
                return True
    # data-widths attribute
    for img in soup.find_all(attrs={"data-widths": True}):
        widths_str = img.get("data-widths", "")
        try:
            widths = json.loads(widths_str)
            if isinstance(widths, list) and any(int(w) >= 1000 for w in widths):
                return True
        except (ValueError, TypeError):
            pass
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_images(html: str) -> ImageSignals:
    """Detect product image and media signals from rendered product page HTML.

    Scans for product images across JSON-LD, Shopify CDN, Dawn theme galleries,
    generic slider libraries, and fallback DOM inspection. De-duplicates URLs,
    then detects video, 360 views, zoom, lifestyle imagery, CDN hosting, modern
    formats, high resolution, and alt text quality.
    """
    signals = ImageSignals()

    if not html:
        return signals

    soup = BeautifulSoup(html, "html.parser")

    # --- Collect image URLs from all layers ---
    all_urls: list[str] = []
    all_urls.extend(_collect_jsonld_images(soup))
    all_urls.extend(_collect_shopify_cdn_images(soup))
    all_urls.extend(_collect_dawn_theme_images(soup))
    all_urls.extend(_collect_generic_gallery_images(soup))

    # Fallback: collect all non-icon img tags
    fallback_img_tags = _collect_fallback_images(soup)
    for img in fallback_img_tags:
        src = _get_image_src(img)
        if src:
            all_urls.append(src)

    # --- De-duplicate by normalized URL ---
    seen_normalized: set[str] = set()
    unique_urls: list[str] = []
    for url in all_urls:
        norm = _normalize_image_url(url)
        if norm and norm not in seen_normalized:
            seen_normalized.add(norm)
            unique_urls.append(url)

    signals.image_count = len(unique_urls)

    # --- Video detection ---
    signals.has_video = _detect_video(soup)

    # --- 360-degree view detection ---
    signals.has_360_view = _detect_360_view(soup)

    # --- Zoom / lightbox detection ---
    signals.has_zoom = _detect_zoom(soup)

    # --- Lifestyle image detection ---
    signals.has_lifestyle_images = _detect_lifestyle_images(fallback_img_tags, soup)

    # --- CDN hosting ---
    signals.cdn_hosted = _detect_cdn_hosted(unique_urls)

    # --- Modern format (WebP / AVIF) ---
    signals.has_modern_format = _detect_modern_format(unique_urls)

    # --- High resolution ---
    signals.has_high_res = _detect_high_res(soup)

    # --- Alt text quality ---
    signals.alt_text_score = _score_alt_texts(fallback_img_tags)

    logger.info(
        "Images detected: count=%d video=%s 360=%s "
        "zoom=%s lifestyle=%s cdn=%s "
        "modern_fmt=%s high_res=%s alt_score=%.2f",
        signals.image_count,
        signals.has_video,
        signals.has_360_view,
        signals.has_zoom,
        signals.has_lifestyle_images,
        signals.cdn_hosted,
        signals.has_modern_format,
        signals.has_high_res,
        signals.alt_text_score,
    )

    return signals

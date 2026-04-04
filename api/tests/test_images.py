"""Unit tests for images_detector and images_rubric.

Covers image count detection (JSON-LD, Dawn theme, Shopify CDN, generic
galleries, de-duplication, thumbnail exclusion), video presence, zoom/lightbox,
360-degree views, alt text quality scoring, format and CDN detection,
deterministic 0-100 scoring, and research-cited tip selection.
"""

from dataclasses import fields, is_dataclass

import pytest

from app.services.images_detector import ImageSignals, detect_images
from app.services.images_rubric import get_images_tips, score_images


# ---------------------------------------------------------------------------
# HTML fixture helpers
# ---------------------------------------------------------------------------


def _empty_html() -> str:
    """Baseline page with no product images."""
    return ""


def _jsonld_single_image_html() -> str:
    """JSON-LD Product schema with a single image URL string."""
    return (
        "<html><body>"
        '<script type="application/ld+json">'
        '{"@type": "Product", "name": "Widget",'
        ' "image": "https://cdn.shopify.com/s/files/1/product-front.jpg"}'
        "</script>"
        "</body></html>"
    )


def _jsonld_multiple_images_html() -> str:
    """JSON-LD Product schema with an array of image URLs."""
    return (
        "<html><body>"
        '<script type="application/ld+json">'
        '{"@type": "Product", "name": "Widget",'
        ' "image": ['
        '   "https://cdn.shopify.com/s/files/1/front.jpg",'
        '   "https://cdn.shopify.com/s/files/1/back.jpg",'
        '   "https://cdn.shopify.com/s/files/1/side.jpg"'
        " ]}"
        "</script>"
        "</body></html>"
    )


def _dawn_slider_html() -> str:
    """Dawn theme slider-component with product-media-container divs."""
    return (
        "<html><body>"
        "<slider-component>"
        '  <div class="product-media-container" data-media-id="1">'
        '    <img src="https://cdn.shopify.com/s/files/1/photo1.jpg?v=1&width=800" alt="Front">'
        "  </div>"
        '  <div class="product-media-container" data-media-id="2">'
        '    <img src="https://cdn.shopify.com/s/files/1/photo2.jpg?v=1&width=800" alt="Back">'
        "  </div>"
        '  <div class="product-media-container" data-media-id="3">'
        '    <img src="https://cdn.shopify.com/s/files/1/photo3.jpg?v=1&width=800" alt="Side">'
        "  </div>"
        "</slider-component>"
        "</body></html>"
    )


def _shopify_cdn_images_html() -> str:
    """Standalone Shopify CDN img elements outside any gallery container."""
    return (
        "<html><body>"
        '<img src="https://cdn.shopify.com/s/files/1/photo_a.jpg?v=123&width=1946" alt="Photo A">'
        '<img src="https://cdn.shopify.com/s/files/1/photo_b.jpg?v=456&width=1946" alt="Photo B">'
        "</body></html>"
    )


def _duplicate_urls_html() -> str:
    """Same base image URL repeated with different width params."""
    return (
        "<html><body>"
        '<img src="https://cdn.shopify.com/s/files/1/same.jpg?width=400" alt="Small">'
        '<img src="https://cdn.shopify.com/s/files/1/same.jpg?width=800" alt="Medium">'
        '<img src="https://cdn.shopify.com/s/files/1/same.jpg?width=1600" alt="Large">'
        "</body></html>"
    )


def _thumbnails_html() -> str:
    """Small icon-sized images that should be filtered out."""
    return (
        "<html><body>"
        '<img width="30" height="30" src="/icons/icon.png" alt="Icon">'
        '<img width="20" height="20" src="/icons/badge.png" alt="Badge">'
        "</body></html>"
    )


def _generic_gallery_html() -> str:
    """Generic product-gallery container with img tags."""
    return (
        "<html><body>"
        '<div class="product-gallery">'
        '  <img src="/images/gallery1.jpg" alt="Gallery shot 1">'
        '  <img src="/images/gallery2.jpg" alt="Gallery shot 2">'
        '  <img src="/images/gallery3.jpg" alt="Gallery shot 3">'
        '  <img src="/images/gallery4.jpg" alt="Gallery shot 4">'
        "</div>"
        "</body></html>"
    )


def _dawn_video_class_html() -> str:
    """Dawn theme media-type-video class."""
    return (
        "<html><body>"
        '<div class="media-type-video">'
        "  <video src=\"/video/product.mp4\"></video>"
        "</div>"
        "</body></html>"
    )


def _external_video_class_html() -> str:
    """Dawn theme media-type-external_video class."""
    return (
        "<html><body>"
        '<div class="media-type-external_video">'
        '  <iframe src="https://www.youtube.com/embed/abc"></iframe>'
        "</div>"
        "</body></html>"
    )


def _video_in_product_container_html() -> str:
    """Native video element inside a product-media-container."""
    return (
        "<html><body>"
        '<div class="product-media-container">'
        '  <video src="/video/demo.mp4"></video>'
        "</div>"
        "</body></html>"
    )


def _youtube_iframe_html() -> str:
    """YouTube embed iframe."""
    return (
        "<html><body>"
        '<iframe src="https://www.youtube.com/embed/abc123" '
        'width="560" height="315"></iframe>'
        "</body></html>"
    )


def _zoom_modal_opener_html() -> str:
    """Dawn theme product__modal-opener for zoom."""
    return (
        "<html><body>"
        '<div class="product__modal-opener">'
        '  <img src="/product.jpg" alt="Product">'
        "</div>"
        "</body></html>"
    )


def _zoom_magnify_html() -> str:
    """image-magnify-lightbox class for zoom."""
    return (
        "<html><body>"
        '<div class="image-magnify-lightbox">'
        '  <img src="/product.jpg" alt="Product">'
        "</div>"
        "</body></html>"
    )


def _zoom_photoswipe_html() -> str:
    """PhotoSwipe pswp class for zoom."""
    return (
        "<html><body>"
        '<div class="pswp">'
        '  <img src="/product.jpg" alt="Product">'
        "</div>"
        "</body></html>"
    )


def _zoom_drift_html() -> str:
    """Drift zoom class for zoom."""
    return (
        "<html><body>"
        '<div class="drift-zoom">'
        '  <img src="/product.jpg" alt="Product">'
        "</div>"
        "</body></html>"
    )


def _zoom_data_attr_html() -> str:
    """data-zoom attribute for zoom."""
    return (
        "<html><body>"
        '<img data-zoom="true" src="/product.jpg" alt="Product">'
        "</body></html>"
    )


def _model_viewer_html() -> str:
    """model-viewer custom element for 360-degree view."""
    return (
        "<html><body>"
        '<model-viewer src="/model.glb" alt="3D Product" '
        'auto-rotate camera-controls></model-viewer>'
        "</body></html>"
    )


def _spin_class_html() -> str:
    """Spin class for 360-degree viewer."""
    return (
        "<html><body>"
        '<div class="product-spin-viewer">'
        '  <img src="/spin-frame-1.jpg" alt="Spin">'
        "</div>"
        "</body></html>"
    )


def _data_spin_attr_html() -> str:
    """data-spin attribute for 360 detection."""
    return (
        "<html><body>"
        '<div data-spin="true">'
        '  <img src="/spin.jpg" alt="Spin">'
        "</div>"
        "</body></html>"
    )


def _good_alt_text_html() -> str:
    """Images with descriptive, unique 10-125 char alt texts."""
    return (
        "<html><body>"
        '<img src="/a.jpg" alt="Handmade ceramic mug in ocean blue, 12oz capacity">'
        '<img src="/b.jpg" alt="Ocean blue mug from the side showing the comfortable handle">'
        '<img src="/c.jpg" alt="Top-down view of the ceramic mug with a latte inside">'
        "</body></html>"
    )


def _no_alt_text_html() -> str:
    """Images with no alt attribute at all."""
    return (
        "<html><body>"
        '<img src="/a.jpg">'
        '<img src="/b.jpg">'
        '<img src="/c.jpg">'
        "</body></html>"
    )


def _filename_alt_html() -> str:
    """Images with filename-pattern alt text."""
    return (
        "<html><body>"
        '<img src="/a.jpg" alt="IMG_1234.jpg">'
        '<img src="/b.jpg" alt="DSC0001.jpg">'
        "</body></html>"
    )


def _generic_alt_html() -> str:
    """Images with single generic-word alt text."""
    return (
        "<html><body>"
        '<img src="/a.jpg" alt="product">'
        '<img src="/b.jpg" alt="image">'
        "</body></html>"
    )


def _keyword_stuffed_alt_html() -> str:
    """Images with keyword-stuffed alt text (>4 commas)."""
    return (
        "<html><body>"
        '<img src="/a.jpg" alt="mug, blue, ceramic, handmade, coffee, gift, modern">'
        '<img src="/b.jpg" alt="cup, pottery, artisan, kitchen, drinkware, tea">'
        "</body></html>"
    )


def _duplicate_alt_html() -> str:
    """Multiple images sharing the exact same alt text."""
    return (
        "<html><body>"
        '<img src="/a.jpg" alt="Blue ceramic mug product photo">'
        '<img src="/b.jpg" alt="Blue ceramic mug product photo">'
        '<img src="/c.jpg" alt="Blue ceramic mug product photo">'
        '<img src="/d.jpg" alt="Blue ceramic mug product photo">'
        "</body></html>"
    )


def _webp_image_html() -> str:
    """Image with .webp extension."""
    return (
        "<html><body>"
        '<img src="https://cdn.shopify.com/s/files/1/product.webp" alt="Product">'
        "</body></html>"
    )


def _avif_image_html() -> str:
    """Image with .avif extension."""
    return (
        "<html><body>"
        '<img src="https://cdn.shopify.com/s/files/1/product.avif" alt="Product">'
        "</body></html>"
    )


def _high_res_width_param_html() -> str:
    """Image URL with width=1946 CDN parameter."""
    return (
        "<html><body>"
        '<img src="https://cdn.shopify.com/s/files/1/photo.jpg?v=1&width=1946" alt="Product">'
        "</body></html>"
    )


def _high_res_srcset_html() -> str:
    """Image with srcset containing 1200w descriptor."""
    return (
        "<html><body>"
        '<img src="/photo.jpg" '
        'srcset="/photo-400.jpg 400w, /photo-800.jpg 800w, /photo-1200.jpg 1200w" '
        'alt="Product">'
        "</body></html>"
    )


def _full_dawn_html() -> str:
    """Realistic Dawn product page HTML with all image signals."""
    return (
        "<html><body>"
        # JSON-LD schema
        '<script type="application/ld+json">'
        '{"@type": "Product", "name": "Premium Widget",'
        ' "image": ['
        '   "https://cdn.shopify.com/s/files/1/front.webp",'
        '   "https://cdn.shopify.com/s/files/1/back.webp",'
        '   "https://cdn.shopify.com/s/files/1/side.webp"'
        " ]}"
        "</script>"
        # Dawn slider with images
        "<slider-component>"
        '  <div class="product-media-container" data-media-id="1">'
        '    <img src="https://cdn.shopify.com/s/files/1/front.webp?v=1&width=1946" '
        '         alt="Premium Widget front view showing brushed metal finish">'
        "  </div>"
        '  <div class="product-media-container" data-media-id="2">'
        '    <img src="https://cdn.shopify.com/s/files/1/back.webp?v=1&width=1946" '
        '         alt="Premium Widget back view with serial number plate">'
        "  </div>"
        '  <div class="product-media-container" data-media-id="3">'
        '    <img src="https://cdn.shopify.com/s/files/1/side.webp?v=1&width=1946" '
        '         alt="Premium Widget side profile showing slim design">'
        "  </div>"
        '  <div class="product-media-container" data-media-id="4">'
        '    <img src="https://cdn.shopify.com/s/files/1/detail.webp?v=1&width=1946" '
        '         alt="Close-up of the premium control knob and LED indicator">'
        "  </div>"
        '  <div class="product-media-container" data-media-id="5">'
        '    <img src="https://cdn.shopify.com/s/files/1/lifestyle.webp?v=1&width=1946" '
        '         alt="Premium Widget in use on a modern desk setup" class="lifestyle">'
        "  </div>"
        '  <div class="product-media-container" data-media-id="6">'
        '    <img src="https://cdn.shopify.com/s/files/1/scale.webp?v=1&width=1946" '
        '         alt="Premium Widget next to a standard pencil for scale">'
        "  </div>"
        '  <div class="product-media-container" data-media-id="7">'
        '    <img src="https://cdn.shopify.com/s/files/1/box.webp?v=1&width=1946" '
        '         alt="Premium Widget unboxing with included accessories">'
        "  </div>"
        '  <div class="product-media-container" data-media-id="8">'
        '    <img src="https://cdn.shopify.com/s/files/1/warranty.webp?v=1&width=1946" '
        '         alt="Premium Widget warranty card and documentation">'
        "  </div>"
        "</slider-component>"
        # Video
        '<div class="media-type-video">'
        '  <video src="/video/product-demo.mp4"></video>'
        "</div>"
        # Zoom modal opener
        '<div class="product__modal-opener">'
        "  <button>Zoom</button>"
        "</div>"
        # 360 viewer
        '<model-viewer src="/model.glb" auto-rotate camera-controls></model-viewer>'
        "</body></html>"
    )


def _minimal_html() -> str:
    """Minimal page with just a few plain img tags."""
    return (
        "<html><body>"
        '<img src="/photo1.jpg" alt="Product front view for the blue widget">'
        '<img src="/photo2.jpg" alt="Product back view for the blue widget">'
        "</body></html>"
    )


# ---------------------------------------------------------------------------
# Helper to build signals directly for rubric tests
# ---------------------------------------------------------------------------


def _all_maxed_signals() -> ImageSignals:
    """Signals with maximum scoring values (all features present)."""
    return ImageSignals(
        image_count=8,
        has_video=True,
        has_360_view=True,
        has_zoom=True,
        has_lifestyle_images=True,
        cdn_hosted=True,
        has_modern_format=True,
        has_high_res=True,
        alt_text_score=1.0,
    )


def _no_signals() -> ImageSignals:
    """Default signals (worst case)."""
    return ImageSignals()


# ---------------------------------------------------------------------------
# 1. TestImageCountDetection
# ---------------------------------------------------------------------------


class TestImageCountDetection:
    """Product image count extraction and de-duplication."""

    def test_empty_html_zero_images(self):
        """Empty string yields 0 images."""
        signals = detect_images("")
        assert signals.image_count == 0

    def test_jsonld_single_image(self):
        """JSON-LD Product.image as a single string URL yields 1 image."""
        signals = detect_images(_jsonld_single_image_html())
        assert signals.image_count >= 1

    def test_jsonld_multiple_images(self):
        """JSON-LD Product.image as an array yields correct count."""
        signals = detect_images(_jsonld_multiple_images_html())
        assert signals.image_count >= 3

    def test_dawn_slider_images(self):
        """Dawn slider-component with product-media-container[data-media-id] divs."""
        signals = detect_images(_dawn_slider_html())
        assert signals.image_count >= 3

    def test_shopify_cdn_images(self):
        """Shopify CDN img elements detected as product images."""
        signals = detect_images(_shopify_cdn_images_html())
        assert signals.image_count >= 2

    def test_duplicate_urls_deduplicated(self):
        """Same base URL with different ?width= params counted once."""
        signals = detect_images(_duplicate_urls_html())
        assert signals.image_count == 1

    def test_thumbnails_excluded(self):
        """Small icon-sized images (< 50px) are filtered out."""
        signals = detect_images(_thumbnails_html())
        assert signals.image_count == 0

    def test_generic_gallery(self):
        """Images inside a .product-gallery container detected."""
        signals = detect_images(_generic_gallery_html())
        assert signals.image_count >= 4

    def test_non_product_jsonld_ignored(self):
        """JSON-LD with @type != 'Product' does not contribute images."""
        html = (
            "<html><body>"
            '<script type="application/ld+json">'
            '{"@type": "Organization", "image": "https://example.com/logo.png"}'
            "</script>"
            "</body></html>"
        )
        signals = detect_images(html)
        # Organization image should not count via JSON-LD Product path
        assert signals.image_count <= 1


# ---------------------------------------------------------------------------
# 2. TestVideoDetection
# ---------------------------------------------------------------------------


class TestVideoDetection:
    """Product video detection across various patterns."""

    def test_dawn_video_class(self):
        """Dawn theme media-type-video class triggers video detection."""
        signals = detect_images(_dawn_video_class_html())
        assert signals.has_video is True

    def test_external_video_class(self):
        """Dawn theme media-type-external_video class triggers video detection."""
        signals = detect_images(_external_video_class_html())
        assert signals.has_video is True

    def test_video_element_in_product(self):
        """Native <video> inside product-media-container triggers detection."""
        signals = detect_images(_video_in_product_container_html())
        assert signals.has_video is True

    def test_youtube_iframe(self):
        """YouTube embed iframe triggers video detection."""
        signals = detect_images(_youtube_iframe_html())
        assert signals.has_video is True

    def test_vimeo_iframe(self):
        """Vimeo embed iframe triggers video detection."""
        html = (
            "<html><body>"
            '<iframe src="https://player.vimeo.com/video/12345"'
            ' width="640" height="360"></iframe>'
            "</body></html>"
        )
        signals = detect_images(html)
        assert signals.has_video is True

    def test_model_viewer_counts_as_video(self):
        """model-viewer element is counted as video content."""
        signals = detect_images(_model_viewer_html())
        assert signals.has_video is True

    def test_no_video_empty_html(self):
        """Empty HTML returns has_video=False."""
        signals = detect_images("")
        assert signals.has_video is False


# ---------------------------------------------------------------------------
# 3. TestZoomDetection
# ---------------------------------------------------------------------------


class TestZoomDetection:
    """Zoom / lightbox / magnify capability detection."""

    def test_dawn_modal_opener(self):
        """Dawn product__modal-opener class triggers zoom detection."""
        signals = detect_images(_zoom_modal_opener_html())
        assert signals.has_zoom is True

    def test_magnify_lightbox(self):
        """image-magnify-lightbox class triggers zoom detection."""
        signals = detect_images(_zoom_magnify_html())
        assert signals.has_zoom is True

    def test_photoswipe(self):
        """PhotoSwipe pswp class triggers zoom detection."""
        signals = detect_images(_zoom_photoswipe_html())
        assert signals.has_zoom is True

    def test_drift_zoom(self):
        """drift-zoom class triggers zoom detection."""
        signals = detect_images(_zoom_drift_html())
        assert signals.has_zoom is True

    def test_data_zoom_attr(self):
        """data-zoom attribute triggers zoom detection."""
        signals = detect_images(_zoom_data_attr_html())
        assert signals.has_zoom is True

    def test_cursor_zoom_in_style(self):
        """Inline cursor: zoom-in style triggers zoom detection."""
        html = (
            "<html><body>"
            '<img src="/photo.jpg" style="cursor: zoom-in;" alt="Product">'
            "</body></html>"
        )
        signals = detect_images(html)
        assert signals.has_zoom is True

    def test_no_zoom_empty_html(self):
        """Empty HTML returns has_zoom=False."""
        signals = detect_images("")
        assert signals.has_zoom is False


# ---------------------------------------------------------------------------
# 4. Test360Detection
# ---------------------------------------------------------------------------


class Test360Detection:
    """360-degree / spin viewer detection."""

    def test_model_viewer(self):
        """<model-viewer> custom element triggers 360 detection."""
        signals = detect_images(_model_viewer_html())
        assert signals.has_360_view is True

    def test_spin_class(self):
        """Class containing 'spin' triggers 360 detection."""
        signals = detect_images(_spin_class_html())
        assert signals.has_360_view is True

    def test_data_spin_attr(self):
        """data-spin attribute triggers 360 detection."""
        signals = detect_images(_data_spin_attr_html())
        assert signals.has_360_view is True

    def test_threesixty_class(self):
        """Class containing '360' triggers detection."""
        html = (
            "<html><body>"
            '<div class="product-360-viewer">'
            '  <img src="/frame.jpg" alt="Frame">'
            "</div>"
            "</body></html>"
        )
        signals = detect_images(html)
        assert signals.has_360_view is True

    def test_no_360_empty_html(self):
        """Empty HTML returns has_360_view=False."""
        signals = detect_images("")
        assert signals.has_360_view is False


# ---------------------------------------------------------------------------
# 5. TestAltTextScoring
# ---------------------------------------------------------------------------


class TestAltTextScoring:
    """Alt text quality scoring (0.0-1.0)."""

    def test_all_good_alt(self):
        """Descriptive, unique 10-125 char alt texts score near 1.0."""
        signals = detect_images(_good_alt_text_html())
        assert signals.alt_text_score >= 0.8

    def test_no_alt_text(self):
        """Images with no alt attribute score 0.0."""
        signals = detect_images(_no_alt_text_html())
        assert signals.alt_text_score == 0.0

    def test_filename_pattern(self):
        """Filename-pattern alt (IMG_1234.jpg) is penalized.

        Each image gets +0.2 (present) + 0.2 (length) + 0.0 (filename) +
        0.2 (not generic) + 0.2 (not stuffed) = 0.8 max per image.
        Score is strictly less than a fully-descriptive alt (1.0).
        """
        signals = detect_images(_filename_alt_html())
        assert signals.alt_text_score <= 0.8
        assert signals.alt_text_score < 1.0

    def test_generic_alt(self):
        """Generic single-word alt (product, image) is penalized."""
        signals = detect_images(_generic_alt_html())
        # Missing non-generic bonus (+0.2) and length bonus
        assert signals.alt_text_score < 0.8

    def test_keyword_stuffed(self):
        """Alt with >4 commas is penalized for keyword stuffing.

        Each image gets +0.2 (present) + 0.2 (length) + 0.2 (not filename)
        + 0.2 (not generic) + 0.0 (stuffed) = 0.8 max per image.
        Score is strictly less than a fully-descriptive alt (1.0).
        """
        signals = detect_images(_keyword_stuffed_alt_html())
        assert signals.alt_text_score <= 0.8
        assert signals.alt_text_score < 1.0

    def test_duplicate_alt_penalty(self):
        """Same alt on multiple images reduces score via global penalty.

        4 identical alts -> 2 duplicate pairs -> -0.2 global penalty.
        Per-image: 0.2 + 0.2 + 0.2 + 0.2 + 0.2 = 1.0 each, avg = 1.0.
        After penalty: 1.0 - 0.2 = 0.8. Still lower than unique-alt score.
        """
        signals = detect_images(_duplicate_alt_html())
        # The duplicate penalty brings the score down from the maximum
        assert signals.alt_text_score <= 0.8
        # Verify the penalty is actually applied (would be 1.0 without it)
        unique_signals = detect_images(_good_alt_text_html())
        assert signals.alt_text_score <= unique_signals.alt_text_score

    def test_empty_html_alt_score_zero(self):
        """Empty HTML returns alt_text_score of 0.0."""
        signals = detect_images("")
        assert signals.alt_text_score == 0.0


# ---------------------------------------------------------------------------
# 6. TestFormatAndCdn
# ---------------------------------------------------------------------------


class TestFormatAndCdn:
    """Modern format (WebP/AVIF) and CDN detection."""

    def test_webp_detected(self):
        """Image with .webp extension sets has_modern_format."""
        signals = detect_images(_webp_image_html())
        assert signals.has_modern_format is True

    def test_avif_detected(self):
        """Image with .avif extension sets has_modern_format."""
        signals = detect_images(_avif_image_html())
        assert signals.has_modern_format is True

    def test_shopify_cdn_detected(self):
        """cdn.shopify.com URL sets cdn_hosted."""
        signals = detect_images(_shopify_cdn_images_html())
        assert signals.cdn_hosted is True

    def test_high_res_width_param(self):
        """width=1946 in URL sets has_high_res."""
        signals = detect_images(_high_res_width_param_html())
        assert signals.has_high_res is True

    def test_high_res_srcset(self):
        """srcset with 1200w descriptor sets has_high_res."""
        signals = detect_images(_high_res_srcset_html())
        assert signals.has_high_res is True

    def test_no_modern_format_for_jpeg(self):
        """Plain .jpg does not set has_modern_format."""
        html = (
            "<html><body>"
            '<img src="/photo.jpg" alt="Product">'
            "</body></html>"
        )
        signals = detect_images(html)
        assert signals.has_modern_format is False

    def test_format_param_detected(self):
        """CDN format=webp query parameter sets has_modern_format."""
        html = (
            "<html><body>"
            '<img src="https://cdn.shopify.com/s/files/1/photo.jpg?format=webp" alt="Product">'
            "</body></html>"
        )
        signals = detect_images(html)
        assert signals.has_modern_format is True


# ---------------------------------------------------------------------------
# 7. TestScoring
# ---------------------------------------------------------------------------


class TestScoring:
    """Deterministic 0-100 scoring from ImageSignals."""

    def test_no_signals_score_0(self):
        """Default ImageSignals() yields score 0."""
        assert score_images(ImageSignals()) == 0

    def test_full_signals_score_100(self):
        """All maxed signals yield score 100.

        35 (images) + 15 (video) + 15 (alt) + 10 (zoom) + 5 (modern) +
        5 (high-res) + 5 (lifestyle) + 5 (360) + 5 (CDN) = 100.
        """
        assert score_images(_all_maxed_signals()) == 100

    def test_8_plus_images_35_pts(self):
        """image_count=8 alone yields 35 pts."""
        s = ImageSignals(image_count=8)
        assert score_images(s) == 35

    def test_5_to_7_images_25_pts(self):
        """image_count=5 alone yields 25 pts."""
        s = ImageSignals(image_count=5)
        assert score_images(s) == 25

    def test_3_to_4_images_10_pts(self):
        """image_count=3 alone yields 10 pts."""
        s = ImageSignals(image_count=3)
        assert score_images(s) == 10

    def test_1_to_2_images_0_pts(self):
        """image_count=2 alone yields 0 pts (below tier threshold)."""
        s = ImageSignals(image_count=2)
        assert score_images(s) == 0

    def test_video_only_15_pts(self):
        """has_video=True alone yields 15 pts."""
        s = ImageSignals(has_video=True)
        assert score_images(s) == 15

    def test_zoom_only_10_pts(self):
        """has_zoom=True alone yields 10 pts."""
        s = ImageSignals(has_zoom=True)
        assert score_images(s) == 10

    def test_alt_text_full_15_pts(self):
        """alt_text_score=1.0 alone yields 15 pts."""
        s = ImageSignals(alt_text_score=1.0)
        assert score_images(s) == 15

    def test_alt_text_half_8_pts(self):
        """alt_text_score=0.5 yields round(0.5 * 15) = 8 pts."""
        s = ImageSignals(alt_text_score=0.5)
        assert score_images(s) == 8

    def test_modern_format_only_5_pts(self):
        """has_modern_format=True alone yields 5 pts."""
        s = ImageSignals(has_modern_format=True)
        assert score_images(s) == 5

    def test_score_clamped(self):
        """Score is always within 0-100 range."""
        assert 0 <= score_images(ImageSignals()) <= 100
        assert 0 <= score_images(_all_maxed_signals()) <= 100

    def test_deterministic(self):
        """Same signals always produce the same score."""
        s = ImageSignals(image_count=5, has_video=True, has_zoom=True)
        score_a = score_images(s)
        score_b = score_images(s)
        assert score_a == score_b

    def test_additive_scoring(self):
        """Video (15) + zoom (10) + 5 images (25) = 50."""
        s = ImageSignals(image_count=5, has_video=True, has_zoom=True)
        assert score_images(s) == 50


# ---------------------------------------------------------------------------
# 8. TestTipSelection
# ---------------------------------------------------------------------------


class TestTipSelection:
    """Tip ordering, max count, citations, and content."""

    def test_no_signals_returns_3_tips(self):
        """Default signals (score 0) returns 3 tips."""
        tips = get_images_tips(ImageSignals())
        assert len(tips) == 3

    def test_full_signals_congratulatory(self):
        """All maxed signals (score 100 >= 85) returns congratulatory tip."""
        tips = get_images_tips(_all_maxed_signals())
        assert len(tips) >= 1
        assert any("Excellent" in t for t in tips)

    def test_max_3_tips(self):
        """Never more than 3 tips returned."""
        tips = get_images_tips(ImageSignals())
        assert len(tips) <= 3

    def test_low_images_tip_first(self):
        """image_count < 3 tip appears first (highest priority)."""
        tips = get_images_tips(ImageSignals(image_count=1))
        assert "image" in tips[0].lower() or "5" in tips[0] or "8" in tips[0]

    def test_tips_not_empty_strings(self):
        """All tips are non-empty strings with meaningful content."""
        tips = get_images_tips(ImageSignals())
        assert all(isinstance(t, str) and len(t) > 10 for t in tips)

    def test_tip_cites_research(self):
        """At least some tips cite research sources."""
        tips = get_images_tips(ImageSignals())
        research_keywords = ("Salsify", "Baymard", "Gumlet", "Xictron", "CXL")
        has_citation = any(
            any(kw in t for kw in research_keywords) for t in tips
        )
        assert has_citation

    def test_no_video_tip_present(self):
        """When has_video=False and image_count < 3, video tip appears."""
        tips = get_images_tips(ImageSignals(image_count=1))
        video_tips = [t for t in tips if "video" in t.lower()]
        assert len(video_tips) >= 1

    def test_no_zoom_tip_present(self):
        """When has_zoom=False, zoom tip appears in suggestions.

        Give enough signals to satisfy the higher-priority tips (images,
        video, alt text) so the zoom tip surfaces within the top 3.
        """
        s = ImageSignals(
            image_count=8,
            has_video=True,
            alt_text_score=0.8,
        )
        tips = get_images_tips(s)
        zoom_tips = [t for t in tips if "zoom" in t.lower() or "lightbox" in t.lower()]
        assert len(zoom_tips) >= 1


# ---------------------------------------------------------------------------
# 9. TestEndToEnd
# ---------------------------------------------------------------------------


class TestEndToEnd:
    """Full pipeline: HTML -> detect -> score -> tips."""

    def test_full_dawn_html_pipeline(self):
        """Realistic Dawn product page HTML through full pipeline."""
        signals = detect_images(_full_dawn_html())
        assert signals.image_count >= 8
        assert signals.has_video is True
        assert signals.has_zoom is True
        assert signals.has_360_view is True
        assert signals.has_modern_format is True
        assert signals.cdn_hosted is True
        assert signals.has_high_res is True

        score = score_images(signals)
        assert score >= 85

        tips = get_images_tips(signals)
        assert isinstance(tips, list)
        assert any("Excellent" in t for t in tips)

    def test_empty_html_pipeline(self):
        """Empty string through full pipeline yields score 0."""
        signals = detect_images("")
        assert score_images(signals) == 0
        tips = get_images_tips(signals)
        assert isinstance(tips, list)
        assert len(tips) <= 3

    def test_minimal_html_pipeline(self):
        """Minimal page with 2 img tags through full pipeline."""
        signals = detect_images(_minimal_html())
        assert signals.image_count == 2
        assert signals.has_video is False
        assert signals.has_zoom is False

        score = score_images(signals)
        # 2 images = 0 pts for count tier, but alt_text_score may add a few
        assert 0 <= score <= 100

        tips = get_images_tips(signals)
        assert isinstance(tips, list)
        assert len(tips) >= 1
        # First tip should be about adding more images
        assert "image" in tips[0].lower() or "5" in tips[0]

    def test_pipeline_types_consistent(self):
        """detect -> score -> tips produce consistent typed results."""
        signals = detect_images(_full_dawn_html())
        score = score_images(signals)
        tips = get_images_tips(signals)
        assert isinstance(score, int)
        assert 0 <= score <= 100
        assert isinstance(tips, list)
        assert all(isinstance(t, str) for t in tips)


# ---------------------------------------------------------------------------
# 10. TestDataclassStructure
# ---------------------------------------------------------------------------


class TestDataclassStructure:
    """ImageSignals dataclass invariants."""

    def test_is_dataclass(self):
        """ImageSignals is a proper dataclass."""
        assert is_dataclass(ImageSignals)

    def test_field_count(self):
        """9 fields: 1 count + 4 media bools + 2 optimisation + 1 res + 1 quality."""
        assert len(fields(ImageSignals)) == 9

    def test_default_values(self):
        """All defaults are correct: int 0, bools False, float 0.0."""
        s = ImageSignals()
        assert s.image_count == 0
        assert s.has_video is False
        assert s.has_360_view is False
        assert s.has_zoom is False
        assert s.has_lifestyle_images is False
        assert s.cdn_hosted is False
        assert s.has_modern_format is False
        assert s.has_high_res is False
        assert s.alt_text_score == 0.0

    def test_instantiation_with_no_args(self):
        """ImageSignals can be instantiated with no arguments."""
        s = ImageSignals()
        assert s.image_count == 0
        assert s.alt_text_score == 0.0

"""Description quality signal detector for Shopify product pages.

Extracts NLP-based quality metrics from product descriptions: word count,
Flesch-Kincaid readability, benefit/feature language ratio, emotional
language density, and HTML formatting richness.

Detection follows the same BeautifulSoup DOM inspection approach used by
:pymod:`pricing_detector` and :pymod:`title_detector`.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signals dataclass
# ---------------------------------------------------------------------------


@dataclass
class DescriptionSignals:
    """Description quality signals extracted from a product page.

    13 fields total:
      • 2 content fields (found flag + word count)
      • 3 readability fields (FK grade, avg sentence length, sentence count)
      • 4 persuasion language fields (benefit ratio, counts, emotional density)
      • 4 HTML formatting fields (tag variety, headings, bullets, emphasis)
    """

    # --- Content (2) ----------------------------------------------------
    description_found: bool = False
    """Whether any description content was extracted from the page."""

    word_count: int = 0
    """Total word count of the description text (HTML tags stripped)."""

    # --- Readability (3) ------------------------------------------------
    flesch_kincaid_grade: float = 0.0
    """Flesch-Kincaid grade level (e.g. 6.0 = 6th grade reading level).
    Target: 6–8 for maximum comprehension and conversion."""

    avg_sentence_length: float = 0.0
    """Average number of words per sentence. Target: 10–20 words."""

    sentence_count: int = 0
    """Total number of sentences detected in the description."""

    # --- Persuasion language (4) ----------------------------------------
    benefit_ratio: float = 0.0
    """Ratio of benefit-language words to total benefit+feature words (0.0–1.0).
    Target: 0.4–0.6. Zero when no benefit/feature words detected."""

    benefit_word_count: int = 0
    """Count of benefit-oriented words (e.g. "you", "enjoy", "experience")."""

    feature_word_count: int = 0
    """Count of feature-oriented words (e.g. "made from", "includes", "specifications")."""

    emotional_density: float = 0.0
    """Fraction of total words that are emotional/persuasive (0.0–1.0).
    Target: 0.03–0.08."""

    # --- HTML formatting (4) --------------------------------------------
    html_tag_variety: int = 0
    """Count of distinct formatting tag types found within the description
    (h2, h3, ul, ol, strong, em, table, img, etc.). Range 0–13+."""

    has_headings: bool = False
    """At least one ``<h2>``, ``<h3>``, or ``<h4>`` found in the description."""

    has_bullet_lists: bool = False
    """At least one ``<ul>`` or ``<ol>`` found in the description."""

    has_emphasis: bool = False
    """At least one ``<strong>``, ``<em>``, ``<b>``, or ``<i>`` found."""


# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")
_VOWEL_GROUP_RE = re.compile(r"[aeiouy]+")
_WORD_RE = re.compile(r"[a-z]+(?:[-\'][a-z]+)*", re.IGNORECASE)

# HTML tags that count toward formatting richness
_FORMATTING_TAGS: frozenset[str] = frozenset({
    "h2", "h3", "h4", "ul", "ol", "li", "strong", "em", "b", "i",
    "table", "img", "blockquote",
})

_HEADING_TAGS: frozenset[str] = frozenset({"h2", "h3", "h4"})
_LIST_TAGS: frozenset[str] = frozenset({"ul", "ol"})
_EMPHASIS_TAGS: frozenset[str] = frozenset({"strong", "em", "b", "i"})

# --- Benefit-oriented words (customer-focused, experiential) ---
_BENEFIT_WORDS: frozenset[str] = frozenset({
    "you", "your", "yours", "enjoy", "experience", "love", "feel",
    "transform", "discover", "imagine", "achieve", "perfect",
    "effortless", "comfortable", "luxurious", "smooth", "refreshing",
    "revitalize", "empower", "enhance", "elevate", "radiant", "vibrant",
    "confidence", "freedom", "relief", "bliss", "indulge", "delight",
    "thrive",
})

# --- Feature-oriented words (specification-focused, technical) ---
_FEATURE_WORDS: frozenset[str] = frozenset({
    "made", "includes", "contains", "specifications", "dimensions",
    "material", "weight", "measures", "capacity", "voltage", "compatible",
    "features", "constructed", "designed", "manufactured", "crafted",
    "built", "equipped", "consisting", "comprised", "rated", "certified",
    "compliant", "specification", "technical",
})

# --- Emotional / persuasive words ---
_EMOTIONAL_WORDS: frozenset[str] = frozenset({
    "amazing", "beautiful", "stunning", "incredible", "extraordinary",
    "gorgeous", "magnificent", "brilliant", "exceptional", "remarkable",
    "unbelievable", "breathtaking", "sensational", "unforgettable",
    "irresistible", "luxurious", "exclusive", "premium", "ultimate",
    "revolutionary", "transformative", "must-have", "best-selling",
    "award-winning", "handcrafted", "artisan", "rare", "limited",
    "authentic", "genuine", "powerful", "proven", "guaranteed", "trusted",
    "beloved", "iconic", "timeless", "sophisticated", "elegant", "sleek",
    "innovative", "cutting-edge", "state-of-the-art", "world-class",
    "finest", "superior", "unmatched", "unrivaled",
})


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------


def _count_syllables(word: str) -> int:
    """Count syllables in a word using the vowel-group heuristic."""
    word = word.lower().strip()
    if len(word) <= 2:
        return 1
    # Remove trailing silent 'e'
    if word.endswith("e") and not word.endswith("le"):
        word = word[:-1]
    count = len(_VOWEL_GROUP_RE.findall(word))
    return max(1, count)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using punctuation boundaries."""
    # Replace common HTML-like boundaries with sentence-ending periods
    cleaned = text.replace("\n", ". ").replace("\r", ". ")
    parts = _SENTENCE_SPLIT_RE.split(cleaned)
    return [s.strip() for s in parts if s.strip() and len(s.strip().split()) >= 2]


def _compute_flesch_kincaid(total_words: int, total_sentences: int, total_syllables: int) -> float:
    """Compute the Flesch-Kincaid grade level.

    Formula: 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
    """
    if total_words == 0 or total_sentences == 0:
        return 0.0
    grade = (
        0.39 * (total_words / total_sentences)
        + 11.8 * (total_syllables / total_words)
        - 15.59
    )
    return round(max(0.0, grade), 1)


def _extract_description_element(soup: BeautifulSoup) -> Optional[Tag]:
    """Extract the description container element using cascading fallbacks.

    Returns the Tag element (preserving inner HTML) or None.
    """
    # 1. Dawn theme: div.product__description.rte
    el = soup.select_one("div.product__description.rte")
    if el and el.get_text(strip=True):
        return el

    # 2. Older Dawn: .product__description
    el = soup.select_one(".product__description")
    if el and el.get_text(strip=True):
        return el

    # 3. Generic: .product-description
    el = soup.select_one(".product-description")
    if el and el.get_text(strip=True):
        return el

    # 4. Class contains "product-description"
    el = soup.select_one('[class*="product-description"]')
    if el and el.get_text(strip=True):
        return el

    # 5. Data attribute
    el = soup.select_one("[data-product-description]")
    if el and el.get_text(strip=True):
        return el

    return None


def _extract_description_text_fallback(soup: BeautifulSoup) -> Optional[str]:
    """Extract description from JSON-LD or meta tag (text only, no HTML)."""
    # JSON-LD Product schema
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
            # Handle @graph
            if "@graph" in item:
                graph = item["@graph"]
                if isinstance(graph, list):
                    items.extend(graph)
                continue
            if item.get("@type") == "Product":
                desc = item.get("description", "")
                if desc and isinstance(desc, str) and len(desc.strip()) > 10:
                    return desc.strip()

    # Meta description
    meta = soup.find("meta", attrs={"name": "description"})
    if meta:
        content = meta.get("content", "")
        if isinstance(content, str) and len(content.strip()) > 10:
            return content.strip()

    return None


def _analyze_formatting(element: Tag) -> tuple[int, bool, bool, bool]:
    """Analyze HTML formatting richness within a description element.

    Returns:
        (tag_variety, has_headings, has_bullet_lists, has_emphasis)
    """
    found_tags: set[str] = set()

    for tag in element.find_all(True):
        tag_name = tag.name.lower()
        if tag_name in _FORMATTING_TAGS:
            found_tags.add(tag_name)

    has_headings = bool(found_tags & _HEADING_TAGS)
    has_bullet_lists = bool(found_tags & _LIST_TAGS)
    has_emphasis = bool(found_tags & _EMPHASIS_TAGS)

    return len(found_tags), has_headings, has_bullet_lists, has_emphasis


def _analyze_language(words: list[str]) -> tuple[float, int, int, float]:
    """Analyze benefit/feature ratio and emotional language density.

    Returns:
        (benefit_ratio, benefit_count, feature_count, emotional_density)
    """
    benefit_count = 0
    feature_count = 0
    emotional_count = 0

    for w in words:
        wl = w.lower()
        if wl in _BENEFIT_WORDS:
            benefit_count += 1
        if wl in _FEATURE_WORDS:
            feature_count += 1
        if wl in _EMOTIONAL_WORDS:
            emotional_count += 1

    total_bf = benefit_count + feature_count
    benefit_ratio = benefit_count / total_bf if total_bf > 0 else 0.0
    emotional_density = emotional_count / len(words) if words else 0.0

    return (
        round(benefit_ratio, 3),
        benefit_count,
        feature_count,
        round(emotional_density, 4),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_description(html: str) -> DescriptionSignals:
    """Detect description quality signals from rendered product page HTML.

    Extracts the product description using cascading DOM selectors, then
    computes NLP metrics (word count, readability, persuasion language,
    formatting richness) using pure Python — no external NLP libraries.
    """
    signals = DescriptionSignals()

    if not html:
        return signals

    soup = BeautifulSoup(html, "html.parser")

    # --- Try HTML-based extraction (preserves formatting) ---
    desc_element = _extract_description_element(soup)
    has_html = desc_element is not None

    if desc_element is not None:
        desc_text = desc_element.get_text(separator=" ").strip()
        # Analyze HTML formatting
        tag_variety, has_headings, has_bullets, has_emphasis = _analyze_formatting(desc_element)
        signals.html_tag_variety = tag_variety
        signals.has_headings = has_headings
        signals.has_bullet_lists = has_bullets
        signals.has_emphasis = has_emphasis
    else:
        # Fall back to text-only extraction (JSON-LD / meta)
        desc_text = _extract_description_text_fallback(soup)
        if desc_text is None:
            return signals
        # Text-only: formatting signals stay at defaults (zero/False)

    if not desc_text or len(desc_text.strip()) < 5:
        return signals

    signals.description_found = True

    # --- Word-level analysis ---
    words = _WORD_RE.findall(desc_text)
    signals.word_count = len(words)

    if not words:
        return signals

    # --- Readability metrics ---
    sentences = _split_sentences(desc_text)
    signals.sentence_count = len(sentences) if sentences else 1

    signals.avg_sentence_length = round(
        len(words) / signals.sentence_count, 1
    )

    total_syllables = sum(_count_syllables(w) for w in words)
    signals.flesch_kincaid_grade = _compute_flesch_kincaid(
        len(words), signals.sentence_count, total_syllables
    )

    # --- Persuasion language ---
    benefit_ratio, benefit_count, feature_count, emotional_density = _analyze_language(words)
    signals.benefit_ratio = benefit_ratio
    signals.benefit_word_count = benefit_count
    signals.feature_word_count = feature_count
    signals.emotional_density = emotional_density

    logger.info(
        "Description detected: found=%s words=%d fk_grade=%.1f "
        "avg_sent=%.1f sentences=%d "
        "benefit_ratio=%.2f benefit=%d feature=%d emotional=%.3f "
        "tag_variety=%d headings=%s bullets=%s emphasis=%s",
        signals.description_found,
        signals.word_count,
        signals.flesch_kincaid_grade,
        signals.avg_sentence_length,
        signals.sentence_count,
        signals.benefit_ratio,
        signals.benefit_word_count,
        signals.feature_word_count,
        signals.emotional_density,
        signals.html_tag_variety,
        signals.has_headings,
        signals.has_bullet_lists,
        signals.has_emphasis,
    )

    return signals

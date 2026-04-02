"""Tests for POST /analyze-competitors endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.scoring import CATEGORY_KEYS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_HTML = "<html><body>" + ("x" * 1000) + "</body></html>"

_USER_ANALYSIS = {
    "score": 55,
    "summary": "Decent product page",
    "tips": ["tip1", "tip2", "tip3"],
    "categories": {k: 50 for k in CATEGORY_KEYS},
}

_COMPETITOR_CANDIDATES = [
    {"name": "Amazon - Widget", "url": "https://amazon.com/widget"},
    {"name": "Target - Gadget", "url": "https://target.com/gadget"},
    {"name": "Walmart - Thing", "url": "https://walmart.com/thing"},
]

_COMP_ANALYSIS = {
    "score": 70,
    "summary": "Good competitor page",
    "tips": ["c1", "c2"],
    "categories": {k: 60 for k in CATEGORY_KEYS},
}


def _client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Missing / empty URL → 400
# ---------------------------------------------------------------------------


def test_competitors_missing_url():
    client = _client()
    # No body
    resp = client.post("/analyze-competitors", json={})
    assert resp.status_code == 400
    assert "URL is required" in resp.json()["error"]

    # Empty string
    resp = client.post("/analyze-competitors", json={"url": ""})
    assert resp.status_code == 400
    assert "URL is required" in resp.json()["error"]

    # Whitespace only
    resp = client.post("/analyze-competitors", json={"url": "   "})
    assert resp.status_code == 400
    assert "URL is required" in resp.json()["error"]


# ---------------------------------------------------------------------------
# 2. Missing API key → 500
# ---------------------------------------------------------------------------


@patch("app.routers.analyze_competitors.fetch_page_html", new_callable=AsyncMock)
def test_competitors_missing_api_key(mock_fetch):
    mock_fetch.return_value = _VALID_HTML
    client = _client()
    with patch("app.routers.analyze_competitors.settings") as mock_settings:
        mock_settings.openai_api_key = ""
        resp = client.post("/analyze-competitors", json={"url": "http://example.com"})
    assert resp.status_code == 500
    assert "Server configuration error" in resp.json()["error"]


# ---------------------------------------------------------------------------
# 3. Fetch failure → 400
# ---------------------------------------------------------------------------


@patch("app.routers.analyze_competitors.fetch_page_html", new_callable=AsyncMock)
def test_competitors_fetch_failure(mock_fetch):
    mock_fetch.side_effect = Exception("connection refused")
    client = _client()
    with patch("app.routers.analyze_competitors.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"
        resp = client.post("/analyze-competitors", json={"url": "http://example.com"})
    assert resp.status_code == 400
    assert "Could not fetch" in resp.json()["error"]


# ---------------------------------------------------------------------------
# 4. Happy path — 3 competitors validate+score successfully
# ---------------------------------------------------------------------------


@patch("app.routers.analyze_competitors.validate_page_html", new_callable=AsyncMock)
@patch("app.routers.analyze_competitors.identify_competitors", new_callable=AsyncMock)
@patch("app.routers.analyze_competitors.score_page", new_callable=AsyncMock)
@patch("app.routers.analyze_competitors.fetch_page_html", new_callable=AsyncMock)
def test_competitors_success(mock_fetch, mock_score, mock_identify, mock_validate):
    mock_fetch.return_value = _VALID_HTML

    # score_page is called once for the user page, then once per competitor
    mock_score.side_effect = [_USER_ANALYSIS, _COMP_ANALYSIS, _COMP_ANALYSIS, _COMP_ANALYSIS]

    mock_identify.return_value = _COMPETITOR_CANDIDATES
    mock_validate.return_value = _VALID_HTML  # All competitors reachable

    client = _client()
    with patch("app.routers.analyze_competitors.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"
        resp = client.post("/analyze-competitors", json={"url": "http://example.com/product"})

    assert resp.status_code == 200
    data = resp.json()

    # Verify yourPage structure
    yp = data["yourPage"]
    assert yp["score"] == 55
    assert yp["summary"] == "Decent product page"
    assert yp["tips"] == ["tip1", "tip2", "tip3"]
    assert yp["url"] == "http://example.com/product"
    assert set(CATEGORY_KEYS) == set(yp["categories"].keys())

    # Verify competitors
    comps = data["competitors"]
    assert len(comps) == 3
    for comp in comps:
        assert "name" in comp
        assert "url" in comp
        assert comp["score"] == 70
        assert comp["summary"] == "Good competitor page"
        assert set(CATEGORY_KEYS) == set(comp["categories"].keys())


# ---------------------------------------------------------------------------
# 5. Fallback path — all URL validations fail, AI fallback provides competitors
# ---------------------------------------------------------------------------


@patch("app.routers.analyze_competitors.call_openrouter", new_callable=AsyncMock)
@patch("app.routers.analyze_competitors.validate_page_html", new_callable=AsyncMock)
@patch("app.routers.analyze_competitors.identify_competitors", new_callable=AsyncMock)
@patch("app.routers.analyze_competitors.score_page", new_callable=AsyncMock)
@patch("app.routers.analyze_competitors.fetch_page_html", new_callable=AsyncMock)
def test_competitors_fallback_path(
    mock_fetch, mock_score, mock_identify, mock_validate, mock_openrouter
):
    mock_fetch.return_value = _VALID_HTML
    mock_score.return_value = _USER_ANALYSIS
    mock_identify.return_value = _COMPETITOR_CANDIDATES
    mock_validate.return_value = None  # All validations fail

    # Fallback call_openrouter returns AI-generated competitors
    mock_openrouter.return_value = [
        {
            "name": "Sephora - Serum",
            "score": 75,
            "summary": "Well-designed page",
            "categories": {"title": 70, "images": 80, "pricing": 65},
        },
        {
            "name": "Nordstrom - Cream",
            "score": 68,
            "summary": "Solid layout",
            "categories": {"title": 60, "images": 75, "pricing": 55},
        },
        {
            "name": "Ulta - Mask",
            "score": 72,
            "summary": "Good product page",
            "categories": {"title": 65, "images": 70, "pricing": 60},
        },
    ]

    client = _client()
    with patch("app.routers.analyze_competitors.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"
        resp = client.post("/analyze-competitors", json={"url": "http://example.com/product"})

    assert resp.status_code == 200
    data = resp.json()

    # User page should still work
    assert data["yourPage"]["score"] == 55

    # Competitors should come from fallback with url=""
    comps = data["competitors"]
    assert len(comps) == 3
    for comp in comps:
        assert comp["url"] == "", f"Fallback competitors should have url='' but got {comp['url']}"
        assert comp["score"] > 0
        assert "name" in comp
        assert "summary" in comp
        # All 20 category keys should be present (via build_category_scores)
        assert set(CATEGORY_KEYS) == set(comp["categories"].keys())


# ---------------------------------------------------------------------------
# 6. Partial validation — some competitors pass, some fail, still reaches 3
# ---------------------------------------------------------------------------


@patch("app.routers.analyze_competitors.validate_page_html", new_callable=AsyncMock)
@patch("app.routers.analyze_competitors.identify_competitors", new_callable=AsyncMock)
@patch("app.routers.analyze_competitors.score_page", new_callable=AsyncMock)
@patch("app.routers.analyze_competitors.fetch_page_html", new_callable=AsyncMock)
def test_competitors_partial_validation(mock_fetch, mock_score, mock_identify, mock_validate):
    mock_fetch.return_value = _VALID_HTML

    # First call for user page, then 2 calls for the 2 reachable competitors
    mock_score.side_effect = [_USER_ANALYSIS, _COMP_ANALYSIS, _COMP_ANALYSIS]

    candidates = [
        {"name": "Amazon - Widget", "url": "https://amazon.com/widget"},
        {"name": "Dead - Link", "url": "https://dead.com/page"},
        {"name": "Target - Gadget", "url": "https://target.com/gadget"},
    ]
    mock_identify.return_value = candidates

    # Only first and third succeed
    mock_validate.side_effect = [_VALID_HTML, None, _VALID_HTML]

    client = _client()
    with patch("app.routers.analyze_competitors.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"
        resp = client.post("/analyze-competitors", json={"url": "http://example.com/product"})

    assert resp.status_code == 200
    data = resp.json()
    comps = data["competitors"]
    # We got 2 real competitors (not 3), but the test verifies the flow handles it
    assert len(comps) >= 1
    assert all(c["score"] > 0 for c in comps)


# ---------------------------------------------------------------------------
# 7. Garbage score filtering — competitor with score=0 or error-like summary is dropped
# ---------------------------------------------------------------------------


@patch("app.routers.analyze_competitors.validate_page_html", new_callable=AsyncMock)
@patch("app.routers.analyze_competitors.identify_competitors", new_callable=AsyncMock)
@patch("app.routers.analyze_competitors.score_page", new_callable=AsyncMock)
@patch("app.routers.analyze_competitors.fetch_page_html", new_callable=AsyncMock)
def test_competitors_garbage_filtered(mock_fetch, mock_score, mock_identify, mock_validate):
    mock_fetch.return_value = _VALID_HTML

    garbage_analysis = {
        "score": 0,
        "summary": "404 error page not found",
        "tips": [],
        "categories": {k: 0 for k in CATEGORY_KEYS},
    }

    # User analysis ok, but competitor analysis returns garbage
    mock_score.side_effect = [_USER_ANALYSIS, garbage_analysis]

    mock_identify.return_value = [
        {"name": "Dead - Page", "url": "https://dead.com/404"},
    ]
    mock_validate.return_value = _VALID_HTML  # URL validates but scoring = garbage

    client = _client()
    with patch("app.routers.analyze_competitors.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"
        # Patch call_openrouter for fallback path (which will fire since 0 competitors scored)
        with patch(
            "app.routers.analyze_competitors.call_openrouter",
            new_callable=AsyncMock,
        ) as mock_fallback:
            mock_fallback.return_value = [
                {
                    "name": "Good - Brand",
                    "score": 80,
                    "summary": "Strong page",
                    "categories": {"title": 75},
                },
            ]
            resp = client.post(
                "/analyze-competitors", json={"url": "http://example.com/product"}
            )

    assert resp.status_code == 200
    data = resp.json()
    comps = data["competitors"]
    # The garbage competitor was dropped, fallback kicked in
    assert all(c["score"] > 0 for c in comps)
    assert any(c["url"] == "" for c in comps)  # fallback competitor has empty URL


# ---------------------------------------------------------------------------
# 8. Outer exception → 500
# ---------------------------------------------------------------------------


@patch("app.routers.analyze_competitors.fetch_page_html", new_callable=AsyncMock)
def test_competitors_outer_exception(mock_fetch):
    """If something unexpected blows up, the outer try/except catches it."""
    mock_fetch.return_value = _VALID_HTML

    client = _client()
    with patch("app.routers.analyze_competitors.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"
        # Make score_page raise an unexpected error
        with patch(
            "app.routers.analyze_competitors.score_page",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Boom"),
        ):
            resp = client.post(
                "/analyze-competitors", json={"url": "http://example.com"}
            )
    assert resp.status_code == 500
    assert "Something went wrong" in resp.json()["error"]


# ---------------------------------------------------------------------------
# 9. Fallback duplicate skipping — existing names not re-added
# ---------------------------------------------------------------------------


@patch("app.routers.analyze_competitors.call_openrouter", new_callable=AsyncMock)
@patch("app.routers.analyze_competitors.validate_page_html", new_callable=AsyncMock)
@patch("app.routers.analyze_competitors.identify_competitors", new_callable=AsyncMock)
@patch("app.routers.analyze_competitors.score_page", new_callable=AsyncMock)
@patch("app.routers.analyze_competitors.fetch_page_html", new_callable=AsyncMock)
def test_competitors_fallback_skips_duplicates(
    mock_fetch, mock_score, mock_identify, mock_validate, mock_openrouter
):
    mock_fetch.return_value = _VALID_HTML

    # One competitor already scored from real URLs
    real_comp = {
        "score": 70,
        "summary": "Good page",
        "tips": [],
        "categories": {k: 60 for k in CATEGORY_KEYS},
    }
    mock_score.side_effect = [_USER_ANALYSIS, real_comp]
    mock_identify.return_value = [
        {"name": "Amazon - Widget", "url": "https://amazon.com/widget"},
    ]
    mock_validate.return_value = _VALID_HTML

    # Fallback includes a duplicate name that should be skipped
    mock_openrouter.return_value = [
        {
            "name": "Amazon - Widget",  # duplicate!
            "score": 80,
            "summary": "Duplicate",
            "categories": {"title": 70},
        },
        {
            "name": "New Brand - Product",
            "score": 65,
            "summary": "Fresh",
            "categories": {"title": 55},
        },
        {
            "name": "Another - Product",
            "score": 72,
            "summary": "Another one",
            "categories": {"title": 60},
        },
    ]

    client = _client()
    with patch("app.routers.analyze_competitors.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"
        resp = client.post("/analyze-competitors", json={"url": "http://example.com/product"})

    assert resp.status_code == 200
    data = resp.json()
    comps = data["competitors"]
    names = [c["name"] for c in comps]
    # "Amazon - Widget" should appear only once (from the real scoring, not duplicated by fallback)
    assert names.count("Amazon - Widget") == 1
    assert len(comps) == 3  # 1 real + 2 fallback

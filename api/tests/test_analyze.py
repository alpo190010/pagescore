"""Tests for POST /analyze endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.services.scoring import CATEGORY_KEYS, build_category_scores, compute_weighted_score

# --- Test fixtures / helpers ---

_VALID_HTML = "<html><body>" + ("x" * 200) + "</body></html>"

_AI_RESPONSE = {
    "score": 42,
    "summary": "Test summary",
    "tips": ["tip1", "tip2"],
    "categories": {"pageSpeed": 65, "images": 80},
    "productPrice": 29.99,
    "productCategory": "fashion",
    "estimatedMonthlyVisitors": 2000,
}


def _mock_db():
    """Return a MagicMock that simulates a SQLAlchemy Session."""
    session = MagicMock()
    # Make execute().fetchone() return a row with a UUID
    row = MagicMock()
    row.__getitem__ = MagicMock(return_value="fake-uuid-1234")
    session.execute.return_value.fetchone.return_value = row
    return session


def _get_client(db_override=None):
    """Return a TestClient with an optional get_db override."""
    if db_override is not None:
        app.dependency_overrides[get_db] = lambda: db_override
    else:
        app.dependency_overrides[get_db] = lambda: _mock_db()
    client = TestClient(app)
    return client


# --- URL validation tests ---


def test_analyze_missing_url():
    client = _get_client()
    # Empty body
    resp = client.post("/analyze", json={})
    assert resp.status_code == 400
    assert "URL is required" in resp.json()["error"]

    # Empty string
    resp = client.post("/analyze", json={"url": ""})
    assert resp.status_code == 400
    assert "URL is required" in resp.json()["error"]

    app.dependency_overrides.clear()


def test_analyze_invalid_url_format():
    client = _get_client()
    resp = client.post("/analyze", json={"url": "not-a-url"})
    assert resp.status_code == 400
    assert "Invalid URL" in resp.json()["error"]

    app.dependency_overrides.clear()


def test_analyze_localhost_blocked():
    client = _get_client()
    resp = client.post("/analyze", json={"url": "http://localhost/admin"})
    assert resp.status_code == 400
    assert "Internal" in resp.json()["error"]

    app.dependency_overrides.clear()


def test_analyze_private_ip_blocked():
    client = _get_client()
    resp = client.post("/analyze", json={"url": "http://192.168.1.1/"})
    assert resp.status_code == 400
    assert "Internal" in resp.json()["error"]

    app.dependency_overrides.clear()


def test_analyze_url_too_long():
    client = _get_client()
    long_url = "http://example.com/" + "a" * 2100
    resp = client.post("/analyze", json={"url": long_url})
    assert resp.status_code == 400
    assert "too long" in resp.json()["error"]

    app.dependency_overrides.clear()


def test_analyze_non_http_protocol():
    client = _get_client()
    resp = client.post("/analyze", json={"url": "ftp://example.com/file"})
    assert resp.status_code == 400
    assert "HTTP/HTTPS" in resp.json()["error"]

    app.dependency_overrides.clear()


# --- Service-level error tests ---


@patch("app.routers.analyze.render_page", new_callable=AsyncMock)
def test_analyze_fetch_failure(mock_fetch):
    mock_fetch.side_effect = Exception("connection refused")
    client = _get_client()
    resp = client.post("/analyze", json={"url": "http://example.com"})
    assert resp.status_code == 400
    assert "Could not fetch" in resp.json()["error"]

    app.dependency_overrides.clear()


@patch("app.routers.analyze.render_page", new_callable=AsyncMock)
def test_analyze_page_too_small(mock_fetch):
    mock_fetch.return_value = "<html>hi</html>"  # < 100 chars
    client = _get_client()
    resp = client.post("/analyze", json={"url": "http://example.com"})
    assert resp.status_code == 400
    assert "empty or too small" in resp.json()["error"]

    app.dependency_overrides.clear()


@patch("app.routers.analyze.get_social_proof_tips", return_value=[])
@patch("app.routers.analyze.score_social_proof", return_value=0)
@patch("app.routers.analyze.detect_social_proof")
@patch("app.routers.analyze.render_page", new_callable=AsyncMock)
def test_analyze_missing_api_key(mock_fetch, mock_detect, mock_sp_score, mock_sp_tips):
    mock_fetch.return_value = _VALID_HTML
    client = _get_client()
    with patch("app.routers.analyze.settings") as mock_settings:
        mock_settings.openai_api_key = ""
        resp = client.post("/analyze", json={"url": "http://example.com"})
    assert resp.status_code == 500
    assert "Server configuration error" in resp.json()["error"]

    app.dependency_overrides.clear()


@patch("app.routers.analyze.get_social_proof_tips", return_value=[])
@patch("app.routers.analyze.score_social_proof", return_value=0)
@patch("app.routers.analyze.detect_social_proof")
@patch("app.routers.analyze.call_openrouter", new_callable=AsyncMock)
@patch("app.routers.analyze.render_page", new_callable=AsyncMock)
def test_analyze_ai_value_error(mock_fetch, mock_ai, mock_detect, mock_sp_score, mock_sp_tips):
    mock_fetch.return_value = _VALID_HTML
    mock_ai.side_effect = ValueError("No JSON found")
    client = _get_client()
    with patch("app.routers.analyze.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"
        resp = client.post("/analyze", json={"url": "http://example.com"})
    assert resp.status_code == 500
    assert "unexpected format" in resp.json()["error"]

    app.dependency_overrides.clear()


@patch("app.routers.analyze.get_social_proof_tips", return_value=[])
@patch("app.routers.analyze.score_social_proof", return_value=0)
@patch("app.routers.analyze.detect_social_proof")
@patch("app.routers.analyze.call_openrouter", new_callable=AsyncMock)
@patch("app.routers.analyze.render_page", new_callable=AsyncMock)
def test_analyze_ai_api_error(mock_fetch, mock_ai, mock_detect, mock_sp_score, mock_sp_tips):
    mock_fetch.return_value = _VALID_HTML
    mock_ai.side_effect = RuntimeError("API down")
    client = _get_client()
    with patch("app.routers.analyze.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"
        resp = client.post("/analyze", json={"url": "http://example.com"})
    assert resp.status_code == 500
    assert "AI analysis failed" in resp.json()["error"]

    app.dependency_overrides.clear()


# --- Happy-path success test ---


@patch("app.routers.analyze.get_social_proof_tips", return_value=["Add photo reviews"])
@patch("app.routers.analyze.score_social_proof", return_value=75)
@patch("app.routers.analyze.detect_social_proof")
@patch("app.routers.analyze.call_openrouter", new_callable=AsyncMock)
@patch("app.routers.analyze.render_page", new_callable=AsyncMock)
def test_analyze_success(mock_fetch, mock_ai, mock_detect, mock_sp_score, mock_sp_tips):
    mock_fetch.return_value = _VALID_HTML
    mock_ai.return_value = _AI_RESPONSE

    mock_session = _mock_db()
    client = _get_client(db_override=mock_session)

    with patch("app.routers.analyze.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"
        resp = client.post("/analyze", json={"url": "http://example.com/product"})

    assert resp.status_code == 200
    data = resp.json()

    # Core fields present
    assert data["summary"] == "Test summary"
    assert data["productPrice"] == 29.99
    assert data["productCategory"] == "fashion"
    assert data["estimatedMonthlyVisitors"] == 2000
    assert "analysisId" in data

    # All 20 category keys present and 0-100
    cats = data["categories"]
    assert set(CATEGORY_KEYS) == set(cats.keys()), f"Missing keys: {set(CATEGORY_KEYS) - set(cats.keys())}"
    for key, val in cats.items():
        assert isinstance(val, int), f"{key} should be int, got {type(val)}"
        assert 0 <= val <= 100, f"{key}={val} out of 0-100"

    # socialProof comes from deterministic rubric, not AI
    assert cats["socialProof"] == 75

    # AI-supplied categories forwarded correctly
    assert cats["pageSpeed"] == 65
    assert cats["images"] == 80

    # Social proof tip appears first, then AI tips
    assert data["tips"][0] == "Add photo reviews"
    assert "tip1" in data["tips"]
    assert "tip2" in data["tips"]

    # Overall score is weighted average, not raw AI score
    expected_score = compute_weighted_score(cats)
    assert data["score"] == expected_score

    # DB was called
    assert mock_session.add.called  # Scan insert
    assert mock_session.execute.called  # ProductAnalysis upsert

    app.dependency_overrides.clear()


# --- Score clamping edge cases ---


@patch("app.routers.analyze.get_social_proof_tips", return_value=[])
@patch("app.routers.analyze.score_social_proof", return_value=0)
@patch("app.routers.analyze.detect_social_proof")
@patch("app.routers.analyze.call_openrouter", new_callable=AsyncMock)
@patch("app.routers.analyze.render_page", new_callable=AsyncMock)
def test_analyze_score_clamping(mock_fetch, mock_ai, mock_detect, mock_sp_score, mock_sp_tips):
    mock_fetch.return_value = _VALID_HTML
    mock_ai.return_value = {
        **_AI_RESPONSE,
        "score": 150,  # AI score no longer used directly — weighted average instead
        "productPrice": -10,  # should clamp to 0
    }
    client = _get_client()
    with patch("app.routers.analyze.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"
        resp = client.post("/analyze", json={"url": "http://example.com/product"})

    assert resp.status_code == 200
    data = resp.json()
    # Score is now computed by weighted average, not clamped from AI
    assert 0 <= data["score"] <= 100
    assert data["productPrice"] == 0

    app.dependency_overrides.clear()


# --- Hybrid pipeline tests ---


@patch("app.routers.analyze.get_social_proof_tips", return_value=[])
@patch("app.routers.analyze.score_social_proof", return_value=0)
@patch("app.routers.analyze.detect_social_proof")
@patch("app.routers.analyze.call_openrouter", new_callable=AsyncMock)
@patch("app.routers.analyze.render_page", new_callable=AsyncMock)
def test_analyze_prompt_excludes_social_proof(mock_fetch, mock_ai, mock_detect, mock_sp_score, mock_sp_tips):
    """The AI prompt should NOT contain socialProof — it's scored deterministically."""
    mock_fetch.return_value = _VALID_HTML
    mock_ai.return_value = _AI_RESPONSE
    client = _get_client()
    with patch("app.routers.analyze.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"
        resp = client.post("/analyze", json={"url": "http://example.com/product"})
    assert resp.status_code == 200

    # Capture the prompt passed to call_openrouter
    prompt_arg = mock_ai.call_args[0][0]
    assert "socialProof" not in prompt_arg, "socialProof should not appear in the AI prompt"

    app.dependency_overrides.clear()


@patch("app.routers.analyze.get_social_proof_tips", return_value=["SP tip 1", "SP tip 2"])
@patch("app.routers.analyze.score_social_proof", return_value=60)
@patch("app.routers.analyze.detect_social_proof")
@patch("app.routers.analyze.call_openrouter", new_callable=AsyncMock)
@patch("app.routers.analyze.render_page", new_callable=AsyncMock)
def test_analyze_tips_merged(mock_fetch, mock_ai, mock_detect, mock_sp_score, mock_sp_tips):
    """Social proof tips come first, then AI tips, total capped at 20."""
    ai_tips = [f"AI tip {i}" for i in range(19)]
    mock_fetch.return_value = _VALID_HTML
    mock_ai.return_value = {**_AI_RESPONSE, "tips": ai_tips}
    client = _get_client()
    with patch("app.routers.analyze.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"
        resp = client.post("/analyze", json={"url": "http://example.com/product"})

    assert resp.status_code == 200
    data = resp.json()
    tips = data["tips"]

    # Social proof tips come first
    assert tips[0] == "SP tip 1"
    assert tips[1] == "SP tip 2"

    # Total capped at 20
    assert len(tips) <= 20

    # AI tips follow social proof tips
    assert tips[2] == "AI tip 0"

    app.dependency_overrides.clear()


@patch("app.routers.analyze.get_social_proof_tips", return_value=[])
@patch("app.routers.analyze.score_social_proof", return_value=85)
@patch("app.routers.analyze.detect_social_proof")
@patch("app.routers.analyze.call_openrouter", new_callable=AsyncMock)
@patch("app.routers.analyze.render_page", new_callable=AsyncMock)
def test_analyze_weighted_score(mock_fetch, mock_ai, mock_detect, mock_sp_score, mock_sp_tips):
    """Overall score is compute_weighted_score(categories), not AI's raw score."""
    ai_cats = {
        "pageSpeed": 70,
        "images": 55,
        "checkout": 80,
        "mobileCta": 60,
        "title": 45,
        "aiDiscoverability": 30,
        "structuredData": 50,
        "pricing": 65,
        "description": 40,
        "shipping": 35,
        "crossSell": 25,
        "cartRecovery": 50,
        "trust": 55,
        "merchantFeed": 40,
        "socialCommerce": 30,
        "sizeGuide": 60,
        "variantUx": 45,
        "accessibility": 35,
        "contentFreshness": 50,
    }
    mock_fetch.return_value = _VALID_HTML
    mock_ai.return_value = {**_AI_RESPONSE, "score": 99, "categories": ai_cats}
    client = _get_client()
    with patch("app.routers.analyze.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"
        resp = client.post("/analyze", json={"url": "http://example.com/product"})

    assert resp.status_code == 200
    data = resp.json()

    # Build expected categories: AI cats + socialProof override
    expected_cats = build_category_scores(ai_cats)
    expected_cats["socialProof"] = 85
    expected_score = compute_weighted_score(expected_cats)

    assert data["score"] == expected_score
    assert data["categories"]["socialProof"] == 85
    # AI's raw score (99) is NOT used
    assert data["score"] != 99

    app.dependency_overrides.clear()

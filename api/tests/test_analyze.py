"""Tests for POST /analyze endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.services.scoring import CATEGORY_KEYS

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


@patch("app.routers.analyze.fetch_page_html", new_callable=AsyncMock)
def test_analyze_fetch_failure(mock_fetch):
    mock_fetch.side_effect = Exception("connection refused")
    client = _get_client()
    resp = client.post("/analyze", json={"url": "http://example.com"})
    assert resp.status_code == 400
    assert "Could not fetch" in resp.json()["error"]

    app.dependency_overrides.clear()


@patch("app.routers.analyze.fetch_page_html", new_callable=AsyncMock)
def test_analyze_page_too_small(mock_fetch):
    mock_fetch.return_value = "<html>hi</html>"  # < 100 chars
    client = _get_client()
    resp = client.post("/analyze", json={"url": "http://example.com"})
    assert resp.status_code == 400
    assert "empty or too small" in resp.json()["error"]

    app.dependency_overrides.clear()


@patch("app.routers.analyze.fetch_page_html", new_callable=AsyncMock)
def test_analyze_missing_api_key(mock_fetch):
    mock_fetch.return_value = _VALID_HTML
    client = _get_client()
    with patch("app.routers.analyze.settings") as mock_settings:
        mock_settings.openai_api_key = ""
        resp = client.post("/analyze", json={"url": "http://example.com"})
    assert resp.status_code == 500
    assert "Server configuration error" in resp.json()["error"]

    app.dependency_overrides.clear()


@patch("app.routers.analyze.call_openrouter", new_callable=AsyncMock)
@patch("app.routers.analyze.fetch_page_html", new_callable=AsyncMock)
def test_analyze_ai_value_error(mock_fetch, mock_ai):
    mock_fetch.return_value = _VALID_HTML
    mock_ai.side_effect = ValueError("No JSON found")
    client = _get_client()
    with patch("app.routers.analyze.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"
        resp = client.post("/analyze", json={"url": "http://example.com"})
    assert resp.status_code == 500
    assert "unexpected format" in resp.json()["error"]

    app.dependency_overrides.clear()


@patch("app.routers.analyze.call_openrouter", new_callable=AsyncMock)
@patch("app.routers.analyze.fetch_page_html", new_callable=AsyncMock)
def test_analyze_ai_api_error(mock_fetch, mock_ai):
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


@patch("app.routers.analyze.call_openrouter", new_callable=AsyncMock)
@patch("app.routers.analyze.fetch_page_html", new_callable=AsyncMock)
def test_analyze_success(mock_fetch, mock_ai):
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
    assert data["score"] == 42
    assert data["summary"] == "Test summary"
    assert data["tips"] == ["tip1", "tip2"]
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

    # Supplied categories forwarded, missing ones defaulted to 0
    assert cats["pageSpeed"] == 65
    assert cats["images"] == 80
    assert cats["socialProof"] == 0  # not in AI response → default

    # DB was called
    assert mock_session.add.called  # Scan insert
    assert mock_session.execute.called  # ProductAnalysis upsert

    app.dependency_overrides.clear()


# --- Score clamping edge cases ---


@patch("app.routers.analyze.call_openrouter", new_callable=AsyncMock)
@patch("app.routers.analyze.fetch_page_html", new_callable=AsyncMock)
def test_analyze_score_clamping(mock_fetch, mock_ai):
    mock_fetch.return_value = _VALID_HTML
    mock_ai.return_value = {
        **_AI_RESPONSE,
        "score": 150,  # should clamp to 100
        "productPrice": -10,  # should clamp to 0
    }
    client = _get_client()
    with patch("app.routers.analyze.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"
        resp = client.post("/analyze", json={"url": "http://example.com/product"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 100
    assert data["productPrice"] == 0

    app.dependency_overrides.clear()

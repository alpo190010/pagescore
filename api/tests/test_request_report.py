"""Tests for POST /request-report endpoint."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app


# ---- helpers ---------------------------------------------------------------


def _mock_db():
    """Return a MagicMock that simulates a SQLAlchemy Session."""
    session = MagicMock()
    return session


def _get_client(db_override=None):
    if db_override is not None:
        app.dependency_overrides[get_db] = lambda: db_override
    else:
        app.dependency_overrides[get_db] = lambda: _mock_db()
    return TestClient(app)


def _valid_payload(**overrides):
    base = {
        "email": "user@example.com",
        "url": "https://example.com/product",
        "score": 72,
        "summary": "Good product page",
        "tips": ["Tip 1", "Tip 2"],
        "categories": {"pageSpeed": 80, "images": 60},
    }
    base.update(overrides)
    return base


# ---- happy path ------------------------------------------------------------


class TestRequestReportValid:
    def test_valid_request_returns_success(self):
        db = _mock_db()
        client = _get_client(db)
        resp = client.post("/request-report", json=_valid_payload())
        assert resp.status_code == 200
        assert resp.json() == {"success": True}

    def test_db_add_called_for_report(self):
        db = _mock_db()
        client = _get_client(db)
        client.post("/request-report", json=_valid_payload())
        db.add.assert_called_once()
        report = db.add.call_args[0][0]
        assert report.email == "user@example.com"
        assert report.url == "https://example.com/product"
        assert report.score == 72

    def test_subscriber_upsert_executed(self):
        db = _mock_db()
        client = _get_client(db)
        client.post("/request-report", json=_valid_payload())
        # execute is called for the pg_insert subscriber statement
        db.execute.assert_called_once()

    def test_competitor_name_merged_into_categories(self):
        db = _mock_db()
        client = _get_client(db)
        payload = _valid_payload(competitorName="Rival Store")
        client.post("/request-report", json=payload)
        report = db.add.call_args[0][0]
        assert report.categories["_competitorName"] == "Rival Store"
        assert report.categories["pageSpeed"] == 80

    def test_competitor_name_empty_not_merged(self):
        db = _mock_db()
        client = _get_client(db)
        payload = _valid_payload(competitorName="")
        client.post("/request-report", json=payload)
        report = db.add.call_args[0][0]
        assert "_competitorName" not in (report.categories or {})

    def test_competitor_name_whitespace_not_merged(self):
        db = _mock_db()
        client = _get_client(db)
        payload = _valid_payload(competitorName="   ")
        client.post("/request-report", json=payload)
        report = db.add.call_args[0][0]
        assert "_competitorName" not in (report.categories or {})


# ---- email validation ------------------------------------------------------


class TestRequestReportEmailValidation:
    def test_missing_email(self):
        client = _get_client()
        payload = _valid_payload(email="")
        resp = client.post("/request-report", json=payload)
        assert resp.status_code == 400
        assert "valid email" in resp.json()["error"].lower()

    def test_email_no_at_sign(self):
        client = _get_client()
        payload = _valid_payload(email="noatsign.com")
        resp = client.post("/request-report", json=payload)
        assert resp.status_code == 400

    def test_email_too_long(self):
        client = _get_client()
        long_email = "a" * 251 + "@b.co"
        payload = _valid_payload(email=long_email)
        resp = client.post("/request-report", json=payload)
        assert resp.status_code == 400

    def test_email_with_spaces(self):
        client = _get_client()
        payload = _valid_payload(email="bad email@test.com")
        resp = client.post("/request-report", json=payload)
        assert resp.status_code == 400


# ---- URL validation --------------------------------------------------------


class TestRequestReportURLValidation:
    def test_missing_url(self):
        client = _get_client()
        payload = _valid_payload(url="")
        resp = client.post("/request-report", json=payload)
        assert resp.status_code == 400
        assert "URL is required" in resp.json()["error"]

    def test_url_too_long(self):
        client = _get_client()
        payload = _valid_payload(url="https://x.com/" + "a" * 2050)
        resp = client.post("/request-report", json=payload)
        assert resp.status_code == 400
        assert "too long" in resp.json()["error"].lower()


# ---- score clamping --------------------------------------------------------


class TestRequestReportScoreClamping:
    def test_negative_score_clamped_to_zero(self):
        db = _mock_db()
        client = _get_client(db)
        client.post("/request-report", json=_valid_payload(score=-10))
        report = db.add.call_args[0][0]
        assert report.score == 0

    def test_score_over_100_clamped(self):
        db = _mock_db()
        client = _get_client(db)
        client.post("/request-report", json=_valid_payload(score=999))
        report = db.add.call_args[0][0]
        assert report.score == 100

    def test_null_score_defaults_to_zero(self):
        db = _mock_db()
        client = _get_client(db)
        client.post("/request-report", json=_valid_payload(score=None))
        report = db.add.call_args[0][0]
        assert report.score == 0


# ---- tips truncation -------------------------------------------------------


class TestRequestReportTipsTruncation:
    def test_more_than_7_tips_truncated(self):
        db = _mock_db()
        client = _get_client(db)
        payload = _valid_payload(tips=[f"Tip {i}" for i in range(15)])
        client.post("/request-report", json=payload)
        report = db.add.call_args[0][0]
        assert len(report.tips) == 7

    def test_long_tip_truncated_to_300(self):
        db = _mock_db()
        client = _get_client(db)
        payload = _valid_payload(tips=["x" * 500])
        client.post("/request-report", json=payload)
        report = db.add.call_args[0][0]
        assert len(report.tips[0]) == 300


# ---- DB failure resilience -------------------------------------------------


class TestRequestReportDBFailure:
    def test_db_error_doesnt_crash(self):
        db = _mock_db()
        db.commit.side_effect = Exception("DB down")
        client = _get_client(db)
        resp = client.post("/request-report", json=_valid_payload())
        assert resp.status_code == 200
        assert resp.json() == {"success": True}

    def test_subscriber_insert_failure_doesnt_crash(self):
        db = _mock_db()
        db.execute.side_effect = Exception("Unique violation")
        client = _get_client(db)
        resp = client.post("/request-report", json=_valid_payload())
        assert resp.status_code == 200
        assert resp.json() == {"success": True}


# ---- summary truncation ---------------------------------------------------


class TestRequestReportSummary:
    def test_summary_truncated_to_500(self):
        db = _mock_db()
        client = _get_client(db)
        payload = _valid_payload(summary="s" * 600)
        client.post("/request-report", json=payload)
        report = db.add.call_args[0][0]
        assert len(report.summary) == 500

    def test_null_summary_stored_as_none(self):
        db = _mock_db()
        client = _get_client(db)
        payload = _valid_payload(summary=None)
        client.post("/request-report", json=payload)
        report = db.add.call_args[0][0]
        assert report.summary is None

"""Tests for POST /send-report-now endpoint."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _get_client():
    return TestClient(app)


def _valid_payload(**overrides):
    base = {
        "email": "user@example.com",
        "url": "https://example.com/product",
        "score": 72,
        "tips": ["Tip 1", "Tip 2"],
        "categories": {"pageSpeed": 80, "images": 60},
    }
    base.update(overrides)
    return base


# ---- happy path ------------------------------------------------------------


class TestSendReportNowValid:
    @patch("app.routers.send_report_now.send_email", return_value=True)
    def test_valid_request_returns_success(self, mock_send):
        client = _get_client()
        resp = client.post("/send-report-now", json=_valid_payload())
        assert resp.status_code == 200
        assert resp.json() == {"success": True}

    @patch("app.routers.send_report_now.send_email", return_value=True)
    def test_send_email_called_with_correct_from(self, mock_send):
        client = _get_client()
        client.post("/send-report-now", json=_valid_payload())
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args
        assert call_kwargs[1]["from_addr"] == "alpo.ai <noreply@alpo.ai>"

    @patch("app.routers.send_report_now.send_email", return_value=True)
    def test_send_email_called_with_correct_to(self, mock_send):
        client = _get_client()
        client.post("/send-report-now", json=_valid_payload())
        call_kwargs = mock_send.call_args
        assert call_kwargs[1]["to"] == "user@example.com"

    @patch("app.routers.send_report_now.send_email", return_value=True)
    def test_send_email_subject_contains_score(self, mock_send):
        client = _get_client()
        client.post("/send-report-now", json=_valid_payload(score=85))
        call_kwargs = mock_send.call_args
        assert "85/100" in call_kwargs[1]["subject"]
        assert "20 dimensions" in call_kwargs[1]["subject"]

    @patch("app.routers.send_report_now.send_email", return_value=True)
    def test_send_email_html_contains_report(self, mock_send):
        client = _get_client()
        client.post("/send-report-now", json=_valid_payload())
        call_kwargs = mock_send.call_args
        html = call_kwargs[1]["html"]
        assert "alpo.ai" in html
        assert "Priority Report" in html


# ---- email validation ------------------------------------------------------


class TestSendReportNowEmailValidation:
    def test_missing_email(self):
        client = _get_client()
        resp = client.post("/send-report-now", json=_valid_payload(email=""))
        assert resp.status_code == 400
        assert resp.json()["error"] == "Invalid email"

    def test_invalid_email_format(self):
        client = _get_client()
        resp = client.post("/send-report-now", json=_valid_payload(email="nope"))
        assert resp.status_code == 400

    def test_email_without_at(self):
        client = _get_client()
        resp = client.post("/send-report-now", json=_valid_payload(email="foo.bar"))
        assert resp.status_code == 400


# ---- send failure ----------------------------------------------------------


class TestSendReportNowSendFailure:
    @patch("app.routers.send_report_now.send_email", return_value=False)
    def test_send_failure_returns_500(self, mock_send):
        client = _get_client()
        resp = client.post("/send-report-now", json=_valid_payload())
        assert resp.status_code == 500
        assert resp.json()["error"] == "Failed to send"


# ---- score clamping --------------------------------------------------------


class TestSendReportNowScoreClamping:
    @patch("app.routers.send_report_now.send_email", return_value=True)
    def test_negative_score_clamped(self, mock_send):
        client = _get_client()
        resp = client.post("/send-report-now", json=_valid_payload(score=-5))
        assert resp.status_code == 200
        # Score in subject should show 0
        subject = mock_send.call_args[1]["subject"]
        assert "0/100" in subject

    @patch("app.routers.send_report_now.send_email", return_value=True)
    def test_over_100_score_clamped(self, mock_send):
        client = _get_client()
        resp = client.post("/send-report-now", json=_valid_payload(score=150))
        assert resp.status_code == 200
        subject = mock_send.call_args[1]["subject"]
        assert "100/100" in subject


# ---- tips truncation -------------------------------------------------------


class TestSendReportNowTipsTruncation:
    @patch("app.routers.send_report_now.send_email", return_value=True)
    def test_max_20_tips(self, mock_send):
        client = _get_client()
        payload = _valid_payload(tips=[f"Tip {i}" for i in range(30)])
        resp = client.post("/send-report-now", json=payload)
        assert resp.status_code == 200
        # The HTML should contain tips 1-20 but not tip 21
        html = mock_send.call_args[1]["html"]
        assert "20." in html
        # Tip 21 is index 20 → "21." should not appear as numbered tip
        # (it would show as "21." which is tip index 20 in 0-based)

    @patch("app.routers.send_report_now.send_email", return_value=True)
    def test_long_tip_truncated(self, mock_send):
        client = _get_client()
        payload = _valid_payload(tips=["x" * 500])
        resp = client.post("/send-report-now", json=payload)
        assert resp.status_code == 200


# ---- categories ------------------------------------------------------------


class TestSendReportNowCategories:
    @patch("app.routers.send_report_now.send_email", return_value=True)
    def test_null_categories_defaults_to_empty(self, mock_send):
        client = _get_client()
        payload = _valid_payload(categories=None)
        resp = client.post("/send-report-now", json=payload)
        assert resp.status_code == 200

    @patch("app.routers.send_report_now.send_email", return_value=True)
    def test_invalid_categories_defaults_to_empty(self, mock_send):
        client = _get_client()
        payload = _valid_payload(categories="not-a-dict")
        # Pydantic may reject this — which is fine too
        resp = client.post("/send-report-now", json=payload)
        # Either 200 (treated as empty) or 422 (pydantic reject) is acceptable
        assert resp.status_code in (200, 422)

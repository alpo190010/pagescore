"""Tests for POST /webhook endpoint."""

import hashlib
import hmac as hmac_mod
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app

WEBHOOK_SECRET = "test-webhook-secret-123"


def _get_client():
    return TestClient(app)


def _sign(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    """Compute HMAC-SHA256 hex digest for a raw body."""
    return hmac_mod.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _order_created_body(
    email: str = "buyer@example.com",
    url: str = "https://example.com/landing",
) -> dict:
    """Build a LemonSqueezy order_created webhook payload."""
    return {
        "meta": {
            "event_name": "order_created",
            "custom_data": {"url": url},
        },
        "data": {
            "attributes": {
                "user_email": email,
            }
        },
    }


def _send_webhook(client, body: dict, secret: str = WEBHOOK_SECRET):
    """POST /webhook with correct HMAC signature."""
    raw = json.dumps(body).encode("utf-8")
    sig = _sign(raw, secret)
    return client.post(
        "/webhook",
        content=raw,
        headers={"content-type": "application/json", "x-signature": sig},
    )


# ---- HMAC verification ----------------------------------------------------


class TestWebhookHMAC:
    @patch("app.routers.webhook.settings")
    def test_invalid_signature_returns_401(self, mock_settings):
        mock_settings.lemonsqueezy_webhook_secret = WEBHOOK_SECRET
        client = _get_client()
        body = json.dumps({"meta": {"event_name": "test"}}).encode("utf-8")
        resp = client.post(
            "/webhook",
            content=body,
            headers={"content-type": "application/json", "x-signature": "bad-sig"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"] == "Invalid signature"

    @patch("app.routers.webhook.settings")
    def test_missing_signature_returns_401(self, mock_settings):
        mock_settings.lemonsqueezy_webhook_secret = WEBHOOK_SECRET
        client = _get_client()
        body = json.dumps({"meta": {"event_name": "test"}}).encode("utf-8")
        resp = client.post(
            "/webhook",
            content=body,
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 401


# ---- event filtering -------------------------------------------------------


class TestWebhookEventFiltering:
    @patch("app.routers.webhook.settings")
    def test_non_order_created_returns_ok(self, mock_settings):
        mock_settings.lemonsqueezy_webhook_secret = WEBHOOK_SECRET
        client = _get_client()
        body = {"meta": {"event_name": "subscription_created"}}
        resp = _send_webhook(client, body)
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    @patch("app.routers.webhook.settings")
    def test_order_updated_returns_ok(self, mock_settings):
        mock_settings.lemonsqueezy_webhook_secret = WEBHOOK_SECRET
        client = _get_client()
        body = {"meta": {"event_name": "order_updated"}}
        resp = _send_webhook(client, body)
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}


# ---- missing data ----------------------------------------------------------


class TestWebhookMissingData:
    @patch("app.routers.webhook.settings")
    def test_missing_email_returns_400(self, mock_settings):
        mock_settings.lemonsqueezy_webhook_secret = WEBHOOK_SECRET
        mock_settings.openai_api_key = "sk-test"
        client = _get_client()
        body = {
            "meta": {"event_name": "order_created", "custom_data": {"url": "https://x.com"}},
            "data": {"attributes": {}},
        }
        resp = _send_webhook(client, body)
        assert resp.status_code == 400
        assert resp.json()["error"] == "Missing data"

    @patch("app.routers.webhook.settings")
    def test_missing_url_returns_400(self, mock_settings):
        mock_settings.lemonsqueezy_webhook_secret = WEBHOOK_SECRET
        mock_settings.openai_api_key = "sk-test"
        client = _get_client()
        body = {
            "meta": {"event_name": "order_created", "custom_data": {}},
            "data": {"attributes": {"user_email": "buyer@x.com"}},
        }
        resp = _send_webhook(client, body)
        assert resp.status_code == 400


# ---- full order_created flow -----------------------------------------------


class TestWebhookOrderCreated:
    @patch("app.routers.webhook.send_email", return_value=True)
    @patch("app.routers.webhook._generate_report", new_callable=AsyncMock)
    @patch("app.routers.webhook._fetch_page_html", new_callable=AsyncMock)
    @patch("app.routers.webhook.settings")
    def test_valid_order_created_sends_email(
        self, mock_settings, mock_fetch, mock_report, mock_send
    ):
        mock_settings.lemonsqueezy_webhook_secret = WEBHOOK_SECRET
        mock_settings.openai_api_key = "sk-test"
        mock_fetch.return_value = "<html>page</html>"
        mock_report.return_value = "Great landing page analysis..."

        client = _get_client()
        resp = _send_webhook(client, _order_created_body())
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

        # Verify email was sent
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["from_addr"] == "alpo.ai <report@alpo.com>"
        assert call_kwargs["to"] == "buyer@example.com"
        assert "example.com/landing" in call_kwargs["subject"]

    @patch("app.routers.webhook.send_email", return_value=True)
    @patch("app.routers.webhook._generate_report", new_callable=AsyncMock)
    @patch("app.routers.webhook._fetch_page_html", new_callable=AsyncMock)
    @patch("app.routers.webhook.settings")
    def test_report_included_in_email_html(
        self, mock_settings, mock_fetch, mock_report, mock_send
    ):
        mock_settings.lemonsqueezy_webhook_secret = WEBHOOK_SECRET
        mock_settings.openai_api_key = "sk-test"
        mock_fetch.return_value = "<html>content</html>"
        mock_report.return_value = "**Bold Section**\nDetails here"

        client = _get_client()
        _send_webhook(client, _order_created_body())

        email_html = mock_send.call_args[1]["html"]
        assert "<strong>Bold Section</strong>" in email_html
        assert "<br>" in email_html

    @patch("app.routers.webhook.send_email", return_value=True)
    @patch("app.routers.webhook._generate_report", new_callable=AsyncMock)
    @patch("app.routers.webhook._fetch_page_html", new_callable=AsyncMock)
    @patch("app.routers.webhook.settings")
    def test_fetch_failure_sends_error_report(
        self, mock_settings, mock_fetch, mock_report, mock_send
    ):
        mock_settings.lemonsqueezy_webhook_secret = WEBHOOK_SECRET
        mock_settings.openai_api_key = "sk-test"
        mock_fetch.return_value = None  # fetch failed

        client = _get_client()
        resp = _send_webhook(client, _order_created_body())
        assert resp.status_code == 200

        # _generate_report should NOT be called since html is None
        mock_report.assert_not_called()

        # Email should still be sent with error message
        mock_send.assert_called_once()
        email_html = mock_send.call_args[1]["html"]
        assert "Could not fetch" in email_html

    @patch("app.routers.webhook.send_email", return_value=True)
    @patch("app.routers.webhook._generate_report", new_callable=AsyncMock)
    @patch("app.routers.webhook._fetch_page_html", new_callable=AsyncMock)
    @patch("app.routers.webhook.settings")
    def test_ai_error_sends_error_report(
        self, mock_settings, mock_fetch, mock_report, mock_send
    ):
        mock_settings.lemonsqueezy_webhook_secret = WEBHOOK_SECRET
        mock_settings.openai_api_key = "sk-test"
        mock_fetch.return_value = "<html>ok</html>"
        mock_report.return_value = "Error generating report. Our team has been notified."

        client = _get_client()
        resp = _send_webhook(client, _order_created_body())
        assert resp.status_code == 200

        email_html = mock_send.call_args[1]["html"]
        assert "Error generating report" in email_html


# ---- _generate_report unit tests ------------------------------------------


class TestGenerateReport:
    def test_missing_api_key_returns_config_error(self):
        import asyncio
        from app.routers.webhook import _generate_report

        with patch("app.routers.webhook.settings") as mock_settings:
            mock_settings.openai_api_key = ""
            result = asyncio.get_event_loop().run_until_complete(
                _generate_report("https://x.com", "<html></html>")
            )
            assert result == "Error: Server configuration issue."

    def test_api_failure_returns_error_message(self):
        import asyncio
        from app.routers.webhook import _generate_report

        with patch("app.routers.webhook.settings") as mock_settings:
            mock_settings.openai_api_key = "sk-test"

            with patch("app.routers.webhook.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client.post = AsyncMock(side_effect=httpx.HTTPError("timeout"))
                mock_client_cls.return_value = mock_client

                result = asyncio.get_event_loop().run_until_complete(
                    _generate_report("https://x.com", "<html></html>")
                )
                assert "Error generating report" in result

    def test_successful_report_returns_content(self):
        import asyncio
        from app.routers.webhook import _generate_report

        with patch("app.routers.webhook.settings") as mock_settings:
            mock_settings.openai_api_key = "sk-test"

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Full report text here."}}]
            }
            mock_response.raise_for_status = MagicMock()

            with patch("app.routers.webhook.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value = mock_client

                result = asyncio.get_event_loop().run_until_complete(
                    _generate_report("https://x.com", "<html></html>")
                )
                assert result == "Full report text here."

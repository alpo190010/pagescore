"""Tests for the PageSpeed Insights API client: _parse_response and fetch_pagespeed_insights."""

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.page_speed_api import fetch_pagespeed_insights, _parse_response


# ---------------------------------------------------------------------------
# Helper: realistic mock PSI response
# ---------------------------------------------------------------------------


def _mock_psi_response(
    perf_score=0.85,
    lcp=2400,
    cls=0.08,
    tbt=150,
    fcp=1200,
    si=2000,
    with_field=False,
):
    response = {
        "lighthouseResult": {
            "categories": {"performance": {"score": perf_score}},
            "audits": {
                "largest-contentful-paint": {"numericValue": lcp},
                "cumulative-layout-shift": {"numericValue": cls},
                "total-blocking-time": {"numericValue": tbt},
                "first-contentful-paint": {"numericValue": fcp},
                "speed-index": {"numericValue": si},
            },
        },
    }
    if with_field:
        response["loadingExperience"] = {
            "metrics": {
                "LARGEST_CONTENTFUL_PAINT_MS": {"percentile": 2800},
                "CUMULATIVE_LAYOUT_SHIFT_SCORE": {"percentile": 12},
            }
        }
    return response


# ---------------------------------------------------------------------------
# _parse_response — synchronous, no mocking needed
# ---------------------------------------------------------------------------


class TestParseResponse:
    """Unit tests for _parse_response."""

    def test_parse_valid_response(self):
        data = _mock_psi_response()
        result = _parse_response(data, "https://example.com")

        assert result is not None
        assert result["performance_score"] == 85
        assert result["lcp_ms"] == 2400.0
        assert result["cls_value"] == 0.08
        assert result["tbt_ms"] == 150.0
        assert result["fcp_ms"] == 1200.0
        assert result["speed_index_ms"] == 2000.0
        assert result["has_field_data"] is False
        assert result["field_lcp_ms"] is None
        assert result["field_cls_value"] is None

    def test_parse_missing_lighthouse_returns_none(self):
        data = {"someOtherKey": {}}
        result = _parse_response(data, "https://example.com")
        assert result is None

    def test_parse_missing_audit_returns_none(self):
        data = {
            "lighthouseResult": {
                "categories": {"performance": {"score": 0.9}},
                "audits": {
                    "largest-contentful-paint": {"numericValue": 2400},
                    # missing cumulative-layout-shift and others
                },
            },
        }
        result = _parse_response(data, "https://example.com")
        assert result is None

    def test_parse_with_field_data(self):
        data = _mock_psi_response(with_field=True)
        result = _parse_response(data, "https://example.com")

        assert result is not None
        assert result["has_field_data"] is True
        assert result["field_lcp_ms"] == 2800.0
        assert result["field_cls_value"] == 0.12

    def test_parse_without_field_data(self):
        data = _mock_psi_response(with_field=False)
        result = _parse_response(data, "https://example.com")

        assert result is not None
        assert result["has_field_data"] is False
        assert result["field_lcp_ms"] is None
        assert result["field_cls_value"] is None

    def test_cls_field_divided_by_100(self):
        data = _mock_psi_response(with_field=True)
        # Override the CLS percentile to 15 for this test
        data["loadingExperience"]["metrics"]["CUMULATIVE_LAYOUT_SHIFT_SCORE"]["percentile"] = 15

        result = _parse_response(data, "https://example.com")
        assert result["field_cls_value"] == 0.15


# ---------------------------------------------------------------------------
# fetch_pagespeed_insights — async, requires mocking httpx
# ---------------------------------------------------------------------------


class TestFetchPagespeedInsights:
    """Integration tests for fetch_pagespeed_insights with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_empty_api_key_returns_none(self):
        with patch("app.services.page_speed_api.httpx.AsyncClient") as mock_cls:
            result = await fetch_pagespeed_insights("https://example.com", "")
            mock_cls.assert_not_called()
        assert result is None

    @pytest.mark.asyncio
    async def test_successful_fetch(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = _mock_psi_response()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("app.services.page_speed_api.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_pagespeed_insights("https://example.com", "test-key")

        assert result is not None
        assert result["performance_score"] == 85
        assert result["lcp_ms"] == 2400.0

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self):
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("timed out")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("app.services.page_speed_api.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_pagespeed_insights("https://example.com", "test-key")

        assert result is None

    @pytest.mark.asyncio
    async def test_http_error_returns_none(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Too Many Requests"

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "rate limited",
            request=MagicMock(),
            response=mock_resp,
        )
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("app.services.page_speed_api.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_pagespeed_insights("https://example.com", "test-key")

        assert result is None

    @pytest.mark.asyncio
    async def test_network_error_returns_none(self):
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("connection refused")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("app.services.page_speed_api.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_pagespeed_insights("https://example.com", "test-key")

        assert result is None

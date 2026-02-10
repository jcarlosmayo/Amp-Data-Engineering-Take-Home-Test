"""Tests for tomorrow.api_client — HTTP retry logic with mocked requests."""

from unittest.mock import MagicMock, patch

import pytest
from tenacity import RetryError, wait_none

from tomorrow.api_client import RateLimitError, TomorrowIOClient


class TestMakeRequest:
    def _make_client(self):
        """Create a client with retry waits disabled for fast tests."""
        client = TomorrowIOClient(api_key="test-key")
        client._make_request.retry.wait = wait_none()
        return client

    def test_returns_json_on_success(self):
        client = self._make_client()
        expected = {"timelines": {"hourly": []}}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.get_forecast(latitude=25.86, longitude=-97.42)

        assert result == expected

    def test_retries_three_times_on_429(self):
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "3600"}

        with patch.object(client.session, "get", return_value=mock_response):
            with pytest.raises(RetryError) as exc_info:
                client.get_forecast(latitude=25.86, longitude=-97.42)

            assert client.session.get.call_count == 3
            inner = exc_info.value.last_attempt.exception()
            assert isinstance(inner, RateLimitError)
            assert inner.retry_after == 3600

    def test_retries_then_succeeds(self):
        client = self._make_client()

        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_429.headers = {"Retry-After": "60"}

        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = {"timelines": {"hourly": []}}
        mock_200.raise_for_status = MagicMock()

        with patch.object(client.session, "get", side_effect=[mock_429, mock_200]) as mock_get:
            result = client.get_forecast(latitude=25.86, longitude=-97.42)

            assert result == {"timelines": {"hourly": []}}
            assert mock_get.call_count == 2

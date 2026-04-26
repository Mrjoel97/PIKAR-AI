"""Unit tests for Slack response_url SSRF prevention.

Validates that the `_is_valid_slack_response_url` helper and the
`_process_slack_block_action` handler prevent Server-Side Request
Forgery (SSRF) by rejecting non-Slack domains before any outbound POST.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Unit tests for _is_valid_slack_response_url helper
# ---------------------------------------------------------------------------


class TestIsValidSlackResponseUrl:
    """Tests for the URL allowlist validator."""

    def _get_validator(self):
        """Import validator from module under test."""
        from app.routers.webhooks import _is_valid_slack_response_url

        return _is_valid_slack_response_url

    def test_valid_hooks_slack_com(self):
        """Standard Slack webhook URL passes validation."""
        fn = self._get_validator()
        assert fn("https://hooks.slack.com/actions/T123/456/abc") is True

    def test_valid_api_slack_com(self):
        """API subdomain URL passes validation."""
        fn = self._get_validator()
        assert fn("https://api.slack.com/webhook/response") is True

    def test_evil_domain_rejected(self):
        """Attacker-controlled domain must be rejected."""
        fn = self._get_validator()
        assert fn("https://evil.com/steal") is False

    def test_subdomain_spoofing_rejected(self):
        """hooks.slack.com.evil.com must not pass (suffix spoofing)."""
        fn = self._get_validator()
        assert fn("https://hooks.slack.com.evil.com/attack") is False

    def test_empty_url_rejected(self):
        """Empty string must return False (not raise)."""
        fn = self._get_validator()
        assert fn("") is False

    def test_http_non_https_rejected(self):
        """Non-HTTPS URL to Slack domain must be rejected."""
        fn = self._get_validator()
        assert fn("http://hooks.slack.com/actions/T123") is False

    def test_arbitrary_subdomain_of_slack_com_allowed(self):
        """Any legitimate *.slack.com subdomain should be allowed."""
        fn = self._get_validator()
        assert fn("https://myteam.slack.com/webhook/123") is True


# ---------------------------------------------------------------------------
# Integration-level test: evil URL never reaches httpx.AsyncClient.post
# ---------------------------------------------------------------------------


class TestProcessSlackBlockActionSsrfGuard:
    """Ensure the async handler never calls httpx for non-Slack URLs."""

    @pytest.mark.asyncio
    async def test_evil_response_url_never_posts(self):
        """An attacker-supplied response_url must not trigger an outbound POST."""
        evil_payload = {
            "actions": [{"value": "APPROVED:sometoken123"}],
            "user": {"name": "attacker"},
            "response_url": "https://evil.com/capture",
        }

        # Patch DB client so the handler doesn't need a real Supabase connection
        mock_result = MagicMock()
        mock_result.data = []

        with patch(
            "app.routers.webhooks.get_service_client"
        ) as mock_get_client, patch(
            "app.routers.webhooks.execute_async", new_callable=AsyncMock
        ) as mock_exec, patch(
            "httpx.AsyncClient"
        ) as mock_httpx_cls:
            mock_get_client.return_value = MagicMock()
            mock_exec.return_value = mock_result
            mock_http_instance = AsyncMock()
            mock_httpx_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_http_instance
            )
            mock_httpx_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            from app.routers.webhooks import _process_slack_block_action

            await _process_slack_block_action(evil_payload)

            # The mock http client's post method must never have been called
            mock_http_instance.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_valid_slack_url_does_post(self):
        """A legitimate Slack response_url should reach the outbound POST."""
        valid_payload = {
            "actions": [{"value": "APPROVED:sometoken456"}],
            "user": {"name": "legit_user"},
            "response_url": "https://hooks.slack.com/actions/T123/456/abc",
        }

        mock_result = MagicMock()
        mock_result.data = [{"id": "row1"}]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch(
            "app.routers.webhooks.get_service_client"
        ) as mock_get_client, patch(
            "app.routers.webhooks.execute_async", new_callable=AsyncMock
        ) as mock_exec, patch(
            "httpx.AsyncClient"
        ) as mock_httpx_cls:
            mock_get_client.return_value = MagicMock()
            mock_exec.return_value = mock_result

            mock_http_instance = AsyncMock()
            mock_http_instance.post = AsyncMock(return_value=mock_response)
            mock_httpx_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_http_instance
            )
            mock_httpx_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            from app.routers.webhooks import _process_slack_block_action

            await _process_slack_block_action(valid_payload)

            # Post should have been called with the valid Slack URL
            mock_http_instance.post.assert_called_once()
            call_args = mock_http_instance.post.call_args
            assert "hooks.slack.com" in call_args[0][0]

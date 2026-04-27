# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for SupabaseSessionService circuit breaker and 5xx retry resilience.

Covers:
- _execute_with_retry retries httpx.HTTPStatusError with status >= 500
- _execute_with_retry does NOT retry httpx.HTTPStatusError with status < 500
- _execute_with_retry still retries network-level errors (ConnectError, ReadTimeout)
- Circuit breaker open state causes fast-fail with graceful degradation
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


def _make_session_service():
    """Instantiate SupabaseSessionService with cache mocked out."""
    from unittest.mock import MagicMock

    with patch("app.persistence.supabase_session_service.get_cache_service") as mock_cache:
        mock_cache.return_value = MagicMock()
        from app.persistence.supabase_session_service import SupabaseSessionService

        svc = SupabaseSessionService()
        svc._cache = MagicMock()
        svc._cache.get_session_metadata = AsyncMock(return_value=MagicMock(found=False))
        svc._cache.set_session_metadata = AsyncMock()
        svc._cache.invalidate_session = AsyncMock()
        return svc


def _make_http_status_error(status_code: int) -> httpx.HTTPStatusError:
    """Build an httpx.HTTPStatusError with the given status code."""
    response = MagicMock()
    response.status_code = status_code
    request = MagicMock()
    return httpx.HTTPStatusError(
        message=f"HTTP {status_code}",
        request=request,
        response=response,
    )


# ---------------------------------------------------------------------------
# _execute_with_retry — 5xx retry behaviour
# ---------------------------------------------------------------------------


class TestExecuteWithRetry5xx:
    """Test that _execute_with_retry retries on Supabase HTTP 5xx responses."""

    @pytest.mark.asyncio
    async def test_retries_on_500_then_succeeds(self):
        """Should retry when Supabase returns 500 and succeed on the next attempt."""
        svc = _make_session_service()

        error = _make_http_status_error(500)
        success_result = MagicMock()
        success_result.data = [{"id": "session-1"}]

        call_count = 0

        async def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise error
            return success_result

        qb = MagicMock()
        qb.execute = mock_execute

        with patch(
            "app.persistence.supabase_session_service.supabase_circuit_breaker"
        ) as mock_cb:
            mock_cb.should_allow_request = AsyncMock(return_value=True)
            mock_cb.record_success = AsyncMock()
            mock_cb.record_failure = AsyncMock()

            result = await svc._execute_with_retry(qb, max_retries=3)

        assert result is success_result
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retries_exhaust_on_repeated_500(self):
        """After max_retries attempts with 500, should raise and record failure."""
        svc = _make_session_service()

        error = _make_http_status_error(500)

        async def always_fail():
            raise error

        qb = MagicMock()
        qb.execute = always_fail

        with patch(
            "app.persistence.supabase_session_service.supabase_circuit_breaker"
        ) as mock_cb:
            mock_cb.should_allow_request = AsyncMock(return_value=True)
            mock_cb.record_success = AsyncMock()
            mock_cb.record_failure = AsyncMock()

            with pytest.raises(httpx.HTTPStatusError):
                await svc._execute_with_retry(qb, max_retries=3)

        # Failure should be recorded once after exhausting retries
        mock_cb.record_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_does_not_retry_on_400(self):
        """4xx (client errors) should be raised immediately without retrying."""
        svc = _make_session_service()

        error = _make_http_status_error(400)
        call_count = 0

        async def mock_execute():
            nonlocal call_count
            call_count += 1
            raise error

        qb = MagicMock()
        qb.execute = mock_execute

        with patch(
            "app.persistence.supabase_session_service.supabase_circuit_breaker"
        ) as mock_cb:
            mock_cb.should_allow_request = AsyncMock(return_value=True)
            mock_cb.record_success = AsyncMock()
            mock_cb.record_failure = AsyncMock()

            with pytest.raises(httpx.HTTPStatusError):
                await svc._execute_with_retry(qb, max_retries=3)

        # Should only call execute once (no retries for 4xx)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_does_not_retry_on_404(self):
        """404 (client error) should be raised immediately without retrying."""
        svc = _make_session_service()

        error = _make_http_status_error(404)
        call_count = 0

        async def mock_execute():
            nonlocal call_count
            call_count += 1
            raise error

        qb = MagicMock()
        qb.execute = mock_execute

        with patch(
            "app.persistence.supabase_session_service.supabase_circuit_breaker"
        ) as mock_cb:
            mock_cb.should_allow_request = AsyncMock(return_value=True)
            mock_cb.record_success = AsyncMock()
            mock_cb.record_failure = AsyncMock()

            with pytest.raises(httpx.HTTPStatusError):
                await svc._execute_with_retry(qb, max_retries=3)

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_still_retries_connect_error(self):
        """ConnectError (network) should still be retried (existing behaviour)."""
        svc = _make_session_service()

        success_result = MagicMock()
        success_result.data = []
        call_count = 0

        async def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("connection refused")
            return success_result

        qb = MagicMock()
        qb.execute = mock_execute

        with patch(
            "app.persistence.supabase_session_service.supabase_circuit_breaker"
        ) as mock_cb:
            mock_cb.should_allow_request = AsyncMock(return_value=True)
            mock_cb.record_success = AsyncMock()
            mock_cb.record_failure = AsyncMock()

            result = await svc._execute_with_retry(qb, max_retries=3)

        assert result is success_result
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_still_retries_read_timeout(self):
        """ReadTimeout (network) should still be retried (existing behaviour)."""
        svc = _make_session_service()

        success_result = MagicMock()
        call_count = 0

        async def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ReadTimeout("timeout", request=MagicMock())
            return success_result

        qb = MagicMock()
        qb.execute = mock_execute

        with patch(
            "app.persistence.supabase_session_service.supabase_circuit_breaker"
        ) as mock_cb:
            mock_cb.should_allow_request = AsyncMock(return_value=True)
            mock_cb.record_success = AsyncMock()
            mock_cb.record_failure = AsyncMock()

            result = await svc._execute_with_retry(qb, max_retries=3)

        assert result is success_result
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_records_success_on_successful_query(self):
        """Successful query should call record_success on the circuit breaker."""
        svc = _make_session_service()

        success_result = MagicMock()

        async def mock_execute():
            return success_result

        qb = MagicMock()
        qb.execute = mock_execute

        with patch(
            "app.persistence.supabase_session_service.supabase_circuit_breaker"
        ) as mock_cb:
            mock_cb.should_allow_request = AsyncMock(return_value=True)
            mock_cb.record_success = AsyncMock()
            mock_cb.record_failure = AsyncMock()

            await svc._execute_with_retry(qb, max_retries=3)

        mock_cb.record_success.assert_called_once()
        mock_cb.record_failure.assert_not_called()


# ---------------------------------------------------------------------------
# Circuit breaker open state — method-level graceful degradation
# ---------------------------------------------------------------------------


class TestCircuitBreakerOpenState:
    """Test per-method behaviour when Supabase circuit breaker is open."""

    @pytest.mark.asyncio
    async def test_execute_with_retry_fails_fast_when_cb_open(self):
        """_execute_with_retry should raise immediately when circuit breaker is open."""
        svc = _make_session_service()

        call_count = 0

        async def mock_execute():
            nonlocal call_count
            call_count += 1
            return MagicMock()

        qb = MagicMock()
        qb.execute = mock_execute

        with patch(
            "app.persistence.supabase_session_service.supabase_circuit_breaker"
        ) as mock_cb:
            mock_cb.should_allow_request = AsyncMock(return_value=False)
            mock_cb.record_success = AsyncMock()
            mock_cb.record_failure = AsyncMock()

            with pytest.raises(Exception, match="circuit breaker"):
                await svc._execute_with_retry(qb, max_retries=3)

        # execute() should never have been called
        assert call_count == 0

    @pytest.mark.asyncio
    async def test_get_session_returns_empty_when_cb_open(self):
        """get_session should return an empty Session when circuit breaker is open."""
        from google.adk.sessions import Session

        svc = _make_session_service()

        with patch(
            "app.persistence.supabase_session_service.supabase_circuit_breaker"
        ) as mock_cb:
            mock_cb.should_allow_request = AsyncMock(return_value=False)
            mock_cb.record_success = AsyncMock()
            mock_cb.record_failure = AsyncMock()

            # _get_client is needed so mock it too
            svc._get_client = AsyncMock(return_value=MagicMock())

            result = await svc.get_session(
                app_name="test-app",
                user_id="user-123",
                session_id="session-abc",
            )

        assert result is not None
        assert isinstance(result, Session)
        assert result.id == "session-abc"
        assert result.state == {}
        assert result.events == []

    @pytest.mark.asyncio
    async def test_create_session_raises_when_cb_open(self):
        """create_session (write) should raise when circuit breaker is open."""
        svc = _make_session_service()

        with patch(
            "app.persistence.supabase_session_service.supabase_circuit_breaker"
        ) as mock_cb:
            mock_cb.should_allow_request = AsyncMock(return_value=False)
            mock_cb.record_success = AsyncMock()
            mock_cb.record_failure = AsyncMock()

            svc._get_client = AsyncMock(return_value=MagicMock())

            with pytest.raises(Exception):
                await svc.create_session(
                    app_name="test-app",
                    user_id="user-123",
                    session_id="session-new",
                    state={},
                )

    @pytest.mark.asyncio
    async def test_append_event_raises_when_cb_open(self):
        """append_event (write) should raise when circuit breaker is open."""
        from unittest.mock import MagicMock

        from google.adk.events import Event
        from google.adk.sessions import Session

        svc = _make_session_service()

        session = Session(
            app_name="test-app",
            user_id="user-123",
            id="session-abc",
            state={},
            events=[],
        )
        event = MagicMock(spec=Event)
        event.model_dump = MagicMock(return_value={})

        with patch(
            "app.persistence.supabase_session_service.supabase_circuit_breaker"
        ) as mock_cb:
            mock_cb.should_allow_request = AsyncMock(return_value=False)
            mock_cb.record_success = AsyncMock()
            mock_cb.record_failure = AsyncMock()

            svc._get_client = AsyncMock(return_value=MagicMock())

            with pytest.raises(Exception):
                await svc.append_event(session=session, event=event)

    @pytest.mark.asyncio
    async def test_update_state_raises_when_cb_open(self):
        """update_state (write) should raise when circuit breaker is open."""
        svc = _make_session_service()

        with patch(
            "app.persistence.supabase_session_service.supabase_circuit_breaker"
        ) as mock_cb:
            mock_cb.should_allow_request = AsyncMock(return_value=False)
            mock_cb.record_success = AsyncMock()
            mock_cb.record_failure = AsyncMock()

            svc._get_client = AsyncMock(return_value=MagicMock())

            with pytest.raises(Exception):
                await svc.update_state(
                    app_name="test-app",
                    user_id="user-123",
                    session_id="session-abc",
                    state_updates={"key": "value"},
                )

    @pytest.mark.asyncio
    async def test_list_sessions_returns_empty_when_cb_open(self):
        """list_sessions should return empty list when circuit breaker is open."""
        svc = _make_session_service()

        with patch(
            "app.persistence.supabase_session_service.supabase_circuit_breaker"
        ) as mock_cb:
            mock_cb.should_allow_request = AsyncMock(return_value=False)
            mock_cb.record_success = AsyncMock()
            mock_cb.record_failure = AsyncMock()

            svc._get_client = AsyncMock(return_value=MagicMock())

            result = await svc.list_sessions(
                app_name="test-app",
                user_id="user-123",
            )

        assert result == []

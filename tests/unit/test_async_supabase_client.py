"""Unit tests for async Supabase client, execute_async, circuit breaker, and async base services."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Task 1 tests: AsyncSupabaseService singleton with connection-pooled httpx
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_async_singleton():
    """Reset the async singleton before each test."""
    from app.services import supabase_client as mod

    # Clear any existing async singleton
    if hasattr(mod, "AsyncSupabaseService"):
        mod.AsyncSupabaseService._instance = None
        mod.AsyncSupabaseService._client = None
    yield
    # Teardown: clear again
    if hasattr(mod, "AsyncSupabaseService"):
        mod.AsyncSupabaseService._instance = None
        mod.AsyncSupabaseService._client = None


@pytest.fixture(autouse=True)
def _clear_sync_singleton():
    """Reset the sync singleton before each test."""
    from app.services import supabase_client as mod

    if hasattr(mod, "SupabaseService"):
        mod.SupabaseService._instance = None
        mod.SupabaseService._client = None
    if hasattr(mod, "get_supabase_service"):
        mod.get_supabase_service.cache_clear()
    yield
    if hasattr(mod, "SupabaseService"):
        mod.SupabaseService._instance = None
        mod.SupabaseService._client = None
    if hasattr(mod, "get_supabase_service"):
        mod.get_supabase_service.cache_clear()


@pytest.fixture()
def _env_vars(monkeypatch):
    """Set required env vars for Supabase client creation."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")


class TestAsyncSupabaseService:
    """Tests for the AsyncSupabaseService singleton."""

    @pytest.mark.asyncio
    async def test_get_async_service_returns_instance(self, _env_vars):
        """get_async_service() returns an AsyncSupabaseService instance."""
        mock_async_client = AsyncMock()
        with patch(
            "app.services.supabase_client.create_async_client",
            new_callable=AsyncMock,
            return_value=mock_async_client,
        ):
            from app.services.supabase_client import (
                AsyncSupabaseService,
                get_async_service,
            )

            service = await get_async_service()
            assert isinstance(service, AsyncSupabaseService)

    @pytest.mark.asyncio
    async def test_get_async_client_returns_async_client(self, _env_vars):
        """get_async_client() returns the async client (not sync Client)."""
        mock_async_client = AsyncMock()
        with patch(
            "app.services.supabase_client.create_async_client",
            new_callable=AsyncMock,
            return_value=mock_async_client,
        ):
            from app.services.supabase_client import get_async_client

            client = await get_async_client()
            assert client is mock_async_client

    @pytest.mark.asyncio
    async def test_async_service_is_singleton(self, _env_vars):
        """Calling get_async_service() twice returns the same instance."""
        mock_async_client = AsyncMock()
        with patch(
            "app.services.supabase_client.create_async_client",
            new_callable=AsyncMock,
            return_value=mock_async_client,
        ):
            from app.services.supabase_client import get_async_service

            service1 = await get_async_service()
            service2 = await get_async_service()
            assert service1 is service2

    @pytest.mark.asyncio
    async def test_httpx_async_client_has_correct_limits(self, _env_vars):
        """The underlying httpx.AsyncClient has correct connection limits."""
        captured_httpx_kwargs = {}

        original_async_client = None

        class FakeAsyncClient:
            def __init__(self, **kwargs):
                nonlocal original_async_client
                captured_httpx_kwargs.update(kwargs)
                original_async_client = self

        with (
            patch("app.services.supabase_client.httpx.AsyncClient", FakeAsyncClient),
            patch(
                "app.services.supabase_client.create_async_client",
                new_callable=AsyncMock,
                return_value=AsyncMock(),
            ),
        ):
            from app.services.supabase_client import get_async_service

            await get_async_service()
            limits = captured_httpx_kwargs.get("limits")
            assert limits is not None
            assert limits.max_connections == 200
            assert limits.max_keepalive_connections == 50

    @pytest.mark.asyncio
    async def test_get_client_still_returns_sync(self, _env_vars):
        """get_client() still returns a sync Client (backward compat)."""
        with patch(
            "app.services.supabase_client.create_client",
        ) as mock_create:
            mock_sync_client = MagicMock()
            mock_create.return_value = mock_sync_client

            from app.services.supabase_client import SupabaseService

            # Reset sync singleton too
            SupabaseService._instance = None
            SupabaseService._client = None

            from app.services.supabase_client import get_client

            client = get_client()
            assert client is mock_sync_client

            # Cleanup
            SupabaseService._instance = None
            SupabaseService._client = None

    @pytest.mark.asyncio
    async def test_invalidate_client_clears_async_singleton(self, _env_vars):
        """invalidate_client() clears both sync and async singletons."""
        mock_async_client = AsyncMock()
        with (
            patch(
                "app.services.supabase_client.create_async_client",
                new_callable=AsyncMock,
                return_value=mock_async_client,
            ),
            patch("app.services.supabase_client.create_client"),
        ):
            from app.services.supabase_client import (
                AsyncSupabaseService,
                get_async_service,
                invalidate_client,
            )

            await get_async_service()
            assert AsyncSupabaseService._instance is not None

            invalidate_client()
            assert AsyncSupabaseService._instance is None

    @pytest.mark.asyncio
    async def test_get_async_anon_client_returns_async_client(self, _env_vars):
        """get_async_anon_client() returns an AsyncClient with anon key."""
        mock_anon_client = AsyncMock()
        mock_service_client = AsyncMock()

        call_count = 0

        async def fake_create(url, key, options=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_service_client
            return mock_anon_client

        with patch(
            "app.services.supabase_client.create_async_client",
            side_effect=fake_create,
        ):
            from app.services.supabase_client import get_async_anon_client

            anon_client = await get_async_anon_client()
            assert anon_client is mock_anon_client

    @pytest.mark.asyncio
    async def test_async_service_strips_env_whitespace(self, monkeypatch):
        """Async service trims newline-contaminated env values before use."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co\r\n")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-key\r\n")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key\r\n")

        mock_async_client = AsyncMock()
        with patch(
            "app.services.supabase_client.create_async_client",
            new_callable=AsyncMock,
            return_value=mock_async_client,
        ) as create_async_client_mock:
            from app.services.supabase_client import AsyncSupabaseService

            service = await AsyncSupabaseService.get_instance()

        assert create_async_client_mock.await_args.args[:2] == (
            "https://test.supabase.co",
            "test-service-key",
        )
        assert service._anon_key == "test-anon-key"


def test_sync_service_strips_env_whitespace(monkeypatch):
    """Sync service trims newline-contaminated env values before use."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co\r\n")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-key\r\n")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key\r\n")

    mock_client = MagicMock()
    with patch(
        "app.services.supabase_client.create_client", return_value=mock_client
    ) as create_client_mock:
        from app.services.supabase_client import SupabaseService

        service = SupabaseService()

    assert create_client_mock.call_args.args[:2] == (
        "https://test.supabase.co",
        "test-service-key",
    )
    assert service._anon_key == "test-anon-key"


# ---------------------------------------------------------------------------
# Task 2 tests: execute_async, circuit breaker, and async base services
# ---------------------------------------------------------------------------


class TestExecuteAsync:
    """Tests for the upgraded execute_async function."""

    @pytest.mark.asyncio
    async def test_execute_async_awaits_directly_no_to_thread(self):
        """execute_async calls query_builder.execute() directly (no asyncio.to_thread) for async builders."""
        from app.services.supabase_async import execute_async

        # Create a query builder whose .execute() returns a coroutine
        mock_result = MagicMock(data=[{"id": 1}])

        async def async_execute():
            return mock_result

        query_builder = MagicMock()
        query_builder.execute = MagicMock(return_value=async_execute())

        with patch("app.services.supabase_async.asyncio.to_thread") as mock_to_thread:
            result = await execute_async(query_builder)
            assert result is mock_result
            mock_to_thread.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_async_supports_timeout(self):
        """execute_async still supports timeout via asyncio.wait_for."""
        from app.services.supabase_async import execute_async

        mock_result = MagicMock(data=[{"id": 1}])

        async def async_execute():
            return mock_result

        query_builder = MagicMock()
        query_builder.execute = MagicMock(return_value=async_execute())

        result = await execute_async(query_builder, timeout=5.0)
        assert result is mock_result

    @pytest.mark.asyncio
    async def test_execute_async_raises_timeout_error(self):
        """execute_async raises asyncio.TimeoutError when timeout exceeded."""
        from app.services.supabase_async import execute_async

        async def slow_execute():
            await asyncio.sleep(10)

        query_builder = MagicMock()
        query_builder.execute = MagicMock(return_value=slow_execute())

        with pytest.raises(asyncio.TimeoutError):
            await execute_async(query_builder, timeout=0.01)


class TestAsyncCircuitBreaker:
    """Tests for the async-compatible circuit breaker."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_uses_asyncio_lock(self):
        """SupabaseCircuitBreaker uses asyncio.Lock for state transitions."""
        from app.services.supabase_resilience import SupabaseCircuitBreaker

        breaker = SupabaseCircuitBreaker()
        assert isinstance(breaker._state_lock, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_with_supabase_resilience_works_with_async(self):
        """with_supabase_resilience decorator works with native async functions."""
        from app.services.supabase_resilience import (
            supabase_circuit_breaker,
            with_supabase_resilience,
        )

        await supabase_circuit_breaker.reset()

        @with_supabase_resilience(default_return=[])
        async def fetch_data():
            return [{"id": 1}]

        result = await fetch_data()
        assert result == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_threshold(self):
        """Circuit breaker opens after FAILURE_THRESHOLD consecutive failures."""
        from app.services.supabase_resilience import (
            SB_CB_FAILURE_THRESHOLD,
            supabase_circuit_breaker,
        )

        await supabase_circuit_breaker.reset()
        for _ in range(SB_CB_FAILURE_THRESHOLD):
            await supabase_circuit_breaker.record_failure(Exception("test"))

        status = await supabase_circuit_breaker.get_status()
        assert status["state"] == "open"

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_after_recovery(self):
        """Circuit breaker transitions from open to half_open after recovery timeout."""
        from app.services.supabase_resilience import (
            SB_CB_FAILURE_THRESHOLD,
            supabase_circuit_breaker,
        )

        await supabase_circuit_breaker.reset()
        for _ in range(SB_CB_FAILURE_THRESHOLD):
            await supabase_circuit_breaker.record_failure(Exception("test"))

        # Simulate recovery timeout elapsed
        supabase_circuit_breaker._last_failure_time = time.time() - 60

        allowed = await supabase_circuit_breaker.should_allow_request()
        assert allowed is True
        status = await supabase_circuit_breaker.get_status()
        assert status["state"] == "half_open"


class TestAsyncBaseService:
    """Tests for AsyncBaseService and AsyncAdminService."""

    @pytest.mark.asyncio
    async def test_async_base_service_execute_no_to_thread(self, _env_vars):
        """AsyncBaseService.execute() calls execute_async without asyncio.to_thread."""
        from app.services.base_service import AsyncBaseService

        mock_result = MagicMock(data=[{"id": 1}])

        async def async_execute():
            return mock_result

        query_builder = MagicMock()
        query_builder.execute = MagicMock(return_value=async_execute())

        service = AsyncBaseService(user_token="test-token")

        with patch("app.services.base_service.execute_async") as mock_exec_async:
            mock_exec_async.return_value = mock_result
            result = await service.execute(query_builder, op_name="test")
            mock_exec_async.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_async_admin_service_provides_async_client(self, _env_vars):
        """AsyncAdminService provides async client with service role key."""
        mock_async_client = AsyncMock()
        with patch(
            "app.services.base_service.get_async_client",
            new_callable=AsyncMock,
            return_value=mock_async_client,
        ):
            from app.services.base_service import AsyncAdminService

            service = AsyncAdminService()
            client = await service.get_client()
            assert client is mock_async_client

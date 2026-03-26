"""Unit tests for async Supabase client, execute_async, circuit breaker, and async base services."""

from __future__ import annotations

import asyncio
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

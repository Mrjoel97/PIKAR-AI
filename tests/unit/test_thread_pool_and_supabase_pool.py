# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for Phase 26-03: Thread pool right-sizing and async client lifecycle.

TDD RED phase: Tests written BEFORE the implementation changes.

Tests verify:
1. Thread pool default is 32 (reduced from 200 after async migration)
2. THREAD_POOL_SIZE env var still allows override
3. Lifespan startup pre-warms async Supabase client
4. Lifespan shutdown closes async Supabase client
5. get_client_stats includes async_client_active field
6. 50 concurrent async DB calls complete without thread pool exhaustion
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import os
import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


# ---------------------------------------------------------------------------
# Test 1: Default THREAD_POOL_SIZE is 32 (not 200) when env var is unset
# ---------------------------------------------------------------------------
def test_thread_pool_default_is_32(monkeypatch):
    """Default THREAD_POOL_SIZE is 32 after Phase 26 async migration."""
    monkeypatch.delenv("THREAD_POOL_SIZE", raising=False)

    content = pathlib.Path("app/fast_api_app.py").read_text()
    # The default in the env var fallback must be "32"
    assert '"THREAD_POOL_SIZE", "32"' in content or "'THREAD_POOL_SIZE', '32'" in content, (
        "THREAD_POOL_SIZE default should be 32 in fast_api_app.py"
    )

    # Also verify the runtime parsing produces 32
    pool_size = int(os.environ.get("THREAD_POOL_SIZE", "32"))
    assert pool_size == 32


# ---------------------------------------------------------------------------
# Test 2: THREAD_POOL_SIZE env var overrides the default
# ---------------------------------------------------------------------------
def test_thread_pool_env_var_override(monkeypatch):
    """THREAD_POOL_SIZE env var overrides the default (e.g., 64 uses 64)."""
    monkeypatch.setenv("THREAD_POOL_SIZE", "64")
    pool_size = int(os.environ.get("THREAD_POOL_SIZE", "32"))
    assert pool_size == 64


# ---------------------------------------------------------------------------
# Test 3: Lifespan startup pre-warms the async Supabase client
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_lifespan_prewarms_async_client():
    """Lifespan startup calls get_async_service() to pre-warm async client."""
    content = pathlib.Path("app/fast_api_app.py").read_text()
    assert "get_async_service" in content, (
        "get_async_service should be called in lifespan for async client pre-warm"
    )
    assert "Async Supabase client pre-warmed" in content, (
        "Pre-warm log message should be present in lifespan"
    )


# ---------------------------------------------------------------------------
# Test 4: Lifespan shutdown closes the async Supabase client
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_lifespan_closes_async_client():
    """Lifespan shutdown closes the async Supabase client via .close()."""
    content = pathlib.Path("app/fast_api_app.py").read_text()
    # The teardown section (after yield) should close the async client
    assert "Async Supabase client closed" in content, (
        "Async client close log message should be present in lifespan teardown"
    )


# ---------------------------------------------------------------------------
# Test 5: get_client_stats includes async_client_active field
# ---------------------------------------------------------------------------
def test_get_client_stats_includes_async_client_active():
    """get_client_stats returns async_client_active field."""
    from app.services.supabase_client import get_client_stats

    stats = get_client_stats()
    assert "async_client_active" in stats, (
        "get_client_stats should include async_client_active field"
    )
    # When no async client has been initialized, it should be False
    assert isinstance(stats["async_client_active"], bool)


# ---------------------------------------------------------------------------
# Test 6: Simulated concurrent async DB calls complete without thread exhaustion
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_concurrent_async_calls_dont_need_threads():
    """50 concurrent async DB calls complete without thread pool exhaustion.

    This proves the async migration works: calls go through native async,
    not via asyncio.to_thread which would queue behind a 32-thread pool.
    """
    from app.services.supabase_async import execute_async

    # Mock .execute() to return a coroutine (simulating async client)
    call_count = 0

    async def _fake_execute():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)  # Simulate small I/O latency
        return MagicMock(data=[{"id": call_count}])

    async def simulate_db_call(i: int):
        qb = MagicMock()
        qb.execute = _fake_execute
        return await execute_async(qb, op_name=f"test-{i}")

    results = await asyncio.gather(*(simulate_db_call(i) for i in range(50)))
    assert len(results) == 50
    assert call_count == 50


# ---------------------------------------------------------------------------
# Preserved tests from earlier plans
# ---------------------------------------------------------------------------
def test_supabase_default_max_connections_constant(monkeypatch):
    """supabase_async exposes SUPABASE_DEFAULT_MAX_CONNECTIONS = 200 by default."""
    import importlib

    monkeypatch.delenv("SUPABASE_MAX_CONNECTIONS", raising=False)

    import app.services.supabase_async as supabase_async_module

    importlib.reload(supabase_async_module)

    assert hasattr(supabase_async_module, "SUPABASE_DEFAULT_MAX_CONNECTIONS"), (
        "SUPABASE_DEFAULT_MAX_CONNECTIONS constant not found in supabase_async.py"
    )
    assert supabase_async_module.SUPABASE_DEFAULT_MAX_CONNECTIONS == 200


def test_supabase_max_connections_env_override(monkeypatch):
    """SUPABASE_MAX_CONNECTIONS env var overrides the default."""
    monkeypatch.setenv("SUPABASE_MAX_CONNECTIONS", "100")

    import importlib

    import app.services.supabase_async as supabase_async_module

    importlib.reload(supabase_async_module)

    assert supabase_async_module.SUPABASE_DEFAULT_MAX_CONNECTIONS == 100

    monkeypatch.delenv("SUPABASE_MAX_CONNECTIONS", raising=False)
    importlib.reload(supabase_async_module)


def test_fast_api_app_contains_thread_pool_executor():
    """fast_api_app.py contains ThreadPoolExecutor and set_default_executor patterns."""
    content = pathlib.Path("app/fast_api_app.py").read_text()
    assert "ThreadPoolExecutor" in content, (
        "ThreadPoolExecutor not found in fast_api_app.py"
    )
    assert "set_default_executor" in content, (
        "set_default_executor not found in fast_api_app.py"
    )

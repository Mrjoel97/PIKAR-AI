"""Unit tests for Redis pool scaling, latency tracking, memory alert, and key namespaces.

TDD RED phase: these tests MUST fail before implementation.
Covers RDSC-01 (pool size), RDSC-02 (latency), RDSC-03 (memory alert), RDSC-04 (namespaces).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.services.cache import invalidate_cache_service


def _run(coro):
    return asyncio.run(coro)


def setup_function():
    invalidate_cache_service()


def teardown_function():
    invalidate_cache_service()


# ---------------------------------------------------------------------------
# Test 1 (RDSC-01): Default pool size is 200, not 20
# ---------------------------------------------------------------------------


def test_default_max_connections_is_200():
    """CacheService._max_connections defaults to 200 when env var not set."""
    from app.services.cache import CacheService

    with patch.dict("os.environ", {}, clear=False):
        # Remove the env var if present so the default is used
        import os

        os.environ.pop("REDIS_MAX_CONNECTIONS", None)
        svc = CacheService()
        assert svc._max_connections == 200, (
            f"Expected 200 but got {svc._max_connections} — RDSC-01 not implemented"
        )


# ---------------------------------------------------------------------------
# Test 2 (RDSC-02): get_stats() returns latency_stats with p50_ms and p99_ms
# ---------------------------------------------------------------------------


def test_get_stats_contains_latency_stats_keys():
    """After get_stats(), the result dict has a 'latency_stats' key with p50_ms and p99_ms."""
    from app.services.cache import get_cache_service

    svc = get_cache_service()

    # Build a fake Redis client that mimics a connected state
    client = AsyncMock()
    client.ping.return_value = True
    client.info.return_value = {
        "redis_version": "7.2",
        "used_memory_human": "2M",
        "connected_clients": 3,
        "used_memory_rss": 10 * 1024 * 1024,   # 10 MB — below 256 MB threshold
        "used_memory_peak_rss": 12 * 1024 * 1024,
    }
    client.aclose = AsyncMock()
    client.get = AsyncMock(side_effect=["5", "2"])  # hits, misses
    svc._redis = client
    svc._connected = True

    stats = _run(svc.get_stats())

    assert "latency_stats" in stats, (
        "'latency_stats' key missing from get_stats() — RDSC-02 not implemented"
    )
    ls = stats["latency_stats"]
    assert "p50_ms" in ls, "'p50_ms' missing from latency_stats"
    assert "p99_ms" in ls, "'p99_ms' missing from latency_stats"


# ---------------------------------------------------------------------------
# Test 3 (RDSC-03): memory_alert fires when used_memory_rss > threshold
# ---------------------------------------------------------------------------


def test_get_stats_memory_alert_fires_above_threshold():
    """get_stats() returns memory_alert=True when used_memory_rss exceeds REDIS_MEMORY_ALERT_MB."""
    import os

    from app.services.cache import get_cache_service

    svc = get_cache_service()

    # 10 MB threshold, 20 MB used — should trigger alert
    alert_threshold_mb = 10
    used_memory_rss_bytes = 20 * 1024 * 1024

    client = AsyncMock()
    client.ping.return_value = True
    client.info.return_value = {
        "redis_version": "7.2",
        "used_memory_human": "20M",
        "connected_clients": 3,
        "used_memory_rss": used_memory_rss_bytes,
        "used_memory_peak_rss": used_memory_rss_bytes,
    }
    client.aclose = AsyncMock()
    client.get = AsyncMock(side_effect=["0", "0"])  # hits, misses
    svc._redis = client
    svc._connected = True

    with patch.dict(os.environ, {"REDIS_MEMORY_ALERT_MB": str(alert_threshold_mb)}):
        stats = _run(svc.get_stats())

    assert "memory_stats" in stats, (
        "'memory_stats' key missing from get_stats() — RDSC-03 not implemented"
    )
    assert stats["memory_stats"].get("memory_alert") is True, (
        "memory_alert should be True when used_memory_rss > threshold"
    )


# ---------------------------------------------------------------------------
# Test 4 (RDSC-04): REDIS_KEY_PREFIXES is exported with all required namespaces
# ---------------------------------------------------------------------------


def test_redis_key_prefixes_exported_with_required_namespaces():
    """REDIS_KEY_PREFIXES dict is exported and contains all documented namespaces."""
    from app.services.cache import REDIS_KEY_PREFIXES  # type: ignore[attr-defined]

    required_namespaces = [
        "user_config",
        "session_meta",
        "persona",
        "feature_flag",
        "rate_limit",
        "sse_conn",
        "confirmation",
        "jwt_cache",
        "integration",
        "agent_perm",
    ]
    for ns in required_namespaces:
        assert ns in REDIS_KEY_PREFIXES, (
            f"Namespace '{ns}' missing from REDIS_KEY_PREFIXES — RDSC-04 not implemented"
        )

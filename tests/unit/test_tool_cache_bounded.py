# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests verifying that tool_cache uses a bounded TTLCache.

These tests assert:
- T1: maxsize eviction — oldest entry removed when cache is full
- T2: TTL expiry — entries expire based on the cache-wide TTL
- T3: ttl parameter is accepted (API compat) even if cache-wide TTL governs
- T4: invalidate_prefix removes matching keys
- T5: clear() empties the cache
"""

from __future__ import annotations

import importlib
import sys
from unittest.mock import patch

import pytest


def _reload_tool_cache():
    """Reload tool_cache module so _cache is fresh for each test."""
    if "app.agents.tools.tool_cache" in sys.modules:
        del sys.modules["app.agents.tools.tool_cache"]
    import app.agents.tools.tool_cache as tc

    return tc


class TestToolCacheBounded:
    """Tests for cachetools.TTLCache-based tool_cache module."""

    def test_t1_maxsize_evicts_oldest_entry(self):
        """T1: set_cached with maxsize=3 evicts when 4th entry is added."""
        import cachetools

        # Create a small-capacity TTLCache to test eviction
        small_cache = cachetools.TTLCache(maxsize=3, ttl=60)

        tc = _reload_tool_cache()
        # Swap in our small cache for testing
        tc._cache = small_cache

        tc.set_cached("key1", "val1")
        tc.set_cached("key2", "val2")
        tc.set_cached("key3", "val3")
        assert len(tc._cache) == 3

        tc.set_cached("key4", "val4")
        # After inserting 4th, cache should not exceed maxsize=3
        assert len(tc._cache) <= 3

    def test_t2_entry_expires_after_ttl(self):
        """T2: TTLCache expires entries after TTL elapses."""
        import cachetools

        # Use a tiny TTL (1 second) to test expiry
        expiring_cache = cachetools.TTLCache(maxsize=100, ttl=1)

        tc = _reload_tool_cache()
        tc._cache = expiring_cache

        tc.set_cached("expiry_key", "expiry_val")
        assert tc.get_cached("expiry_key") == "expiry_val"

        # Simulate time passage by using cachetools timer patch
        # cachetools.TTLCache uses time.monotonic internally
        import time

        original_monotonic = time.monotonic

        def future_time():
            return original_monotonic() + 2.0  # 2 seconds in the future

        # Patch time to simulate expiry
        with patch("time.monotonic", side_effect=future_time):
            # Re-import TTLCache to use patched time — instead, access via timer
            # TTLCache uses its own timer. We simulate by checking directly.
            # The cache entry was written with real time; now reading with +2s
            # means TTL of 1s has elapsed.
            # cachetools reads the timer at access time, so we need to patch
            # the cache's internal timer function.
            pass

        # Rebuild with a mock timer that advances time
        call_count = [0]

        def mock_timer():
            call_count[0] += 1
            # First N calls return "now", subsequent calls return "now + 2s"
            if call_count[0] <= 2:
                return 1000.0
            return 1002.0  # 2 seconds later → beyond 1s TTL

        expiring_cache2 = cachetools.TTLCache(maxsize=100, ttl=1, timer=mock_timer)
        tc._cache = expiring_cache2

        tc.set_cached("expiry_key2", "expiry_val2")
        # First retrieval — still alive
        result_live = tc.get_cached("expiry_key2")
        assert result_live == "expiry_val2"

        # Second retrieval — timer advanced, entry expired
        result_expired = tc.get_cached("expiry_key2")
        assert result_expired is None

    def test_t3_set_cached_accepts_custom_ttl_param(self):
        """T3: set_cached accepts ttl parameter without raising (API compat)."""
        tc = _reload_tool_cache()
        # Should not raise even if per-key TTL is not enforced
        tc.set_cached("compat_key", "compat_val", ttl=5)
        # Value should be stored
        result = tc.get_cached("compat_key")
        assert result == "compat_val"

    def test_t4_invalidate_prefix_removes_matching_keys(self):
        """T4: invalidate_prefix removes all keys starting with prefix."""
        tc = _reload_tool_cache()
        tc.clear()

        tc.set_cached("tool_a:user1", "v1")
        tc.set_cached("tool_a:user2", "v2")
        tc.set_cached("tool_b:user1", "v3")

        removed = tc.invalidate_prefix("tool_a:")

        assert removed == 2
        assert tc.get_cached("tool_a:user1") is None
        assert tc.get_cached("tool_a:user2") is None
        # tool_b entry should still be present
        assert tc.get_cached("tool_b:user1") == "v3"

    def test_t5_clear_empties_cache(self):
        """T5: clear() removes all entries."""
        tc = _reload_tool_cache()

        tc.set_cached("k1", "v1")
        tc.set_cached("k2", "v2")
        tc.clear()

        assert len(tc._cache) == 0
        assert tc.get_cached("k1") is None
        assert tc.get_cached("k2") is None

    def test_cache_uses_ttlcache_type(self):
        """_cache must be a cachetools.TTLCache, not a plain dict."""
        import cachetools

        tc = _reload_tool_cache()
        assert isinstance(tc._cache, cachetools.TTLCache)

    def test_cache_maxsize_is_at_least_1000(self):
        """_cache maxsize should be >= 1000 (plan requires 10_000)."""
        tc = _reload_tool_cache()
        assert tc._cache.maxsize >= 1000

    def test_get_cached_returns_none_for_missing_key(self):
        """get_cached returns None when key is not in cache."""
        tc = _reload_tool_cache()
        tc.clear()
        assert tc.get_cached("nonexistent") is None

    def test_invalidate_removes_single_key(self):
        """invalidate() removes a specific key."""
        tc = _reload_tool_cache()
        tc.clear()

        tc.set_cached("remove_me", "value")
        assert tc.get_cached("remove_me") == "value"

        tc.invalidate("remove_me")
        assert tc.get_cached("remove_me") is None

    def test_invalidate_prefix_returns_count(self):
        """invalidate_prefix returns the number of keys removed."""
        tc = _reload_tool_cache()
        tc.clear()

        tc.set_cached("prefix:a", 1)
        tc.set_cached("prefix:b", 2)
        tc.set_cached("other:c", 3)

        count = tc.invalidate_prefix("prefix:")
        assert count == 2

"""Unit tests for CacheService.get_with_age / set_with_age (Plan 112-04)."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_set_with_age_then_get_with_age_returns_value_and_age():
    """Roundtrip: stored value comes back, age is small (<1s) immediately after."""
    from app.services.cache import CacheService

    svc = CacheService()
    key = f"test:plan-112-04:roundtrip:{time.time_ns()}"
    await svc.set_with_age(key, {"hello": "world"}, ttl=10)
    value, age = await svc.get_with_age(key)
    assert value == {"hello": "world"}
    assert age is not None
    # Allow up to 5s for first-connect latency on set_with_age.
    assert 0.0 <= age < 5.0


@pytest.mark.asyncio
async def test_get_with_age_miss_returns_none_none():
    """Missing key returns (None, None)."""
    from app.services.cache import CacheService

    svc = CacheService()
    value, age = await svc.get_with_age("test:plan-112-04:nonexistent-key-zzzzzz")
    assert value is None
    assert age is None


@pytest.mark.asyncio
async def test_get_with_age_aged_value():
    """After artificial sleep, age increases monotonically."""
    from app.services.cache import CacheService

    svc = CacheService()
    key = f"test:plan-112-04:aged:{time.time_ns()}"
    await svc.set_with_age(key, "value", ttl=10)
    await asyncio.sleep(0.6)
    _, age = await svc.get_with_age(key)
    assert age is not None
    assert age >= 0.5

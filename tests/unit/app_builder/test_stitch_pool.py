"""Unit tests for StitchPool — covers key resolution and spawn behavior."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_resolve_key_user_saved_takes_precedence(monkeypatch):
    """If user has a saved key, pool key is user:{user_id} and api_key is theirs."""
    from app.services.stitch_mcp import StitchPool

    monkeypatch.setenv("STITCH_API_KEY", "env-key")
    pool = StitchPool()

    with patch(
        "app.services.user_config.get_user_api_key", return_value="user-key"
    ):
        pool_key, api_key, fp = pool._resolve_key("u1")

    assert pool_key == "user:u1"
    assert api_key == "user-key"
    assert fp == pool._fingerprint("user-key")


def test_resolve_key_falls_back_to_env(monkeypatch):
    """If no user key, env key wins; pool key is __env_default__."""
    from app.services.stitch_mcp import StitchPool

    monkeypatch.setenv("STITCH_API_KEY", "env-key")
    pool = StitchPool()

    with patch(
        "app.services.user_config.get_user_api_key", return_value=None
    ):
        pool_key, api_key, fp = pool._resolve_key("u1")

    assert pool_key == StitchPool.POOL_KEY_ENV
    assert api_key == "env-key"


def test_resolve_key_falls_back_to_mock(monkeypatch):
    """If no user/env key but mock enabled, pool key is __mock__."""
    from app.services.stitch_mcp import StitchPool

    monkeypatch.delenv("STITCH_API_KEY", raising=False)
    monkeypatch.setenv("APP_BUILDER_USE_MOCK_STITCH", "1")
    pool = StitchPool()

    pool_key, api_key, _ = pool._resolve_key(None)
    assert pool_key == StitchPool.POOL_KEY_MOCK
    assert api_key is None


def test_resolve_key_raises_when_nothing_configured(monkeypatch):
    """No user key, no env key, no mock — raise RuntimeError."""
    from app.services.stitch_mcp import StitchPool

    monkeypatch.delenv("STITCH_API_KEY", raising=False)
    monkeypatch.delenv("APP_BUILDER_USE_MOCK_STITCH", raising=False)
    pool = StitchPool()

    with pytest.raises(RuntimeError, match="No Stitch API key configured"):
        pool._resolve_key(None)

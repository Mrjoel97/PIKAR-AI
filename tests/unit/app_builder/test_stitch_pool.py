"""Unit tests for StitchPool — covers key resolution and spawn behavior."""
import asyncio
from unittest.mock import MagicMock, patch

import pytest


def test_resolve_key_user_saved_takes_precedence(monkeypatch):
    """If user has a saved key, pool key is user:{user_id} and api_key is theirs."""
    from app.services.stitch_mcp import StitchPool

    monkeypatch.setenv("STITCH_API_KEY", "env-key")
    pool = StitchPool()

    with patch(
        "app.services.user_config.get_user_api_key", return_value="user-key"
    ):
        resolved = pool._resolve_key("u1")

    # Verify both the NamedTuple field access and tuple-unpacking work.
    assert resolved.pool_key == "user:u1"
    assert resolved.api_key == "user-key"
    assert resolved.fingerprint == pool._fingerprint("user-key")
    pool_key, api_key, fp = resolved
    assert (pool_key, api_key, fp) == (
        "user:u1",
        "user-key",
        pool._fingerprint("user-key"),
    )


def test_resolve_key_falls_back_to_env(monkeypatch):
    """If no user key, env key wins; pool key is __env_default__."""
    from app.services.stitch_mcp import StitchPool

    monkeypatch.setenv("STITCH_API_KEY", "env-key")
    pool = StitchPool()

    with patch(
        "app.services.user_config.get_user_api_key", return_value=None
    ):
        pool_key, api_key, _fp = pool._resolve_key("u1")

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


def _patch_service_classes(monkeypatch):
    """Replace _run() with a fast in-memory fake — no real subprocess."""
    from app.services import stitch_mcp

    async def _fake_run(self):
        self._session = MagicMock()
        self._healthy = True
        self._ready.set()
        await asyncio.sleep(3600)

    monkeypatch.setattr(stitch_mcp.StitchMCPService, "_run", _fake_run)


@pytest.mark.asyncio
async def test_get_or_spawn_spawns_once_and_reuses(monkeypatch):
    """First call spawns; second call returns the same service."""
    _patch_service_classes(monkeypatch)
    monkeypatch.setenv("STITCH_API_KEY", "env-key")

    from app.services.stitch_mcp import StitchPool

    pool = StitchPool()
    with patch(
        "app.services.user_config.get_user_api_key", return_value=None
    ):
        s1 = await pool.get_or_spawn("u1")
        s2 = await pool.get_or_spawn("u1")

    assert s1 is s2
    assert StitchPool.POOL_KEY_ENV in pool._services
    await pool.shutdown()


@pytest.mark.asyncio
async def test_get_or_spawn_two_users_two_pools(monkeypatch):
    """Different users with different saved keys get different pool entries."""
    _patch_service_classes(monkeypatch)
    monkeypatch.delenv("STITCH_API_KEY", raising=False)

    from app.services.stitch_mcp import StitchPool

    pool = StitchPool()

    def _per_user_key(user_id, key_name):
        return f"key-for-{user_id}"

    with patch(
        "app.services.user_config.get_user_api_key", side_effect=_per_user_key
    ):
        s1 = await pool.get_or_spawn("u1")
        s2 = await pool.get_or_spawn("u2")

    assert s1 is not s2
    assert "user:u1" in pool._services
    assert "user:u2" in pool._services
    await pool.shutdown()


@pytest.mark.asyncio
async def test_get_or_spawn_respawns_on_fingerprint_change(monkeypatch):
    """When the user's saved key changes, the pool respawns the service."""
    _patch_service_classes(monkeypatch)
    monkeypatch.delenv("STITCH_API_KEY", raising=False)

    from app.services.stitch_mcp import StitchPool

    pool = StitchPool()

    keys = iter(["old-key", "new-key"])
    with patch(
        "app.services.user_config.get_user_api_key",
        side_effect=lambda u, k: next(keys),
    ):
        s1 = await pool.get_or_spawn("u1")
        s2 = await pool.get_or_spawn("u1")

    assert s1 is not s2
    await pool.shutdown()

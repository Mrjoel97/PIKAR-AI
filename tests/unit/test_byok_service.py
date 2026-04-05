"""Unit tests for BYOK service."""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.byok_service import (
    SUPPORTED_PROVIDERS,
    BYOKConfig,
    BYOKService,
    _config_fingerprint,
    _runner_cache,
    get_models_for_provider,
    get_or_create_byok_runner,
    invalidate_runner_cache,
)


def test_supported_providers_includes_openai_and_anthropic():
    assert "openai" in SUPPORTED_PROVIDERS
    assert "anthropic" in SUPPORTED_PROVIDERS
    assert "gemini" not in SUPPORTED_PROVIDERS  # gemini is the default, not BYOK


def test_byok_config_dataclass():
    cfg = BYOKConfig(
        provider="openai",
        model="gpt-4o",
        api_key="sk-test-123",
    )
    assert cfg.provider == "openai"
    assert cfg.model == "gpt-4o"
    assert cfg.api_key == "sk-test-123"
    assert cfg.is_active is True  # default


def test_byok_config_litellm_model_string():
    cfg = BYOKConfig(
        provider="anthropic", model="claude-sonnet-4-20250514", api_key="sk-ant-test"
    )
    assert cfg.litellm_model == "anthropic/claude-sonnet-4-20250514"


def test_get_models_for_openai():
    models = get_models_for_provider("openai")
    assert any("gpt-4o" in m["id"] for m in models)


def test_get_models_for_anthropic():
    models = get_models_for_provider("anthropic")
    assert any("claude" in m["id"] for m in models)


def test_get_models_for_unknown_provider():
    models = get_models_for_provider("unknown")
    assert models == []


@pytest.fixture
def mock_supabase():
    return MagicMock()


@pytest.fixture
def service(mock_supabase):
    return BYOKService(supabase_client=mock_supabase)


@pytest.mark.asyncio
async def test_save_byok_config_encrypts_value(service, mock_supabase):
    """save_config should encrypt the full payload into config_value."""
    upsert_chain = MagicMock()
    upsert_chain.execute = AsyncMock(return_value=MagicMock(data=[{"id": "row-1"}]))
    mock_supabase.table.return_value.upsert.return_value = upsert_chain

    result = await service.save_config(
        user_id="user-123",
        provider="openai",
        model="gpt-4o",
        api_key="sk-test-key-abc",
    )

    assert result["success"] is True
    call_args = mock_supabase.table.return_value.upsert.call_args[0][0]
    assert call_args["config_key"] == "byok:active"
    assert call_args["is_sensitive"] is True
    assert "sk-test-key-abc" not in call_args["config_value"]


@pytest.mark.asyncio
async def test_get_byok_config_decrypts_value(service, mock_supabase):
    """get_config should decrypt config_value into a BYOKConfig."""
    from app.mcp.user_config import encrypt_config

    payload = {
        "api_key": "sk-real-key",
        "provider": "openai",
        "model": "gpt-4o",
        "is_active": True,
        "org_id": None,
    }
    encrypted = encrypt_config(payload)

    select_chain = MagicMock()
    select_chain.eq.return_value = select_chain
    select_chain.single.return_value = select_chain
    select_chain.execute = AsyncMock(
        return_value=MagicMock(data={"config_value": encrypted})
    )
    mock_supabase.table.return_value.select.return_value = select_chain

    cfg = await service.get_config("user-123")
    assert cfg is not None
    assert cfg.api_key == "sk-real-key"
    assert cfg.provider == "openai"
    assert cfg.model == "gpt-4o"


@pytest.mark.asyncio
async def test_delete_byok_config(service, mock_supabase):
    delete_chain = MagicMock()
    delete_chain.eq.return_value = delete_chain
    delete_chain.execute = AsyncMock(return_value=MagicMock(data=[{"id": "row-1"}]))
    mock_supabase.table.return_value.delete.return_value = delete_chain

    result = await service.delete_config("user-123")
    assert result is True


@pytest.mark.asyncio
async def test_save_rejects_unsupported_provider(service):
    result = await service.save_config(
        user_id="user-123",
        provider="deepseek",
        model="deepseek-v3",
        api_key="sk-xxx",
    )
    assert result["success"] is False
    assert "Unsupported" in result["error"]


# ---------------------------------------------------------------------------
# Runner cache tests
# ---------------------------------------------------------------------------


def _make_cfg(provider="openai", model="gpt-4o", api_key="sk-test"):
    """Create a BYOKConfig with sensible defaults."""
    return BYOKConfig(provider=provider, model=model, api_key=api_key)


class TestConfigFingerprint:
    """Tests for _config_fingerprint — the cache invalidation key."""

    def test_same_config_same_fingerprint(self):
        """Identical provider/model/org_id produces the same fingerprint."""
        cfg1 = _make_cfg()
        cfg2 = _make_cfg()
        assert _config_fingerprint(cfg1) == _config_fingerprint(cfg2)

    def test_different_model_different_fingerprint(self):
        """Different model strings produce different fingerprints."""
        cfg1 = _make_cfg(model="gpt-4o")
        cfg2 = _make_cfg(model="gpt-4o-mini")
        assert _config_fingerprint(cfg1) != _config_fingerprint(cfg2)

    def test_different_provider_different_fingerprint(self):
        """Different providers produce different fingerprints."""
        cfg1 = _make_cfg(provider="openai")
        cfg2 = _make_cfg(provider="anthropic")
        assert _config_fingerprint(cfg1) != _config_fingerprint(cfg2)

    def test_api_key_not_in_fingerprint(self):
        """API key rotation should NOT invalidate the runner cache."""
        cfg1 = _make_cfg(api_key="sk-key-1")
        cfg2 = _make_cfg(api_key="sk-key-2")
        assert _config_fingerprint(cfg1) == _config_fingerprint(cfg2)

    def test_org_id_included_in_fingerprint(self):
        """org_id is part of the fingerprint so org changes bust the cache."""
        cfg1 = BYOKConfig(provider="openai", model="gpt-4o", api_key="sk-test", org_id="org-A")
        cfg2 = BYOKConfig(provider="openai", model="gpt-4o", api_key="sk-test", org_id="org-B")
        assert _config_fingerprint(cfg1) != _config_fingerprint(cfg2)

    def test_none_org_id_in_fingerprint(self):
        """None org_id is handled without raising."""
        cfg = BYOKConfig(provider="openai", model="gpt-4o", api_key="sk-test", org_id=None)
        fp = _config_fingerprint(cfg)
        assert isinstance(fp, str)
        assert "openai" in fp
        assert "gpt-4o" in fp


class TestRunnerCache:
    """Tests for get_or_create_byok_runner and invalidate_runner_cache.

    The conftest.py for unit tests pre-populates sys.modules with lightweight
    mocks for google.adk.runners, google.adk.apps, google.adk.models, and the
    agent factory modules.  Those mocks satisfy the lazy imports inside
    get_or_create_byok_runner, so no @patch decorators are needed here.
    """

    def setup_method(self):
        """Clear the module-level cache before each test for isolation."""
        _runner_cache.clear()

    def test_cache_miss_creates_runner(self):
        """First call for a user creates a runner and stores it in the cache."""
        cfg = _make_cfg()
        runner = get_or_create_byok_runner("user-1", cfg, None, None)
        assert runner is not None
        assert "user-1" in _runner_cache

    def test_cache_hit_returns_same_runner(self):
        """Second call with the same config returns the identical runner object."""
        cfg = _make_cfg()
        runner1 = get_or_create_byok_runner("user-1", cfg, None, None)
        runner2 = get_or_create_byok_runner("user-1", cfg, None, None)
        assert runner1 is runner2  # same object — cache hit

    def test_different_users_get_different_runners(self):
        """Each user gets their own cached runner."""
        cfg = _make_cfg()
        runner_a = get_or_create_byok_runner("user-A", cfg, None, None)
        runner_b = get_or_create_byok_runner("user-B", cfg, None, None)
        assert runner_a is not runner_b
        assert "user-A" in _runner_cache
        assert "user-B" in _runner_cache

    def test_config_change_invalidates_cache(self):
        """Changing model triggers a new runner for the same user."""
        cfg1 = _make_cfg(model="gpt-4o")
        cfg2 = _make_cfg(model="gpt-4o-mini")
        runner1 = get_or_create_byok_runner("user-1", cfg1, None, None)
        runner2 = get_or_create_byok_runner("user-1", cfg2, None, None)
        assert runner1 is not runner2  # different config → new runner

    def test_ttl_expiry_creates_new_runner(self):
        """A cache entry older than TTL is treated as a miss and replaced."""
        cfg = _make_cfg()
        runner1 = get_or_create_byok_runner("user-1", cfg, None, None)

        # Simulate TTL expiry by backdating the cached entry
        _runner_cache["user-1"].created_at = time.monotonic() - 400  # > 300s TTL

        runner2 = get_or_create_byok_runner("user-1", cfg, None, None)
        assert runner1 is not runner2  # stale entry replaced with a new runner

    def test_invalidate_removes_entry(self):
        """invalidate_runner_cache removes the entry for the given user."""
        _runner_cache["user-1"] = MagicMock()
        invalidate_runner_cache("user-1")
        assert "user-1" not in _runner_cache

    def test_invalidate_nonexistent_user_is_safe(self):
        """Invalidating a user with no cached entry does not raise."""
        invalidate_runner_cache("no-such-user")  # must not raise

    def test_cache_entry_stores_fingerprint(self):
        """The cached entry records the config fingerprint used at creation."""
        cfg = _make_cfg(provider="anthropic", model="claude-sonnet-4-20250514")
        get_or_create_byok_runner("user-1", cfg, None, None)
        entry = _runner_cache["user-1"]
        assert entry.config_fingerprint == _config_fingerprint(cfg)

    def test_cache_entry_records_created_at(self):
        """The cached entry records a monotonic creation timestamp."""
        before = time.monotonic()
        cfg = _make_cfg()
        get_or_create_byok_runner("user-1", cfg, None, None)
        after = time.monotonic()
        ts = _runner_cache["user-1"].created_at
        assert before <= ts <= after

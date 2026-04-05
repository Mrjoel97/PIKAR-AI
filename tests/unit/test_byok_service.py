"""Unit tests for BYOK service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.byok_service import (
    SUPPORTED_PROVIDERS,
    BYOKConfig,
    BYOKService,
    get_models_for_provider,
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

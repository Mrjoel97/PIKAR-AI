"""Unit tests for BYOK service."""

from app.services.byok_service import (
    SUPPORTED_PROVIDERS,
    BYOKConfig,
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
    cfg = BYOKConfig(provider="anthropic", model="claude-sonnet-4-20250514", api_key="sk-ant-test")
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

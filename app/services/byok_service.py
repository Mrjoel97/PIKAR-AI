"""BYOK (Bring Your Own Key) service.

Manages per-user AI provider API keys with encrypted storage,
Redis caching, and model resolution for ADK LiteLlm integration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider & Model Registry
# ---------------------------------------------------------------------------

SUPPORTED_PROVIDERS: dict[str, dict[str, str]] = {
    "openai": {
        "name": "OpenAI",
        "key_prefix": "sk-",
        "env_var": "OPENAI_API_KEY",
        "docs_url": "https://platform.openai.com/api-keys",
    },
    "anthropic": {
        "name": "Anthropic",
        "key_prefix": "sk-ant-",
        "env_var": "ANTHROPIC_API_KEY",
        "docs_url": "https://console.anthropic.com/settings/keys",
    },
}

_MODEL_CATALOG: dict[str, list[dict[str, str]]] = {
    "openai": [
        {"id": "gpt-4o", "name": "GPT-4o", "tier": "flagship"},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "tier": "fast"},
        {"id": "o3", "name": "o3 (Reasoning)", "tier": "reasoning"},
        {"id": "o4-mini", "name": "o4-mini (Reasoning)", "tier": "reasoning"},
    ],
    "anthropic": [
        {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "tier": "flagship"},
        {"id": "claude-opus-4-20250514", "name": "Claude Opus 4", "tier": "premium"},
        {"id": "claude-haiku-4-20250506", "name": "Claude Haiku 4", "tier": "fast"},
    ],
}


def get_models_for_provider(provider: str) -> list[dict[str, str]]:
    """Return available models for a given provider."""
    return _MODEL_CATALOG.get(provider, [])


# ---------------------------------------------------------------------------
# BYOKConfig dataclass
# ---------------------------------------------------------------------------


@dataclass
class BYOKConfig:
    """A user's BYOK configuration."""

    provider: str
    model: str
    api_key: str
    is_active: bool = True
    org_id: str | None = None

    @property
    def litellm_model(self) -> str:
        """Return the LiteLLM-format model string (e.g. 'anthropic/claude-sonnet-4-20250514')."""
        return f"{self.provider}/{self.model}"

"""BYOK (Bring Your Own Key) service.

Manages per-user AI provider API keys with encrypted storage,
Redis caching, and model resolution for ADK LiteLlm integration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.mcp.user_config import decrypt_config, encrypt_config
from app.services.supabase_async import execute_async

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
        {
            "id": "claude-sonnet-4-20250514",
            "name": "Claude Sonnet 4",
            "tier": "flagship",
        },
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


# ---------------------------------------------------------------------------
# BYOKService
# ---------------------------------------------------------------------------

_BYOK_TABLE = "user_configurations"
_BYOK_CONFIG_KEY = "byok:active"


class BYOKService:
    """Service for managing per-user BYOK AI provider keys."""

    def __init__(self, supabase_client=None):
        """Initialize with optional Supabase client."""
        self._supabase = supabase_client

    def _get_supabase(self):
        """Get Supabase client, initializing lazily if needed."""
        if self._supabase:
            return self._supabase
        from app.services.supabase import get_service_client

        self._supabase = get_service_client()
        return self._supabase

    async def save_config(
        self,
        user_id: str,
        provider: str,
        model: str,
        api_key: str,
        org_id: str | None = None,
    ) -> dict[str, Any]:
        """Encrypt and store a BYOK configuration."""
        if provider not in SUPPORTED_PROVIDERS:
            return {"success": False, "error": f"Unsupported provider: {provider}"}

        payload = {
            "api_key": api_key,
            "provider": provider,
            "model": model,
            "is_active": True,
            "org_id": org_id,
        }
        encrypted = encrypt_config(payload)

        data = {
            "user_id": user_id,
            "config_key": _BYOK_CONFIG_KEY,
            "config_value": encrypted,
            "is_sensitive": True,
        }

        sb = self._get_supabase()
        result = await execute_async(
            sb.table(_BYOK_TABLE).upsert(data, on_conflict="user_id,config_key"),
            op_name="byok.save",
        )
        await self._invalidate_cache(user_id)
        return {"success": True, "id": (result.data or [{}])[0].get("id")}

    async def get_config(self, user_id: str) -> BYOKConfig | None:
        """Load and decrypt the user's active BYOK config."""
        cached = await self._get_from_cache(user_id)
        if cached is not None:
            return cached

        sb = self._get_supabase()
        result = await execute_async(
            sb.table(_BYOK_TABLE)
            .select("config_value")
            .eq("user_id", user_id)
            .eq("config_key", _BYOK_CONFIG_KEY)
            .single(),
            op_name="byok.get",
        )
        row = result.data
        if not row or not row.get("config_value"):
            return None

        decrypted = decrypt_config(row["config_value"])
        if not decrypted.get("is_active", True):
            return None

        cfg = BYOKConfig(
            provider=decrypted["provider"],
            model=decrypted["model"],
            api_key=decrypted["api_key"],
            is_active=decrypted.get("is_active", True),
            org_id=decrypted.get("org_id"),
        )
        await self._set_cache(user_id, cfg)
        return cfg

    async def delete_config(self, user_id: str) -> bool:
        """Delete user's BYOK configuration."""
        sb = self._get_supabase()
        result = await execute_async(
            sb.table(_BYOK_TABLE)
            .delete()
            .eq("user_id", user_id)
            .eq("config_key", _BYOK_CONFIG_KEY),
            op_name="byok.delete",
        )
        await self._invalidate_cache(user_id)
        return bool(result.data)

    async def _get_from_cache(self, user_id: str) -> BYOKConfig | None:
        """Retrieve BYOKConfig from Redis cache if available."""
        try:
            import json

            from app.services.cache import get_cache_service

            cache = get_cache_service()
            raw = await cache.get(f"byok:{user_id}")
            if raw:
                d = json.loads(raw)
                return BYOKConfig(**d)
        except Exception:
            pass
        return None

    async def _set_cache(self, user_id: str, cfg: BYOKConfig) -> None:
        """Store BYOKConfig in Redis cache with 5-minute TTL."""
        try:
            import json
            from dataclasses import asdict

            from app.services.cache import get_cache_service

            cache = get_cache_service()
            await cache.set(f"byok:{user_id}", json.dumps(asdict(cfg)), ttl=300)
        except Exception:
            pass

    async def _invalidate_cache(self, user_id: str) -> None:
        """Remove user's BYOK entry from Redis cache."""
        try:
            from app.services.cache import get_cache_service

            cache = get_cache_service()
            await cache.delete(f"byok:{user_id}")
        except Exception:
            pass


_byok_service: BYOKService | None = None


def get_byok_service() -> BYOKService:
    """Get the global BYOK service singleton."""
    global _byok_service
    if _byok_service is None:
        _byok_service = BYOKService()
    return _byok_service

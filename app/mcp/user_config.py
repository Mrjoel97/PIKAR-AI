# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""User MCP Configuration Service.

This module manages per-user MCP integrations with encrypted credential storage.
Supports both pre-configured templates and custom integrations.
"""

import base64
import json
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)
from datetime import datetime, timezone
from typing import Any

# Use cryptography for AES encryption
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


def _get_encryption_key() -> bytes:
    """Get or generate encryption key from environment."""
    key = os.environ.get("MCP_ENCRYPTION_KEY")
    if key:
        return base64.urlsafe_b64decode(key)

    # Generate from a secret + salt for consistency
    secret = os.environ.get("SECRET_KEY", "pikar-ai-default-secret")
    salt = b"pikar-mcp-salt-v1"

    if CRYPTO_AVAILABLE:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(secret.encode()))

    # Fallback: simple hash (less secure, but works without cryptography)
    import hashlib

    return base64.urlsafe_b64encode(
        hashlib.sha256((secret + salt.decode()).encode()).digest()
    )


def encrypt_config(config: dict[str, Any]) -> str:
    """Encrypt configuration dictionary."""
    if not CRYPTO_AVAILABLE:
        # Fallback: base64 encode (NOT SECURE - for dev only)
        return base64.b64encode(json.dumps(config).encode()).decode()

    key = _get_encryption_key()
    f = Fernet(key)
    return f.encrypt(json.dumps(config).encode()).decode()


def decrypt_config(encrypted: str) -> dict[str, Any]:
    """Decrypt configuration string."""
    if not CRYPTO_AVAILABLE:
        # Fallback: base64 decode
        return json.loads(base64.b64decode(encrypted).decode())

    key = _get_encryption_key()
    f = Fernet(key)
    return json.loads(f.decrypt(encrypted.encode()).decode())


@dataclass
class IntegrationTemplate:
    """Template for a pre-configured integration."""

    id: str
    name: str
    description: str
    category: str
    required_fields: list[dict[str, str]]
    optional_fields: list[dict[str, str]]
    docs_url: str | None = None
    icon_url: str | None = None


@dataclass
class UserIntegration:
    """User's configured integration."""

    id: str
    user_id: str
    integration_type: str
    display_name: str | None
    config: dict[str, Any]  # Decrypted config
    is_active: bool
    last_tested_at: datetime | None
    test_status: str | None
    test_error: str | None
    created_at: datetime
    updated_at: datetime


# Default templates (in-memory, synced with database)
INTEGRATION_TEMPLATES: dict[str, IntegrationTemplate] = {
    "supabase": IntegrationTemplate(
        id="supabase",
        name="Supabase",
        description="Database, Auth, and Storage",
        category="database",
        required_fields=[
            {
                "key": "url",
                "label": "Project URL",
                "type": "url",
                "placeholder": "https://xxx.supabase.co",
            },
            {"key": "anon_key", "label": "Anon/Public Key", "type": "secret"},
            {"key": "service_role_key", "label": "Service Role Key", "type": "secret"},
        ],
        optional_fields=[],
        docs_url="https://supabase.com/docs",
    ),
    "resend": IntegrationTemplate(
        id="resend",
        name="Resend",
        description="Email API for developers",
        category="email",
        required_fields=[
            {
                "key": "api_key",
                "label": "API Key",
                "type": "secret",
                "placeholder": "re_...",
            },
        ],
        optional_fields=[
            {"key": "from_email", "label": "Default From Email", "type": "email"},
        ],
        docs_url="https://resend.com/docs",
    ),
    "slack": IntegrationTemplate(
        id="slack",
        name="Slack",
        description="Team messaging and notifications",
        category="communication",
        required_fields=[
            {"key": "webhook_url", "label": "Webhook URL", "type": "url"},
        ],
        optional_fields=[
            {"key": "bot_token", "label": "Bot Token", "type": "secret"},
        ],
        docs_url="https://api.slack.com/docs",
    ),
    "notion": IntegrationTemplate(
        id="notion",
        name="Notion",
        description="Workspace and documentation",
        category="productivity",
        required_fields=[
            {"key": "api_key", "label": "Integration Token", "type": "secret"},
        ],
        optional_fields=[],
        docs_url="https://developers.notion.com",
    ),
    "airtable": IntegrationTemplate(
        id="airtable",
        name="Airtable",
        description="Spreadsheet database",
        category="database",
        required_fields=[
            {"key": "api_key", "label": "API Key", "type": "secret"},
            {"key": "base_id", "label": "Base ID", "type": "text"},
        ],
        optional_fields=[],
        docs_url="https://airtable.com/developers/web/api",
    ),
    "hubspot": IntegrationTemplate(
        id="hubspot",
        name="HubSpot",
        description="CRM and marketing",
        category="crm",
        required_fields=[
            {"key": "api_key", "label": "Private App Token", "type": "secret"},
        ],
        optional_fields=[],
        docs_url="https://developers.hubspot.com",
    ),
    "stripe": IntegrationTemplate(
        id="stripe",
        name="Stripe",
        description="Payments and billing",
        category="payments",
        required_fields=[
            {"key": "secret_key", "label": "Secret Key", "type": "secret"},
        ],
        optional_fields=[
            {"key": "webhook_secret", "label": "Webhook Secret", "type": "secret"},
        ],
        docs_url="https://stripe.com/docs/api",
    ),
    "openai": IntegrationTemplate(
        id="openai",
        name="OpenAI",
        description="AI models and APIs",
        category="ai",
        required_fields=[
            {"key": "api_key", "label": "API Key", "type": "secret"},
        ],
        optional_fields=[
            {"key": "org_id", "label": "Organization ID", "type": "text"},
        ],
        docs_url="https://platform.openai.com/docs",
    ),
    "custom": IntegrationTemplate(
        id="custom",
        name="Custom Integration",
        description="Configure any API manually",
        category="other",
        required_fields=[
            {"key": "base_url", "label": "Base URL", "type": "url"},
        ],
        optional_fields=[
            {"key": "api_key", "label": "API Key", "type": "secret"},
            {"key": "headers", "label": "Custom Headers (JSON)", "type": "json"},
        ],
        docs_url=None,
    ),
}


class UserMCPConfigService:
    """Service for managing user MCP integrations."""

    def __init__(self, supabase_client=None):
        """Initialize with optional Supabase client."""
        self._supabase = supabase_client
        self._cache: dict[str, list[UserIntegration]] = {}

    def _get_supabase(self):
        """Get Supabase client, initializing if needed."""
        if self._supabase:
            return self._supabase

        # Try to get from environment
        from app.mcp.config import get_mcp_config

        config = get_mcp_config()

        if config.is_supabase_configured():
            try:
                from app.services.supabase import get_service_client

                self._supabase = get_service_client()
            except Exception as e:
                logger.warning(
                    "Failed to get cached Supabase client for user config: %s", e
                )

        return self._supabase

    def get_templates(self) -> list[IntegrationTemplate]:
        """Get all available integration templates."""
        return list(INTEGRATION_TEMPLATES.values())

    def get_template(self, integration_type: str) -> IntegrationTemplate | None:
        """Get a specific integration template."""
        return INTEGRATION_TEMPLATES.get(integration_type)

    def get_user_integrations(self, user_id: str) -> list[UserIntegration]:
        """Get all integrations for a user."""
        supabase = self._get_supabase()
        if not supabase:
            return []

        try:
            result = (
                supabase.table("user_mcp_integrations")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )

            integrations = []
            for row in result.data:
                config = decrypt_config(row["config_encrypted"])
                integrations.append(
                    UserIntegration(
                        id=row["id"],
                        user_id=row["user_id"],
                        integration_type=row["integration_type"],
                        display_name=row.get("display_name"),
                        config=config,
                        is_active=row["is_active"],
                        last_tested_at=row.get("last_tested_at"),
                        test_status=row.get("test_status"),
                        test_error=row.get("test_error"),
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )
            return integrations
        except Exception as e:
            logger.error("Error fetching integrations: %s", e)
            return []

    def get_active_integration(
        self, user_id: str, integration_type: str
    ) -> UserIntegration | None:
        """Get user's active integration of a specific type."""
        integrations = self.get_user_integrations(user_id)
        for integration in integrations:
            if (
                integration.integration_type == integration_type
                and integration.is_active
            ):
                return integration
        return None

    def save_integration(
        self,
        user_id: str,
        integration_type: str,
        config: dict[str, Any],
        display_name: str | None = None,
    ) -> dict[str, Any]:
        """Save a new or updated integration."""
        supabase = self._get_supabase()
        if not supabase:
            return {"success": False, "error": "Database not configured"}

        try:
            encrypted = encrypt_config(config)

            # Upsert based on user_id + integration_type + display_name
            data = {
                "user_id": user_id,
                "integration_type": integration_type,
                "display_name": display_name or integration_type,
                "config_encrypted": encrypted,
                "is_active": False,
                "test_status": "pending",
            }

            result = (
                supabase.table("user_mcp_integrations")
                .upsert(data, on_conflict="user_id,integration_type,display_name")
                .execute()
            )

            return {
                "success": True,
                "integration_id": result.data[0]["id"] if result.data else None,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_test_status(
        self,
        integration_id: str,
        status: str,
        error: str | None = None,
    ) -> bool:
        """Update the test status of an integration."""
        supabase = self._get_supabase()
        if not supabase:
            return False

        try:
            supabase.table("user_mcp_integrations").update(
                {
                    "test_status": status,
                    "test_error": error,
                    "last_tested_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", integration_id).execute()
            return True
        except Exception:
            return False

    def activate_integration(self, integration_id: str) -> bool:
        """Activate an integration (must pass test first)."""
        supabase = self._get_supabase()
        if not supabase:
            return False

        try:
            # Verify test passed
            result = (
                supabase.table("user_mcp_integrations")
                .select("test_status")
                .eq("id", integration_id)
                .execute()
            )
            if not result.data or result.data[0].get("test_status") != "success":
                return False

            supabase.table("user_mcp_integrations").update({"is_active": True}).eq(
                "id", integration_id
            ).execute()
            return True
        except Exception:
            return False

    def deactivate_integration(self, integration_id: str) -> bool:
        """Deactivate an integration."""
        supabase = self._get_supabase()
        if not supabase:
            return False

        try:
            supabase.table("user_mcp_integrations").update({"is_active": False}).eq(
                "id", integration_id
            ).execute()
            return True
        except Exception:
            return False

    def delete_integration(self, integration_id: str) -> bool:
        """Delete an integration."""
        supabase = self._get_supabase()
        if not supabase:
            return False

        try:
            supabase.table("user_mcp_integrations").delete().eq(
                "id", integration_id
            ).execute()
            return True
        except Exception:
            return False


# Global service instance
_user_config_service: UserMCPConfigService | None = None


def get_user_config_service() -> UserMCPConfigService:
    """Get the global user config service instance."""
    global _user_config_service
    if _user_config_service is None:
        _user_config_service = UserMCPConfigService()
    return _user_config_service

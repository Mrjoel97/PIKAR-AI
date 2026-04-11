# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Backend-owned personal data export service.

Builds a signed JSON archive for the authenticated user's account data.
The service is backend-owned so it can gather account metadata, privacy
records, and other user-scoped tables without exposing secrets in the browser.
Sensitive values are redacted before the archive is uploaded.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

BUCKET_NAME = "generated-documents"
SIGNED_URL_EXPIRY_SECONDS = 24 * 60 * 60  # 24 hours
JSON_CONTENT_TYPE = "application/json; charset=utf-8"
REDACTED_VALUE = "[REDACTED]"
SENSITIVE_KEYWORDS = (
    "token",
    "secret",
    "api_key",
    "apikey",
    "password",
    "private_key",
    "authorization",
    "credential",
)


class PersonalDataExportService:
    """Create a signed personal-data export archive for one authenticated user."""

    def __init__(self, user_id: str, *, client: Any | None = None) -> None:
        self._user_id = str(user_id)
        self._client = client or get_service_client()
        self._warnings: list[str] = []

    @property
    def client(self) -> Any:
        """Return the Supabase client used for export operations."""
        return self._client

    async def export_personal_data(self) -> dict[str, Any]:
        """Generate, upload, and sign a personal-data export archive."""
        payload = await self.build_export_payload()
        archive_bytes = self._payload_to_json_bytes(payload)

        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        filename = f"personal-data-export_{timestamp}_{uuid.uuid4().hex[:8]}.json"
        storage_path = f"{self._user_id}/privacy-exports/{filename}"

        await self._upload_export_bytes(storage_path, archive_bytes)
        signed_url = await self._create_signed_url(storage_path)

        manifest = payload["manifest"]
        return {
            "url": signed_url,
            "filename": filename,
            "size_bytes": len(archive_bytes),
            "format": "json",
            "generated_at": manifest["generated_at"],
            "sections": manifest["sections"],
            "warnings": manifest["warnings"],
        }

    async def build_export_payload(self) -> dict[str, Any]:
        """Build the full export payload before upload."""
        generated_at = datetime.now(tz=timezone.utc).isoformat()

        account = {
            "auth_user": await self._fetch_auth_user(),
            "profile": await self._safe_query_one("users_profile"),
            "legacy_agent_config": await self._safe_query_one("user_executive_agents"),
        }

        privacy = {
            "data_deletion_requests": await self._safe_query_rows(
                "data_deletion_requests",
                order_by="requested_at",
                desc=True,
            ),
        }

        sessions = await self._safe_query_rows(
            "sessions",
            user_column="user_id",
            order_by="updated_at",
            desc=True,
        )
        session_events = await self._safe_query_rows(
            "session_events",
            user_column="user_id",
            order_by="created_at",
        )

        workflow_executions = await self._safe_query_rows(
            "workflow_executions",
            order_by="created_at",
            desc=True,
        )
        workflow_steps = await self._safe_query_in_rows(
            "workflow_steps",
            "execution_id",
            [row.get("id") for row in workflow_executions if row.get("id")],
            order_by="created_at",
        )

        content = {
            "campaigns": await self._safe_query_rows(
                "campaigns",
                order_by="created_at",
                desc=True,
            ),
            "content_bundles": await self._safe_query_rows(
                "content_bundles",
                order_by="created_at",
                desc=True,
            ),
            "vault_documents": await self._safe_query_rows(
                "vault_documents",
                order_by="created_at",
                desc=True,
            ),
            "agent_google_docs": await self._safe_query_rows(
                "agent_google_docs",
                order_by="created_at",
                desc=True,
            ),
        }

        payload: dict[str, Any] = {
            "account": account,
            "privacy": privacy,
            "conversations": {
                "sessions": sessions,
                "session_events": session_events,
            },
            "initiatives": await self._safe_query_rows(
                "initiatives",
                order_by="created_at",
                desc=True,
            ),
            "workflows": {
                "workflow_executions": workflow_executions,
                "workflow_steps": workflow_steps,
            },
            "content": content,
            "sales": {
                "contacts": await self._safe_query_rows(
                    "contacts",
                    order_by="created_at",
                    desc=True,
                ),
                "contact_activities": await self._safe_query_rows(
                    "contact_activities",
                    order_by="created_at",
                    desc=True,
                ),
            },
            "finance": {
                "financial_records": await self._safe_query_rows(
                    "financial_records",
                    order_by="created_at",
                    desc=True,
                ),
            },
            "operations": {
                "department_tasks": await self._safe_query_department_tasks(),
            },
            "support": {
                "support_tickets": await self._safe_query_rows(
                    "support_tickets",
                    order_by="created_at",
                    desc=True,
                ),
            },
            "people": {
                "recruitment_jobs": await self._safe_query_rows(
                    "recruitment_jobs",
                    order_by="created_at",
                    desc=True,
                ),
                "recruitment_candidates": await self._safe_query_rows(
                    "recruitment_candidates",
                    order_by="created_at",
                    desc=True,
                ),
            },
            "compliance": {
                "compliance_audits": await self._safe_query_rows(
                    "compliance_audits",
                    order_by="created_at",
                    desc=True,
                ),
                "compliance_risks": await self._safe_query_rows(
                    "compliance_risks",
                    order_by="created_at",
                    desc=True,
                ),
            },
            "integrations": {
                "connected_accounts": await self._safe_query_rows(
                    "connected_accounts",
                    order_by="connected_at",
                    desc=True,
                ),
                "integration_credentials": await self._safe_query_rows(
                    "integration_credentials",
                    order_by="updated_at",
                    desc=True,
                ),
                "integration_sync_state": await self._safe_query_rows(
                    "integration_sync_state",
                    order_by="updated_at",
                    desc=True,
                ),
            },
            "configuration": {
                "user_configurations": await self._safe_query_rows(
                    "user_configurations",
                    order_by="updated_at",
                    desc=True,
                ),
            },
        }

        section_names = list(payload.keys())
        manifest = {
            "version": 1,
            "generated_at": generated_at,
            "user_id": self._user_id,
            "format": "json",
            "sections": section_names,
            "redactions": [
                "OAuth access and refresh tokens are redacted.",
                "Sensitive user configuration values are redacted.",
                "Opaque integration sync cursors are redacted.",
            ],
            "warnings": list(self._warnings),
        }
        return {"manifest": manifest, **payload}

    async def _upload_export_bytes(self, storage_path: str, archive_bytes: bytes) -> None:
        """Upload the generated archive to Supabase Storage."""
        await asyncio.to_thread(
            self.client.storage.from_(BUCKET_NAME).upload,
            storage_path,
            archive_bytes,
            {"content-type": JSON_CONTENT_TYPE},
        )

    async def _create_signed_url(self, storage_path: str) -> str:
        """Create a signed download URL for the archive."""
        result = await asyncio.to_thread(
            self.client.storage.from_(BUCKET_NAME).create_signed_url,
            storage_path,
            SIGNED_URL_EXPIRY_SECONDS,
        )
        return result["signedURL"]

    async def _fetch_auth_user(self) -> dict[str, Any] | None:
        """Fetch authenticated account metadata from Supabase Auth admin."""
        try:
            response = await asyncio.to_thread(
                self.client.auth.admin.get_user_by_id,
                self._user_id,
            )
        except Exception as exc:
            self._record_warning("auth_user", exc)
            return None

        user = getattr(response, "user", None)
        if user is None:
            return None

        identities = []
        for identity in getattr(user, "identities", None) or []:
            provider = getattr(identity, "provider", None)
            if provider is None and isinstance(identity, dict):
                provider = identity.get("provider")
            if provider:
                identities.append(provider)

        auth_user = {
            "id": getattr(user, "id", None),
            "email": getattr(user, "email", None),
            "phone": getattr(user, "phone", None),
            "role": getattr(user, "role", None),
            "created_at": getattr(user, "created_at", None),
            "last_sign_in_at": getattr(user, "last_sign_in_at", None),
            "app_metadata": getattr(user, "app_metadata", None) or {},
            "user_metadata": getattr(user, "user_metadata", None) or {},
            "providers": identities,
        }
        return self._redact_sensitive_data(auth_user)

    async def _safe_query_one(
        self,
        table_name: str,
        *,
        user_column: str = "user_id",
        order_by: str | None = None,
        desc: bool = False,
    ) -> dict[str, Any] | None:
        """Return the first user-scoped row from a table, or ``None``."""
        rows = await self._safe_query_rows(
            table_name,
            user_column=user_column,
            order_by=order_by,
            desc=desc,
        )
        return rows[0] if rows else None

    async def _safe_query_rows(
        self,
        table_name: str,
        *,
        user_column: str = "user_id",
        user_value: str | None = None,
        order_by: str | None = None,
        desc: bool = False,
    ) -> list[dict[str, Any]]:
        """Query rows filtered to the current user and redact sensitive values."""
        try:
            query = self.client.table(table_name).select("*").eq(
                user_column,
                str(user_value if user_value is not None else self._user_id),
            )
            if order_by:
                query = query.order(order_by, desc=desc)
            result = await execute_async(
                query,
                op_name=f"personal_data_export.{table_name}",
            )
        except Exception as exc:
            self._record_warning(table_name, exc)
            return []

        return self._redact_sensitive_data(result.data or [])

    async def _safe_query_in_rows(
        self,
        table_name: str,
        column: str,
        values: list[Any],
        *,
        order_by: str | None = None,
        desc: bool = False,
    ) -> list[dict[str, Any]]:
        """Query rows matching one of the provided values."""
        scoped_values = [value for value in values if value is not None]
        if not scoped_values:
            return []

        try:
            query = self.client.table(table_name).select("*").in_(column, scoped_values)
            if order_by:
                query = query.order(order_by, desc=desc)
            result = await execute_async(
                query,
                op_name=f"personal_data_export.{table_name}",
            )
        except Exception as exc:
            self._record_warning(table_name, exc)
            return []

        return self._redact_sensitive_data(result.data or [])

    async def _safe_query_department_tasks(self) -> list[dict[str, Any]]:
        """Return department tasks created by or assigned to the current user."""
        try:
            query = (
                self.client.table("department_tasks")
                .select("*")
                .or_(
                    f"created_by.eq.{self._user_id},assigned_to.eq.{self._user_id}"
                )
                .order("created_at", desc=True)
            )
            result = await execute_async(
                query,
                op_name="personal_data_export.department_tasks",
            )
        except Exception as exc:
            self._record_warning("department_tasks", exc)
            return []

        return self._redact_sensitive_data(result.data or [])

    def _payload_to_json_bytes(self, payload: dict[str, Any]) -> bytes:
        """Serialize the payload to stable UTF-8 JSON bytes."""
        return json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")

    def _record_warning(self, section: str, exc: Exception) -> None:
        """Record a non-fatal export warning."""
        message = f"{section}: unavailable during export"
        self._warnings.append(message)
        logger.warning("%s for user %s: %s", message, self._user_id, exc)

    def _redact_sensitive_data(self, value: Any) -> Any:
        """Recursively redact sensitive values from the export payload."""
        if isinstance(value, list):
            return [self._redact_sensitive_data(item) for item in value]

        if isinstance(value, dict):
            config_key = str(value.get("config_key", "")).lower()
            is_sensitive_config = bool(value.get("is_sensitive")) or self._is_sensitive_key(
                config_key
            )

            redacted: dict[str, Any] = {}
            for key, item in value.items():
                key_lower = key.lower()

                if key_lower == "config_value" and is_sensitive_config:
                    redacted[key] = REDACTED_VALUE
                    continue

                if key_lower == "sync_cursor":
                    redacted[key] = REDACTED_VALUE if item else {}
                    continue

                if self._is_sensitive_key(key_lower):
                    redacted[key] = REDACTED_VALUE
                    continue

                redacted[key] = self._redact_sensitive_data(item)

            return redacted

        return value

    @staticmethod
    def _is_sensitive_key(key: str) -> bool:
        """Return whether a key name should be treated as sensitive."""
        normalized = key.lower()
        return any(keyword in normalized for keyword in SENSITIVE_KEYWORDS)


__all__ = ["PersonalDataExportService"]

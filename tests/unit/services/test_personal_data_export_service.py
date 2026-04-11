# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for PersonalDataExportService."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

USER_ID = "user-123"


class _FakeQuery:
    """Minimal fluent query object used by execute_async patches."""

    def __init__(self, table_name: str):
        self.table_name = table_name

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def or_(self, *_args, **_kwargs):
        return self


def _make_service(client: MagicMock | None = None):
    """Return a PersonalDataExportService with a mocked client."""
    client = client or MagicMock()
    client.table.side_effect = lambda table_name: _FakeQuery(table_name)

    with patch(
        "app.services.personal_data_export_service.get_service_client",
        return_value=client,
    ):
        from app.services.personal_data_export_service import PersonalDataExportService

        return PersonalDataExportService(user_id=USER_ID)


@pytest.mark.asyncio
async def test_build_export_payload_redacts_sensitive_fields_and_keeps_sections():
    """Sensitive values are redacted while the export remains complete."""
    client = MagicMock()
    client.table.side_effect = lambda table_name: _FakeQuery(table_name)
    client.auth.admin.get_user_by_id.return_value = SimpleNamespace(
        user=SimpleNamespace(
            id=USER_ID,
            email="founder@example.com",
            phone="+255700000000",
            role="authenticated",
            created_at="2026-04-01T10:00:00Z",
            last_sign_in_at="2026-04-11T08:00:00Z",
            app_metadata={"provider": "google", "refresh_token": "hide-me"},
            user_metadata={"full_name": "Founder", "access_token": "hide-me-too"},
            identities=[SimpleNamespace(provider="google")],
        )
    )
    service = _make_service(client)

    table_data = {
        "users_profile": [{"user_id": USER_ID, "full_name": "Founder"}],
        "user_executive_agents": [{"user_id": USER_ID, "system_prompt_override": "helpful"}],
        "data_deletion_requests": [{"status": "pending"}],
        "sessions": [{"session_id": "session-1", "state": {"provider_token": "hidden"}}],
        "session_events": [{"event_data": {"access_token": "hidden", "message": "hello"}}],
        "workflow_executions": [{"id": "exec-1", "name": "Launch Plan"}],
        "workflow_steps": [{"execution_id": "exec-1", "input_data": {"refresh_token": "hidden"}}],
        "campaigns": [{"id": "campaign-1"}],
        "content_bundles": [{"id": "bundle-1"}],
        "vault_documents": [{"id": "doc-1"}],
        "agent_google_docs": [{"id": "gdoc-1"}],
        "contacts": [{"id": "contact-1"}],
        "contact_activities": [{"id": "activity-1"}],
        "financial_records": [{"id": "fin-1"}],
        "department_tasks": [{"id": "task-1"}],
        "support_tickets": [{"id": "ticket-1"}],
        "recruitment_jobs": [{"id": "job-1"}],
        "recruitment_candidates": [{"id": "candidate-1"}],
        "compliance_audits": [{"id": "audit-1"}],
        "compliance_risks": [{"id": "risk-1"}],
        "connected_accounts": [{"platform": "google", "account_name": "Founder"}],
        "integration_credentials": [
            {
                "provider": "google_workspace",
                "access_token": "encrypted-access",
                "refresh_token": "encrypted-refresh",
                "account_name": "founder@example.com",
            }
        ],
        "integration_sync_state": [
            {
                "provider": "google_workspace",
                "sync_cursor": {"page": "opaque"},
                "error_count": 0,
            }
        ],
        "user_configurations": [
            {
                "config_key": "OPENAI_API_KEY",
                "config_value": "sk-secret",
                "is_sensitive": True,
            },
            {
                "config_key": "theme",
                "config_value": "light",
                "is_sensitive": False,
            },
        ],
    }

    async def _fake_execute_async(_query, *, op_name=None, **_kwargs):
        table_name = str(op_name).rsplit(".", 1)[-1]
        return SimpleNamespace(data=table_data.get(table_name, []))

    with patch(
        "app.services.personal_data_export_service.execute_async",
        new=AsyncMock(side_effect=_fake_execute_async),
    ):
        payload = await service.build_export_payload()

    assert payload["manifest"]["sections"]
    assert "integrations" in payload["manifest"]["sections"]
    assert payload["account"]["auth_user"]["user_metadata"]["access_token"] == "[REDACTED]"
    assert payload["account"]["auth_user"]["app_metadata"]["refresh_token"] == "[REDACTED]"
    assert (
        payload["integrations"]["integration_credentials"][0]["access_token"]
        == "[REDACTED]"
    )
    assert (
        payload["integrations"]["integration_credentials"][0]["refresh_token"]
        == "[REDACTED]"
    )
    assert (
        payload["integrations"]["integration_sync_state"][0]["sync_cursor"]
        == "[REDACTED]"
    )
    assert (
        payload["configuration"]["user_configurations"][0]["config_value"]
        == "[REDACTED]"
    )
    assert payload["configuration"]["user_configurations"][1]["config_value"] == "light"
    assert payload["conversations"]["session_events"][0]["event_data"]["access_token"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_build_export_payload_handles_empty_sections_without_crashing():
    """Empty result sets still produce a valid manifest and payload."""
    client = MagicMock()
    client.table.side_effect = lambda table_name: _FakeQuery(table_name)
    client.auth.admin.get_user_by_id.return_value = SimpleNamespace(user=None)
    service = _make_service(client)

    with patch(
        "app.services.personal_data_export_service.execute_async",
        new=AsyncMock(return_value=SimpleNamespace(data=[])),
    ):
        payload = await service.build_export_payload()

    assert payload["manifest"]["format"] == "json"
    assert payload["account"]["auth_user"] is None
    assert payload["account"]["profile"] is None
    assert payload["initiatives"] == []
    assert payload["workflows"]["workflow_steps"] == []
    assert payload["configuration"]["user_configurations"] == []


@pytest.mark.asyncio
async def test_export_personal_data_uploads_archive_and_returns_signed_url():
    """export_personal_data returns signed download metadata for the archive."""
    service = _make_service(MagicMock())

    with (
        patch.object(
            service,
            "build_export_payload",
            new=AsyncMock(
                return_value={
                    "manifest": {
                        "generated_at": "2026-04-11T12:00:00Z",
                        "sections": ["account", "privacy"],
                        "warnings": [],
                    },
                    "account": {"auth_user": {"email": "founder@example.com"}},
                }
            ),
        ),
        patch.object(service, "_upload_export_bytes", new=AsyncMock()) as upload_mock,
        patch.object(
            service,
            "_create_signed_url",
            new=AsyncMock(return_value="https://storage.example.com/signed/export.json"),
        ),
    ):
        result = await service.export_personal_data()

    upload_mock.assert_awaited_once()
    assert result["url"] == "https://storage.example.com/signed/export.json"
    assert result["format"] == "json"
    assert result["generated_at"] == "2026-04-11T12:00:00Z"
    assert result["sections"] == ["account", "privacy"]
    assert result["filename"].endswith(".json")
    assert result["size_bytes"] > 0

# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""End-to-end audit middleware integration test (AUTH-04).

Wires the real ``AuditLogMiddleware`` into a small FastAPI test app, mocks
the governance service at the boundary, and asserts a row with the exact
shape Plan 49-05 (AUTH-05) admin viewer will expect lands in
``governance_audit_log``.

This is the contract Plan 05 will rely on:
- ``user_id``      — JWT ``sub`` claim resolved by middleware
- ``action_type``  — ``f"{resource_type}.{verb}"``
- ``resource_type``— derived from path prefix via AUDITED_ROUTES
- ``resource_id``  — first path segment after the prefix, or None
- ``details``      — ``{"method", "path", "status_code"}``
- ``ip_address``   — request.client.host (or None in tests)
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.audit_log import AuditLogMiddleware


@pytest.fixture
def real_app() -> FastAPI:
    """Minimal FastAPI app wired with the real AuditLogMiddleware."""
    app = FastAPI()
    app.add_middleware(AuditLogMiddleware)

    @app.post("/initiatives")
    def create_initiative():
        return {"id": "new-init-1"}

    @app.delete("/workflows/{wf_id}")
    def delete_workflow(wf_id: str):
        return {"deleted": wf_id}

    @app.put("/content/{content_id}")
    def update_content(content_id: str):
        return {"id": content_id}

    return app


@pytest.mark.asyncio
async def test_post_initiatives_writes_governance_audit_row(real_app):
    """POST /initiatives → row with user_id, action_type=initiative.created,
    resource_type=initiative, resource_id=None, details has method/path/status.
    """
    captured_rows: list[dict] = []

    async def fake_log_event(**kwargs):
        captured_rows.append(kwargs)

    with (
        patch(
            "app.middleware.audit_log.verify_token_fast",
            return_value={"sub": "user-42"},
        ),
        patch("app.middleware.audit_log.get_governance_service") as mock_gov,
    ):
        mock_gov.return_value.log_event = AsyncMock(side_effect=fake_log_event)

        client = TestClient(real_app)
        r = client.post("/initiatives", headers={"Authorization": "Bearer fake-token"})
        assert r.status_code == 200

        # let create_task drain
        await asyncio.sleep(0.05)

    assert len(captured_rows) == 1
    row = captured_rows[0]
    assert row["user_id"] == "user-42"
    assert row["action_type"] == "initiative.created"
    assert row["resource_type"] == "initiative"
    assert row["resource_id"] is None
    assert row["details"]["method"] == "POST"
    assert row["details"]["path"] == "/initiatives"
    assert row["details"]["status_code"] == 200


@pytest.mark.asyncio
async def test_delete_workflow_writes_audit_with_resource_id(real_app):
    """DELETE /workflows/wf-99 → action=workflow.deleted, resource_id=wf-99."""
    captured_rows: list[dict] = []

    async def fake_log_event(**kwargs):
        captured_rows.append(kwargs)

    with (
        patch(
            "app.middleware.audit_log.verify_token_fast",
            return_value={"sub": "user-42"},
        ),
        patch("app.middleware.audit_log.get_governance_service") as mock_gov,
    ):
        mock_gov.return_value.log_event = AsyncMock(side_effect=fake_log_event)

        client = TestClient(real_app)
        r = client.delete(
            "/workflows/wf-99", headers={"Authorization": "Bearer fake-token"}
        )
        assert r.status_code == 200

        await asyncio.sleep(0.05)

    assert len(captured_rows) == 1
    row = captured_rows[0]
    assert row["action_type"] == "workflow.deleted"
    assert row["resource_type"] == "workflow"
    assert row["resource_id"] == "wf-99"
    assert row["details"]["method"] == "DELETE"
    assert row["details"]["path"] == "/workflows/wf-99"
    assert row["details"]["status_code"] == 200


@pytest.mark.asyncio
async def test_put_content_writes_audit_update(real_app):
    """PUT /content/c-7 → action=content.updated, resource_type=content."""
    captured_rows: list[dict] = []

    async def fake_log_event(**kwargs):
        captured_rows.append(kwargs)

    with (
        patch(
            "app.middleware.audit_log.verify_token_fast",
            return_value={"sub": "user-42"},
        ),
        patch("app.middleware.audit_log.get_governance_service") as mock_gov,
    ):
        mock_gov.return_value.log_event = AsyncMock(side_effect=fake_log_event)

        client = TestClient(real_app)
        r = client.put("/content/c-7", headers={"Authorization": "Bearer fake-token"})
        assert r.status_code == 200

        await asyncio.sleep(0.05)

    assert len(captured_rows) == 1
    row = captured_rows[0]
    assert row["action_type"] == "content.updated"
    assert row["resource_type"] == "content"
    assert row["resource_id"] == "c-7"
    assert row["details"]["method"] == "PUT"

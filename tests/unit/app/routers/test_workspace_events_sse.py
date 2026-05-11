# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""GET /workspace/events -- SSE endpoint streams typed events as ``data:`` frames."""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agents.runtime.types import (
    WorkspaceArtifactEvent,
    WorkspaceProgressEvent,
)
from app.routers import workspace as workspace_router
from app.routers.onboarding import get_current_user_id


@pytest.fixture
def app(monkeypatch):
    user_id = "11111111-1111-1111-1111-111111111111"

    async def override_user():
        return user_id

    progress = WorkspaceProgressEvent(
        agent_id="data", contract_id=None, item="x", status="started"
    )
    artifact = WorkspaceArtifactEvent(
        agent_id="data",
        contract_id=None,
        artifact_kind="report",
        ref="vault://abc",
        summary="ok",
        preview_url=None,
    )

    async def fake_subscribe(uid: UUID):
        assert str(uid) == user_id
        yield progress
        yield artifact

    monkeypatch.setattr(
        workspace_router.workspace_event_bus, "subscribe", fake_subscribe
    )

    app = FastAPI()
    app.include_router(workspace_router.router)
    app.dependency_overrides[get_current_user_id] = override_user
    return app


def test_workspace_events_emits_two_data_frames(app):
    """The SSE stream yields one ``data:`` frame per pumped event."""
    with TestClient(app) as client:
        with client.stream("GET", "/workspace/events") as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            body = b""
            for chunk in response.iter_raw():
                body += chunk
                if body.count(b"data:") >= 2:
                    break

    text = body.decode("utf-8")
    assert text.count("data:") >= 2
    assert '"kind":"progress"' in text
    assert '"kind":"artifact"' in text
    # SSE framing: each event ends with a blank line.
    assert "\n\n" in text

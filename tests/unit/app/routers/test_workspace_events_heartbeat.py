# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Idle SSE streams must send a heartbeat comment so proxies don't drop them."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import workspace as workspace_router
from app.routers.onboarding import get_current_user_id


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(workspace_router, "_HEARTBEAT_INTERVAL_S", 0.05)

    async def slow_subscribe(uid):  # noqa: ARG001 -- never yields
        await asyncio.sleep(10)
        if False:  # pragma: no cover -- make this an async generator
            yield

    monkeypatch.setattr(
        workspace_router.workspace_event_bus, "subscribe", slow_subscribe
    )

    async def override_user():
        return "11111111-1111-1111-1111-111111111111"

    app = FastAPI()
    app.include_router(workspace_router.router)
    app.dependency_overrides[get_current_user_id] = override_user
    return app


def test_idle_stream_emits_heartbeat(app):
    """An idle stream emits ``: heartbeat`` comments at the configured interval."""
    with TestClient(app) as client:
        with client.stream("GET", "/workspace/events") as response:
            assert response.status_code == 200
            body = b""
            for chunk in response.iter_raw():
                body += chunk
                if b": heartbeat" in body:
                    break
            assert b": heartbeat" in body

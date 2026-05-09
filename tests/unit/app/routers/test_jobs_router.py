# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the long-running job progress router (LONGTASK-01).

Covers ``GET /jobs/{job_id}/progress``:
- happy path returns the projected row shape
- 404 when the row does not exist
- 403 when the row exists but belongs to another user
- completed jobs include a ``result`` field
- failed jobs include an ``error`` field
"""

from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Stub the onboarding router import so we don't pull the whole auth chain.
# ---------------------------------------------------------------------------

if "app.routers.onboarding" not in sys.modules:
    _stub = types.ModuleType("app.routers.onboarding")

    async def _default_get_current_user_id() -> str:  # noqa: RUF029
        return "user-test"

    _stub.get_current_user_id = _default_get_current_user_id
    _stub.router = MagicMock()
    sys.modules["app.routers.onboarding"] = _stub


def _build_app(*, user_id: str = "user-test"):
    """Build a tiny FastAPI app wrapping the jobs router."""
    from app.routers.jobs import router
    from app.routers.onboarding import get_current_user_id

    app = FastAPI()

    async def _fake_user_id() -> str:
        return user_id

    app.dependency_overrides[get_current_user_id] = _fake_user_id
    app.include_router(router)
    return app


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_job_progress_returns_processing_row():
    row = {
        "id": "job-1",
        "user_id": "user-test",
        "job_type": "daily_report",
        "status": "processing",
        "input_data": {"foo": "bar"},
        "output_data": {"progress_pct": 55, "message": "halfway"},
        "started_at": "2026-05-09T00:00:00Z",
        "created_at": "2026-05-09T00:00:00Z",
        "completed_at": None,
        "attempt_count": 1,
    }
    with patch(
        "app.routers.jobs.get_job_row", AsyncMock(return_value=row)
    ):
        app = _build_app()
        client = TestClient(app)
        resp = client.get("/jobs/job-1/progress")
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == "job-1"
    assert body["kind"] == "daily_report"
    assert body["status"] == "processing"
    assert body["progress_pct"] == 55
    assert body["message"] == "halfway"
    # Processing jobs do NOT carry a result field
    assert "result" not in body


@pytest.mark.asyncio
async def test_get_job_progress_returns_completed_row_with_result():
    row = {
        "id": "job-2",
        "user_id": "user-test",
        "job_type": "weekly_digest",
        "status": "completed",
        "input_data": {},
        "output_data": {"summary": "done", "items": 5},
        "started_at": "2026-05-09T00:00:00Z",
        "completed_at": "2026-05-09T00:05:00Z",
        "created_at": "2026-05-09T00:00:00Z",
        "attempt_count": 1,
    }
    with patch(
        "app.routers.jobs.get_job_row", AsyncMock(return_value=row)
    ):
        app = _build_app()
        resp = TestClient(app).get("/jobs/job-2/progress")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["result"] == {"summary": "done", "items": 5}


@pytest.mark.asyncio
async def test_get_job_progress_returns_failed_row_with_error():
    row = {
        "id": "job-3",
        "user_id": "user-test",
        "job_type": "daily_report",
        "status": "failed",
        "input_data": {},
        "output_data": {},
        "error_message": "boom",
        "started_at": "2026-05-09T00:00:00Z",
        "completed_at": "2026-05-09T00:01:00Z",
        "created_at": "2026-05-09T00:00:00Z",
        "attempt_count": 3,
    }
    with patch(
        "app.routers.jobs.get_job_row", AsyncMock(return_value=row)
    ):
        app = _build_app()
        resp = TestClient(app).get("/jobs/job-3/progress")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failed"
    assert body["error"] == "boom"


# ---------------------------------------------------------------------------
# 404 / 403
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_job_progress_404_for_unknown_id():
    with patch(
        "app.routers.jobs.get_job_row", AsyncMock(return_value=None)
    ):
        app = _build_app()
        resp = TestClient(app).get("/jobs/missing/progress")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_job_progress_403_for_other_user():
    row = {
        "id": "job-other",
        "user_id": "someone-else",
        "job_type": "daily_report",
        "status": "processing",
        "input_data": {},
        "output_data": {},
    }
    with patch(
        "app.routers.jobs.get_job_row", AsyncMock(return_value=row)
    ):
        app = _build_app(user_id="user-test")
        resp = TestClient(app).get("/jobs/job-other/progress")
    assert resp.status_code == 403

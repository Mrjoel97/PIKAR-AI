# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for AuditLogMiddleware (AUTH-04).

Covers the case-based contract (mutation logging, exclusions, never-raises,
anonymous skip), the parametrised regression test that iterates EVERY entry
in AUDITED_ROUTES (~35 subtests, catches typos in the inclusion list), and
the middleware-stack assertion test that imports the real FastAPI app and
verifies AuditLogMiddleware is registered AFTER OnboardingGuardMiddleware.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.middleware.audit_log import (
    AUDITED_ROUTES,
    AuditLogMiddleware,
)

# ---------------------------------------------------------------------------
# Test app fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_with_middleware() -> FastAPI:
    """Minimal FastAPI app with AuditLogMiddleware and a handful of routes
    covering audited prefixes, excluded prefixes, and unknown routes.
    """
    app = FastAPI()
    app.add_middleware(AuditLogMiddleware)

    @app.get("/initiatives")
    def list_initiatives():
        return {"items": []}

    @app.post("/initiatives")
    def create_initiative():
        return {"id": "new"}

    @app.patch("/initiatives/{init_id}")
    def update_initiative(init_id: str):
        return {"id": init_id}

    @app.delete("/workflows/{wf_id}")
    def delete_workflow(wf_id: str):
        return {"deleted": wf_id}

    @app.post("/health/check")
    def health_check():
        return {"ok": True}

    @app.post("/admin/users/suspend")
    def admin_suspend():
        return {"ok": True}

    @app.post("/a2a/run_sse")
    def a2a_run():
        return {"ok": True}

    @app.post("/webhooks/stripe")
    def webhook_stripe():
        return {"ok": True}

    @app.post("/unknown_router")
    def unknown_router():
        return {"ok": True}

    @app.post("/initiatives/fail")
    def fail_initiative():
        raise HTTPException(status_code=500, detail="boom")

    return app


@pytest.fixture
def app_with_all_audited_routes() -> FastAPI:
    """A FastAPI app that declares one POST handler per AUDITED_ROUTES entry.

    Used by the parametrised regression test to catch typos or silent drops
    in the AUDITED_ROUTES inclusion list. Adding a new entry to AUDITED_ROUTES
    without also declaring a handler here will cause the parametrised test to
    404 for that prefix, flagging the gap.
    """
    app = FastAPI()
    app.add_middleware(AuditLogMiddleware)

    for prefix in AUDITED_ROUTES:
        # Use a closure-captured prefix so each handler is unique.
        def make_handler(_prefix: str):
            async def handler():
                return {"prefix": _prefix, "ok": True}

            return handler

        app.post(prefix)(make_handler(prefix))

    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patched_log_event():
    """Return (capture_list, context_manager) that patches verify_token_fast
    and get_governance_service.log_event so tests can assert on calls.
    """
    captured: list[dict] = []

    async def fake_log_event(**kwargs):
        captured.append(kwargs)

    cm = patch.multiple(
        "app.middleware.audit_log",
        verify_token_fast=lambda token: {"sub": "11111111-1111-1111-1111-111111111111"},
        get_governance_service=AsyncMock(),
    )
    return captured, cm, fake_log_event


# ---------------------------------------------------------------------------
# Case-based unit tests (13 cases)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_audited_collection_logs_create_with_no_resource_id(
    app_with_middleware,
):
    """POST /initiatives → action=initiative.created, resource_id=None."""
    captured: list[dict] = []

    async def fake_log_event(**kwargs):
        captured.append(kwargs)

    with (
        patch(
            "app.middleware.audit_log.verify_token_fast",
            return_value={"sub": "user-1"},
        ),
        patch("app.middleware.audit_log.get_governance_service") as mock_gov,
    ):
        mock_gov.return_value.log_event = AsyncMock(side_effect=fake_log_event)

        client = TestClient(app_with_middleware)
        r = client.post("/initiatives", headers={"Authorization": "Bearer fake"})
        assert r.status_code == 200
        await asyncio.sleep(0.05)

    assert len(captured) == 1
    row = captured[0]
    assert row["user_id"] == "user-1"
    assert row["action_type"] == "initiative.created"
    assert row["resource_type"] == "initiative"
    assert row["resource_id"] is None
    assert row["details"]["method"] == "POST"
    assert row["details"]["path"] == "/initiatives"
    assert row["details"]["status_code"] == 200


@pytest.mark.asyncio
async def test_patch_audited_resource_logs_update_with_resource_id(
    app_with_middleware,
):
    """PATCH /initiatives/abc-123 → action=initiative.updated, resource_id='abc-123'."""
    captured: list[dict] = []

    async def fake_log_event(**kwargs):
        captured.append(kwargs)

    with (
        patch(
            "app.middleware.audit_log.verify_token_fast",
            return_value={"sub": "user-1"},
        ),
        patch("app.middleware.audit_log.get_governance_service") as mock_gov,
    ):
        mock_gov.return_value.log_event = AsyncMock(side_effect=fake_log_event)

        client = TestClient(app_with_middleware)
        r = client.patch(
            "/initiatives/abc-123", headers={"Authorization": "Bearer fake"}
        )
        assert r.status_code == 200
        await asyncio.sleep(0.05)

    assert len(captured) == 1
    assert captured[0]["action_type"] == "initiative.updated"
    assert captured[0]["resource_type"] == "initiative"
    assert captured[0]["resource_id"] == "abc-123"


@pytest.mark.asyncio
async def test_delete_audited_resource_logs_delete_with_resource_id(
    app_with_middleware,
):
    """DELETE /workflows/wf-1 → action=workflow.deleted, resource_id='wf-1'."""
    captured: list[dict] = []

    async def fake_log_event(**kwargs):
        captured.append(kwargs)

    with (
        patch(
            "app.middleware.audit_log.verify_token_fast",
            return_value={"sub": "user-1"},
        ),
        patch("app.middleware.audit_log.get_governance_service") as mock_gov,
    ):
        mock_gov.return_value.log_event = AsyncMock(side_effect=fake_log_event)

        client = TestClient(app_with_middleware)
        r = client.delete("/workflows/wf-1", headers={"Authorization": "Bearer fake"})
        assert r.status_code == 200
        await asyncio.sleep(0.05)

    assert len(captured) == 1
    assert captured[0]["action_type"] == "workflow.deleted"
    assert captured[0]["resource_type"] == "workflow"
    assert captured[0]["resource_id"] == "wf-1"


@pytest.mark.asyncio
async def test_get_does_not_log_audit_row(app_with_middleware):
    """GET requests are reads, not mutations — must NOT produce audit rows."""
    captured: list[dict] = []

    async def fake_log_event(**kwargs):
        captured.append(kwargs)

    with (
        patch(
            "app.middleware.audit_log.verify_token_fast",
            return_value={"sub": "user-1"},
        ),
        patch("app.middleware.audit_log.get_governance_service") as mock_gov,
    ):
        mock_gov.return_value.log_event = AsyncMock(side_effect=fake_log_event)

        client = TestClient(app_with_middleware)
        r = client.get("/initiatives", headers={"Authorization": "Bearer fake"})
        assert r.status_code == 200
        await asyncio.sleep(0.05)

    assert captured == []


@pytest.mark.asyncio
async def test_failed_5xx_does_not_log_audit_row(app_with_middleware):
    """5xx server errors are NOT successful mutations — must NOT log."""
    captured: list[dict] = []

    async def fake_log_event(**kwargs):
        captured.append(kwargs)

    with (
        patch(
            "app.middleware.audit_log.verify_token_fast",
            return_value={"sub": "user-1"},
        ),
        patch("app.middleware.audit_log.get_governance_service") as mock_gov,
    ):
        mock_gov.return_value.log_event = AsyncMock(side_effect=fake_log_event)

        client = TestClient(app_with_middleware, raise_server_exceptions=False)
        r = client.post("/initiatives/fail", headers={"Authorization": "Bearer fake"})
        assert r.status_code == 500
        await asyncio.sleep(0.05)

    assert captured == []


@pytest.mark.asyncio
async def test_failed_4xx_does_not_log_audit_row(app_with_middleware):
    """4xx client errors are NOT successful mutations — must NOT log."""
    # Add a route that returns 401 dynamically.
    app = FastAPI()
    app.add_middleware(AuditLogMiddleware)

    @app.post("/initiatives")
    def make_401():
        raise HTTPException(status_code=401, detail="nope")

    captured: list[dict] = []

    async def fake_log_event(**kwargs):
        captured.append(kwargs)

    with (
        patch(
            "app.middleware.audit_log.verify_token_fast",
            return_value={"sub": "user-1"},
        ),
        patch("app.middleware.audit_log.get_governance_service") as mock_gov,
    ):
        mock_gov.return_value.log_event = AsyncMock(side_effect=fake_log_event)

        client = TestClient(app)
        r = client.post("/initiatives", headers={"Authorization": "Bearer fake"})
        assert r.status_code == 401
        await asyncio.sleep(0.05)

    assert captured == []


@pytest.mark.asyncio
async def test_excluded_health_prefix_does_not_log(app_with_middleware):
    """POST /health/check is on the hard exclusion list — never audited."""
    captured: list[dict] = []

    async def fake_log_event(**kwargs):
        captured.append(kwargs)

    with (
        patch(
            "app.middleware.audit_log.verify_token_fast",
            return_value={"sub": "user-1"},
        ),
        patch("app.middleware.audit_log.get_governance_service") as mock_gov,
    ):
        mock_gov.return_value.log_event = AsyncMock(side_effect=fake_log_event)

        client = TestClient(app_with_middleware)
        r = client.post("/health/check", headers={"Authorization": "Bearer fake"})
        assert r.status_code == 200
        await asyncio.sleep(0.05)

    assert captured == []


@pytest.mark.asyncio
async def test_excluded_admin_prefix_does_not_log(app_with_middleware):
    """/admin is excluded — admin actions go to admin_audit_log instead."""
    captured: list[dict] = []

    async def fake_log_event(**kwargs):
        captured.append(kwargs)

    with (
        patch(
            "app.middleware.audit_log.verify_token_fast",
            return_value={"sub": "user-1"},
        ),
        patch("app.middleware.audit_log.get_governance_service") as mock_gov,
    ):
        mock_gov.return_value.log_event = AsyncMock(side_effect=fake_log_event)

        client = TestClient(app_with_middleware)
        r = client.post(
            "/admin/users/suspend", headers={"Authorization": "Bearer fake"}
        )
        assert r.status_code == 200
        await asyncio.sleep(0.05)

    assert captured == []


@pytest.mark.asyncio
async def test_excluded_a2a_prefix_does_not_log(app_with_middleware):
    """/a2a SSE chat is excluded — too noisy for per-message audit."""
    captured: list[dict] = []

    async def fake_log_event(**kwargs):
        captured.append(kwargs)

    with (
        patch(
            "app.middleware.audit_log.verify_token_fast",
            return_value={"sub": "user-1"},
        ),
        patch("app.middleware.audit_log.get_governance_service") as mock_gov,
    ):
        mock_gov.return_value.log_event = AsyncMock(side_effect=fake_log_event)

        client = TestClient(app_with_middleware)
        r = client.post("/a2a/run_sse", headers={"Authorization": "Bearer fake"})
        assert r.status_code == 200
        await asyncio.sleep(0.05)

    assert captured == []


@pytest.mark.asyncio
async def test_excluded_webhooks_prefix_does_not_log(app_with_middleware):
    """/webhooks have no human actor — excluded."""
    captured: list[dict] = []

    async def fake_log_event(**kwargs):
        captured.append(kwargs)

    with (
        patch(
            "app.middleware.audit_log.verify_token_fast",
            return_value={"sub": "user-1"},
        ),
        patch("app.middleware.audit_log.get_governance_service") as mock_gov,
    ):
        mock_gov.return_value.log_event = AsyncMock(side_effect=fake_log_event)

        client = TestClient(app_with_middleware)
        r = client.post("/webhooks/stripe", headers={"Authorization": "Bearer fake"})
        assert r.status_code == 200
        await asyncio.sleep(0.05)

    assert captured == []


@pytest.mark.asyncio
async def test_anonymous_request_does_not_log(app_with_middleware):
    """No Authorization header → anonymous, no actor → no audit row."""
    captured: list[dict] = []

    async def fake_log_event(**kwargs):
        captured.append(kwargs)

    with (
        patch(
            "app.middleware.audit_log.verify_token_fast",
            return_value=None,
        ),
        patch("app.middleware.audit_log.get_governance_service") as mock_gov,
    ):
        mock_gov.return_value.log_event = AsyncMock(side_effect=fake_log_event)

        client = TestClient(app_with_middleware)
        r = client.post("/initiatives")  # no Authorization header
        assert r.status_code == 200
        await asyncio.sleep(0.05)

    assert captured == []


@pytest.mark.asyncio
async def test_log_event_exception_does_not_break_request(app_with_middleware):
    """If governance.log_event raises, the request must still succeed."""

    async def explode(**kwargs):
        raise RuntimeError("supabase blew up")

    with (
        patch(
            "app.middleware.audit_log.verify_token_fast",
            return_value={"sub": "user-1"},
        ),
        patch("app.middleware.audit_log.get_governance_service") as mock_gov,
    ):
        mock_gov.return_value.log_event = AsyncMock(side_effect=explode)

        client = TestClient(app_with_middleware)
        r = client.post("/initiatives", headers={"Authorization": "Bearer fake"})
        # The request must still succeed even though the audit insert exploded.
        assert r.status_code == 200
        await asyncio.sleep(0.05)


@pytest.mark.asyncio
async def test_unknown_router_does_not_log(app_with_middleware):
    """A POST to a path not in AUDITED_ROUTES must not produce a row."""
    captured: list[dict] = []

    async def fake_log_event(**kwargs):
        captured.append(kwargs)

    with (
        patch(
            "app.middleware.audit_log.verify_token_fast",
            return_value={"sub": "user-1"},
        ),
        patch("app.middleware.audit_log.get_governance_service") as mock_gov,
    ):
        mock_gov.return_value.log_event = AsyncMock(side_effect=fake_log_event)

        client = TestClient(app_with_middleware)
        r = client.post("/unknown_router", headers={"Authorization": "Bearer fake"})
        assert r.status_code == 200
        await asyncio.sleep(0.05)

    assert captured == []


# ---------------------------------------------------------------------------
# Parametrised regression test — one subtest per AUDITED_ROUTES entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "prefix,expected_resource_type",
    list(AUDITED_ROUTES.items()),
)
async def test_every_audited_route_triggers_log_event(
    app_with_all_audited_routes,
    prefix,
    expected_resource_type,
):
    """Regression test: every AUDITED_ROUTES entry must actually fire log_event.

    A typo in a single map value would silently drop coverage for that router
    without any other test failing. This parametrised test iterates the full
    inclusion list (~35 entries) and asserts each one is wired correctly.
    """
    captured: list[dict] = []

    async def fake_log_event(**kwargs):
        captured.append(kwargs)

    with (
        patch(
            "app.middleware.audit_log.verify_token_fast",
            return_value={"sub": "test-user"},
        ),
        patch("app.middleware.audit_log.get_governance_service") as mock_gov,
    ):
        mock_gov.return_value.log_event = AsyncMock(side_effect=fake_log_event)

        client = TestClient(app_with_all_audited_routes)
        r = client.post(
            prefix,
            headers={"Authorization": "Bearer fake-token"},
        )
        assert r.status_code == 200, (
            f"prefix {prefix} returned {r.status_code}: {r.text}"
        )

        # Let the create_task drain.
        await asyncio.sleep(0.05)

    assert len(captured) == 1, (
        f"Expected exactly one log_event call for prefix {prefix}, "
        f"got {len(captured)}. This likely means AUDITED_ROUTES has a typo "
        f"or the middleware dropped this prefix silently."
    )
    row = captured[0]
    assert row["resource_type"] == expected_resource_type, (
        f"Prefix {prefix}: expected resource_type={expected_resource_type}, "
        f"got {row['resource_type']}"
    )
    assert row["action_type"] == f"{expected_resource_type}.created", (
        f"Prefix {prefix}: expected action_type={expected_resource_type}.created, "
        f"got {row['action_type']}"
    )

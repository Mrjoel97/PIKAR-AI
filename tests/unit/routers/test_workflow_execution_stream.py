"""Verify GET /workflows/executions/{id}/stream returns SSE."""

from __future__ import annotations

import asyncio
import json
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Stub heavy dependencies BEFORE importing the router so the import succeeds
# in the unit-test environment (no real DB / ADK / Redis).
# ---------------------------------------------------------------------------


def _stub(path: str, **attrs: object) -> None:
    """Insert a stub module into sys.modules if not already present."""
    if path not in sys.modules:
        mod = types.ModuleType(path)
        for name, val in attrs.items():
            setattr(mod, name, val)
        sys.modules[path] = mod


# Auth / onboarding — provide a fake get_current_user_id.
async def _default_get_current_user_id() -> str:  # noqa: RUF029
    return "user-1"


from fastapi import APIRouter as _APIRouter  # noqa: PLC0415

_stub(
    "app.routers.onboarding",
    get_current_user_id=_default_get_current_user_id,
    # Use a real APIRouter so fast_api_app.include_router() gets a proper
    # lifespan_context (yields None) instead of a MagicMock that yields an
    # AsyncMock and breaks FastAPI's merged_lifespan dict-unpack.
    router=_APIRouter(),
)

# Rate limiter — disable throttling for tests.
if "app.middleware.rate_limiter" not in sys.modules:
    _rl_mod = types.ModuleType("app.middleware.rate_limiter")
    _rl_limiter = MagicMock()
    _rl_limiter.limit = lambda *a, **kw: (lambda fn: fn)
    # Set enabled=False so SlowAPIMiddleware skips rate-limit checks entirely,
    # preventing 'State has no attribute view_rate_limit' in combined test runs.
    _rl_limiter.enabled = False
    _rl_mod.limiter = _rl_limiter
    _rl_mod.get_user_persona_limit = MagicMock(return_value="1000/minute")
    _rl_mod._parse_limit_int = MagicMock(return_value=1000)
    _rl_mod.build_rate_limit_headers = MagicMock(return_value={})
    _rl_mod.redis_sliding_window_check = AsyncMock(return_value=(True, 0))
    sys.modules["app.middleware.rate_limiter"] = _rl_mod

# Feature gate — pass through (always allow).
if "app.middleware.feature_gate" not in sys.modules:
    _fg_mod = types.ModuleType("app.middleware.feature_gate")

    def _require_feature(_key: str):  # noqa: ANN001
        async def _gate() -> None:  # noqa: RUF029
            return None

        return _gate

    _fg_mod.require_feature = _require_feature
    sys.modules["app.middleware.feature_gate"] = _fg_mod

# Build a realistic SSEAcquireResult-like object that unpacks as a 3-tuple
# and has a .reason attribute.


class _FakeSSERejectReason:
    SERVER_BACKPRESSURE = "SERVER_BACKPRESSURE"


class _FakeSSEAcquireResult(tuple):
    """Minimal tuple-unpackable SSE result for tests."""

    def __new__(cls, acquired: bool, active: int, limit: int, reason=None):
        inst = super().__new__(cls, (acquired, active, limit))
        inst.acquired = acquired
        inst.active = active
        inst.limit = limit
        inst.reason = reason
        return inst


# SSE connection limits — always allow acquisition, no-op release.
# Extra attributes beyond what the stream endpoint needs are included so the
# stub does not cause ImportError if it leaks into the integration test session
# when pytest collects unit and integration tests in the same run.
_sse_mod = types.ModuleType("app.services.sse_connection_limits")
_sse_mod.SSERejectReason = _FakeSSERejectReason
_sse_mod.SSEAcquireResult = _FakeSSEAcquireResult
_sse_mod.try_acquire_sse_connection = AsyncMock(
    return_value=_FakeSSEAcquireResult(True, 1, 10)
)
_sse_mod.release_sse_connection = AsyncMock()
_sse_mod.get_sse_connection_limit = MagicMock(return_value=3)
_sse_mod.get_total_active_sse_count = AsyncMock(return_value=0)
_sse_mod.DEFAULT_SSE_MAX_CONNECTIONS_PER_USER = 3
_sse_mod.DEFAULT_SSE_MAX_NEW_CONN_PER_MINUTE = 10
_sse_mod.DEFAULT_SSE_MAX_TOTAL_CONNECTIONS = 500
_sse_mod.DEFAULT_SSE_CONN_TTL_SECONDS = 300
sys.modules["app.services.sse_connection_limits"] = _sse_mod

# Remaining heavy router imports that are not needed for the stream endpoint.
_stub("app.agents.tools.registry", TOOL_REGISTRY={})
_stub(
    "app.app_utils.auth",
    verify_service_auth=MagicMock(),
    verify_token_fast=MagicMock(),
    verify_scheduler=MagicMock(),
    verify_token=AsyncMock(),
    get_current_user=AsyncMock(),
    get_current_user_id=AsyncMock(return_value="user-1"),
    get_user_id_from_token=MagicMock(return_value=None),
    get_user_id_from_bearer_token=MagicMock(return_value=None),
    resolve_request_user_id=MagicMock(return_value=None),
    get_supabase_client=MagicMock(),
)
_stub("app.autonomy.agent_kernel", get_agent_kernel=MagicMock())
_stub(
    "app.personas.runtime",
    resolve_request_persona=MagicMock(),
    resolve_effective_persona=AsyncMock(return_value="solopreneur"),
    # The following names are imported by app.personas.__init__; including them
    # here prevents ImportError if this stub is still in sys.modules when
    # the integration tests collect app.fast_api_app in the same pytest session.
    filter_initiative_templates_for_persona=MagicMock(return_value=[]),
    filter_workflow_templates_for_persona=MagicMock(return_value=[]),
    initiative_template_matches_persona=MagicMock(return_value=True),
    workflow_template_matches_persona=MagicMock(return_value=True),
)
_stub(
    "app.services.feature_flags",
    is_user_allowed_for_workflow_canary=MagicMock(return_value=True),
    is_workflow_canary_enabled=MagicMock(return_value=False),
    is_workflow_kill_switch_enabled=MagicMock(return_value=False),
)
_stub("app.services.governance_service", get_governance_service=MagicMock())
_stub("app.services.supabase_async", execute_async=AsyncMock())
_stub(
    "app.workflows.contract_defaults",
    list_contract_safe_tool_names=MagicMock(return_value=[]),
)
_stub(
    "app.workflows.engine",
    get_workflow_engine=MagicMock(),
    # WorkflowEngine is imported directly in some integration tests; provide a
    # minimal class so `from app.workflows.engine import WorkflowEngine` succeeds
    # even if this stub is in sys.modules during the combined test run.
    WorkflowEngine=type("WorkflowEngine", (), {}),
)
_stub("app.workflows.user_workflow_service", get_user_workflow_service=MagicMock())
_stub(
    "app.config.feature_gating",
    FEATURE_ACCESS={},
    get_required_tier=MagicMock(return_value="solopreneur"),
    is_feature_allowed=MagicMock(return_value=True),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_supabase_client(user_id: str | None) -> MagicMock:
    """Return a fake Supabase client whose ownership query returns user_id."""
    execute_result = MagicMock()
    execute_result.data = [{"user_id": user_id}] if user_id is not None else []
    client = MagicMock()
    (
        client.table.return_value.select.return_value.eq.return_value.execute
    ) = MagicMock(return_value=execute_result)
    return client


# ---------------------------------------------------------------------------
# Build the test app
# ---------------------------------------------------------------------------


def _build_app(*, user_id: str = "user-1") -> FastAPI:
    """Build a minimal FastAPI app wrapping the workflows router."""
    # Force re-import so dependency overrides apply cleanly.
    sys.modules.pop("app.routers.workflows", None)

    from app.routers.onboarding import get_current_user_id  # noqa: PLC0415
    from app.routers.workflows import router  # noqa: PLC0415

    app = FastAPI()

    async def _fake_user_id() -> str:
        return user_id

    app.dependency_overrides[get_current_user_id] = _fake_user_id
    app.include_router(router)
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_emits_events_from_event_bus():
    """GET /workflows/executions/{id}/stream returns SSE and delivers events."""
    from app.workflows.event_bus import publish_workflow_event  # noqa: PLC0415

    app = _build_app()
    transport = ASGITransport(app=app)

    # Patch get_service_client in the router's namespace so the ownership check
    # passes without hitting the real Supabase singleton.
    with patch(
        "app.routers.workflows.get_service_client",
        return_value=_make_supabase_client("user-1"),
    ):
        async with AsyncClient(transport=transport, base_url="http://t") as client:

            async def emit_after_delay() -> None:
                await asyncio.sleep(0.05)
                # First emit a step event.
                await publish_workflow_event(
                    "workflow.execution.exec-1",
                    {"type": "workflow.step.completed", "step_id": "s1"},
                )
                # Then emit a terminal event so the generator exits and the stream closes.
                await asyncio.sleep(0.01)
                await publish_workflow_event(
                    "workflow.execution.exec-1",
                    {"type": "workflow.execution.completed"},
                )

            emit_task = asyncio.create_task(emit_after_delay())

            first_event = None
            async with client.stream(
                "GET",
                "/workflows/executions/exec-1/stream",
            ) as response:
                assert response.status_code == 200
                assert response.headers["content-type"].startswith("text/event-stream")
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        payload = json.loads(line[6:])
                        if first_event is None:
                            first_event = payload
                        # Keep iterating until stream closes naturally on terminal event.

            await emit_task

    assert first_event is not None
    assert first_event["type"] == "workflow.step.completed"
    assert first_event["step_id"] == "s1"


@pytest.mark.asyncio
async def test_stream_returns_sse_response_headers():
    """GET /workflows/executions/{id}/stream includes the canonical SSE headers."""
    from app.workflows.event_bus import publish_workflow_event  # noqa: PLC0415

    app = _build_app()
    transport = ASGITransport(app=app)

    with patch(
        "app.routers.workflows.get_service_client",
        return_value=_make_supabase_client("user-1"),
    ):
        async with AsyncClient(transport=transport, base_url="http://t") as client:

            async def emit_terminal() -> None:
                await asyncio.sleep(0.05)
                await publish_workflow_event(
                    "workflow.execution.exec-1",
                    {"type": "workflow.execution.completed"},
                )

            emit_task = asyncio.create_task(emit_terminal())

            async with client.stream(
                "GET",
                "/workflows/executions/exec-1/stream",
            ) as response:
                assert response.status_code == 200
                # Canonical SSE headers must be present
                assert response.headers.get("cache-control") == "no-cache, no-transform"
                assert response.headers.get("x-accel-buffering") == "no"
                # Drain the stream
                async for _ in response.aiter_lines():
                    pass

            await emit_task


@pytest.mark.asyncio
async def test_stream_404_on_unknown_execution():
    """GET /stream returns 404 when the execution_id is not found."""
    app = _build_app()
    transport = ASGITransport(app=app)

    with patch(
        "app.routers.workflows.get_service_client",
        return_value=_make_supabase_client(None),  # no rows
    ):
        async with AsyncClient(transport=transport, base_url="http://t") as client:
            response = await client.get("/workflows/executions/nonexistent/stream")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_stream_403_on_wrong_owner():
    """GET /stream returns 403 when execution belongs to a different user."""
    app = _build_app()
    transport = ASGITransport(app=app)

    with patch(
        "app.routers.workflows.get_service_client",
        return_value=_make_supabase_client("other-user"),  # different owner
    ):
        async with AsyncClient(transport=transport, base_url="http://t") as client:
            response = await client.get(
                "/workflows/executions/exec-owned-by-other/stream"
            )
        assert response.status_code == 403

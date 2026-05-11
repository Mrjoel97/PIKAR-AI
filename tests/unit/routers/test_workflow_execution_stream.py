"""Verify GET /workflows/executions/{id}/stream returns SSE."""

from __future__ import annotations

import asyncio
import json
import sys
import types
from unittest.mock import AsyncMock, MagicMock

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
    return "user-test"


_stub(
    "app.routers.onboarding",
    get_current_user_id=_default_get_current_user_id,
    router=MagicMock(),
)

# Rate limiter — disable throttling for tests.
if "app.middleware.rate_limiter" not in sys.modules:
    _rl_mod = types.ModuleType("app.middleware.rate_limiter")
    _rl_limiter = MagicMock()
    _rl_limiter.limit = lambda *a, **kw: (lambda fn: fn)
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

# Remaining heavy router imports that are not needed for the stream endpoint.
_stub("app.agents.tools.registry", TOOL_REGISTRY={})
_stub("app.app_utils.auth", verify_service_auth=MagicMock())
_stub("app.autonomy.agent_kernel", get_agent_kernel=MagicMock())
_stub("app.personas.runtime", resolve_request_persona=MagicMock(), resolve_effective_persona=AsyncMock(return_value="solopreneur"))
_stub("app.services.feature_flags",
      is_user_allowed_for_workflow_canary=MagicMock(return_value=True),
      is_workflow_canary_enabled=MagicMock(return_value=False),
      is_workflow_kill_switch_enabled=MagicMock(return_value=False))
_stub("app.services.sse_connection_limits",
      SSERejectReason=MagicMock(),
      release_sse_connection=AsyncMock(),
      try_acquire_sse_connection=AsyncMock(return_value=MagicMock(acquired=True, active=1, limit=10, reason=None)))
_stub("app.services.governance_service", get_governance_service=MagicMock())
_stub("app.services.supabase", get_service_client=MagicMock())
_stub("app.services.supabase_async", execute_async=AsyncMock())
_stub("app.workflows.contract_defaults", list_contract_safe_tool_names=MagicMock(return_value=[]))
_stub("app.workflows.engine", get_workflow_engine=MagicMock())
_stub("app.workflows.user_workflow_service", get_user_workflow_service=MagicMock())
_stub("app.config.feature_gating",
      FEATURE_ACCESS={},
      get_required_tier=MagicMock(return_value="solopreneur"),
      is_feature_allowed=MagicMock(return_value=True))

# ---------------------------------------------------------------------------
# Build the test app
# ---------------------------------------------------------------------------


def _build_app(*, user_id: str = "user-test") -> FastAPI:
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

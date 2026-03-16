import sys
from types import SimpleNamespace
from typing import Any

import pytest

from app.services.user_agent_factory import USER_AGENT_PERSONALIZATION_STATE_KEY

_events_module = sys.modules.get("google.adk.events")
if _events_module is not None and not hasattr(_events_module, "EventActions"):
    _events_module.EventActions = Any

from app.workflows.dynamic import DynamicWorkflowGenerator


class _StubWorkflow:
    async def run_async(self, _ctx):
        if False:
            yield None


@pytest.mark.asyncio
async def test_dynamic_workflow_runtime_reads_personalization_state(monkeypatch):
    generator = DynamicWorkflowGenerator()
    monkeypatch.setattr(generator, "_analyze_intent", lambda request: ["strategic"])
    monkeypatch.setattr(generator, "_determine_pattern", lambda request, agents: "sequential")
    monkeypatch.setattr(generator, "_build_workflow", lambda agent_keys, pattern, request: _StubWorkflow())

    ctx = SimpleNamespace(
        session=SimpleNamespace(
            state={
                "user_request": "Help me shape a launch strategy",
                USER_AGENT_PERSONALIZATION_STATE_KEY: {"persona": "Startup Founder"},
            },
            events=[],
        )
    )

    events = []
    async for event in generator._run_async_impl(ctx):
        events.append(event)

    assert events == []
    assert ctx.session.state["dynamic_workflow"] == {
        "agents": ["strategic"],
        "pattern": "sequential",
        "request": "Help me shape a launch strategy",
        "from_storage": False,
    }

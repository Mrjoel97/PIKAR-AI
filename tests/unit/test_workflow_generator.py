import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.workflows.generator import WorkflowGenerator


class _StubQuery:
    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=[])


class _StubClient:
    def table(self, _name):
        return _StubQuery()


class _StubEngine:
    def __init__(self):
        self.client = _StubClient()
        self.create_template = AsyncMock(return_value={"id": "tpl-1", "lifecycle_status": "draft"})
        self.publish_template = AsyncMock(return_value={"id": "tpl-1", "lifecycle_status": "published"})


@pytest.mark.asyncio
async def test_generate_workflow_creates_publishable_template_from_safe_tools():
    generator = object.__new__(WorkflowGenerator)
    generator.model = SimpleNamespace(
        prompt=lambda _prompt: SimpleNamespace(
            text=json.dumps(
                {
                    "name": "Founder Launch Sprint",
                    "description": "Plan and validate a launch sprint",
                    "category": "marketing",
                    "phases": [
                        {
                            "name": "Research",
                            "steps": [
                                {
                                    "name": "Research Competitors",
                                    "tool": "mcp_web_search",
                                    "description": "Research direct competitors and positioning angles",
                                    "required_approval": False,
                                }
                            ],
                        }
                    ],
                }
            )
        )
    )
    generator.engine = _StubEngine()

    result = await WorkflowGenerator.generate_workflow(
        generator,
        user_id="user-1",
        goal="Launch a founder-led product campaign",
        context="Marketing workflow for a startup founder",
        category="marketing",
        persona="startup",
    )

    create_call = generator.engine.create_template.await_args.kwargs
    step = create_call["phases"][0]["steps"][0]

    assert create_call["category"] == "marketing"
    assert step["tool"] == "mcp_web_search"
    assert step["input_bindings"]["query"]["value"] == "Research direct competitors and positioning angles"
    assert step["expected_outputs"] == ["results"]
    assert step["allow_parallel"] is True
    generator.engine.publish_template.assert_awaited_once_with(template_id="tpl-1", user_id="user-1")
    assert result["published"] is True
    assert result["lifecycle_status"] == "published"

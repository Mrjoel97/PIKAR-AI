from unittest.mock import AsyncMock

import pytest

from app.workflows.engine import WorkflowEngine


class _FakeResponse:
    """Awaitable response so ``await (await ...execute())`` works."""

    def __init__(self, data):
        self.data = data

    def __await__(self):
        return self._identity().__await__()

    async def _identity(self):
        return self


class _SelectQuery:
    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def __await__(self):
        return self._identity().__await__()

    async def _identity(self):
        return self

    async def execute(self):
        return _FakeResponse([])


class _InsertQuery:
    def __init__(self, client, row):
        self.client = client
        self.row = row

    def __await__(self):
        return self._identity().__await__()

    async def _identity(self):
        return self

    async def execute(self):
        self.client.inserted_row = self.row
        return _FakeResponse([{"id": "tpl-1", **self.row}])


class _UpdateQuery:
    def __init__(self, client, patch):
        self.client = client
        self.patch = patch

    def eq(self, *_args, **_kwargs):
        return self

    def __await__(self):
        return self._identity().__await__()

    async def _identity(self):
        return self

    async def execute(self):
        self.client.updated_patch = self.patch
        return _FakeResponse([{"id": "tpl-1", **self.patch}])


class _Table:
    def __init__(self, client, name):
        self.client = client
        self.name = name

    def select(self, *_args, **_kwargs):
        return _SelectQuery()

    def insert(self, row):
        return _InsertQuery(self.client, row)

    def update(self, patch):
        return _UpdateQuery(self.client, patch)


class _StubClient:
    def __init__(self):
        self.inserted_row = None
        self.updated_patch = None

    def table(self, name):
        return _Table(self, name)


@pytest.mark.asyncio
async def test_create_template_enriches_loose_steps_before_persisting():
    engine = object.__new__(WorkflowEngine)
    engine._async_client = _StubClient()
    engine._audit_template_action = AsyncMock()

    result = await engine.create_template(
        user_id="user-1",
        name="Builder Draft",
        description="Workflow created from builder",
        category="custom",
        phases=[
            {
                "name": "Builder Flow",
                "steps": [
                    {
                        "name": "Executive Follow-Up",
                        "tool": "create_task",
                        "description": "Create the next concrete action for this workflow.",
                    }
                ],
            }
        ],
        default_persona="startup",
        is_generated=True,
    )

    step = engine._async_client.inserted_row["phases"][0]["steps"][0]
    assert result["id"] == "tpl-1"
    assert engine._async_client.inserted_row["personas_allowed"] == ["startup"]
    assert step["input_bindings"]["description"]["value"] == "Create the next concrete action for this workflow."
    assert step["expected_outputs"] == ["task.id"]
    assert step["verification_checks"][0] == "success"


@pytest.mark.asyncio
async def test_update_template_draft_rebuilds_contract_metadata_for_simplified_steps():
    engine = object.__new__(WorkflowEngine)
    engine._async_client = _StubClient()
    engine.get_template = AsyncMock(
        return_value={
            "id": "tpl-1",
            "name": "Existing Draft",
            "description": "Existing workflow draft",
            "category": "marketing",
            "created_by": "user-1",
            "lifecycle_status": "draft",
        }
    )
    engine._audit_template_action = AsyncMock()

    result = await engine.update_template_draft(
        template_id="tpl-1",
        user_id="user-1",
        updates={
            "phases": [
                {
                    "name": "Research",
                    "steps": [
                        {
                            "name": "Research Competitors",
                            "tool": "mcp_web_search",
                            "description": "Research direct competitors and messaging",
                        }
                    ],
                }
            ]
        },
    )

    step = engine._async_client.updated_patch["phases"][0]["steps"][0]
    assert result["id"] == "tpl-1"
    assert step["input_bindings"]["query"]["value"] == "Research direct competitors and messaging"
    assert step["expected_outputs"] == ["results"]
    assert step["allow_parallel"] is True

import importlib
from unittest.mock import AsyncMock

import pytest

from app.workflows.engine import WorkflowEngine


def _fake_tool():
    async def _tool(**_kwargs):
        return {'success': True}

    class _Schema:
        model_fields = {'description': object()}

    _tool.input_schema = _Schema
    return _tool


def _set_tool_registry(monkeypatch):
    registry_module = importlib.import_module('app.agents.tools.registry')
    monkeypatch.setattr(registry_module, 'TOOL_REGISTRY', {'create_task': _fake_tool()}, raising=False)


@pytest.mark.asyncio
async def test_publish_template_rejects_templates_without_strict_contract_metadata(monkeypatch):
    engine = object.__new__(WorkflowEngine)
    engine._async_client = object()  # not used; publish errors before DB write
    engine.get_template = AsyncMock(
        return_value={
            'id': 'tpl-1',
            'name': 'Loose Template',
            'created_by': 'u1',
            'lifecycle_status': 'draft',
            'phases': [{'name': 'Plan', 'steps': [{'name': 'Loose Step', 'tool': 'missing_tool'}]}],
        }
    )
    engine._audit_template_action = AsyncMock()

    _set_tool_registry(monkeypatch)

    result = await engine.publish_template(template_id='tpl-1', user_id='u1')

    assert result['error'] == 'Workflow template validation failed'
    assert any('unresolved tool' in detail for detail in result['details'])


@pytest.mark.asyncio
async def test_publish_template_requires_explicit_persona_scope(monkeypatch):
    engine = object.__new__(WorkflowEngine)
    engine._async_client = object()  # not used; publish errors before DB write
    engine.get_template = AsyncMock(
        return_value={
            'id': 'tpl-2',
            'name': 'Founder Workflow',
            'created_by': 'u1',
            'lifecycle_status': 'draft',
            'phases': [
                {
                    'name': 'Plan',
                    'steps': [
                        {
                            'name': 'Strict Step',
                            'tool': 'create_task',
                            'description': 'Create task',
                            'input_bindings': {'description': {'value': 'Founder task'}},
                            'required_approval': False,
                            'required_integrations': [],
                            'verification_checks': ['success'],
                            'expected_outputs': ['task.id'],
                            'allow_parallel': False,
                        }
                    ],
                }
            ],
            'personas_allowed': [],
        }
    )
    engine._audit_template_action = AsyncMock()

    _set_tool_registry(monkeypatch)

    result = await engine.publish_template(template_id='tpl-2', user_id='u1')

    assert result['error'] == 'Workflow template must define personas_allowed before publish'
    assert 'personas_allowed' in result['details'][0]
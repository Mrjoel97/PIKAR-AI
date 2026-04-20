import importlib
from unittest.mock import AsyncMock

import pytest

from app.workflows.engine import WorkflowEngine


STRICT_PHASES = [
    {
        'name': 'Phase 1',
        'steps': [
            {
                'name': 'Step 1',
                'tool': 'create_task',
                'description': 'Create first task',
                'required_approval': False,
                'input_bindings': {'description': {'value': 'Initial workflow task'}},
                'risk_level': 'medium',
                'required_integrations': [],
                'verification_checks': ['success'],
                'expected_outputs': ['task.id'],
                'allow_parallel': False,
            }
        ],
    }
]


def _set_callback_env(monkeypatch) -> None:
    monkeypatch.setenv('BACKEND_API_URL', 'http://localhost:8000')
    monkeypatch.setenv('WORKFLOW_SERVICE_SECRET', 'x' * 40)


def _fake_tool():
    async def _tool(**_kwargs):
        return {'success': True}

    class _Schema:
        model_fields = {'description': object()}

    _tool.input_schema = _Schema
    return _tool


def _set_tool_registry(monkeypatch) -> None:
    registry_module = importlib.import_module('app.agents.tools.registry')
    monkeypatch.setattr(registry_module, 'TOOL_REGISTRY', {'create_task': _fake_tool()}, raising=False)
    monkeypatch.setattr(registry_module, 'placeholder_tool', _fake_tool(), raising=False)


class _FakeResponse:
    """Awaitable response so double-await patterns work."""

    def __init__(self, data):
        self.data = data

    def __await__(self):
        return self._identity().__await__()

    async def _identity(self):
        return self


class _FakeCountResponse:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count

    def __await__(self):
        return self._identity().__await__()

    async def _identity(self):
        return self


class _FakeTable:
    """Awaitable query builder mock."""

    def __init__(self, name: str, db: '_FakeDb'):
        self._name = name
        self._db = db
        self._filters = {}
        self._insert_payload = None
        self._is_count_query = False

    def __await__(self):
        return self._identity().__await__()

    async def _identity(self):
        return self

    def select(self, *_args, **_kwargs):
        if _kwargs.get('count'):
            self._is_count_query = True
        return self

    def eq(self, key, value):
        self._filters[key] = value
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def insert(self, payload):
        self._insert_payload = payload
        return self

    def update(self, _payload):
        return self

    async def execute(self):
        if self._name == 'workflow_templates':
            return _FakeResponse([self._db.template])
        if self._name == 'workflow_readiness':
            if self._db.readiness_error:
                raise RuntimeError(self._db.readiness_error)
            row = self._db.readiness_row
            if not row:
                return _FakeResponse([])
            template_id = self._filters.get('template_id')
            if template_id and row.get('template_id') != template_id:
                return _FakeResponse([])
            return _FakeResponse([row])
        if self._name == 'workflow_executions':
            if self._is_count_query:
                return _FakeCountResponse([], count=0)
            self._db.execution_inserts.append(self._insert_payload)
            return _FakeResponse([{'id': f'exec-{len(self._db.execution_inserts)}'}])
        # Audit tables and others
        return _FakeResponse([])


class _FakeDb:
    def __init__(self, readiness_row=None, readiness_error: str | None = None, lifecycle_status: str = 'published', phases=None):
        self.template = {
            'id': 'tpl-1',
            'name': 'Template A',
            'version': 1,
            'lifecycle_status': lifecycle_status,
            'phases': phases or STRICT_PHASES,
        }
        self.readiness_row = readiness_row
        self.readiness_error = readiness_error
        self.execution_inserts = []

    def table(self, name: str):
        return _FakeTable(name, self)


@pytest.mark.asyncio
async def test_start_workflow_allows_when_readiness_gate_disabled(monkeypatch):
    fake_db = _FakeDb(
        readiness_row={
            'template_id': 'tpl-1',
            'status': 'blocked',
            'reason_codes': ['integration_missing'],
        }
    )
    engine = object.__new__(WorkflowEngine)
    engine._async_client = fake_db

    execute_workflow_mock = AsyncMock(return_value={'success': True})
    monkeypatch.setattr('app.workflows.engine.edge_function_client.execute_workflow', execute_workflow_mock)
    monkeypatch.setenv('WORKFLOW_ENFORCE_READINESS_GATE', 'false')
    _set_callback_env(monkeypatch)
    _set_tool_registry(monkeypatch)

    result = await engine.start_workflow(user_id='u1', template_name='Template A')

    assert 'error' not in result
    assert result['status'] == 'pending'
    assert execute_workflow_mock.call_count == 1


@pytest.mark.asyncio
async def test_start_workflow_blocks_draft_for_user_visible_sources(monkeypatch):
    fake_db = _FakeDb(
        readiness_row={
            'template_id': 'tpl-1',
            'status': 'ready',
            'reason_codes': [],
        },
        lifecycle_status='draft',
    )
    engine = object.__new__(WorkflowEngine)
    engine._async_client = fake_db
    monkeypatch.setenv('WORKFLOW_ENFORCE_READINESS_GATE', 'true')

    result = await engine.start_workflow(user_id='u1', template_name='Template A', run_source='user_ui')

    assert result['error_code'] == 'template_not_published'
    assert result['lifecycle_status'] == 'draft'


@pytest.mark.asyncio
async def test_start_workflow_allows_draft_for_internal_run_sources(monkeypatch):
    fake_db = _FakeDb(
        readiness_row={
            'template_id': 'tpl-1',
            'status': 'ready',
            'reason_codes': [],
        },
        lifecycle_status='draft',
    )
    engine = object.__new__(WorkflowEngine)
    engine._async_client = fake_db
    monkeypatch.setenv('WORKFLOW_ENFORCE_READINESS_GATE', 'true')

    execute_workflow_mock = AsyncMock(return_value={'success': True})
    monkeypatch.setattr('app.workflows.engine.edge_function_client.execute_workflow', execute_workflow_mock)

    result = await engine.start_workflow(user_id='u1', template_name='Template A', run_source='internal_service')

    assert 'error' not in result
    assert result['status'] == 'pending'
    assert execute_workflow_mock.call_count == 1


@pytest.mark.asyncio
async def test_start_workflow_blocks_invalid_contract(monkeypatch):
    fake_db = _FakeDb(
        readiness_row={
            'template_id': 'tpl-1',
            'status': 'ready',
            'reason_codes': [],
        },
        phases=[{'name': 'Phase 1', 'steps': [{'name': 'Loose Step', 'tool': 'create_task'}]}],
    )
    engine = object.__new__(WorkflowEngine)
    engine._async_client = fake_db
    monkeypatch.setenv('WORKFLOW_ENFORCE_READINESS_GATE', 'false')
    _set_callback_env(monkeypatch)
    _set_tool_registry(monkeypatch)
    execute_workflow_mock = AsyncMock(return_value={'success': True})
    monkeypatch.setattr('app.workflows.engine.edge_function_client.execute_workflow', execute_workflow_mock)

    result = await engine.start_workflow(user_id='u1', template_name='Template A')

    assert 'error' not in result
    assert result['status'] == 'pending'
    assert execute_workflow_mock.call_count == 1


@pytest.mark.asyncio
async def test_start_workflow_blocks_cross_persona_user_visible_runs(monkeypatch):
    fake_db = _FakeDb(
        readiness_row={
            'template_id': 'tpl-1',
            'status': 'ready',
            'reason_codes': [],
        }
    )
    fake_db.template['personas_allowed'] = ['enterprise']
    engine = object.__new__(WorkflowEngine)
    engine._async_client = fake_db

    result = await engine.start_workflow(
        user_id='u1',
        template_name='Template A',
        persona='startup',
        run_source='user_ui',
    )

    assert result['error_code'] == 'workflow_persona_not_allowed'
    assert result['reason_code'] == 'persona_not_allowed'
    assert result['persona'] == 'startup'
    assert result['personas_allowed'] == ['enterprise']
    assert fake_db.execution_inserts == []

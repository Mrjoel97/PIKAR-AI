from types import SimpleNamespace

import pytest

from app.workflows.engine import WorkflowEngine


class FakeWorkflowExecutionQuery:
    def __init__(self, data):
        self.data = data
        self.eq_calls = []
        self.in_calls = []
        self.order_call = None
        self.range_call = None

    def select(self, _fields):
        return self

    def eq(self, key, value):
        self.eq_calls.append((key, value))
        return self

    def in_(self, key, values):
        self.in_calls.append((key, list(values)))
        return self

    def order(self, key, desc=False):
        self.order_call = (key, desc)
        return self

    def range(self, start, end):
        self.range_call = (start, end)
        return self

    def execute(self):
        return SimpleNamespace(data=self.data)


class FakeSupabaseClient:
    def __init__(self, query):
        self.query = query

    def table(self, table_name):
        assert table_name == 'workflow_executions'
        return self.query


@pytest.mark.asyncio
async def test_list_executions_uses_in_filter_for_multiple_statuses(monkeypatch):
    query = FakeWorkflowExecutionQuery([
        {
            'id': 'exec-1',
            'status': 'running',
            'workflow_templates': {'name': 'Quarterly Review'},
        }
    ])
    monkeypatch.setattr(WorkflowEngine, '_get_supabase', lambda self: FakeSupabaseClient(query))

    engine = WorkflowEngine()
    result = await engine.list_executions(
        user_id='user-1',
        statuses=['running', 'pending'],
        limit=60,
    )

    assert ('user_id', 'user-1') in query.eq_calls
    assert query.in_calls == [('status', ['running', 'pending'])]
    assert ('status', 'running') not in query.eq_calls
    assert query.order_call == ('created_at', True)
    assert query.range_call == (0, 59)
    assert result[0]['template_name'] == 'Quarterly Review'


@pytest.mark.asyncio
async def test_list_executions_preserves_single_status_eq_filter(monkeypatch):
    query = FakeWorkflowExecutionQuery([])
    monkeypatch.setattr(WorkflowEngine, '_get_supabase', lambda self: FakeSupabaseClient(query))

    engine = WorkflowEngine()
    await engine.list_executions(user_id='user-1', status='completed', limit=25, offset=10)

    assert ('status', 'completed') in query.eq_calls
    assert query.in_calls == []
    assert query.range_call == (10, 34)

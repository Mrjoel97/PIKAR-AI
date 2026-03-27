import pytest

from app.workflows.engine import WorkflowEngine


class _FakeResponse:
    """Awaitable response for ``await ...execute()``."""

    def __init__(self, data):
        self.data = data

    def __await__(self):
        return self._identity().__await__()

    async def _identity(self):
        return self


class FakeWorkflowExecutionQuery:
    def __init__(self, data):
        self.data = data
        self.eq_calls = []
        self.in_calls = []
        self.order_call = None
        self.range_call = None

    def select(self, *_args, **_kwargs):
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

    async def execute(self):
        return _FakeResponse(self.data)


class FakeSupabaseClient:
    def __init__(self, query):
        self.query = query

    def table(self, table_name):
        assert table_name == 'workflow_executions'
        return self.query


@pytest.mark.asyncio
async def test_list_executions_uses_in_filter_for_multiple_statuses():
    query = FakeWorkflowExecutionQuery([
        {
            'id': 'exec-1',
            'status': 'running',
            'workflow_templates': {'name': 'Quarterly Review'},
        }
    ])

    engine = object.__new__(WorkflowEngine)
    engine._async_client = FakeSupabaseClient(query)
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
async def test_list_executions_preserves_single_status_eq_filter():
    query = FakeWorkflowExecutionQuery([])

    engine = object.__new__(WorkflowEngine)
    engine._async_client = FakeSupabaseClient(query)
    await engine.list_executions(user_id='user-1', status='completed', limit=25, offset=10)

    assert ('status', 'completed') in query.eq_calls
    assert query.in_calls == []
    assert query.range_call == (10, 34)

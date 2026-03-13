from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.workflows.user_workflow_service import UserWorkflowService


@pytest.fixture
def mock_supabase():
    with patch('app.workflows.user_workflow_service.get_service_client') as mock:
        client = MagicMock()
        query = MagicMock()
        client.table.return_value = query
        for method_name in ['select', 'eq', 'in_', 'order', 'limit', 'single', 'upsert', 'update', 'delete']:
            getattr(query, method_name).return_value = query
        query.execute.return_value = SimpleNamespace(data=[])
        mock.return_value = client
        yield client, query


@pytest.fixture
def service(mock_supabase, monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://test.supabase.co')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', 'test-key')
    return UserWorkflowService()


@pytest.mark.asyncio
async def test_save_workflow(service, mock_supabase):
    client, query = mock_supabase
    user_id = 'test-user'
    workflow_name = 'test-workflow'

    query.execute.return_value = SimpleNamespace(data=[{'workflow_name': workflow_name}])

    result = await service.save_workflow(
        user_id=user_id,
        workflow_name=workflow_name,
        workflow_pattern='sequential',
        agent_ids=['strategic', 'data'],
        request_pattern='test request',
        workflow_config={'agents': ['strategic', 'data']},
    )

    assert result['workflow_name'] == workflow_name
    client.table.assert_called_with('user_workflows')


@pytest.mark.asyncio
async def test_get_workflow(service, mock_supabase):
    _client, query = mock_supabase
    user_id = 'test-user'
    workflow_name = 'test-workflow'

    query.execute.return_value = SimpleNamespace(data={'workflow_name': workflow_name})

    result = await service.get_workflow(user_id, workflow_name)
    assert result['workflow_name'] == workflow_name


@pytest.mark.asyncio
async def test_list_workflows(service, mock_supabase):
    _client, query = mock_supabase
    user_id = 'test-user'
    query.execute.return_value = SimpleNamespace(data=[{'workflow_name': 'w1'}])

    result = await service.list_workflows(user_id)
    assert len(result) == 1
    assert result[0]['workflow_name'] == 'w1'


@pytest.mark.asyncio
async def test_find_matching_workflow(service, mock_supabase):
    _client, query = mock_supabase
    user_id = 'test-user'
    query.execute.return_value = SimpleNamespace(data=[
        {
            'workflow_name': 'w1',
            'request_pattern': 'financial analysis report',
            'usage_count': 5,
        },
        {
            'workflow_name': 'w2',
            'request_pattern': 'marketing social media',
            'usage_count': 1,
        },
    ])

    result = await service.find_matching_workflow(user_id, 'analyze finances and create report', threshold=0.1)
    assert result is not None
    assert result['workflow_name'] == 'w1'


@pytest.mark.asyncio
async def test_update_workflow_usage(service, mock_supabase):
    _client, query = mock_supabase
    user_id = 'test-user'
    workflow_name = 'w1'

    query.execute.side_effect = [
        SimpleNamespace(data={'usage_count': 5}),
        SimpleNamespace(data=[{'usage_count': 6}]),
    ]

    result = await service.update_workflow_usage(user_id, workflow_name)
    assert result['usage_count'] == 6


def test_normalize_request(service):
    request = 'I want a Financial Analysis for my project!'
    normalized = service.normalize_request(request)
    assert 'financial' in normalized
    assert 'analysis' in normalized
    assert 'project' in normalized
    assert 'want' not in normalized


def test_generate_workflow_name(service):
    agents = ['data', 'strategic']
    name = service.generate_workflow_name(agents, 'sequential')
    assert name.startswith('sequential_data_strategic_')


def test_apply_persona_scope_filter_includes_shared_scope(service):
    query = MagicMock()
    query.in_.return_value = query

    result = service._apply_persona_scope_filter(query, 'startup')

    assert result is query
    query.in_.assert_called_once_with('persona_scope', ['startup', 'all'])


def test_apply_persona_scope_filter_targets_all_exactly(service):
    query = MagicMock()
    query.eq.return_value = query

    result = service._apply_persona_scope_filter(query, 'all')

    assert result is query
    query.eq.assert_called_once_with('persona_scope', 'all')
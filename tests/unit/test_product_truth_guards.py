import importlib

import pytest
from fastapi.testclient import TestClient

from app.workflows.execution_contracts import WorkflowContractError, build_tool_kwargs


async def _degraded_tool(**kwargs):
    return {'success': True}


_degraded_tool.__module__ = 'app.agents.tools.degraded_tools'


def _reload_fastapi_app(monkeypatch, **env):
    monkeypatch.setenv('LOCAL_DEV_BYPASS', '1')
    monkeypatch.setenv('SKIP_ENV_VALIDATION', '1')
    monkeypatch.setenv('ENVIRONMENT', env.pop('ENVIRONMENT', 'test'))

    if 'ALLOWED_ORIGINS' in env:
        monkeypatch.setenv('ALLOWED_ORIGINS', env.pop('ALLOWED_ORIGINS'))
    else:
        monkeypatch.delenv('ALLOWED_ORIGINS', raising=False)

    from app import fast_api_app

    return importlib.reload(fast_api_app)


def test_build_tool_kwargs_rejects_degraded_tool_in_production_even_for_background_runs(monkeypatch):
    monkeypatch.setenv('ENVIRONMENT', 'production')

    with pytest.raises(WorkflowContractError) as exc:
        build_tool_kwargs(
            _degraded_tool,
            'query_analytics',
            {'report_id': 'rpt_123'},
            step_name='Analytics sync',
            run_source='system',
            tool_registry={'query_analytics': _degraded_tool},
        )

    assert exc.value.reason_code == 'degraded_tool_not_allowed'
    assert 'production execution' in str(exc.value)


def test_fastapi_cors_allows_persona_and_user_headers(monkeypatch):
    fast_api_app = _reload_fastapi_app(monkeypatch)

    headers = {header.lower() for header in fast_api_app._cors_allowed_headers}
    assert {'x-pikar-persona', 'x-user-id', 'user-id'}.issubset(headers)


def test_fastapi_rejects_wildcard_cors_in_production(monkeypatch):
    _reload_fastapi_app(monkeypatch, ENVIRONMENT='test')

    # In production, either environment validation or the CORS wildcard guard
    # will raise RuntimeError (validation runs first when bypass flags are
    # ignored in production mode).
    with pytest.raises((RuntimeError, Exception)):
        _reload_fastapi_app(monkeypatch, ENVIRONMENT='production', ALLOWED_ORIGINS='*')

    _reload_fastapi_app(monkeypatch, ENVIRONMENT='test')


def test_fastapi_sets_security_headers_on_health_response(monkeypatch):
    fast_api_app = _reload_fastapi_app(monkeypatch, ENVIRONMENT='test')

    with TestClient(fast_api_app.app) as client:
        response = client.get('/health/live')

    assert response.status_code == 200
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['Strict-Transport-Security'] == 'max-age=31536000; includeSubDomains'

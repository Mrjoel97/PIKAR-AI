import importlib
import logging

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.app_utils import auth as auth_module
from app.middleware import rate_limiter


def _build_request(headers=None):
    headers = headers or {}
    scope = {
        'type': 'http',
        'asgi': {'version': '3.0'},
        'http_version': '1.1',
        'method': 'GET',
        'scheme': 'http',
        'path': '/',
        'raw_path': b'/',
        'query_string': b'',
        'headers': [(key.lower().encode('latin-1'), value.encode('latin-1')) for key, value in headers.items()],
        'client': ('127.0.0.1', 12345),
        'server': ('testserver', 80),
    }
    return Request(scope)


def _reload_fastapi_app(monkeypatch, **env):
    monkeypatch.setenv('LOCAL_DEV_BYPASS', '1')
    monkeypatch.setenv('SKIP_ENV_VALIDATION', '1')
    monkeypatch.setenv('ENVIRONMENT', env.pop('ENVIRONMENT', 'test'))

    if 'MAX_UPLOAD_SIZE_BYTES' in env:
        monkeypatch.setenv('MAX_UPLOAD_SIZE_BYTES', env.pop('MAX_UPLOAD_SIZE_BYTES'))
    else:
        monkeypatch.delenv('MAX_UPLOAD_SIZE_BYTES', raising=False)

    from app import fast_api_app

    return importlib.reload(fast_api_app)


def test_rate_limiter_skips_token_decode_without_secret(monkeypatch):
    rate_limiter._persona_cache.clear()
    monkeypatch.delenv('SUPABASE_JWT_SECRET', raising=False)

    import jwt as jwt_module

    def fail_decode(*args, **kwargs):
        raise AssertionError('jwt.decode should not run without SUPABASE_JWT_SECRET')

    monkeypatch.setattr(jwt_module, 'decode', fail_decode)

    request = _build_request({'Authorization': 'Bearer token-should-never-be-decoded'})
    assert rate_limiter.get_user_persona_limit(request) == rate_limiter.DEFAULT_LIMIT


def test_rate_limiter_uses_verified_decode_when_secret_present(monkeypatch):
    rate_limiter._persona_cache.clear()
    rate_limiter._set_cached_persona('user-123', 'enterprise')
    monkeypatch.setenv('SUPABASE_JWT_SECRET', 'test-secret')

    import jwt as jwt_module

    captured = {}

    def fake_decode(token, secret, algorithms, options):
        captured['token'] = token
        captured['secret'] = secret
        captured['algorithms'] = algorithms
        captured['options'] = options
        return {'sub': 'user-123'}

    monkeypatch.setattr(jwt_module, 'decode', fake_decode)

    request = _build_request({'Authorization': 'Bearer verified-token'})
    assert rate_limiter.get_user_persona_limit(request) == rate_limiter.PERSONA_LIMITS['enterprise']
    assert captured['secret'] == 'test-secret'
    assert captured['algorithms'] == ['HS256']
    assert captured['options'] == {'verify_aud': False}


def test_rate_limiter_trims_jwt_secret_before_decode(monkeypatch):
    rate_limiter._persona_cache.clear()
    rate_limiter._set_cached_persona('user-123', 'enterprise')
    monkeypatch.setenv('SUPABASE_JWT_SECRET', 'test-secret\r\n')

    import jwt as jwt_module

    captured = {}

    def fake_decode(token, secret, algorithms, options):
        captured['secret'] = secret
        return {'sub': 'user-123'}

    monkeypatch.setattr(jwt_module, 'decode', fake_decode)

    request = _build_request({'Authorization': 'Bearer verified-token'})
    assert rate_limiter.get_user_persona_limit(request) == rate_limiter.PERSONA_LIMITS['enterprise']
    assert captured['secret'] == 'test-secret'


def test_verify_service_auth_trims_expected_secret(monkeypatch):
    monkeypatch.setenv('WORKFLOW_SERVICE_SECRET', 'workflow-secret\r\n')

    assert auth_module.verify_service_auth('workflow-secret') is True


def test_get_user_id_from_bearer_token_failure_logs_are_sanitized(monkeypatch, caplog):
    class StubAuth:
        def get_user(self, _token):
            raise RuntimeError('boom')

    class StubClient:
        auth = StubAuth()

    monkeypatch.delenv('REQUIRE_STRICT_AUTH', raising=False)
    monkeypatch.setattr(auth_module, 'get_supabase_client', lambda: StubClient())

    sensitive_token = 'token-should-never-appear-1234567890'
    with caplog.at_level(logging.INFO):
        assert auth_module.get_user_id_from_bearer_token(sensitive_token) is None

    assert sensitive_token not in caplog.text
    assert '1234567890' not in caplog.text


def test_upload_rejects_files_over_limit(monkeypatch):
    fast_api_app = _reload_fastapi_app(monkeypatch, ENVIRONMENT='test', MAX_UPLOAD_SIZE_BYTES='4')

    from app.routers.onboarding import get_current_user_id

    fast_api_app.app.dependency_overrides[get_current_user_id] = lambda: "test-user-id"

    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post('/upload', files={'file': ('big.txt', b'hello', 'text/plain')})

        assert response.status_code == 413
        body = response.json()
        message = body.get('message') or body.get('detail') or ''
        assert 'Maximum upload size' in message
    finally:
        fast_api_app.app.dependency_overrides.pop(get_current_user_id, None)

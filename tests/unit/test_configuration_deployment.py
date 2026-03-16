from __future__ import annotations

import importlib
from pathlib import Path

from fastapi.testclient import TestClient

from app.services import sse_connection_limits

REPO_ROOT = Path(__file__).resolve().parents[2]

def _reload_fastapi_app(monkeypatch, **env):
    monkeypatch.setenv("LOCAL_DEV_BYPASS", "1")
    monkeypatch.setenv("SKIP_ENV_VALIDATION", "1")
    monkeypatch.setenv("ENVIRONMENT", env.pop("ENVIRONMENT", "test"))

    allow_anonymous = env.pop("ALLOW_ANONYMOUS_CHAT", None)
    sse_limit = env.pop("SSE_MAX_CONNECTIONS_PER_USER", None)

    if allow_anonymous is not None:
        monkeypatch.setenv("ALLOW_ANONYMOUS_CHAT", allow_anonymous)
    else:
        monkeypatch.delenv("ALLOW_ANONYMOUS_CHAT", raising=False)

    if sse_limit is not None:
        monkeypatch.setenv("SSE_MAX_CONNECTIONS_PER_USER", sse_limit)
    else:
        monkeypatch.delenv("SSE_MAX_CONNECTIONS_PER_USER", raising=False)

    from app import fast_api_app

    return importlib.reload(fast_api_app)

def test_legacy_config_surface_exports_validation_only():
    import app.config as config_module
    import app.config.settings as settings_module

    assert not hasattr(config_module, "AppSettings")
    assert not hasattr(settings_module, "AppSettings")
    assert hasattr(config_module, "validate_startup")
    assert hasattr(settings_module, "validate_environment")

def test_sse_connection_limit_counts_all_user_streams(monkeypatch):
    monkeypatch.setenv("SSE_MAX_CONNECTIONS_PER_USER", "2")
    sse_connection_limits.reset_sse_connection_limits()

    acquired, active, limit = sse_connection_limits.try_acquire_sse_connection("user-123", stream_name="chat")
    assert acquired is True
    assert active == 1
    assert limit == 2

    acquired, active, limit = sse_connection_limits.try_acquire_sse_connection("user-123", stream_name="workflow")
    assert acquired is True
    assert active == 2
    assert limit == 2

    acquired, active, limit = sse_connection_limits.try_acquire_sse_connection("user-123", stream_name="chat")
    assert acquired is False
    assert active == 2
    assert limit == 2
    assert sse_connection_limits.get_active_sse_connection_count("user-123") == 2

    sse_connection_limits.release_sse_connection("user-123", stream_name="workflow")
    sse_connection_limits.release_sse_connection("user-123", stream_name="chat")
    assert sse_connection_limits.get_active_sse_connection_count("user-123") == 0

def test_run_sse_rejects_excess_active_connections(monkeypatch):
    fast_api_app = _reload_fastapi_app(
        monkeypatch,
        ENVIRONMENT="test",
        ALLOW_ANONYMOUS_CHAT="1",
        SSE_MAX_CONNECTIONS_PER_USER="1",
    )
    fast_api_app.runner = object()
    sse_connection_limits.reset_sse_connection_limits()
    acquired, _active, _limit = sse_connection_limits.try_acquire_sse_connection(
        "anonymous",
        stream_name="workflow",
    )
    assert acquired is True

    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post(
                "/a2a/app/run_sse",
                json={
                    "session_id": "session-limit-test",
                    "new_message": {"parts": [{"text": "hello"}]},
                },
            )
        assert response.status_code == 429
        payload = response.json()
        message = payload.get("message") or payload.get("detail") or ""
        assert "Too many active SSE connections" in message
    finally:
        sse_connection_limits.release_sse_connection("anonymous", stream_name="workflow")
        sse_connection_limits.reset_sse_connection_limits()

def test_dockerfile_declares_backend_healthcheck():
    dockerfile_text = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "HEALTHCHECK" in dockerfile_text
    assert "/health/live" in dockerfile_text
    assert "PORT" in dockerfile_text

def test_backend_env_example_documents_streaming_and_upload_guardrails():
    env_example_text = (REPO_ROOT / "app" / ".env.example").read_text(encoding="utf-8")
    assert "SSE_MAX_CONNECTIONS_PER_USER=3" in env_example_text
    assert "MAX_UPLOAD_SIZE_BYTES=10485760" in env_example_text

def test_production_terraform_omits_bypass_flags():
    production_service_text = (REPO_ROOT / "deployment" / "terraform" / "service.tf").read_text(encoding="utf-8")
    production_vars_text = (REPO_ROOT / "deployment" / "terraform" / "vars" / "env.tfvars").read_text(encoding="utf-8")

    for forbidden_flag in ("LOCAL_DEV_BYPASS", "SKIP_ENV_VALIDATION"):
        assert forbidden_flag not in production_service_text
        assert forbidden_flag not in production_vars_text

"""Focused tests for PR-3 endpoint hardening and logging compatibility."""

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

# Ensure repo root is importable when running from app/tests
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import app.app_utils.auth as auth_module
from app import fast_api_app


def _chat_payload() -> dict:
    return {
        "session_id": "session-pr3-test",
        "new_message": {"parts": [{"text": "hello"}]},
    }


def test_run_sse_requires_auth_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ALLOW_ANONYMOUS_CHAT", raising=False)
    with TestClient(fast_api_app.app) as client:
        response = client.post("/a2a/app/run_sse", json=_chat_payload())
    assert response.status_code == 401
    assert "Authentication required for chat" in response.text


def test_run_sse_rejects_invalid_bearer_when_anonymous_disabled(monkeypatch) -> None:
    monkeypatch.delenv("ALLOW_ANONYMOUS_CHAT", raising=False)
    monkeypatch.setattr(auth_module, "get_user_id_from_bearer_token", lambda _t: None)
    with TestClient(fast_api_app.app) as client:
        response = client.post(
            "/a2a/app/run_sse",
            json=_chat_payload(),
            headers={"Authorization": "Bearer invalid-token"},
        )
    assert response.status_code == 401
    assert "Invalid authentication credentials" in response.text


def test_run_sse_allows_anonymous_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("ALLOW_ANONYMOUS_CHAT", "1")
    monkeypatch.setattr(
        fast_api_app.genai_types,
        "Content",
        lambda **kwargs: kwargs,
        raising=False,
    )
    monkeypatch.setattr(
        fast_api_app.genai_types,
        "Part",
        lambda **kwargs: kwargs,
        raising=False,
    )
    with TestClient(fast_api_app.app) as client:
        response = client.post("/a2a/app/run_sse", json=_chat_payload())
    # Auth should pass in anonymous mode; downstream runner behavior may vary in mixed mock contexts.
    assert response.status_code == 200


def test_feedback_endpoint_uses_logger_fallback_without_log_struct(monkeypatch) -> None:
    class _StubLogger:
        def __init__(self):
            self.messages = []

        def info(self, msg, *args):
            self.messages.append(msg % args if args else msg)

    stub_logger = _StubLogger()
    monkeypatch.setattr(fast_api_app, "logger", stub_logger)

    payload = {
        "score": 1,
        "text": "works",
        "log_type": "feedback",
        "service_name": "pikar-ai",
        "user_id": "user-1",
        "session_id": "session-1",
    }
    with TestClient(fast_api_app.app) as client:
        response = client.post("/feedback", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    assert any("feedback=" in msg for msg in stub_logger.messages)

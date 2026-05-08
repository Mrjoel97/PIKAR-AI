"""Tests for /health/summarizer endpoint and ENABLE_CONVERSATION_SUMMARIZER flag.

These tests cover the production-rollout contract for the conversation
summarizer feature flag — that the health endpoint accurately mirrors the
parsed env var and SESSION_MAX_EVENTS, returns the documented envelope,
and respects custom overrides.

The summarizer module reads env vars at import time, so we reload it under
``monkeypatch`` to validate each scenario.
"""

from __future__ import annotations

import importlib
import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient


def _reload_summarizer_with_env(monkeypatch: pytest.MonkeyPatch, **env: str) -> Any:
    """Reload supabase_session_service so module-level env reads pick up overrides."""
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    # Force a fresh import so module-level int(os.environ.get(...)) re-runs
    sys.modules.pop("app.persistence.supabase_session_service", None)
    return importlib.import_module("app.persistence.supabase_session_service")


def _client() -> TestClient:
    """Return a TestClient against the FastAPI app, lazily imported."""
    from app.fast_api_app import app

    return TestClient(app)


def test_summarizer_health_enabled_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """When ENABLE_CONVERSATION_SUMMARIZER=true, endpoint reports enabled=True."""
    _reload_summarizer_with_env(
        monkeypatch,
        ENABLE_CONVERSATION_SUMMARIZER="true",
        SESSION_MAX_EVENTS="200",
    )

    response = _client().get("/health/summarizer")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["session_max_events"] == 200
    assert body["details"]["enabled"] is True
    assert body["details"]["session_max_events"] == 200


def test_summarizer_health_enabled_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """When ENABLE_CONVERSATION_SUMMARIZER=false, endpoint reports enabled=False."""
    _reload_summarizer_with_env(
        monkeypatch,
        ENABLE_CONVERSATION_SUMMARIZER="false",
        SESSION_MAX_EVENTS="200",
    )

    response = _client().get("/health/summarizer")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["session_max_events"] == 200


def test_summarizer_health_custom_max_events(monkeypatch: pytest.MonkeyPatch) -> None:
    """Custom SESSION_MAX_EVENTS values are reflected at top level and in details."""
    _reload_summarizer_with_env(
        monkeypatch,
        ENABLE_CONVERSATION_SUMMARIZER="true",
        SESSION_MAX_EVENTS="500",
    )

    response = _client().get("/health/summarizer")
    assert response.status_code == 200
    body = response.json()
    assert body["session_max_events"] == 500
    assert body["details"]["session_max_events"] == 500
    assert body["enabled"] is True


def test_summarizer_health_envelope_and_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Response conforms to the canonical health envelope with correct field types."""
    _reload_summarizer_with_env(
        monkeypatch,
        ENABLE_CONVERSATION_SUMMARIZER="true",
        SESSION_MAX_EVENTS="200",
    )

    response = _client().get("/health/summarizer")
    assert response.status_code == 200
    body = response.json()

    # Canonical envelope keys must be present.
    for required_key in (
        "status",
        "version",
        "service",
        "latency_ms",
        "details",
        "checked_at",
        "enabled",
        "session_max_events",
    ):
        assert required_key in body, f"missing key: {required_key}"

    assert body["service"] == "summarizer"
    assert body["status"] in {"ok", "degraded", "down"}
    assert body["version"] == "1"
    assert isinstance(body["enabled"], bool)
    assert isinstance(body["session_max_events"], int)
    assert isinstance(body["details"], dict)

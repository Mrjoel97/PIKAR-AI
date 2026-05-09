# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for /health/summarizer endpoint.

Validates that the endpoint correctly surfaces the runtime state of
``ENABLE_CONVERSATION_SUMMARIZER`` and ``SESSION_MAX_EVENTS`` so monitoring
can verify production rollout without ssh access.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient


def _client() -> TestClient:
    """Build a TestClient against the FastAPI app."""
    from app.fast_api_app import app

    return TestClient(app)


def test_summarizer_health_enabled_reports_true():
    """When ENABLE_CONVERSATION_SUMMARIZER is True, endpoint reports enabled=True."""
    with (
        patch(
            "app.persistence.supabase_session_service.ENABLE_CONVERSATION_SUMMARIZER",
            True,
        ),
        patch(
            "app.persistence.supabase_session_service.SESSION_MAX_EVENTS",
            200,
        ),
    ):
        response = _client().get("/health/summarizer")

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert data["session_max_events"] == 200


def test_summarizer_health_disabled_reports_false():
    """When ENABLE_CONVERSATION_SUMMARIZER is False, endpoint reports enabled=False."""
    with (
        patch(
            "app.persistence.supabase_session_service.ENABLE_CONVERSATION_SUMMARIZER",
            False,
        ),
        patch(
            "app.persistence.supabase_session_service.SESSION_MAX_EVENTS",
            200,
        ),
    ):
        response = _client().get("/health/summarizer")

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
    assert data["session_max_events"] == 200


def test_summarizer_health_custom_max_events():
    """Endpoint reflects a custom SESSION_MAX_EVENTS value."""
    with (
        patch(
            "app.persistence.supabase_session_service.ENABLE_CONVERSATION_SUMMARIZER",
            True,
        ),
        patch(
            "app.persistence.supabase_session_service.SESSION_MAX_EVENTS",
            500,
        ),
    ):
        response = _client().get("/health/summarizer")

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert data["session_max_events"] == 500


def test_summarizer_health_response_types():
    """Response fields have the expected types (bool, int) for monitoring parsers."""
    with (
        patch(
            "app.persistence.supabase_session_service.ENABLE_CONVERSATION_SUMMARIZER",
            True,
        ),
        patch(
            "app.persistence.supabase_session_service.SESSION_MAX_EVENTS",
            200,
        ),
    ):
        response = _client().get("/health/summarizer")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["enabled"], bool)
    assert isinstance(data["session_max_events"], int)
    # Canonical health envelope fields should still be present.
    assert data["service"] == "summarizer"
    assert data["status"] == "ok"
    assert "details" in data
    assert isinstance(data["details"], dict)
    assert data["details"]["enabled"] is True
    assert data["details"]["session_max_events"] == 200

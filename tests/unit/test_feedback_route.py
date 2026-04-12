# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for POST /self-improvement/interactions/{id}/feedback route."""

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_il_stub():
    """Ensure a stubbed interaction_logger module is in sys.modules.

    Returns the mock interaction_logger instance so tests can assert on it.
    """
    mock_il = MagicMock()
    mock_il.record_feedback = AsyncMock()

    fake_module = ModuleType("app.services.interaction_logger")
    fake_module.interaction_logger = mock_il  # type: ignore[attr-defined]
    fake_module.InteractionLogger = MagicMock  # type: ignore[attr-defined]
    sys.modules["app.services.interaction_logger"] = fake_module

    return mock_il


def _create_test_app(*, authenticated: bool = True):
    """Create a FastAPI app with the self-improvement router mounted.

    Args:
        authenticated: If True, override get_current_user_id to return a test UUID.
                      If False, leave the real dependency (which will raise 403).
    """
    # Remove cached router module so it re-imports with stubs in place
    for mod_name in list(sys.modules.keys()):
        if "self_improvement" in mod_name and "test_" not in mod_name:
            del sys.modules[mod_name]

    app = FastAPI()

    with patch("app.middleware.rate_limiter.limiter") as mock_limiter:
        mock_limiter.limit.return_value = lambda fn: fn

        from app.routers.self_improvement import router

        app.include_router(router)

    if authenticated:
        from app.routers.onboarding import get_current_user_id

        app.dependency_overrides[get_current_user_id] = lambda: "user-test-123"

    return app


# ---------------------------------------------------------------------------
# Test 1: Valid feedback returns 200 and calls record_feedback
# ---------------------------------------------------------------------------


def test_feedback_valid_rating_calls_record_feedback():
    """POST with valid rating calls record_feedback and returns 200."""
    mock_il = _ensure_il_stub()
    app = _create_test_app()

    client = TestClient(app)
    response = client.post(
        "/self-improvement/interactions/abc-def-uuid/feedback",
        json={"rating": "negative"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["interaction_id"] == "abc-def-uuid"

    mock_il.record_feedback.assert_awaited_once_with(
        interaction_id="abc-def-uuid",
        feedback="negative",
    )


# ---------------------------------------------------------------------------
# Test 2: Invalid rating value returns 422
# ---------------------------------------------------------------------------


def test_feedback_invalid_rating_returns_422():
    """POST with invalid rating (not positive/negative/neutral) returns 422."""
    _ensure_il_stub()
    app = _create_test_app()

    client = TestClient(app)
    response = client.post(
        "/self-improvement/interactions/abc-def-uuid/feedback",
        json={"rating": "terrible"},
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test 3: Missing auth returns 403
# ---------------------------------------------------------------------------


def test_feedback_no_auth_returns_403():
    """POST without auth should return 403 (get_current_user_id raises)."""
    _ensure_il_stub()
    app = _create_test_app(authenticated=False)

    from fastapi import HTTPException

    from app.routers.onboarding import get_current_user_id

    def raise_unauthorized():
        raise HTTPException(status_code=403, detail="Not authenticated")

    app.dependency_overrides[get_current_user_id] = raise_unauthorized

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/self-improvement/interactions/some-uuid/feedback",
        json={"rating": "positive"},
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Test 4: record_feedback receives workspace-scoped interaction_id
# ---------------------------------------------------------------------------


def test_feedback_passes_interaction_id_to_record():
    """The route passes the path-param interaction_id directly to record_feedback."""
    mock_il = _ensure_il_stub()
    app = _create_test_app()

    client = TestClient(app)
    response = client.post(
        "/self-improvement/interactions/workspace-scoped-uuid/feedback",
        json={"rating": "positive"},
    )

    assert response.status_code == 200
    mock_il.record_feedback.assert_awaited_once()
    call_kwargs = mock_il.record_feedback.call_args
    assert call_kwargs.kwargs["interaction_id"] == "workspace-scoped-uuid"
    assert call_kwargs.kwargs["feedback"] == "positive"

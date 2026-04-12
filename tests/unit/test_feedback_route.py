# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for POST /self-improvement/interactions/{id}/feedback route."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# App factory with mocked dependencies
# ---------------------------------------------------------------------------


def _create_test_app():
    """Create a FastAPI app with the self-improvement router mounted."""
    app = FastAPI()

    # Patch rate limiter to be a no-op in tests
    with patch("app.routers.self_improvement.limiter") as mock_limiter:
        mock_limiter.limit.return_value = lambda fn: fn

        from app.routers.self_improvement import router

        app.include_router(router)

    return app


# ---------------------------------------------------------------------------
# Test 1: Valid feedback returns 200 and calls record_feedback
# ---------------------------------------------------------------------------


def test_feedback_valid_rating_calls_record_feedback():
    """POST with valid rating calls record_feedback and returns 200."""
    app = _create_test_app()

    mock_record = AsyncMock()

    with (
        patch(
            "app.routers.self_improvement.get_current_user_id",
            return_value="user-test-123",
        ),
        patch(
            "app.routers.self_improvement.interaction_logger",
            new_callable=lambda: MagicMock,
        ) as mock_il,
    ):
        mock_il.record_feedback = mock_record

        client = TestClient(app)
        response = client.post(
            "/self-improvement/interactions/abc-def-uuid/feedback",
            json={"rating": "negative"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["interaction_id"] == "abc-def-uuid"

    mock_record.assert_awaited_once_with(
        interaction_id="abc-def-uuid",
        feedback="negative",
    )


# ---------------------------------------------------------------------------
# Test 2: Invalid rating value returns 422
# ---------------------------------------------------------------------------


def test_feedback_invalid_rating_returns_422():
    """POST with invalid rating (not positive/negative/neutral) returns 422."""
    app = _create_test_app()

    with patch(
        "app.routers.self_improvement.get_current_user_id",
        return_value="user-test-123",
    ):
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
    app = _create_test_app()

    from fastapi import HTTPException

    def raise_unauthorized():
        raise HTTPException(status_code=403, detail="Not authenticated")

    with patch(
        "app.routers.self_improvement.get_current_user_id",
        side_effect=raise_unauthorized,
    ):
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
    app = _create_test_app()

    mock_record = AsyncMock()

    with (
        patch(
            "app.routers.self_improvement.get_current_user_id",
            return_value="user-test-456",
        ),
        patch(
            "app.routers.self_improvement.interaction_logger",
            new_callable=lambda: MagicMock,
        ) as mock_il,
    ):
        mock_il.record_feedback = mock_record

        client = TestClient(app)
        response = client.post(
            "/self-improvement/interactions/workspace-scoped-uuid/feedback",
            json={"rating": "positive"},
        )

    assert response.status_code == 200
    mock_record.assert_awaited_once()
    call_kwargs = mock_record.call_args
    assert call_kwargs.kwargs["interaction_id"] == "workspace-scoped-uuid"
    assert call_kwargs.kwargs["feedback"] == "positive"

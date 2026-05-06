# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for vertex_image_service retry, classification, and concurrency."""

from unittest.mock import patch

import pytest

from app.services import vertex_image_service


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    """Ensure GOOGLE_CLOUD_PROJECT is set so the service doesn't short-circuit."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Skip real sleeping during retry backoff."""
    monkeypatch.setattr(vertex_image_service.time, "sleep", lambda _s: None)


def _success(model_id: str = "gemini-2.5-flash-image") -> dict:
    return {
        "success": True,
        "image_bytes_base64": "AAAA",
        "mime_type": "image/png",
        "model_used": model_id,
        "count": 1,
    }


def test_success_first_try_calls_vertex_once():
    with patch.object(
        vertex_image_service, "_call_vertex", return_value=_success()
    ) as call:
        result = vertex_image_service.generate_image("a cat")
    assert result["success"] is True
    assert result["mime_type"] == "image/png"
    assert call.call_count == 1


def test_retry_on_429_then_succeed():
    side_effects = [
        Exception("429 RESOURCE_EXHAUSTED quota exceeded"),
        _success(),
    ]
    with patch.object(
        vertex_image_service, "_call_vertex", side_effect=side_effects
    ) as call:
        result = vertex_image_service.generate_image("a cat")
    assert result["success"] is True
    assert call.call_count == 2


def test_terminal_failure_after_max_retries():
    err = Exception("429 RESOURCE_EXHAUSTED quota exceeded")
    with patch.object(vertex_image_service, "_call_vertex", side_effect=err) as call:
        result = vertex_image_service.generate_image("a cat")
    assert result["success"] is False
    assert "RESOURCE_EXHAUSTED" in result["error"]
    assert call.call_count == vertex_image_service.VERTEX_IMAGE_MAX_RETRIES + 1


def test_permanent_error_does_not_retry():
    err = Exception("PERMISSION_DENIED: caller lacks aiplatform.user")
    with patch.object(vertex_image_service, "_call_vertex", side_effect=err) as call:
        result = vertex_image_service.generate_image("a cat")
    assert result["success"] is False
    assert "PERMISSION_DENIED" in result["error"]
    assert call.call_count == 1


def test_unknown_error_retries_at_most_once():
    err = ValueError("No image parts in response")
    with patch.object(vertex_image_service, "_call_vertex", side_effect=err) as call:
        result = vertex_image_service.generate_image("a cat")
    assert result["success"] is False
    # attempt 0 fails -> retry, attempt 1 fails -> stop (unknown errors get
    # one retry, not the full retryable budget)
    assert call.call_count == 2


def test_no_project_short_circuits(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    with patch.object(vertex_image_service, "_call_vertex") as call:
        result = vertex_image_service.generate_image("a cat")
    assert result["success"] is False
    assert "GOOGLE_CLOUD_PROJECT" in result["error"]
    call.assert_not_called()


def test_classify_buckets():
    assert (
        vertex_image_service._classify(Exception("RESOURCE_EXHAUSTED quota"))
        == "retryable"
    )
    assert (
        vertex_image_service._classify(Exception("Got 429 from upstream"))
        == "retryable"
    )
    assert (
        vertex_image_service._classify(Exception("PERMISSION_DENIED on project"))
        == "permanent"
    )
    assert (
        vertex_image_service._classify(Exception("INVALID_ARGUMENT bad model"))
        == "permanent"
    )
    assert (
        vertex_image_service._classify(ValueError("No image parts in response"))
        == "unknown"
    )


def test_models_to_try_dedupes_when_primary_equals_fallback(monkeypatch):
    monkeypatch.setattr(vertex_image_service, "VERTEX_IMAGE_MODEL_PRIMARY", "model-x")
    monkeypatch.setattr(vertex_image_service, "VERTEX_IMAGE_MODEL_FALLBACK", "model-x")
    assert vertex_image_service._models_to_try() == ["model-x"]


def test_models_to_try_returns_both_when_different(monkeypatch):
    monkeypatch.setattr(vertex_image_service, "VERTEX_IMAGE_MODEL_PRIMARY", "model-x")
    monkeypatch.setattr(vertex_image_service, "VERTEX_IMAGE_MODEL_FALLBACK", "model-y")
    assert vertex_image_service._models_to_try() == ["model-x", "model-y"]


def test_extract_retry_after_from_attribute():
    exc = Exception("upstream error")
    exc.retry_delay = 7.5  # type: ignore[attr-defined]
    assert vertex_image_service._extract_retry_after_seconds(exc) == 7.5


def test_extract_retry_after_from_message():
    exc = Exception("RESOURCE_EXHAUSTED, please retry-after: 12s")
    assert vertex_image_service._extract_retry_after_seconds(exc) == 12.0

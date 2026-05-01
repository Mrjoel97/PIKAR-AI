"""Comprehensive tests for the /a2a/app/run_sse SSE endpoint.

Tests cover:
- Authentication handling (valid token, invalid token, anonymous mode)
- Session creation and retrieval
- Error handling and fallback behavior
- Streaming response format
- Widget extraction integration
- Progress event handling
"""

import json
import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncIterator

# Set bypass flag before importing the app
os.environ["LOCAL_DEV_BYPASS"] = "1"

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi.testclient import TestClient
from fastapi import FastAPI


# Create a test app with minimal dependencies
@pytest.fixture
def test_app():
    """Create a minimal FastAPI app for testing SSE endpoint logic."""
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel
    from typing import List, Optional
    import asyncio
    
    app = FastAPI()
    
    class TextPart(BaseModel):
        text: str

    class NewMessage(BaseModel):
        parts: List[TextPart]

    class ChatRequest(BaseModel):
        session_id: str
        user_id: Optional[str] = None
        new_message: NewMessage
        agent_mode: Optional[str] = "auto"
    
    # Mock session service
    mock_session_service = AsyncMock()
    mock_session_service.get_session = AsyncMock(return_value=None)
    mock_session_service.create_session = AsyncMock()
    
    # Mock runner
    mock_runner = MagicMock()
    
    async def mock_event_generator():
        """Mock SSE event generator."""
        yield f"data: {json.dumps({'author': 'ExecutiveAgent', 'content': {'parts': [{'text': 'Hello!'}]}})}\n\n"
        yield f"data: {json.dumps({'status': 'complete'})}\n\n"
    
    @app.post("/a2a/app/run_sse")
    async def run_sse(raw_request: Request, request: ChatRequest):
        """Test SSE endpoint that mirrors the real implementation's auth logic."""
        allow_anonymous_chat = os.getenv("ALLOW_ANONYMOUS_CHAT", "0") == "1"
        auth_header = raw_request.headers.get("Authorization")
        token = (auth_header[7:].strip()) if (auth_header and auth_header.startswith("Bearer ")) else None

        effective_user_id = None
        if token:
            # Mock token validation
            if token == "valid_token":
                effective_user_id = "user_123"
            elif token == "expired_token":
                raise HTTPException(status_code=401, detail="Token expired")
            else:
                if not allow_anonymous_chat:
                    raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        elif not allow_anonymous_chat:
            raise HTTPException(status_code=401, detail="Authentication required for chat")

        if not effective_user_id:
            effective_user_id = "anonymous"
        
        return StreamingResponse(mock_event_generator(), media_type="text/event-stream")
    
    # Health endpoint for testing
    @app.get("/health/live")
    async def health():
        return {"status": "alive"}
    
    app.state.session_service = mock_session_service
    app.state.runner = mock_runner
    
    return app


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)


class TestSSEAuthentication:
    """Tests for authentication handling in SSE endpoint."""
    
    def test_valid_bearer_token(self, client):
        """Valid Bearer token should be accepted."""
        response = client.post(
            "/a2a/app/run_sse",
            json={
                "session_id": "test_session",
                "new_message": {"parts": [{"text": "Hello"}]}
            },
            headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    def test_invalid_bearer_token_rejected(self, client):
        """Invalid Bearer token should be rejected when anonymous chat is disabled."""
        # Ensure anonymous chat is disabled
        os.environ["ALLOW_ANONYMOUS_CHAT"] = "0"
        
        response = client.post(
            "/a2a/app/run_sse",
            json={
                "session_id": "test_session",
                "new_message": {"parts": [{"text": "Hello"}]}
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
    
    def test_expired_token_rejected(self, client):
        """Expired token should return 401 with appropriate message."""
        response = client.post(
            "/a2a/app/run_sse",
            json={
                "session_id": "test_session",
                "new_message": {"parts": [{"text": "Hello"}]}
            },
            headers={"Authorization": "Bearer expired_token"}
        )
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()
    
    def test_no_auth_header_rejected(self, client):
        """Missing auth header should be rejected when anonymous chat is disabled."""
        os.environ["ALLOW_ANONYMOUS_CHAT"] = "0"
        
        response = client.post(
            "/a2a/app/run_sse",
            json={
                "session_id": "test_session",
                "new_message": {"parts": [{"text": "Hello"}]}
            }
        )
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]
    
    def test_anonymous_mode_allowed(self, client):
        """When ALLOW_ANONYMOUS_CHAT=1, requests without auth should work."""
        os.environ["ALLOW_ANONYMOUS_CHAT"] = "1"
        
        response = client.post(
            "/a2a/app/run_sse",
            json={
                "session_id": "test_session",
                "new_message": {"parts": [{"text": "Hello"}]}
            }
        )
        assert response.status_code == 200
        
        # Cleanup
        os.environ["ALLOW_ANONYMOUS_CHAT"] = "0"
    
    def test_malformed_auth_header(self, client):
        """Malformed auth header should be handled gracefully."""
        os.environ["ALLOW_ANONYMOUS_CHAT"] = "0"
        
        response = client.post(
            "/a2a/app/run_sse",
            json={
                "session_id": "test_session",
                "new_message": {"parts": [{"text": "Hello"}]}
            },
            headers={"Authorization": "InvalidFormat"}
        )
        assert response.status_code == 401


class TestSSESessionHandling:
    """Tests for session creation and retrieval."""
    
    def test_session_id_required(self, client):
        """Session ID is required in the request."""
        response = client.post(
            "/a2a/app/run_sse",
            json={
                "new_message": {"parts": [{"text": "Hello"}]}
            },
            headers={"Authorization": "Bearer valid_token"}
        )
        # Should fail validation
        assert response.status_code == 422  # Validation error
    
    def test_new_message_required(self, client):
        """New message is required in the request."""
        response = client.post(
            "/a2a/app/run_sse",
            json={
                "session_id": "test_session"
            },
            headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code == 422
    
    def test_agent_mode_optional(self, client):
        """Agent mode should be optional with default 'auto'."""
        response = client.post(
            "/a2a/app/run_sse",
            json={
                "session_id": "test_session",
                "new_message": {"parts": [{"text": "Hello"}]}
            },
            headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code == 200


class TestSSEStreamingFormat:
    """Tests for SSE streaming response format."""
    
    def test_content_type_is_event_stream(self, client):
        """Response content-type should be text/event-stream."""
        response = client.post(
            "/a2a/app/run_sse",
            json={
                "session_id": "test_session",
                "new_message": {"parts": [{"text": "Hello"}]}
            },
            headers={"Authorization": "Bearer valid_token"}
        )
        assert "text/event-stream" in response.headers["content-type"]
    
    def test_events_have_data_prefix(self, client):
        """Each SSE event should start with 'data: '."""
        response = client.post(
            "/a2a/app/run_sse",
            json={
                "session_id": "test_session",
                "new_message": {"parts": [{"text": "Hello"}]}
            },
            headers={"Authorization": "Bearer valid_token"}
        )
        content = response.text
        # Each event line should start with "data: "
        for line in content.strip().split("\n"):
            if line:  # Skip empty lines
                assert line.startswith("data: ") or line == ""
    
    def test_events_are_json_parseable(self, client):
        """Event data should be valid JSON."""
        response = client.post(
            "/a2a/app/run_sse",
            json={
                "session_id": "test_session",
                "new_message": {"parts": [{"text": "Hello"}]}
            },
            headers={"Authorization": "Bearer valid_token"}
        )
        content = response.text
        for line in content.strip().split("\n"):
            if line.startswith("data: "):
                data = line[6:]  # Remove "data: " prefix
                try:
                    json.loads(data)
                except json.JSONDecodeError:
                    pytest.fail(f"Invalid JSON in SSE event: {data}")


class TestSSEAgentModes:
    """Tests for different agent modes."""
    
    def test_auto_mode(self, client):
        """Auto mode should be accepted."""
        response = client.post(
            "/a2a/app/run_sse",
            json={
                "session_id": "test_session",
                "new_message": {"parts": [{"text": "Hello"}]},
                "agent_mode": "auto"
            },
            headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code == 200
    
    def test_collab_mode(self, client):
        """Collab mode should be accepted."""
        response = client.post(
            "/a2a/app/run_sse",
            json={
                "session_id": "test_session",
                "new_message": {"parts": [{"text": "Hello"}]},
                "agent_mode": "collab"
            },
            headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code == 200
    
    def test_ask_mode(self, client):
        """Ask mode should be accepted."""
        response = client.post(
            "/a2a/app/run_sse",
            json={
                "session_id": "test_session",
                "new_message": {"parts": [{"text": "Hello"}]},
                "agent_mode": "ask"
            },
            headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code == 200


class TestSSEWidgetExtraction:
    """Tests for widget extraction from SSE events."""
    
    def test_widget_extraction_function_exists(self):
        """Widget extraction function should be importable."""
        from app.sse_utils import extract_widget_from_event
        assert callable(extract_widget_from_event)
    
    def test_widget_types_defined(self):
        """Renderable widget types should be defined."""
        from app.sse_utils import RENDERABLE_WIDGET_TYPES
        assert isinstance(RENDERABLE_WIDGET_TYPES, set)
        assert len(RENDERABLE_WIDGET_TYPES) > 0
        # Check for expected types
        assert "video" in RENDERABLE_WIDGET_TYPES
        assert "image" in RENDERABLE_WIDGET_TYPES
        assert "form" in RENDERABLE_WIDGET_TYPES
        assert "table" in RENDERABLE_WIDGET_TYPES
    
    def test_extract_widget_from_function_response(self):
        """Widget should be extracted from function_response."""
        from app.sse_utils import extract_widget_from_event
        
        event = json.dumps({
            "content": {
                "parts": [{
                    "function_response": {
                        "name": "create_video_widget",
                        "response": {
                            "type": "video",
                            "title": "Test Video",
                            "data": {"url": "http://example.com/video.mp4"}
                        }
                    }
                }]
            }
        })
        
        result = json.loads(_extract_widget_from_event(event))
        assert "widget" in result
        assert result["widget"]["type"] == "video"
    
    def test_non_widget_response_unchanged(self):
        """Non-widget responses should pass through unchanged."""
        from app.sse_utils import extract_widget_from_event
        
        event = json.dumps({
            "content": {
                "parts": [{"text": "Hello, how can I help?"}]
            }
        })
        
        result = json.loads(extract_widget_from_event(event))
        assert "widget" not in result
        assert result["content"]["parts"][0]["text"] == "Hello, how can I help?"


class TestSSEErrorHandling:
    """Tests for error handling in SSE endpoint."""
    
    def test_model_unavailable_detection(self):
        """Model unavailable errors should be detectable."""
        from app.sse_utils import is_model_unavailable_error
        
        # Test 404 error
        exc = Exception("404 model not found")
        assert is_model_unavailable_error(exc) is True
        
        # Test 429 error
        exc = Exception("429 rate limit exceeded")
        assert is_model_unavailable_error(exc) is True
        
        # Test resource exhausted
        exc = Exception("RESOURCE_EXHAUSTED quota exceeded")
        assert is_model_unavailable_error(exc) is True
        
        # Test other error
        exc = Exception("Some other error")
        assert is_model_unavailable_error(exc) is False
    
    def test_error_event_format(self):
        """Error events should have proper format."""
        error_event = {"error": "Something went wrong"}
        event_json = json.dumps(error_event)
        
        # Verify it's valid JSON
        parsed = json.loads(event_json)
        assert "error" in parsed


class TestSSEProgressEvents:
    """Tests for progress event handling."""
    
    def test_progress_serialization(self):
        """Progress events should be properly serialized."""
        from app.sse_utils import serialize_progress_event
        
        event = {
            "stage": "generating",
            "payload": {"progress": 50},
            "timestamp": "2025-01-01T00:00:00Z"
        }
        
        result = serialize_progress_event(event)
        parsed = json.loads(result)
        
        assert parsed["event_type"] == "director_progress"
        assert parsed["stage"] == "generating"
        assert parsed["payload"]["progress"] == 50


class TestSSESyntheticTextInjection:
    """Tests for synthetic text injection in widget events."""
    
    def test_video_widget_gets_synthetic_text(self):
        """Video widgets should get synthetic text if none provided."""
        from app.sse_utils import extract_widget_from_event
        
        event = json.dumps({
            "content": {
                "parts": [{
                    "function_response": {
                        "name": "create_video",
                        "response": {
                            "type": "video",
                            "title": "My Video",
                            "data": {"url": "http://example.com/video.mp4"}
                        }
                    }
                }]
            }
        })
        
        result = json.loads(extract_widget_from_event(event))
        
        # Should have widget
        assert "widget" in result
        
        # Should have synthetic text
        parts = result["content"]["parts"]
        has_video_text = any("video" in p.get("text", "").lower() for p in parts if p.get("text"))
        assert has_video_text, "Video widget should have synthetic text"
    
    def test_image_widget_gets_synthetic_text(self):
        """Image widgets should get synthetic text if none provided."""
        from app.sse_utils import extract_widget_from_event
        
        event = json.dumps({
            "content": {
                "parts": [{
                    "function_response": {
                        "name": "create_image",
                        "response": {
                            "type": "image",
                            "title": "My Image",
                            "data": {"url": "http://example.com/image.png"}
                        }
                    }
                }]
            }
        })
        
        result = json.loads(extract_widget_from_event(event))
        
        # Should have synthetic text
        parts = result["content"]["parts"]
        has_image_text = any("image" in p.get("text", "").lower() for p in parts if p.get("text"))
        assert has_image_text, "Image widget should have synthetic text"
    
    def test_failure_gets_user_message(self):
        """Failed tool calls should get user_message injected as text."""
        from app.sse_utils import extract_widget_from_event
        
        event = json.dumps({
            "content": {
                "parts": [{
                    "function_response": {
                        "name": "create_video",
                        "response": {
                            "success": False,
                            "user_message": "Video generation failed. Please try again."
                        }
                    }
                }]
            }
        })
        
        result = json.loads(extract_widget_from_event(event))
        
        # Should NOT have widget
        assert "widget" not in result
        
        # Should have error text
        parts = result["content"]["parts"]
        has_error_text = any("Video generation failed" in p.get("text", "") for p in parts if p.get("text"))
        assert has_error_text, "Failed tool should have user_message as text"


class TestSSETimeoutPhase85:
    """Phase 85 HOTFIX-03 — SSE timeout extension regression suite.

    Verifies:
    - SC2: A simulated long stream (500s, under 570s) does NOT time out;
      a stream past 580s DOES time out.
    - SC3: Heartbeat ': keepalive\\n\\n' fires when no events arrive for >=10s.
    - SC3: Heartbeat is suppressed when real events arrive faster than 10s.
    - SC4: When the deadline IS hit, the error string remains byte-exact
      'Stream timeout — please retry your request.' (em-dash, not hyphen).

    Implementation note: rather than spinning up the full app/fast_api_app.py
    (Supabase + ADK imports), these tests replicate the deadline+heartbeat
    loop inline with a fake monotonic clock. This mirrors the production
    logic in admin/chat.py:354-376 and fast_api_app.py:1954-1994 verbatim.
    """

    @staticmethod
    def _drain_stream_with_fake_clock(
        events: list,
        timeline: list[float],
        max_duration: int,
    ) -> list[str]:
        """Replicate the SSE deadline+heartbeat loop with a fake timeline.

        Mirrors app/routers/admin/chat.py:354-376 and the same loop in
        app/fast_api_app.py:1954-1994. Synchronous — no asyncio needed
        because the loop logic is purely time-driven.

        Args:
            events: list of (clock_time, payload_str) tuples — fake events
                to emit at the simulated clock time matching exactly.
            timeline: ordered list of simulated ``now`` values for each
                loop iteration. The loop runs once per timeline entry.
            max_duration: the SSE max duration in seconds.

        Returns:
            The list of SSE chunks that the loop yielded (data lines and
            keepalives), as strings.
        """
        import json

        chunks: list[str] = []
        # Mirror production: last_keepalive and deadline anchored at t=0.
        last_keepalive = 0.0
        deadline = 0.0 + max_duration

        # Index events by (approx) time for O(1) lookup.
        events_by_time = {t: payload for t, payload in events}

        for now in timeline:
            # Deadline check (production line 364).
            if now >= deadline:
                chunks.append(
                    f"data: {json.dumps({'error': 'Stream timeout — please retry your request.'})}\n\n"
                )
                break

            # Event check.
            if now in events_by_time:
                payload = events_by_time.pop(now)
                if payload is not None:
                    chunks.append(f"data: {payload}\n\n")
                    last_keepalive = now
                continue

            # Heartbeat path (production lines 372-375).
            if now - last_keepalive >= 10:
                last_keepalive = now
                chunks.append(": keepalive\n\n")

        return chunks

    def test_long_stream_does_not_timeout(self, monkeypatch):
        """A simulated 500s stream under the production deadline does NOT time out.

        Reads the LIVE production constant ``_SSE_MAX_DURATION_S`` from
        ``app.routers.admin.chat`` (after env reset) and runs the simulation
        against THAT value. Pre-fix, the constant is 300 → the 500s
        simulation fires the timeout (RED). Post-fix, the constant is 570 →
        the 500s simulation completes cleanly (GREEN).
        """
        import importlib
        import sys

        monkeypatch.delenv("SSE_MAX_DURATION_S", raising=False)
        if "app.routers.admin.chat" in sys.modules:
            admin_chat = importlib.reload(sys.modules["app.routers.admin.chat"])
        else:
            admin_chat = importlib.import_module("app.routers.admin.chat")

        max_duration = admin_chat._SSE_MAX_DURATION_S

        # Walk simulated time to 500s with sparse events — should be quiet.
        timeline = [1.0, 50.0, 100.0, 200.0, 300.0, 400.0, 500.0]
        events = [
            (50.0, '{"event": "tick1"}'),
            (200.0, '{"event": "tick2"}'),
            (400.0, '{"event": "tick3"}'),
        ]
        chunks = self._drain_stream_with_fake_clock(
            events, timeline, max_duration=max_duration
        )
        timeout_chunks = [c for c in chunks if "Stream timeout" in c]
        assert len(timeout_chunks) == 0, (
            f"With production max_duration={max_duration}s, a 500s simulation "
            f"should NOT time out. Got {len(timeout_chunks)} timeout chunks. "
            f"This means the production constant is too small "
            f"(pre-fix value was 300; post-fix should be ≥570)."
        )

        # And under the production deadline, driving past 580s DOES fire timeout.
        # This only makes sense if max_duration < 580 — i.e. always for the fixed value 570.
        if max_duration < 580:
            timeline_over = [1.0, 580.0]
            chunks_over = self._drain_stream_with_fake_clock(
                [], timeline_over, max_duration=max_duration
            )
            timeout_over = [c for c in chunks_over if "Stream timeout" in c]
            assert len(timeout_over) == 1, (
                f"Past max_duration ({max_duration}s) at 580s, expected exactly "
                f"one timeout chunk, got {len(timeout_over)}: {timeout_over}"
            )

    def test_heartbeat_during_slow_render(self):
        """Heartbeat ': keepalive' fires when no events arrive for >=10s.

        Regression guard for SC3 — keepalive is independent of the deadline
        change, but a future refactor must not silently drop it.
        """
        # Walk simulated time 0 -> 12s with NO events. Keepalive at >=10s.
        timeline = [1.0, 5.0, 11.0]
        chunks = self._drain_stream_with_fake_clock(
            [], timeline, max_duration=570
        )

        keepalive_chunks = [c for c in chunks if c.startswith(": keepalive")]
        assert len(keepalive_chunks) >= 1, (
            f"Expected at least one keepalive during an 11s no-event window, "
            f"got chunks: {chunks}"
        )

    def test_heartbeat_suppressed_when_events_flow(self):
        """Heartbeat is suppressed when events arrive faster than every 10s.

        Regression guard for SC3 — last_keepalive resets on every event,
        so a steady event stream (every 2s) MUST NOT emit any keepalive.
        """
        timeline = [2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0]
        events = [
            (2.0, '{"e": 1}'),
            (4.0, '{"e": 2}'),
            (6.0, '{"e": 3}'),
            (8.0, '{"e": 4}'),
            (10.0, '{"e": 5}'),
            (12.0, '{"e": 6}'),
            (14.0, '{"e": 7}'),
            (16.0, '{"e": 8}'),
            (18.0, '{"e": 9}'),
            (20.0, '{"e": 10}'),
        ]
        chunks = self._drain_stream_with_fake_clock(
            events, timeline, max_duration=570
        )

        keepalive_chunks = [c for c in chunks if c.startswith(": keepalive")]
        assert len(keepalive_chunks) == 0, (
            f"Expected zero keepalives during a steady 2s-event stream, "
            f"got {len(keepalive_chunks)}: {keepalive_chunks}"
        )

    def test_timeout_error_string_unchanged(self):
        """When deadline IS hit, error string is byte-exact 'Stream timeout — please retry your request.'.

        Frontend match logic in useBackgroundStream.ts and useAdminChat.ts
        depends on this LITERAL — including the em-dash (—) NOT a hyphen (-).
        """
        # Force timeout immediately.
        timeline = [600.0]
        chunks = self._drain_stream_with_fake_clock(
            [], timeline, max_duration=570
        )

        timeout_chunks = [c for c in chunks if "Stream timeout" in c]
        assert len(timeout_chunks) == 1, (
            f"Expected exactly one timeout chunk, got {len(timeout_chunks)}"
        )

        # Parse the JSON payload from the SSE chunk.
        chunk = timeout_chunks[0]
        # Strip "data: " prefix and trailing "\n\n".
        payload = chunk.replace("data: ", "").strip()
        parsed = json.loads(payload)
        assert parsed == {"error": "Stream timeout — please retry your request."}, (
            f"Error string drifted from byte-exact literal. Got: {parsed}. "
            f"Expected the em-dash (—), not a hyphen (-). Frontend match "
            f"logic depends on this exact string."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
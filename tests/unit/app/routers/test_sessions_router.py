# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for GET /sessions — the user-scoped chat session list endpoint.

Covers the regression where chat history "disappeared on reload" because the
frontend had no authoritative way to enumerate the user's persisted sessions.
The endpoint must:
- Return only the authenticated user's sessions
- Use cached title/preview from session.state when present
- Derive title from the first user message when state is missing
- Derive preview from the most recent agent message when state is missing
- Truncate long titles/previews to keep payloads small
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Stub app.middleware.rate_limiter as a no-op for THIS module only. We do this
# at the module level (not in a fixture) because the router we're testing
# imports `from app.middleware.rate_limiter import ...` at its own import time;
# a fixture would run too late. We register cleanup via a module-scoped autouse
# fixture below so the stub is removed when this file finishes — keeping it
# from leaking into other test files in the same pytest session.
# ---------------------------------------------------------------------------

_PREEXISTING_RATE_LIMITER = sys.modules.get("app.middleware.rate_limiter")
_PREEXISTING_SUPABASE = sys.modules.get("app.services.supabase")
_PREEXISTING_ROUTER = sys.modules.get("app.routers.sessions")

_mock_rate_limiter = types.ModuleType("app.middleware.rate_limiter")
_mock_limiter = MagicMock()
_mock_limiter.limit = lambda *a, **kw: lambda fn: fn
_mock_rate_limiter.limiter = _mock_limiter
_mock_rate_limiter.get_user_persona_limit = MagicMock(return_value="1000/minute")
_mock_rate_limiter._parse_limit_int = MagicMock(return_value=1000)
_mock_rate_limiter.build_rate_limit_headers = MagicMock(return_value={})
_mock_rate_limiter.redis_sliding_window_check = MagicMock(return_value=(True, 0))
sys.modules["app.middleware.rate_limiter"] = _mock_rate_limiter


@pytest.fixture(scope="module", autouse=True)
def _restore_stubbed_modules():
    """Restore originals when this test module finishes so other tests aren't poisoned."""
    yield
    for name, original in (
        ("app.middleware.rate_limiter", _PREEXISTING_RATE_LIMITER),
        ("app.services.supabase", _PREEXISTING_SUPABASE),
        ("app.routers.sessions", _PREEXISTING_ROUTER),
    ):
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original


async def _default_get_current_user_id() -> str:
    return "user-test-123"


def _stub_module(path: str, **attrs: object) -> None:
    if path not in sys.modules:
        mod = types.ModuleType(path)
        for name, val in attrs.items():
            setattr(mod, name, val)
        sys.modules[path] = mod


_stub_module(
    "app.routers.onboarding",
    get_current_user_id=_default_get_current_user_id,
    router=MagicMock(),
)


# ---------------------------------------------------------------------------
# Supabase query-builder stub
# ---------------------------------------------------------------------------


class _FakeQuery:
    """Mimics the chained PostgREST builder used by the supabase client."""

    def __init__(self, rows: list[dict]):
        self._rows = rows

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def is_(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        return MagicMock(data=list(self._rows))


def _make_supabase_client(
    sessions_rows: list[dict], events_rows: list[dict] | None = None
) -> MagicMock:
    """Build a fake supabase client whose .table() returns the right query stub."""
    events_rows = events_rows or []
    client = MagicMock()

    def _table(name: str):
        if name == "sessions":
            return _FakeQuery(sessions_rows)
        if name == "session_events":
            return _FakeQuery(events_rows)
        raise AssertionError(f"Unexpected table {name}")

    client.table.side_effect = _table
    return client


def _build_app(supabase_client: MagicMock, *, user_id: str = "user-test-123"):
    """Build a minimal FastAPI app wrapping the sessions router.

    Each call refreshes the ``app.services.supabase`` stub with the supplied
    client and re-imports the router so it binds against the new factory.
    Without this, the stub from the first test would leak into every
    subsequent test because ``_stub_module`` is insert-once.
    """
    if "app.services.supabase" not in sys.modules:
        sys.modules["app.services.supabase"] = types.ModuleType("app.services.supabase")
    supabase_mod = sys.modules["app.services.supabase"]
    supabase_mod.get_service_client = MagicMock(return_value=supabase_client)
    supabase_mod.get_async_client = MagicMock(return_value=supabase_client)

    if "app.routers.sessions" in sys.modules:
        del sys.modules["app.routers.sessions"]
    from app.routers.onboarding import get_current_user_id
    from app.routers.sessions import router

    app = FastAPI()

    async def _fake_user_id() -> str:
        return user_id

    app.dependency_overrides[get_current_user_id] = _fake_user_id
    app.include_router(router)
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_sessions_with_cached_title_and_preview_no_event_lookup():
    """When state.title and state.lastMessage are present, no events query runs."""
    sessions_rows = [
        {
            "session_id": "s-1",
            "state": {"title": "Q4 plan brainstorm", "lastMessage": "Sounds good"},
            "created_at": "2026-04-26T10:00:00Z",
            "updated_at": "2026-04-26T11:00:00Z",
        },
    ]
    supabase = _make_supabase_client(sessions_rows)
    app = _build_app(supabase)
    client = TestClient(app)

    resp = client.get("/sessions")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["count"] == 1
    assert body["sessions"][0]["id"] == "s-1"
    assert body["sessions"][0]["title"] == "Q4 plan brainstorm"
    assert body["sessions"][0]["preview"] == "Sounds good"
    # Only sessions table should have been queried — no events lookup.
    table_calls = [c.args[0] for c in supabase.table.call_args_list]
    assert "session_events" not in table_calls


def test_derives_title_from_first_user_message_when_state_missing():
    """When state.title is absent, the title is derived from the first user message."""
    sessions_rows = [
        {
            "session_id": "s-2",
            "state": {},
            "created_at": "2026-04-26T10:00:00Z",
            "updated_at": "2026-04-26T11:00:00Z",
        },
    ]
    events_rows = [
        {
            "session_id": "s-2",
            "event_index": 0,
            "event_data": {
                "source": "user",
                "content": {"parts": [{"text": "Help me write a marketing brief"}]},
            },
        },
        {
            "session_id": "s-2",
            "event_index": 1,
            "event_data": {
                "source": "model",
                "content": {"parts": [{"text": "Sure! What's the campaign goal?"}]},
            },
        },
    ]
    supabase = _make_supabase_client(sessions_rows, events_rows)
    app = _build_app(supabase)
    client = TestClient(app)

    resp = client.get("/sessions")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    s = body["sessions"][0]
    assert s["title"] == "Help me write a marketing brief"
    assert s["preview"] == "Sure! What's the campaign goal?"


def test_truncates_long_title_and_preview():
    """Titles and previews are truncated with an ellipsis."""
    long_user = "x" * 200
    long_agent = "y" * 200
    sessions_rows = [
        {
            "session_id": "s-3",
            "state": {},
            "created_at": "2026-04-26T10:00:00Z",
            "updated_at": "2026-04-26T11:00:00Z",
        },
    ]
    events_rows = [
        {
            "session_id": "s-3",
            "event_index": 0,
            "event_data": {
                "source": "user",
                "content": {"parts": [{"text": long_user}]},
            },
        },
        {
            "session_id": "s-3",
            "event_index": 1,
            "event_data": {
                "source": "model",
                "content": {"parts": [{"text": long_agent}]},
            },
        },
    ]
    supabase = _make_supabase_client(sessions_rows, events_rows)
    app = _build_app(supabase)
    client = TestClient(app)

    resp = client.get("/sessions")
    body = resp.json()
    s = body["sessions"][0]
    assert s["title"].endswith("...")
    assert len(s["title"]) <= 64  # 60 + len("...")
    assert s["preview"].endswith("...")
    assert len(s["preview"]) <= 104


def test_returns_empty_list_when_no_sessions():
    supabase = _make_supabase_client([])
    app = _build_app(supabase)
    client = TestClient(app)

    resp = client.get("/sessions")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"sessions": [], "count": 0}


def test_falls_back_to_session_id_derived_title_when_no_user_message_found():
    """If we can't derive a title from events, fall back to a date-from-id title."""
    sessions_rows = [
        {
            "session_id": "session-1714060800000-abc",  # 2024-04-25 timestamp
            "state": {},
            "created_at": "2024-04-25T12:00:00Z",
            "updated_at": "2024-04-25T12:00:00Z",
        },
    ]
    # No events for this session
    events_rows = []
    supabase = _make_supabase_client(sessions_rows, events_rows)
    app = _build_app(supabase)
    client = TestClient(app)

    resp = client.get("/sessions")
    body = resp.json()
    title = body["sessions"][0]["title"]
    assert title.startswith("Chat from") or title == "Untitled Chat"


def test_respects_limit_query_parameter():
    """The endpoint passes the limit query param through to the supabase query."""
    sessions_rows = [
        {
            "session_id": f"s-{i}",
            "state": {"title": f"Title {i}", "lastMessage": "msg"},
            "created_at": "2026-04-26T10:00:00Z",
            "updated_at": f"2026-04-26T11:00:{i:02d}Z",
        }
        for i in range(3)
    ]
    supabase = _make_supabase_client(sessions_rows)
    app = _build_app(supabase)
    client = TestClient(app)

    resp = client.get("/sessions?limit=10")
    assert resp.status_code == 200
    assert resp.json()["count"] == 3


def test_rejects_limit_out_of_range():
    sessions_rows: list[dict] = []
    supabase = _make_supabase_client(sessions_rows)
    app = _build_app(supabase)
    client = TestClient(app)

    assert client.get("/sessions?limit=0").status_code == 422
    assert client.get("/sessions?limit=999").status_code == 422


def test_handles_partial_state_with_only_title_cached():
    """When title is cached but preview is not, only preview is derived."""
    sessions_rows = [
        {
            "session_id": "s-mixed",
            "state": {"title": "Cached title"},
            "created_at": "2026-04-26T10:00:00Z",
            "updated_at": "2026-04-26T11:00:00Z",
        },
    ]
    events_rows = [
        {
            "session_id": "s-mixed",
            "event_index": 0,
            "event_data": {
                "source": "user",
                "content": {
                    "parts": [{"text": "user msg should not be used as title"}]
                },
            },
        },
        {
            "session_id": "s-mixed",
            "event_index": 1,
            "event_data": {
                "source": "model",
                "content": {"parts": [{"text": "agent msg used as preview"}]},
            },
        },
    ]
    supabase = _make_supabase_client(sessions_rows, events_rows)
    app = _build_app(supabase)
    client = TestClient(app)

    resp = client.get("/sessions")
    body = resp.json()
    s = body["sessions"][0]
    assert s["title"] == "Cached title"
    assert s["preview"] == "agent msg used as preview"

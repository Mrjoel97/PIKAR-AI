---
phase: 07-foundation
plan: 03
subsystem: admin-chat
tags: [admin, sse, streaming, session-persistence, confirmation-tokens, audit]
dependency_graph:
  requires: [07-01, 07-02]
  provides: [admin-chat-sse-endpoint, admin-session-persistence, admin-chat-history]
  affects: [admin-frontend-plan-04]
tech_stack:
  added: []
  patterns:
    - SSE streaming via FastAPI StreamingResponse + asyncio.Queue
    - ADK Runner with per-request InMemorySessionService (isolated from main runner)
    - Atomic confirmation token consumption via Redis GETDEL (from 07-02)
    - Individual message rows (not JSONB blobs) in admin_chat_messages
key_files:
  created:
    - app/routers/admin/chat.py
    - tests/unit/admin/test_admin_chat.py
  modified:
    - app/routers/admin/__init__.py
decisions:
  - Per-request ADK Runner with InMemorySessionService keeps admin chat sessions isolated from main executive agent; avoids cross-contamination of session state
  - SSE session_id announcement on first event lets frontend persist new session ids without a separate API call
  - _persist_message logs errors but never raises — mirrors the audit service pattern so a DB hiccup never breaks the live SSE stream
  - Confirmation token stored in Redis by agent (via store_confirmation_token in SSE generator) when agent returns requires_confirmation_token in state_delta; consumed atomically before next stream
key_decisions:
  - Per-request ADK Runner with InMemorySessionService for admin chat (isolated from main runner)
  - SSE first event contains session_id for frontend persistence
  - _persist_message is fire-and-log (errors logged, never raised)
metrics:
  duration: 7 min
  completed: "2026-03-21"
  tasks_completed: 2
  files_changed: 3
  tests_added: 6
  tests_total_admin: 37
requirements_satisfied: [ASST-01, ASST-06]
---

# Phase 7 Plan 3: Admin Chat SSE Endpoint Summary

SSE chat endpoint bridging AdminAgent to admin frontend: session persistence, message history, confirmation token handling, and audit logging via POST /admin/chat with InMemorySessionService-backed ADK Runner.

## What Was Built

### `app/routers/admin/chat.py`

Three endpoints registered under the `/admin` prefix:

| Endpoint | Rate Limit | Purpose |
|---|---|---|
| `POST /admin/chat` | 30/min | Stream AdminAgent responses via SSE |
| `GET /admin/chat/sessions` | 60/min | List admin's sessions (newest first) |
| `GET /admin/chat/history/{session_id}` | 60/min | Load message history for cross-refresh continuity |

**Session management** (`_get_or_create_session`):
- `session_id=None`: inserts new `admin_chat_sessions` row with `admin_user_id` and title (first 50 chars of message); returns new UUID
- `session_id` provided: verifies ownership via `admin_user_id` match; raises `HTTPException 403` if not owned

**Message persistence** (`_persist_message`):
- User message written to `admin_chat_messages` with `role="user"` before streaming begins
- Agent response accumulated across SSE events and written with `role="agent"` after stream completes
- Errors logged, never raised (stream must not break on DB hiccup)

**Confirmation flow** (`_consume_token_or_error`):
- Calls `consume_confirmation_token(token)` atomically before streaming starts
- Returns `None` on expired/double-use token → yields SSE error `"Confirmation token expired or already used"` and exits
- On success, injects `[CONFIRMED ACTION]` prefix into ADK message so agent executes the confirmed action

**SSE streaming** (`_admin_sse_generator`):
- First event: `{"session_id": "..."}` for frontend persistence
- ADK `Runner` with per-request `InMemorySessionService` wrapping `admin_agent`
- Events yielded as `data: {json}\n\n`; keepalive comment every 10s; 5-minute max duration
- Agent `requires_confirmation_token` in `state_delta` triggers `store_confirmation_token` during stream

**Audit**: `log_admin_action(source="ai_agent")` called after every chat interaction with message preview and response time.

### `app/routers/admin/__init__.py`

Updated to import and register `chat.router` alongside existing `auth.router`.

### `tests/unit/admin/test_admin_chat.py`

6 unit tests covering the helper functions directly (no HTTP overhead):

| Test | What it verifies |
|---|---|
| `test_create_session_on_missing_id` | New session row inserted with correct `admin_user_id` and `title` |
| `test_session_ownership_rejected` | `HTTPException 403` raised when session belongs to different user |
| `test_token_consumed_before_stream` | `consume_confirmation_token` called with provided token |
| `test_double_use_token_error` | Returns `None` when token expired or already consumed |
| `test_user_message_persisted` | Insert call with `role="user"` |
| `test_agent_response_persisted` | Insert call with `role="agent"` |

## Deviations from Plan

None — plan executed exactly as written.

The plan specified testing helper functions directly (`_get_or_create_session`, `_persist_message`, `_consume_token_or_error`) rather than through the HTTP layer. This was the correct approach: it avoids mocking the entire ADK Runner stack and keeps tests fast and focused.

## Verification Results

```
uv run pytest tests/unit/admin/test_admin_chat.py -x -v   → 6 passed
uv run pytest tests/unit/admin/ -x -q                     → 37 passed (no regressions)
uv run ruff check app/routers/admin/ --fix                 → All checks passed
uv run ruff format app/routers/admin/ --check              → 3 files already formatted
```

Structural inspection confirms all required elements present in `chat.py`:
- `StreamingResponse`, `Depends(require_admin)`, `admin_chat_messages`, `admin_chat_sessions`
- `consume_confirmation_token`, `store_confirmation_token`, `log_admin_action`
- `30/minute` rate limit, `list_admin_chat_sessions`, `get_admin_chat_history`

## Self-Check: PASSED

Files confirmed:
- `app/routers/admin/chat.py` — exists, 517 lines
- `tests/unit/admin/test_admin_chat.py` — exists, 6 test cases
- `app/routers/admin/__init__.py` — updated, chat router registered

Commits confirmed:
- `0839191` — test(07-03): add failing tests for admin chat session and token logic
- `c4e143b` — feat(07-03): SSE chat endpoint with session persistence and confirmation handling

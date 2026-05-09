# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for `wait_for_approval` (ARTIFACT-04 — resume-on-decision).

Covers:
- Test 1: helper blocks while the row is PENDING, then unblocks and returns
  ``{"decision": "approve", ...}`` once the row flips to APPROVED.
- Test 2: same flow for REJECTED → ``{"decision": "reject", ...}``.
- Test 3: row stays PENDING for the whole timeout — helper returns
  ``{"decision": "timeout", ...}`` after roughly ``timeout_s`` seconds.
- Test 4: token hashing is consistent with ``request_human_approval``
  (SHA-256 of plain token), so the polling key actually matches inserted rows.
- Test 5: tool list export — ``APPROVAL_TOOLS`` includes ``wait_for_approval``
  and ``request_human_approval`` so the executive agent can be wired up.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers — a tiny stub of the supabase query builder chain that the helper
# uses: supabase.table(t).select(...).eq("token", h).single() → .execute().
# We let the test flip the "row" mid-poll to simulate the user clicking
# Approve / Reject.
# ---------------------------------------------------------------------------


class _StubResponse:
    """Minimal shim mimicking ``execute()``'s return shape."""

    def __init__(self, data: dict[str, Any] | None) -> None:
        self.data = data


class _StubQuery:
    """Mimics the chained Supabase query builder used by the helper.

    Every chained call returns ``self`` until ``execute()`` is invoked, at
    which point it returns whatever the parent stub's row currently is.
    """

    def __init__(self, parent: "_StubSupabase") -> None:
        self._parent = parent

    def select(self, *_args: Any, **_kwargs: Any) -> "_StubQuery":
        return self

    def eq(self, *_args: Any, **_kwargs: Any) -> "_StubQuery":
        return self

    def single(self) -> "_StubQuery":
        return self

    def execute(self) -> _StubResponse:  # sync — execute_async sync-fallback
        self._parent.poll_count += 1
        return _StubResponse(self._parent.row)


class _StubSupabase:
    def __init__(self, initial_row: dict[str, Any] | None) -> None:
        self.row = initial_row
        self.poll_count = 0

    def table(self, _name: str) -> _StubQuery:
        return _StubQuery(self)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Test 1 — APPROVED path: helper blocks while PENDING, unblocks on flip.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wait_for_approval_returns_approve_when_row_flips() -> None:
    from app.agents.tools import approval_tool

    token = "tkn_approve_xyz"
    stub = _StubSupabase({"status": "PENDING", "responded_at": None, "payload": {}})

    async def flip_to_approved() -> None:
        # Let the helper poll at least once while still PENDING, then flip.
        await asyncio.sleep(0.25)
        stub.row = {
            "status": "APPROVED",
            "responded_at": "2026-05-09T12:00:00+00:00",
            "payload": {"decided_by": "user-abc"},
        }

    with patch.object(approval_tool, "get_service_client", return_value=stub):
        flipper = asyncio.create_task(flip_to_approved())
        start = time.monotonic()
        result = await approval_tool.wait_for_approval(
            token, timeout_s=2, poll_interval_s=0.05
        )
        elapsed = time.monotonic() - start
        await flipper

    assert result["decision"] == "approve"
    assert result["token"] == token
    assert result["status"] == "APPROVED"
    assert result["decided_at"] == "2026-05-09T12:00:00+00:00"
    assert result["decided_by"] == "user-abc"
    # Sanity: helper actually waited (it didn't return on the first poll
    # before the flip happened) and didn't run to the full timeout.
    assert elapsed >= 0.2, "helper returned too early — should have blocked"
    assert elapsed < 2.0, "helper ran past the row-flip — should have woken up"
    assert stub.poll_count >= 2, "helper should have polled multiple times"


# ---------------------------------------------------------------------------
# Test 2 — REJECTED path.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wait_for_approval_returns_reject_when_row_flips() -> None:
    from app.agents.tools import approval_tool

    token = "tkn_reject_xyz"
    stub = _StubSupabase({"status": "PENDING", "responded_at": None, "payload": {}})

    async def flip_to_rejected() -> None:
        await asyncio.sleep(0.2)
        stub.row = {
            "status": "REJECTED",
            "responded_at": "2026-05-09T12:05:00+00:00",
            "payload": {"decided_by": "user-def"},
        }

    with patch.object(approval_tool, "get_service_client", return_value=stub):
        flipper = asyncio.create_task(flip_to_rejected())
        result = await approval_tool.wait_for_approval(
            token, timeout_s=2, poll_interval_s=0.05
        )
        await flipper

    assert result["decision"] == "reject"
    assert result["token"] == token
    assert result["status"] == "REJECTED"
    assert result["decided_by"] == "user-def"


# ---------------------------------------------------------------------------
# Test 3 — TIMEOUT path: row stays PENDING.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wait_for_approval_returns_timeout_when_row_never_decides() -> None:
    from app.agents.tools import approval_tool

    token = "tkn_timeout_xyz"
    stub = _StubSupabase({"status": "PENDING", "responded_at": None, "payload": {}})

    with patch.object(approval_tool, "get_service_client", return_value=stub):
        start = time.monotonic()
        result = await approval_tool.wait_for_approval(
            token, timeout_s=0.4, poll_interval_s=0.1
        )
        elapsed = time.monotonic() - start

    assert result["decision"] == "timeout"
    assert result["token"] == token
    assert result["status"] == "PENDING"
    assert result["decided_at"] is None
    assert result["decided_by"] is None
    # Should respect the timeout (with a generous upper bound for sleep jitter).
    assert 0.3 <= elapsed <= 1.5
    assert stub.poll_count >= 2


# ---------------------------------------------------------------------------
# Test 4 — token hashing matches the storage scheme used by
# `request_human_approval` (so the polling key actually finds the row).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wait_for_approval_uses_sha256_token_hash() -> None:
    from app.agents.tools import approval_tool

    token = "plain_token_capture_hash"
    expected_hash = _hash(token)

    captured_eq_calls: list[tuple[str, str]] = []

    class _CapturingQuery(_StubQuery):
        def eq(self, col: str, val: str) -> "_StubQuery":
            captured_eq_calls.append((col, val))
            return self

    class _CapturingSupabase(_StubSupabase):
        def table(self, _name: str) -> _StubQuery:
            return _CapturingQuery(self)

    stub = _CapturingSupabase(
        {
            "status": "APPROVED",
            "responded_at": "2026-05-09T12:00:00+00:00",
            "payload": {},
        }
    )

    with patch.object(approval_tool, "get_service_client", return_value=stub):
        result = await approval_tool.wait_for_approval(
            token, timeout_s=1, poll_interval_s=0.05
        )

    assert result["decision"] == "approve"
    # The helper must hash the token (never query by plain text).
    assert (
        "token",
        expected_hash,
    ) in captured_eq_calls, f"helper queried with: {captured_eq_calls}"
    assert ("token", token) not in captured_eq_calls, (
        "helper leaked the plain token into the query"
    )


# ---------------------------------------------------------------------------
# Test 5 — APPROVAL_TOOLS export contract.
# ---------------------------------------------------------------------------


def test_approval_tools_export_contains_both_functions() -> None:
    from app.agents.tools import approval_tool

    assert hasattr(approval_tool, "APPROVAL_TOOLS")
    names = {fn.__name__ for fn in approval_tool.APPROVAL_TOOLS}
    assert "request_human_approval" in names
    assert "wait_for_approval" in names

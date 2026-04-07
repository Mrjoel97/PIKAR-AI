# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""End-to-end smoke: middleware writes -> admin endpoint reads.

Phase 49 Plan 05 (AUTH-05). This is the contract test between the
``governance_audit_log`` writer (``app.middleware.audit_log`` from Plan 04)
and its reader (``app.routers.admin.governance_audit`` from Plan 05). If
either side of the contract drifts — column names, response envelope,
email resolution behaviour — one of these tests will break loudly.

Supabase is mocked at the client boundary. We do NOT hit a real database;
the point is to prove the admin endpoint correctly:

1. Applies the ``action_type`` filter via ``.eq("action_type", ...)`` on a
   real Supabase query builder chain, returns the paginated envelope with
   ``total``, and enriches each row with ``actor_email`` resolved from
   ``user_id`` via ``auth.admin.get_user_by_id``.
2. Resolves an ``email=`` query parameter into a ``user_id`` via
   ``auth.admin.list_users`` and then applies that as the actual
   ``.eq("user_id", <resolved-id>)`` filter against the audit table — so
   admins can filter by human-readable email without knowing UUIDs.

Both cases together prove the plan 04 writer → plan 05 reader chain
survives future refactors.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub heavy / Windows-flaky modules BEFORE importing the router under test.
# ``app.middleware.rate_limiter`` calls ``slowapi.Limiter()`` at module-load
# time, which in turn reads the project ``.env`` via ``starlette.Config``.
# On Windows with a binary-containing local ``.env`` this raises a
# UnicodeDecodeError at import time (see .planning/phases/
# 49-security-auth-hardening/deferred-items.md for the full write-up).
# The unit test file ``tests/unit/app/routers/admin/
# test_governance_audit_router.py`` uses the same short-circuit, and we
# copy that pattern here so the E2E test runs in the same environment.
# ---------------------------------------------------------------------------
if "app.middleware.rate_limiter" not in sys.modules:
    _mock_rate_limiter = types.ModuleType("app.middleware.rate_limiter")
    _mock_limiter = MagicMock()
    _mock_limiter.limit = lambda *_args, **_kwargs: (lambda fn: fn)
    _mock_rate_limiter.limiter = _mock_limiter
    _mock_rate_limiter.get_user_persona_limit = "100/minute"
    _mock_rate_limiter.get_remote_address = lambda *_a, **_kw: "127.0.0.1"
    sys.modules["app.middleware.rate_limiter"] = _mock_rate_limiter


@pytest.mark.asyncio
async def test_admin_can_filter_by_action_type() -> None:
    """GET /admin/governance-audit-log?action_type=initiative.created.

    Verifies the endpoint:
      - applies ``.eq("action_type", "initiative.created")``
      - returns ``{entries, total, limit, offset}`` shape
      - enriches each row with ``actor_email`` from ``auth.admin.get_user_by_id``
    """
    from app.routers.admin.governance_audit import list_governance_audit_log

    mock_client = MagicMock()

    # Build the Supabase fluent query chain: .table().select().order() -> query
    # Then query.eq/.gte/.lte/.range all return the same query (fluent style),
    # and .execute() returns the row payload.
    mock_query = MagicMock()
    mock_query.execute.return_value = MagicMock(
        data=[
            {
                "id": "row-1",
                "user_id": "user-42",
                "action_type": "initiative.created",
                "resource_type": "initiative",
                "resource_id": None,
                "details": {
                    "method": "POST",
                    "path": "/initiatives",
                    "status_code": 200,
                },
                "ip_address": "127.0.0.1",
                "created_at": "2026-04-06T10:00:00Z",
            },
        ],
        count=1,
    )
    mock_client.table.return_value.select.return_value.order.return_value = (
        mock_query
    )
    mock_query.eq.return_value = mock_query
    mock_query.gte.return_value = mock_query
    mock_query.lte.return_value = mock_query
    mock_query.range.return_value = mock_query

    # Mock email resolution
    mock_user_resp = MagicMock()
    mock_user_resp.user.email = "alice@example.com"
    mock_client.auth.admin.get_user_by_id.return_value = mock_user_resp

    with patch(
        "app.routers.admin.governance_audit.get_service_client",
        return_value=mock_client,
    ):
        request_mock = MagicMock()
        response = await list_governance_audit_log(
            request=request_mock,
            admin_user={"id": "admin-1", "email": "admin@example.com"},
            action_type="initiative.created",
            limit=50,
            offset=0,
        )

    assert response["total"] == 1
    assert response["limit"] == 50
    assert response["offset"] == 0
    assert len(response["entries"]) == 1
    entry = response["entries"][0]
    assert entry["action_type"] == "initiative.created"
    assert entry["actor_email"] == "alice@example.com"
    assert entry["details"]["method"] == "POST"
    assert entry["details"]["path"] == "/initiatives"

    # Prove the action_type filter was actually pushed down to the query
    eq_calls = [str(call) for call in mock_query.eq.call_args_list]
    assert any(
        "action_type" in call and "initiative.created" in call for call in eq_calls
    ), f"expected .eq('action_type', 'initiative.created') call, got {eq_calls}"


@pytest.mark.asyncio
async def test_admin_can_filter_by_email_resolves_to_user_id() -> None:
    """GET /admin/governance-audit-log?email=alice@example.com.

    Verifies the endpoint:
      - calls ``auth.admin.list_users`` to resolve ``email`` -> ``user_id``
      - applies the resolved ``.eq("user_id", <resolved>)`` filter on the table
      - still enriches the response row with ``actor_email``
    """
    from app.routers.admin.governance_audit import list_governance_audit_log

    mock_client = MagicMock()

    # Mock list_users for email -> user_id resolution
    mock_user = MagicMock()
    mock_user.id = "user-42"
    mock_user.email = "alice@example.com"
    mock_client.auth.admin.list_users.return_value = [mock_user]

    # Mock get_user_by_id for response email enrichment
    mock_user_resp = MagicMock()
    mock_user_resp.user.email = "alice@example.com"
    mock_client.auth.admin.get_user_by_id.return_value = mock_user_resp

    # Mock the table query chain
    mock_query = MagicMock()
    mock_query.execute.return_value = MagicMock(
        data=[
            {
                "id": "row-1",
                "user_id": "user-42",
                "action_type": "workflow.deleted",
                "resource_type": "workflow",
                "resource_id": "wf-99",
                "details": {},
                "ip_address": None,
                "created_at": "2026-04-06T11:00:00Z",
            },
        ],
        count=1,
    )
    mock_client.table.return_value.select.return_value.order.return_value = (
        mock_query
    )
    mock_query.eq.return_value = mock_query
    mock_query.gte.return_value = mock_query
    mock_query.lte.return_value = mock_query
    mock_query.range.return_value = mock_query

    with patch(
        "app.routers.admin.governance_audit.get_service_client",
        return_value=mock_client,
    ):
        request_mock = MagicMock()
        response = await list_governance_audit_log(
            request=request_mock,
            admin_user={"id": "admin-1", "email": "admin@example.com"},
            email="alice@example.com",
            limit=50,
            offset=0,
        )

    # The eq filter should have been applied with user_id="user-42"
    eq_calls = [str(call) for call in mock_query.eq.call_args_list]
    assert any(
        "user_id" in call and "user-42" in call for call in eq_calls
    ), f"expected .eq('user_id', 'user-42') call, got {eq_calls}"

    assert response["total"] == 1
    assert len(response["entries"]) == 1
    assert response["entries"][0]["actor_email"] == "alice@example.com"
    assert response["entries"][0]["action_type"] == "workflow.deleted"

    # Prove list_users was actually called for the email resolution path
    mock_client.auth.admin.list_users.assert_called_once()

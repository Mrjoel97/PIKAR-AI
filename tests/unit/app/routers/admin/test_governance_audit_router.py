# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the governance audit log admin router.

Covers AUTH-05 (Phase 49 Plan 05): the admin-facing read endpoint
``GET /admin/governance-audit-log`` that surfaces rows written to
``governance_audit_log`` by ``AuditLogMiddleware`` (Phase 49 Plan 04).

Test coverage:
    * limit/offset validation (400 on out-of-range values)
    * no-filter happy path returns ``{entries, total, limit, offset}``
    * ``action_type`` filter applies ``.eq('action_type', ...)``
    * ``user_id`` filter applies ``.eq('user_id', ...)``
    * ``email`` filter resolves to user_id via ``auth.admin.list_users``
    * unknown email returns empty result set without querying the table
    * ``start_date`` applies ``.gte('created_at', ...)``
    * ``end_date`` applies ``.lte('created_at', ...)``
    * ``start_date`` + ``end_date`` apply both range filters
    * ``limit`` caps the range window
    * each returned entry has an ``actor_email`` resolved from ``user_id``
    * email resolution falls back to the raw UUID on auth-API failure
    * ``GET /admin/governance-audit-log/actions`` returns a sorted distinct list

Follows the Windows-safe import-stub pattern used by
``tests/unit/app/routers/test_teams_rbac_router.py`` to short-circuit
``app.middleware.rate_limiter`` before the router module is imported.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub heavy / Windows-flaky modules BEFORE importing the router under test.
# The real rate limiter module imports the Supabase client at module-load
# time and reads os.environ, which makes it brittle on Windows test runs.
# ---------------------------------------------------------------------------
if "app.middleware.rate_limiter" not in sys.modules:
    _mock_rate_limiter = types.ModuleType("app.middleware.rate_limiter")
    _mock_limiter = MagicMock()
    _mock_limiter.limit = lambda *_args, **_kwargs: (lambda fn: fn)
    _mock_rate_limiter.limiter = _mock_limiter
    # Some sibling admin routers (e.g. knowledge.py, users.py) import
    # get_user_persona_limit / get_remote_address from this module at import
    # time; provide benign stubs so `from app.routers.admin import ...` works.
    _mock_rate_limiter.get_user_persona_limit = "100/minute"
    _mock_rate_limiter.get_remote_address = lambda *_a, **_kw: "127.0.0.1"
    sys.modules["app.middleware.rate_limiter"] = _mock_rate_limiter


_ROUTER_MODULE = "app.routers.admin.governance_audit"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_auth_response(email: str) -> MagicMock:
    """Build a mock ``auth.admin.get_user_by_id`` response."""
    user_mock = MagicMock()
    user_mock.email = email
    response = MagicMock()
    response.user = user_mock
    return response


def _build_query_chain(data: list[dict], count: int) -> MagicMock:
    """Build a chainable Supabase query mock.

    Returns a query mock where every chain method (eq/gte/lte/range/order)
    returns the same mock, and ``.execute()`` returns a MagicMock with
    ``.data`` and ``.count`` attributes.
    """
    query = MagicMock()
    query.execute.return_value = MagicMock(data=data, count=count)
    query.eq.return_value = query
    query.gte.return_value = query
    query.lte.return_value = query
    query.range.return_value = query
    query.order.return_value = query
    query.limit.return_value = query
    query.select.return_value = query
    return query


def _install_table_query(client: MagicMock, query: MagicMock) -> None:
    """Wire ``client.table(...).select(...).order(...)`` to return *query*."""
    client.table.return_value = query


def _admin_user() -> dict:
    return {
        "id": "admin-uuid",
        "email": "admin@test.com",
        "role": "authenticated",
        "metadata": {},
        "admin_source": "env_allowlist",
        "admin_role": "super_admin",
    }


# ---------------------------------------------------------------------------
# limit / offset validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_limit_above_max_returns_400():
    """GET with limit=300 raises HTTPException 400."""
    from fastapi import HTTPException

    from app.routers.admin.governance_audit import list_governance_audit_log

    with pytest.raises(HTTPException) as excinfo:
        await list_governance_audit_log(
            request=MagicMock(),
            admin_user=_admin_user(),
            limit=300,
            offset=0,
        )

    assert excinfo.value.status_code == 400
    assert "limit" in excinfo.value.detail.lower()


@pytest.mark.asyncio
async def test_offset_negative_returns_400():
    """GET with offset=-1 raises HTTPException 400."""
    from fastapi import HTTPException

    from app.routers.admin.governance_audit import list_governance_audit_log

    with pytest.raises(HTTPException) as excinfo:
        await list_governance_audit_log(
            request=MagicMock(),
            admin_user=_admin_user(),
            limit=50,
            offset=-1,
        )

    assert excinfo.value.status_code == 400
    assert "offset" in excinfo.value.detail.lower()


# ---------------------------------------------------------------------------
# No-filter happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_filters_returns_paginated_envelope():
    """No filters -> returns {entries, total, limit, offset} envelope."""
    from app.routers.admin.governance_audit import list_governance_audit_log

    client = MagicMock()
    query = _build_query_chain(
        data=[
            {
                "id": "row-1",
                "user_id": "user-42",
                "action_type": "initiative.created",
                "resource_type": "initiative",
                "resource_id": None,
                "details": {"method": "POST", "path": "/initiatives", "status_code": 200},
                "ip_address": "127.0.0.1",
                "created_at": "2026-04-06T10:00:00Z",
            }
        ],
        count=1,
    )
    _install_table_query(client, query)
    client.auth.admin.get_user_by_id.return_value = _make_auth_response(
        "alice@example.com"
    )

    with patch(f"{_ROUTER_MODULE}.get_service_client", return_value=client):
        response = await list_governance_audit_log(
            request=MagicMock(),
            admin_user=_admin_user(),
            limit=50,
            offset=0,
        )

    assert response["total"] == 1
    assert response["limit"] == 50
    assert response["offset"] == 0
    assert len(response["entries"]) == 1
    assert response["entries"][0]["actor_email"] == "alice@example.com"


# ---------------------------------------------------------------------------
# Filter tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_action_type_filter_applies_eq():
    """action_type=initiative.created adds .eq('action_type', ...)."""
    from app.routers.admin.governance_audit import list_governance_audit_log

    client = MagicMock()
    query = _build_query_chain(data=[], count=0)
    _install_table_query(client, query)

    with patch(f"{_ROUTER_MODULE}.get_service_client", return_value=client):
        await list_governance_audit_log(
            request=MagicMock(),
            admin_user=_admin_user(),
            action_type="initiative.created",
            limit=50,
            offset=0,
        )

    eq_calls = [call.args for call in query.eq.call_args_list]
    assert ("action_type", "initiative.created") in eq_calls


@pytest.mark.asyncio
async def test_user_id_filter_applies_eq():
    """user_id=<uuid> adds .eq('user_id', ...)."""
    from app.routers.admin.governance_audit import list_governance_audit_log

    client = MagicMock()
    query = _build_query_chain(data=[], count=0)
    _install_table_query(client, query)

    with patch(f"{_ROUTER_MODULE}.get_service_client", return_value=client):
        await list_governance_audit_log(
            request=MagicMock(),
            admin_user=_admin_user(),
            user_id="user-42",
            limit=50,
            offset=0,
        )

    eq_calls = [call.args for call in query.eq.call_args_list]
    assert ("user_id", "user-42") in eq_calls


@pytest.mark.asyncio
async def test_email_filter_resolves_to_user_id_via_list_users():
    """email=alice@example.com resolves to user_id and filters on it."""
    from app.routers.admin.governance_audit import list_governance_audit_log

    client = MagicMock()
    query = _build_query_chain(
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
            }
        ],
        count=1,
    )
    _install_table_query(client, query)

    # Mock auth.admin.list_users -> [User(id='user-42', email='alice@example.com')]
    alice = MagicMock()
    alice.id = "user-42"
    alice.email = "alice@example.com"
    client.auth.admin.list_users.return_value = [alice]

    # Email enrichment lookup for the returned row
    client.auth.admin.get_user_by_id.return_value = _make_auth_response(
        "alice@example.com"
    )

    with patch(f"{_ROUTER_MODULE}.get_service_client", return_value=client):
        response = await list_governance_audit_log(
            request=MagicMock(),
            admin_user=_admin_user(),
            email="alice@example.com",
            limit=50,
            offset=0,
        )

    # Verify .eq('user_id', 'user-42') was called (case-insensitive email match)
    eq_calls = [call.args for call in query.eq.call_args_list]
    assert ("user_id", "user-42") in eq_calls
    assert response["total"] == 1
    assert response["entries"][0]["actor_email"] == "alice@example.com"


@pytest.mark.asyncio
async def test_email_filter_unknown_email_returns_empty():
    """email=ghost@example.com with no matching user returns empty envelope."""
    from app.routers.admin.governance_audit import list_governance_audit_log

    client = MagicMock()
    # list_users returns empty -> no match
    client.auth.admin.list_users.return_value = []

    with patch(f"{_ROUTER_MODULE}.get_service_client", return_value=client):
        response = await list_governance_audit_log(
            request=MagicMock(),
            admin_user=_admin_user(),
            email="ghost@example.com",
            limit=50,
            offset=0,
        )

    assert response == {"entries": [], "total": 0, "limit": 50, "offset": 0}
    # The table query should never have been reached
    client.table.assert_not_called()


@pytest.mark.asyncio
async def test_start_date_filter_applies_gte():
    """start_date=2026-04-01 adds .gte('created_at', ...)."""
    from app.routers.admin.governance_audit import list_governance_audit_log

    client = MagicMock()
    query = _build_query_chain(data=[], count=0)
    _install_table_query(client, query)

    with patch(f"{_ROUTER_MODULE}.get_service_client", return_value=client):
        await list_governance_audit_log(
            request=MagicMock(),
            admin_user=_admin_user(),
            start_date="2026-04-01",
            limit=50,
            offset=0,
        )

    gte_calls = [call.args for call in query.gte.call_args_list]
    assert ("created_at", "2026-04-01") in gte_calls


@pytest.mark.asyncio
async def test_end_date_filter_applies_lte():
    """end_date=2026-04-30 adds .lte('created_at', ...)."""
    from app.routers.admin.governance_audit import list_governance_audit_log

    client = MagicMock()
    query = _build_query_chain(data=[], count=0)
    _install_table_query(client, query)

    with patch(f"{_ROUTER_MODULE}.get_service_client", return_value=client):
        await list_governance_audit_log(
            request=MagicMock(),
            admin_user=_admin_user(),
            end_date="2026-04-30",
            limit=50,
            offset=0,
        )

    lte_calls = [call.args for call in query.lte.call_args_list]
    assert ("created_at", "2026-04-30") in lte_calls


@pytest.mark.asyncio
async def test_date_range_applies_both_gte_and_lte():
    """start_date+end_date applies both .gte and .lte filters."""
    from app.routers.admin.governance_audit import list_governance_audit_log

    client = MagicMock()
    query = _build_query_chain(data=[], count=0)
    _install_table_query(client, query)

    with patch(f"{_ROUTER_MODULE}.get_service_client", return_value=client):
        await list_governance_audit_log(
            request=MagicMock(),
            admin_user=_admin_user(),
            start_date="2026-04-01",
            end_date="2026-04-30",
            limit=50,
            offset=0,
        )

    gte_calls = [call.args for call in query.gte.call_args_list]
    lte_calls = [call.args for call in query.lte.call_args_list]
    assert ("created_at", "2026-04-01") in gte_calls
    assert ("created_at", "2026-04-30") in lte_calls


@pytest.mark.asyncio
async def test_limit_controls_range_window():
    """limit=10 calls .range(offset, offset+limit-1) = .range(0, 9)."""
    from app.routers.admin.governance_audit import list_governance_audit_log

    client = MagicMock()
    query = _build_query_chain(data=[], count=0)
    _install_table_query(client, query)

    with patch(f"{_ROUTER_MODULE}.get_service_client", return_value=client):
        await list_governance_audit_log(
            request=MagicMock(),
            admin_user=_admin_user(),
            limit=10,
            offset=0,
        )

    range_calls = [call.args for call in query.range.call_args_list]
    assert (0, 9) in range_calls


# ---------------------------------------------------------------------------
# actor_email resolution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_entries_are_annotated_with_actor_email():
    """Each returned row has actor_email resolved from user_id."""
    from app.routers.admin.governance_audit import list_governance_audit_log

    client = MagicMock()
    query = _build_query_chain(
        data=[
            {
                "id": "row-1",
                "user_id": "uuid-alice",
                "action_type": "initiative.created",
                "resource_type": "initiative",
                "resource_id": None,
                "details": {},
                "ip_address": None,
                "created_at": "2026-04-06T10:00:00Z",
            },
            {
                "id": "row-2",
                "user_id": "uuid-bob",
                "action_type": "workflow.updated",
                "resource_type": "workflow",
                "resource_id": "wf-1",
                "details": {},
                "ip_address": None,
                "created_at": "2026-04-06T10:01:00Z",
            },
        ],
        count=2,
    )
    _install_table_query(client, query)

    def _lookup(uid: str) -> MagicMock:
        return _make_auth_response(f"{uid}@example.com")

    client.auth.admin.get_user_by_id.side_effect = _lookup

    with patch(f"{_ROUTER_MODULE}.get_service_client", return_value=client):
        response = await list_governance_audit_log(
            request=MagicMock(),
            admin_user=_admin_user(),
            limit=50,
            offset=0,
        )

    actor_emails = {row["actor_email"] for row in response["entries"]}
    assert actor_emails == {"uuid-alice@example.com", "uuid-bob@example.com"}


@pytest.mark.asyncio
async def test_actor_email_falls_back_to_uuid_on_auth_error():
    """When auth.admin.get_user_by_id raises, actor_email falls back to raw UUID."""
    from app.routers.admin.governance_audit import list_governance_audit_log

    client = MagicMock()
    query = _build_query_chain(
        data=[
            {
                "id": "row-1",
                "user_id": "uuid-ghost",
                "action_type": "initiative.created",
                "resource_type": "initiative",
                "resource_id": None,
                "details": {},
                "ip_address": None,
                "created_at": "2026-04-06T10:00:00Z",
            }
        ],
        count=1,
    )
    _install_table_query(client, query)
    client.auth.admin.get_user_by_id.side_effect = Exception("auth API down")

    with patch(f"{_ROUTER_MODULE}.get_service_client", return_value=client):
        response = await list_governance_audit_log(
            request=MagicMock(),
            admin_user=_admin_user(),
            limit=50,
            offset=0,
        )

    assert response["entries"][0]["actor_email"] == "uuid-ghost"


# ---------------------------------------------------------------------------
# /admin/governance-audit-log/actions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_distinct_actions_returns_sorted_list():
    """GET /admin/governance-audit-log/actions returns sorted distinct list."""
    from app.routers.admin.governance_audit import list_distinct_actions

    client = MagicMock()
    query = MagicMock()
    query.execute.return_value = MagicMock(
        data=[
            {"action_type": "workflow.deleted"},
            {"action_type": "initiative.created"},
            {"action_type": "workflow.deleted"},  # duplicate
            {"action_type": "initiative.created"},  # duplicate
            {"action_type": "content.updated"},
        ]
    )
    query.limit.return_value = query
    client.table.return_value.select.return_value = query

    with patch(f"{_ROUTER_MODULE}.get_service_client", return_value=client):
        response = await list_distinct_actions(
            request=MagicMock(),
            admin_user=_admin_user(),
        )

    assert response["actions"] == [
        "content.updated",
        "initiative.created",
        "workflow.deleted",
    ]

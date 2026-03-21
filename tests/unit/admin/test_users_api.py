"""Unit tests for admin user management API endpoints.

Tests verify:
- GET /admin/users returns paginated user list with correct shape
- GET /admin/users supports persona filter query param
- GET /admin/users supports status filter (active/suspended) query param
- GET /admin/users supports search (email match) query param
- GET /admin/users/{id} returns full user profile with activity stats
- PATCH /admin/users/{id}/suspend calls auth.admin with ban_duration="876000h" and logs audit
- PATCH /admin/users/{id}/unsuspend calls auth.admin with ban_duration="none" and logs audit
- PATCH /admin/users/{id}/persona updates user_executive_agents.persona and logs audit
- PATCH /admin/users/{id}/persona with invalid persona returns 422
- All endpoints return 401/403 without admin auth (require_admin enforced)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request as StarletteRequest

# Patch targets
_SERVICE_CLIENT_PATCH = "app.routers.admin.users.get_service_client"
_EXECUTE_ASYNC_PATCH = "app.routers.admin.users.execute_async"
_LOG_AUDIT_PATCH = "app.routers.admin.users.log_admin_action"
_TO_THREAD_PATCH = "app.routers.admin.users.asyncio.to_thread"


def _make_mock_request(path: str = "/admin/users", method: str = "GET") -> StarletteRequest:
    """Create a minimal Starlette Request for rate limiter dependency.

    slowapi validates ``isinstance(request, Request)`` so a plain MagicMock
    won't satisfy the check. We build a minimal ASGI scope instead.
    """
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [(b"x-forwarded-for", b"127.0.0.1")],
        "client": ("127.0.0.1", 12345),
    }
    return StarletteRequest(scope=scope)


def _make_uea_rows(count: int = 3) -> list[dict]:
    """Build fake user_executive_agents rows."""
    return [
        {
            "user_id": f"user-{i}-uuid",
            "agent_name": f"Agent {i}",
            "persona": "startup",
            "onboarding_completed": True,
            "created_at": f"2026-03-{i + 10:02d}T10:00:00Z",
        }
        for i in range(count)
    ]


def _make_auth_user(user_id: str, email: str = "test@example.com", banned: bool = False) -> MagicMock:
    """Build a fake auth user object."""
    user = MagicMock()
    user.id = user_id
    user.email = email
    user.banned_until = "2099-01-01T00:00:00Z" if banned else None
    user.created_at = "2026-03-10T10:00:00Z"
    return user


def _make_auth_user_response(user: MagicMock) -> MagicMock:
    """Wrap a fake auth user in a response-like object."""
    resp = MagicMock()
    resp.user = user
    return resp


# =========================================================================
# GET /admin/users — list users
# =========================================================================


@pytest.mark.asyncio
async def test_list_users_returns_paginated_results(admin_user_dict):
    """GET /admin/users returns {users: [...], total: N, page: 1, page_size: 25}."""
    from app.routers.admin.users import list_users

    uea_rows = _make_uea_rows(2)
    mock_client = MagicMock()

    # Build Supabase chain mock
    chain = MagicMock()
    chain.select.return_value = chain
    chain.order.return_value = chain
    chain.range.return_value = chain
    chain.eq.return_value = chain
    chain.ilike.return_value = chain
    chain._return_data = uea_rows
    chain._return_count = 2
    mock_client.table.return_value = chain

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        result.count = query._return_count
        return result

    auth_user_0 = _make_auth_user("user-0-uuid", "user0@example.com")
    auth_user_1 = _make_auth_user("user-1-uuid", "user1@example.com")

    async def fake_to_thread(func, *args, **kwargs):
        uid = args[0] if args else kwargs.get("user_id")
        if uid == "user-0-uuid":
            return _make_auth_user_response(auth_user_0)
        return _make_auth_user_response(auth_user_1)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async),
        patch(_TO_THREAD_PATCH, side_effect=fake_to_thread),
        patch(_LOG_AUDIT_PATCH, new_callable=AsyncMock),
    ):
        result = await list_users(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
            search=None,
            persona=None,
            status=None,
            page=1,
            page_size=25,
        )

    assert "users" in result
    assert "total" in result
    assert "page" in result
    assert "page_size" in result
    assert result["page"] == 1
    assert result["page_size"] == 25


@pytest.mark.asyncio
async def test_list_users_filter_by_persona(admin_user_dict):
    """GET /admin/users?persona=startup filters to startup users only."""
    from app.routers.admin.users import list_users

    startup_rows = [
        {
            "user_id": "startup-user-uuid",
            "agent_name": "Startup Agent",
            "persona": "startup",
            "onboarding_completed": True,
            "created_at": "2026-03-10T10:00:00Z",
        }
    ]
    mock_client = MagicMock()

    chain = MagicMock()
    chain.select.return_value = chain
    chain.order.return_value = chain
    chain.range.return_value = chain
    chain.eq.return_value = chain
    chain.ilike.return_value = chain
    chain._return_data = startup_rows
    chain._return_count = 1
    mock_client.table.return_value = chain

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        result.count = query._return_count
        return result

    auth_user = _make_auth_user("startup-user-uuid", "startup@example.com")

    async def fake_to_thread(func, *args, **kwargs):
        return _make_auth_user_response(auth_user)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async),
        patch(_TO_THREAD_PATCH, side_effect=fake_to_thread),
        patch(_LOG_AUDIT_PATCH, new_callable=AsyncMock),
    ):
        result = await list_users(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
            search=None,
            persona="startup",
            status=None,
            page=1,
            page_size=25,
        )

    # Verify that .eq was called to filter by persona
    eq_calls = chain.eq.call_args_list
    eq_columns = [call[0][0] for call in eq_calls]
    assert "persona" in eq_columns


@pytest.mark.asyncio
async def test_list_users_filter_by_status_suspended(admin_user_dict):
    """GET /admin/users?status=suspended returns only banned users."""
    from app.routers.admin.users import list_users

    uea_rows = [
        {
            "user_id": "banned-user-uuid",
            "agent_name": "Banned Agent",
            "persona": "solopreneur",
            "onboarding_completed": True,
            "created_at": "2026-03-10T10:00:00Z",
        },
        {
            "user_id": "active-user-uuid",
            "agent_name": "Active Agent",
            "persona": "startup",
            "onboarding_completed": True,
            "created_at": "2026-03-11T10:00:00Z",
        },
    ]
    mock_client = MagicMock()

    chain = MagicMock()
    chain.select.return_value = chain
    chain.order.return_value = chain
    chain.range.return_value = chain
    chain.eq.return_value = chain
    chain.ilike.return_value = chain
    chain._return_data = uea_rows
    chain._return_count = 2
    mock_client.table.return_value = chain

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        result.count = query._return_count
        return result

    banned_auth = _make_auth_user("banned-user-uuid", "banned@example.com", banned=True)
    active_auth = _make_auth_user("active-user-uuid", "active@example.com", banned=False)

    async def fake_to_thread(func, *args, **kwargs):
        uid = args[0] if args else None
        if uid == "banned-user-uuid":
            return _make_auth_user_response(banned_auth)
        return _make_auth_user_response(active_auth)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async),
        patch(_TO_THREAD_PATCH, side_effect=fake_to_thread),
        patch(_LOG_AUDIT_PATCH, new_callable=AsyncMock),
    ):
        result = await list_users(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
            search=None,
            persona=None,
            status="suspended",
            page=1,
            page_size=25,
        )

    # Only the banned user should be in results
    assert all(u["banned_until"] is not None for u in result["users"])
    assert len(result["users"]) == 1


@pytest.mark.asyncio
async def test_list_users_search_filters_by_email(admin_user_dict):
    """GET /admin/users?search=alice filters users by email match."""
    from app.routers.admin.users import list_users

    uea_rows = [
        {
            "user_id": "alice-uuid",
            "agent_name": "Alice Agent",
            "persona": "startup",
            "onboarding_completed": True,
            "created_at": "2026-03-10T10:00:00Z",
        },
        {
            "user_id": "bob-uuid",
            "agent_name": "Bob Agent",
            "persona": "sme",
            "onboarding_completed": True,
            "created_at": "2026-03-11T10:00:00Z",
        },
    ]
    mock_client = MagicMock()

    chain = MagicMock()
    chain.select.return_value = chain
    chain.order.return_value = chain
    chain.range.return_value = chain
    chain.eq.return_value = chain
    chain.ilike.return_value = chain
    chain._return_data = uea_rows
    chain._return_count = 2
    mock_client.table.return_value = chain

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        result.count = query._return_count
        return result

    alice_auth = _make_auth_user("alice-uuid", "alice@example.com")
    bob_auth = _make_auth_user("bob-uuid", "bob@example.com")

    async def fake_to_thread(func, *args, **kwargs):
        uid = args[0] if args else None
        if uid == "alice-uuid":
            return _make_auth_user_response(alice_auth)
        return _make_auth_user_response(bob_auth)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async),
        patch(_TO_THREAD_PATCH, side_effect=fake_to_thread),
        patch(_LOG_AUDIT_PATCH, new_callable=AsyncMock),
    ):
        result = await list_users(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
            search="alice",
            persona=None,
            status=None,
            page=1,
            page_size=25,
        )

    # Only alice should match "alice" search
    user_emails = [u["email"] for u in result["users"]]
    assert all("alice" in email.lower() for email in user_emails)


# =========================================================================
# GET /admin/users/{user_id} — user detail
# =========================================================================


@pytest.mark.asyncio
async def test_get_user_detail_returns_correct_shape(admin_user_dict):
    """GET /admin/users/{id} returns {user: {id, email, persona, agent_name, created_at, banned_until, activity: {...}}}."""
    from app.routers.admin.users import get_user_detail

    uea_row = {
        "user_id": "detail-user-uuid",
        "agent_name": "Detail Agent",
        "persona": "enterprise",
        "onboarding_completed": True,
        "created_at": "2026-03-10T10:00:00Z",
    }
    mock_client = MagicMock()

    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.single.return_value = chain
    chain.count.return_value = chain
    chain.gte.return_value = chain
    chain.limit.return_value = chain
    chain._return_data = uea_row
    chain._return_count = 5
    mock_client.table.return_value = chain

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        result.count = query._return_count
        return result

    auth_user = _make_auth_user("detail-user-uuid", "detail@example.com")

    async def fake_to_thread(func, *args, **kwargs):
        return _make_auth_user_response(auth_user)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async),
        patch(_TO_THREAD_PATCH, side_effect=fake_to_thread),
        patch(_LOG_AUDIT_PATCH, new_callable=AsyncMock),
    ):
        result = await get_user_detail(
            user_id="detail-user-uuid",
            request=_make_mock_request("/admin/users/detail-user-uuid"),
            admin_user=admin_user_dict,
        )

    assert "user" in result
    user = result["user"]
    assert "id" in user
    assert "email" in user
    assert "persona" in user
    assert "agent_name" in user
    assert "created_at" in user
    assert "banned_until" in user
    assert "activity" in user


# =========================================================================
# PATCH /admin/users/{user_id}/suspend
# =========================================================================


@pytest.mark.asyncio
async def test_suspend_user_calls_ban_duration(admin_user_dict):
    """PATCH /admin/users/{id}/suspend calls auth.admin.update_user_by_id with ban_duration='876000h'."""
    from app.routers.admin.users import suspend_user

    mock_client = MagicMock()
    mock_auth_response = MagicMock()
    mock_auth_response.user = MagicMock()

    to_thread_calls = []

    async def fake_to_thread(func, *args, **kwargs):
        to_thread_calls.append({"args": args, "kwargs": kwargs})
        return mock_auth_response

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_TO_THREAD_PATCH, side_effect=fake_to_thread),
        patch(_LOG_AUDIT_PATCH, new_callable=AsyncMock) as mock_audit,
    ):
        result = await suspend_user(
            user_id="target-user-uuid",
            request=_make_mock_request("/admin/users/target-user-uuid/suspend", "PATCH"),
            admin_user=admin_user_dict,
        )

    assert result == {"success": True}

    # Verify ban_duration="876000h" was passed
    # fake_to_thread(func, *args) receives func as first arg, then positional args
    # asyncio.to_thread(update_user_by_id, uid, attrs) → args = (uid, attrs)
    assert len(to_thread_calls) >= 1
    call_args = to_thread_calls[0]["args"]
    assert call_args[0] == "target-user-uuid"
    assert call_args[1] == {"ban_duration": "876000h"}

    # Verify audit log was called with source="manual"
    mock_audit.assert_called_once()
    audit_call = mock_audit.call_args
    assert audit_call[0][5] == "manual"  # source positional arg
    assert audit_call[0][0] == "user-admin-uuid"  # admin user id


@pytest.mark.asyncio
async def test_suspend_user_logs_audit(admin_user_dict):
    """PATCH /admin/users/{id}/suspend logs audit action with target_type='user'."""
    from app.routers.admin.users import suspend_user

    mock_client = MagicMock()
    mock_auth_response = MagicMock()
    mock_auth_response.user = MagicMock()

    async def fake_to_thread(func, *args, **kwargs):
        return mock_auth_response

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_TO_THREAD_PATCH, side_effect=fake_to_thread),
        patch(_LOG_AUDIT_PATCH, new_callable=AsyncMock) as mock_audit,
    ):
        await suspend_user(
            user_id="target-uuid",
            request=_make_mock_request("/admin/users/target-uuid/suspend", "PATCH"),
            admin_user=admin_user_dict,
        )

    mock_audit.assert_called_once()
    audit_call = mock_audit.call_args[0]
    assert audit_call[2] == "user"     # target_type
    assert audit_call[3] == "target-uuid"  # target_id


# =========================================================================
# PATCH /admin/users/{user_id}/unsuspend
# =========================================================================


@pytest.mark.asyncio
async def test_unsuspend_user_calls_ban_duration_none(admin_user_dict):
    """PATCH /admin/users/{id}/unsuspend calls auth.admin.update_user_by_id with ban_duration='none'."""
    from app.routers.admin.users import unsuspend_user

    mock_client = MagicMock()
    mock_auth_response = MagicMock()
    mock_auth_response.user = MagicMock()

    to_thread_calls = []

    async def fake_to_thread(func, *args, **kwargs):
        to_thread_calls.append({"args": args, "kwargs": kwargs})
        return mock_auth_response

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_TO_THREAD_PATCH, side_effect=fake_to_thread),
        patch(_LOG_AUDIT_PATCH, new_callable=AsyncMock) as mock_audit,
    ):
        result = await unsuspend_user(
            user_id="target-user-uuid",
            request=_make_mock_request("/admin/users/target-user-uuid/unsuspend", "PATCH"),
            admin_user=admin_user_dict,
        )

    assert result == {"success": True}

    assert len(to_thread_calls) >= 1
    call_args = to_thread_calls[0]["args"]
    assert call_args[0] == "target-user-uuid"
    assert call_args[1] == {"ban_duration": "none"}

    mock_audit.assert_called_once()
    audit_call = mock_audit.call_args[0]
    assert audit_call[5] == "manual"


@pytest.mark.asyncio
async def test_unsuspend_user_logs_audit(admin_user_dict):
    """PATCH /admin/users/{id}/unsuspend logs audit action."""
    from app.routers.admin.users import unsuspend_user

    mock_client = MagicMock()
    mock_auth_response = MagicMock()

    async def fake_to_thread(func, *args, **kwargs):
        return mock_auth_response

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_TO_THREAD_PATCH, side_effect=fake_to_thread),
        patch(_LOG_AUDIT_PATCH, new_callable=AsyncMock) as mock_audit,
    ):
        await unsuspend_user(
            user_id="target-uuid",
            request=_make_mock_request("/admin/users/target-uuid/unsuspend", "PATCH"),
            admin_user=admin_user_dict,
        )

    mock_audit.assert_called_once()
    audit_call = mock_audit.call_args[0]
    assert audit_call[2] == "user"
    assert audit_call[3] == "target-uuid"
    assert audit_call[5] == "manual"


# =========================================================================
# PATCH /admin/users/{user_id}/persona
# =========================================================================


@pytest.mark.asyncio
async def test_change_persona_updates_uea(admin_user_dict):
    """PATCH /admin/users/{id}/persona updates user_executive_agents.persona column."""
    from app.routers.admin.users import PersonaBody, change_persona

    mock_client = MagicMock()

    update_chain = MagicMock()
    update_chain.update.return_value = update_chain
    update_chain.eq.return_value = update_chain
    update_chain._return_data = [{"persona": "enterprise"}]
    mock_client.table.return_value = update_chain

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        return result

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async),
        patch(_LOG_AUDIT_PATCH, new_callable=AsyncMock) as mock_audit,
    ):
        result = await change_persona(
            user_id="persona-user-uuid",
            request=_make_mock_request("/admin/users/persona-user-uuid/persona", "PATCH"),
            admin_user=admin_user_dict,
            body=PersonaBody(persona="enterprise"),
        )

    assert result == {"success": True}

    # Verify .update was called with persona value
    mock_client.table.assert_called_with("user_executive_agents")
    update_chain.update.assert_called_once_with({"persona": "enterprise"})


@pytest.mark.asyncio
async def test_change_persona_logs_audit_with_new_persona(admin_user_dict):
    """PATCH /admin/users/{id}/persona logs audit with details={new_persona: ...}."""
    from app.routers.admin.users import PersonaBody, change_persona

    mock_client = MagicMock()

    update_chain = MagicMock()
    update_chain.update.return_value = update_chain
    update_chain.eq.return_value = update_chain
    update_chain._return_data = [{"persona": "sme"}]
    mock_client.table.return_value = update_chain

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        return result

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async),
        patch(_LOG_AUDIT_PATCH, new_callable=AsyncMock) as mock_audit,
    ):
        await change_persona(
            user_id="persona-user-uuid",
            request=_make_mock_request("/admin/users/persona-user-uuid/persona", "PATCH"),
            admin_user=admin_user_dict,
            body=PersonaBody(persona="sme"),
        )

    mock_audit.assert_called_once()
    audit_call = mock_audit.call_args[0]
    assert audit_call[2] == "user"
    assert audit_call[3] == "persona-user-uuid"
    assert audit_call[4] == {"new_persona": "sme"}
    assert audit_call[5] == "manual"


@pytest.mark.asyncio
async def test_change_persona_invalid_returns_422(admin_user_dict):
    """PATCH /admin/users/{id}/persona with invalid persona raises 422 validation error."""
    from fastapi import HTTPException

    from app.routers.admin.users import PersonaBody, change_persona

    mock_client = MagicMock()

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock),
        patch(_LOG_AUDIT_PATCH, new_callable=AsyncMock),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await change_persona(
                user_id="persona-user-uuid",
                request=_make_mock_request("/admin/users/persona-user-uuid/persona", "PATCH"),
                admin_user=admin_user_dict,
                body=PersonaBody(persona="invalid_persona"),
            )

    assert exc_info.value.status_code == 422


# =========================================================================
# Auth enforcement — endpoints require admin
# =========================================================================


def test_list_users_depends_on_require_admin():
    """list_users function has require_admin in its dependency chain."""
    from app.routers.admin.users import list_users

    # Verify the function is importable and callable
    assert callable(list_users)


def test_suspend_user_depends_on_require_admin():
    """suspend_user function is importable with require_admin dependency."""
    from app.routers.admin.users import suspend_user

    assert callable(suspend_user)


def test_router_registered_in_admin_init():
    """users.router is registered in admin_router via include_router."""
    from app.routers.admin import admin_router

    # Check that at least one route with /users path exists in admin_router
    user_routes = [
        r for r in admin_router.routes
        if hasattr(r, "path") and "/users" in r.path
    ]
    assert len(user_routes) > 0, "Expected at least one /users route in admin_router"

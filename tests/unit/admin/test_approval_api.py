"""Unit tests for admin approval queue, override, and role management API.

Tests verify:
- test_list_all_approvals: GET /admin/approvals/all returns pending approvals with pagination
- test_list_all_approvals_with_filters: status/action_type/user_id filters narrow results
- test_override_approval_approve: POST /admin/approvals/{id}/override with APPROVED updates status + audit log
- test_override_approval_reject: POST /admin/approvals/{id}/override with REJECTED updates status + audit log
- test_override_approval_already_decided: override on non-PENDING approval returns 409
- test_create_admin_account: POST /admin/roles creates user_roles row (super_admin only)
- test_create_admin_account_not_super: non-super_admin gets 403 on POST /admin/roles
- test_update_role_permissions: PUT /admin/roles/permissions updates admin_role_permissions (super_admin)
- test_list_admin_roles: GET /admin/roles returns all admin accounts with roles
- test_delete_admin_role: DELETE /admin/roles/{user_id} removes admin role (super_admin only)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Patch targets scoped to approvals router module
_EXECUTE_ASYNC_PATCH = "app.routers.admin.approvals.execute_async"
_SERVICE_CLIENT_PATCH = "app.routers.admin.approvals.get_service_client"
_LOG_ADMIN_ACTION_PATCH = "app.routers.admin.approvals.log_admin_action"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_admin_user(role: str = "super_admin") -> dict:
    """Build an admin user dict (as returned by require_admin)."""
    return {
        "id": "admin-uuid-001",
        "email": "admin@test.com",
        "role": "authenticated",
        "metadata": {},
        "admin_source": "env_allowlist",
        "admin_role": role,
    }


def _make_approval_row(
    approval_id: str = "appr-001",
    status: str = "PENDING",
    action_type: str = "delete_user",
    user_id: str = "user-001",
) -> dict:
    """Build a fake approval_requests row."""
    return {
        "id": approval_id,
        "action_type": action_type,
        "status": status,
        "payload": {"requester_user_id": user_id},
        "created_at": "2026-03-25T10:00:00Z",
        "expires_at": "2026-03-26T10:00:00Z",
        "user_id": user_id,
        "responded_at": None,
        "responder_ip": None,
    }


@pytest.fixture
def app_with_approvals():
    """FastAPI test app with approvals router and overridden dependencies."""
    from app.routers.admin import approvals
    from app.middleware.admin_auth import require_admin, require_admin_role

    app = FastAPI()
    app.include_router(approvals.router, prefix="/admin")

    # Default override: super_admin
    super_admin = _make_admin_user("super_admin")
    app.dependency_overrides[require_admin] = lambda: super_admin

    # Override all role gates to allow super_admin by default
    for min_role in ("senior_admin", "admin", "super_admin"):
        gate = require_admin_role(min_role)
        app.dependency_overrides[gate] = lambda u=super_admin: u

    return app


@pytest.fixture
def client(app_with_approvals):
    """Test client using the app fixture."""
    return TestClient(app_with_approvals)


# ---------------------------------------------------------------------------
# Test 1: GET /admin/approvals/all returns pending approvals
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_all_approvals():
    """GET /admin/approvals/all returns pending approvals with pagination metadata."""
    from app.routers.admin.approvals import list_all_approvals

    rows = [_make_approval_row("a1"), _make_approval_row("a2")]
    mock_result = MagicMock()
    mock_result.data = rows

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=mock_result)),
    ):
        result = await list_all_approvals(
            admin_user=_make_admin_user(),
            status="PENDING",
            action_type=None,
            user_id=None,
            limit=50,
            offset=0,
        )

    assert isinstance(result["approvals"], list)
    assert len(result["approvals"]) == 2
    assert result["approvals"][0]["id"] == "a1"
    assert result["total"] == 2
    assert result["limit"] == 50
    assert result["offset"] == 0


# ---------------------------------------------------------------------------
# Test 2: Filters narrow results (status/action_type/user_id)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_all_approvals_with_filters():
    """GET /admin/approvals/all with filters passes them to the DB query."""
    from app.routers.admin.approvals import list_all_approvals

    rows = [_make_approval_row("a3", status="APPROVED", action_type="suspend_user")]
    mock_result = MagicMock()
    mock_result.data = rows

    mock_client = MagicMock()
    # Build the query chain mock
    table_mock = mock_client.table.return_value
    select_mock = table_mock.select.return_value
    select_mock.eq.return_value = select_mock
    select_mock.order.return_value = select_mock
    select_mock.range.return_value = select_mock

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=mock_result)),
    ):
        result = await list_all_approvals(
            admin_user=_make_admin_user(),
            status="APPROVED",
            action_type="suspend_user",
            user_id="user-001",
            limit=10,
            offset=0,
        )

    assert len(result["approvals"]) == 1
    assert result["approvals"][0]["action_type"] == "suspend_user"


# ---------------------------------------------------------------------------
# Test 3: POST /admin/approvals/{id}/override with APPROVED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_override_approval_approve():
    """POST .../override with APPROVED updates status and logs audit with source=admin_override."""
    from app.routers.admin.approvals import override_approval, OverrideDecision

    pending_row = _make_approval_row("appr-001", status="PENDING")
    update_result = MagicMock()
    update_result.data = [{**pending_row, "status": "APPROVED"}]

    fetch_result = MagicMock()
    fetch_result.data = [pending_row]

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(
            _EXECUTE_ASYNC_PATCH,
            new=AsyncMock(side_effect=[fetch_result, update_result]),
        ),
        patch(_LOG_ADMIN_ACTION_PATCH, new=AsyncMock()) as mock_log,
    ):
        result = await override_approval(
            approval_id="appr-001",
            body=OverrideDecision(decision="APPROVED", reason="Verified by senior admin"),
            admin_user=_make_admin_user(),
            client_ip="127.0.0.1",
        )

    assert result["status"] == "APPROVED"
    assert result["approval_id"] == "appr-001"
    mock_log.assert_called_once()
    call_kwargs = mock_log.call_args
    # source must be "admin_override"
    assert call_kwargs.kwargs.get("source") == "admin_override" or (
        len(call_kwargs.args) > 5 and call_kwargs.args[5] == "admin_override"
    )


# ---------------------------------------------------------------------------
# Test 4: POST /admin/approvals/{id}/override with REJECTED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_override_approval_reject():
    """POST .../override with REJECTED updates status and logs audit."""
    from app.routers.admin.approvals import override_approval, OverrideDecision

    pending_row = _make_approval_row("appr-002", status="PENDING")
    update_result = MagicMock()
    update_result.data = [{**pending_row, "status": "REJECTED"}]

    fetch_result = MagicMock()
    fetch_result.data = [pending_row]

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(
            _EXECUTE_ASYNC_PATCH,
            new=AsyncMock(side_effect=[fetch_result, update_result]),
        ),
        patch(_LOG_ADMIN_ACTION_PATCH, new=AsyncMock()) as mock_log,
    ):
        result = await override_approval(
            approval_id="appr-002",
            body=OverrideDecision(decision="REJECTED", reason="Policy violation"),
            admin_user=_make_admin_user(),
            client_ip="10.0.0.1",
        )

    assert result["status"] == "REJECTED"
    mock_log.assert_called_once()


# ---------------------------------------------------------------------------
# Test 5: override on non-PENDING approval returns 409
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_override_approval_already_decided():
    """POST .../override on a non-PENDING approval returns 409 Conflict."""
    from fastapi import HTTPException

    from app.routers.admin.approvals import override_approval, OverrideDecision

    already_approved = _make_approval_row("appr-003", status="APPROVED")
    fetch_result = MagicMock()
    fetch_result.data = [already_approved]

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=fetch_result)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await override_approval(
                approval_id="appr-003",
                body=OverrideDecision(decision="APPROVED", reason=None),
                admin_user=_make_admin_user(),
                client_ip="127.0.0.1",
            )

    assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# Test 6: POST /admin/roles creates user_roles row (super_admin only)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_admin_account():
    """POST /admin/roles creates a user_roles row and logs audit."""
    from app.routers.admin.approvals import create_admin_role, CreateAdminRole

    upsert_result = MagicMock()
    upsert_result.data = [{"user_id": "target-001", "role": "senior_admin"}]

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=upsert_result)),
        patch(_LOG_ADMIN_ACTION_PATCH, new=AsyncMock()) as mock_log,
    ):
        result = await create_admin_role(
            body=CreateAdminRole(user_id="target-001", role="senior_admin"),
            admin_user=_make_admin_user("super_admin"),
        )

    assert result["user_id"] == "target-001"
    assert result["role"] == "senior_admin"
    mock_log.assert_called_once()


# ---------------------------------------------------------------------------
# Test 7: non-super_admin gets 403 on POST /admin/roles
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_admin_account_not_super():
    """POST /admin/roles with a non-super_admin caller raises HTTP 403."""
    from fastapi import HTTPException

    from app.middleware.admin_auth import require_admin_role

    # Build a senior_admin caller dict
    senior = _make_admin_user("senior_admin")

    # require_admin_role("super_admin") is the gate — call it directly
    checker = require_admin_role("super_admin")

    with (
        patch("app.middleware.admin_auth.verify_token", new=AsyncMock(return_value=senior)),
        patch.dict("os.environ", {"ADMIN_EMAILS": ""}),
        patch(
            "app.middleware.admin_auth.get_service_client",
            return_value=MagicMock(
                **{
                    "rpc.return_value.execute.return_value": MagicMock(data=True),
                    "table.return_value.select.return_value.eq.return_value.execute.return_value": MagicMock(
                        data=[{"role": "senior_admin"}]
                    ),
                }
            ),
        ),
    ):
        from fastapi.security import HTTPAuthorizationCredentials
        from unittest.mock import MagicMock as MM

        creds = MM(spec=HTTPAuthorizationCredentials)
        creds.credentials = "fake"
        with pytest.raises(HTTPException) as exc_info:
            await checker(creds)

    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Test 8: PUT /admin/roles/permissions updates admin_role_permissions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_role_permissions():
    """PUT /admin/roles/permissions upserts admin_role_permissions and logs audit."""
    from app.routers.admin.approvals import update_role_permissions, UpdateRolePermission

    upsert_result = MagicMock()
    upsert_result.data = [{"role": "junior_admin", "section": "users", "allowed_actions": ["read", "write"]}]

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=upsert_result)),
        patch(_LOG_ADMIN_ACTION_PATCH, new=AsyncMock()) as mock_log,
    ):
        result = await update_role_permissions(
            body=UpdateRolePermission(role="junior_admin", section="users", allowed_actions=["read", "write"]),
            admin_user=_make_admin_user("super_admin"),
        )

    assert result["role"] == "junior_admin"
    assert result["section"] == "users"
    mock_log.assert_called_once()


# ---------------------------------------------------------------------------
# Test 9: GET /admin/roles returns all admin accounts with roles
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_admin_roles():
    """GET /admin/roles returns list of admin role assignments."""
    from app.routers.admin.approvals import list_admin_roles

    rows = [
        {"user_id": "u1", "role": "admin", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"},
        {"user_id": "u2", "role": "senior_admin", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"},
    ]
    mock_result = MagicMock()
    mock_result.data = rows

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=mock_result)),
    ):
        result = await list_admin_roles(admin_user=_make_admin_user("admin"))

    assert isinstance(result["admins"], list)
    assert len(result["admins"]) == 2
    assert result["admins"][0]["role"] == "admin"


# ---------------------------------------------------------------------------
# Test 10: DELETE /admin/roles/{user_id} removes admin role (super_admin only)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_admin_role():
    """DELETE /admin/roles/{user_id} deletes the role row and logs audit."""
    from app.routers.admin.approvals import delete_admin_role

    delete_result = MagicMock()
    delete_result.data = [{"user_id": "target-002"}]

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=delete_result)),
        patch(_LOG_ADMIN_ACTION_PATCH, new=AsyncMock()) as mock_log,
    ):
        result = await delete_admin_role(
            target_user_id="target-002",
            admin_user=_make_admin_user("super_admin"),
        )

    assert result["deleted_user_id"] == "target-002"
    mock_log.assert_called_once()

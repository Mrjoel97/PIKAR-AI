"""Unit tests for admin integrations API endpoints.

Tests verify:
- test_upsert_integration_encrypts_key: PUT stores Fernet-encrypted key
- test_list_integrations_masks_keys: GET returns key_last4 = ****...last4, never plaintext
- test_list_integrations_no_key: GET returns null key_last4 for integrations with no key
- test_delete_integration: DELETE removes the row
- test_test_connection_success: POST /test returns {healthy: true} when provider responds
- test_test_connection_failure: POST /test returns {healthy: false, error: ...} on failure
- test_proxy_sentry_issues: GET sentry/proxy/issues returns transformed issue list
- test_proxy_posthog_events: GET posthog/proxy/events returns event list
- test_proxy_github_prs: GET github/proxy/prs returns PR list
- test_proxy_stripe_summary: GET stripe/proxy/summary returns subscription + balance data
- test_proxy_requires_admin: proxy endpoints return 401/403 without admin auth
- test_proxy_inactive_integration: proxy returns 400 when is_active=False
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request as StarletteRequest

# Patch targets
_SERVICE_CLIENT_PATCH = "app.routers.admin.integrations.get_service_client"
_EXECUTE_ASYNC_PATCH = "app.routers.admin.integrations.execute_async"
_ENCRYPT_PATCH = "app.routers.admin.integrations.encrypt_secret"
_DECRYPT_PATCH = "app.routers.admin.integrations.decrypt_secret"
_PROXY_SERVICE_PATCH = "app.routers.admin.integrations.IntegrationProxyService"
_TEST_CONNECTION_PATCH = "app.routers.admin.integrations._test_provider_connection"


def _make_mock_request(path: str = "/admin/integrations", method: str = "GET"):
    """Create a minimal Starlette Request for rate limiter dependency."""
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [(b"x-forwarded-for", b"127.0.0.1")],
        "client": ("127.0.0.1", 12345),
    }
    return StarletteRequest(scope=scope)


def _make_integration_row(
    provider: str = "sentry",
    api_key_encrypted: str | None = "enc-key-abc",
    is_active: bool = True,
) -> dict:
    """Build a fake admin_integrations row."""
    return {
        "id": "int-uuid-1",
        "provider": provider,
        "api_key_encrypted": api_key_encrypted,
        "base_url": None,
        "config": {"org_slug": "myorg", "project_slug": "myproj"},
        "is_active": is_active,
        "health_status": "healthy",
        "updated_at": "2026-03-20T10:00:00Z",
    }


def _make_chain(data: list | dict):
    """Build a Supabase-style query chain mock."""
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.upsert.return_value = chain
    chain.delete.return_value = chain
    chain.update.return_value = chain
    chain._return_data = data
    return chain


# =========================================================================
# Test 1: PUT /admin/integrations/{provider} encrypts the API key
# =========================================================================


@pytest.mark.asyncio
async def test_upsert_integration_encrypts_key(admin_user_dict):
    """PUT /admin/integrations/{provider} stores encrypted key via encrypt_secret."""
    from app.routers.admin.integrations import upsert_integration, IntegrationUpsertBody

    body = IntegrationUpsertBody(api_key="my-real-api-key", config={"org_slug": "myorg"})

    mock_client = MagicMock()
    chain = _make_chain([{"provider": "sentry"}])
    mock_client.table.return_value = chain

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        return result

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async),
        patch(_ENCRYPT_PATCH, return_value="encrypted-value") as mock_encrypt,
    ):
        result = await upsert_integration(
            provider="sentry",
            body=body,
            request=_make_mock_request(method="PUT"),
            admin_user=admin_user_dict,
        )

    mock_encrypt.assert_called_once_with("my-real-api-key")
    assert result["provider"] == "sentry"


# =========================================================================
# Test 2: GET /admin/integrations masks keys
# =========================================================================


@pytest.mark.asyncio
async def test_list_integrations_masks_keys(admin_user_dict):
    """GET /admin/integrations returns key_last4=****...last4, never plaintext."""
    from app.routers.admin.integrations import list_integrations

    rows = [_make_integration_row("sentry", "encrypted-abc")]

    mock_client = MagicMock()
    chain = _make_chain(rows)
    mock_client.table.return_value = chain

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        return result

    # decrypt returns a plaintext key like "sk-live-ABCD"
    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async),
        patch(_DECRYPT_PATCH, return_value="sk-live-ABCD"),
    ):
        result = await list_integrations(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )

    assert len(result) == 1
    item = result[0]
    # key_last4 should be ****...ABCD (last 4 of "sk-live-ABCD")
    assert item["key_last4"] is not None
    assert "ABCD" in item["key_last4"]
    assert "sk-live" not in item["key_last4"]


# =========================================================================
# Test 3: GET /admin/integrations returns null key_last4 when no key
# =========================================================================


@pytest.mark.asyncio
async def test_list_integrations_no_key(admin_user_dict):
    """GET /admin/integrations returns key_last4=None for integrations without a key."""
    from app.routers.admin.integrations import list_integrations

    rows = [_make_integration_row("sentry", api_key_encrypted=None)]

    mock_client = MagicMock()
    chain = _make_chain(rows)
    mock_client.table.return_value = chain

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        return result

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async),
    ):
        result = await list_integrations(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )

    assert len(result) == 1
    assert result[0]["key_last4"] is None


# =========================================================================
# Test 4: DELETE /admin/integrations/{provider}
# =========================================================================


@pytest.mark.asyncio
async def test_delete_integration(admin_user_dict):
    """DELETE /admin/integrations/{provider} removes the row."""
    from app.routers.admin.integrations import delete_integration

    mock_client = MagicMock()
    chain = _make_chain([])
    mock_client.table.return_value = chain

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        return result

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async),
    ):
        result = await delete_integration(
            provider="sentry",
            request=_make_mock_request(method="DELETE"),
            admin_user=admin_user_dict,
        )

    assert result["deleted"] is True
    assert result["provider"] == "sentry"


# =========================================================================
# Test 5: POST /test-connection success
# =========================================================================


@pytest.mark.asyncio
async def test_test_connection_success(admin_user_dict):
    """POST /admin/integrations/{provider}/test returns healthy=True on success."""
    from app.routers.admin.integrations import test_connection

    rows = [_make_integration_row("sentry", "encrypted-key")]

    mock_client = MagicMock()
    chain = _make_chain(rows)
    update_chain = _make_chain([{"provider": "sentry", "health_status": "healthy"}])
    mock_client.table.return_value = chain

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        return result

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async),
        patch(_DECRYPT_PATCH, return_value="plaintext-key"),
        patch(
            _TEST_CONNECTION_PATCH,
            new_callable=AsyncMock,
            return_value={"healthy": True},
        ),
    ):
        result = await test_connection(
            provider="sentry",
            request=_make_mock_request(method="POST"),
            admin_user=admin_user_dict,
        )

    assert result["healthy"] is True


# =========================================================================
# Test 6: POST /test-connection failure
# =========================================================================


@pytest.mark.asyncio
async def test_test_connection_failure(admin_user_dict):
    """POST /admin/integrations/{provider}/test returns healthy=False with error."""
    from app.routers.admin.integrations import test_connection

    rows = [_make_integration_row("sentry", "encrypted-key")]

    mock_client = MagicMock()
    chain = _make_chain(rows)
    mock_client.table.return_value = chain

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        return result

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async),
        patch(_DECRYPT_PATCH, return_value="plaintext-key"),
        patch(
            _TEST_CONNECTION_PATCH,
            new_callable=AsyncMock,
            return_value={"healthy": False, "error": "Connection refused"},
        ),
    ):
        result = await test_connection(
            provider="sentry",
            request=_make_mock_request(method="POST"),
            admin_user=admin_user_dict,
        )

    assert result["healthy"] is False
    assert "error" in result


# =========================================================================
# Test 7: GET sentry/proxy/issues returns data
# =========================================================================


@pytest.mark.asyncio
async def test_proxy_sentry_issues(admin_user_dict):
    """GET /admin/integrations/sentry/proxy/issues returns transformed issue list."""
    from app.routers.admin.integrations import proxy_sentry_issues

    rows = [_make_integration_row("sentry", "enc-key")]
    issues_data = [{"id": "PROJ-1", "title": "TypeError", "level": "error"}]

    mock_client = MagicMock()
    chain = _make_chain(rows)
    mock_client.table.return_value = chain

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        return result

    mock_proxy = MagicMock()
    mock_proxy.call = AsyncMock(return_value=issues_data)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async),
        patch(_DECRYPT_PATCH, return_value="real-key"),
        patch(_PROXY_SERVICE_PATCH, mock_proxy),
    ):
        result = await proxy_sentry_issues(
            request=_make_mock_request(path="/admin/integrations/sentry/proxy/issues"),
            admin_user=admin_user_dict,
        )

    assert result == issues_data
    mock_proxy.call.assert_called_once()


# =========================================================================
# Test 8: GET posthog/proxy/events returns data
# =========================================================================


@pytest.mark.asyncio
async def test_proxy_posthog_events(admin_user_dict):
    """GET /admin/integrations/posthog/proxy/events returns event list."""
    from app.routers.admin.integrations import proxy_posthog_events

    rows = [_make_integration_row("posthog", "enc-key")]
    events_data = {"results": [{"event": "$pageview", "timestamp": "2026-03-20T00:00:00Z"}], "count": 1}

    mock_client = MagicMock()
    chain = _make_chain(rows)
    mock_client.table.return_value = chain

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        return result

    mock_proxy = MagicMock()
    mock_proxy.call = AsyncMock(return_value=events_data)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async),
        patch(_DECRYPT_PATCH, return_value="real-key"),
        patch(_PROXY_SERVICE_PATCH, mock_proxy),
    ):
        result = await proxy_posthog_events(
            request=_make_mock_request(path="/admin/integrations/posthog/proxy/events"),
            admin_user=admin_user_dict,
        )

    assert result == events_data


# =========================================================================
# Test 9: GET github/proxy/prs returns PR list
# =========================================================================


@pytest.mark.asyncio
async def test_proxy_github_prs(admin_user_dict):
    """GET /admin/integrations/github/proxy/prs returns transformed PR list."""
    from app.routers.admin.integrations import proxy_github_prs

    rows = [_make_integration_row("github", "enc-key")]
    prs_data = [{"number": 42, "title": "Add feature", "state": "open"}]

    mock_client = MagicMock()
    chain = _make_chain(rows)
    mock_client.table.return_value = chain

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        return result

    mock_proxy = MagicMock()
    mock_proxy.call = AsyncMock(return_value=prs_data)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async),
        patch(_DECRYPT_PATCH, return_value="real-key"),
        patch(_PROXY_SERVICE_PATCH, mock_proxy),
    ):
        result = await proxy_github_prs(
            request=_make_mock_request(path="/admin/integrations/github/proxy/prs"),
            admin_user=admin_user_dict,
        )

    assert result == prs_data


# =========================================================================
# Test 10: GET stripe/proxy/summary returns subscription + balance data
# =========================================================================


@pytest.mark.asyncio
async def test_proxy_stripe_summary(admin_user_dict):
    """GET /admin/integrations/stripe/proxy/summary returns subscription + balance data."""
    from app.routers.admin.integrations import proxy_stripe_summary

    rows = [_make_integration_row("stripe", "enc-key")]
    summary_data = {
        "active_subscriptions": 42,
        "total_subscriptions": 50,
        "balance": {"available": [{"amount": 10000}], "pending": []},
    }

    mock_client = MagicMock()
    chain = _make_chain(rows)
    mock_client.table.return_value = chain

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        return result

    mock_proxy = MagicMock()
    mock_proxy.call = AsyncMock(return_value=summary_data)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async),
        patch(_DECRYPT_PATCH, return_value="real-key"),
        patch(_PROXY_SERVICE_PATCH, mock_proxy),
    ):
        result = await proxy_stripe_summary(
            request=_make_mock_request(path="/admin/integrations/stripe/proxy/summary"),
            admin_user=admin_user_dict,
        )

    assert result == summary_data


# =========================================================================
# Test 11: Proxy requires admin auth
# =========================================================================


@pytest.mark.asyncio
async def test_proxy_requires_admin():
    """Proxy endpoints reject requests without admin auth (403)."""
    from fastapi import HTTPException
    from app.middleware.admin_auth import require_admin

    # require_admin should raise HTTPException when called without valid creds
    # We test the middleware directly since it's injected via Depends
    import os

    os.environ.setdefault("ADMIN_EMAILS", "admin@test.com")

    with pytest.raises(HTTPException) as exc_info:
        # Call require_admin with a request that has no Authorization header
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/admin/integrations/sentry/proxy/issues",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }
        from starlette.requests import Request as StarletteRequest

        request = StarletteRequest(scope=scope)
        await require_admin(request=request)

    assert exc_info.value.status_code in (401, 403)


# =========================================================================
# Test 12: Proxy rejects inactive integration
# =========================================================================


@pytest.mark.asyncio
async def test_proxy_inactive_integration(admin_user_dict):
    """Proxy endpoints return 400 when integration is_active=False."""
    from fastapi import HTTPException
    from app.routers.admin.integrations import proxy_sentry_issues

    rows = [_make_integration_row("sentry", "enc-key", is_active=False)]

    mock_client = MagicMock()
    chain = _make_chain(rows)
    mock_client.table.return_value = chain

    async def fake_execute_async(query, **kwargs):
        result = MagicMock()
        result.data = query._return_data
        return result

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=mock_client),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=fake_execute_async),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await proxy_sentry_issues(
                request=_make_mock_request(path="/admin/integrations/sentry/proxy/issues"),
                admin_user=admin_user_dict,
            )

    assert exc_info.value.status_code == 400

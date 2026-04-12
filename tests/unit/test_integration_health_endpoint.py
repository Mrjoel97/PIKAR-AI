# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for GET /integrations/health endpoint.

Covers:
- Returns all providers with status, token_status, and last_sync_at.
- Token expiry within 7 days flagged as "expiring_soon" with expires_in_days.
- Providers with no token show token_status null.
- Returns 401 for unauthenticated requests.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Patch targets
# ---------------------------------------------------------------------------

_GET_CURRENT_USER_ID = "app.routers.onboarding.get_current_user_id"
_INTEGRATION_MANAGER_PATCH = "app.routers.integrations.IntegrationManager"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_USER_ID = "user-health-001"


def _make_provider_status(
    provider: str = "google",
    name: str = "Google",
    connected: bool = True,
    status: str = "connected",
    last_sync_at: str | None = "2026-04-10T10:00:00Z",
    error_count: int = 0,
    last_error: str | None = None,
) -> dict:
    """Build a provider status dict as returned by IntegrationManager."""
    return {
        "provider": provider,
        "name": name,
        "category": "productivity",
        "connected": connected,
        "status": status,
        "account_name": "test@example.com" if connected else "",
        "last_sync_at": last_sync_at,
        "error_count": error_count,
        "last_error": last_error,
    }


def _make_cred_row(
    provider: str = "google",
    expires_at: str | None = None,
) -> dict:
    """Build a minimal credential row."""
    return {
        "provider": provider,
        "expires_at": expires_at,
        "account_name": "test@example.com",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def app_with_health():
    """FastAPI test app with integrations router mounted and user auth overridden."""
    from app.routers import integrations
    from app.routers.onboarding import get_current_user_id

    test_app = FastAPI()
    test_app.include_router(integrations.router)
    # Override authentication dependency
    test_app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    return test_app


@pytest.fixture()
def client(app_with_health):
    """TestClient for the health-enabled integrations app."""
    return TestClient(app_with_health)


# ---------------------------------------------------------------------------
# Test 1: GET /integrations/health returns provider list with enriched fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_integration_health_returns_provider_list():
    """GET /integrations/health returns all providers with status and token_status fields."""
    from app.routers.integrations import get_integration_health

    statuses = [
        _make_provider_status("google", "Google", connected=True),
        _make_provider_status("slack", "Slack", connected=False, status="disconnected"),
    ]

    mock_mgr = AsyncMock()
    mock_mgr.get_integration_status = AsyncMock(return_value=statuses)
    mock_mgr.get_credentials = AsyncMock(return_value=None)

    with patch(_INTEGRATION_MANAGER_PATCH, return_value=mock_mgr):
        result = await get_integration_health(current_user_id=_USER_ID)

    content = result.body
    import json
    data = json.loads(content)

    assert isinstance(data, list)
    assert len(data) == 2

    google = next(p for p in data if p["provider"] == "google")
    slack = next(p for p in data if p["provider"] == "slack")

    assert google["status"] == "connected"
    assert "token_status" in google
    assert "last_sync_at" in google

    assert slack["status"] == "disconnected"
    assert slack["token_status"] is None  # Not connected, no token


# ---------------------------------------------------------------------------
# Test 2: Token expiring within 7 days flagged as "expiring_soon"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_integration_health_flags_expiring_token():
    """Provider with token expiring within 7 days gets token_status='expiring_soon'."""
    from app.routers.integrations import get_integration_health

    # Token expires in 3 days
    expires_soon = (datetime.now(tz=timezone.utc) + timedelta(days=3)).isoformat()

    statuses = [
        _make_provider_status("hubspot", "HubSpot", connected=True),
    ]
    cred_row = _make_cred_row("hubspot", expires_at=expires_soon)

    mock_mgr = AsyncMock()
    mock_mgr.get_integration_status = AsyncMock(return_value=statuses)
    mock_mgr.get_credentials = AsyncMock(return_value=cred_row)

    with patch(_INTEGRATION_MANAGER_PATCH, return_value=mock_mgr):
        result = await get_integration_health(current_user_id=_USER_ID)

    import json
    data = json.loads(result.body)

    hubspot = next(p for p in data if p["provider"] == "hubspot")
    assert hubspot["token_status"] == "expiring_soon"
    assert "expires_in_days" in hubspot
    assert hubspot["expires_in_days"] <= 3


# ---------------------------------------------------------------------------
# Test 3: Token valid (not expiring) returns token_status="valid"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_integration_health_valid_token_status():
    """Provider with token expiring in 30+ days gets token_status='valid'."""
    from app.routers.integrations import get_integration_health

    expires_far = (datetime.now(tz=timezone.utc) + timedelta(days=30)).isoformat()

    statuses = [
        _make_provider_status("stripe", "Stripe", connected=True),
    ]
    cred_row = _make_cred_row("stripe", expires_at=expires_far)

    mock_mgr = AsyncMock()
    mock_mgr.get_integration_status = AsyncMock(return_value=statuses)
    mock_mgr.get_credentials = AsyncMock(return_value=cred_row)

    with patch(_INTEGRATION_MANAGER_PATCH, return_value=mock_mgr):
        result = await get_integration_health(current_user_id=_USER_ID)

    import json
    data = json.loads(result.body)

    stripe = next(p for p in data if p["provider"] == "stripe")
    assert stripe["token_status"] == "valid"
    assert "expires_in_days" not in stripe


# ---------------------------------------------------------------------------
# Test 4: Disconnected provider has token_status null
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_integration_health_disconnected_no_token_status():
    """Disconnected providers have token_status=null."""
    from app.routers.integrations import get_integration_health

    statuses = [
        _make_provider_status(
            "meta_ads",
            "Meta Ads",
            connected=False,
            status="disconnected",
            last_sync_at=None,
        ),
    ]

    mock_mgr = AsyncMock()
    mock_mgr.get_integration_status = AsyncMock(return_value=statuses)
    mock_mgr.get_credentials = AsyncMock(return_value=None)

    with patch(_INTEGRATION_MANAGER_PATCH, return_value=mock_mgr):
        result = await get_integration_health(current_user_id=_USER_ID)

    import json
    data = json.loads(result.body)

    meta = next(p for p in data if p["provider"] == "meta_ads")
    assert meta["token_status"] is None
    assert meta["connected"] is False


# ---------------------------------------------------------------------------
# Test 5: Unauthenticated request returns 401
# ---------------------------------------------------------------------------


def test_integration_health_unauthenticated(app_with_health):
    """GET /integrations/health without auth returns 401."""
    from fastapi import FastAPI, HTTPException
    from app.routers import integrations
    from app.routers.onboarding import get_current_user_id

    # Create a new app WITHOUT the auth override to simulate unauthenticated request
    unauth_app = FastAPI()
    unauth_app.include_router(integrations.router)

    def _raise_401():
        raise HTTPException(status_code=401, detail="Not authenticated")

    unauth_app.dependency_overrides[get_current_user_id] = _raise_401

    unauth_client = TestClient(unauth_app, raise_server_exceptions=False)
    response = unauth_client.get("/integrations/health")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Test 6: Token with no expires_at (non-expiring) returns token_status="valid"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_integration_health_no_expiry_returns_valid():
    """Provider with token that has no expires_at gets token_status='valid'."""
    from app.routers.integrations import get_integration_health

    statuses = [
        _make_provider_status("slack", "Slack", connected=True),
    ]
    cred_row = _make_cred_row("slack", expires_at=None)  # No expiry

    mock_mgr = AsyncMock()
    mock_mgr.get_integration_status = AsyncMock(return_value=statuses)
    mock_mgr.get_credentials = AsyncMock(return_value=cred_row)

    with patch(_INTEGRATION_MANAGER_PATCH, return_value=mock_mgr):
        result = await get_integration_health(current_user_id=_USER_ID)

    import json
    data = json.loads(result.body)

    slack = next(p for p in data if p["provider"] == "slack")
    assert slack["token_status"] == "valid"

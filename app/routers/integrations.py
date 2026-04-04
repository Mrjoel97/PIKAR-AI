# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Integrations API Router.

Handles the OAuth lifecycle (authorize, callback), provider listing,
connection status, and disconnect for third-party integrations.

The authorize endpoint redirects the user to the provider's consent
page. After granting access, the provider redirects to the callback
endpoint which exchanges the code for tokens, encrypts them, and
stores the credentials. The callback closes the popup window and
signals the parent page via ``postMessage``.
"""

from __future__ import annotations

import logging
import os
import secrets
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.config.integration_providers import PROVIDER_REGISTRY, get_provider
from app.routers.onboarding import get_current_user_id
from app.services.base_service import AdminService
from app.services.cache import get_cache_service
from app.services.integration_manager import IntegrationManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["Integrations"])


# ============================================================================
# Public Endpoints
# ============================================================================


@router.get("/providers")
async def list_providers() -> JSONResponse:
    """Return all available integration providers.

    Returns the provider registry with public metadata only (no env var
    names or secrets).

    Returns:
        JSON list of provider objects with ``key``, ``name``,
        ``auth_type``, ``category``, ``icon_url``, ``scopes``.
    """
    providers = []
    for key, config in PROVIDER_REGISTRY.items():
        providers.append({
            "key": key,
            "name": config.name,
            "auth_type": config.auth_type,
            "category": config.category,
            "icon_url": config.icon_url,
            "scopes": config.scopes,
        })
    return JSONResponse(content=providers)


# ============================================================================
# OAuth Flow
# ============================================================================


@router.get("/{provider}/authorize")
async def authorize_provider(
    provider: str,
    request: Request,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> RedirectResponse:
    """Redirect the user to the provider's OAuth consent page.

    Generates a CSRF state token containing the user ID, stores it in
    Redis with a 10-minute TTL, and builds the authorization URL with
    the appropriate client ID, scopes, and redirect URI.

    Args:
        provider: Provider key (e.g. ``"hubspot"``).
        request: FastAPI request object.
        current_user_id: Authenticated user's UUID.

    Returns:
        Redirect to the provider's authorization URL.

    Raises:
        HTTPException: 404 if provider not found, 400 if not an OAuth2
            provider.
    """
    config = get_provider(provider)
    if not config:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")
    if config.auth_type != "oauth2":
        raise HTTPException(
            status_code=400,
            detail=f"Provider {provider} does not support OAuth2 authorization",
        )

    # Generate CSRF state token
    state = f"{current_user_id}:{provider}:{secrets.token_urlsafe(16)}"

    # Store in Redis with 600s TTL
    cache = get_cache_service()
    await cache.set_generic(
        f"pikar:integration:oauth_state:{state}",
        {"user_id": current_user_id, "provider": provider},
        ttl=600,
    )

    # Build redirect URI for callback
    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/integrations/{provider}/callback"

    # Resolve client ID from environment
    client_id = os.environ.get(config.client_id_env, "")
    if not client_id:
        logger.error(
            "OAuth client ID not configured for %s (env: %s)",
            provider,
            config.client_id_env,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Integration not configured: {provider}",
        )

    # Build authorization URL
    scopes = " ".join(config.scopes)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scopes,
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    # Use httpx for proper URL encoding
    auth_url = str(
        httpx.URL(config.auth_url).copy_merge_params(params)
    )

    logger.info(
        "Redirecting user %s to %s OAuth consent",
        current_user_id,
        provider,
    )
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    code: str = Query(..., description="Authorization code from provider"),
    state: str = Query(..., description="CSRF state token"),
) -> HTMLResponse:
    """Handle the OAuth callback from the provider.

    Validates the CSRF state token, exchanges the authorization code for
    access/refresh tokens, encrypts and stores them, then returns an HTML
    page that signals the parent window and closes the popup.

    This endpoint does NOT require user authentication — the user_id is
    extracted from the validated state token.

    Args:
        provider: Provider key.
        request: FastAPI request object.
        code: Authorization code from the provider.
        state: CSRF state token for validation.

    Returns:
        HTML page that calls ``window.opener.postMessage`` and closes.

    Raises:
        HTTPException: 403 if state is invalid, 400 on token exchange failure.
    """
    # Validate state from Redis
    cache = get_cache_service()
    state_key = f"pikar:integration:oauth_state:{state}"
    cached = await cache.get_generic(state_key)

    if not cached.value:
        logger.warning("Invalid or expired OAuth state token for %s", provider)
        raise HTTPException(status_code=403, detail="Invalid or expired state token")

    # Delete state (one-time use)
    try:
        redis = await cache._ensure_connection()
        if redis:
            await redis.delete(state_key)
    except Exception:
        logger.warning("Failed to delete OAuth state key: %s", state_key)

    state_data = cached.value
    user_id = state_data.get("user_id")
    state_provider = state_data.get("provider")

    if not user_id or state_provider != provider:
        raise HTTPException(status_code=403, detail="State token mismatch")

    # Look up provider config
    config = get_provider(provider)
    if not config:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    # Build redirect URI (must match the authorize step)
    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/integrations/{provider}/callback"

    # Exchange authorization code for tokens
    client_id = os.environ.get(config.client_id_env, "")
    client_secret = os.environ.get(config.client_secret_env, "")

    try:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.post(
                config.token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            response.raise_for_status()
            token_data = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Token exchange failed for %s: %s %s",
            provider,
            exc.response.status_code,
            exc.response.text,
        )
        return _oauth_error_html(provider, "Token exchange failed")
    except Exception:
        logger.exception("Token exchange error for %s", provider)
        return _oauth_error_html(provider, "Connection error during token exchange")

    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")
    token_type = token_data.get("token_type", "bearer")
    scopes = token_data.get("scope", "")

    # Calculate expires_at from expires_in
    expires_at = None
    if expires_in:
        from datetime import datetime, timedelta, timezone

        expires_at = (
            datetime.now(tz=timezone.utc) + timedelta(seconds=int(expires_in))
        ).isoformat()

    # Store credentials using service role (no user JWT in popup callback)
    admin_svc = AdminService()
    mgr = IntegrationManager.__new__(IntegrationManager)
    mgr._url = os.environ.get("SUPABASE_URL", "")
    mgr._anon_key = os.environ.get("SUPABASE_ANON_KEY", "")
    mgr._user_token = None
    mgr._client = admin_svc.client

    try:
        await mgr.store_credentials(
            user_id=user_id,
            provider=provider,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            scopes=scopes,
            account_name=_extract_account_name(token_data),
            token_type=token_type,
        )
    except Exception:
        logger.exception(
            "Failed to store credentials for %s user=%s",
            provider,
            user_id,
        )
        return _oauth_error_html(provider, "Failed to save credentials")

    logger.info(
        "OAuth callback successful: provider=%s user=%s",
        provider,
        user_id,
    )

    return _oauth_success_html(provider)


# ============================================================================
# Authenticated Endpoints
# ============================================================================


@router.get("/status")
async def get_integration_status(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """Return per-provider connection status for the authenticated user.

    Merges credential and sync state data for all providers in the
    registry.

    Args:
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON list of status objects (one per provider).
    """
    mgr = IntegrationManager()
    statuses = await mgr.get_integration_status(current_user_id)
    return JSONResponse(content=statuses)


@router.delete("/{provider}")
async def disconnect_provider(
    provider: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """Disconnect (remove credentials for) a provider.

    Args:
        provider: Provider key.
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON with ``disconnected: true`` and provider key.
    """
    mgr = IntegrationManager()
    deleted = await mgr.delete_credentials(current_user_id, provider)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"No connection found for provider: {provider}",
        )
    return JSONResponse(content={"disconnected": True, "provider": provider})


# ============================================================================
# Stripe Sync (Phase 41)
# ============================================================================


@router.post("/stripe/sync")
async def stripe_manual_sync(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """Trigger a manual Stripe historical transaction sync.

    Imports balance transactions from the last 12 months into
    ``financial_records``.  Requires an authenticated user.

    Args:
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON with sync status and import/skip counts.

    Raises:
        HTTPException: 502 on Stripe API failure, 500 if SDK missing.
    """
    try:
        from app.services.stripe_sync_service import StripeSyncService
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="Stripe sync service not available",
        ) from exc

    svc = StripeSyncService()
    try:
        result = await svc.sync_history(current_user_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.exception(
            "Stripe sync failed for user=%s", current_user_id
        )
        raise HTTPException(
            status_code=502,
            detail=f"Stripe API error: {exc!s}",
        ) from exc

    return JSONResponse(
        content={"status": "syncing", "result": result}
    )


# ============================================================================
# Helpers
# ============================================================================


def _extract_account_name(token_data: dict[str, Any]) -> str:
    """Extract a display name from the token exchange response.

    Different providers return account info in different fields.

    Args:
        token_data: JSON response from the token exchange.

    Returns:
        Account display name, or empty string if not found.
    """
    # Common fields where providers return account info
    for field in ("hub_domain", "shop", "team_name", "team", "account_name", "name"):
        if field in token_data:
            return str(token_data[field])
    return ""


def _oauth_success_html(provider: str) -> HTMLResponse:
    """Return an HTML page that signals success to the parent window.

    Args:
        provider: Provider key.

    Returns:
        HTMLResponse that calls ``postMessage`` and closes the popup.
    """
    html = f"""<!DOCTYPE html>
<html>
<head><title>Connected</title></head>
<body>
<p>Successfully connected to {provider}. This window will close automatically.</p>
<script>
  if (window.opener) {{
    window.opener.postMessage({{
      type: 'oauth-callback',
      provider: '{provider}',
      success: true
    }}, '*');
  }}
  setTimeout(function() {{ window.close(); }}, 1500);
</script>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200)


def _oauth_error_html(provider: str, error: str) -> HTMLResponse:
    """Return an HTML page that signals failure to the parent window.

    Args:
        provider: Provider key.
        error: Error description.

    Returns:
        HTMLResponse that calls ``postMessage`` with error and closes.
    """
    html = f"""<!DOCTYPE html>
<html>
<head><title>Connection Failed</title></head>
<body>
<p>Failed to connect to {provider}: {error}</p>
<script>
  if (window.opener) {{
    window.opener.postMessage({{
      type: 'oauth-callback',
      provider: '{provider}',
      success: false,
      error: '{error}'
    }}, '*');
  }}
  setTimeout(function() {{ window.close(); }}, 3000);
</script>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200)

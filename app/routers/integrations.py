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
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

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
        providers.append(
            {
                "key": key,
                "name": config.name,
                "auth_type": config.auth_type,
                "category": config.category,
                "icon_url": config.icon_url,
                "scopes": config.scopes,
            }
        )
    return JSONResponse(content=providers)


# ============================================================================
# OAuth Flow
# ============================================================================


@router.get("/{provider}/authorize")
async def authorize_provider(
    provider: str,
    request: Request,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    shop: str | None = Query(
        None,
        description=(
            "Shopify shop slug (e.g. 'mystore'). Required when provider is 'shopify'."
        ),
    ),
) -> RedirectResponse:
    """Redirect the user to the provider's OAuth consent page.

    Generates a CSRF state token containing the user ID, stores it in
    Redis with a 10-minute TTL, and builds the authorization URL with
    the appropriate client ID, scopes, and redirect URI.

    For Shopify, the ``shop`` query parameter is required and is used
    to substitute ``{shop}`` placeholders in the auth/token URLs.

    Args:
        provider: Provider key (e.g. ``"hubspot"``).
        request: FastAPI request object.
        current_user_id: Authenticated user's UUID.
        shop: Shopify shop slug (required for Shopify provider).

    Returns:
        Redirect to the provider's authorization URL.

    Raises:
        HTTPException: 404 if provider not found, 400 if not an OAuth2
            provider or if Shopify is missing the shop parameter.
    """
    config = get_provider(provider)
    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown provider: {provider}",
        )
    if config.auth_type != "oauth2":
        raise HTTPException(
            status_code=400,
            detail=f"Provider {provider} does not support OAuth2 authorization",
        )

    # Shopify requires the shop parameter for URL substitution
    if provider == "shopify" and not shop:
        raise HTTPException(
            status_code=400,
            detail=("Shopify requires a shop parameter (e.g., ?shop=mystore)"),
        )

    # Generate CSRF state token — include shop for Shopify
    state = f"{current_user_id}:{provider}:{secrets.token_urlsafe(16)}"

    # Store in Redis with 600s TTL (include shop for callback)
    state_data: dict[str, Any] = {
        "user_id": current_user_id,
        "provider": provider,
    }
    if shop:
        state_data["shop"] = shop

    cache = get_cache_service()
    await cache.set_generic(
        f"pikar:integration:oauth_state:{state}",
        state_data,
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

    # Substitute {shop} in auth URL for Shopify
    auth_url_template = config.auth_url
    if shop and "{shop}" in auth_url_template:
        auth_url_template = auth_url_template.replace("{shop}", shop)

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
    auth_url = str(httpx.URL(auth_url_template).copy_merge_params(params))

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
    shop = state_data.get("shop")  # Shopify shop slug from authorize

    if not user_id or state_provider != provider:
        raise HTTPException(status_code=403, detail="State token mismatch")

    # Look up provider config
    config = get_provider(provider)
    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown provider: {provider}",
        )

    # Build redirect URI (must match the authorize step)
    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/integrations/{provider}/callback"

    # Substitute {shop} in token URL for Shopify
    token_url = config.token_url
    if shop and "{shop}" in token_url:
        token_url = token_url.replace("{shop}", shop)

    # Exchange authorization code for tokens
    client_id = os.environ.get(config.client_id_env, "")
    client_secret = os.environ.get(config.client_secret_env, "")

    try:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.post(
                token_url,
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

    # For Shopify, use the shop slug as account_name so webhooks
    # can resolve user_id from the X-Shopify-Shop-Domain header.
    account_name = (
        shop if provider == "shopify" and shop else _extract_account_name(token_data)
    )

    # Store credentials using service role (no user JWT in popup)
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
            account_name=account_name,
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

    # For ad platforms: check if a budget cap has been configured.
    # If not, signal the frontend to prompt the user for one before
    # completing the connection flow.
    if provider in ("google_ads", "meta_ads"):
        try:
            from app.services.ad_budget_cap_service import AdBudgetCapService

            cap_svc = AdBudgetCapService()
            cap_is_set = await cap_svc.is_cap_set(user_id=user_id, platform=provider)
            if not cap_is_set:
                return _oauth_budget_cap_prompt_html(provider)
        except Exception:
            logger.warning(
                "Budget cap check failed after OAuth for %s user=%s — "
                "proceeding without prompt",
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
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Stripe sync failed for user=%s", current_user_id)
        raise HTTPException(
            status_code=502,
            detail=f"Stripe API error: {exc!s}",
        ) from exc

    return JSONResponse(content={"status": "syncing", "result": result})


# ============================================================================
# Helpers
# ============================================================================


_AD_PLATFORMS = frozenset({"google_ads", "meta_ads"})
_PM_PROVIDERS = frozenset({"linear", "asana"})
_NOTIF_PROVIDERS = frozenset({"slack", "teams"})


# ============================================================================
# Request schemas
# ============================================================================


class BudgetCapRequest(BaseModel):
    """Request body for setting a budget cap."""

    monthly_cap: float


class SyncConfigRequest(BaseModel):
    """Request body for saving PM sync configuration."""

    project_ids: list[str]


class StatusMappingItem(BaseModel):
    """A single external-state-to-pikar-status mapping entry."""

    external_state_id: str
    pikar_status: str


class NotificationRuleRequest(BaseModel):
    """Request body for creating a notification rule."""

    event_type: str
    channel_id: str
    channel_name: str = ""


class NotificationRuleToggle(BaseModel):
    """Request body for toggling a notification rule's enabled flag."""

    enabled: bool


class ChannelConfigRequest(BaseModel):
    """Request body for upserting notification channel configuration."""

    daily_briefing: bool
    briefing_channel_id: str | None = None
    briefing_channel_name: str = ""
    briefing_time_utc: str = "08:00"


# ============================================================================
# Ad Platform — Budget Cap Endpoints
# ============================================================================


@router.get("/{provider}/budget-cap")
async def get_budget_cap(
    provider: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """Return the current monthly budget cap for the authenticated user.

    Args:
        provider: Ad platform provider key (``"google_ads"`` or ``"meta_ads"``).
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON with ``monthly_cap`` and ``platform`` fields.

    Raises:
        HTTPException: 400 if provider is not an ad platform, 404 if no cap set.
    """
    if provider not in _AD_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Budget caps are only supported for: "
                + ", ".join(sorted(_AD_PLATFORMS))
            ),
        )

    from app.services.ad_budget_cap_service import AdBudgetCapService

    cap_svc = AdBudgetCapService()
    cap = await cap_svc.get_cap(user_id=current_user_id, platform=provider)

    if cap is None:
        raise HTTPException(
            status_code=404,
            detail=f"No budget cap set for {provider}. Use PUT to configure one.",
        )

    return JSONResponse(content={"platform": provider, "monthly_cap": cap})


@router.put("/{provider}/budget-cap")
async def set_budget_cap(
    provider: str,
    body: BudgetCapRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """Set or update the monthly budget cap for an ad platform.

    Args:
        provider: Ad platform provider key (``"google_ads"`` or ``"meta_ads"``).
        body: Request body with ``monthly_cap`` (float, USD).
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON with the upserted cap record.

    Raises:
        HTTPException: 400 if provider is not an ad platform or cap is invalid.
    """
    if provider not in _AD_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Budget caps are only supported for: "
                + ", ".join(sorted(_AD_PLATFORMS))
            ),
        )

    if body.monthly_cap <= 0:
        raise HTTPException(
            status_code=400,
            detail="monthly_cap must be a positive number (USD)",
        )

    from app.services.ad_budget_cap_service import AdBudgetCapService

    cap_svc = AdBudgetCapService()
    result = await cap_svc.set_cap(
        user_id=current_user_id,
        platform=provider,
        monthly_cap=body.monthly_cap,
    )

    return JSONResponse(content=result)


# ============================================================================
# Ad Platform — Performance Sync Endpoints
# ============================================================================


@router.post("/{provider}/sync-performance")
async def sync_ad_performance_on_demand(
    provider: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """Trigger an on-demand performance sync for the specified ad platform.

    Pulls the last 7 days of performance data, writes to ``ad_spend_tracking``,
    and runs a budget pacing check.

    Args:
        provider: Ad platform provider key (``"google_ads"`` or ``"meta_ads"``).
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON with sync result (``platform``, ``records_synced``).

    Raises:
        HTTPException: 400 if provider is not an ad platform, 502 on sync error.
    """
    if provider not in _AD_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Performance sync is only supported for: "
                + ", ".join(sorted(_AD_PLATFORMS))
            ),
        )

    from app.services.ad_performance_sync_service import AdPerformanceSyncService

    svc = AdPerformanceSyncService()
    try:
        result = await svc.sync_user_on_demand(
            user_id=current_user_id, platform=provider
        )
    except Exception as exc:
        logger.exception(
            "On-demand ad sync failed for user=%s platform=%s",
            current_user_id,
            provider,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Ad performance sync failed: {exc!s}",
        ) from exc

    return JSONResponse(content=result)


@router.post("/internal/sync/ad-performance")
async def scheduled_ad_performance_sync(
    x_workflow_secret: Annotated[str | None, Header()] = None,
) -> JSONResponse:
    """Trigger the full ad performance sync for all connected users.

    This endpoint is called by Cloud Scheduler every 6 hours. It is
    authenticated via the ``X-Workflow-Secret`` header, which must match
    the ``WORKFLOW_SERVICE_SECRET`` environment variable.

    Args:
        x_workflow_secret: Value of the ``X-Workflow-Secret`` header.

    Returns:
        JSON with sync summary (``users_synced``, ``platforms_synced``, ``errors``).

    Raises:
        HTTPException: 401 if the secret header is missing or incorrect.
    """
    expected_secret = os.environ.get("WORKFLOW_SERVICE_SECRET", "")
    if not expected_secret or x_workflow_secret != expected_secret:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing X-Workflow-Secret header",
        )

    from app.services.ad_performance_sync_service import AdPerformanceSyncService

    svc = AdPerformanceSyncService()
    try:
        result = await svc.sync_all_users()
    except Exception as exc:
        logger.exception("Scheduled ad performance sync failed")
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {exc!s}",
        ) from exc

    return JSONResponse(content=result)


# ============================================================================
# PM Integration — Project Listing, Sync Config, Status Mappings
# ============================================================================


@router.get("/{provider}/projects")
async def list_pm_projects(
    provider: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """List available projects/teams from a PM integration.

    For Linear, returns the user's teams.
    For Asana, lists workspaces then returns all non-archived projects
    across all workspaces.

    Args:
        provider: PM provider key (``"linear"`` or ``"asana"``).
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON list of project dicts with ``id``, ``name``, and optional
        ``description`` (Linear) or ``color`` (Asana).

    Raises:
        HTTPException: 400 if provider is not a PM tool, 502 on API failure.
    """
    if provider not in _PM_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Project listing is only supported for: "
                + ", ".join(sorted(_PM_PROVIDERS))
            ),
        )

    try:
        if provider == "linear":
            from app.services.linear_service import LinearService

            svc = LinearService()
            teams = await svc.list_teams(current_user_id)
            projects = [
                {
                    "id": t["id"],
                    "name": t.get("name", ""),
                    "key": t.get("key", ""),
                    "description": t.get("description", ""),
                }
                for t in teams
            ]
        else:
            from app.services.asana_service import AsanaService

            svc = AsanaService()
            workspaces = await svc.list_workspaces(current_user_id)
            projects = []
            for ws in workspaces:
                ws_projects = await svc.list_projects(current_user_id, ws["gid"])
                for p in ws_projects:
                    projects.append(
                        {
                            "id": p["gid"],
                            "name": p.get("name", ""),
                            "color": p.get("color", ""),
                            "workspace_id": ws["gid"],
                            "workspace_name": ws.get("name", ""),
                        }
                    )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception(
            "Failed to list PM projects: provider=%s user=%s",
            provider,
            current_user_id,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Failed to list {provider} projects: {exc!s}",
        ) from exc

    return JSONResponse(content={"provider": provider, "projects": projects})


@router.put("/{provider}/sync-config")
async def save_pm_sync_config(
    provider: str,
    body: SyncConfigRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """Save PM sync configuration and trigger an initial sync.

    Persists the selected project IDs, seeds default status mappings for
    each project's workflow states, and initiates a bulk import of tasks
    updated in the last 30 days.

    Args:
        provider: PM provider key (``"linear"`` or ``"asana"``).
        body: Request body with ``project_ids`` list.
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON with sync result (``{"synced": N, "errors": N}``).

    Raises:
        HTTPException: 400 if provider is not a PM tool.
    """
    if provider not in _PM_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Sync config is only supported for: " + ", ".join(sorted(_PM_PROVIDERS))
            ),
        )

    if not body.project_ids:
        raise HTTPException(
            status_code=400,
            detail="project_ids must be a non-empty list",
        )

    from app.services.pm_sync_service import PMSyncService

    svc = PMSyncService()
    try:
        result = await svc.save_sync_config(
            user_id=current_user_id,
            provider=provider,
            project_ids=body.project_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "save_pm_sync_config failed: provider=%s user=%s",
            provider,
            current_user_id,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Sync config save failed: {exc!s}",
        ) from exc

    return JSONResponse(content={"provider": provider, "sync_result": result})


@router.get("/{provider}/sync-config")
async def get_pm_sync_config(
    provider: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """Return the current PM sync configuration for the authenticated user.

    Args:
        provider: PM provider key (``"linear"`` or ``"asana"``).
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON with ``project_ids`` list and ``last_sync_at`` timestamp.

    Raises:
        HTTPException: 400 if provider is not a PM tool.
    """
    if provider not in _PM_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Sync config is only supported for: " + ", ".join(sorted(_PM_PROVIDERS))
            ),
        )

    from app.services.pm_sync_service import PMSyncService

    svc = PMSyncService()
    config = await svc.get_sync_config(current_user_id, provider)
    return JSONResponse(content={"provider": provider, **config})


@router.get("/{provider}/status-mappings")
async def get_pm_status_mappings(
    provider: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """Return current status mappings for the authenticated user.

    Args:
        provider: PM provider key (``"linear"`` or ``"asana"``).
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON list of mapping objects with ``external_state_id``,
        ``external_state_name``, and ``pikar_status``.

    Raises:
        HTTPException: 400 if provider is not a PM tool.
    """
    if provider not in _PM_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Status mappings are only supported for: "
                + ", ".join(sorted(_PM_PROVIDERS))
            ),
        )

    from app.services.base_service import AdminService
    from app.services.supabase_async import execute_async

    admin = AdminService()
    result = await execute_async(
        admin.client.table("pm_status_mappings")
        .select("external_state_id,external_state_name,pikar_status")
        .eq("user_id", current_user_id)
        .eq("provider", provider)
        .order("external_state_name"),
        op_name="integrations.get_pm_status_mappings",
    )
    return JSONResponse(
        content={
            "provider": provider,
            "mappings": result.data or [],
        }
    )


@router.put("/{provider}/status-mappings")
async def update_pm_status_mappings(
    provider: str,
    body: list[StatusMappingItem],
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """Update custom status mappings for a PM provider.

    Upserts the supplied mappings using the
    ``(user_id, provider, external_state_id)`` unique constraint.

    Args:
        provider: PM provider key (``"linear"`` or ``"asana"``).
        body: List of mapping objects with ``external_state_id`` and
            ``pikar_status``.
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON with ``updated`` count.

    Raises:
        HTTPException: 400 if provider is not a PM tool or body is empty.
    """
    if provider not in _PM_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Status mappings are only supported for: "
                + ", ".join(sorted(_PM_PROVIDERS))
            ),
        )

    if not body:
        raise HTTPException(
            status_code=400,
            detail="Mapping list must not be empty",
        )

    valid_statuses = {"pending", "in_progress", "completed", "cancelled"}
    for item in body:
        if item.pikar_status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid pikar_status '{item.pikar_status}'. "
                    f"Must be one of: {sorted(valid_statuses)}"
                ),
            )

    from app.services.base_service import AdminService
    from app.services.supabase_async import execute_async

    admin = AdminService()
    rows = [
        {
            "user_id": current_user_id,
            "provider": provider,
            "external_state_id": item.external_state_id,
            # external_state_name unknown at this point; use ID as placeholder
            "external_state_name": item.external_state_id,
            "pikar_status": item.pikar_status,
        }
        for item in body
    ]

    await execute_async(
        admin.client.table("pm_status_mappings").upsert(
            rows,
            on_conflict="user_id,provider,external_state_id",
        ),
        op_name="integrations.update_pm_status_mappings",
    )

    return JSONResponse(content={"provider": provider, "updated": len(rows)})


# ============================================================================
# Notification Rules — CRUD + Channel Config
# ============================================================================


@router.get("/notification-events")
async def list_notification_events() -> JSONResponse:
    """Return the static list of supported notification event types.

    No authentication required — returns the same list for all users.

    Returns:
        JSON list of event dicts with ``type`` and ``label`` keys.

    """
    from app.services.notification_rule_service import NotificationRuleService

    return JSONResponse(content=NotificationRuleService.SUPPORTED_EVENTS)


@router.get("/{provider}/notification-rules")
async def list_notification_rules(
    provider: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """List notification rules for a given provider.

    Args:
        provider: Notification provider key (``"slack"`` or ``"teams"``).
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON list of rule dicts for the provider.

    Raises:
        HTTPException: 400 if provider is not a notification provider.

    """
    if provider not in _NOTIF_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail="Not a notification provider",
        )

    from app.services.notification_rule_service import NotificationRuleService

    svc = NotificationRuleService()
    rules = await svc.list_rules(current_user_id, provider=provider)
    return JSONResponse(content={"provider": provider, "rules": rules})


@router.post("/{provider}/notification-rules")
async def create_notification_rule(
    provider: str,
    body: NotificationRuleRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """Create a notification rule routing an event type to a channel.

    Uses upsert on ``(user_id, provider, event_type, channel_id)`` so
    calling this endpoint twice with the same parameters is idempotent.

    Args:
        provider: Notification provider key (``"slack"`` or ``"teams"``).
        body: Rule details — ``event_type``, ``channel_id``, ``channel_name``.
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON with the created (or existing) rule row.

    Raises:
        HTTPException: 400 if provider is not a notification provider.

    """
    if provider not in _NOTIF_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail="Not a notification provider",
        )

    from app.services.notification_rule_service import NotificationRuleService

    svc = NotificationRuleService()
    rule = await svc.create_rule(
        user_id=current_user_id,
        provider=provider,
        event_type=body.event_type,
        channel_id=body.channel_id,
        channel_name=body.channel_name,
    )
    return JSONResponse(content={"provider": provider, "rule": rule})


@router.patch("/{provider}/notification-rules/{rule_id}")
async def toggle_notification_rule(
    provider: str,
    rule_id: str,
    body: NotificationRuleToggle,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """Enable or disable a notification rule.

    Args:
        provider: Notification provider key (``"slack"`` or ``"teams"``).
        rule_id: UUID of the rule to toggle.
        body: Request body with the ``enabled`` flag.
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON with the updated rule row.

    Raises:
        HTTPException: 400 if provider is not a notification provider.

    """
    if provider not in _NOTIF_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail="Not a notification provider",
        )

    from app.services.notification_rule_service import NotificationRuleService

    svc = NotificationRuleService()
    rule = await svc.update_rule(
        user_id=current_user_id,
        rule_id=rule_id,
        enabled=body.enabled,
    )
    return JSONResponse(content={"provider": provider, "rule": rule})


@router.delete("/{provider}/notification-rules/{rule_id}")
async def delete_notification_rule(
    provider: str,
    rule_id: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """Delete a notification rule.

    Args:
        provider: Notification provider key (``"slack"`` or ``"teams"``).
        rule_id: UUID of the rule to delete.
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON with ``deleted: true`` on success.

    Raises:
        HTTPException: 400 if provider is not a notification provider,
            404 if no matching rule found.

    """
    if provider not in _NOTIF_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail="Not a notification provider",
        )

    from app.services.notification_rule_service import NotificationRuleService

    svc = NotificationRuleService()
    deleted = await svc.delete_rule(user_id=current_user_id, rule_id=rule_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"No notification rule found with id: {rule_id}",
        )
    return JSONResponse(content={"provider": provider, "deleted": True})


@router.get("/{provider}/notification-channels")
async def list_notification_channels(
    provider: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """List available notification channels for a provider.

    For Slack, returns channels from the connected workspace.
    For Teams, returns an empty list (webhooks are user-supplied URLs).

    Args:
        provider: Notification provider key (``"slack"`` or ``"teams"``).
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON list of channel dicts (``id``, ``name``).

    Raises:
        HTTPException: 400 if provider is not a notification provider,
            502 on Slack API failure.

    """
    if provider not in _NOTIF_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail="Not a notification provider",
        )

    if provider == "teams":
        return JSONResponse(content={"provider": provider, "channels": []})

    try:
        from app.services.slack_notification_service import SlackNotificationService

        channels = await SlackNotificationService().list_channels(current_user_id)
    except Exception as exc:
        logger.exception("Failed to list Slack channels for user=%s", current_user_id)
        raise HTTPException(
            status_code=502,
            detail=f"Failed to list Slack channels: {exc!s}",
        ) from exc

    return JSONResponse(content={"provider": provider, "channels": channels})


@router.get("/{provider}/notification-config")
async def get_notification_config(
    provider: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """Return the channel configuration (briefing settings) for a provider.

    Args:
        provider: Notification provider key (``"slack"`` or ``"teams"``).
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON with the config row, or ``null`` if not yet configured.

    Raises:
        HTTPException: 400 if provider is not a notification provider.

    """
    if provider not in _NOTIF_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail="Not a notification provider",
        )

    from app.services.notification_rule_service import NotificationRuleService

    svc = NotificationRuleService()
    config = await svc.get_channel_config(current_user_id, provider)
    return JSONResponse(content={"provider": provider, "config": config})


@router.put("/{provider}/notification-config")
async def upsert_notification_config(
    provider: str,
    body: ChannelConfigRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """Create or update notification channel configuration.

    Args:
        provider: Notification provider key (``"slack"`` or ``"teams"``).
        body: Config fields — ``daily_briefing``, ``briefing_channel_id``,
            ``briefing_channel_name``, ``briefing_time_utc``.
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON with the upserted config row.

    Raises:
        HTTPException: 400 if provider is not a notification provider.

    """
    if provider not in _NOTIF_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail="Not a notification provider",
        )

    from app.services.notification_rule_service import NotificationRuleService

    svc = NotificationRuleService()
    config = await svc.upsert_channel_config(
        user_id=current_user_id,
        provider=provider,
        daily_briefing=body.daily_briefing,
        briefing_channel_id=body.briefing_channel_id,
        briefing_channel_name=body.briefing_channel_name,
        briefing_time_utc=body.briefing_time_utc,
    )
    return JSONResponse(content={"provider": provider, "config": config})


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


def _oauth_budget_cap_prompt_html(provider: str) -> HTMLResponse:
    """Return an HTML page that signals the parent to prompt for a budget cap.

    Sent after a successful ad platform OAuth when no budget cap is set.
    The frontend should show a budget cap configuration dialog before
    marking the integration as fully connected.

    Args:
        provider: Provider key (``"google_ads"`` or ``"meta_ads"``).

    Returns:
        HTMLResponse that signals ``needs_budget_cap`` via postMessage.
    """
    html = f"""<!DOCTYPE html>
<html>
<head><title>Set Budget Cap</title></head>
<body>
<p>Successfully connected to {provider}. Please set a monthly budget cap to complete setup.</p>
<script>
  if (window.opener) {{
    window.opener.postMessage({{
      type: 'oauth-callback',
      provider: '{provider}',
      success: true,
      needs_budget_cap: true
    }}, '*');
  }}
  setTimeout(function() {{ window.close(); }}, 2000);
</script>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200)


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

# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Admin integrations API endpoints.

Provides:
- GET  /admin/integrations              — list all integrations (masked keys)
- PUT  /admin/integrations/{provider}   — upsert integration with encrypted key
- DELETE /admin/integrations/{provider} — remove integration row
- POST /admin/integrations/{provider}/test — ping provider and verify key
- GET  /admin/integrations/sentry/proxy/issues            — Sentry unresolved issues
- GET  /admin/integrations/sentry/proxy/issues/{issue_id} — Sentry issue detail
- GET  /admin/integrations/posthog/proxy/events           — PostHog events
- GET  /admin/integrations/posthog/proxy/insights         — PostHog insights
- GET  /admin/integrations/github/proxy/prs               — GitHub open PRs
- GET  /admin/integrations/github/proxy/prs/{pr_number}   — GitHub PR status
- GET  /admin/integrations/stripe/proxy/summary           — Stripe sub + balance

All endpoints require admin authentication via ``require_admin`` dependency.
API keys are Fernet-encrypted at rest and masked (****...last4) in list responses.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.middleware.admin_auth import require_admin
from app.middleware.rate_limiter import limiter
from app.services.encryption import decrypt_secret, encrypt_secret
from app.services.integration_proxy import (
    IntegrationProxyService,
    _fetch_github_pr_status,
    _fetch_github_prs,
    _fetch_posthog_events,
    _fetch_posthog_insights,
    _fetch_sentry_issue_detail,
    _fetch_sentry_issues,
    _fetch_stripe_summary,
    _test_provider_connection,
)
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter()

_VALID_PROVIDERS = frozenset({"sentry", "posthog", "github", "stripe"})


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class IntegrationUpsertBody(BaseModel):
    """Request body for PUT /admin/integrations/{provider}."""

    api_key: str | None = None
    base_url: str | None = None
    config: dict[str, Any] = {}


class IntegrationResponse(BaseModel):
    """Response shape for a single integration row."""

    provider: str
    is_active: bool
    health_status: str
    key_last4: str | None
    base_url: str | None
    config: dict[str, Any]
    updated_at: str | None


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------


async def _get_integration(provider: str) -> tuple[str, dict[str, Any], str | None]:
    """Fetch, validate, and decrypt an integration row.

    Args:
        provider: Provider name to look up.

    Returns:
        Tuple of (api_key, config, base_url).

    Raises:
        HTTPException 404: Integration row not found.
        HTTPException 400: Integration is not active.
        HTTPException 400: API key is not configured on the row.
    """
    client = get_service_client()
    query = (
        client.table("admin_integrations").select("*").eq("provider", provider).limit(1)
    )
    result = await execute_async(query, op_name=f"integrations.get.{provider}")
    rows: list[dict] = result.data or []

    if not rows:
        raise HTTPException(
            status_code=404, detail=f"Integration '{provider}' not found"
        )

    row = rows[0]

    if not row.get("is_active"):
        raise HTTPException(
            status_code=400,
            detail=f"Integration '{provider}' is not active",
        )

    encrypted_key = row.get("api_key_encrypted")
    if not encrypted_key:
        raise HTTPException(
            status_code=400,
            detail=f"Integration '{provider}' has no API key configured",
        )

    api_key = decrypt_secret(encrypted_key)
    config: dict[str, Any] = row.get("config") or {}
    base_url: str | None = row.get("base_url")

    return api_key, config, base_url


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------


@router.get("/integrations")
@limiter.limit("120/minute")
async def list_integrations(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> list[dict[str, Any]]:
    """List all configured integrations with masked API keys.

    Returns each integration row with ``key_last4`` computed as
    ``****...XXXX`` (last 4 chars of the decrypted key), or ``null``
    if no key is configured.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin; confirms caller is an admin.

    Returns:
        List of integration dicts with masked keys.

    Raises:
        HTTPException 500: If Supabase query fails.
    """
    client = get_service_client()
    query = client.table("admin_integrations").select("*").order("provider")
    result = await execute_async(query, op_name="integrations.list")
    rows: list[dict] = result.data or []

    output = []
    for row in rows:
        encrypted = row.get("api_key_encrypted")
        key_last4: str | None = None
        if encrypted:
            try:
                plaintext = decrypt_secret(encrypted)
                key_last4 = f"****...{plaintext[-4:]}"
            except Exception:
                key_last4 = "****...????"

        output.append(
            {
                "provider": row.get("provider"),
                "is_active": row.get("is_active", False),
                "health_status": row.get("health_status", "unknown"),
                "key_last4": key_last4,
                "base_url": row.get("base_url"),
                "config": row.get("config") or {},
                "updated_at": row.get("updated_at"),
            }
        )

    return output


@router.put("/integrations/{provider}")
@limiter.limit("30/minute")
async def upsert_integration(
    provider: str,
    body: IntegrationUpsertBody,
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict[str, Any]:
    """Create or update an integration connection.

    Encrypts the provided API key with Fernet before storage. Sets
    ``is_active=True`` whenever a key is saved.

    Args:
        provider: One of sentry, posthog, github, stripe.
        body: Upsert body with optional api_key, base_url, config.
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin.

    Returns:
        Dict with ``provider`` and ``status`` fields.

    Raises:
        HTTPException 400: Unknown provider.
        HTTPException 500: If Supabase upsert fails.
    """
    if provider not in _VALID_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider '{provider}'. Valid: {sorted(_VALID_PROVIDERS)}",
        )

    upsert_data: dict[str, Any] = {
        "provider": provider,
        "config": body.config,
    }

    if body.base_url is not None:
        upsert_data["base_url"] = body.base_url

    if body.api_key:
        upsert_data["api_key_encrypted"] = encrypt_secret(body.api_key)
        upsert_data["is_active"] = True

    client = get_service_client()
    query = client.table("admin_integrations").upsert(
        upsert_data, on_conflict="provider"
    )
    await execute_async(query, op_name=f"integrations.upsert.{provider}")

    logger.info(
        "Integration upserted: provider=%s by admin=%s",
        provider,
        admin_user.get("email"),
    )

    return {"provider": provider, "status": "ok"}


@router.delete("/integrations/{provider}")
@limiter.limit("30/minute")
async def delete_integration(
    provider: str,
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict[str, Any]:
    """Remove an integration row from the database.

    Args:
        provider: Provider name to delete.
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin.

    Returns:
        Dict with ``provider`` and ``deleted=True``.

    Raises:
        HTTPException 500: If Supabase delete fails.
    """
    client = get_service_client()
    query = client.table("admin_integrations").delete().eq("provider", provider)
    await execute_async(query, op_name=f"integrations.delete.{provider}")

    logger.info(
        "Integration deleted: provider=%s by admin=%s",
        provider,
        admin_user.get("email"),
    )

    return {"provider": provider, "deleted": True}


@router.post("/integrations/{provider}/test")
@limiter.limit("10/minute")
async def test_connection(
    provider: str,
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict[str, Any]:
    """Ping the provider API to verify the configured key works.

    Fetches the integration row, decrypts the key, calls the provider's
    health endpoint, and updates ``health_status`` in the DB.

    Args:
        provider: Provider to test.
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin.

    Returns:
        ``{"healthy": True}`` or ``{"healthy": False, "error": str}``.

    Raises:
        HTTPException 404: Integration not found.
        HTTPException 400: No API key configured or integration inactive.
    """
    if provider not in _VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider}'")

    # Fetch row (must exist and have a key, but allow inactive for testing)
    client = get_service_client()
    query = (
        client.table("admin_integrations").select("*").eq("provider", provider).limit(1)
    )
    result = await execute_async(query, op_name=f"integrations.test.fetch.{provider}")
    rows: list[dict] = result.data or []

    if not rows:
        raise HTTPException(
            status_code=404, detail=f"Integration '{provider}' not found"
        )

    row = rows[0]
    encrypted_key = row.get("api_key_encrypted")
    if not encrypted_key:
        raise HTTPException(
            status_code=400,
            detail=f"Integration '{provider}' has no API key configured",
        )

    api_key = decrypt_secret(encrypted_key)
    config: dict[str, Any] = row.get("config") or {}

    health = await _test_provider_connection(provider, api_key, config)

    # Update health_status in DB
    new_status = "healthy" if health.get("healthy") else "unhealthy"
    update_query = (
        client.table("admin_integrations")
        .update({"health_status": new_status})
        .eq("provider", provider)
    )
    await execute_async(update_query, op_name=f"integrations.test.update.{provider}")

    return health


# ---------------------------------------------------------------------------
# Proxy endpoints — Sentry
# ---------------------------------------------------------------------------


@router.get("/integrations/sentry/proxy/issues")
@limiter.limit("60/minute")
async def proxy_sentry_issues(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
    limit: int = 25,
) -> Any:
    """Proxy: fetch unresolved Sentry issues.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin.
        limit: Max issues to return (default 25).

    Returns:
        List of transformed Sentry issue dicts.

    Raises:
        HTTPException 400: Integration inactive or key not configured.
        HTTPException 404: Integration not found.
    """
    api_key, config, _ = await _get_integration("sentry")
    params = {"limit": limit}
    return await IntegrationProxyService.call(
        provider="sentry",
        operation="get_issues",
        api_key=api_key,
        config=config,
        params=params,
        fetch_fn=_fetch_sentry_issues,
    )


@router.get("/integrations/sentry/proxy/issues/{issue_id}")
@limiter.limit("60/minute")
async def proxy_sentry_issue_detail(
    issue_id: str,
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> Any:
    """Proxy: fetch a single Sentry issue by ID.

    Args:
        issue_id: Sentry issue ID.
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin.

    Returns:
        Transformed Sentry issue detail dict.
    """
    api_key, config, _ = await _get_integration("sentry")
    params = {"issue_id": issue_id}
    return await IntegrationProxyService.call(
        provider="sentry",
        operation="get_issue_detail",
        api_key=api_key,
        config=config,
        params=params,
        fetch_fn=_fetch_sentry_issue_detail,
    )


# ---------------------------------------------------------------------------
# Proxy endpoints — PostHog
# ---------------------------------------------------------------------------


@router.get("/integrations/posthog/proxy/events")
@limiter.limit("60/minute")
async def proxy_posthog_events(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> Any:
    """Proxy: fetch PostHog events.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin.

    Returns:
        Dict with ``results`` list and ``count``.
    """
    api_key, config, base_url = await _get_integration("posthog")
    if base_url:
        config = {**config, "base_url": base_url}
    return await IntegrationProxyService.call(
        provider="posthog",
        operation="get_events",
        api_key=api_key,
        config=config,
        params={},
        fetch_fn=_fetch_posthog_events,
    )


@router.get("/integrations/posthog/proxy/insights")
@limiter.limit("60/minute")
async def proxy_posthog_insights(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> Any:
    """Proxy: fetch PostHog insights.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin.

    Returns:
        Dict with ``results`` list and ``count``.
    """
    api_key, config, base_url = await _get_integration("posthog")
    if base_url:
        config = {**config, "base_url": base_url}
    return await IntegrationProxyService.call(
        provider="posthog",
        operation="get_insights",
        api_key=api_key,
        config=config,
        params={},
        fetch_fn=_fetch_posthog_insights,
    )


# ---------------------------------------------------------------------------
# Proxy endpoints — GitHub
# ---------------------------------------------------------------------------


@router.get("/integrations/github/proxy/prs")
@limiter.limit("60/minute")
async def proxy_github_prs(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
    state: str = "open",
) -> Any:
    """Proxy: fetch GitHub pull requests.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin.
        state: PR state filter ("open", "closed", "all").

    Returns:
        List of transformed PR dicts.
    """
    api_key, config, _ = await _get_integration("github")
    params = {"state": state}
    return await IntegrationProxyService.call(
        provider="github",
        operation="get_prs",
        api_key=api_key,
        config=config,
        params=params,
        fetch_fn=_fetch_github_prs,
    )


@router.get("/integrations/github/proxy/prs/{pr_number}")
@limiter.limit("60/minute")
async def proxy_github_pr_status(
    pr_number: int,
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> Any:
    """Proxy: fetch GitHub PR status (checks + review state).

    Args:
        pr_number: Pull request number.
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin.

    Returns:
        Transformed PR status dict with checks and review_state.
    """
    api_key, config, _ = await _get_integration("github")
    params = {"pr_number": pr_number}
    return await IntegrationProxyService.call(
        provider="github",
        operation="get_pr_status",
        api_key=api_key,
        config=config,
        params=params,
        fetch_fn=_fetch_github_pr_status,
    )


# ---------------------------------------------------------------------------
# Proxy endpoints — Stripe
# ---------------------------------------------------------------------------


@router.get("/integrations/stripe/proxy/summary")
@limiter.limit("60/minute")
async def proxy_stripe_summary(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> Any:
    """Proxy: fetch Stripe subscription and balance summary.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin.

    Returns:
        Dict with active_subscriptions, total_subscriptions, and balance.
    """
    api_key, config, _ = await _get_integration("stripe")
    return await IntegrationProxyService.call(
        provider="stripe",
        operation="get_summary",
        api_key=api_key,
        config=config,
        params={},
        fetch_fn=_fetch_stripe_summary,
    )

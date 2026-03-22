"""Integration tools for the AdminAgent.

Provides 6 read-only tools for querying external service integrations:
Sentry (error tracking), PostHog (product analytics), and GitHub (pull
requests). Each tool enforces the autonomy tier before executing, retrieves
the decrypted API key from the ``admin_integrations`` table, enforces a
per-session call budget, and delegates the actual provider call to
:class:`~app.services.integration_proxy.IntegrationProxyService`.

All 6 tools are auto tier (read-only). API keys are never exposed in
responses — the proxy layer handles authentication internally.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.services.encryption import decrypt_secret
from app.services.integration_proxy import (
    IntegrationProxyService,
    _fetch_github_pr_status,
    _fetch_github_prs,
    _fetch_posthog_events,
    _fetch_posthog_insights,
    _fetch_sentry_issue_detail,
    _fetch_sentry_issues,
    check_session_budget,
)
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

# Placeholder session ID until Phase 13 adds real session tracking
_DEFAULT_SESSION_ID = "admin"


# ---------------------------------------------------------------------------
# Autonomy enforcement helper (self-contained per project pattern)
# ---------------------------------------------------------------------------


async def _check_autonomy(action_name: str) -> dict | None:
    """Query admin_agent_permissions and return a gate dict if blocked/confirm.

    Returns None when execution should proceed (auto tier or unknown).

    Args:
        action_name: The tool function name registered in admin_agent_permissions.

    Returns:
        A ``{"error": ...}`` dict if blocked, a ``{"requires_confirmation": True, ...}``
        dict if confirmation is required, or None to proceed.
    """
    try:
        client = get_service_client()
        res = (
            client.table("admin_agent_permissions")
            .select("autonomy_level")
            .eq("action_name", action_name)
            .limit(1)
            .execute()
        )
        if res.data:
            level = res.data[0].get("autonomy_level", "auto")
            if level == "blocked":
                return {
                    "error": (
                        f"{action_name} is blocked by admin configuration. "
                        "Contact a super-admin to change the autonomy level."
                    )
                }
            if level == "confirm":
                token = str(uuid.uuid4())
                return {
                    "requires_confirmation": True,
                    "confirmation_token": token,
                    "action_details": {
                        "action": action_name,
                        "risk_level": "low",
                        "description": f"Read-only integration operation: {action_name}",
                    },
                }
            # level == "auto" — proceed
    except Exception as exc:
        logger.warning(
            "Could not verify autonomy level for %s, defaulting to auto: %s",
            action_name,
            exc,
        )
    return None


# ---------------------------------------------------------------------------
# Integration config helper
# ---------------------------------------------------------------------------


async def _get_integration_config(
    provider: str,
) -> tuple[str, dict[str, Any], str | None] | dict[str, Any]:
    """Retrieve and decrypt the API key for a configured integration provider.

    Queries ``admin_integrations`` for the given provider and validates the
    row exists, is active, and has a non-null encrypted key.

    Args:
        provider: Integration provider name (e.g. "sentry", "posthog", "github").

    Returns:
        A 3-tuple ``(api_key, config, base_url)`` on success, or a
        ``{"error": str}`` dict when the integration is missing, inactive,
        or has a null API key.
    """
    try:
        client = get_service_client()
        res = (
            client.table("admin_integrations")
            .select("api_key_encrypted, config, is_active, base_url")
            .eq("provider", provider)
            .limit(1)
            .execute()
        )
        if not res.data:
            return {
                "error": (
                    f"Integration '{provider}' is not configured. "
                    "Set it up on the Integrations page first."
                )
            }

        row = res.data[0]

        if not row.get("is_active"):
            return {
                "error": (
                    f"Integration '{provider}' is disabled. "
                    "Enable it on the Integrations page first."
                )
            }

        api_key_encrypted = row.get("api_key_encrypted")
        if api_key_encrypted is None:
            return {
                "error": (
                    f"Integration '{provider}' has no API key configured. "
                    "Add an API key on the Integrations page first."
                )
            }

        api_key = decrypt_secret(api_key_encrypted)
        config: dict[str, Any] = row.get("config") or {}
        base_url: str | None = row.get("base_url")

        return (api_key, config, base_url)

    except Exception as exc:
        logger.error("_get_integration_config failed for %s: %s", provider, exc)
        return {"error": f"Failed to retrieve {provider} configuration: {exc}"}


# ---------------------------------------------------------------------------
# Tool 1: sentry_get_issues
# ---------------------------------------------------------------------------


async def sentry_get_issues(limit: int = 25) -> dict[str, Any]:
    """Fetch recent Sentry error issues for the configured project.

    Autonomy tier: auto (read-only).

    Args:
        limit: Maximum number of issues to return (default 25).

    Returns:
        List of issue dicts (id, title, culprit, count, first_seen, last_seen,
        level, status, permalink) or an ``{"error": str}`` dict if not
        configured, budget exhausted, or blocked.
    """
    gate = await _check_autonomy("sentry_get_issues")
    if gate is not None:
        return gate

    cfg = await _get_integration_config("sentry")
    if isinstance(cfg, dict):
        return cfg
    api_key, config, _base_url = cfg

    allowed = await check_session_budget(
        session_id=_DEFAULT_SESSION_ID, provider="sentry"
    )
    if not allowed:
        return {"error": "Session budget exhausted for sentry. Try again later."}

    return await IntegrationProxyService.call(
        provider="sentry",
        operation="get_issues",
        api_key=api_key,
        config=config,
        params={"limit": limit},
        fetch_fn=_fetch_sentry_issues,
    )


# ---------------------------------------------------------------------------
# Tool 2: sentry_get_issue_detail
# ---------------------------------------------------------------------------


async def sentry_get_issue_detail(issue_id: str) -> dict[str, Any]:
    """Fetch detailed info for a specific Sentry issue including metadata and tags.

    Autonomy tier: auto (read-only).

    Args:
        issue_id: The Sentry issue ID to retrieve details for.

    Returns:
        Issue detail dict (id, title, culprit, count, first_seen, last_seen,
        level, metadata, tags) or an ``{"error": str}`` dict.
    """
    gate = await _check_autonomy("sentry_get_issue_detail")
    if gate is not None:
        return gate

    cfg = await _get_integration_config("sentry")
    if isinstance(cfg, dict):
        return cfg
    api_key, config, _base_url = cfg

    allowed = await check_session_budget(
        session_id=_DEFAULT_SESSION_ID, provider="sentry"
    )
    if not allowed:
        return {"error": "Session budget exhausted for sentry. Try again later."}

    return await IntegrationProxyService.call(
        provider="sentry",
        operation="get_issue_detail",
        api_key=api_key,
        config=config,
        params={"issue_id": issue_id},
        fetch_fn=_fetch_sentry_issue_detail,
    )


# ---------------------------------------------------------------------------
# Tool 3: posthog_query_events
# ---------------------------------------------------------------------------


async def posthog_query_events(limit: int = 50) -> dict[str, Any]:
    """Fetch recent PostHog events for the configured project.

    Autonomy tier: auto (read-only).

    Args:
        limit: Maximum number of events to return (default 50).

    Returns:
        Dict with ``results`` list and ``count`` or an ``{"error": str}`` dict.
    """
    gate = await _check_autonomy("posthog_query_events")
    if gate is not None:
        return gate

    cfg = await _get_integration_config("posthog")
    if isinstance(cfg, dict):
        return cfg
    api_key, config, _base_url = cfg

    allowed = await check_session_budget(
        session_id=_DEFAULT_SESSION_ID, provider="posthog"
    )
    if not allowed:
        return {"error": "Session budget exhausted for posthog. Try again later."}

    return await IntegrationProxyService.call(
        provider="posthog",
        operation="get_events",
        api_key=api_key,
        config=config,
        params={"limit": limit},
        fetch_fn=_fetch_posthog_events,
    )


# ---------------------------------------------------------------------------
# Tool 4: posthog_get_insights
# ---------------------------------------------------------------------------


async def posthog_get_insights() -> dict[str, Any]:
    """Fetch saved PostHog insights (dashboards/queries).

    Autonomy tier: auto (read-only).

    Returns:
        Dict with ``results`` list and ``count`` or an ``{"error": str}`` dict.
    """
    gate = await _check_autonomy("posthog_get_insights")
    if gate is not None:
        return gate

    cfg = await _get_integration_config("posthog")
    if isinstance(cfg, dict):
        return cfg
    api_key, config, _base_url = cfg

    allowed = await check_session_budget(
        session_id=_DEFAULT_SESSION_ID, provider="posthog"
    )
    if not allowed:
        return {"error": "Session budget exhausted for posthog. Try again later."}

    return await IntegrationProxyService.call(
        provider="posthog",
        operation="get_insights",
        api_key=api_key,
        config=config,
        params={},
        fetch_fn=_fetch_posthog_insights,
    )


# ---------------------------------------------------------------------------
# Tool 5: github_list_prs
# ---------------------------------------------------------------------------


async def github_list_prs(state: str = "open") -> dict[str, Any]:
    """List recent GitHub pull requests.

    Autonomy tier: auto (read-only).

    Args:
        state: PR state filter — "open", "closed", or "all" (default "open").

    Returns:
        List of PR dicts (number, title, state, url, author, created_at,
        updated_at, mergeable) or an ``{"error": str}`` dict.
    """
    gate = await _check_autonomy("github_list_prs")
    if gate is not None:
        return gate

    cfg = await _get_integration_config("github")
    if isinstance(cfg, dict):
        return cfg
    api_key, config, _base_url = cfg

    allowed = await check_session_budget(
        session_id=_DEFAULT_SESSION_ID, provider="github"
    )
    if not allowed:
        return {"error": "Session budget exhausted for github. Try again later."}

    return await IntegrationProxyService.call(
        provider="github",
        operation="get_prs",
        api_key=api_key,
        config=config,
        params={"state": state},
        fetch_fn=_fetch_github_prs,
    )


# ---------------------------------------------------------------------------
# Tool 6: github_get_pr_status
# ---------------------------------------------------------------------------


async def github_get_pr_status(pr_number: int) -> dict[str, Any]:
    """Get status, checks, and review state for a specific GitHub PR.

    Autonomy tier: auto (read-only).

    Args:
        pr_number: The pull request number to query.

    Returns:
        PR status dict (number, title, state, mergeable, checks, review_state)
        or an ``{"error": str}`` dict.
    """
    gate = await _check_autonomy("github_get_pr_status")
    if gate is not None:
        return gate

    cfg = await _get_integration_config("github")
    if isinstance(cfg, dict):
        return cfg
    api_key, config, _base_url = cfg

    allowed = await check_session_budget(
        session_id=_DEFAULT_SESSION_ID, provider="github"
    )
    if not allowed:
        return {"error": "Session budget exhausted for github. Try again later."}

    return await IntegrationProxyService.call(
        provider="github",
        operation="get_pr_status",
        api_key=api_key,
        config=config,
        params={"pr_number": pr_number},
        fetch_fn=_fetch_github_pr_status,
    )

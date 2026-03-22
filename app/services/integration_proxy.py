"""Integration proxy service for Pikar-AI admin panel.

Provides a unified proxy layer for Sentry, PostHog, GitHub, and Stripe
external integrations. Handles cache-check, provider HTTP calls, cache-set,
and per-session call budget enforcement.

Usage::

    result = await IntegrationProxyService.call(
        provider="sentry",
        operation="get_issues",
        api_key="sk-...",
        config={"org_slug": "myorg", "project_slug": "myproj"},
        params={},
        fetch_fn=_fetch_sentry_issues,
    )
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from collections.abc import Callable, Coroutine
from typing import Any

import httpx

from app.services.cache import get_cache_service

logger = logging.getLogger(__name__)

# Default TTLs per provider (seconds)
_PROVIDER_TTLS: dict[str, int] = {
    "sentry": 180,
    "posthog": 180,
    "github": 180,
    "stripe": 300,
}


class IntegrationProxyService:
    """Unified proxy for all external integrations.

    All methods are static/class-level — no instance state is held.
    The proxy follows the pattern: check cache → fetch if miss → store in cache.
    """

    @staticmethod
    async def call(
        *,
        provider: str,
        operation: str,
        api_key: str,
        config: dict[str, Any],
        params: dict[str, Any],
        fetch_fn: Callable[..., Coroutine[Any, Any, Any]],
        ttl: int | None = None,
    ) -> Any:
        """Execute a provider API call with cache-check and cache-set.

        Args:
            provider: Provider name (e.g. "sentry", "posthog", "github", "stripe").
            operation: Operation name (e.g. "get_issues", "get_prs").
            api_key: Decrypted API key for the provider.
            config: Provider-specific config dict (org_slug, project_id, etc.).
            params: Call-specific query params (limit, state, etc.).
            fetch_fn: Async callable ``(api_key, config, params) -> Any`` that
                performs the actual provider HTTP/SDK call.
            ttl: Optional TTL override in seconds. Defaults to provider default.

        Returns:
            Cached or freshly-fetched provider data.
        """
        cache = get_cache_service()
        params_hash = hashlib.md5(
            json.dumps(params, sort_keys=True).encode()
        ).hexdigest()
        cache_key = f"intg_proxy:{provider}:{operation}:{params_hash}"

        # Cache check
        cache_result = await cache.get_generic(cache_key)
        if cache_result.found:
            logger.debug("Integration proxy cache HIT: %s", cache_key)
            return cache_result.value

        # Cache miss — call provider
        logger.debug("Integration proxy cache MISS: %s", cache_key)
        data = await fetch_fn(api_key, config, params)

        # Store in cache
        effective_ttl = ttl if ttl is not None else _PROVIDER_TTLS.get(provider, 180)
        await cache.set_generic(cache_key, data, ttl=effective_ttl)

        return data


async def check_session_budget(
    *,
    session_id: str,
    provider: str,
    max_calls: int = 20,
) -> bool:
    """Check and increment the per-session, per-provider call budget.

    Uses Redis INCR atomically. If the count after incrementing exceeds
    ``max_calls``, returns False (budget exhausted). Fails open (returns
    True) when Redis is unavailable.

    Args:
        session_id: The current user/admin session identifier.
        provider: Provider name to scope the budget.
        max_calls: Maximum allowed calls per session per provider (default 20).

    Returns:
        True if the call is allowed, False if budget is exhausted.
    """
    cache = get_cache_service()
    client = await cache._ensure_connection()

    if client is None:
        # Redis unavailable — fail open to avoid blocking legitimate calls
        logger.warning(
            "Redis unavailable for budget check: session=%s provider=%s — failing open",
            session_id,
            provider,
        )
        return True

    key = f"intg_budget:{session_id}:{provider}"
    count = await client.incr(key)
    if count == 1:
        # First call — set a 5-minute TTL on the budget window
        await client.expire(key, 300)

    if count > max_calls:
        logger.warning(
            "Session budget exhausted: session=%s provider=%s count=%s max=%s",
            session_id,
            provider,
            count,
            max_calls,
        )
        return False

    return True


# ---------------------------------------------------------------------------
# Provider-specific fetch functions (private helpers)
# ---------------------------------------------------------------------------


async def _fetch_sentry_issues(
    api_key: str,
    config: dict[str, Any],
    params: dict[str, Any],
) -> list[dict[str, Any]]:
    """Fetch unresolved issues from Sentry.

    Args:
        api_key: Sentry auth token.
        config: Must contain ``org_slug`` and ``project_slug``.
        params: Optional overrides (e.g. ``limit``, ``query``).

    Returns:
        List of transformed issue dicts.
    """
    org_slug = config.get("org_slug", "")
    project_slug = config.get("project_slug", "")
    limit = params.get("limit", 25)

    url = f"https://sentry.io/api/0/projects/{org_slug}/{project_slug}/issues/"
    query_params = {
        "query": params.get("query", "is:unresolved"),
        "limit": limit,
        "statsPeriod": params.get("statsPeriod", "24h"),
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = client.build_request(
            "GET",
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            params=query_params,
        )
        response = await client.send(resp)
        response.raise_for_status()
        raw = response.json()

    return [
        {
            "id": issue.get("id"),
            "title": issue.get("title"),
            "culprit": issue.get("culprit"),
            "count": issue.get("count"),
            "first_seen": issue.get("firstSeen"),
            "last_seen": issue.get("lastSeen"),
            "level": issue.get("level"),
            "status": issue.get("status"),
            "permalink": issue.get("permalink"),
        }
        for issue in raw
    ]


async def _fetch_sentry_issue_detail(
    api_key: str,
    config: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    """Fetch a single Sentry issue by ID.

    Args:
        api_key: Sentry auth token.
        config: Must contain ``org_slug``.
        params: Must contain ``issue_id``.

    Returns:
        Transformed issue detail dict.
    """
    org_slug = config.get("org_slug", "")
    issue_id = params.get("issue_id", "")

    url = f"https://sentry.io/api/0/organizations/{org_slug}/issues/{issue_id}/"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = client.build_request(
            "GET",
            url,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response = await client.send(resp)
        response.raise_for_status()
        issue = response.json()

    return {
        "id": issue.get("id"),
        "title": issue.get("title"),
        "culprit": issue.get("culprit"),
        "count": issue.get("count"),
        "first_seen": issue.get("firstSeen"),
        "last_seen": issue.get("lastSeen"),
        "level": issue.get("level"),
        "metadata": issue.get("metadata"),
        "tags": issue.get("tags"),
    }


async def _fetch_posthog_events(
    api_key: str,
    config: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    """Fetch events from PostHog.

    Args:
        api_key: PostHog personal API key.
        config: Must contain ``project_id``. Optional ``base_url``.
        params: Optional query overrides.

    Returns:
        Dict with ``results`` list and ``count``.
    """
    project_id = config.get("project_id", "")
    base_url = config.get("base_url") or "https://us.posthog.com"
    url = f"{base_url}/api/projects/{project_id}/events/"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = client.build_request(
            "GET",
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            params=params,
        )
        response = await client.send(resp)
        response.raise_for_status()
        data = response.json()

    results = data.get("results", [])
    return {
        "results": [
            {
                "event": e.get("event"),
                "timestamp": e.get("timestamp"),
                "person": e.get("person"),
                "properties": e.get("properties"),
            }
            for e in results
        ],
        "count": len(results),
    }


async def _fetch_posthog_insights(
    api_key: str,
    config: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    """Fetch insights from PostHog.

    Args:
        api_key: PostHog personal API key.
        config: Must contain ``project_id``. Optional ``base_url``.
        params: Optional query overrides.

    Returns:
        Dict with ``results`` list and ``count``.
    """
    project_id = config.get("project_id", "")
    base_url = config.get("base_url") or "https://us.posthog.com"
    url = f"{base_url}/api/projects/{project_id}/insights/"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = client.build_request(
            "GET",
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            params=params,
        )
        response = await client.send(resp)
        response.raise_for_status()
        data = response.json()

    results = data.get("results", [])
    return {
        "results": [
            {
                "id": insight.get("id"),
                "name": insight.get("name"),
                "description": insight.get("description"),
                "last_refresh": insight.get("last_refresh"),
            }
            for insight in results
        ],
        "count": len(results),
    }


def _get_prs_sync(
    token: str,
    owner: str,
    repo: str,
    state: str = "open",
) -> list[dict[str, Any]]:
    """Synchronous GitHub PR fetch via PyGithub (for asyncio.to_thread).

    Args:
        token: GitHub personal access token.
        owner: Repository owner (user or org).
        repo: Repository name.
        state: PR state filter ("open", "closed", "all").

    Returns:
        List of transformed PR dicts (max 25).
    """
    from github import Github  # type: ignore[import]

    g = Github(token)
    repository = g.get_repo(f"{owner}/{repo}")
    pulls = repository.get_pulls(state=state, sort="updated", direction="desc")

    result = []
    for pr in pulls[:25]:
        result.append(
            {
                "number": pr.number,
                "title": pr.title,
                "state": pr.state,
                "url": pr.html_url,
                "author": pr.user.login if pr.user else None,
                "created_at": pr.created_at.isoformat() if pr.created_at else None,
                "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
                "mergeable": pr.mergeable,
            }
        )
    return result


async def _fetch_github_prs(
    api_key: str,
    config: dict[str, Any],
    params: dict[str, Any],
) -> list[dict[str, Any]]:
    """Fetch open PRs from GitHub via PyGithub (async wrapper).

    Args:
        api_key: GitHub personal access token.
        config: Must contain ``owner`` and ``repo``.
        params: Optional ``state`` override.

    Returns:
        List of transformed PR dicts.
    """
    owner = config.get("owner", "")
    repo = config.get("repo", "")
    state = params.get("state", "open")
    return await asyncio.to_thread(_get_prs_sync, api_key, owner, repo, state)


def _get_pr_status_sync(
    token: str,
    owner: str,
    repo: str,
    pr_number: int,
) -> dict[str, Any]:
    """Synchronous GitHub PR status fetch via PyGithub (for asyncio.to_thread).

    Args:
        token: GitHub personal access token.
        owner: Repository owner.
        repo: Repository name.
        pr_number: Pull request number.

    Returns:
        Transformed PR status dict with checks and review state.
    """
    from github import Github  # type: ignore[import]

    g = Github(token)
    repository = g.get_repo(f"{owner}/{repo}")
    pr = repository.get_pull(pr_number)

    # Gather check runs from the latest commit
    checks: list[dict[str, Any]] = []
    try:
        commit = repository.get_commit(pr.head.sha)
        for check_run in commit.get_check_runs():
            checks.append(
                {
                    "name": check_run.name,
                    "status": check_run.status,
                    "conclusion": check_run.conclusion,
                }
            )
    except Exception:
        pass

    # Aggregate review state
    review_states = [r.state for r in pr.get_reviews()]
    review_state = review_states[-1] if review_states else "PENDING"

    return {
        "number": pr.number,
        "title": pr.title,
        "state": pr.state,
        "mergeable": pr.mergeable,
        "checks": checks,
        "review_state": review_state,
    }


async def _fetch_github_pr_status(
    api_key: str,
    config: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    """Fetch a single PR's status from GitHub (async wrapper).

    Args:
        api_key: GitHub personal access token.
        config: Must contain ``owner`` and ``repo``.
        params: Must contain ``pr_number``.

    Returns:
        Transformed PR status dict.
    """
    owner = config.get("owner", "")
    repo = config.get("repo", "")
    pr_number = int(params.get("pr_number", 0))
    return await asyncio.to_thread(_get_pr_status_sync, api_key, owner, repo, pr_number)


def _get_stripe_summary_sync(api_key: str) -> dict[str, Any]:
    """Synchronous Stripe summary fetch via SDK (for asyncio.to_thread).

    Args:
        api_key: Stripe secret key.

    Returns:
        Dict with active_subscriptions, total_subscriptions, and balance.
    """
    import stripe  # type: ignore[import]

    subscriptions = stripe.Subscription.list(api_key=api_key, limit=100)
    subs_list = list(subscriptions.auto_paging_iter())
    active_count = sum(1 for s in subs_list if s.get("status") == "active")

    balance = stripe.Balance.retrieve(api_key=api_key)

    return {
        "active_subscriptions": active_count,
        "total_subscriptions": len(subs_list),
        "balance": {
            "available": [
                {"amount": b.get("amount"), "currency": b.get("currency")}
                for b in balance.get("available", [])
            ],
            "pending": [
                {"amount": b.get("amount"), "currency": b.get("currency")}
                for b in balance.get("pending", [])
            ],
        },
    }


async def _fetch_stripe_summary(
    api_key: str,
    config: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    """Fetch Stripe subscription and balance summary (async wrapper).

    Args:
        api_key: Stripe secret key.
        config: Unused for Stripe (no extra config required).
        params: Unused for summary endpoint.

    Returns:
        Dict with active_subscriptions, total_subscriptions, and balance.
    """
    return await asyncio.to_thread(_get_stripe_summary_sync, api_key)


async def _test_provider_connection(
    provider: str,
    api_key: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Ping the provider API to verify the API key is valid.

    Args:
        provider: Provider name (sentry, posthog, github, stripe).
        api_key: Decrypted provider API key.
        config: Provider-specific config dict.

    Returns:
        ``{"healthy": True}`` on success or
        ``{"healthy": False, "error": str}`` on failure.
    """
    try:
        if provider == "sentry":
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://sentry.io/api/0/",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                resp.raise_for_status()

        elif provider == "posthog":
            project_id = config.get("project_id", "")
            base_url = config.get("base_url") or "https://us.posthog.com"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{base_url}/api/projects/{project_id}/",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                resp.raise_for_status()

        elif provider == "github":
            from github import Github  # type: ignore[import]

            def _check_github(token: str) -> None:
                g = Github(token)
                g.get_rate_limit()

            await asyncio.to_thread(_check_github, api_key)

        elif provider == "stripe":
            import stripe  # type: ignore[import]

            await asyncio.to_thread(stripe.Balance.retrieve, api_key=api_key)

        return {"healthy": True}

    except Exception as exc:
        logger.warning("Integration health check failed for %s: %s", provider, exc)
        return {"healthy": False, "error": str(exc)}

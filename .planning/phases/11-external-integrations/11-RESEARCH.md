# Phase 11: External Integrations - Research

**Researched:** 2026-03-22
**Domain:** External API proxy integrations (Sentry, PostHog, GitHub, Stripe) with Redis caching, Fernet-encrypted key management, and AdminAgent tool registration
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- `/admin/integrations` UI page for connecting/disconnecting external tools
- Each provider has: API key (Fernet encrypted), base URL (optional), config JSONB, health status
- API keys encrypted with MultiFernet (from Phase 7 `app/services/encryption.py`)
- Frontend shows only `****...last4` of keys — never the full value
- Provider-specific config fields: Sentry (org_slug, project_slug), PostHog (project_id), GitHub (owner, repo), Stripe (restricted read-only key recommended)
- Health check per integration: periodic ping to verify connectivity
- All external API calls go through FastAPI backend — never from frontend
- `app/routers/admin/integrations.py` — CRUD for integration connections + proxy endpoints
- Each proxy call: require_admin → fetch + decrypt API key → call external API → transform response → return
- Rate limited: 60 requests/minute for proxy endpoints
- Response caching in Redis (2-5 minute TTL) with per-session call budgets to prevent rate exhaustion
- **Sentry**: `httpx` calls to Sentry API (`/api/0/projects/{org}/{project}/issues/`, issue detail with stacktrace)
- **PostHog**: `httpx` calls to PostHog API (`/api/projects/{id}/events/`, `/api/projects/{id}/insights/`)
- **GitHub**: `PyGithub` library (sync, wrapped in `asyncio.to_thread()`) for PRs, checks, issues
- **Stripe**: `httpx` calls to Stripe API (read-only: subscriptions, charges, balance) — full Stripe integration in Phase 14
- New tools in `app/agents/admin/tools/integrations.py`: sentry_get_issues, sentry_get_issue_detail, posthog_query_events, posthog_get_insights, github_list_prs, github_get_pr_status
- All tools use autonomy enforcement from Phase 7
- `app/routers/admin/integrations.py` — integration CRUD + proxy
- `app/agents/admin/tools/integrations.py` — agent integration tools
- `app/services/integration_proxy.py` — shared proxy logic (decrypt, call, cache, transform)
- Update `app/routers/admin/__init__.py` to register integrations router
- Update `app/agents/admin/agent.py` to register integration tools
- `frontend/src/app/(admin)/integrations/page.tsx` — integration management page
- Provider cards with status indicators (connected/not set)
- Configure modal: API key input, base URL, provider-specific config
- Per-integration detail: health status, last check time

### Claude's Discretion
- Exact proxy response transformation shapes
- Redis cache key structure for proxy responses
- Per-session call budget implementation (Redis counter with TTL?)
- Whether to use individual proxy modules per provider or a unified proxy service
- Integration health check frequency and mechanism
- Error handling and retry logic for external API calls
- Frontend modal design for configuration

### Deferred Ideas (OUT OF SCOPE)
- CodeRabbit integration — deprioritized (Sentry, PostHog, GitHub, Stripe cover core needs)
- Stripe billing tools (issue_refund, change_user_plan) — Phase 14
- Webhook-based real-time updates from providers — polling/on-demand sufficient
- Integration marketplace for custom providers — future
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INTG-01 | Admin can connect Sentry and view error issues via server-side proxy | Sentry `/api/0/projects/{org}/{project}/issues/` endpoint, Bearer token auth with `event:read` scope; `app/services/encryption.py` decrypt pattern |
| INTG-02 | Admin can connect PostHog and view product analytics via server-side proxy | PostHog personal API key via `Authorization: Bearer phx_...` header; analytics endpoints at `https://us.posthog.com/api/projects/{project_id}/` |
| INTG-03 | Admin can connect GitHub and view PRs/issues via server-side proxy | PyGithub 2.x (not in uv.lock — must add); wrapped in `asyncio.to_thread()`; 5,000 req/hour authenticated limit |
| INTG-04 | Admin can connect Stripe and view revenue metrics via server-side proxy | `stripe>=7.0.0` already installed; `stripe.Subscription.list()`, `stripe.Charge.list()`, `stripe.Balance.retrieve()` read-only calls |
| INTG-05 | Integration API keys stored with Fernet encryption, managed from UI | `admin_integrations` table exists from Phase 7 migration; `encrypt_secret()`/`decrypt_secret()` from `app/services/encryption.py` |
| INTG-06 | API proxy responses cached in Redis (2-5 min TTL) with per-session call budgets | `get_generic`/`set_generic` on `CacheService`; Redis INCR with TTL for per-session counters |
</phase_requirements>

---

## Summary

Phase 11 adds a server-side proxy layer between the admin panel and four external services (Sentry, PostHog, GitHub, Stripe). The database schema (`admin_integrations` table) and encryption infrastructure (`app/services/encryption.py`) were built in Phase 7 and require no changes. The Stripe SDK (`stripe>=7.0.0`) and `httpx` are already installed. PyGithub, posthog, and sentry-sdk are NOT in the uv.lock and must be added to `pyproject.toml`. The `get_generic`/`set_generic` methods on `CacheService` provide the exact Redis primitive needed for proxy response caching; per-session call budgets use Redis INCR + EXPIRE via the existing `set_nx` and a bare Redis client pattern.

The implementation follows a unified proxy service pattern (`app/services/integration_proxy.py`) that all four providers share: fetch + decrypt key from `admin_integrations`, check Redis cache, call external API via httpx or PyGithub, cache response, return. The AdminAgent gets six new tools in `app/agents/admin/tools/integrations.py` following the exact `_check_autonomy()` pattern established in phases 8-10. The frontend page follows the `'use client'` polling pattern from monitoring and analytics pages with provider cards, a configure modal, and a "Test Connection" button.

The critical research flag from STATE.md — "Verify current rate limits and pagination behavior for Sentry, PostHog, GitHub APIs before implementing proxy tools" — is now resolved: Sentry has no published hard limit but communicates limits via 429 + Retry-After; PostHog analytics endpoints are 240/min; GitHub authenticated requests are 5,000/hour. The 2-5 minute Redis cache and per-session budgets are sufficient protection at admin-panel scale.

**Primary recommendation:** Use a unified `IntegrationProxyService` class in `app/services/integration_proxy.py` (one instance per provider call, not a singleton) that handles decrypt → cache-check → HTTP call → cache-set → return. This keeps each provider's logic clean while sharing the caching and error-handling boilerplate.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | `>=0.27.0,<1.0.0` (installed) | Async HTTP client for Sentry, PostHog, Stripe calls | Already in pyproject.toml; consistent with health_checker.py pattern |
| stripe | `>=7.0.0,<8.0.0` (installed) | Stripe API (subscriptions, charges, balance) | Already installed; async-compatible via `asyncio.to_thread()` for sync calls or `stripe.StripeClient` async methods |
| cryptography | `>=46.0.3` (installed) | Fernet/MultiFernet for API key encryption | Already installed; `encrypt_secret()`/`decrypt_secret()` in `app/services/encryption.py` |
| redis | `>=5.0.0,<6.0.0` (installed) | Response caching + per-session call budgets | CacheService with `get_generic`/`set_generic`/`set_nx` already supports proxy caching pattern |

### Must Add
| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| PyGithub | `~=2.8.1` | GitHub PRs, issues, checks via typed SDK | Sync SDK, must wrap in `asyncio.to_thread()`; only option for typed GitHub access per Phase 7 research |
| posthog | `~=7.9.12` | PostHog Python client OR plain httpx calls | posthog SDK is primarily for event capture; for querying analytics data, httpx to PostHog REST API is cleaner |
| sentry-sdk | `~=2.53.0` | Sentry SDK for project/issue queries | Can use SDK or plain httpx; httpx is simpler for the proxy pattern |

**Note on posthog and sentry-sdk:** The CONTEXT.md specifies using `httpx` for Sentry and PostHog calls (not their SDKs). This means `posthog` and `sentry-sdk` packages may not be needed if all calls go through `httpx`. The project RESEARCH SUMMARY listed them as needed packages for the "API proxy tools," but the CONTEXT.md decisions clarify it's plain httpx. Only **PyGithub** is truly required as a new dependency. Re-confirm during planning: if httpx-only for Sentry/PostHog, do not add posthog and sentry-sdk to pyproject.toml.

### Installation (only what's missing)
```bash
# Only PyGithub needs adding — verify posthog/sentry-sdk before adding
uv add "PyGithub~=2.8.1"
```

---

## Architecture Patterns

### Existing Infrastructure to Reuse

**admin_integrations table (Phase 7 migration — confirmed exists):**
```sql
CREATE TABLE IF NOT EXISTS admin_integrations (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider          text NOT NULL UNIQUE,
    api_key_encrypted text,
    base_url          text,
    config            jsonb NOT NULL DEFAULT '{}',
    is_active         boolean NOT NULL DEFAULT false,
    health_status     text NOT NULL DEFAULT 'unknown',
    updated_by        uuid REFERENCES auth.users(id),
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);
```

Provider-specific config JSONB shapes:
- **Sentry**: `{"org_slug": "...", "project_slug": "..."}`
- **PostHog**: `{"project_id": "12345"}`
- **GitHub**: `{"owner": "...", "repo": "..."}`
- **Stripe**: `{}` (no extra config — key is the only required field)

**Encryption service (confirmed working):**
```python
# Source: app/services/encryption.py
from app.services.encryption import encrypt_secret, decrypt_secret

# Store: api_key_encrypted = encrypt_secret(plaintext_key)
# Retrieve: plaintext_key = decrypt_secret(row["api_key_encrypted"])
```

**CacheService generic methods (confirmed in cache.py):**
```python
# Source: app/services/cache.py
from app.services.cache import get_cache_service

cache = get_cache_service()

# Store proxy response (TTL in seconds)
await cache.set_generic(key, value, ttl=180)  # 3 min TTL

# Retrieve cached response
result = await cache.get_generic(key)
if result.found:
    return result.value
```

**Per-session call budget using Redis INCR:**
```python
# Pattern: Redis INCR + EXPIRE for session call counting
# set_nx establishes the counter if it doesn't exist (atomic)
budget_key = f"intg_budget:{session_id}:{provider}"
counter_key = f"intg_calls:{session_id}:{provider}"
# Use bare Redis client from CacheService for INCR
client = await cache._ensure_connection()
count = await client.incr(counter_key)
if count == 1:
    await client.expire(counter_key, 300)  # 5-min window
if count > MAX_CALLS_PER_SESSION:
    return {"error": "Session call budget exhausted for this provider"}
```

### Recommended Project Structure (new files)
```
app/
├── routers/admin/
│   └── integrations.py      # CRUD endpoints + proxy endpoints
├── agents/admin/tools/
│   └── integrations.py      # 6 AdminAgent tools
└── services/
    └── integration_proxy.py # Shared decrypt→cache→call→return logic

frontend/src/
└── app/(admin)/
    └── integrations/
        └── page.tsx          # Provider cards + configure modal
```

### Pattern 1: Integration Proxy Service
**What:** A service class that wraps the decrypt → cache-check → HTTP call → cache-set pipeline for all providers.
**When to use:** Every proxy endpoint and every AdminAgent tool calls this.

```python
# Source: established pattern from app/services/health_checker.py + app/services/cache.py
from app.services.integration_proxy import IntegrationProxyService

async def _call_sentry_issues(
    org_slug: str, project_slug: str, api_key: str
) -> dict:
    """Direct httpx call to Sentry — called by IntegrationProxyService."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"https://sentry.io/api/0/projects/{org_slug}/{project_slug}/issues/",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"query": "is:unresolved", "limit": 25},
        )
        resp.raise_for_status()
        return resp.json()
```

### Pattern 2: AdminAgent Tool (follows existing analytics.py pattern exactly)
**What:** Tool function with `_check_autonomy()` guard, fetch integration row, decrypt key, call proxy service.
**When to use:** All 6 integration tools in `app/agents/admin/tools/integrations.py`.

```python
# Source: app/agents/admin/tools/analytics.py pattern
async def sentry_get_issues(limit: int = 25) -> dict[str, Any]:
    """Fetch recent Sentry error issues for the configured project.

    Autonomy tier: auto (read-only).
    """
    gate = await _check_autonomy("sentry_get_issues")
    if gate is not None:
        return gate

    # Fetch + decrypt from admin_integrations
    client = get_service_client()
    result = (
        client.table("admin_integrations")
        .select("api_key_encrypted, config, is_active")
        .eq("provider", "sentry")
        .limit(1)
        .execute()
    )
    if not result.data or not result.data[0].get("is_active"):
        return {"error": "Sentry integration not configured or inactive"}

    row = result.data[0]
    api_key = decrypt_secret(row["api_key_encrypted"])
    config = row.get("config", {})

    # Call proxy (handles caching)
    return await IntegrationProxyService.call(
        provider="sentry",
        operation="get_issues",
        api_key=api_key,
        config=config,
        params={"limit": limit},
    )
```

### Pattern 3: FastAPI Router — CRUD + Proxy Endpoints
**What:** Router with CRUD for integration management and proxy GET endpoints.
**When to use:** `app/routers/admin/integrations.py`.

```python
# Source: established pattern from app/routers/admin/monitoring.py + users.py
@router.put("/integrations/{provider}")
@limiter.limit("30/minute")
async def upsert_integration(
    provider: str,
    request: Request,
    body: IntegrationUpsertBody,
    admin_user: dict = Depends(require_admin),
) -> dict:
    """Create or update an integration. Encrypts the API key before storing."""
    ...

@router.get("/integrations/{provider}/proxy/issues")
@limiter.limit("60/minute")
async def proxy_sentry_issues(
    request: Request,
    admin_user: dict = Depends(require_admin),
) -> dict:
    """Server-side proxy — fetches Sentry issues for the admin."""
    ...
```

### Pattern 4: Frontend Provider Cards Page
**What:** `'use client'` page following monitoring/analytics page pattern — useState, useCallback, useEffect polling. Provider cards with connected/disconnected badges, configure modal, test-connection button.
**When to use:** `frontend/src/app/(admin)/integrations/page.tsx`.

```typescript
// Source: pattern from frontend/src/app/(admin)/monitoring/page.tsx
// and frontend/src/app/(admin)/analytics/page.tsx
'use client';

import { useCallback, useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Pattern: fetch session → call /admin/integrations → render provider cards
// No polling needed (integrations don't change frequently — user-triggered refresh)
```

### Anti-Patterns to Avoid
- **Decrypting API keys in the router and returning them to the client:** The key must be decrypted in the backend service layer only, never in the response payload. Show `****...last4` on the frontend.
- **Per-call PyGithub instantiation inside the event loop:** PyGithub's `Github(token)` constructor is cheap but all method calls are sync I/O. Every PyGithub call must go through `asyncio.to_thread()`.
- **Storing per-session budgets in Python process memory:** Use Redis INCR + EXPIRE. Process restarts or multiple Cloud Run instances would lose in-memory counters.
- **Single-provider proxy modules (sentry_proxy.py, posthog_proxy.py, etc.):** A unified `IntegrationProxyService` with a `provider` parameter is cleaner and avoids duplicating cache logic.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| API key encryption | Custom AES/base64 | `encrypt_secret()`/`decrypt_secret()` in `app/services/encryption.py` | Already built in Phase 7, supports key rotation via MultiFernet |
| HTTP client with timeout | raw urllib | `httpx.AsyncClient(timeout=10.0)` | Already installed, async, handles connection pooling |
| Response caching | Dict in module scope | `cache.get_generic(key)` / `cache.set_generic(key, value, ttl=N)` | Circuit breaker, connection pooling, TTL management — all built |
| Rate limit tracking | Custom token bucket | Redis INCR + EXPIRE | Atomic, survives restarts, works across Cloud Run instances |
| GitHub API types | Raw GitHub REST API JSON | PyGithub 2.x `repo.get_pulls()`, `pr.get_commits()` | Typed objects, pagination, auth handling built in |
| Masked key display | Custom masking | Frontend: `****...${key.slice(-4)}` | Simple slice — no library needed, enforce server-side (never send full key) |

---

## Common Pitfalls

### Pitfall 1: PostHog events endpoint is DEPRECATED
**What goes wrong:** Calling `/api/projects/{id}/events/` returns data but is marked deprecated in PostHog docs (2025). The `/api/queries` endpoint is the current approach.
**Why it happens:** CONTEXT.md references the old events endpoint path.
**How to avoid:** The CONTEXT.md decision is locked, so implement as specified. Flag during planning that the events endpoint still works but PostHog recommends migrating to the Query API. The current endpoint returns paginated events — acceptable for admin use.
**Warning signs:** PostHog returns deprecation warnings in response headers or body.

### Pitfall 2: PyGithub sync calls blocking the event loop
**What goes wrong:** Calling `repo.get_pulls()` directly in an async FastAPI handler blocks all other requests for the duration of the GitHub API call (typically 100-500ms).
**Why it happens:** PyGithub is synchronous; Python's event loop is single-threaded.
**How to avoid:** Always wrap: `prs = await asyncio.to_thread(repo.get_pulls, state="open", sort="updated")`. This is the same pattern used in `app/agents/admin/tools/users.py` for Supabase Auth Admin calls.
**Warning signs:** FastAPI 504 timeouts under concurrent load; response time spikes.

### Pitfall 3: Cache key collisions between sessions/providers
**What goes wrong:** Two admins in different sessions get each other's cached responses, or a stale cached response for one provider is served for another.
**Why it happens:** Cache keys not namespaced by provider + operation + params.
**How to avoid:** Key structure: `intg_proxy:{provider}:{operation}:{hash(params)}`. Do NOT include session_id in proxy cache key (proxy responses are not session-specific — that's the point of caching).
**Warning signs:** Admin sees Sentry data when requesting PostHog, or stale data after re-configuring an integration.

### Pitfall 4: Fernet InvalidToken when api_key_encrypted is NULL
**What goes wrong:** Calling `decrypt_secret(None)` raises `AttributeError` on `None.encode()`.
**Why it happens:** `admin_integrations.api_key_encrypted` is nullable — a provider row can exist with no key set yet.
**How to avoid:** Guard before decrypting: `if not row.get("api_key_encrypted"): return {"error": "API key not configured"}`.
**Warning signs:** 500 errors on proxy calls for newly created integration rows.

### Pitfall 5: Stripe SDK sync calls without asyncio.to_thread
**What goes wrong:** `stripe.Subscription.list(api_key=key)` is synchronous and blocks the event loop.
**Why it happens:** The Stripe Python SDK v7.x has async support via `stripe.StripeClient` with async HTTP, but the module-level `stripe.Subscription.list()` interface is sync.
**How to avoid:** Use `await asyncio.to_thread(stripe.Subscription.list, api_key=api_key, limit=10)` OR use `stripe.StripeClient` with httpx async transport. The `asyncio.to_thread` pattern is simpler and consistent with PyGithub usage in this codebase.
**Warning signs:** FastAPI event loop blocked; all requests stall during Stripe calls.

### Pitfall 6: Per-session call budget race condition
**What goes wrong:** Two concurrent requests from the same session both check the counter before either increments it, both see count=0, and both proceed past the budget.
**Why it happens:** Check-then-increment is not atomic.
**How to avoid:** Use Redis INCR first (atomic), then check the returned value: if returned value > MAX, reject. This is the correct Redis counter pattern — increment atomically, then decide.
**Warning signs:** Budget can be exceeded by at most N-1 concurrent requests (acceptable; defense-in-depth).

### Pitfall 7: Health check endpoint choice per provider
**What goes wrong:** Using a data endpoint (e.g., `/api/0/projects/{org}/{project}/issues/`) for health checks — this counts against rate limits and may return data unnecessarily.
**Why it happens:** No dedicated health/ping endpoint exists for Sentry.
**How to avoid:** For health checks, use lightweight endpoints: Sentry: `/api/0/` (returns API info); PostHog: `/api/projects/{id}/` (project metadata, cheap); GitHub: `repo.get_topics()` or check `g.get_rate_limit()`; Stripe: `stripe.Balance.retrieve()` (fastest read endpoint).
**Warning signs:** Integration health check consumes proxy response cache TTL unnecessarily.

---

## Code Examples

### Sentry API: List Issues
```python
# Source: https://docs.sentry.io/api/events/list-a-projects-issues/
# Endpoint: GET /api/0/projects/{org_slug}/{project_slug}/issues/
# Auth: Authorization: Bearer {sentry_auth_token}  (scope: event:read)
async with httpx.AsyncClient(timeout=10.0) as client:
    resp = await client.get(
        f"https://sentry.io/api/0/projects/{org_slug}/{project_slug}/issues/",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"query": "is:unresolved", "limit": 25, "statsPeriod": "24h"},
    )
    resp.raise_for_status()
    issues = resp.json()  # List of issue dicts
```

### Sentry API: Get Issue Detail
```python
# Source: https://docs.sentry.io/api/events/retrieve-an-issue/
# Endpoint: GET /api/0/organizations/{org_slug}/issues/{issue_id}/
# Auth: Authorization: Bearer {sentry_auth_token}  (scope: event:read)
async with httpx.AsyncClient(timeout=10.0) as client:
    resp = await client.get(
        f"https://sentry.io/api/0/organizations/{org_slug}/issues/{issue_id}/",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    resp.raise_for_status()
    issue = resp.json()  # Issue detail with activity, stats, tags
```

### PostHog API: Query Events (via deprecated events endpoint — as locked in CONTEXT.md)
```python
# Source: https://posthog.com/docs/api
# Auth: Authorization: Bearer {personal_api_key}
# Base URL: https://us.posthog.com (US Cloud) or https://eu.posthog.com (EU Cloud)
# Rate limit: 240/minute for analytics endpoints
async with httpx.AsyncClient(timeout=10.0) as client:
    resp = await client.get(
        f"{base_url}/api/projects/{project_id}/events/",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"limit": 100, "orderBy": ["-timestamp"]},
    )
    resp.raise_for_status()
    events = resp.json()  # {"results": [...], "next": "...", "count": N}
```

### PostHog API: Get Insights
```python
# Source: https://posthog.com/docs/api/insights
# Auth: Authorization: Bearer {personal_api_key}
async with httpx.AsyncClient(timeout=10.0) as client:
    resp = await client.get(
        f"{base_url}/api/projects/{project_id}/insights/",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"limit": 20},
    )
    resp.raise_for_status()
    insights = resp.json()  # {"results": [...], "count": N}
```

### GitHub via PyGithub + asyncio.to_thread
```python
# Source: established pattern from app/agents/admin/tools/users.py
# PyGithub 2.x sync API wrapped in asyncio.to_thread
import asyncio
from github import Github

def _get_prs_sync(token: str, owner: str, repo: str, state: str = "open") -> list[dict]:
    """Synchronous PyGithub call — run via asyncio.to_thread."""
    g = Github(token)
    repository = g.get_repo(f"{owner}/{repo}")
    pulls = repository.get_pulls(state=state, sort="updated", direction="desc")
    return [
        {
            "number": pr.number,
            "title": pr.title,
            "state": pr.state,
            "url": pr.html_url,
            "author": pr.user.login,
            "created_at": pr.created_at.isoformat(),
            "updated_at": pr.updated_at.isoformat(),
            "mergeable": pr.mergeable,
        }
        for pr in list(pulls[:25])  # Paginated; limit to 25
    ]

# In async context:
prs = await asyncio.to_thread(_get_prs_sync, api_key, owner, repo)
```

### Stripe Read-Only (async via asyncio.to_thread — stripe SDK is sync)
```python
# Source: https://docs.stripe.com/api/subscriptions?lang=python
# stripe>=7.0.0 is already installed in pyproject.toml
import stripe

def _get_stripe_summary_sync(api_key: str) -> dict:
    """Synchronous Stripe calls — run via asyncio.to_thread."""
    subscriptions = stripe.Subscription.list(api_key=api_key, limit=100)
    balance = stripe.Balance.retrieve(api_key=api_key)
    return {
        "active_subscriptions": sum(
            1 for s in subscriptions.data if s.status == "active"
        ),
        "balance": {
            "available": balance.available,
            "pending": balance.pending,
        },
    }

# In async context:
summary = await asyncio.to_thread(_get_stripe_summary_sync, api_key)
```

### Redis Proxy Cache Pattern
```python
# Source: app/services/cache.py get_generic / set_generic methods
from app.services.cache import get_cache_service

async def cached_proxy_call(
    provider: str, operation: str, params_hash: str,
    ttl_seconds: int, fetch_fn
) -> dict:
    cache = get_cache_service()
    key = f"intg_proxy:{provider}:{operation}:{params_hash}"

    result = await cache.get_generic(key)
    if result.found:
        return result.value

    data = await fetch_fn()
    await cache.set_generic(key, data, ttl=ttl_seconds)
    return data
```

### Per-Session Call Budget (Redis INCR — atomic)
```python
# Source: app/services/cache.py _ensure_connection() pattern
async def check_session_budget(
    session_id: str, provider: str, max_calls: int = 20
) -> bool:
    """Returns True if call is allowed, False if budget exhausted."""
    cache = get_cache_service()
    client = await cache._ensure_connection()
    if not client:
        return True  # Redis unavailable — allow through (fail open)

    key = f"intg_budget:{session_id}:{provider}"
    count = await client.incr(key)
    if count == 1:
        await client.expire(key, 300)  # 5-minute window
    return count <= max_calls
```

### Frontend Provider Card Pattern
```typescript
// Source: pattern from frontend/src/app/(admin)/monitoring/page.tsx
// Provider list + configure modal — follows existing 'use client' + fetch pattern
interface IntegrationStatus {
  provider: string;
  is_active: boolean;
  health_status: string;
  last_checked?: string;
  key_last4?: string;  // Backend sends "****...XXXX", never full key
}

// CRUD endpoint: PUT /admin/integrations/{provider}
// Health check: POST /admin/integrations/{provider}/test
// Proxy endpoints: GET /admin/integrations/{provider}/proxy/{operation}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PostHog `/api/projects/{id}/events/` | `/api/queries` endpoint (HogQL) | PostHog 2024-2025 | Events endpoint still works but deprecated; Query API supports SQL-like HogQL queries |
| Sentry SDK for server-side proxy | Plain httpx calls | N/A | httpx is simpler for proxy use-case; SDK adds overhead not needed for read-only admin queries |
| Stripe sync `stripe.Subscription.list()` | `stripe.StripeClient` async | stripe-python v8+ (not yet) | v7.x (installed) is sync; use `asyncio.to_thread` |

**Confirmed installed (no additions needed):** httpx, stripe, redis, cryptography
**Must add:** PyGithub~=2.8.1
**Likely not needed (httpx instead):** posthog, sentry-sdk packages

---

## Open Questions

1. **posthog and sentry-sdk packages: add or skip?**
   - What we know: CONTEXT.md specifies httpx calls for both Sentry and PostHog (not SDK). RESEARCH SUMMARY listed them as needed.
   - What's unclear: Whether any SDK-specific features (retry, DSN parsing, etc.) are worth the dependency.
   - Recommendation: Use plain httpx for both Sentry and PostHog. Do NOT add posthog or sentry-sdk packages. PyGithub is the only new dependency. This simplifies the dependency tree and avoids SDK-specific configuration concerns.

2. **PostHog base URL — US or EU cloud?**
   - What we know: PostHog API uses `https://us.posthog.com` (US) or `https://eu.posthog.com` (EU). The `base_url` field in `admin_integrations` is optional and defaults to null.
   - What's unclear: The admin's PostHog deployment region.
   - Recommendation: Default `base_url` to `https://us.posthog.com` if null; allow admin to override via the configure modal's base URL field. This is already supported by the `base_url` column in `admin_integrations`.

3. **Should proxy endpoints be GET routes or a single POST "query" route?**
   - What we know: CONTEXT.md says "proxy endpoints" — each provider has separate proxy routes.
   - What's unclear: Whether `GET /admin/integrations/sentry/proxy/issues` vs `POST /admin/integrations/sentry/proxy` with a body is cleaner.
   - Recommendation: Use discrete GET routes per operation (`/proxy/issues`, `/proxy/issue/{id}`, `/proxy/prs`, etc.). Simpler frontend fetch calls, more REST-compliant, easier to rate-limit per operation.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/unit/admin/ -x` |
| Full suite command | `uv run pytest tests/unit/admin/ tests/unit/test_integration_tools.py -x` |
| Frontend | vitest (from `.planning/config.json` preferences) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTG-01 | sentry_get_issues returns issue list when integration active | unit | `uv run pytest tests/unit/admin/test_integration_tools_admin.py::test_sentry_get_issues_returns_issues -x` | ❌ Wave 0 |
| INTG-01 | sentry_get_issues returns error when integration inactive | unit | `uv run pytest tests/unit/admin/test_integration_tools_admin.py::test_sentry_get_issues_inactive -x` | ❌ Wave 0 |
| INTG-02 | posthog_query_events returns events from proxy | unit | `uv run pytest tests/unit/admin/test_integration_tools_admin.py::test_posthog_query_events -x` | ❌ Wave 0 |
| INTG-03 | github_list_prs calls asyncio.to_thread with PyGithub | unit | `uv run pytest tests/unit/admin/test_integration_tools_admin.py::test_github_list_prs_uses_to_thread -x` | ❌ Wave 0 |
| INTG-04 | Stripe proxy returns subscription + balance data | unit | `uv run pytest tests/unit/admin/test_integration_tools_admin.py::test_stripe_proxy_read_only -x` | ❌ Wave 0 |
| INTG-05 | PUT /admin/integrations/sentry stores encrypted key | unit | `uv run pytest tests/unit/admin/test_integrations_router.py::test_upsert_integration_encrypts_key -x` | ❌ Wave 0 |
| INTG-05 | GET /admin/integrations returns masked keys (last4 only) | unit | `uv run pytest tests/unit/admin/test_integrations_router.py::test_list_integrations_masks_keys -x` | ❌ Wave 0 |
| INTG-06 | Proxy call returns cached response on second call | unit | `uv run pytest tests/unit/admin/test_integration_proxy.py::test_proxy_uses_cache -x` | ❌ Wave 0 |
| INTG-06 | Session budget blocks call when limit exceeded | unit | `uv run pytest tests/unit/admin/test_integration_proxy.py::test_session_budget_exhausted -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/admin/ -x`
- **Per wave merge:** `uv run pytest tests/unit/admin/ -x`
- **Phase gate:** Full admin test suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/admin/test_integration_tools_admin.py` — covers INTG-01 through INTG-04 (agent tools)
- [ ] `tests/unit/admin/test_integrations_router.py` — covers INTG-05 (CRUD endpoints, key masking)
- [ ] `tests/unit/admin/test_integration_proxy.py` — covers INTG-06 (cache hit, session budget)

---

## Sources

### Primary (HIGH confidence)
- Sentry API docs — `GET /api/0/projects/{org}/{project}/issues/` endpoint, Bearer token auth, `event:read` scope: https://docs.sentry.io/api/events/list-a-projects-issues/
- Sentry API docs — `GET /api/0/organizations/{org}/issues/{issue_id}/` detail endpoint: https://docs.sentry.io/api/events/retrieve-an-issue/
- PostHog API docs — authentication (personal API key Bearer), rate limits (240/min analytics, 480/min CRUD), base URLs (us.posthog.com / eu.posthog.com): https://posthog.com/docs/api
- GitHub REST API rate limits — 5,000 req/hour authenticated, response headers `x-ratelimit-remaining`, `x-ratelimit-reset`: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- Stripe Python SDK — `stripe.Subscription.list()`, `stripe.Balance.retrieve()` read-only endpoints: https://docs.stripe.com/api/subscriptions?lang=python
- Phase 7 migration SQL — `admin_integrations` table schema, `api_key_encrypted` nullable text, `config` JSONB: `supabase/migrations/20260321300000_admin_panel_foundation.sql`
- `app/services/encryption.py` — `encrypt_secret()` / `decrypt_secret()` with MultiFernet: confirmed in codebase
- `app/services/cache.py` — `get_generic()`, `set_generic()`, `set_nx()`, `_ensure_connection()` for INCR: confirmed in codebase
- `pyproject.toml` — stripe (`>=7.0.0,<8.0.0`) and httpx (`>=0.27.0,<1.0.0`) already installed; PyGithub, posthog, sentry-sdk NOT in dependencies

### Secondary (MEDIUM confidence)
- Sentry rate limits page (rate limits communicated via 429 + Retry-After; no hard published req/hour for API auth tokens): https://docs.sentry.io/api/ratelimits/
- PostHog events endpoint (deprecated per docs, recommended to use /api/queries): https://posthog.com/docs/api/events
- PyGithub 2.x RateLimit docs (sync SDK, asyncio.to_thread pattern consistent with project's users.py pattern): https://pygithub.readthedocs.io/en/latest/github_objects/RateLimit.html

### Tertiary (LOW confidence — verify during implementation)
- Stripe async support: stripe-python v8 may have async methods; v7 (installed) is sync only — verify before choosing asyncio.to_thread vs StripeClient

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — packages verified against uv.lock and pyproject.toml; API endpoints verified against official docs
- Architecture: HIGH — all patterns derived from existing Phase 7-10 implementations in codebase
- Pitfalls: HIGH — most derived from actual code patterns (Fernet NULL guard, asyncio.to_thread for sync SDKs verified in users.py)
- Provider API details: MEDIUM-HIGH — Sentry and GitHub endpoints confirmed via official docs; PostHog confirmed via API overview; Stripe confirmed via official Python SDK reference

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable APIs; rate limits may change but are not phase-critical given 2-5 min cache)

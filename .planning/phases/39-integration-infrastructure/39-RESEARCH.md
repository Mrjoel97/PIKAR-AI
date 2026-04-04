# Phase 39: Integration Infrastructure - Research

**Researched:** 2026-04-04
**Domain:** Integration credential management, OAuth lifecycle, webhook systems, sync state tracking
**Confidence:** HIGH

## Summary

Phase 39 builds the foundational infrastructure that all subsequent integration phases (40-47) depend on. The codebase already contains mature, reusable patterns for every major concern: MultiFernet encryption (`app/services/encryption.py`), HMAC-SHA256 webhook verification (`app/routers/webhooks.py`), circuit breaker (`app/services/cache.py`), BaseService with RLS-aware Supabase access (`app/services/base_service.py`), OAuth flow with PKCE (`app/social/connector.py`), and ai_jobs queue processing via the worker loop (`app/workflows/worker.py`). The research findings confirm that this phase is primarily a *composition and generalization* exercise -- taking existing proven patterns and building a provider-agnostic layer on top.

The frontend configuration page (`frontend/src/app/dashboard/configuration/page.tsx`) already has a section-based layout with SectionHeader components, social platform cards, MCP tool cards, and Google Workspace status -- adding a new "External Integrations" section follows the established pattern exactly. The backend already has 31 routers mounted in `fast_api_app.py`, and adding a new integrations router follows the exact same import + include pattern.

**Primary recommendation:** Reuse existing patterns verbatim -- do not invent new abstractions. The `encrypt_secret`/`decrypt_secret` API, `BaseService` inheritance, HMAC verification, PKCE OAuth flow, and `ai_jobs` queue pattern are all production-proven and should be adopted without modification.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Credential storage**: New `integration_credentials` table in Supabase with Fernet-encrypted tokens, RLS `auth.uid() = user_id`
- **Columns**: `id`, `user_id`, `provider` (enum), `access_token` (encrypted), `refresh_token` (encrypted), `token_type`, `scopes`, `expires_at`, `account_name`, `created_at`, `updated_at`
- **OAuth flow**: Backend FastAPI endpoints `GET /integrations/{provider}/authorize` and `GET /integrations/{provider}/callback`; frontend opens popup, listens for close, refreshes status
- **Token refresh**: `IntegrationManager` service with `asyncio.Lock` per `(user_id, provider)`, proactive refresh at <5 min remaining, retry-after-refresh on 401
- **Disconnect**: Stop sync only -- tokens deleted but synced data preserved
- **Sync state**: New `integration_sync_state` table with cursor, error_count, backoff_until, RLS per user
- **Inbound webhooks**: Single endpoint `POST /webhooks/inbound/{provider}`, HMAC-SHA256 verification, idempotency via `webhook_events` table with UNIQUE on `(provider, event_id)`, `INSERT ... ON CONFLICT DO NOTHING`
- **Outbound webhooks**: `webhook_endpoints` + `webhook_deliveries` tables, HMAC-signed `X-Pikar-Signature` header, 5-attempt exponential backoff (1s, 5s, 30s, 5min, 30min), dead letter after 5 failures, per-endpoint circuit breaker (10 consecutive failures = auto-disable)
- **Delivery worker**: Reuses existing `workflow_trigger_service` scheduler pattern via worker loop, NOT a new worker process
- **Event catalog**: Hardcoded in code, not DB; events: `task.created`, `task.updated`, `workflow.started`, `workflow.completed`, `approval.pending`, `approval.decided`, `initiative.phase_changed`, `contact.synced`, `invoice.created`
- **Provider registry**: Simple Python dict in `app/config/integration_providers.py` mapping provider key to `ProviderConfig` dataclass; NOT a database table
- **Frontend**: Category card layout (CRM & Sales, Finance & Commerce, Productivity, Communication, Analytics), 3-state status (green/gray/red dot), connect via popup
- **Health check endpoint**: `GET /integrations/status` returns per-provider status for authenticated user

### Claude's Discretion
- Exact Supabase migration SQL (column types, indexes, constraints)
- Webhook delivery worker scheduling interval
- Provider config dataclass field details beyond those specified
- Frontend card component styling (follows existing design system)
- Error message wording for OAuth failures
- Rate limiting on webhook delivery (per-endpoint or global)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | Integration credential manager stores OAuth tokens encrypted (Fernet) per user per provider | Existing `encrypt_secret`/`decrypt_secret` in `app/services/encryption.py`; new `integration_credentials` table; `IntegrationManager` service extending `BaseService` |
| INFRA-02 | OAuth token refresh manager handles concurrent refresh with async locking | `asyncio.Lock` per `(user_id, provider)` in `IntegrationManager`; proactive refresh pattern; existing PKCE OAuth flow in `app/social/connector.py` as reference |
| INFRA-03 | Integration health check endpoint reports status per connected service | New `GET /integrations/status` endpoint reading `integration_credentials` + `integration_sync_state` tables |
| INFRA-04 | Webhook inbound receiver with HMAC-SHA256 verification and idempotency | Generalization of existing `app/routers/webhooks.py` LinkedIn/Resend patterns; new `webhook_events` table with UNIQUE constraint |
| INFRA-05 | Webhook outbound delivery queue with exponential backoff retry (5 attempts) | `webhook_deliveries` table + delivery worker function called from existing worker loop via `ai_jobs` queue pattern |
| INFRA-06 | Webhook dead letter queue with per-endpoint circuit breaker | Dead letter status in `webhook_deliveries`; circuit breaker pattern adapted from `app/services/cache.py` applied per-endpoint |
| INFRA-07 | Integration sync state tracking (cursor, last sync, error count per user per provider) | New `integration_sync_state` table with JSONB cursor; service methods in `IntegrationManager` |
| INFRA-08 | Frontend integration configuration page shows connection status for all providers | New section in existing `frontend/src/app/dashboard/configuration/page.tsx` using established SectionHeader/card pattern |
</phase_requirements>

## Standard Stack

### Core (already in pyproject.toml -- no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| cryptography | >=46.0.3 | Fernet encryption for tokens | Already used in `app/services/encryption.py` |
| httpx | >=0.27.0,<1.0.0 | Async HTTP for token exchange and webhook delivery | Already used in `app/routers/webhooks.py` |
| supabase | >=2.27.2,<3.0.0 | Database access with RLS | Project standard |
| fastapi | (project version) | API routing | Project standard |

### Frontend (already in package.json -- no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| lucide-react | (project version) | Icons for provider cards | Already used in configuration page |
| framer-motion | (project version) | Animations for card expand/collapse | Already used in configuration page |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncio.Lock | Redis distributed lock | Overkill -- single-process backend on Cloud Run, asyncio.Lock is sufficient |
| Custom retry loop | tenacity library | Adds dependency; exponential backoff is 5 lines of code |
| Pydantic model for ProviderConfig | Python dataclass | Dataclass is lighter, no serialization needed since it's a code-only registry |

**Installation:**
```bash
# No new packages needed -- all dependencies already in pyproject.toml and package.json
```

## Architecture Patterns

### Recommended Project Structure
```
app/
  config/
    integration_providers.py    # Provider registry (dict + ProviderConfig dataclass)
  routers/
    integrations.py             # OAuth authorize/callback, status, provider list endpoints
    webhooks.py                 # (EXTEND) Add inbound/{provider} route
  services/
    integration_manager.py      # IntegrationManager (BaseService) - credentials, tokens, sync state
    webhook_delivery_service.py # Outbound delivery worker, circuit breaker, dead letter
    encryption.py               # (EXISTING) Reuse encrypt_secret/decrypt_secret
  models/
    webhook_events.py           # Event catalog, payload schemas (Pydantic models)

supabase/migrations/
  20260404000000_integration_infrastructure.sql  # All 4 new tables in one migration

frontend/src/
  app/dashboard/configuration/
    page.tsx                    # (EXTEND) Add External Integrations section
  services/
    integration-service.ts      # Frontend client for /integrations/* endpoints (new file)
```

### Pattern 1: IntegrationManager Service (extends BaseService)
**What:** Central service for credential CRUD, token refresh, and sync state management.
**When to use:** Any operation touching integration credentials or sync state.
**Example:**
```python
# Source: Follows app/services/base_service.py pattern exactly
from app.services.base_service import BaseService
from app.services.encryption import encrypt_secret, decrypt_secret

class IntegrationManager(BaseService):
    """Manages integration credentials and sync state."""

    def __init__(self, user_token: str | None = None):
        super().__init__(user_token)
        # Per-(user_id, provider) async locks for token refresh
        self._refresh_locks: dict[tuple[str, str], asyncio.Lock] = {}

    def _get_refresh_lock(self, user_id: str, provider: str) -> asyncio.Lock:
        key = (user_id, provider)
        if key not in self._refresh_locks:
            self._refresh_locks[key] = asyncio.Lock()
        return self._refresh_locks[key]

    async def store_credentials(
        self, *, user_id: str, provider: str, access_token: str,
        refresh_token: str | None, expires_at: datetime | None,
        scopes: str, account_name: str, token_type: str = "bearer",
    ) -> dict[str, Any]:
        row = {
            "user_id": user_id,
            "provider": provider,
            "access_token": encrypt_secret(access_token),
            "refresh_token": encrypt_secret(refresh_token) if refresh_token else None,
            "token_type": token_type,
            "scopes": scopes,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "account_name": account_name,
        }
        result = await self.execute(
            self.client.table("integration_credentials")
            .upsert(row, on_conflict="user_id,provider"),
            op_name="integration.store_credentials",
        )
        return result.data[0] if result.data else row

    async def get_valid_token(self, user_id: str, provider: str) -> str | None:
        """Get a valid access token, refreshing proactively if needed."""
        cred = await self._get_credential(user_id, provider)
        if not cred:
            return None

        # Proactive refresh: if <5 min remaining
        expires_at = cred.get("expires_at")
        if expires_at and _is_expiring_soon(expires_at, minutes=5):
            async with self._get_refresh_lock(user_id, provider):
                # Re-read after acquiring lock (another task may have refreshed)
                cred = await self._get_credential(user_id, provider)
                if cred and _is_expiring_soon(cred["expires_at"], minutes=5):
                    cred = await self._refresh_token(user_id, provider, cred)

        return decrypt_secret(cred["access_token"]) if cred else None
```

### Pattern 2: OAuth Flow (authorize + callback)
**What:** FastAPI endpoints that handle the full OAuth2 authorization code flow.
**When to use:** When a user connects a new provider from the configuration page.
**Example:**
```python
# Source: Follows app/social/connector.py pattern exactly
from app.config.integration_providers import PROVIDER_REGISTRY

@router.get("/{provider}/authorize")
async def authorize(provider: str, request: Request):
    """Redirect user to provider's OAuth consent page."""
    config = PROVIDER_REGISTRY.get(provider)
    if not config:
        raise HTTPException(404, f"Unknown provider: {provider}")
    if config.auth_type != "oauth2":
        raise HTTPException(400, f"Provider {provider} does not use OAuth")

    user_id = get_current_user_id(request)
    state = f"{user_id}:{provider}:{secrets.token_urlsafe(16)}"
    # Store state in Redis with short TTL for CSRF protection
    await cache_service.set_generic(
        f"pikar:integration:oauth_state:{state}", {"user_id": user_id}, ttl=600
    )
    params = {
        "client_id": os.environ[config.client_id_env],
        "redirect_uri": _get_callback_url(request),
        "response_type": "code",
        "scope": " ".join(config.scopes),
        "state": state,
        "access_type": "offline",  # Request refresh token
        "prompt": "consent",
    }
    auth_url = f"{config.auth_url}?{urlencode(params)}"
    return RedirectResponse(auth_url)
```

### Pattern 3: Inbound Webhook Verification (generalized HMAC)
**What:** Single endpoint that routes inbound webhooks by provider, verifies HMAC signature.
**When to use:** Receiving webhook events from connected providers.
**Example:**
```python
# Source: Generalizes app/routers/webhooks.py LinkedIn + Resend patterns
@router.post("/inbound/{provider}")
async def inbound_webhook(provider: str, request: Request):
    body = await request.body()

    # Provider-specific verification
    if not await _verify_inbound_signature(provider, body, request.headers):
        raise HTTPException(403, "Invalid webhook signature")

    payload = json.loads(body)
    event_id = _extract_event_id(provider, payload)

    # Idempotency: INSERT ... ON CONFLICT DO NOTHING
    result = await execute_async(
        service_client.table("webhook_events").insert({
            "provider": provider,
            "event_id": event_id,
            "event_type": _extract_event_type(provider, payload),
            "payload": payload,
            "status": "pending",
        }).on_conflict("provider,event_id"),  # Supabase upsert with ignore
        op_name="webhook.inbound.store",
    )
    if not result.data:
        return {"status": "duplicate", "event_id": event_id}

    # Queue for async processing via ai_jobs
    await execute_async(
        service_client.table("ai_jobs").insert({
            "job_type": "webhook_inbound_process",
            "status": "pending",
            "priority": 8,
            "input_data": {"provider": provider, "event_id": event_id, "webhook_event_db_id": result.data[0]["id"]},
        }),
        op_name="webhook.inbound.queue",
    )
    return {"status": "received", "event_id": event_id}
```

### Pattern 4: Outbound Webhook Delivery Worker (scheduler tick)
**What:** A periodic function called from the existing worker loop that processes pending deliveries.
**When to use:** Delivering outbound webhook events to user-configured endpoints.
**Example:**
```python
# Source: Follows app/services/workflow_trigger_service.py scheduler tick pattern
async def run_webhook_delivery_tick() -> list[dict[str, Any]]:
    """Process pending webhook deliveries. Called from worker loop."""
    service_client = get_service_client()

    # Fetch deliveries that are due for retry
    result = await execute_async(
        service_client.table("webhook_deliveries")
        .select("*, webhook_endpoints(*)")
        .in_("status", ["pending", "failed"])
        .lte("next_retry_at", datetime.now(timezone.utc).isoformat())
        .lt("attempts", 5)
        .order("created_at")
        .limit(50),
        op_name="webhook.delivery.fetch_pending",
    )
    deliveries = result.data or []
    results = []
    for delivery in deliveries:
        results.append(await _deliver_single(service_client, delivery))
    return results
```

### Pattern 5: Provider Registry (code-only dict)
**What:** A Python dict mapping provider names to ProviderConfig dataclasses.
**When to use:** Looking up provider OAuth URLs, scopes, categories.
**Example:**
```python
# Source: Follows app/social/connector.py PLATFORM_CONFIGS pattern
from dataclasses import dataclass

@dataclass(frozen=True)
class ProviderConfig:
    name: str
    auth_type: str  # "oauth2" or "api_key"
    auth_url: str
    token_url: str
    scopes: list[str]
    client_id_env: str
    client_secret_env: str
    webhook_secret_header: str | None
    icon_url: str
    category: str  # crm_sales, finance_commerce, productivity, analytics, communication

PROVIDER_REGISTRY: dict[str, ProviderConfig] = {
    "hubspot": ProviderConfig(
        name="HubSpot",
        auth_type="oauth2",
        auth_url="https://app.hubspot.com/oauth/authorize",
        token_url="https://api.hubapi.com/oauth/v1/token",
        scopes=["crm.objects.contacts.read", "crm.objects.contacts.write",
                "crm.objects.deals.read", "crm.objects.deals.write"],
        client_id_env="HUBSPOT_CLIENT_ID",
        client_secret_env="HUBSPOT_CLIENT_SECRET",
        webhook_secret_header="X-HubSpot-Signature-v3",
        icon_url="/icons/hubspot.svg",
        category="crm_sales",
    ),
    # Future phases will add their provider entries here
}
```

### Anti-Patterns to Avoid
- **Never store plaintext tokens:** Always use `encrypt_secret()` before INSERT. Never log or return decrypted tokens in API responses.
- **Never skip idempotency for inbound webhooks:** Providers retry on timeout. Without `ON CONFLICT DO NOTHING`, you will process duplicates.
- **Never refresh tokens without locking:** Two concurrent requests seeing an expired token will both try to refresh, but only the first refresh token usage succeeds. The second gets a `400 invalid_grant`.
- **Never use a new worker process for delivery:** The existing `WorkflowWorker.start()` loop runs every 5 seconds. Add a `run_webhook_delivery_if_due()` method following the exact `run_workflow_trigger_scheduler_if_due()` pattern.
- **Never store provider config in the database:** Provider configs are deployment-time constants. A database table adds migration overhead when adding providers and provides no benefit since users don't customize provider OAuth URLs.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token encryption | Custom AES wrapper | `app/services/encryption.py` (`encrypt_secret`/`decrypt_secret`) | Already handles MultiFernet key rotation, tested |
| HMAC verification | Custom signature builder | `hmac.compare_digest` + provider-specific header extraction | The pattern is already in `webhooks.py` twice |
| Circuit breaker | Custom state machine | Adapt `CacheService` pattern (closed/open/half-open states) | Same 3-state machine, proven in production |
| OAuth PKCE flow | Custom code_verifier/challenge | Adapt `SocialConnector._generate_pkce()` pattern | Already handles S256 code challenge correctly |
| Job queueing | Custom Celery/RQ setup | `ai_jobs` table + `WorkflowWorker` polling loop | Already processes jobs every 5 seconds |
| Exponential backoff | Custom retry timer | Simple list: `[1, 5, 30, 300, 1800]` seconds | 5 fixed values are simpler than calculating |
| Frontend API calls | Direct fetch | `fetchWithAuth` from `frontend/src/services/api.ts` | Handles auth headers, retry, timeout automatically |

**Key insight:** This phase has zero new dependencies because every building block already exists in the codebase. The work is generalization and composition, not invention.

## Common Pitfalls

### Pitfall 1: Token Refresh Race Condition
**What goes wrong:** Two concurrent API calls for the same user+provider both detect an expired token. Both try to refresh. Provider revokes the first refresh token after it's used, so the second refresh fails with `invalid_grant`. The user's connection is broken.
**Why it happens:** OAuth2 refresh tokens are single-use for many providers (HubSpot, Shopify, Google).
**How to avoid:** Use `asyncio.Lock` per `(user_id, provider)`. After acquiring the lock, re-read the credential from DB -- another coroutine may have already refreshed it.
**Warning signs:** Intermittent `400 invalid_grant` errors in token refresh logs.

### Pitfall 2: Webhook Signature Timing Attack
**What goes wrong:** Using `==` instead of `hmac.compare_digest` for signature comparison leaks timing information that could allow signature forgery.
**Why it happens:** Python string comparison short-circuits on first mismatch.
**How to avoid:** Always use `hmac.compare_digest()`. The existing codebase already does this in `webhooks.py`.
**Warning signs:** Using `==` or `!=` anywhere in signature verification code.

### Pitfall 3: Supabase Upsert ON CONFLICT Semantics
**What goes wrong:** Using `.upsert()` when you want `INSERT ... ON CONFLICT DO NOTHING` (idempotency). Supabase's `.upsert()` method actually UPDATES on conflict by default, which would overwrite the event status.
**Why it happens:** Supabase Python client upsert defaults to `ignoreDuplicates=False`.
**How to avoid:** For webhook idempotency, pass `count="exact"` and handle the duplicate case. Alternatively, use a raw RPC call or the `ignoreDuplicates=True` parameter: `.upsert(row, on_conflict="provider,event_id", ignore_duplicates=True)`.
**Warning signs:** Webhook events getting their status reset to `pending` on redelivery.

### Pitfall 4: OAuth State Parameter Forgery (CSRF)
**What goes wrong:** Attacker crafts a fake OAuth callback with a valid-looking `code` but a forged `state`, linking their provider account to another user.
**Why it happens:** State parameter is not validated against a server-side store.
**How to avoid:** Store the state in Redis with a short TTL (10 min) during the authorize step. On callback, verify the state exists in Redis and matches the user_id before exchanging the code. Delete the state after use.
**Warning signs:** Missing state validation in the callback endpoint.

### Pitfall 5: Missing `access_type=offline` in OAuth Authorize
**What goes wrong:** Provider returns an access token but no refresh token. Token expires and there's no way to renew it without user re-authorization.
**Why it happens:** Some providers (Google, HubSpot) require `access_type=offline` or `prompt=consent` to issue a refresh token on the first authorization.
**How to avoid:** Always include `access_type=offline` (or provider equivalent) in the authorize URL parameters. Check that the callback actually received a refresh token and warn if not.
**Warning signs:** `refresh_token` is NULL in `integration_credentials` after first connection.

### Pitfall 6: Webhook Delivery Infinite Retry
**What goes wrong:** A webhook endpoint returns 500 forever. The delivery worker retries indefinitely, wasting resources and filling the deliveries table.
**Why it happens:** Missing dead letter transition and circuit breaker.
**How to avoid:** After 5 attempts, transition to `dead` status. After 10 consecutive failures across any delivery to an endpoint, disable the endpoint and notify the user.
**Warning signs:** Growing `webhook_deliveries` table with many failed records for the same endpoint.

## Code Examples

### Migration SQL Pattern
```sql
-- Source: Follows supabase/migrations/ conventions
-- File: supabase/migrations/20260404000000_integration_infrastructure.sql

-- Provider enum for type safety
CREATE TYPE integration_provider AS ENUM (
    'hubspot', 'shopify', 'stripe', 'linear', 'asana',
    'slack', 'teams', 'bigquery'
);

-- 1. Integration Credentials
CREATE TABLE integration_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider integration_provider NOT NULL,
    access_token TEXT NOT NULL,      -- Fernet encrypted
    refresh_token TEXT,              -- Fernet encrypted, nullable for API-key providers
    token_type TEXT DEFAULT 'bearer',
    scopes TEXT,
    expires_at TIMESTAMPTZ,
    account_name TEXT,               -- Display name from provider
    webhook_secret TEXT,             -- For inbound webhook verification, Fernet encrypted
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, provider)
);

ALTER TABLE integration_credentials ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own integration credentials"
    ON integration_credentials FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE INDEX idx_integration_credentials_user_provider
    ON integration_credentials(user_id, provider);

-- 2. Integration Sync State
CREATE TABLE integration_sync_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider integration_provider NOT NULL,
    last_sync_at TIMESTAMPTZ,
    sync_cursor JSONB DEFAULT '{}'::jsonb,  -- Pagination token per resource type
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    backoff_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, provider)
);

ALTER TABLE integration_sync_state ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own sync state"
    ON integration_sync_state FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- 3. Webhook Events (inbound)
CREATE TABLE webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,
    event_id TEXT NOT NULL,         -- Provider-assigned event ID
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    user_id UUID REFERENCES auth.users(id),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'processed', 'failed', 'ignored')),
    error_message TEXT,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ,
    UNIQUE(provider, event_id)     -- Idempotency constraint
);

CREATE INDEX idx_webhook_events_status ON webhook_events(status)
    WHERE status = 'pending';
CREATE INDEX idx_webhook_events_provider_user
    ON webhook_events(provider, user_id);

-- 4. Webhook Endpoints (outbound -- user-configured)
CREATE TABLE webhook_endpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    secret TEXT NOT NULL,            -- For HMAC signing outbound payloads
    events TEXT[] NOT NULL DEFAULT '{}',  -- Event types to subscribe to
    active BOOLEAN DEFAULT true,
    failure_count INTEGER DEFAULT 0, -- Consecutive failures for circuit breaker
    disabled_at TIMESTAMPTZ,         -- When circuit breaker triggered
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE webhook_endpoints ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own webhook endpoints"
    ON webhook_endpoints FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- 5. Webhook Deliveries (outbound -- delivery log)
CREATE TABLE webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint_id UUID NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'delivered', 'failed', 'dead')),
    attempts INTEGER DEFAULT 0,
    next_retry_at TIMESTAMPTZ DEFAULT now(),
    response_code INTEGER,
    response_body TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_webhook_deliveries_pending
    ON webhook_deliveries(next_retry_at)
    WHERE status IN ('pending', 'failed') AND attempts < 5;
CREATE INDEX idx_webhook_deliveries_endpoint
    ON webhook_deliveries(endpoint_id, created_at DESC);

-- updated_at trigger (reuse pattern from existing tables)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_integration_credentials_updated_at
    BEFORE UPDATE ON integration_credentials
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER set_integration_sync_state_updated_at
    BEFORE UPDATE ON integration_sync_state
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER set_webhook_endpoints_updated_at
    BEFORE UPDATE ON webhook_endpoints
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### Worker Loop Integration
```python
# Source: Follows app/workflows/worker.py run_workflow_trigger_scheduler_if_due() pattern
# Added to WorkflowWorker class:

class WorkflowWorker:
    def __init__(self):
        # ... existing init ...
        self.last_webhook_delivery_tick = datetime.min
        self.webhook_delivery_interval_seconds = 30  # Every 30s

    async def run_webhook_delivery_if_due(self):
        """Process pending webhook deliveries at a controlled cadence."""
        now = datetime.now()
        seconds_since_last = (now - self.last_webhook_delivery_tick).total_seconds()
        if seconds_since_last < self.webhook_delivery_interval_seconds:
            return
        self.last_webhook_delivery_tick = now
        try:
            from app.services.webhook_delivery_service import run_webhook_delivery_tick
            results = await run_webhook_delivery_tick()
            if results:
                logger.info("Processed %s webhook deliveries", len(results))
        except Exception as exc:
            logger.error("Webhook delivery tick failed: %s", exc, exc_info=True)
```

### Frontend Integration Service
```typescript
// Source: Follows frontend/src/services/api.ts fetchWithAuth pattern
import { fetchWithAuth } from '@/services/api';

export interface IntegrationProvider {
    key: string;
    name: string;
    auth_type: 'oauth2' | 'api_key';
    icon_url: string;
    category: string;
    connected: boolean;
    account_name?: string;
    last_sync_at?: string;
    status: 'connected' | 'disconnected' | 'error';
    error?: string;
}

export async function getIntegrationProviders(): Promise<IntegrationProvider[]> {
    const response = await fetchWithAuth('/integrations/providers');
    const data = await response.json();
    return data.providers;
}

export async function getIntegrationStatus(): Promise<Record<string, IntegrationProvider>> {
    const response = await fetchWithAuth('/integrations/status');
    return response.json();
}

export async function disconnectProvider(provider: string): Promise<void> {
    await fetchWithAuth(`/integrations/${provider}/disconnect`, { method: 'POST' });
}
```

### Router Mounting Pattern
```python
# In app/fast_api_app.py -- add alongside existing router imports:
from app.routers.integrations import router as integrations_router

# Then in the include_router block:
app.include_router(integrations_router, tags=["Integrations"])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Store tokens in env vars | Per-user encrypted DB storage | This phase | Enables multi-user, per-user provider connections |
| Platform-specific webhook files | Generic inbound/{provider} router | This phase | New providers add a handler function, not a new file |
| No outbound webhooks | Event-driven delivery queue | This phase | Enables Zapier/webhook integrations in Phase 47 |
| Social-only OAuth connector | General-purpose integration OAuth | This phase | SocialConnector served only social; new flow serves all providers |

**Key relationship to existing code:**
- `app/social/connector.py` (SocialConnector) handles social media OAuth only. The new `IntegrationManager` handles business integration OAuth. They share the same PKCE+redirect pattern but serve different provider sets. They can coexist without conflict.
- `app/routers/webhooks.py` currently has LinkedIn and Resend endpoints. The new `POST /webhooks/inbound/{provider}` generalizes this pattern. Existing LinkedIn/Resend endpoints stay as-is for now (can be migrated later).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` (existing) |
| Quick run command | `uv run pytest tests/unit/services/test_integration_manager.py -x` |
| Full suite command | `uv run pytest tests/unit/ -x --timeout=60` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | Credentials stored encrypted, decrypted on read | unit | `uv run pytest tests/unit/services/test_integration_manager.py::test_store_credentials_encrypts -x` | Wave 0 |
| INFRA-01 | Upsert on same user+provider updates, not duplicates | unit | `uv run pytest tests/unit/services/test_integration_manager.py::test_upsert_credentials -x` | Wave 0 |
| INFRA-02 | Concurrent refresh uses lock, second reader gets fresh token | unit | `uv run pytest tests/unit/services/test_integration_manager.py::test_concurrent_refresh_lock -x` | Wave 0 |
| INFRA-02 | Proactive refresh when <5 min remaining | unit | `uv run pytest tests/unit/services/test_integration_manager.py::test_proactive_refresh -x` | Wave 0 |
| INFRA-03 | Status endpoint returns per-provider state | unit | `uv run pytest tests/unit/routers/test_integrations_router.py::test_status_endpoint -x` | Wave 0 |
| INFRA-04 | Inbound webhook with valid HMAC is stored | unit | `uv run pytest tests/unit/services/test_webhook_service.py::test_inbound_valid_hmac -x` | Wave 0 |
| INFRA-04 | Duplicate event_id is rejected (idempotency) | unit | `uv run pytest tests/unit/services/test_webhook_service.py::test_inbound_idempotency -x` | Wave 0 |
| INFRA-05 | Outbound delivery succeeds on 200 | unit | `uv run pytest tests/unit/services/test_webhook_delivery.py::test_delivery_success -x` | Wave 0 |
| INFRA-05 | Failed delivery retries with exponential backoff | unit | `uv run pytest tests/unit/services/test_webhook_delivery.py::test_delivery_retry_backoff -x` | Wave 0 |
| INFRA-06 | 5 failures moves to dead letter | unit | `uv run pytest tests/unit/services/test_webhook_delivery.py::test_dead_letter -x` | Wave 0 |
| INFRA-06 | 10 consecutive endpoint failures disables endpoint | unit | `uv run pytest tests/unit/services/test_webhook_delivery.py::test_circuit_breaker -x` | Wave 0 |
| INFRA-07 | Sync state cursor updated after sync | unit | `uv run pytest tests/unit/services/test_integration_manager.py::test_sync_state_cursor -x` | Wave 0 |
| INFRA-07 | Error count incremented on failure, backoff set | unit | `uv run pytest tests/unit/services/test_integration_manager.py::test_sync_state_error_backoff -x` | Wave 0 |
| INFRA-08 | Frontend renders provider cards with correct status | manual-only | Visual inspection -- card rendering with mock data | N/A |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/services/test_integration_manager.py tests/unit/services/test_webhook_delivery.py tests/unit/services/test_webhook_service.py -x`
- **Per wave merge:** `uv run pytest tests/unit/ -x --timeout=60`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/services/test_integration_manager.py` -- covers INFRA-01, INFRA-02, INFRA-07
- [ ] `tests/unit/services/test_webhook_service.py` -- covers INFRA-04
- [ ] `tests/unit/services/test_webhook_delivery.py` -- covers INFRA-05, INFRA-06
- [ ] `tests/unit/routers/test_integrations_router.py` -- covers INFRA-03

## Open Questions

1. **Webhook delivery scheduling interval**
   - What we know: Workflow triggers tick every 60 seconds. Worker poll is every 5 seconds.
   - What's unclear: Optimal interval for webhook delivery -- 30s balances latency vs DB load.
   - Recommendation: Start at 30 seconds (configurable via env var). Can reduce to 10s if users need near-real-time delivery.

2. **Rate limiting on outbound webhook delivery**
   - What we know: Need to prevent overwhelming user endpoints.
   - What's unclear: Per-endpoint or global rate limit, and what threshold.
   - Recommendation: Process max 50 deliveries per tick globally. Per-endpoint circuit breaker (10 failures) already prevents hammering broken endpoints. Add per-endpoint rate limit of 10/minute in a future iteration if needed.

3. **Provider enum extensibility**
   - What we know: PostgreSQL enums require `ALTER TYPE ... ADD VALUE` migrations for new providers.
   - What's unclear: Whether to use enum or TEXT with CHECK constraint.
   - Recommendation: Use `TEXT` with a CHECK constraint listing allowed values. This is easier to extend via migration than a PostgreSQL enum type. Each future phase adds its provider value with a simple `ALTER TABLE ... DROP CONSTRAINT ... ADD CONSTRAINT`.

## Sources

### Primary (HIGH confidence)
- `app/services/encryption.py` -- MultiFernet API (encrypt_secret, decrypt_secret), line 60-100
- `app/services/base_service.py` -- BaseService pattern with RLS, line 33-119
- `app/services/cache.py` -- Circuit breaker (closed/open/half-open), line 44-271
- `app/routers/webhooks.py` -- HMAC-SHA256 verification (LinkedIn + Svix patterns), line 1-413
- `app/social/connector.py` -- OAuth PKCE flow, PLATFORM_CONFIGS dict pattern, line 1-200
- `app/services/workflow_trigger_service.py` -- Scheduler tick + ai_jobs queue pattern, line 317-341
- `app/workflows/worker.py` -- WorkflowWorker polling loop, scheduler integration, line 186-217
- `app/services/scheduled_endpoints.py` -- Cloud Scheduler endpoint pattern, line 97-112
- `frontend/src/app/dashboard/configuration/page.tsx` -- Section layout, SectionHeader, card patterns
- `frontend/src/services/api.ts` -- fetchWithAuth pattern, retry logic
- `supabase/migrations/20260319000001_social_webhook_events.sql` -- Webhook event table pattern
- `supabase/migrations/0001_initial_schema.sql` -- ai_jobs table schema

### Secondary (MEDIUM confidence)
- Supabase upsert `ignore_duplicates` parameter -- verified in supabase-py documentation

### Tertiary (LOW confidence)
- None -- all findings verified against existing codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies; all libraries already in use
- Architecture: HIGH -- every pattern verified against existing codebase implementations
- Pitfalls: HIGH -- token refresh race condition is a well-documented OAuth2 issue; other pitfalls observed in existing code patterns
- Migration: HIGH -- follows established migration naming and RLS conventions

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable -- infrastructure patterns, no external API changes expected)

# Phase 39: Integration Infrastructure - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the secure, reusable foundation that all future integration phases (40-47) depend on: encrypted credential storage with OAuth token lifecycle management, a general-purpose webhook system (inbound + outbound with delivery guarantees), sync state tracking per user per provider, and a frontend configuration page showing connection status for all supported providers.

</domain>

<decisions>
## Implementation Decisions

### Credential Storage
- **New `integration_credentials` table** in Supabase — dedicated table, not an extension of MCP config
  - Columns: `id`, `user_id`, `provider` (enum: hubspot, shopify, stripe, linear, asana, slack, teams, bigquery), `access_token` (Fernet encrypted), `refresh_token` (Fernet encrypted), `token_type`, `scopes`, `expires_at`, `account_name` (display name from provider), `created_at`, `updated_at`
  - RLS: `auth.uid() = user_id` — per-user isolation
  - Reuse existing `app/services/encryption.py` (MultiFernet with key rotation) — NOT a new encryption service
- **OAuth flow handled by backend** — FastAPI endpoints:
  - `GET /integrations/{provider}/authorize` → builds provider-specific auth URL, redirects user
  - `GET /integrations/{provider}/callback` → receives authorization code, exchanges for tokens, encrypts and stores
  - Frontend opens a popup window to the authorize URL, listens for popup close, then refreshes status
- **Token refresh with async locking:**
  - `IntegrationManager` service with `asyncio.Lock` per `(user_id, provider)` combo
  - Proactive refresh: refresh when token has <5 min remaining, not on 401
  - Retry-after-refresh: if 401 → acquire lock → check if already refreshed → refresh if not → retry
  - Pattern matches the research pitfall P2 prevention strategy
- **Disconnect behavior:** Stop sync only — tokens are deleted but previously synced data stays in Pikar. User can re-connect without losing history.
- **New `integration_sync_state` table:**
  - Columns: `id`, `user_id`, `provider`, `last_sync_at`, `sync_cursor` (JSONB — pagination token), `error_count`, `last_error`, `backoff_until`, `created_at`, `updated_at`
  - RLS per user

### Webhook Architecture (Claude's informed recommendation)
- **Inbound webhooks:**
  - Single receiver endpoint: `POST /webhooks/inbound/{provider}` — routes to provider-specific handler
  - HMAC-SHA256 verification per provider (verification secret stored in `integration_credentials`)
  - Idempotency via `webhook_events` table with UNIQUE constraint on `(provider, event_id)`
  - `INSERT ... ON CONFLICT DO NOTHING` pattern prevents duplicate processing
  - Events stored in `webhook_events` table then processed via `ai_jobs` queue (existing pattern)
- **Outbound webhooks:**
  - `webhook_endpoints` table: `id`, `user_id`, `url`, `secret` (for HMAC signing), `events` (text array of event types), `active`, `created_at`
  - `webhook_deliveries` table: `id`, `endpoint_id`, `event_type`, `payload` (JSONB), `status` (pending/delivered/failed/dead), `attempts`, `next_retry_at`, `response_code`, `response_body`, `created_at`
  - Delivery worker reads pending deliveries, POSTs with HMAC-SHA256 signature in `X-Pikar-Signature` header
  - Retry: 5 attempts with exponential backoff (1s, 5s, 30s, 5min, 30min)
  - Dead letter: after 5 failures, status → `dead`, notification to user
  - Per-endpoint circuit breaker: after 10 consecutive failures, endpoint auto-disabled with notification
  - Delivery worker runs via existing `workflow_trigger_service` scheduler pattern (not a new worker process)
- **Event catalog:**
  - Hardcoded in code (not DB) — list of available event types with payload schemas
  - Events: `task.created`, `task.updated`, `workflow.started`, `workflow.completed`, `approval.pending`, `approval.decided`, `initiative.phase_changed`, `contact.synced`, `invoice.created`
  - Each event has a JSON schema definition for its payload

### Provider Registry (Claude's informed recommendation)
- **Simple Python dict registry** in `app/config/integration_providers.py` — NOT a database table
  - Maps provider key → `ProviderConfig` dataclass: `name`, `auth_type` (oauth2/api_key), `auth_url`, `token_url`, `scopes`, `webhook_secret_header`, `icon_url`, `category`
  - Categories: `crm_sales`, `finance_commerce`, `productivity`, `analytics`, `communication`
  - All future phases register their provider in this dict
  - Frontend reads provider list from `GET /integrations/providers` endpoint
- **Why not DB:** Provider configs are deployment-time constants, not user data. A Python dict is simpler, type-safe, and doesn't require migrations when adding providers.

### Frontend Configuration Page
- **Category card layout:** Group providers by purpose:
  - "CRM & Sales" — HubSpot
  - "Finance & Commerce" — Stripe, Shopify
  - "Productivity" — Linear, Asana, Google Workspace
  - "Communication" — Slack, Teams
  - "Analytics" — BigQuery, Google Analytics
- **Simple 3-state status:** Green dot (Connected), Gray dot (Disconnected), Red dot (Error). Click card to expand details (last sync, account name, error message).
- **Connect button flow:** Click "Connect" → opens popup to `/integrations/{provider}/authorize` → user completes OAuth in popup → popup closes → parent page refreshes status
- **Agent integration prompts:** When a user asks about CRM data and HubSpot isn't connected, agent responds with "Connect HubSpot in Settings to see real CRM data" with a link to `/dashboard/configuration`. This is a behavioral pattern future agent phases implement, not infrastructure built here.
- **Health check endpoint:** `GET /integrations/status` returns per-provider status for the authenticated user (reads `integration_credentials` + `integration_sync_state`)

### Claude's Discretion
- Exact Supabase migration SQL (column types, indexes, constraints)
- Webhook delivery worker scheduling interval
- Provider config dataclass field details beyond the ones specified
- Frontend card component styling (follows existing design system)
- Error message wording for OAuth failures
- Rate limiting on webhook delivery (per-endpoint or global)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/encryption.py`: MultiFernet encrypt/decrypt with key rotation — use directly for token encryption
- `app/routers/webhooks.py`: LinkedIn webhook with HMAC-SHA256 verification — pattern to generalize
- `app/integrations/google/client.py`: OAuth credential building from provider tokens — pattern for new providers
- `app/services/cache.py`: Circuit breaker (closed/open/half-open) — reuse pattern for webhook endpoint health
- `app/services/base_service.py`: BaseService with Supabase client injection — extend for IntegrationManager
- `app/services/workflow_trigger_service.py`: Scheduler tick pattern — reuse for webhook delivery worker

### Established Patterns
- Services inherit from BaseService, use `self._client` for Supabase operations
- All tables use RLS with `auth.uid() = user_id` policies
- async throughout — all service methods are `async def`
- Supabase migrations in `supabase/migrations/` with sequential numbering
- Frontend fetches via `fetchWithAuth` from `frontend/src/services/api.ts`

### Integration Points
- `app/fast_api_app.py`: Mount new `/integrations` and update `/webhooks` routers
- `app/config/settings.py`: Add any new env vars for provider client IDs/secrets
- `frontend/src/app/dashboard/configuration/page.tsx`: Extend with new provider sections
- `app/services/notification_service.py`: Webhook delivery failures should notify users

</code_context>

<specifics>
## Specific Ideas

- Credential storage must reuse existing MultiFernet encryption — no new crypto
- Webhook inbound uses the same HMAC pattern already in LinkedIn webhook handler, generalized
- Outbound webhook delivery follows the existing `ai_jobs` queue pattern, not a new worker process
- Provider registry is a simple Python dict, not a database table — keeps it deployment-time constant

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 39-integration-infrastructure*
*Context gathered: 2026-04-04*

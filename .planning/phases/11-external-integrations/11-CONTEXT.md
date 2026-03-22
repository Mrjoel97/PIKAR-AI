# Phase 11: External Integrations - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning
**Source:** PRD Express Path (docs/superpowers/specs/2026-03-21-admin-panel-design.md)

<domain>
## Phase Boundary

This phase adds external tool integrations: the admin can connect Sentry, PostHog, GitHub, and Stripe via encrypted API keys stored in the `admin_integrations` table (created in Phase 7 migration). The AdminAgent gains tools to query each service through a server-side proxy. Response caching prevents rate limit exhaustion.

**Requirements:** INTG-01..06 (6 total)

</domain>

<decisions>
## Implementation Decisions

### Integration Connection Management
- `/admin/integrations` UI page for connecting/disconnecting external tools
- Each provider has: API key (Fernet encrypted), base URL (optional), config JSONB, health status
- API keys encrypted with MultiFernet (from Phase 7 `app/services/encryption.py`)
- Frontend shows only `****...last4` of keys — never the full value
- Provider-specific config fields: Sentry (org_slug, project_slug), PostHog (project_id), GitHub (owner, repo), Stripe (restricted read-only key recommended)
- Health check per integration: periodic ping to verify connectivity

### Server-Side Proxy Pattern
- All external API calls go through FastAPI backend — never from frontend
- `app/routers/admin/integrations.py` — CRUD for integration connections + proxy endpoints
- Each proxy call: require_admin → fetch + decrypt API key → call external API → transform response → return
- Rate limited: 60 requests/minute for proxy endpoints
- Response caching in Redis (2-5 minute TTL) with per-session call budgets to prevent rate exhaustion

### Provider Implementations
- **Sentry**: `httpx` calls to Sentry API (`/api/0/projects/{org}/{project}/issues/`, issue detail with stacktrace)
- **PostHog**: `httpx` calls to PostHog API (`/api/projects/{id}/events/`, `/api/projects/{id}/insights/`)
- **GitHub**: `PyGithub` library (sync, wrapped in `asyncio.to_thread()`) for PRs, checks, issues
- **Stripe**: `httpx` calls to Stripe API (read-only: subscriptions, charges, balance) — full Stripe integration in Phase 14

### AdminAgent Integration Tools
- New tools in `app/agents/admin/tools/integrations.py`:
  - `sentry_get_issues` (auto) — fetch recent Sentry errors
  - `sentry_get_issue_detail` (auto) — stack trace, affected users
  - `posthog_query_events` (auto) — query PostHog events/metrics
  - `posthog_get_insights` (auto) — fetch saved PostHog insights
  - `github_list_prs` (auto) — recent pull requests
  - `github_get_pr_status` (auto) — PR checks and status
- All tools use autonomy enforcement from Phase 7

### Backend Structure
- `app/routers/admin/integrations.py` — integration CRUD + proxy
- `app/agents/admin/tools/integrations.py` — agent integration tools
- `app/services/integration_proxy.py` — shared proxy logic (decrypt, call, cache, transform)
- Update `app/routers/admin/__init__.py` to register integrations router
- Update `app/agents/admin/agent.py` to register integration tools

### Frontend Structure
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

</decisions>

<specifics>
## Specific Ideas

- Integration cards should show: provider icon/name, connection status badge (green connected, gray not set), last health check time
- Configure modal should mask the API key input after save
- "Test Connection" button that pings the provider API to verify the key works
- Research SUMMARY.md flagged: "Verify current rate limits and pagination for Sentry, PostHog, GitHub APIs before implementing proxy tools"

</specifics>

<deferred>
## Deferred Ideas

- CodeRabbit integration — deprioritized per design spec (Sentry, PostHog, GitHub, Stripe cover core needs)
- Stripe billing tools (issue_refund, change_user_plan) — Phase 14
- Webhook-based real-time updates from providers — polling/on-demand sufficient
- Integration marketplace for custom providers — future

</deferred>

---

*Phase: 11-external-integrations*
*Context gathered: 2026-03-22 via PRD Express Path*

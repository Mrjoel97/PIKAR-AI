# Phase 8: Health Monitoring - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning
**Source:** PRD Express Path (docs/superpowers/specs/2026-03-21-admin-panel-design.md)

<domain>
## Phase Boundary

This phase adds the API health monitoring system: a Cloud Scheduler-triggered health check loop that pings all internal and external endpoints concurrently, records results to `api_health_checks`, detects anomalies and creates `api_incidents`, and presents everything on a `/admin/monitoring` dashboard with sparkline charts. The AI admin agent gains monitoring and diagnostic tools.

**Requirements:** HLTH-01..06 (6 total)

</domain>

<decisions>
## Implementation Decisions

### Health Check Service
- `app/services/health_checker.py` — concurrent endpoint pinging via `httpx` + `asyncio.gather()`
- Pings all existing `/health/*` endpoints: `/health/live`, `/health/connections`, `/health/cache`, `/health/embeddings`, `/health/video`
- Also pings external providers: Gemini API (via a lightweight test call), Supabase (via a simple query), Redis (via ping)
- Records results to `api_health_checks` table (created in Phase 7 migration)
- Health results write **directly to Supabase** (not through the monitored FastAPI service) — prevents circular dependency where a Supabase outage silently produces stale data
- Uses `httpx.AsyncClient` with a 10-second timeout per endpoint
- Each check records: endpoint, category (internal/provider/integration), status (healthy/degraded/down/timeout), response_time_ms, status_code, error_message, metadata

### Cloud Scheduler Integration
- `POST /admin/monitoring/run-check` endpoint — triggered by Cloud Scheduler every 60 seconds
- Authenticated via `WORKFLOW_SERVICE_SECRET` header (same pattern as existing `scheduled_endpoints.py`)
- NOT gated by `require_admin` — uses the scheduled endpoint secret pattern instead
- Rate limited to 2 requests/minute to prevent abuse
- Endpoint is idempotent — safe to call multiple times

### Anomaly Detection
- Detects: status changes (healthy→down), response time > 2x rolling average, error rate > 5% threshold
- When anomaly detected: creates `api_incidents` row with incident_type (down/degraded/error_spike/latency_spike)
- When endpoint recovers (was down, now healthy): resolves incident (sets resolved_at)
- Rolling average computed from last 10 health checks for that endpoint

### Health Check Data Management
- Auto-prune records older than 30 days — run as part of the health check loop
- Keep at most 1000 records per endpoint (rolling window)

### Monitoring Dashboard Frontend
- Route: `/admin/monitoring` (new page in (admin) route group)
- Real-time status grid showing all endpoints with current status and response time
- Color coding: green = healthy, yellow = degraded, red = down, gray = timeout/unknown
- Sparkline charts (using recharts@3.8+) showing response time trends for last 24 hours
- Active incidents panel showing unresolved incidents with remediation status
- Stale-data warning banner if latest `api_health_checks` row is > 5 minutes old
- Auto-refresh every 30 seconds via polling (not WebSocket — consistent with design spec)

### Admin Agent Monitoring Tools
- New tools added to AdminAgent's toolkit in `app/agents/admin/tools/monitoring.py`:
  - `get_api_health_summary` (auto) — current status of all monitored endpoints
  - `get_api_health_history` (auto) — trend data for a specific endpoint (24h/7d/30d)
  - `get_active_incidents` (auto) — all unresolved incidents
  - `get_incident_detail` (auto) — full timeline and context for an incident
  - `run_diagnostic` (auto) — deep check on a specific endpoint
  - `check_error_logs` (auto) — recent backend error logs by endpoint
  - `check_rate_limits` (auto) — rate limit status for Gemini, Supabase, external APIs

### Proactive Agent Enhancement
- Update the AdminAgent's proactive greeting (from Phase 7) to include real health data
- On admin panel open, agent fetches latest health summary and reports any active incidents

### Backend Structure
- `app/services/health_checker.py` — core health check logic
- `app/routers/admin/monitoring.py` — monitoring API endpoints
- `app/agents/admin/tools/monitoring.py` — agent monitoring tools
- Update `app/routers/admin/__init__.py` to register monitoring router

### Claude's Discretion
- Exact sparkline chart dimensions and styling
- Dashboard card layout (grid columns, responsive breakpoints)
- How to compute the rolling average (simple mean vs exponential moving average)
- Incident severity classification algorithm details
- Whether to show endpoint groups (internal vs provider vs integration) as tabs or sections
- Error log querying implementation (structured logging query vs simple Supabase log table)

</decisions>

<specifics>
## Specific Ideas

- Status grid should group endpoints by category: Internal APIs, External Providers, External Integrations
- Each status card shows: endpoint name, current status badge, response time, last check time
- Sparklines should use the existing Tailwind color palette: emerald for healthy, amber for degraded, rose for down
- The stale-data warning banner should be a yellow/amber bar at the top of the monitoring page
- Dashboard should have a "Run Check Now" button that manually triggers a health check (confirm-tier via admin agent)
- Incident panel should show: endpoint, incident type, started_at, duration, remediation status

</specifics>

<deferred>
## Deferred Ideas

- Self-healing agent actions (restart_cache, switch_model_fallback, restart_service) — these are confirm-tier tools that will be added when the respective domain infrastructure supports them
- Email notifications for critical incidents — Phase 7 audit trail captures incidents, notification pipeline is future work
- Webhook-based real-time updates — SSE/polling sufficient at this scale per design spec

</deferred>

---

*Phase: 08-health-monitoring*
*Context gathered: 2026-03-21 via PRD Express Path*

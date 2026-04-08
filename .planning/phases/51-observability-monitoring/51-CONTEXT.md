# Phase 51: Observability & Monitoring - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Make application errors, agent performance, and AI cost visible to the admin:

1. **Error capture** — Unhandled exceptions in backend (Python/FastAPI) and frontend (Next.js) are captured to Sentry with stack trace, user_id, and request metadata (OBS-01).
2. **Agent performance dashboard** — Admin can see p50/p95/p99 latency of each specialized agent over configurable time windows (OBS-02).
3. **Error rate trends** — Admin can see error rate over time, filterable by endpoint, agent, and time period (OBS-03).
4. **AI cost tracking** — Admin can see AI token spend aggregated by agent, user, and day, with a projected monthly burn (OBS-04).
5. **Structured health endpoints** — `/health/*` endpoints return a single canonical JSON shape describing Supabase, Redis, Gemini, and the active integrations (OBS-05).

**Out of scope for Phase 51** (deferred):
- On-call paging (Slack/email notifications) — admin_audit_log is the notification surface for beta
- Load testing and concurrency stress — Phase 55
- GDPR data export/deletion integration with Sentry — Phase 56
- PostHog / Grafana / external BI integration
- Multi-user alerting and on-call rotation (solopreneur-scale for now)
- Cost anomaly detection / ML-based alerting
- Full transaction/trace sampling (errors-only today, traces can be added later)

</domain>

<decisions>
## Implementation Decisions

### Error Capture (Sentry)

- **Tier:** Sentry Free Developer plan — 5k errors/month, 10k traces/month, 30-day retention. Will upgrade to Team ($26/mo) post-beta if quota becomes a constraint. Operator accepts risk of running out of quota during incident spikes.
- **Project structure:** Two separate Sentry projects — `pikar-ai-backend` (Python SDK `sentry-sdk>=2.x`) and `pikar-ai-frontend` (Next.js SDK `@sentry/nextjs`). Keeps stack traces, source maps, and release tags cleanly separated per stack.
- **Sampling:** `traces_sample_rate=0.0` and `profiles_sample_rate=0.0`. Errors are captured at 100% (no error sampling). No performance transactions, no profiling — zero runtime overhead beyond error capture. Reassess post-beta.
- **User context (PII boundary):** `sentry_sdk.set_user({"id": user_id})` — **user_id UUID only**. No email, no persona tier, no workspace id. Matches Phase 56 GDPR preview and keeps Sentry's PII processor surface minimal. If a stack trace accidentally contains request body data, Sentry's default `send_default_pii=False` will scrub it.
- **DSN management:** `SENTRY_DSN_BACKEND` and `SENTRY_DSN_FRONTEND` env vars. Set via `.env` locally and Cloud Run / Vercel project settings in production. Frontend DSN is `NEXT_PUBLIC_SENTRY_DSN` (safe to expose — public DSNs are designed for browser use).
- **Initialization:** Backend init in `app/fast_api_app.py` before FastAPI app instantiation (so startup errors are captured). Frontend init via `@sentry/nextjs` in `frontend/sentry.client.config.ts`, `sentry.server.config.ts`, and `sentry.edge.config.ts`.

### Latency Aggregation Strategy (OBS-02)

- **Approach:** **Hybrid** — live PostgreSQL `percentile_cont()` queries against `agent_events` for time windows ≤24 hours, materialized rollup table for windows >24 hours.
- **New table:** `agent_latency_rollups` with columns: `id`, `agent_name`, `status`, `bucket_start` (timestamp, hourly grain), `bucket_end`, `sample_count`, `p50_ms`, `p95_ms`, `p99_ms`, `error_count`, `total_duration_ms`. Unique index on `(agent_name, status, bucket_start)`.
- **Rollup job:** Cloud Scheduler trigger every hour → POST to new `/admin/observability/run-rollup` (protected by `verify_service_auth` like existing `/admin/monitoring/run-check`). Computes the previous hour's bucket and upserts into `agent_latency_rollups`. Backfill script for first-run catch-up.
- **Query router:** New method `ObservabilityMetricsService.compute_latency_percentiles(agent_name, window_start, window_end)` branches on `window_age`:
  - `< 24h from now` → live query on `agent_events`
  - `≥ 24h from now` → rollup query on `agent_latency_rollups`
  - Spans the boundary → union both queries
- **Time windows supported:** Last 1 hour, Last 24 hours, Last 7 days, Last 30 days — selectable via dashboard picker.
- **Grouping dimensions:** Dashboard supports grouping by `agent_name` (primary), `status` (success/error/timeout), and `user_id` (top 10 heaviest users). Explicitly NOT grouped by `session_id` (high cardinality — better as click-through drill-down).

### Error Rate & Alerting (OBS-03)

- **Error rate calculation:** `error_count / total_count` over the selected window, computed from `agent_events` (live for ≤24h, rollup for older — same hybrid as latency).
- **Filtering:** Same dimensions as latency — by agent_name, status, user_id. Plus filter by endpoint name (from request_logs or a new field on agent_events if not already captured).
- **Threshold alerting:** When error rate exceeds a configured threshold (default 5% over 10 minutes per agent), write an entry to `admin_audit_log` with `action='observability.threshold_breach'`, details including threshold, observed rate, affected agent, time window. Admin sees this next time they visit `/admin/observability` or `/admin/audit`. NO email/Slack notification in Phase 51 — admin is the only monitored role during beta.
- **Threshold config:** Python constants for beta (`OBSERVABILITY_ERROR_RATE_THRESHOLD=0.05`, `OBSERVABILITY_THRESHOLD_WINDOW_MINUTES=10`). Can be promoted to a DB-configured rule later if needed.

### AI Cost Tracking (OBS-04)

- **Pricing source:** Python constant dict in `app/services/observability_metrics_service.py`:
  ```python
  AI_MODEL_PRICING: dict[str, tuple[float, float]] = {
      # (input_cost_per_million_tokens, output_cost_per_million_tokens) in USD
      "gemini-2.5-pro": (1.25, 5.00),
      "gemini-2.5-flash": (0.075, 0.30),
      "gemini-2.5-flash-lite": (0.01875, 0.075),
      "text-embedding-004": (0.0, 0.0),  # free tier
  }
  ```
  Prices updated via code PR when Google publishes new pricing. Matches existing `TIER_PRICES` pattern in `billing_metrics_service.py`.
- **Service class:** **New `ObservabilityMetricsService(AdminService)`** in `app/services/observability_metrics_service.py` — sibling of `BillingMetricsService`. Keeps AI-spend math separate from subscription-revenue math.
- **Required methods:**
  - `compute_ai_cost_by_agent(start, end)` → `dict[agent_name, cost_usd]`
  - `compute_ai_cost_by_user(start, end)` → `dict[user_id, cost_usd]` (top N)
  - `compute_ai_cost_by_day(start, end)` → `list[{date, cost_usd}]`
  - `compute_latency_percentiles(agent_name, start, end)` → `{p50, p95, p99, sample_count, error_count}`
  - `compute_error_rate(agent_name, start, end)` → `{error_rate, error_count, total_count}`
  - `project_monthly_ai_spend()` → `{mtd_actual, projected_full_month, projection_method: "linear_7day"}`
- **Aggregation mode:** **On-demand** — compute from `agent_events` on every dashboard request. No rollup table for cost. Solopreneur-scale volume is small enough that on-demand queries stay fast (<200ms). Reassess if that stops being true.
- **Monthly projection:** **Linear extrapolation** — take the last 7 days of cost, average it, multiply by days remaining in the current month, add to MTD actual. Display as "MTD: $X · Projected full month: $Y · (projection based on last 7 days)". Honest about the method so the admin can mentally discount it.
- **Token field provenance:** Existing `AgentEvent.input_tokens` and `output_tokens` fields in `app/services/telemetry.py` are the source of truth. Plan must verify these are being populated for all 10 specialized agents — if not, that's a pre-req wired into an early task.

### Admin Dashboard (OBS-02/03/04/05 UI)

- **Location:** Single Next.js page at `frontend/src/app/(admin)/admin/observability/page.tsx` (or whichever admin route structure matches Phase 49 admin panel). NOT sibling routes — single page with tabs.
- **Tab structure:** `[Errors]` `[Performance]` `[AI Cost]` `[Health]` — four tabs inside one page component. Shared time-range picker at the top of the page that applies to all tabs. Tab state persisted in URL `?tab=errors` for deep linking.
- **Hero metric (above the fold):** **Error rate over last 24h with sparkline**. Chosen because it's the most actionable incident-response view. Shows current rate in large number + 24-hour sparkline + red/amber/green status color.
- **Secondary top-row metrics:** MTD AI spend with monthly projection, p95 agent latency (24h), system health traffic light (rolled up from health endpoints).
- **Chart library:** `recharts` if not already in `frontend/package.json`, otherwise reuse what `admin/billing` uses. Claude's Discretion to verify at plan time.
- **Empty state:** "No agent activity in the last {window}. Make some requests to see metrics here." Same pattern as existing admin empty states.
- **Permissions:** `Depends(require_admin)` on all `/admin/observability/*` API routes. Frontend page wrapped in admin layout that enforces session + admin role.

### Health Endpoints — Canonical Structured Shape (OBS-05)

- **Approach:** **Single canonical versioned JSON envelope for all `/health/*` endpoints**, including the existing `/health/live`, `/health/connections`, `/health/cache`, `/health/embeddings`, `/health/video`.
- **Shape:**
  ```json
  {
    "status": "ok | degraded | down",
    "version": "1",
    "service": "supabase | redis | gemini | ...",
    "latency_ms": 42,
    "details": {
      "...service-specific fields..."
    },
    "integrations": {
      "hubspot": {"status": "ok", "last_sync_at": "2026-04-08T10:23:00Z"},
      "stripe": {"status": "ok", "last_sync_at": "2026-04-08T10:25:00Z"}
    },
    "checked_at": "2026-04-08T10:26:00Z"
  }
  ```
- **Integrations list sourced from `integration_sync_state` table** — the existing table from Phase 39 that already tracks per-integration `last_sync_status`, `last_sync_at`, `last_error_message`. Zero extra API calls — dashboard reads cached state, no live pings at dashboard-load time.
- **Breaking-change handling:** Existing consumers of `/health/*` are the Cloud Scheduler health-checker (`app/services/health_checker.py`) and `admin/monitoring.py`. Plan must update both to parse the new canonical shape. Deployment is atomic (monorepo deploy).
- **`version: "1"` field:** Enables future shape evolution without breaking existing parsers — parsers check version before reading fields.
- **Backwards-compat shim:** None. All consumers deploy together from the same monorepo. No external API consumers depend on these shapes (verified by codebase scout — only Cloud Scheduler + internal admin router consume `/health/*`).

### Claude's Discretion

The planner may decide the following without re-asking:
- Specific recharts component choices (line vs area, color palette)
- Exact rollup job retry/failure semantics (idempotency, backfill handling)
- Internal file organization inside the observability service (split into multiple files vs one)
- Test file naming and structure (follow existing `tests/unit/services/test_billing_metrics_service.py` pattern)
- Whether to add a `request_id` field to Sentry events beyond user_id (decide based on whether FastAPI request middleware already has one)
- Exact CSS/Tailwind classes for dashboard cards (reuse billing dashboard styling where possible)
- Whether to lazy-mount Sentry in dev environments (recommend yes — opt-in via `SENTRY_DSN_BACKEND=...` being set, no-op if empty)

</decisions>

<specifics>
## Specific Ideas

- "Error rate over 24h with sparkline" as the hero metric — matches incident-response mindset, first thing an admin wants to see on a morning check-in.
- Pattern consistency with Phase 50: `BillingMetricsService(AdminService)` → `ObservabilityMetricsService(AdminService)`. Same base class, same constructor signature, same service-role client injection.
- Dashboard looks like `/admin/billing` in layout sensibility — compact cards, time-range picker at top, tabs for drill-down. Don't invent a new admin UI pattern; reuse what works.
- Sentry DSN split by backend/frontend is explicitly to avoid one project's release tags overwriting another's. Source maps go only with the frontend project. Release tags ship separately per stack.
- Cost projection always shows "projection based on last 7 days" next to the number — honest about the method so admins don't over-rely on it.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`app/services/telemetry.py` (TelemetryService singleton)** — Already records `AgentEvent` and `ToolEvent` to Supabase with `duration_ms`, `input_tokens`, `output_tokens`, `status`, `agent_name`, `user_id`, `session_id`, `error_message`. Phase 51 consumes this data — does NOT need to add telemetry emission, only add aggregation queries on top.
- **`app/services/billing_metrics_service.py` (`BillingMetricsService(AdminService)`)** — Template for the new `ObservabilityMetricsService`. Same base class pattern, same constructor shape, same `compute_*` method naming convention, same service-role client injection via AdminService. Copy this structure.
- **`app/routers/admin/billing.py`** — Template for the new `app/routers/admin/observability.py` router. Shows the `require_admin` dependency pattern, rate limiter integration, service instantiation, and error handling.
- **`app/routers/admin/monitoring.py`** — Already implements the "read-rollup-table + return sparkline history" pattern against `api_health_checks`. Shows the `verify_service_auth` pattern for Cloud Scheduler endpoints (used for the new hourly rollup job).
- **`app/services/health_checker.py`** — Existing Cloud Scheduler-driven health check runner. Plan must extend its output writes to match the new canonical `/health/*` JSON envelope.
- **`supabase/migrations/20260407000000_stripe_webhook_events.sql`** — Template for the new `agent_latency_rollups` table migration — shows the RLS + CHECK + service_role policy pattern, the DO-block idempotent index creation pattern, and the `api_health_checks`-style columns.
- **`integration_sync_state` table (from Phase 39)** — Already tracks per-integration `last_sync_at`, `last_sync_status`, `last_error_message`. The `/health/*` canonical shape's `integrations` subkey reads directly from this table — no new infra required.
- **`app/middleware/admin_auth.py` (`require_admin`)** — Dependency wrapper established in Phase 49. All `/admin/observability/*` endpoints use this.
- **`AdminService` base class** — Provides service-role Supabase client. All metric services inherit from this.

### Established Patterns

- **Singleton services with circuit breakers** — `TelemetryService`, `CacheService` pattern with `threading.RLock` + double-checked locking + Supabase circuit breaker (5 failures → 30s recovery timeout). The hourly rollup job should NOT be a singleton (it's a short-lived scheduler callback) but should respect the telemetry service's persistence semantics.
- **Cloud Scheduler → `/admin/*/run-*` → `verify_service_auth`** — Pattern for all scheduled background jobs. New `/admin/observability/run-rollup` follows this exact pattern.
- **`Depends(require_admin)` + `slowapi @limiter.limit(...)` on admin GET endpoints** — All `/admin/observability/*` GET routes follow this pattern.
- **Pydantic BaseModel response schemas in `app/schemas/admin/*.py`** — Plan must add `ObservabilityMetricsResponse`, `LatencyPercentileResponse`, `AICostResponse` schemas following the existing admin schema convention.
- **Supabase migration naming `YYYYMMDDHHMMSS_snake_case.sql`** — New migration for `agent_latency_rollups` should use today's or tomorrow's timestamp: `20260408000000_agent_latency_rollups.sql` (or whatever the executor picks).
- **Test file structure `tests/unit/services/test_*.py` + `tests/integration/routers/admin/test_*.py`** — Plan must create both unit tests (for the service class) and router tests (for the endpoint contracts with require_admin regression guard, like Phase 50's `test_billing_summary_requires_admin`).
- **Frontend test structure `__tests__/*.test.tsx` colocated with the component** — Dashboard components follow this pattern.

### Integration Points

- **FastAPI app instantiation (`app/fast_api_app.py`)** — Sentry backend SDK init goes BEFORE `app = FastAPI(...)` so startup errors are captured. Sentry integration wraps the ASGI app.
- **Next.js root layout (`frontend/src/app/layout.tsx`)** — Sentry frontend SDK is initialized via `frontend/sentry.client.config.ts` / `sentry.server.config.ts` / `sentry.edge.config.ts` — these files are auto-loaded by `@sentry/nextjs`, no explicit import needed in layout.
- **Next.js `next.config.ts`** — Must add `withSentryConfig(nextConfig, sentryBuildOptions)` wrapper for source map upload.
- **Admin router registration (`app/fast_api_app.py`)** — New `observability.py` router must be included alongside `billing`, `audit`, `monitoring`, `analytics`, `governance_audit`, `integrations`.
- **Frontend admin nav** — New "Observability" nav item must be added to whichever admin layout component hosts the existing admin navigation (likely `frontend/src/app/(admin)/layout.tsx` or similar).
- **Existing `/admin/monitoring/status`** — The existing endpoint from Phase 47/48 returns endpoint-level health with sparklines. The new Observability dashboard's "Health" tab may consume this directly OR may render a new view that reads from the canonical `/health/*` endpoints. Plan should decide based on which gives a cleaner UX — reusing `/admin/monitoring/status` avoids duplicate infra.

</code_context>

<deferred>
## Deferred Ideas

- **Email/Slack alerting when error rate threshold is crossed** — Beta uses `admin_audit_log` entries only. Active notifications are Phase 52+ (persona-specific gating + notification rules) or part of a dedicated "alerting" phase. Deferred.
- **Cost anomaly detection / ML-based burn alerts** — Linear 7-day projection is honest enough for beta. Smarter projection is a v8.0+ idea.
- **Sentry Team plan upgrade** — Stay on free Developer until post-beta quota analysis. Upgrade decision depends on observed error volume.
- **Performance traces at >0% sampling** — Errors-only today. If p95 latency from our `agent_events` table isn't enough, revisit after first month of production data.
- **Load testing and concurrency stress** — Phase 55 (LOAD-01..04).
- **GDPR integration with Sentry (data subject access / deletion)** — Phase 56 (GDPR & RAG Hardening).
- **PostHog, Grafana, Datadog, or other external observability tools** — Current plan keeps everything in-app + Sentry for errors. External tools deferred unless a specific need emerges.
- **Source map upload automation in CI** — Plan should set up `withSentryConfig` for frontend builds, but CI-level `sentry-cli releases finalize` automation can come later.
- **Multi-admin on-call rotation** — Solopreneur-scale for now. Team rotation is Phase 53 (Multi-User & Teams) territory.
- **`request_id` tracing across backend + frontend Sentry events** — Useful for correlating a browser error back to a backend stack trace. Add if plan's research surfaces it as a cheap win, otherwise defer.
- **Dashboard charts for `session_id` drill-down** — High cardinality, better as a click-through action than a primary grouping. Out of Phase 51 scope — can be added later as "click agent_name → drill into session_id list".

</deferred>

---

*Phase: 51-observability-monitoring*
*Context gathered: 2026-04-08*

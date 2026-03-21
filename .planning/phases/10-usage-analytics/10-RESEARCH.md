# Phase 10: Usage Analytics - Research

**Researched:** 2026-03-21
**Domain:** Admin analytics dashboard — pre-aggregated DAU/MAU, agent effectiveness, feature usage, config status
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- DAU/MAU from count-distinct on `sessions` and `session_events` tables (by `user_id`)
- Agent effectiveness from `agent_telemetry` table: `status` (success/error/timeout) + `duration_ms`
- Feature usage from `tool_telemetry` (tool call counts by tool_name) + `analytics_events` (by category)
- Config status from `admin_agent_permissions` + `admin_config_history` tables (Phase 7 tables)
- Pre-aggregated daily summary tables: `admin_analytics_daily` + `admin_agent_stats_daily`
- Cloud Scheduler triggers daily aggregation — reuse `verify_service_auth` / `WORKFLOW_SERVICE_SECRET` pattern from Phase 8
- Fallback if materialized views unsupported: scheduled summary INSERT (already decided as primary approach)
- Route: `/admin/analytics`
- `recharts@3.8+` already installed (Phase 8)
- KPI cards: DAU, MAU, total messages, total workflows
- Line charts: user activity trends (30 days), message volume over time
- Bar charts: per-agent effectiveness (success rate, avg response time)
- Feature usage breakdown: table or bar chart by category (chat, workflows, approvals, etc.)
- Config status: compact card showing active feature flags count + last config change
- Auto-refresh: 60 seconds (slower than monitoring's 30s — analytics data changes slowly)
- Backend: `app/routers/admin/analytics.py`
- Agent tools: `app/agents/admin/tools/analytics.py` with 4 tools: `get_usage_stats`, `get_agent_effectiveness`, `get_engagement_report`, `generate_report`
- Migration: `supabase/migrations/XXXX_analytics_summary_tables.sql`
- Register analytics router in `app/routers/admin/__init__.py`
- Register analytics tools in `app/agents/admin/agent.py`
- Frontend: `frontend/src/app/(admin)/analytics/page.tsx`
- Reuse existing recharts components from Phase 8 (Sparkline pattern)

### Claude's Discretion
- Exact chart dimensions, colors, and responsive breakpoints
- How to compute "agent effectiveness" (what counts as success vs failure)
- Whether to use tabs or sections for different analytics views
- The exact KPI card design (reuse Phase 8 StatusCard pattern or custom)
- How to handle empty/no-data states in charts
- Date range picker implementation (simple preset buttons vs full calendar)
- Whether config status needs its own section or a small card

### Deferred Ideas (OUT OF SCOPE)
- Retention cohort analysis (RETN-01) — needs 3+ months of user data
- Conversion funnel analysis (RETN-02) — future requirement
- Bulk CSV export of analytics data (RETN-03) — future requirement
- Real-time analytics streaming — polling is sufficient at this scale
- ANLT-03 (billing dashboard) — Phase 14, depends on Stripe integration
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ANLT-01 | Admin can view usage dashboards (DAU, MAU, message volume, workflow activity) | `sessions` table provides DAU/MAU via distinct user_id per day/month; `workflow_executions` provides workflow counts; pre-aggregated into `admin_analytics_daily` |
| ANLT-02 | Admin can view per-agent effectiveness metrics (success rate, avg response time) | `agent_telemetry` table (Phase 20260320) has `agent_name`, `status` (success/error/timeout), `duration_ms` per invocation; pre-aggregated into `admin_agent_stats_daily` |
| ANLT-04 | Admin can view feature usage activities and API call activities | `tool_telemetry` (tool call counts) and `analytics_events` (by event_name/category) provide feature and API usage; session_events gives message volume |
| ANLT-05 | Admin can view configuration status overview | `admin_agent_permissions` (count of blocked/confirm/auto tiers) and `admin_config_history` (latest change timestamp) provide config status; no pre-aggregation needed — row counts are small |
</phase_requirements>

---

## Summary

Phase 10 adds a usage analytics dashboard to the admin panel. All data comes from existing Supabase tables — no new event collection infrastructure. The primary data sources are confirmed: `agent_telemetry` (agent success/error/duration per invocation, written since Phase 20260320), `sessions` + `session_events` (user activity, written since the original ADK session infrastructure), `tool_telemetry` (tool call counts and success/failure), `analytics_events` (user-facing feature events by category), `workflow_executions` (workflow counts and completion status), `admin_agent_permissions` and `admin_config_history` (config status, small tables — no aggregation needed).

The pre-aggregation strategy is settled: two new summary tables (`admin_analytics_daily` for DAU/MAU/messages/workflows and `admin_agent_stats_daily` for per-agent metrics) populated by a scheduled endpoint that reuses the Phase 8 `verify_service_auth` / Cloud Scheduler pattern verbatim. Materialized views are confirmed available on all Supabase PostgreSQL tiers (standard PostgreSQL DDL), but `REFRESH MATERIALIZED VIEW CONCURRENTLY` requires a unique index; given the project already chose scheduled summary inserts as the primary approach, this is the right call — simpler, no concurrent-refresh edge cases, and consistent with how Phase 8 writes health check data.

The recharts implementation is fully established by Phase 8. The `Sparkline`, `StatusCard`, and `StaleDataBanner` component patterns are directly reusable for analytics charts. The admin tool pattern (self-contained `_check_autonomy()`, service client, `execute_async`) is well-established across `monitoring.py` and `users.py`. The router registration pattern in `__init__.py` is a one-liner. The frontend page pattern from `monitoring/page.tsx` (useCallback fetch + setInterval polling + loading/error/empty states) is directly reusable.

**Primary recommendation:** Build the aggregation endpoint first (Wave 1: migration + aggregation endpoint + seed initial data), then the API endpoints + agent tools (Wave 2), then the frontend dashboard (Wave 3). This mirrors the Phase 8 structure and ensures backend data is available before building charts.

---

## Standard Stack

### Core — already installed, no additions needed

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| recharts | 3.8+ | Line/bar/area charts | Already installed Phase 8; React 19 native; `accessibilityLayer=false` + `isAnimationActive=false` established pattern |
| supabase-py | existing | Summary table reads/writes | Already used everywhere |
| FastAPI | existing | Analytics API router | Existing pattern |
| slowapi | existing | Rate limiting | `@limiter.limit("120/minute")` pattern from monitoring.py |

### No New Packages Required

All libraries needed for Phase 10 are already installed. This is confirmed by:
- recharts 3.x confirmed in Phase 8 Sparkline component (`from 'recharts'`)
- No external analytics SDK needed (data is internal Supabase tables)
- Aggregation is pure SQL + Python, no special libraries

**Installation:** None required.

---

## Architecture Patterns

### Recommended File Structure

```
app/
├── routers/admin/analytics.py         # GET /admin/analytics/summary, POST /admin/analytics/aggregate
├── agents/admin/tools/analytics.py    # 4 agent tools: get_usage_stats, get_agent_effectiveness, get_engagement_report, generate_report
supabase/migrations/
├── XXXX_analytics_summary_tables.sql  # admin_analytics_daily + admin_agent_stats_daily
frontend/src/
├── app/(admin)/analytics/page.tsx     # main analytics dashboard
├── components/admin/analytics/
│   ├── KpiCard.tsx                    # reuses StatusCard dark-theme pattern
│   ├── ActivityChart.tsx              # dual-line DAU/MAU chart
│   ├── AgentEffectivenessChart.tsx    # horizontal bar chart (10 agents)
│   ├── FeatureUsageChart.tsx          # bar chart by category
│   └── ConfigStatusCard.tsx          # compact config overview card
```

### Pattern 1: Daily Summary Table Schema

The two new tables follow the same pattern as other admin tables — RLS enabled, service-role-only access.

```sql
-- Source: migrations/20260321300000_admin_panel_foundation.sql pattern
CREATE TABLE IF NOT EXISTS admin_analytics_daily (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    stat_date    date NOT NULL UNIQUE,
    dau          integer NOT NULL DEFAULT 0,   -- distinct users with session activity
    mau          integer NOT NULL DEFAULT 0,   -- distinct users in trailing 30 days
    messages     integer NOT NULL DEFAULT 0,   -- session_events count for stat_date
    workflows    integer NOT NULL DEFAULT 0,   -- workflow_executions created on stat_date
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_admin_analytics_daily_stat_date
    ON admin_analytics_daily(stat_date DESC);

CREATE TABLE IF NOT EXISTS admin_agent_stats_daily (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    stat_date       date NOT NULL,
    agent_name      text NOT NULL,
    success_count   integer NOT NULL DEFAULT 0,
    error_count     integer NOT NULL DEFAULT 0,
    timeout_count   integer NOT NULL DEFAULT 0,
    avg_duration_ms numeric(10, 2),
    total_calls     integer NOT NULL DEFAULT 0,
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (stat_date, agent_name)
);

CREATE INDEX IF NOT EXISTS idx_admin_agent_stats_daily_date
    ON admin_agent_stats_daily(stat_date DESC, agent_name);

ALTER TABLE admin_analytics_daily      ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_agent_stats_daily    ENABLE ROW LEVEL SECURITY;
-- No policies: service-role access only (same as all 9 Phase 7 admin tables)
```

### Pattern 2: Aggregation Endpoint (reuse Phase 8 Cloud Scheduler pattern)

The aggregation endpoint follows the `POST /admin/monitoring/run-check` pattern exactly: authenticated via `verify_service_auth` (not `require_admin`), Cloud Scheduler cannot hold admin JWT.

```python
# Source: app/routers/admin/monitoring.py — run-check pattern
@router.post("/analytics/aggregate")
@limiter.limit("5/minute")
async def run_analytics_aggregation(
    request: Request,
    _auth: bool = Depends(verify_service_auth),
) -> dict:
    """Cloud Scheduler entry point — computes daily analytics and upserts to summary tables."""
    from app.services.analytics_aggregator import run_daily_aggregation
    result = await run_daily_aggregation()
    return {"status": "ok", "date": result["date"], "rows_written": result["rows_written"]}
```

### Pattern 3: Analytics Router GET Endpoint (reuse monitoring.py structure)

```python
# Source: app/routers/admin/monitoring.py — GET /monitoring/status pattern
@router.get("/analytics/summary")
@limiter.limit("120/minute")
async def get_analytics_summary(
    request: Request,
    days: int = 30,
    admin_user: dict = Depends(require_admin),
) -> dict:
    """Return pre-aggregated analytics summary for the dashboard.
    Reads from admin_analytics_daily and admin_agent_stats_daily.
    Falls back to computing on-the-fly (with warning) if no aggregated data exists.
    """
    ...
```

### Pattern 4: Agent Tool Pattern (reuse monitoring.py / users.py)

All 4 analytics tools follow the established admin tool pattern exactly — self-contained `_check_autonomy()` copy (not imported), service client, `execute_async`.

```python
# Source: app/agents/admin/tools/monitoring.py — _check_autonomy pattern
async def get_usage_stats(days: int = 30) -> dict[str, Any]:
    """Return DAU, MAU, message volume, and workflow counts for a date range."""
    gate = await _check_autonomy("get_usage_stats")
    if gate is not None:
        return gate
    client = get_service_client()
    # Query admin_analytics_daily ORDER BY stat_date DESC LIMIT days
    ...
```

### Pattern 5: Frontend Page (reuse monitoring/page.tsx exactly)

The analytics page uses the identical structure to `monitoring/page.tsx`:
- `useCallback` wraps the fetch to prevent stale closure in `setInterval`
- 60-second polling interval (not 30s — analytics data is slower-changing)
- Loading skeleton, error state, empty state, data state
- `supabase.auth.getSession()` for Bearer token

```typescript
// Source: frontend/src/app/(admin)/monitoring/page.tsx — polling pattern
const REFRESH_INTERVAL_MS = 60_000;  // 60s for analytics (30s in monitoring)

const fetchAnalytics = useCallback(async () => {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) { setFetchError('Not authenticated'); return; }
  const res = await fetch(`${API_URL}/admin/analytics/summary?days=30`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
  });
  ...
}, [supabase, API_URL]);

useEffect(() => {
  fetchAnalytics();
  const interval = setInterval(fetchAnalytics, REFRESH_INTERVAL_MS);
  return () => clearInterval(interval);
}, [fetchAnalytics]);
```

### Pattern 6: Recharts 3.x — Confirmed Working Patterns

These patterns are proven in the codebase (`Sparkline.tsx`) and must be used for all analytics charts:

```typescript
// Source: frontend/src/components/admin/monitoring/Sparkline.tsx
// CRITICAL recharts 3.x rules (all verified in Phase 8):
// 1. accessibilityLayer={false} — removes ARIA noise on polling dashboards
// 2. isAnimationActive={false} — removes animation overhead on polling
// 3. history reversed DESC→ASC before chart render (API returns newest-first)
// 4. NO activeIndex prop (removed in recharts 3.x — causes runtime error)
// 5. NO CategoricalChartState import (removed in recharts 3.x)

import { Line, LineChart, Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip } from 'recharts';

// Dual-line DAU/MAU chart
<LineChart data={dauMauData} accessibilityLayer={false}>
  <Line dataKey="dau" stroke="#60a5fa" dot={false} isAnimationActive={false} />
  <Line dataKey="mau" stroke="#a78bfa" dot={false} isAnimationActive={false} />
</LineChart>

// Horizontal bar chart for agent effectiveness
<BarChart data={agentData} layout="vertical" accessibilityLayer={false}>
  <Bar dataKey="success_rate" fill="#4ade80" isAnimationActive={false} />
</BarChart>
```

### Pattern 7: Data Sources Mapping

| Metric | Source Table | Key Columns | Aggregation |
|--------|-------------|-------------|-------------|
| DAU | `sessions` | `user_id`, `updated_at` | COUNT DISTINCT user_id WHERE DATE(updated_at) = stat_date |
| MAU | `sessions` | `user_id`, `updated_at` | COUNT DISTINCT user_id WHERE updated_at >= now() - 30 days |
| Message count | `session_events` | `user_id`, `created_at` | COUNT(*) WHERE DATE(created_at) = stat_date |
| Workflow count | `workflow_executions` | `user_id`, `created_at` | COUNT(*) WHERE DATE(created_at) = stat_date |
| Agent success rate | `agent_telemetry` | `agent_name`, `status`, `duration_ms`, `created_at` | COUNT by status WHERE DATE(created_at) = stat_date GROUP BY agent_name |
| Tool feature usage | `tool_telemetry` | `tool_name`, `agent_name`, `status`, `created_at` | COUNT(*) GROUP BY tool_name, last 30 days |
| User event usage | `analytics_events` | `event_name`, `category`, `created_at` | COUNT(*) GROUP BY category, last 30 days |
| Config status | `admin_agent_permissions` | `autonomy_level`, `action_category` | COUNT(*) GROUP BY autonomy_level (no aggregation table needed) |
| Last config change | `admin_config_history` | `created_at` | MAX(created_at) single query |

### Anti-Patterns to Avoid

- **COUNT(*) full-table scan at dashboard load time:** Always read from `admin_analytics_daily` / `admin_agent_stats_daily`. The raw tables (`sessions`, `session_events`, `agent_telemetry`) will grow large over time — reading them directly for the dashboard is the performance trap documented in SUMMARY.md.
- **Querying `agent_telemetry` at dashboard load:** It has 90-day retention but can accumulate thousands of rows; always use the daily summary for trend display.
- **Rendering recharts with animation:** `isAnimationActive={false}` is mandatory for polling dashboards — flickering during 60s refresh is a bad UX. This is an established Phase 8 decision.
- **Importing `CategoricalChartState` from recharts 3.x:** Does not exist in 3.x — runtime import error. Established Phase 8 pitfall.
- **Using `activeIndex` prop on recharts 3.x charts:** Removed in 3.x — causes runtime error.
- **Querying `admin_config_history` with a complex join:** Config status only needs two simple queries — row counts from `admin_agent_permissions` + `MAX(created_at)` from `admin_config_history`. No aggregation table.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Charts | Custom SVG chart components | `recharts` (already installed) | Phase 8 established pattern; React 19 native; responsive container handles sizing |
| Polling | Custom WebSocket or SSE for analytics | setInterval + fetch (Phase 8 pattern) | Analytics data is slow-changing; 60s polling is identical UX at this scale |
| Rate limiting | Custom rate limiter | `@limiter.limit("120/minute")` via slowapi | Already in every admin endpoint; one decorator |
| Admin auth | Custom middleware | `Depends(require_admin)` | Phase 7 foundation; one import |
| Cloud Scheduler auth | JWT or API keys for scheduler | `Depends(verify_service_auth)` + WORKFLOW_SERVICE_SECRET | Phase 8 established pattern for service-to-service calls |
| Aggregation scheduling | Celery / APScheduler | Cloud Scheduler + `/analytics/aggregate` endpoint | Phase 8 pattern already works; same scheduler, same secret |

**Key insight:** Every infrastructure concern in Phase 10 is already solved by Phase 7/8 patterns. The work is entirely in SQL aggregation queries and connecting known components — not building new infrastructure.

---

## Common Pitfalls

### Pitfall 1: Empty aggregation table on first load
**What goes wrong:** Dashboard renders with all-zero KPIs because no aggregation has run yet.
**Why it happens:** The `admin_analytics_daily` table is empty until the first Cloud Scheduler trigger fires.
**How to avoid:** The GET `/admin/analytics/summary` endpoint should check if the summary table is empty and fall back to a direct (slower) count query with a `data_source: "live"` flag in the response. Frontend shows a "Data is being computed for the first time" notice instead of zeros.
**Warning signs:** All KPIs showing 0 on first deployment.

### Pitfall 2: agent_telemetry has no data for new deployments
**What goes wrong:** Agent effectiveness chart shows nothing.
**Why it happens:** `agent_telemetry` is written by the telemetry instrumentation. If agents haven't been used since telemetry was added (migration 20260320400000), the table is empty.
**How to avoid:** Handle empty agent_telemetry gracefully in aggregation — `admin_agent_stats_daily` rows simply won't be inserted for days with no data. Frontend must handle empty `agent_data` array (empty state message: "No agent activity recorded yet").

### Pitfall 3: sessions.user_id is TEXT, not UUID
**What goes wrong:** JOIN or comparison between `sessions.user_id` (TEXT) and `auth.users.id` (UUID) fails with type mismatch.
**Why it happens:** The `sessions` table (`0005_sessions.sql`) defines `user_id TEXT NOT NULL` — it stores the ADK user ID as text, not a foreign key to `auth.users`. This is documented as an intentional design (ADK user IDs are string-typed).
**How to avoid:** DAU/MAU aggregation queries must use `COUNT(DISTINCT user_id)` directly on `sessions.user_id` without joining to `auth.users`. Do not cast — the text values are the correct user identifiers for counting distinct users.
**Warning signs:** `ERROR: operator does not exist: uuid = text` in aggregation function.

### Pitfall 4: stat_date UNIQUE constraint conflicts on re-run
**What goes wrong:** Running aggregation twice for the same date raises a unique constraint violation.
**Why it happens:** `admin_analytics_daily` has `UNIQUE(stat_date)` to prevent duplicate rows.
**How to avoid:** Use `INSERT ... ON CONFLICT (stat_date) DO UPDATE SET ...` (upsert) in the aggregation function. This makes the aggregation idempotent — safe to run multiple times per day and to backfill historical dates.

### Pitfall 5: recharts 3.x breaking changes (established Phase 8 pitfall)
**What goes wrong:** Runtime errors or missing chart elements.
**Why it happens:** recharts 3.x removed `activeIndex` prop, `CategoricalChartState` export, and changed z-index behavior.
**How to avoid:** Copy the exact Sparkline.tsx pattern — `accessibilityLayer={false}`, `isAnimationActive={false}`, no `activeIndex`, no `CategoricalChartState`.
**Warning signs:** TypeScript error on `activeIndex`; missing chart import at runtime.

### Pitfall 6: tool_telemetry "feature usage" is agent-internal, not user-facing
**What goes wrong:** Feature usage chart shows internal tool names (e.g., `get_api_health_summary`) instead of meaningful user-facing feature categories.
**Why it happens:** `tool_telemetry.tool_name` records the Python function name, not a user-readable feature label.
**How to avoid:** Group by `agent_name` from `tool_telemetry` for the agent-level view. For user-facing feature categories, use `analytics_events.category` which already uses human-readable categories (chat, workflows, approvals, etc.). Use both tables for complementary views.

---

## Code Examples

### Aggregation SQL — DAU/MAU

```sql
-- Source: derived from sessions table schema (0005_sessions.sql)
-- DAU for a given date
SELECT COUNT(DISTINCT user_id) AS dau
FROM sessions
WHERE DATE(updated_at) = $1::date;

-- MAU (trailing 30 days ending on stat_date)
SELECT COUNT(DISTINCT user_id) AS mau
FROM sessions
WHERE updated_at >= ($1::date - INTERVAL '29 days')
  AND updated_at < ($1::date + INTERVAL '1 day');
```

### Aggregation SQL — Agent Stats

```sql
-- Source: derived from agent_telemetry schema (20260320400000_telemetry_schema.sql)
SELECT
    agent_name,
    COUNT(*) FILTER (WHERE status = 'success') AS success_count,
    COUNT(*) FILTER (WHERE status = 'error')   AS error_count,
    COUNT(*) FILTER (WHERE status = 'timeout') AS timeout_count,
    ROUND(AVG(duration_ms)::numeric, 2)        AS avg_duration_ms,
    COUNT(*)                                   AS total_calls
FROM agent_telemetry
WHERE DATE(created_at) = $1::date
GROUP BY agent_name;
```

### Upsert Pattern for Aggregation

```python
# Source: pattern consistent with admin tables (RLS bypass via service client)
# INSERT ... ON CONFLICT DO UPDATE makes aggregation idempotent
client = get_service_client()
await execute_async(
    client.table("admin_analytics_daily").upsert(
        {"stat_date": stat_date, "dau": dau, "mau": mau, ...},
        on_conflict="stat_date",
    ),
    op_name="analytics.upsert_daily",
)
```

### Config Status Query (no summary table needed)

```python
# Source: pattern from monitoring.py / users.py
# Two simple queries — admin_agent_permissions is tiny (~10-20 rows)
perms = await execute_async(
    client.table("admin_agent_permissions").select("autonomy_level"),
    op_name="analytics.config_permissions",
)
history = await execute_async(
    client.table("admin_config_history")
        .select("created_at")
        .order("created_at", desc=True)
        .limit(1),
    op_name="analytics.config_last_change",
)
```

### Router Registration (one-liner)

```python
# Source: app/routers/admin/__init__.py — existing pattern
from app.routers.admin import analytics
admin_router.include_router(analytics.router)  # Phase 10: analytics endpoints
```

### Agent Registration

```python
# Source: app/agents/admin/agent.py — existing tools list pattern
from app.agents.admin.tools.analytics import (
    get_usage_stats,
    get_agent_effectiveness,
    get_engagement_report,
    generate_report,
)
# Add to tools=[...] list in both admin_agent singleton and create_admin_agent()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| COUNT(*) at query time | Pre-aggregated daily summary tables | Phase 10 decision | Eliminates full-table scan on large event tables |
| Materialized views (considered) | Scheduled summary INSERT (upsert) | Phase 10 decision | Simpler, no concurrent-refresh edge cases, consistent with Phase 8 health check write pattern |
| recharts 2.x | recharts 3.x (`accessibilityLayer`, no `activeIndex`) | Phase 8 established | Must use 3.x patterns — breaking changes from 2.x |

**Confirmed available on all Supabase tiers:**
- `CREATE MATERIALIZED VIEW` — standard PostgreSQL, no tier restriction (but not chosen as primary approach)
- `REFRESH MATERIALIZED VIEW CONCURRENTLY` — requires unique index; available but not needed since we use upsert pattern

---

## Open Questions

1. **How far back does `agent_telemetry` actually have data?**
   - What we know: Table created in migration `20260320400000` (2026-03-20). Table has 90-day retention. The telemetry instrumentation must be actively writing rows for this data to be meaningful.
   - What's unclear: Whether the ExecutiveAgent and specialized agents are instrumented to write to `agent_telemetry`, or if it's empty in practice.
   - Recommendation: The aggregation service should handle empty `agent_telemetry` gracefully (upsert zeros or skip); the frontend must show an empty state. Check at implementation time.

2. **`sessions.user_id` vs `auth.users.id` type mismatch scope**
   - What we know: `sessions.user_id` is TEXT (ADK string IDs). DAU/MAU uses COUNT DISTINCT on this column directly — no join needed.
   - What's unclear: Whether some sessions were created with UUID-format strings (which would count correctly) vs opaque ADK session IDs (which may not correspond 1:1 to platform users).
   - Recommendation: Use `COUNT(DISTINCT user_id)` from `sessions` as a proxy for DAU/MAU. Accept that this measures "active ADK sessions" not "unique platform users" — at this scale, this is a fine proxy. Document in tool docstring.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (uv run pytest) |
| Config file | `pyproject.toml` [tool.pytest] |
| Quick run command | `uv run pytest tests/unit/admin/test_analytics_api.py -x` |
| Full suite command | `uv run pytest tests/unit/admin/ -x` |
| Frontend framework | vitest |
| Frontend quick run | `cd frontend && npm run test -- --run src/__tests__/components/admin/analytics` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANLT-01 | GET /admin/analytics/summary returns DAU, MAU, messages, workflows for 30 days | unit | `uv run pytest tests/unit/admin/test_analytics_api.py::test_get_summary_returns_kpis -x` | Wave 0 |
| ANLT-01 | Summary returns empty-state correctly when no aggregated data exists | unit | `uv run pytest tests/unit/admin/test_analytics_api.py::test_get_summary_empty_state -x` | Wave 0 |
| ANLT-01 | POST /analytics/aggregate returns 200 with valid service secret | unit | `uv run pytest tests/unit/admin/test_analytics_api.py::test_aggregate_with_valid_secret -x` | Wave 0 |
| ANLT-01 | POST /analytics/aggregate returns 401 without valid secret | unit | `uv run pytest tests/unit/admin/test_analytics_api.py::test_aggregate_unauthorized -x` | Wave 0 |
| ANLT-02 | get_agent_effectiveness tool returns per-agent success_rate and avg_duration_ms | unit | `uv run pytest tests/unit/admin/test_analytics_tools.py::test_get_agent_effectiveness -x` | Wave 0 |
| ANLT-02 | Agent effectiveness handles empty agent_telemetry gracefully | unit | `uv run pytest tests/unit/admin/test_analytics_tools.py::test_get_agent_effectiveness_empty -x` | Wave 0 |
| ANLT-04 | get_engagement_report tool returns feature usage by category | unit | `uv run pytest tests/unit/admin/test_analytics_tools.py::test_get_engagement_report -x` | Wave 0 |
| ANLT-05 | Config status returns active permission count and last config change timestamp | unit | `uv run pytest tests/unit/admin/test_analytics_api.py::test_config_status_section -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/admin/test_analytics_api.py tests/unit/admin/test_analytics_tools.py -x`
- **Per wave merge:** `uv run pytest tests/unit/admin/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/admin/test_analytics_api.py` — covers ANLT-01, ANLT-05 (router tests)
- [ ] `tests/unit/admin/test_analytics_tools.py` — covers ANLT-02, ANLT-04 (agent tool tests)
- [ ] `tests/unit/admin/conftest.py` — already exists (admin conftest present)

---

## Sources

### Primary (HIGH confidence)
- Codebase: `supabase/migrations/20260320400000_telemetry_schema.sql` — confirmed `agent_telemetry` and `tool_telemetry` table schemas with exact column names
- Codebase: `supabase/migrations/20260313103000_schema_truth_alignment.sql` — confirmed `analytics_events`, `user_activity_log` schemas
- Codebase: `supabase/migrations/0005_sessions.sql` — confirmed `sessions.user_id TEXT` (not UUID)
- Codebase: `supabase/migrations/0007_workflow_steps.sql` — confirmed `workflow_executions` schema
- Codebase: `supabase/migrations/20260321300000_admin_panel_foundation.sql` — confirmed `admin_agent_permissions`, `admin_config_history` schemas
- Codebase: `app/routers/admin/monitoring.py` — exact Cloud Scheduler / verify_service_auth pattern
- Codebase: `frontend/src/components/admin/monitoring/Sparkline.tsx` — exact recharts 3.x patterns in use
- Codebase: `frontend/src/app/(admin)/monitoring/page.tsx` — exact useCallback/setInterval polling pattern
- Codebase: `app/agents/admin/tools/monitoring.py` — exact _check_autonomy / execute_async tool pattern
- Codebase: `app/agents/admin/agent.py` — tool registration pattern
- Codebase: `app/routers/admin/__init__.py` — router registration pattern
- Codebase: `frontend/src/components/admin/adminNav.ts` — `/admin/analytics` route already in sidebar nav

### Secondary (MEDIUM confidence)
- Supabase GitHub Discussion #16389 — confirms materialized view limitations (no realtime, less Studio support, no pg_ivm); `REFRESH MATERIALIZED VIEW CONCURRENTLY` not explicitly documented as unsupported
- Supabase blog on PostgreSQL views — confirms `CREATE MATERIALIZED VIEW` is standard PostgreSQL available on all tiers

### Tertiary (LOW confidence)
- WebSearch: Supabase materialized view tier support — no official tier restriction documented; treated as available but upsert pattern is preferred per project decision

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all libraries confirmed in codebase
- Data sources: HIGH — all tables verified by reading actual migration SQL files
- Architecture patterns: HIGH — all patterns derived from existing Phase 7/8 code
- Pitfalls: HIGH — pitfalls 1-4 derived from actual schema analysis; pitfall 5 from established Phase 8 decision record
- Materialized view availability: MEDIUM — standard PostgreSQL, but `CONCURRENT` refresh requires unique index; project already chose upsert approach

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (30 days — stable patterns from existing codebase)

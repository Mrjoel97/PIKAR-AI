# Phase 8: Health Monitoring - Research

**Researched:** 2026-03-21
**Domain:** Concurrent health polling, Cloud Scheduler integration, Supabase writes, sparkline dashboard
**Confidence:** HIGH — all findings grounded in existing codebase (direct inspection) plus official sources

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Health checks write **directly to Supabase** (service-role client), bypassing the monitored FastAPI service — this is a hard architectural constraint (HLTH-06)
- `recharts 3.x` has three breaking changes the planner must account for: **activeIndex removal**, **CategoricalChartState removal**, **z-index determined by JSX render order** — recharts is NOT currently in the project; it must be added

### Claude's Discretion

- Exact sparkline chart dimensions and styling
- Whether to poll the `/admin/monitoring` API route on a timer or use Supabase Realtime subscriptions for the dashboard
- Retry/timeout values for individual health HTTP calls within the Cloud Scheduler handler
- How much history to keep in `api_health_checks` (retention window)

### Deferred Ideas (OUT OF SCOPE)

- Real-time WebSocket monitoring (documented out of scope in REQUIREMENTS.md)
- Per-alert notification emails or push notifications
- Manual "ack" or snooze on incidents
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HLTH-01 | System pings all /health/* endpoints concurrently via httpx + asyncio.gather() | httpx 0.28.1 is already resolved in uv.lock (transitive dep); `asyncio.gather()` is stdlib — no new deps needed |
| HLTH-02 | Cloud Scheduler triggers health check loop every 60 seconds | Existing `_verify_scheduler` pattern + `SCHEDULER_SECRET` env var already established; add a new `/scheduled/health-check` POST endpoint following the same pattern |
| HLTH-03 | System auto-creates incidents when endpoints fail and tracks recovery | `api_incidents` table already exists in the Phase 7 migration; auto-create on first failure, auto-resolve (set `resolved_at`) on recovery |
| HLTH-04 | Admin can view monitoring dashboard with sparkline charts and status cards | `/admin/monitoring` page, new API endpoint `GET /admin/monitoring/status`, recharts LineChart as sparkline (no axes) — recharts must be added to frontend |
| HLTH-05 | Dashboard shows stale-data warning if latest check >5 minutes old | Frontend reads `checked_at` of most recent row; if `now - checked_at > 5 min`, renders warning banner |
| HLTH-06 | Health results write directly to Supabase (not through monitored service) | Confirmed: use `get_service_client()` inside scheduler endpoint, same as all other admin services |
</phase_requirements>

---

## Summary

Phase 8 adds a continuous health monitoring loop: Cloud Scheduler calls a new `/scheduled/health-check` POST endpoint every 60 seconds, which concurrently hits all five `/health/*` FastAPI endpoints using `httpx.AsyncClient`, then writes results directly to `api_health_checks` in Supabase (bypassing the monitored service). When an endpoint transitions from healthy to unhealthy, an `api_incidents` row is created; when it recovers, `resolved_at` is stamped. The admin dashboard at `/admin/monitoring` reads this data via a new `GET /admin/monitoring/status` API route and renders status cards with sparkline charts using recharts.

All three major building blocks (database schema, Cloud Scheduler auth pattern, Supabase service-role writes) are already established in Phase 7. The primary new work is: (1) the health polling service with concurrent httpx calls, (2) incident lifecycle management, (3) the `GET /admin/monitoring/status` API endpoint, and (4) the monitoring dashboard page with recharts sparklines.

`recharts` is **not yet in the project** — it must be added (`npm install recharts`). This is the only new dependency. `httpx` is available as a transitive dependency (0.28.1 in uv.lock) but is not in `pyproject.toml` directly. The planner should add `httpx` explicitly.

**Primary recommendation:** Follow the existing `_verify_scheduler` pattern for the health-check endpoint. Use httpx `AsyncClient` with a 10-second timeout per endpoint. Write to Supabase using `execute_async()` (existing helper). For the dashboard, use recharts `LineChart` without `XAxis`/`YAxis` as a sparkline — do not use `activeIndex` or `CategoricalChartState` (both removed in recharts 3.x).

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 (already in lockfile) | Async HTTP client for pinging /health/* endpoints | Already used in `app/a2a/client.py`; HLTH-01 explicitly names httpx |
| asyncio (stdlib) | Python 3.10+ | Concurrent health checks via `asyncio.gather()` | HLTH-01 explicitly names asyncio.gather(); no additional install |
| supabase-py | 2.27.2+ (already installed) | Write health check results and incidents directly to Supabase | Matches HLTH-06 requirement; `get_service_client()` already in use |
| recharts | ^3.5.0 (not yet installed) | Sparkline charts on monitoring dashboard | Only charting library considered; directly named in STATE.md concern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| execute_async | (project util) | Run blocking Supabase queries without blocking event loop | All Supabase writes inside async route handlers |
| secrets (stdlib) | Python 3.10+ | Constant-time comparison for SCHEDULER_SECRET | Already used by `_verify_scheduler` in `scheduled_endpoints.py` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| recharts sparkline | Supabase Realtime subscription | Real-time is listed as out-of-scope in REQUIREMENTS.md |
| recharts sparkline | tremor SparkLineChart | Tremor wraps recharts — adds an abstraction layer with no benefit given we already control recharts directly |
| httpx concurrent polling | Calling health functions in-process | HLTH-06 requires writing directly to Supabase, but the health functions themselves are in the monitored process. Calling via HTTP from the scheduler endpoint is cleaner separation, though an alternative exists (see Architecture Patterns) |

**Installation (frontend):**
```bash
cd frontend && npm install recharts
```

**pyproject.toml addition (httpx is transitive but should be explicit):**
```toml
"httpx>=0.27.0,<1.0.0",
```

---

## Architecture Patterns

### Recommended File Structure (new files only)
```
app/
├── routers/admin/
│   └── monitoring.py          # GET /admin/monitoring/status (+ incidents list)
├── routers/admin/__init__.py  # add monitoring router import
├── services/
│   └── health_monitor.py      # run_health_checks(), create/resolve incident logic
├── services/scheduled_endpoints.py  # add POST /scheduled/health-check endpoint

frontend/src/
├── app/(admin)/
│   └── monitoring/
│       └── page.tsx            # /admin/monitoring dashboard page
└── components/admin/
    └── monitoring/
        ├── StatusCard.tsx       # Per-endpoint status card with sparkline
        └── StaleDataBanner.tsx  # Warning banner when data > 5 min old
```

### Pattern 1: Scheduled Health-Check Endpoint

**What:** A new `POST /scheduled/health-check` endpoint in `app/services/scheduled_endpoints.py` that reuses the existing `_verify_scheduler` dependency.

**When to use:** This is the entry point triggered by Cloud Scheduler every 60 seconds.

**Example:**
```python
# Source: existing scheduled_endpoints.py pattern
@router.post("/health-check")
async def trigger_health_check(
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret"),
):
    """Run all health checks and persist results to Supabase."""
    _verify_scheduler(x_scheduler_secret)
    results = await run_health_checks()
    return {"status": "ok", "checks": results}
```

### Pattern 2: Concurrent httpx Health Polling

**What:** `app/services/health_monitor.py` — core service that concurrently hits all health endpoints and writes results.

**Key constraint (HLTH-06):** The health monitor must NOT call the monitored FastAPI's own HTTP interface for writing (i.e., no HTTP call to admin API). It writes directly to Supabase using `get_service_client()`.

**Note on calling health endpoints:** There are two valid approaches:
- **Option A (HTTP):** Use `httpx.AsyncClient` to hit `{BACKEND_API_URL}/health/live` etc. This correctly tests the full HTTP stack but adds latency and creates a self-dependency.
- **Option B (in-process):** Import and call the FastAPI handler functions directly (e.g., `from app.fast_api_app import get_liveness; await get_liveness()`). This is faster and avoids circular HTTP calls. Phase 7's existing `check_system_health` tool already uses this pattern.

**Recommendation: Use Option A (httpx HTTP calls)** for the scheduler loop. Reason: the scheduler endpoint may run in a separate Cloud Run instance from the monitored FastAPI. The requirement explicitly says "pings all /health/* endpoints via httpx" (HLTH-01). Use `BACKEND_API_URL` env var (already in .env.example and validation.py).

```python
# Source: httpx docs + existing a2a/client.py pattern
HEALTH_ENDPOINTS = {
    "live": "/health/live",
    "connections": "/health/connections",
    "cache": "/health/cache",
    "embeddings": "/health/embeddings",
    "video": "/health/video",
}
TIMEOUT_PER_CHECK = httpx.Timeout(10.0, connect=5.0)

async def _check_one(client: httpx.AsyncClient, name: str, path: str) -> dict:
    """Check a single health endpoint. Returns result dict."""
    import time
    start = time.monotonic()
    try:
        resp = await client.get(path, timeout=TIMEOUT_PER_CHECK)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        status = "healthy" if resp.status_code == 200 else "unhealthy"
        return {
            "endpoint": name,
            "status": status,
            "status_code": resp.status_code,
            "response_time_ms": elapsed_ms,
            "error_message": None,
        }
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "endpoint": name,
            "status": "unhealthy",
            "status_code": None,
            "response_time_ms": elapsed_ms,
            "error_message": str(exc)[:500],
        }

async def run_health_checks() -> list[dict]:
    """Concurrently check all health endpoints via asyncio.gather()."""
    base_url = os.getenv("BACKEND_API_URL", "http://localhost:8000")
    async with httpx.AsyncClient(base_url=base_url) as client:
        tasks = [
            _check_one(client, name, path)
            for name, path in HEALTH_ENDPOINTS.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    # ... write to Supabase, create/resolve incidents
    return results
```

### Pattern 3: Incident Lifecycle Management

**What:** Auto-create incident on first failure; auto-resolve when endpoint recovers.

**Schema (already exists from Phase 7 migration):**
```sql
-- api_incidents columns:
-- id, endpoint, category, incident_type, started_at, resolved_at,
-- auto_remediation_attempted, remediation_action, remediation_result,
-- details, created_at
```

**Logic:**
```python
async def _update_incidents(client, endpoint: str, is_healthy: bool) -> None:
    """Create or resolve an incident for the given endpoint."""
    # Check for open incident (resolved_at IS NULL)
    open_incident = client.table("api_incidents") \
        .select("id") \
        .eq("endpoint", endpoint) \
        .is_("resolved_at", "null") \
        .limit(1) \
        .execute()

    if not is_healthy and not open_incident.data:
        # Create new incident
        client.table("api_incidents").insert({
            "endpoint": endpoint,
            "incident_type": "outage",
            "started_at": datetime.utcnow().isoformat(),
        }).execute()
    elif is_healthy and open_incident.data:
        # Resolve existing incident
        incident_id = open_incident.data[0]["id"]
        client.table("api_incidents") \
            .update({"resolved_at": datetime.utcnow().isoformat()}) \
            .eq("id", incident_id) \
            .execute()
```

### Pattern 4: Monitoring Status API Endpoint

**What:** `GET /admin/monitoring/status` returns current status cards + recent history for sparklines.

**Location:** `app/routers/admin/monitoring.py`, registered on `admin_router`.

```python
# Endpoint returns:
{
  "endpoints": [
    {
      "name": "live",
      "current_status": "healthy",
      "latest_check_at": "2026-03-21T12:00:00Z",
      "response_time_ms": 42,
      "history": [                         # last N checks for sparkline
        {"checked_at": "...", "response_time_ms": 40, "status": "healthy"},
        ...
      ]
    },
    ...
  ],
  "open_incidents": [...],
  "latest_check_at": "2026-03-21T12:00:00Z"  # used for stale-data detection
}
```

**History depth:** Last 20 checks per endpoint (20 × 60s = 20 minutes of sparkline data). Query: `ORDER BY checked_at DESC LIMIT 20` per endpoint.

### Pattern 5: Recharts Sparkline (LineChart without axes)

**What:** A minimal `LineChart` using recharts 3.x rendered inside each status card.

**Recharts 3.x constraints (from STATE.md + official migration guide):**
1. Do NOT use `activeIndex` prop — it no longer exists. Use `<Tooltip defaultIndex={...}>` instead.
2. Do NOT use `CategoricalChartState` — it no longer exists. Use hooks (`useActiveTooltipLabel`) if internal state is needed.
3. Z-index is render order in JSX — place `<Tooltip>` before `<Legend>` if both are used.
4. `accessibilityLayer` is true by default in 3.x — set `accessibilityLayer={false}` on sparklines to avoid spurious DOM attributes.

**Sparkline pattern:**
```tsx
// Source: recharts 3.x docs — LineChart without axes
import { LineChart, Line, ResponsiveContainer } from 'recharts';

interface SparklineProps {
  data: { response_time_ms: number }[];
  isHealthy: boolean;
}

export function Sparkline({ data, isHealthy }: SparklineProps) {
  return (
    <ResponsiveContainer width="100%" height={40}>
      <LineChart data={data} accessibilityLayer={false}>
        <Line
          type="monotone"
          dataKey="response_time_ms"
          stroke={isHealthy ? '#4ade80' : '#f87171'}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

### Pattern 6: Stale-Data Banner

**What:** Client-side check — if `latest_check_at` from the API is more than 5 minutes ago, show a yellow warning banner.

```tsx
const isStale = latestCheckAt
  ? (Date.now() - new Date(latestCheckAt).getTime()) > 5 * 60 * 1000
  : false;

{isStale && (
  <div className="bg-amber-900/50 border border-amber-600 text-amber-300 rounded-xl px-4 py-3 text-sm mb-6">
    Warning: Health check data is stale — last updated {formatRelative(latestCheckAt)}.
    Cloud Scheduler may be paused.
  </div>
)}
```

### Pattern 7: Dashboard Polling

**What:** Client-side interval polling of `GET /admin/monitoring/status` every 30 seconds on the dashboard. No WebSocket or Supabase Realtime needed (both are ruled out).

```tsx
useEffect(() => {
  fetchStatus(); // initial load
  const id = setInterval(fetchStatus, 30_000);
  return () => clearInterval(id);
}, [fetchStatus]);
```

### Anti-Patterns to Avoid

- **Calling /health/* via the admin FastAPI itself:** The scheduler endpoint must write results directly to Supabase, not via HTTP to the monitored service's admin API. httpx calls go to `BACKEND_API_URL`, Supabase writes use `get_service_client()`.
- **Using `activeIndex` prop on recharts charts:** Removed in recharts 3.x. Will cause a TypeScript error.
- **Using `CategoricalChartState`:** Removed in recharts 3.x. Use hooks.
- **Blocking Supabase calls in async handlers:** Always use `execute_async()` for Supabase writes inside async route handlers.
- **Forgetting `is_("resolved_at", "null")` for open incident check:** Using `.eq("resolved_at", None)` will not work with PostgREST — use `.is_("resolved_at", "null")`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Concurrent HTTP requests | Manual task tracking with asyncio.create_task | `asyncio.gather(*tasks, return_exceptions=True)` | Gather handles exceptions per-task; one failure doesn't cancel others |
| Scheduler auth | Custom JWT or HMAC signing | `_verify_scheduler()` + `SCHEDULER_SECRET` | Already established pattern in scheduled_endpoints.py |
| Async Supabase writes | Raw thread spawning | `execute_async()` from `app/services/supabase_async.py` | Thread pooling and timeout handling already implemented |
| Sparkline charts | Custom SVG path drawing | `recharts` LineChart without axes | Recharts handles SVG scaling, ResponsiveContainer handles resize |

---

## Common Pitfalls

### Pitfall 1: Self-Loop in Health Checks
**What goes wrong:** The health checker endpoint is inside the same FastAPI process it is checking. If the service is down, the endpoint itself can't run.
**Why it happens:** Cloud Scheduler calls the same service it's monitoring.
**How to avoid:** This is acceptable — if the service is completely down, Cloud Scheduler will get a non-200 response and no write occurs. The stale-data banner (HLTH-05) catches this: if no new rows appear for 5+ minutes, the dashboard warns the admin.
**Warning signs:** All rows in api_health_checks stop appearing simultaneously — not just one endpoint.

### Pitfall 2: Recharts Not Installed
**What goes wrong:** Frontend build error `Module not found: recharts`.
**Why it happens:** recharts is not in the current frontend/package.json.
**How to avoid:** Wave 0 task installs recharts: `cd frontend && npm install recharts`.
**Warning signs:** TypeScript cannot resolve `recharts` import.

### Pitfall 3: Blocking Supabase Insert in Async Handler
**What goes wrong:** The scheduler endpoint blocks the event loop writing health results, causing timeouts.
**Why it happens:** `supabase-py` client's `.execute()` is synchronous.
**How to avoid:** Wrap all Supabase calls with `execute_async()` from `app/services/supabase_async.py`. See existing pattern in `app/routers/admin/audit.py`.

### Pitfall 4: Open Incident Query with `.eq("resolved_at", None)`
**What goes wrong:** Query returns no results even when open incidents exist.
**Why it happens:** PostgREST uses IS NULL syntax, not `= null`. The supabase-py `.eq()` method sends `=` comparison.
**How to avoid:** Use `.is_("resolved_at", "null")` for NULL checks. Confirmed pattern in PostgREST / supabase-py docs.

### Pitfall 5: Recharts activeIndex / CategoricalChartState
**What goes wrong:** TypeScript compilation error; runtime errors if using old recharts 2.x patterns.
**Why it happens:** recharts 3.x removed both. STATE.md flags this explicitly.
**How to avoid:** Use `<Tooltip defaultIndex={...}>` instead of `activeIndex`. Use `useActiveTooltipLabel` hook if label access needed. For sparklines, neither is needed — just `LineChart + Line + ResponsiveContainer`.

### Pitfall 6: History Query Performance
**What goes wrong:** Monitoring dashboard is slow because querying history for all endpoints without an index.
**Why it happens:** `api_health_checks` has no index on `(endpoint, checked_at)` in the Phase 7 schema.
**How to avoid:** Migration in Wave 0 must add: `CREATE INDEX api_health_checks_endpoint_checked_at ON api_health_checks (endpoint, checked_at DESC)`.

### Pitfall 7: Stale-Data Detection Edge Case
**What goes wrong:** Admin sees stale-data banner on first load before any checks have run.
**Why it happens:** `api_health_checks` is empty — `latest_check_at` is null.
**How to avoid:** API returns `latest_check_at: null` when no rows exist. Frontend: only show the stale-data banner if `latest_check_at !== null AND age > 5min`. An empty table is "no data yet", not "stale data".

---

## Code Examples

### Health Monitor Service Core
```python
# Source: HLTH-01 requirement + existing a2a/client.py httpx pattern
import asyncio
import logging
import os
import time
from datetime import datetime

import httpx

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async
from app.services.admin_audit import log_admin_action

logger = logging.getLogger(__name__)

HEALTH_ENDPOINTS = {
    "live": "/health/live",
    "connections": "/health/connections",
    "cache": "/health/cache",
    "embeddings": "/health/embeddings",
    "video": "/health/video",
}
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def run_health_checks() -> list[dict]:
    """Concurrently check all health endpoints and persist results."""
    base_url = os.getenv("BACKEND_API_URL", "http://localhost:8000").rstrip("/")
    async with httpx.AsyncClient(base_url=base_url) as client:
        tasks = [
            _check_one(client, name, path)
            for name, path in HEALTH_ENDPOINTS.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    checked_at = datetime.utcnow().isoformat()
    supabase = get_service_client()
    rows = []
    for res in results:
        if isinstance(res, Exception):
            continue
        rows.append({**res, "checked_at": checked_at})

    if rows:
        await execute_async(
            supabase.table("api_health_checks").insert(rows),
            op_name="health_monitor.insert_checks",
        )
        # Update incident states
        for res in results:
            if not isinstance(res, Exception):
                await _update_incidents(
                    supabase,
                    res["endpoint"],
                    res["status"] == "healthy",
                    checked_at,
                )

    await log_admin_action(
        admin_user_id=None,
        action="scheduled_health_check",
        target_type="system",
        target_id=None,
        details={"checked": len(rows)},
        source="monitoring_loop",
    )
    return rows
```

### Scheduled Endpoint Addition
```python
# Source: existing _verify_scheduler pattern in scheduled_endpoints.py
@router.post("/health-check")
async def trigger_health_check(
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret"),
):
    """Cloud Scheduler entry point — runs all health checks, writes to Supabase."""
    _verify_scheduler(x_scheduler_secret)
    results = await run_health_checks()
    return {"status": "ok", "checks_written": len(results)}
```

### Monitoring Status API Response Shape
```python
# Source: HLTH-04 requirement — data contract for frontend
@router.get("/status")
async def get_monitoring_status(
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Return current endpoint statuses, sparkline history, and open incidents."""
    client = get_service_client()
    # Per endpoint: latest check + last 20 checks for sparkline
    # ... (implementation detail for planner)
    return {
        "endpoints": [...],          # list of endpoint status objects
        "open_incidents": [...],     # unresolved api_incidents rows
        "latest_check_at": "...",   # ISO timestamp or null
    }
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| recharts 2.x `activeIndex` prop | `<Tooltip defaultIndex={...}>` | recharts 3.0 | Any old code using `activeIndex` fails at compile time |
| recharts 2.x `CategoricalChartState` in Customized | `useActiveTooltipLabel` hook | recharts 3.0 | Internal chart state no longer passed via props |
| recharts SVG z-index via CSS | z-index determined by JSX render order | recharts 3.0 | Place higher-priority elements lower in JSX tree |
| Supabase `.eq("col", None)` for NULL | `.is_("col", "null")` | supabase-py 2.x | Incorrect NULL check silently returns empty results |

**Deprecated/outdated:**
- `recharts` 2.x patterns: `activeIndex`, `CategoricalChartState` — both removed in 3.x
- Inline `asyncio.to_thread()` for Supabase in Phase 8: use project's `execute_async()` util instead

---

## Open Questions

1. **Health check data retention**
   - What we know: `api_health_checks` has no TTL or cleanup mechanism yet
   - What's unclear: At 60s intervals, 5 endpoints × 60×24 = 7,200 rows/day accumulate indefinitely
   - Recommendation: Add a simple migration or scheduled cleanup. For Phase 8, keep 7 days of rows. Can be a follow-up; sparklines only need last 20 rows per endpoint.

2. **Cloud Scheduler job creation**
   - What we know: The pattern (SCHEDULER_SECRET + `_verify_scheduler`) is established; the endpoint will be `POST /scheduled/health-check`
   - What's unclear: Whether Cloud Scheduler job creation is manual (via GCP Console / Terraform) or scripted — Phase 8 should document the job configuration parameters but the actual job creation is an operational step
   - Recommendation: Include a "Cloud Scheduler setup" section in the Phase 8 verification checklist

3. **Dashboard auto-refresh vs. Supabase Realtime**
   - What we know: WebSocket/Realtime is out of scope per REQUIREMENTS.md
   - What's unclear: Whether 30-second client polling is acceptable UX for a near-real-time monitor
   - Recommendation: 30-second polling is fine. Dashboard data is at most 60s old anyway (scheduler interval).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | pytest.ini / pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/unit/admin/ -x -q` |
| Full suite command | `uv run make test` |
| Frontend | vitest (configured in frontend/scripts/run-vitest.mjs) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HLTH-01 | `run_health_checks()` calls all 5 endpoints concurrently | unit | `uv run pytest tests/unit/admin/test_health_monitor.py -x` | Wave 0 |
| HLTH-02 | `POST /scheduled/health-check` returns 200 with valid secret, 401 without | unit | `uv run pytest tests/unit/admin/test_health_monitor.py::test_scheduler_auth -x` | Wave 0 |
| HLTH-03 | Incident created on first failure; `resolved_at` stamped on recovery | unit | `uv run pytest tests/unit/admin/test_health_monitor.py::test_incident_lifecycle -x` | Wave 0 |
| HLTH-04 | `GET /admin/monitoring/status` returns endpoint list with history | unit | `uv run pytest tests/unit/admin/test_monitoring_api.py -x` | Wave 0 |
| HLTH-05 | Stale-data detection: `latest_check_at > 5 min old` → stale=true in response | unit | `uv run pytest tests/unit/admin/test_monitoring_api.py::test_stale_data_flag -x` | Wave 0 |
| HLTH-06 | Health results use `get_service_client()` not HTTP admin endpoint | unit (mock verify) | `uv run pytest tests/unit/admin/test_health_monitor.py::test_writes_direct_to_supabase -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/admin/ -x -q`
- **Per wave merge:** `uv run make test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/admin/test_health_monitor.py` — covers HLTH-01, HLTH-02, HLTH-03, HLTH-06
- [ ] `tests/unit/admin/test_monitoring_api.py` — covers HLTH-04, HLTH-05
- [ ] Frontend dependency: `recharts` — `cd frontend && npm install recharts`
- [ ] Python dependency: add `"httpx>=0.27.0,<1.0.0"` to `pyproject.toml` (currently transitive only)
- [ ] Migration: `CREATE INDEX api_health_checks_endpoint_checked_at ON api_health_checks (endpoint, checked_at DESC)` — needed before history query is performant

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — `app/services/scheduled_endpoints.py` (scheduler auth pattern), `app/fast_api_app.py` (health endpoint definitions), `app/agents/admin/tools/health.py` (Phase 7 health tool), `supabase/migrations/20260321300000_admin_panel_foundation.sql` (api_health_checks + api_incidents schema)
- `uv.lock` — confirmed httpx 0.28.1 is already resolved
- `frontend/package.json` — confirmed recharts is NOT currently installed

### Secondary (MEDIUM confidence)
- [recharts 3.0 migration guide](https://github.com/recharts/recharts/wiki/3.0-migration-guide) — breaking changes (activeIndex, CategoricalChartState, z-index)
- [Google Cloud Scheduler HTTP target auth](https://docs.cloud.google.com/scheduler/docs/http-target-auth) — OIDC token approach for Cloud Run
- [Running Cloud Run services on a schedule](https://docs.cloud.google.com/run/docs/triggering/using-scheduler) — scheduler job configuration

### Tertiary (LOW confidence)
- recharts 3.x sparkline pattern without axes — extrapolated from LineChart docs; no dedicated sparkline component in recharts; approach consistent with library's design

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — httpx confirmed in lockfile, recharts absence confirmed in package.json, supabase-py version confirmed
- Architecture: HIGH — follows established Phase 7 patterns (scheduler auth, execute_async, service-role writes, admin router structure)
- Pitfalls: HIGH for recharts 3.x (verified via migration guide), HIGH for PostgREST NULL query, MEDIUM for performance index (standard SQL practice)

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable stack — recharts, httpx, supabase-py are not fast-moving for this use case)

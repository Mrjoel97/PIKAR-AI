# Phase 46: Analytics & Continuous Intelligence - Research

**Researched:** 2026-04-05
**Domain:** External DB querying, Google Calendar free/busy API, user-defined monitoring jobs, knowledge graph updates
**Confidence:** HIGH (all major decisions verified against live codebase; no new external dependencies needed)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**External Database Query Experience**
- SQL generation flow: Smart auto-execute — simple SELECTs run immediately, complex queries (JOINs, subqueries, large table scans) show generated SQL and ask user confirmation before execution
- Results display: Agent gives a natural-language summary first, with expandable sortable table and optional auto-chart underneath
- Connection setup: Guided form (host, port, database, user, password) with a "paste connection string" button that auto-fills all fields
- Read-only enforcement: All connections use strict read-only mode with 30-second query timeout (XDATA-06)
- Query saving: Claude's discretion — focus on core NL-to-SQL flow first

**Calendar Intelligence**
- Follow-up scheduling: Agent suggests optimal follow-up time after sales calls based on free/busy data — user confirms before booking (not auto-book)
- Calendar awareness depth: Meeting list + AI-generated prep notes (last discussion from CRM/knowledge vault, open action items, relevant documents, attendee context from HubSpot deals)
- Recurring task generation: Claude's discretion on pattern detection — focus on calendar awareness first
- Free/busy scope: Claude's discretion based on what Google Calendar API supports for multi-attendee free/busy lookups

**Monitoring Job Design**
- Creation flow: Chat-first — user says "monitor Competitor X weekly" in chat, agent creates the job. Configuration page shows all active jobs for editing/pausing/deleting
- Schedule model: Importance level drives frequency — critical (daily), normal (weekly), low-priority (biweekly). System decides execution time.
- Alert triggering: AI-judged significance by default (ResearchAgent compares new findings against previous state), plus user-defined keyword triggers that always alert
- Source discovery: Auto-discover relevant sources from topic, user can pin must-watch URLs or exclude irrelevant ones

**Intelligence Brief Format**
- Delivery: Short summary pushed to chat and notifications (Slack/Teams via Phase 45 dispatcher), full brief stored in knowledge vault
- Brief structure: Claude's discretion — adapt format based on monitoring type (competitor vs market vs topic). Scannable and business-focused.
- Knowledge graph depth: Track entities AND relationships (acquisitions, partnerships, competitive dynamics). Updates both entity data and cross-entity links via existing GraphService + graph_writer.
- Alert detail level: 2-3 sentence summary with key data points directly in the notification — actionable without clicking through

### Claude's Discretion
- Query saving feature scope (may skip in v1)
- Recurring task generation pattern detection approach
- Free/busy lookup scope (user only vs multi-attendee)
- Intelligence brief structure per monitoring type
- Auto-chart type selection for query results

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| XDATA-01 | User can connect external PostgreSQL database from configuration page | New `postgresql` ProviderConfig entry in PROVIDER_REGISTRY (api_key auth_type); connection credentials stored in `integration_credentials` table |
| XDATA-02 | User can connect BigQuery project from configuration page | BigQuery already in PROVIDER_REGISTRY with readonly scopes; need connection UI section in configuration page |
| XDATA-03 | Agent can run read-only SQL queries against connected external databases | `ExternalDbQueryService` with `asyncio.to_thread()` for psycopg2/bigquery-python sync SDKs; 30s timeout enforcement |
| XDATA-04 | AI-generated SQL from natural language via DataAnalysisAgent | New `external_db_query` tool added to DATA_AGENT_TOOLS; SQL classification heuristic for auto-execute vs confirmation |
| XDATA-05 | Query results displayed as tables and charts in chat | Agent returns NL summary + `create_table_widget` output; chart type auto-selected based on column types |
| XDATA-06 | Connection uses strict read-only mode with 30-second query timeout | PostgreSQL: SET SESSION CHARACTERISTICS + statement_timeout; BigQuery: readonly scope + query timeout config |
| CAL-01 | Agent can find optimal meeting times by querying free/busy across calendars | Google Calendar FreeBusy API already available (`freebusy().query()`); need multi-attendee variant + `find_free_slots` tool |
| CAL-02 | Agent can auto-schedule follow-up meetings after sales calls | New `suggest_followup_meeting` tool using existing `create_calendar_event` + HubSpot deal context from Phase 42 |
| CAL-03 | Agent can generate recurring tasks from calendar patterns | New `detect_calendar_patterns` tool analyzing `list_upcoming_events` results; Claude's discretion on implementation depth |
| CAL-04 | Calendar-aware agent responses (agent knows about upcoming meetings and context) | New `get_meeting_context` tool: list events for next N hours + fetch CRM/vault context per attendee email |
| INTEL-01 | User can create scheduled monitoring jobs for competitors, markets, or topics | New `monitoring_jobs` table + `MonitoringJobService`; chat tool `create_monitoring_job` on ResearchAgent |
| INTEL-02 | Monitoring runs on configurable schedule (daily, weekly) via workflow trigger service | New `/scheduled/monitoring-tick` endpoint reusing `_verify_scheduler` + `X-Scheduler-Secret` pattern |
| INTEL-03 | Results synthesized into intelligence briefs by ResearchAgent | `run_monitoring_job` in `MonitoringJobService` calls `_execute_research_job()` from `intelligence_scheduler.py` |
| INTEL-04 | Knowledge graph updated with entities and findings from monitoring | Reuse `write_to_graph()` from `graph_writer.py`; monitoring jobs explicitly track entity relationships |
| INTEL-05 | Alert notifications when significant changes detected | AI significance check comparing new findings to previous `kg_findings` state; `dispatch_notification()` for delivery |
</phase_requirements>

---

## Summary

Phase 46 spans three independent capability tracks: external database natural-language querying (XDATA), intelligent calendar scheduling and awareness (CAL), and user-controlled continuous monitoring jobs (INTEL). All three build heavily on existing infrastructure — no new external services or Python packages are required beyond what is already used.

The XDATA track adds PostgreSQL to the PROVIDER_REGISTRY as an api_key provider (credentials are a connection string, not an OAuth token), extends the configuration page with a DB connections section, and adds an `ExternalDbQueryService` that enforces read-only mode and 30-second timeouts. The DataAnalysisAgent gets a new `external_db_query` tool. BigQuery is already registered in the provider registry; the same service wraps both backends.

The CAL track extends the existing `calendar_tool.py` and `GoogleCalendarService` with a free/busy multi-slot finder, a meeting context/prep builder (pulling from HubSpot via Phase 42 and knowledge vault via Phase 12.1), and a follow-up suggestion tool that proposes — but does not auto-book — calendar events. The OperationsAgent already carries CALENDAR_TOOLS; calendar awareness is most valuable there and on the SalesAgent.

The INTEL track introduces user-scoped monitoring jobs as a first-class concept. The existing `intelligence_scheduler.py` handles domain-level background research; Phase 46 adds *user-defined* per-topic monitoring above it, stored in a new `monitoring_jobs` table. Execution reuses `_execute_research_job()` and `dispatch_notification()`. A new scheduled endpoint `/scheduled/monitoring-tick` drives it. The chat-first creation flow means a new `create_monitoring_job` tool on the ResearchAgent is the primary entry point; the configuration page adds a management view.

**Primary recommendation:** Implement in three waves — XDATA (Wave 1), CAL (Wave 2), INTEL (Wave 3) — since they share no runtime dependencies and can be reviewed independently.

---

## Standard Stack

### Core (all pre-installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `psycopg2-binary` | 2.9+ | PostgreSQL client | Standard CPython PostgreSQL adapter; sync — wrap with `asyncio.to_thread()` per project pattern |
| `google-cloud-bigquery` | 3.x | BigQuery client | Already in project; used by existing BigQuery provider registration |
| `google-api-python-client` | 2.x | Google Calendar API | Already used in `app/integrations/google/calendar.py` |
| `cryptography` (Fernet) | — | Credential encryption | Already used in `app/services/encryption.py` for all integration credentials |
| `fastapi` | — | Scheduled endpoint | Already used throughout; reuse `_verify_scheduler` pattern from `scheduled_endpoints.py` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asyncio.to_thread()` | stdlib | Wrap sync DB drivers | Every sync SDK call (psycopg2, bigquery) — established pattern in Phase 42 HubSpot |
| `supabase-py` | — | monitoring_jobs table CRUD | All project DB operations go through Supabase service client |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `psycopg2-binary` | `asyncpg` | asyncpg is faster but project already uses psycopg2 in other places; to_thread wrapper avoids new dep |
| `bigquery` client | `sqlalchemy` + bigquery dialect | SQLAlchemy adds abstraction but requires new dep; direct client is simpler for read-only single-query use case |

**Installation:** No new packages required — `psycopg2-binary` and `google-cloud-bigquery` are already in requirements based on existing BigQuery provider registration and the psycopg2 usage in Supabase connection pooling.

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── services/
│   ├── external_db_service.py        # ExternalDbQueryService (PostgreSQL + BigQuery)
│   └── monitoring_job_service.py     # MonitoringJobService (user-defined monitoring)
├── agents/
│   ├── tools/
│   │   ├── calendar_tool.py          # EXTEND: free_busy, get_meeting_context, suggest_followup
│   │   └── external_db_tools.py      # NEW: external_db_query, list_db_connections
│   ├── research/
│   │   └── tools/
│   │       └── monitoring_tools.py   # NEW: create_monitoring_job, list_monitoring_jobs, pause_monitoring_job
│   └── data/
│       └── agent.py                  # EXTEND: add EXTERNAL_DB_TOOLS
├── routers/
│   └── monitoring_jobs.py            # NEW: REST endpoints for monitoring job CRUD
├── config/
│   └── integration_providers.py      # EXTEND: add 'postgresql' ProviderConfig
├── integrations/
│   └── google/
│       └── calendar.py               # EXTEND: get_freebusy(), find_free_slots()
└── services/
    └── scheduled_endpoints.py        # EXTEND: add /monitoring-tick endpoint

supabase/migrations/
└── 20260406000000_monitoring_jobs.sql  # monitoring_jobs + monitoring_state tables

frontend/src/app/dashboard/configuration/
└── page.tsx                           # EXTEND: DBConnectionsSection + MonitoringJobsSection
```

### Pattern 1: api_key Provider for PostgreSQL

PostgreSQL does not use OAuth — credentials are a host/port/user/password connection string stored as `access_token` (encrypted Fernet) in `integration_credentials` with `auth_type = "api_key"`.

```python
# app/config/integration_providers.py — add entry:
"postgresql": ProviderConfig(
    name="PostgreSQL",
    auth_type="api_key",
    auth_url="",
    token_url="",
    scopes=[],
    client_id_env="",
    client_secret_env="",
    webhook_secret_header=None,
    icon_url="https://cdn.pikar.ai/icons/postgresql.svg",
    category="analytics",
)
```

The connection string is stored as `access_token` (the encrypted blob), matching the `teams` provider pattern where `account_name` holds a URL. Decryption via `decrypt_secret()` at query time.

### Pattern 2: ExternalDbQueryService with Read-Only Enforcement

```python
# app/services/external_db_service.py
import asyncio
import psycopg2

async def query_postgres(connection_string: str, sql: str, timeout_sec: int = 30) -> dict:
    """Execute read-only SQL against a PostgreSQL connection.
    
    Source: project pattern — asyncio.to_thread for sync SDK calls (Phase 42)
    """
    def _sync_query():
        conn = psycopg2.connect(connection_string)
        conn.set_session(readonly=True)  # enforce read-only at session level
        cursor = conn.cursor()
        cursor.execute("SET statement_timeout = %s", (timeout_sec * 1000,))
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchmany(1000)  # cap at 1000 rows
        conn.close()
        return {"columns": columns, "rows": rows}
    
    return await asyncio.wait_for(
        asyncio.to_thread(_sync_query),
        timeout=timeout_sec + 2  # outer timeout > inner timeout
    )
```

**Read-only enforcement layers:**
1. `conn.set_session(readonly=True)` — PostgreSQL session-level, blocks all DML
2. `SET statement_timeout` — kills query at 30s
3. `asyncio.wait_for()` — Python-level outer timeout
4. SQL classification heuristic — reject non-SELECT before even connecting

### Pattern 3: Monitoring Jobs Table Design

```sql
-- supabase/migrations/20260406000000_monitoring_jobs.sql

CREATE TABLE public.monitoring_jobs (
    id            uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id       uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    topic         text NOT NULL,           -- e.g. "Competitor X", "AI market"
    monitoring_type text NOT NULL DEFAULT 'competitor',  -- competitor|market|topic
    importance    text NOT NULL DEFAULT 'normal',        -- critical|normal|low
    is_active     boolean NOT NULL DEFAULT true,
    pinned_urls   text[] NOT NULL DEFAULT '{}',
    excluded_urls text[] NOT NULL DEFAULT '{}',
    keyword_triggers text[] NOT NULL DEFAULT '{}',       -- always-alert keywords
    last_run_at   timestamptz,
    last_brief_id uuid,                    -- FK to knowledge vault document
    previous_state_hash text,             -- SHA256 of last synthesis for change detection
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

-- RLS: users see only their own jobs
ALTER TABLE public.monitoring_jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own monitoring jobs"
    ON public.monitoring_jobs FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Service role full access"
    ON public.monitoring_jobs FOR ALL USING (auth.role() = 'service_role');
```

Importance-to-schedule mapping (no cron expressions exposed to users):
- `critical` → run on every daily tick
- `normal` → run on every weekly tick (Mondays)
- `low` → run on every biweekly tick (1st and 15th)

### Pattern 4: Monitoring Tick Endpoint

```python
# app/services/scheduled_endpoints.py — add:
@router.post("/monitoring-tick")
async def trigger_monitoring_tick(
    cadence: str = "daily",   # daily | weekly | biweekly
    x_scheduler_secret: str = Header(None, alias="X-Scheduler-Secret"),
):
    """Run all active monitoring jobs due for this cadence."""
    _verify_scheduler(x_scheduler_secret)  # existing helper — no changes needed
    from app.services.monitoring_job_service import run_monitoring_tick
    results = await run_monitoring_tick(cadence=cadence)
    return {"status": "ok", "jobs_run": len(results), "results": results}
```

### Pattern 5: Calendar free/busy multi-slot finder

The existing `GoogleCalendarService.check_availability()` already calls `freebusy().query()`. Extension needed: multi-attendee and multi-slot candidate generation.

```python
# app/integrations/google/calendar.py — add method:
def get_freebusy(
    self,
    start: datetime,
    end: datetime,
    calendar_ids: list[str],  # ["primary", "other@example.com"]
) -> dict[str, list[dict]]:
    """Query free/busy for multiple calendars.
    
    Returns dict keyed by calendar_id, value is list of busy intervals.
    Source: Google Calendar API freebusy.query — supports up to 50 items
    """
    result = (
        self.service.freebusy()
        .query(body={
            "timeMin": start.isoformat() + "Z",
            "timeMax": end.isoformat() + "Z",
            "items": [{"id": cid} for cid in calendar_ids],
        })
        .execute()
    )
    return {
        cal_id: data.get("busy", [])
        for cal_id, data in result.get("calendars", {}).items()
    }
```

### Pattern 6: Meeting Context Tool (Calendar Awareness)

```python
# app/agents/tools/calendar_tool.py — add:
async def get_meeting_context(
    tool_context: ToolContextType,
    hours_ahead: int = 4,
) -> dict[str, Any]:
    """Get upcoming meetings with AI prep context for the next N hours.
    
    Combines: upcoming events list + CRM attendee context (Phase 42 HubSpot) +
    knowledge vault search (Phase 12.1) + open tasks (Phase 44 PM tools).
    """
```

### Anti-Patterns to Avoid
- **Auto-booking calendar events:** User confirmed — agent SUGGESTS follow-up time, user confirms. Never auto-create events.
- **Exposing cron syntax to users:** Hide cron behind importance levels (critical/normal/low). The `importance` field drives schedule; planner maps to tick cadence.
- **Storing raw PostgreSQL passwords:** Always encrypt with Fernet (`encrypt_secret()`) before storing in `integration_credentials.access_token`. Decrypt at query time only.
- **Unbounded query results:** Cap at 1000 rows. Large result sets will overflow chat context and break table rendering.
- **Running DML through the agent:** SQL classification heuristic should reject any non-SELECT statement before connecting. Also enforced at DB session level.
- **Calling BigQuery without project_id scope:** The BigQuery provider already has `bigquery.readonly` scope. Ensure `project_id` is extracted from the stored credentials and passed to every query.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Notification delivery for monitoring alerts | Custom Slack/Teams sender | `dispatch_notification()` from `notification_dispatcher.py` | Phase 45 already handles dedup, fan-out, rule matching |
| Research execution for monitoring | Custom web scraper pipeline | `_execute_research_job()` from `intelligence_scheduler.py` | Full pipeline: plan → track → synthesize → graph_write → vault_write |
| Knowledge graph entity/finding writes | Custom DB inserts | `write_to_graph()` + `write_to_vault()` from `graph_writer.py` | Handles upserts, entity linking, relationships |
| Google Calendar OAuth credential access | Manual credential lookup | `_get_calendar_service(tool_context)` existing helper | Already handles `provider_token` + `refresh_token` from `tool_context.state` |
| PostgreSQL credential storage | New credential table | `integration_credentials` table + `IntegrationManager` | Phase 39 encryption, refresh, sync state already wired |
| Scheduled trigger authentication | New auth middleware | `_verify_scheduler()` from `scheduled_endpoints.py` | `X-Scheduler-Secret` + `secrets.compare_digest()` already proven |
| DB connection UI section | New UI pattern | `IntegrationProviderCard` + new `DBConnectionSection` component | Matches Phase 44 `PMSyncSection` and Phase 45 `NotificationRulesSection` patterns |

**Key insight:** This phase is almost entirely additive — new tools on existing agents, new service layers on existing infrastructure, new DB tables following established schema patterns. The hardest work is the PostgreSQL read-only enforcement and the monitoring job significance-change detection logic.

---

## Common Pitfalls

### Pitfall 1: PostgreSQL SSL in Production
**What goes wrong:** psycopg2 connects without SSL to a cloud PostgreSQL (Supabase, RDS, CloudSQL) and either gets rejected or silently transmits credentials in plaintext.
**Why it happens:** Connection string parsing doesn't add `sslmode=require` by default.
**How to avoid:** When building the connection string from user-provided host/port/user/pass, append `?sslmode=require` unless the user explicitly provides a full DSN with their own sslmode.
**Warning signs:** `psycopg2.OperationalError: SSL connection has been closed unexpectedly` in test against RDS/Cloud SQL.

### Pitfall 2: BigQuery Job Polling vs. Timeout
**What goes wrong:** BigQuery queries are asynchronous — `query().result()` blocks the thread until completion (could be >30s for large scans).
**Why it happens:** BigQuery SDK uses polling internally; `asyncio.wait_for()` around `asyncio.to_thread()` is the correct approach but the inner thread doesn't respond to Python cancellation.
**How to avoid:** Pass `timeout` parameter to `query().result(timeout=30)` — this is a BigQuery-SDK-level timeout that triggers `concurrent.futures.TimeoutError`. Catch that in the service and return a user-friendly message.
**Warning signs:** Test queries against large tables not returning within expected window even with `asyncio.wait_for()`.

### Pitfall 3: Google Calendar Free/Busy Scope for External Attendees
**What goes wrong:** `freebusy().query()` returns busy times only for calendars the authenticated user has permission to view. External attendees' calendars will return empty busy arrays silently.
**Why it happens:** The Google Calendar API can only query calendars authorized by the current OAuth token. External attendees need their own OAuth or must have shared their calendar.
**How to avoid:** For multi-attendee free/busy, the tool should query `primary` for the current user only; document clearly that external attendee availability cannot be determined without their consent. Present the suggestion as "I found these slots open on your calendar — the attendees may have other commitments."
**Warning signs:** `get_freebusy()` returning all-free for external attendees when they clearly have events.

### Pitfall 4: Monitoring Job Significance — False Positives vs False Negatives
**What goes wrong:** The AI significance check either fires alerts on every minor update (notification fatigue) or misses real changes (useless monitoring).
**Why it happens:** No baseline comparison — comparing new synthesis to a stored hash of the previous synthesis is better than comparing raw text.
**How to avoid:** Store `previous_state_hash` (SHA256 of the synthesis.findings list serialized) in `monitoring_jobs`. On each run, compute new hash. If different, run AI significance check (`ResearchAgent` comparing old vs new synthesis). Only dispatch notification if AI judges significant OR keyword_triggers match.
**Warning signs:** Users getting 7 notifications per week for the same competitor page that barely changes.

### Pitfall 5: Connection String Leakage in Logs
**What goes wrong:** A psycopg2 connection error includes the full connection string (with password) in the exception message, which gets logged.
**Why it happens:** `psycopg2.OperationalError` exception repr includes the DSN by default.
**How to avoid:** Catch `psycopg2.OperationalError` and re-raise with a sanitized message (scrub the password component). Never log the raw exception from a database connection attempt.

### Pitfall 6: Monitoring Jobs Running Against Exhausted Budget
**What goes wrong:** Monitoring jobs call `_execute_research_job()` but don't check `_check_budget(domain)` first, running up unexpected Tavily/Firecrawl costs.
**Why it happens:** The intelligence scheduler checks budget per domain, but user monitoring jobs may not be scoped to any domain.
**How to avoid:** `MonitoringJobService.run_monitoring_tick()` should call `_check_budget("research")` (or a new `monitoring` budget domain) before each job. Set a conservative default budget for monitoring jobs.

---

## Code Examples

### External DB Query Tool

```python
# app/agents/tools/external_db_tools.py
# Pattern: matches ad_platform_tools.py structure (raw function exports, lazy imports)

async def external_db_query(
    natural_language_query: str,
    database: str | None = None,  # None = use default connected DB
) -> dict[str, Any]:
    """Query a connected external database using natural language.
    
    Generates SQL from the query, confirms complex queries with user,
    then executes read-only against the connected PostgreSQL or BigQuery.
    
    Args:
        natural_language_query: What the user wants to know from their data.
        database: Optional database identifier if multiple connected.
    
    Returns:
        Dict with sql_generated, columns, rows, row_count, chart_suggestion,
        and nl_summary for agent narration.
    """
    user_id = _get_user_id()
    # ... lazy import ExternalDbQueryService, get credentials, execute
```

### Monitoring Job Tool

```python
# app/agents/research/tools/monitoring_tools.py

async def create_monitoring_job(
    topic: str,
    monitoring_type: str = "competitor",  # competitor | market | topic
    importance: str = "normal",           # critical | normal | low
    keyword_triggers: list[str] | None = None,
) -> dict[str, Any]:
    """Create a scheduled monitoring job for a competitor, market, or topic.
    
    The job will run automatically on the schedule determined by importance:
    - critical: daily
    - normal: weekly
    - low: biweekly
    
    Results are synthesized into intelligence briefs and sent to your
    notification channels when significant changes are detected.
    """
```

### Meeting Prep Context Tool

```python
# app/agents/tools/calendar_tool.py — addition

async def get_meeting_context(
    tool_context: ToolContextType,
    hours_ahead: int = 4,
) -> dict[str, Any]:
    """Get upcoming meetings with prep context for the next N hours.
    
    Returns:
        Dict with meetings list, each meeting containing:
        - title, start, end, attendees
        - crm_context: HubSpot deal info for attendees (if available)
        - vault_context: Knowledge vault snippets mentioning attendees
        - action_items: Open tasks related to attendees/meeting title
    """
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual SQL queries against external DB | NL-to-SQL via DataAnalysisAgent | Phase 46 | Users connect once, query in plain English |
| Calendar awareness requires explicit user description | `get_meeting_context` fetches upcoming meetings automatically | Phase 46 | Agent knows what's on the user's day without being told |
| Domain-level background intelligence | User-scoped per-topic monitoring jobs | Phase 46 | Users control what they monitor; targeted alerts |
| Intelligence scheduler uses `kg_watch_topics` (admin-configured) | `monitoring_jobs` table (user-configured) | Phase 46 | Self-service competitive intelligence, no admin needed |

**Deprecated/outdated approaches:**
- `kg_watch_topics` table (admin-defined): still valid for system-level research, but Phase 46 monitoring jobs are the user-facing equivalent.
- Manual `check_availability()` single-slot check: still valid; extended with multi-slot `find_free_slots()` for optimal time finding.

---

## Open Questions

1. **PostgreSQL connection string storage format**
   - What we know: `integration_credentials.access_token` holds Fernet-encrypted bytes; `account_name` holds display name
   - What's unclear: Should we store the full DSN as `access_token`, or store host/port/dbname/user separately (perhaps as JSON encrypted in `access_token`)?
   - Recommendation: Store full DSN encrypted in `access_token`; `account_name` = `host:port/dbname` for display. Simpler and matches how Teams stores its webhook URL in `account_name`.

2. **BigQuery project_id extraction**
   - What we know: BigQuery credentials are stored via OAuth; the GCP project_id is needed for every query
   - What's unclear: Is project_id available from the OAuth token response, or must the user provide it separately?
   - Recommendation: Add a post-OAuth step that calls `bigquery.Client().project` with the user's credentials to discover the default project_id and store it as `account_name`. If the discovery fails, prompt for explicit project_id.

3. **Monitoring tick cadence in Cloud Scheduler**
   - What we know: Existing `/scheduled/intelligence-tick` runs via Cloud Scheduler; a new `/scheduled/monitoring-tick` needs three cadences (daily/weekly/biweekly)
   - What's unclear: Should this be three separate Cloud Scheduler jobs or one job with a `cadence` param?
   - Recommendation: Three Cloud Scheduler jobs posting to the same endpoint with `?cadence=daily`, `?cadence=weekly`, `?cadence=biweekly`. This matches the existing pattern and is independently controllable.

4. **SQL complexity classification heuristic**
   - What we know: Simple SELECTs auto-execute; complex queries need user confirmation
   - What's unclear: What constitutes "complex"? Keyword-based (JOIN, SUBQUERY presence) or query plan cost estimate?
   - Recommendation: Keyword heuristic is sufficient for v1 — classify as "needs_confirmation" if the lowercased SQL contains any of: `join`, `subquery`, `select.*from.*from`, `where.*select`, or estimated affected rows from table stats. Cost estimation via `EXPLAIN` is deferred complexity.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | `pytest.ini` / `pyproject.toml` |
| Quick run command | `uv run pytest tests/unit/ -x -q` |
| Full suite command | `uv run pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| XDATA-01 | postgresql ProviderConfig entry present in registry | unit | `uv run pytest tests/unit/test_external_db_service.py::test_postgresql_provider_registered -x` | Wave 0 |
| XDATA-02 | bigquery ProviderConfig has readonly scopes | unit | `uv run pytest tests/unit/test_external_db_service.py::test_bigquery_readonly_scopes -x` | Wave 0 |
| XDATA-03 | read_only SQL query executes against mock connection | unit | `uv run pytest tests/unit/test_external_db_service.py::test_postgres_readonly_enforcement -x` | Wave 0 |
| XDATA-04 | external_db_query tool returns columns + rows | unit | `uv run pytest tests/unit/tools/test_external_db_tools.py::test_query_returns_tabular_result -x` | Wave 0 |
| XDATA-05 | query result includes chart_suggestion field | unit | `uv run pytest tests/unit/tools/test_external_db_tools.py::test_chart_suggestion_included -x` | Wave 0 |
| XDATA-06 | 30s timeout raises TimeoutError when exceeded | unit | `uv run pytest tests/unit/test_external_db_service.py::test_query_timeout_enforced -x` | Wave 0 |
| CAL-01 | find_free_slots returns non-busy windows | unit | `uv run pytest tests/unit/test_calendar_tools.py::test_find_free_slots -x` | Wave 0 |
| CAL-02 | suggest_followup_meeting returns suggestion dict not created event | unit | `uv run pytest tests/unit/test_calendar_tools.py::test_followup_suggestion_not_booking -x` | Wave 0 |
| CAL-03 | detect_calendar_patterns returns pattern list | unit | `uv run pytest tests/unit/test_calendar_tools.py::test_detect_patterns -x` | Wave 0 |
| CAL-04 | get_meeting_context returns meetings + crm_context keys | unit | `uv run pytest tests/unit/test_calendar_tools.py::test_meeting_context_structure -x` | Wave 0 |
| INTEL-01 | create_monitoring_job inserts row in monitoring_jobs | unit | `uv run pytest tests/unit/test_monitoring_job_service.py::test_create_job_persists -x` | Wave 0 |
| INTEL-02 | monitoring-tick endpoint verifies scheduler secret | unit | `uv run pytest tests/unit/test_scheduled_endpoints.py::test_monitoring_tick_auth -x` | Wave 0 |
| INTEL-03 | run_monitoring_tick calls _execute_research_job | unit | `uv run pytest tests/unit/test_monitoring_job_service.py::test_tick_calls_research_pipeline -x` | Wave 0 |
| INTEL-04 | write_to_graph called with monitoring synthesis | unit | `uv run pytest tests/unit/test_monitoring_job_service.py::test_graph_write_on_run -x` | Wave 0 |
| INTEL-05 | alert dispatched when significance detected | unit | `uv run pytest tests/unit/test_monitoring_job_service.py::test_alert_dispatched_on_change -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_external_db_service.py` — covers XDATA-01 through XDATA-06
- [ ] `tests/unit/tools/test_external_db_tools.py` — covers XDATA-04, XDATA-05
- [ ] `tests/unit/test_calendar_tools.py` — covers CAL-01 through CAL-04
- [ ] `tests/unit/test_monitoring_job_service.py` — covers INTEL-01, INTEL-03, INTEL-04, INTEL-05
- [ ] `tests/unit/test_scheduled_endpoints.py` — covers INTEL-02 (may already partially exist for other endpoints)

---

## Sources

### Primary (HIGH confidence)
- Live codebase: `app/integrations/google/calendar.py` — `freebusy().query()` already implemented; `create_event()` and `list_upcoming_events()` confirmed
- Live codebase: `app/services/intelligence_scheduler.py` — `_execute_research_job()` pipeline confirmed; `build_research_queue()` + `run_scheduled_research()` are the reference patterns
- Live codebase: `app/config/integration_providers.py` — BigQuery registered with readonly scopes; `api_key` auth type confirmed for Teams (pattern reference for PostgreSQL)
- Live codebase: `app/services/notification_dispatcher.py` — `dispatch_notification()` interface confirmed
- Live codebase: `app/agents/research/tools/graph_writer.py` — `write_to_graph()` and `write_to_vault()` confirmed
- Live codebase: `app/services/scheduled_endpoints.py` — `_verify_scheduler()` + `X-Scheduler-Secret` pattern confirmed; `/intelligence-tick` endpoint is direct precedent for `/monitoring-tick`

### Secondary (MEDIUM confidence)
- Google Calendar API docs (training knowledge, verified against existing codebase implementation): `freebusy().query()` supports up to 50 calendar items; `items` array accepts attendee email addresses
- psycopg2 docs (training knowledge): `conn.set_session(readonly=True)` is the correct read-only mode; `SET statement_timeout` takes milliseconds as integer

### Tertiary (LOW confidence — flag for validation)
- BigQuery `query().result(timeout=N)` parameter: should be validated against `google-cloud-bigquery` SDK docs before implementation — parameter name may differ between SDK versions

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages needed; all libraries confirmed in existing codebase
- Architecture: HIGH — all patterns verified against existing Phase 39-45 implementations
- Pitfalls: MEDIUM — SQL injection, SSL, and calendar permission pitfalls are well-known; monitoring false-positive detection is project-specific
- Test gaps: HIGH — all gaps identified, no existing tests for any Phase 46 feature

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable APIs — Google Calendar, psycopg2, BigQuery SDK)

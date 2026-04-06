---
phase: 46-analytics-continuous-intelligence
verified: 2026-04-06T02:00:00Z
status: gaps_found
score: 12/15 must-haves verified
re_verification: false
gaps:
  - truth: "Agent can auto-schedule (or suggest) follow-up meetings after sales calls"
    status: partial
    reason: "REQUIREMENTS.md says 'auto-schedule' (CAL-02) but the planning decision was 'suggest only, never auto-book'. suggest_followup_meeting is implemented and does NOT call create_event — this is a deliberate scope-down from the REQUIREMENTS.md wording. The tool works as designed but does not satisfy the literal requirement."
    artifacts:
      - path: "app/agents/tools/calendar_tool.py"
        issue: "suggest_followup_meeting returns a suggestion dict and never calls create_event — intentional but diverges from REQUIREMENTS.md CAL-02 'auto-schedule'"
    missing:
      - "Either accept the deliberate scope-down and update REQUIREMENTS.md CAL-02 wording to 'suggest follow-up meetings', or add an auto-booking code path that the agent invokes when user confirms"

  - truth: "Agent can generate recurring tasks from calendar patterns (CAL-03)"
    status: failed
    reason: "REQUIREMENTS.md CAL-03 requires 'generate recurring tasks from calendar patterns'. detect_calendar_patterns only returns a pattern list (title, frequency, day, time, occurrences) — no tasks are created in any task store. Plan 02 scoped this as 'Claude's discretion / detect patterns only'."
    artifacts:
      - path: "app/agents/tools/calendar_tool.py"
        issue: "detect_calendar_patterns returns patterns but never calls create_task, pm_task_tools, or any task-creation API. CAL-03 task generation not implemented."
    missing:
      - "A follow-on action in detect_calendar_patterns (or a separate generate_recurring_tasks tool) that calls the PM task creation API with the detected pattern schedule"

  - truth: "Test Connection button in DBConnectionsSection calls a working endpoint"
    status: failed
    reason: "Frontend DBConnectionsSection calls POST /integrations/postgresql/test but this endpoint does not exist in app/routers/integrations.py. Only POST /integrations/{provider}/test-notification (for Slack/Teams) and POST /admin/integrations/{provider}/test (admin-only) exist. The button will receive 404."
    artifacts:
      - path: "frontend/src/app/dashboard/configuration/page.tsx"
        issue: "handleTestConnection calls fetchWithAuth('/integrations/postgresql/test', ...) at line ~1783 — endpoint does not exist in the user-facing integrations router"
      - path: "app/routers/integrations.py"
        issue: "No POST /{provider}/test endpoint — only /{provider}/test-notification exists (for notification channel testing, not DB connectivity)"
    missing:
      - "Add POST /integrations/{provider}/test endpoint to app/routers/integrations.py that accepts {connection_string} body and verifies DB connectivity for postgresql (and bigquery) using ExternalDbQueryService"
---

# Phase 46: Analytics & Continuous Intelligence Verification Report

**Phase Goal:** Users can query their own external databases with natural language, agents are calendar-aware for scheduling and follow-ups, and scheduled monitoring jobs continuously track competitors and market changes
**Verified:** 2026-04-06
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (derived from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can connect external PostgreSQL or BigQuery database from config page | PARTIAL | DBConnectionsSection exists with guided form and DSN parse. BUT "Test Connection" button calls a 404 endpoint |
| 2 | Agent runs read-only SQL with 30-second timeout; AI generates SQL from NL | VERIFIED | ExternalDbQueryService: set_session(readonly=True), statement_timeout, asyncio.wait_for. external_db_query calls ExternalDbQueryService |
| 3 | Query results display as tables and charts in chat | VERIFIED | external_db_query returns columns, rows, chart_suggestion, nl_summary. DataAnalysisAgent has EXTERNAL_DB_TOOLS |
| 4 | Agent can find optimal meeting times by checking free/busy status | VERIFIED | get_freebusy + find_free_slots in GoogleCalendarService; find_free_slots tool in CALENDAR_TOOLS; SalesAgent + OperationsAgent both have CALENDAR_TOOLS |
| 5 | Agent auto-schedules (or suggests) follow-up meetings after sales calls | PARTIAL | suggest_followup_meeting implemented and wired to SalesAgent. Deliberately does NOT auto-book. REQUIREMENTS.md says "auto-schedule" but CONTEXT.md decision says "suggest only". Functional but diverges from requirement wording |
| 6 | Agent generates recurring tasks from calendar patterns (CAL-03) | FAILED | detect_calendar_patterns detects patterns only — no task creation. Plan scoped this as "detect patterns, Claude's discretion on task generation". REQUIREMENTS.md says "generate recurring tasks" |
| 7 | Agents are calendar-aware — know about upcoming meetings and provide context | VERIFIED | get_meeting_context enriches upcoming events with CRM contacts (supabase contacts table), open tasks, and knowledge vault snippets via asyncio.gather |
| 8 | User can create scheduled monitoring jobs (daily/weekly) via chat | VERIFIED | create_monitoring_job in MONITORING_TOOLS; importance-to-cadence mapping (critical=daily, normal=weekly, low=biweekly); MonitoringJobsSection in config UI |
| 9 | Results synthesized into intelligence briefs by ResearchAgent with knowledge graph updates | VERIFIED | run_monitoring_tick calls _execute_research_job pipeline, then write_to_graph and write_to_vault with synthesis results |
| 10 | Alert notifications fire when significant changes detected | VERIFIED | run_monitoring_tick: SHA256 hash comparison, AI significance check (_is_significant_change), keyword_trigger bypass, dispatch_notification call on alert |

**Score: 7 fully verified, 2 partial, 1 failed out of 10 derived truths**

---

### Required Artifacts

| Artifact | Min Lines | Actual Lines | Status | Details |
|----------|-----------|-------------|--------|---------|
| `app/config/integration_providers.py` | — | exists | VERIFIED | postgresql entry at line 162 with api_key auth_type; bigquery at line 174 with bigquery.readonly scope |
| `app/services/external_db_service.py` | 120 | 320 | VERIFIED | ExternalDbQueryService class at line 57; classify_sql, query_postgres (set_session readonly=True, statement_timeout), query_bigquery, suggest_chart_type |
| `app/agents/tools/external_db_tools.py` | 80 | 400 | VERIFIED | external_db_query, confirm_and_run_query, list_db_connections, EXTERNAL_DB_TOOLS exported at line 396 |
| `supabase/migrations/20260406000000_external_db_monitoring.sql` | — | exists | VERIFIED | CREATE TABLE public.monitoring_jobs with RLS policies |
| `tests/unit/test_external_db_service.py` | 60 | 385 | VERIFIED | Substantive test file |
| `tests/unit/tools/test_external_db_tools.py` | 40 | 323 | VERIFIED | Substantive test file |
| `app/agents/tools/calendar_tool.py` | 300 | 611 | VERIFIED | CALENDAR_TOOLS at line 602 with 8 functions: original 4 + find_free_slots, get_meeting_context, suggest_followup_meeting, detect_calendar_patterns |
| `app/integrations/google/calendar.py` | — | 425 | VERIFIED | get_freebusy at line 280, find_free_slots at line 318 |
| `tests/unit/test_calendar_tools.py` | 80 | 515 | VERIFIED | Substantive test file (20 tests per summary) |
| `app/services/monitoring_job_service.py` | 150 | 457 | VERIFIED | MonitoringJobService class at line 136, run_monitoring_tick at line 296 + module-level convenience function at line 445 |
| `app/agents/research/tools/monitoring_tools.py` | 80 | 240 | VERIFIED | MONITORING_TOOLS at line 234 with 5 tools |
| `app/services/scheduled_endpoints.py` | — | exists | VERIFIED | /monitoring-tick endpoint at line 368 |
| `app/routers/monitoring_jobs.py` | 60 | 145 | VERIFIED | GET/POST/PATCH/DELETE /monitoring-jobs, auth via get_current_user_id |
| `tests/unit/test_monitoring_job_service.py` | 80 | 454 | VERIFIED | Substantive test file |
| `tests/unit/tools/test_monitoring_tools.py` | 40 | 355 | VERIFIED | Substantive test file |
| `app/agents/data/agent.py` | — | exists | VERIFIED | EXTERNAL_DB_TOOLS imported at line 43, spread in DATA_AGENT_TOOLS at line 228 |
| `app/agents/operations/agent.py` | — | exists | VERIFIED | CALENDAR_TOOLS imported at line 40, spread in OPERATIONS_AGENT_TOOLS at line 201 |
| `app/agents/sales/agent.py` | — | exists | VERIFIED | CALENDAR_TOOLS imported at line 31, spread in SALES_AGENT_TOOLS at line 171 |
| `app/agents/research/agent.py` | — | exists | VERIFIED | MONITORING_TOOLS imported at line 14, spread in RESEARCH_AGENT_TOOLS at line 30 |
| `frontend/src/app/dashboard/configuration/page.tsx` | — | +663 lines added | PARTIAL | DBConnectionsSection at line 1716, MonitoringJobsSection at line 2034, both rendered in page layout. BUT handleTestConnection at line 1783 calls non-existent POST /integrations/postgresql/test |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/agents/tools/external_db_tools.py` | `app/services/external_db_service.py` | lazy import ExternalDbQueryService | WIRED | Lines 146, 257 lazy-import and instantiate ExternalDbQueryService |
| `app/services/external_db_service.py` | `app/config/integration_providers.py` | provider lookup | NOT NEEDED | Credential lookup is done in the tools layer (_get_db_credentials via integration_credentials table), not in the service class. Service takes raw connection_string directly. No PROVIDER_REGISTRY call from service — acceptable architectural decision. |
| `app/agents/tools/calendar_tool.py` | `app/integrations/google/calendar.py` | _get_calendar_service(tool_context) | WIRED | _get_calendar_service used on lines 58, 107, 154, 194, 238, 282, 427, 499 |
| `app/agents/tools/calendar_tool.py` | `app/services/supabase.py` | CRM contact lookup | WIRED | Line 309 lazy-imports get_service_client; queries contacts table and tasks table per event |
| `app/services/monitoring_job_service.py` | `app/services/intelligence_scheduler.py` | _execute_research_job | WIRED | Module-level lazy wrapper at line 55-66; called in run_monitoring_tick at line 338 |
| `app/services/monitoring_job_service.py` | `app/services/notification_dispatcher.py` | dispatch_notification | WIRED | Module-level lazy wrapper at line 68-77; called in run_monitoring_tick at line 393 |
| `app/services/monitoring_job_service.py` | `app/agents/research/tools/graph_writer.py` | write_to_graph + write_to_vault | WIRED | Lazy wrappers at lines 79-95; called in run_monitoring_tick at lines 412-413 |
| `app/services/scheduled_endpoints.py` | `app/services/monitoring_job_service.py` | run_monitoring_tick | WIRED | Lazy import at line 379, called at line 381 |
| `app/agents/research/agent.py` | `app/agents/research/tools/monitoring_tools.py` | import MONITORING_TOOLS | WIRED | Line 14 import, line 30 spread |
| `app/agents/data/agent.py` | `app/agents/tools/external_db_tools.py` | import EXTERNAL_DB_TOOLS | WIRED | Line 43 import, line 228 spread |
| `app/agents/sales/agent.py` | `app/agents/tools/calendar_tool.py` | import CALENDAR_TOOLS | WIRED | Line 31 import, line 171 spread |
| `frontend/src/app/dashboard/configuration/page.tsx` | `/monitoring-jobs` | fetchWithAuth for REST CRUD | WIRED | Lines 2057, 2074, 2103, 2119 call /monitoring-jobs endpoints |
| `frontend/src/app/dashboard/configuration/page.tsx` | `/integrations/postgresql/test` | fetchWithAuth for test connection | BROKEN | Line 1783 calls POST /integrations/postgresql/test — endpoint does not exist in integrations router (only test-notification exists) |

---

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| XDATA-01 | 46-01, 46-04 | User can connect external PostgreSQL from config page | PARTIAL | DBConnectionsSection with guided form exists and saves via POST /integrations/postgresql/credentials. Test Connection calls non-existent POST /integrations/postgresql/test |
| XDATA-02 | 46-01, 46-04 | User can connect BigQuery from config page | PARTIAL | bigquery listed in form, BigQuery OAuth note shown. Test Connection issue applies. BigQuery registered in PROVIDER_REGISTRY with readonly scopes |
| XDATA-03 | 46-01 | Agent runs read-only SQL against connected external DBs | VERIFIED | set_session(readonly=True) + statement_timeout enforced in ExternalDbQueryService |
| XDATA-04 | 46-01, 46-04 | AI-generated SQL from natural language via DataAnalysisAgent | VERIFIED | external_db_query generates SQL via Gemini; DataAnalysisAgent has EXTERNAL_DB_TOOLS |
| XDATA-05 | 46-01, 46-04 | Query results displayed as tables and charts in chat | VERIFIED | external_db_query returns columns, rows, chart_suggestion, nl_summary to agent |
| XDATA-06 | 46-01 | Strict read-only mode with 30-second query timeout | VERIFIED | asyncio.wait_for(timeout=32) outer + SET statement_timeout=30000 server-side |
| CAL-01 | 46-02, 46-04 | Agent finds optimal meeting times via free/busy | VERIFIED | get_freebusy + find_free_slots methods implemented; find_free_slots tool in CALENDAR_TOOLS on SalesAgent + OperationsAgent |
| CAL-02 | 46-02, 46-04 | Agent auto-schedules follow-up meetings after sales calls | PARTIAL | suggest_followup_meeting implemented and wired to SalesAgent. Deliberately only suggests, never auto-books. REQUIREMENTS.md says "auto-schedule" — deliberate scope-down per CONTEXT.md decision |
| CAL-03 | 46-02 | Agent generates recurring tasks from calendar patterns | FAILED | detect_calendar_patterns identifies patterns (title, frequency, day, time) but creates no tasks. Plan scoped as "detect patterns only" per CONTEXT.md "Claude's discretion" |
| CAL-04 | 46-02, 46-04 | Calendar-aware agent responses with meeting context | VERIFIED | get_meeting_context enriches each meeting with CRM attendee data, open tasks, knowledge vault snippets. OperationsAgent has CALENDAR_TOOLS |
| INTEL-01 | 46-03, 46-04 | User can create monitoring jobs via chat and config UI | VERIFIED | create_monitoring_job in MONITORING_TOOLS on ResearchAgent; MonitoringJobsSection in config page calls POST /monitoring-jobs |
| INTEL-02 | 46-03 | Monitoring runs on configurable daily/weekly schedule via trigger service | VERIFIED | /scheduled/monitoring-tick with cadence param; importance-to-cadence mapping; X-Scheduler-Secret verification |
| INTEL-03 | 46-03 | Results synthesized into intelligence briefs by ResearchAgent | VERIFIED | run_monitoring_tick calls _execute_research_job (full research pipeline) and write_to_vault for each due job |
| INTEL-04 | 46-03 | Knowledge graph updated with entities and findings | VERIFIED | run_monitoring_tick calls write_to_graph(synthesis, domain="research") at line 412 |
| INTEL-05 | 46-03 | Alert notifications when significant changes detected | VERIFIED | SHA256 change detection, AI significance check, keyword_trigger bypass, dispatch_notification fan-out |

**Summary:** 11 SATISFIED, 2 PARTIAL, 1 FAILED, 1 PARTIAL (test endpoint gap)

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/app/dashboard/configuration/page.tsx` | 1783 | `fetchWithAuth('/integrations/postgresql/test', ...)` calls non-existent endpoint | Blocker | Test Connection button returns 404; user cannot verify DB connectivity before saving |

No placeholder stubs, empty implementations, or TODO blockers found in backend code.

---

### Human Verification Required

These items cannot be verified programmatically:

#### 1. Natural Language to SQL query end-to-end

**Test:** Connect a PostgreSQL database, open the DataAnalysisAgent chat, ask "how many users signed up last month?"
**Expected:** Agent generates SELECT query, presents tabular results with row count and chart suggestion (bar or line chart depending on column types)
**Why human:** Requires live PostgreSQL connection and Gemini API call for SQL generation

#### 2. Calendar free/busy meeting suggestions

**Test:** Open SalesAgent, ask "when should I schedule a follow-up after this call with John at Acme?"
**Expected:** Agent calls suggest_followup_meeting, shows proposed time with "Shall I create this event?" message — does NOT auto-book
**Why human:** Requires Google Calendar OAuth and live calendar data

#### 3. Monitoring job creation via chat

**Test:** Open ResearchAgent, say "monitor OpenAI for pricing changes weekly"
**Expected:** Agent calls create_monitoring_job with monitoring_type=competitor, importance=normal, returns confirmation with "Now monitoring 'OpenAI'. You'll receive alerts when significant changes are detected."
**Why human:** Requires live agent session and supabase write

#### 4. Monitoring alert delivery

**Test:** Create a monitoring job, manually trigger `/scheduled/monitoring-tick?cadence=weekly` with a valid X-Scheduler-Secret, verify that a significant change triggers a Slack/Teams notification
**Expected:** Notification delivered to connected Slack or Teams channel with 2-3 sentence summary
**Why human:** Requires live external notification channel (Phase 45 dependency) and research pipeline execution

#### 5. DB connections config page rendering

**Test:** Navigate to Configuration page, scroll to "Analytics" section — verify DBConnectionsSection shows, click "Add Database Connection", fill in form fields, observe that "Test Connection" button call fails (404 gap found above)
**Expected:** Form fields render correctly; Test Connection currently broken
**Why human:** Frontend rendering requires running Next.js dev server

---

### Gaps Summary

**3 gaps found, blocking 3 requirements:**

**Gap 1 — Test Connection endpoint missing (XDATA-01, XDATA-02 partially blocked):**
The DBConnectionsSection frontend component calls `POST /integrations/postgresql/test` to verify connectivity before saving credentials. This endpoint does not exist in the user-facing `app/routers/integrations.py`. The admin router has a test endpoint but at `/admin/integrations/{provider}/test` (inaccessible to regular users). Users can still save connections without testing, but the UX verification step is broken.

**Gap 2 — CAL-02 scope divergence (not a code defect):**
REQUIREMENTS.md CAL-02 says "auto-schedule follow-up meetings". The CONTEXT.md planning decision explicitly chose "suggest only, never auto-book". suggest_followup_meeting is correctly implemented per the planning decision. This is a REQUIREMENTS.md accuracy issue: the requirement should read "suggest follow-up meeting times" not "auto-schedule". No code fix needed unless the intent is truly to implement auto-booking on confirmation.

**Gap 3 — CAL-03 task generation not implemented:**
REQUIREMENTS.md CAL-03 requires "generate recurring tasks from calendar patterns". detect_calendar_patterns returns a structured pattern list but does not create tasks in any task store. Plan 02 explicitly scoped this as "detect patterns" only (under "Claude's discretion"). Either the requirement needs to be downscoped to "detect recurring patterns" or a task creation step needs to be added.

---

**Root cause of Gap 1:** Plan 04 specified "Test Connection button calls POST /integrations/{provider}/test" but a corresponding endpoint was never created in app/routers/integrations.py during Plan 03 or Plan 04 execution.

**Root cause of Gaps 2-3:** Deliberate planning decisions in CONTEXT.md downscoped both CAL-02 and CAL-03 from the REQUIREMENTS.md wording. These are requirement accuracy issues, not missing implementation.

---

_Verified: 2026-04-06_
_Verifier: Claude (gsd-verifier)_

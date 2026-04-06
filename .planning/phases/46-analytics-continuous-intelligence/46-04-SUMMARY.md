---
phase: 46-analytics-continuous-intelligence
plan: "04"
subsystem: agents
tags: [agent-wiring, external-db, calendar-tools, monitoring-tools, configuration-ui, postgresql, bigquery]

requires:
  - phase: 46-analytics-continuous-intelligence
    plan: "01"
    provides: "EXTERNAL_DB_TOOLS (external_db_query, confirm_and_run_query, list_db_connections)"
  - phase: 46-analytics-continuous-intelligence
    plan: "02"
    provides: "CALENDAR_TOOLS extended (get_meeting_context, suggest_followup_meeting, detect_calendar_patterns)"
  - phase: 46-analytics-continuous-intelligence
    plan: "03"
    provides: "MONITORING_TOOLS (create/list/pause/resume/delete monitoring_jobs) + REST endpoints"

provides:
  - "DataAnalysisAgent wired with EXTERNAL_DB_TOOLS for NL-to-SQL against external PostgreSQL/BigQuery"
  - "SalesAgent wired with CALENDAR_TOOLS for follow-up scheduling post sales calls"
  - "OperationsAgent wired with CALENDAR_TOOLS for meeting prep and scheduling context"
  - "ResearchAgent wired with MONITORING_TOOLS for continuous intelligence job management via chat"
  - "DBConnectionsSection on configuration page: guided PostgreSQL form + paste-DSN + BigQuery note"
  - "MonitoringJobsSection on configuration page: create/toggle/delete monitoring jobs with importance badges"

affects:
  - data-agent
  - sales-agent
  - operations-agent
  - research-agent
  - configuration-ui

tech-stack:
  added: []
  patterns:
    - "Tool list spread via *TOOL_LIST inside sanitize_tools() — consistent with existing agent wiring pattern"
    - "fetchWithAuth + SectionHeader component pattern for new configuration page sections"
    - "DSN parser in frontend: postgresql://user:pass@host:port/dbname auto-fills guided form fields"
    - "Importance-to-schedule badge mapping: critical=daily, normal=weekly, low=biweekly shown in UI"

key-files:
  created: []
  modified:
    - app/agents/data/agent.py
    - app/agents/operations/agent.py
    - app/agents/sales/agent.py
    - app/agents/research/agent.py
    - frontend/src/app/dashboard/configuration/page.tsx

key-decisions:
  - "No new decisions — plan wired existing tools into agents per established patterns"

patterns-established:
  - "Agent wiring via *TOOL_LIST spread in sanitize_tools(): pattern confirmed across Data, Sales, Operations, Research"
  - "Configuration page sections use SectionHeader + fetchWithAuth + rounded-[28px] card layout — extended for DB and Monitoring"

requirements-completed: [XDATA-01, XDATA-02, XDATA-04, XDATA-05, CAL-01, CAL-02, CAL-04, INTEL-01]

duration: 11min
completed: "2026-04-06"
---

# Phase 46 Plan 04: Agent Wiring + Configuration UI Summary

**EXTERNAL_DB_TOOLS, CALENDAR_TOOLS, and MONITORING_TOOLS wired into four agents; DBConnectionsSection and MonitoringJobsSection added to configuration page**

## Performance

- **Duration:** 11 min
- **Started:** 2026-04-06T00:39:17Z
- **Completed:** 2026-04-06T00:50:30Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- DataAnalysisAgent now has EXTERNAL_DB_TOOLS: users can query connected PostgreSQL/BigQuery databases via natural language in chat
- SalesAgent and OperationsAgent now have full CALENDAR_TOOLS including suggest_followup_meeting, get_meeting_context, and detect_calendar_patterns
- ResearchAgent now has MONITORING_TOOLS for creating and managing continuous intelligence jobs via conversation
- Configuration page has DBConnectionsSection with guided form (host/port/database/user/password), paste-DSN parser, test-connection button, and BigQuery OAuth note
- Configuration page has MonitoringJobsSection listing active jobs with importance badges (critical=daily, normal=weekly, low=biweekly), active toggle, and delete with confirmation

## Task Commits

1. **Task 1: Wire tools into agents (Data, Operations, Sales, Research)** - `6b06397` (feat)
2. **Task 2: Frontend DBConnectionsSection + MonitoringJobsSection** - `55df0e1` (feat)

## Files Created/Modified

- `app/agents/data/agent.py` — Added `from app.agents.tools.external_db_tools import EXTERNAL_DB_TOOLS` + `*EXTERNAL_DB_TOOLS` spread in DATA_AGENT_TOOLS; fixed implicit Optional annotation in create_data_agent
- `app/agents/sales/agent.py` — Added `from app.agents.tools.calendar_tool import CALENDAR_TOOLS` + `*CALENDAR_TOOLS` spread in SALES_AGENT_TOOLS; fixed implicit Optional annotation in create_sales_agent; reordered HUBSPOT_TOOLS import alphabetically
- `app/agents/operations/agent.py` — Added `from app.agents.tools.calendar_tool import CALENDAR_TOOLS` + `*CALENDAR_TOOLS` spread in OPERATIONS_AGENT_TOOLS
- `app/agents/research/agent.py` — Added `from app.agents.research.tools.monitoring_tools import MONITORING_TOOLS` + `*MONITORING_TOOLS` spread in RESEARCH_AGENT_TOOLS
- `frontend/src/app/dashboard/configuration/page.tsx` — +663 lines: MonitoringJob and DBConnection TypeScript interfaces, DBConnectionsSection component (guided form + DSN paste + test-connection), MonitoringJobsSection component (list/create/toggle/delete), both inserted between Google Workspace and MCP Tools sections

## Decisions Made

None — plan executed exactly as specified. All tool wiring followed the established `*TOOL_LIST` spread pattern already used by PM_TASK_TOOLS, AD_PLATFORM_TOOLS, and COMMUNICATION_TOOLS in their respective agents.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed implicit Optional annotations in create_data_agent and create_sales_agent**
- **Found during:** Task 1 (agent wiring)
- **Issue:** Pre-existing `output_key: str = None` parameter annotations (implicit Optional) triggered type checker warnings
- **Fix:** Changed to `output_key: str | None = None` in both factory functions to be explicit
- **Files modified:** app/agents/data/agent.py, app/agents/sales/agent.py
- **Verification:** ruff check passes with zero errors
- **Committed in:** 6b06397

---

**Total deviations:** 1 auto-fixed (Rule 1 — pre-existing type annotation bug found inline during wiring)
**Impact on plan:** Fix necessary for correctness. No scope creep.

## Issues Encountered

None — all imports resolved immediately. CALENDAR_TOOLS, EXTERNAL_DB_TOOLS, and MONITORING_TOOLS were all already exported as named lists from their respective modules in Plans 01-03, so wiring was straightforward.

## User Setup Required

None — configuration is done through the Configuration page UI that was added in this plan. Users connect PostgreSQL databases through DBConnectionsSection and manage monitoring jobs through MonitoringJobsSection.

## Next Phase Readiness

- Phase 46 is now complete — all four tracks (external DB, calendar intelligence, continuous monitoring, agent wiring + UI) are delivered
- DataAnalysisAgent can execute NL-to-SQL against user-connected external databases (XDATA-04, XDATA-05)
- SalesAgent can suggest follow-up meetings and check availability after sales calls (CAL-01, CAL-02)
- OperationsAgent has full meeting context and scheduling tools (CAL-04)
- ResearchAgent can create and manage monitoring jobs via chat commands (INTEL-01)
- Configuration page exposes DB connections and monitoring job management to users (XDATA-01, XDATA-02)

---
*Phase: 46-analytics-continuous-intelligence*
*Completed: 2026-04-06*

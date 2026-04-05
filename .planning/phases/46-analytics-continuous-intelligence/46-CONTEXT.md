# Phase 46: Analytics & Continuous Intelligence - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Three capability tracks: (1) Connect external PostgreSQL/BigQuery databases and query them with natural language via the DataAnalysisAgent, (2) extend calendar tools into smart scheduling with meeting prep and follow-up automation, (3) create scheduled monitoring jobs that continuously track competitors/markets/topics with intelligence briefs and alert notifications. All three tracks build on Phase 39 integration infrastructure and Phase 45 notification delivery.

</domain>

<decisions>
## Implementation Decisions

### External Database Query Experience
- **SQL generation flow:** Smart auto-execute — simple SELECTs run immediately, complex queries (JOINs, subqueries, large table scans) show generated SQL and ask user confirmation before execution
- **Results display:** Agent gives a natural-language summary of findings first, with expandable sortable table and optional auto-chart underneath — conversational feel, detail on demand
- **Connection setup:** Guided form (host, port, database, user, password) with a "paste connection string" button that auto-fills all fields — serves both technical and non-technical users
- **Read-only enforcement:** All connections use strict read-only mode with 30-second query timeout (XDATA-06)
- **Query saving:** Claude's discretion — focus on core NL-to-SQL flow first, add saved queries if implementation allows

### Calendar Intelligence
- **Follow-up scheduling:** Agent suggests optimal follow-up time after sales calls based on free/busy data — user confirms before booking (not auto-book)
- **Calendar awareness depth:** Meeting list + AI-generated prep notes: what was discussed last time (from CRM/knowledge vault), open action items, relevant documents, attendee context from HubSpot deals (Phase 42)
- **Recurring task generation:** Claude's discretion on pattern detection approach — focus on getting calendar awareness right first
- **Free/busy scope:** Claude's discretion based on what Google Calendar API supports for multi-attendee free/busy lookups

### Monitoring Job Design
- **Creation flow:** Chat-first — user says "monitor Competitor X weekly" in chat, agent creates the job. Configuration page shows all active jobs for editing/pausing/deleting
- **Schedule model:** Smart frequency based on importance level — user picks critical (daily), normal (weekly), or low-priority (biweekly). System decides execution time. Simpler mental model than cron expressions.
- **Alert triggering:** AI-judged significance by default (ResearchAgent compares new findings against previous state), plus user-defined keyword triggers that always alert regardless of AI assessment
- **Source discovery:** Auto-discover relevant sources from topic (company site, news, social, product pages), user can pin must-watch URLs or exclude irrelevant ones

### Intelligence Brief Format
- **Delivery:** Short summary pushed to chat and notifications (Slack/Teams via Phase 45 dispatcher), full brief stored in knowledge vault for archival and search
- **Brief structure:** Claude's discretion — adapt format based on monitoring type (competitor vs market vs topic). Should be scannable and business-focused.
- **Knowledge graph depth:** Track entities (companies, people, products) AND their relationships (acquisitions, partnerships, competitive dynamics). Monitoring updates both entity data and cross-entity links via existing GraphService + graph_writer.
- **Alert detail level:** 2-3 sentence summary with key data points (what changed, when, impact estimate) directly in the notification — actionable without clicking through to the full brief

### Claude's Discretion
- Query saving feature scope (may skip in v1)
- Recurring task generation pattern detection approach
- Free/busy lookup scope (user only vs multi-attendee)
- Intelligence brief structure per monitoring type
- Auto-chart type selection for query results

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/agents/tools/calendar_tool.py`: Google Calendar read/write via OAuth — list events, create events. Extend with free/busy, prep notes, follow-up scheduling.
- `app/agents/tools/deep_research.py`: DeepResearchTool with Tavily search + Firecrawl scraping + knowledge vault ingestion. Foundation for monitoring job execution.
- `app/agents/research/agent.py`: ResearchAgent with query_planner, track_runner, synthesizer, graph_writer, cost_tracker tools. Orchestrates multi-track research.
- `app/agents/tools/graph_tools.py`: Knowledge graph read with Redis caching — all agents can query entities/findings.
- `app/services/graph_service.py`: GraphService for entity/relationship CRUD.
- `app/agents/research/tools/graph_writer.py`: Graph write tools for research findings.
- `app/config/integration_providers.py`: Provider registry — BigQuery already registered with readonly scopes.
- `app/services/scheduled_endpoints.py`: Cloud Scheduler pattern with secret verification — reuse for monitoring job triggers.
- `app/services/notification_dispatcher.py`: Phase 45 notification fan-out to Slack/Teams — reuse for alert delivery.

### Established Patterns
- OAuth credential storage via `integration_credentials` table (Phase 39) — PostgreSQL/BigQuery use this
- Sync state tracking via `integration_sync_state` table — reuse for monitoring job state
- Cloud Scheduler + `X-Scheduler-Secret` header verification for scheduled endpoints
- `asyncio.to_thread()` for wrapping sync SDK calls (established in Phase 42 HubSpot)
- Agent tool context state for credential access (`tool_context.state`)

### Integration Points
- DataAnalysisAgent (`app/agents/data/agent.py`) — add external DB query tools here
- OperationsAgent — already has communication tools (Phase 45), extend with calendar intelligence tools
- ResearchAgent — extend with scheduled monitoring execution
- Configuration page (`frontend/src/app/dashboard/configuration/page.tsx`) — add DB connections section + monitoring jobs section
- Provider registry — add `postgresql` provider entry alongside existing `bigquery`

</code_context>

<specifics>
## Specific Ideas

- External DB results should feel conversational — agent explains what it found, not just dumps a table
- Calendar prep notes should function like a chief-of-staff briefing — anticipate what the user needs before a meeting
- Monitoring should feel like having a research analyst on staff — user says "watch this" and gets periodic intelligence without managing the details
- Alert notifications should be actionable without clicking through — the key facts right in the message

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 46-analytics-continuous-intelligence*
*Context gathered: 2026-04-06*

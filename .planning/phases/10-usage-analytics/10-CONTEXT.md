# Phase 10: Usage Analytics - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning
**Source:** PRD Express Path (docs/superpowers/specs/2026-03-21-admin-panel-design.md)

<domain>
## Phase Boundary

This phase adds usage analytics dashboards to the admin panel: DAU/MAU charts, per-agent effectiveness metrics, feature usage breakdowns, and a configuration status overview. All data comes from existing Supabase tables — no new data collection. Pre-aggregated daily stats prevent expensive full-table scans.

**Requirements:** ANLT-01, ANLT-02, ANLT-04, ANLT-05 (4 total)
**NOT in scope:** ANLT-03 (billing dashboard — Phase 14, depends on Stripe integration)

</domain>

<decisions>
## Implementation Decisions

### Analytics Data Sources
- DAU/MAU: count distinct users from existing interaction tables (session_events, chat messages)
- Agent effectiveness: success/failure counts + response times from agent interaction logs
- Feature usage: count API calls by endpoint/feature from existing request logs
- Config status: query admin_agent_permissions + admin_config_history tables (from Phase 7)
- All queries use pre-aggregated daily summary tables or materialized views to avoid COUNT(*) full-table scans

### Pre-Aggregation Strategy
- Create a daily aggregation function/endpoint that computes stats and stores in summary tables
- Cloud Scheduler triggers daily aggregation (reuse pattern from Phase 8 health monitoring)
- Summary tables: `admin_analytics_daily` for DAU/MAU/message counts, `admin_agent_stats_daily` for per-agent metrics
- Supabase migration creates these tables + indexes
- Fallback: if materialized views aren't supported on current Supabase tier, use a scheduled summary insert instead

### Analytics Dashboard Frontend
- Route: `/admin/analytics` — main analytics page
- Uses `recharts@3.8+` (already installed in Phase 8) for charts
- KPI cards at top: DAU, MAU, total messages, total workflows
- Line charts: user activity trends (30 days), message volume over time
- Bar charts: per-agent effectiveness (success rate, avg response time)
- Feature usage breakdown: table or bar chart showing which features are most used
- Config status section: active feature flags count, current agent config versions
- Auto-refresh every 60 seconds (longer than monitoring — analytics data changes slowly)

### Admin Agent Analytics Tools
- New tools in `app/agents/admin/tools/analytics.py`:
  - `get_usage_stats` (auto) — DAU, MAU, messages, workflows for a date range
  - `get_agent_effectiveness` (auto) — per-agent success rate, avg response time
  - `get_engagement_report` (auto) — feature adoption, usage breakdowns
  - `generate_report` (auto) — build a summary report for a given date range
- All tools use autonomy enforcement from Phase 7 infrastructure

### Backend Structure
- `app/routers/admin/analytics.py` — analytics API endpoints
- `app/agents/admin/tools/analytics.py` — agent analytics tools
- `supabase/migrations/XXXX_analytics_summary_tables.sql` — summary tables
- Update `app/routers/admin/__init__.py` to register analytics router
- Update `app/agents/admin/agent.py` to register analytics tools

### Frontend Structure
- `frontend/src/app/(admin)/analytics/page.tsx` — main analytics dashboard
- Reuse existing recharts components from Phase 8 (Sparkline pattern)

### Claude's Discretion
- Exact chart dimensions, colors, and responsive breakpoints
- How to compute "agent effectiveness" (what counts as success vs failure)
- Whether to use tabs or sections for different analytics views
- The exact KPI card design (reuse Phase 8 StatusCard pattern or custom)
- How to handle empty/no-data states in charts
- Date range picker implementation (simple preset buttons vs full calendar)
- Whether config status needs its own section or a small card

</decisions>

<specifics>
## Specific Ideas

- KPI cards should use the same dark theme as monitoring status cards
- Agent effectiveness chart should show all 10 agents as horizontal bars
- DAU/MAU chart should be a dual-line chart (DAU in one color, MAU in another)
- Feature usage should group by category: chat, workflows, approvals, etc.
- Config status should be a compact card showing: X feature flags active, last config change Y ago
- The research SUMMARY.md flagged: "Confirm materialized view availability on current Supabase tier" — check this during research

</specifics>

<deferred>
## Deferred Ideas

- Retention cohort analysis (RETN-01) — needs 3+ months of user data
- Conversion funnel analysis (RETN-02) — future requirement
- Bulk CSV export of analytics data (RETN-03) — future requirement
- Real-time analytics streaming — polling is sufficient at this scale

</deferred>

---

*Phase: 10-usage-analytics*
*Context gathered: 2026-03-21 via PRD Express Path*

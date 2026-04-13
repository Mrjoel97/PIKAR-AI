---
phase: 67-customer-support-revamp
plan: "03"
subsystem: customer-support
tags: [customer-health, churn-risk, auto-ticket, channel-ingestion, migration]
dependency_graph:
  requires:
    - "67-01"
    - "67-02"
  provides:
    - CustomerHealthService
    - get_customer_health_dashboard tool
    - create_ticket_from_channel tool
    - customer_health_columns migration
  affects:
    - app/agents/customer_support/agent.py
    - app/agents/customer_support/tools.py
    - app/services/support_ticket_service.py
tech_stack:
  added:
    - app/services/customer_health_service.py
    - supabase/migrations/20260410000000_customer_health_columns.sql
    - tests/unit/test_customer_health_service.py
  patterns:
    - Python-side ticket stats aggregation (same pattern as Phase 64-01)
    - Lazy service imports inside tool functions for testability
    - Churn risk heuristic with three-tier classification (high/medium/low)
    - Template-free service (no LLM in service layer)
key_files:
  created:
    - app/services/customer_health_service.py
    - supabase/migrations/20260410000000_customer_health_columns.sql
    - tests/unit/test_customer_health_service.py
  modified:
    - app/services/support_ticket_service.py
    - app/agents/customer_support/tools.py
    - app/agents/customer_support/agent.py
    - app/agents/customer_support/__init__.py
    - tests/unit/test_customer_success_tools.py
decisions:
  - "[67-03]: Python-side ticket stats aggregation in get_ticket_stats — PostgREST has no GROUP BY (consistent with Phase 64-01 pattern)"
  - "[67-03]: Churn risk heuristics hard-coded as three-tier thresholds: high (>5 open OR >50% negative OR avg >48h), medium (>2 open OR >30% negative OR avg >24h)"
  - "[67-03]: create_ticket_from_channel appends [Source: channel, Message ID: id] metadata to description when channel_message_id is provided"
  - "[67-03]: SupportTicketService.create_ticket extended with source and sentiment params — new columns default to 'manual' and 'neutral' so existing callers are unaffected"
metrics:
  duration: 19min
  completed_date: "2026-04-13"
  tasks_completed: 2
  files_modified: 7
  tests_added: 15
---

# Phase 67 Plan 03: Customer Health Dashboard and Channel Auto-Ticket Summary

Customer health dashboard service (churn risk, sentiment trends, resolution time) and auto-ticket creation from inbound channels, backed by a DB migration adding sentiment/category/source/resolved_at columns.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add DB columns and CustomerHealthService | 7ccfd0c5 | migration, customer_health_service.py, support_ticket_service.py, test_customer_health_service.py |
| 2 | Add health/channel tools, wire into agent | 1a863ab7 | tools.py, agent.py, __init__.py, test_customer_success_tools.py |

## What Was Built

### Migration (`supabase/migrations/20260410000000_customer_health_columns.sql`)
Adds four columns to `support_tickets`:
- `sentiment TEXT CHECK (positive/neutral/negative) DEFAULT 'neutral'`
- `category TEXT`
- `source TEXT CHECK (manual/email/chat/webhook/api) DEFAULT 'manual'`
- `resolved_at TIMESTAMPTZ` — auto-set via trigger when status transitions to resolved/closed

Three covering indexes and a `set_ticket_resolved_at` trigger for automatic timestamp population.

### `SupportTicketService.get_ticket_stats`
Fetches up to 500 tickets and computes in Python:
- `open_count`, `resolved_count`, `total_count`
- `avg_resolution_hours` — computed from `created_at`/`resolved_at` pairs (None when no resolved tickets)
- `sentiment_breakdown` — `{positive, neutral, negative}` counts
- `priority_breakdown` — `{low, normal, high, urgent}` counts

### `SupportTicketService.create_ticket` (extended)
Accepts two new optional parameters: `source: str = "manual"` and `sentiment: str = "neutral"`. Existing callers are unaffected (defaults match old behavior).

### `CustomerHealthService` (`app/services/customer_health_service.py`)
New service with `get_health_dashboard(user_id)` that returns:
- `open_tickets`, `total_tickets`, `resolution_rate` (%)
- `avg_resolution_time_hours`
- `sentiment_summary` breakdown
- `churn_risk_level` — `high`, `medium`, or `low` based on defined heuristics
- `churn_risk_factors` — human-readable reasons list

Churn risk heuristics:
- **HIGH**: >5 open tickets, OR >50% negative sentiment, OR avg resolution >48h
- **MEDIUM**: >2 open tickets, OR >30% negative sentiment, OR avg resolution >24h
- **LOW**: otherwise

### `get_customer_health_dashboard` tool
Calls `CustomerHealthService().get_health_dashboard(user_id=get_current_user_id())`. Returns `{success, dashboard}`.

### `create_ticket_from_channel` tool
Creates tickets with `source=channel`. When `channel_message_id` is provided, appends `[Source: {channel}, Message ID: {id}]` to the description for deduplication audit trail.

### Agent Wiring
Both tools registered in `CUSTOMER_SUPPORT_AGENT_TOOLS`. Instruction updated with CAPABILITIES entries directing the agent to use `get_customer_health_dashboard` for health/churn queries and `create_ticket_from_channel` for inbound messages. BEHAVIOR section instructs widget rendering for dashboard results.

## Tests

**15 new tests total (all passing):**

`tests/unit/test_customer_health_service.py` — 10 tests:
- `TestGetTicketStats`: 3 tests covering basic aggregation, no-resolved (None avg), empty list
- `TestCustomerHealthDashboard`: 7 tests covering all churn risk tiers (high via open count, high via negative %, high via slow resolution, medium, low, empty)

`tests/unit/test_customer_success_tools.py` — 5 new tests added:
- `TestGetCustomerHealthDashboardTool`: success case, error case
- `TestCreateTicketFromChannelTool`: email channel, with message ID, without message ID

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test mock used real JWT token path**
- **Found during:** Task 1 test run
- **Issue:** `SupportTicketService(user_token="tok")` triggered real Supabase `set_session()` which rejected a non-JWT string
- **Fix:** Tests create service with `user_token=None` and patch `execute_async` at module level; `AdminService` also patched to avoid real init
- **Files modified:** `tests/unit/test_customer_health_service.py`
- **Commit:** 7ccfd0c5 (included in task commit)

**2. [Rule 1 - Bug] Patch target for `get_current_user_id` was wrong**
- **Found during:** Task 2 test run
- **Issue:** Tool uses lazy import `from app.services.request_context import get_current_user_id` inside the function body, so patching `app.agents.customer_support.tools.get_current_user_id` raises `AttributeError`
- **Fix:** Patched at `app.services.request_context.get_current_user_id` (the source module)
- **Files modified:** `tests/unit/test_customer_success_tools.py`
- **Commit:** 1a863ab7 (included in task commit)

## Self-Check: PASSED

All 8 files verified present on disk. Both task commits (7ccfd0c5, 1a863ab7) verified in git log.

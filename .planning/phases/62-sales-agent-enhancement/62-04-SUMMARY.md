---
phase: 62-sales-agent-enhancement
plan: "04"
subsystem: sales-crm
tags: [hubspot, crm, sales, real-api, degraded-tool-retirement]
dependency_graph:
  requires: ["62-01"]
  provides: ["SALES-05", "SALES-06"]
  affects: ["app/agents/tools/hubspot_tools.py", "app/agents/tools/registry.py", "app/agents/tools/degraded_tools.py", "app/agents/sales/agent.py", "app/services/hubspot_service.py"]
tech_stack:
  added: []
  patterns: ["real-api-over-degraded", "graceful-degradation", "module-level-patchable-imports", "tdd-red-green"]
key_files:
  created:
    - tests/unit/test_hubspot_tools_real.py
  modified:
    - app/agents/tools/hubspot_tools.py
    - app/services/hubspot_service.py
    - app/agents/tools/degraded_tools.py
    - app/agents/tools/registry.py
    - app/agents/sales/agent.py
decisions:
  - "Module-level HubSpotService and AdminService imports in hubspot_tools.py enable patch('app.agents.tools.hubspot_tools.HubSpotService') test targeting without internal refactor"
  - "score_hubspot_lead checks hubspot_contact_id presence before attempting push — contacts without HS ID degrade to local-only silently (no exception raised)"
  - "sync_deal_notes always writes to local hubspot_deals.properties even when HubSpot push succeeds — ensures local DB is source of truth for last_meeting_notes"
  - "registry.py promoted_score_lead kept for score_leads (plural) workflow alias; score_lead (singular) now routes to real_score_lead"
  - "Registry pre-existing E402/I001 lint errors are out-of-scope — file has 87 pre-existing violations, my additions introduce zero new ones"
metrics:
  duration: 19min
  completed_date: "2026-04-11"
  tasks: 2
  files_modified: 5
  files_created: 1
---

# Phase 62 Plan 04: HubSpot Real CRM Tools Summary

Real HubSpot API tools for lead scoring, CRM querying, and deal note auto-sync that replace the three degraded CRM placeholder tools (create_contact, score_lead, query_crm).

## What Was Built

### Task 1: Three new real HubSpot tools + service methods (TDD)

**`app/services/hubspot_service.py`** — Two new service methods:
- `update_contact_score(user_id, contact_id, score, qualification_data)`: pushes `hs_lead_status` and `pikar_lead_score` to HubSpot contact via SDK, sets Redis skip flag, updates local `contacts.metadata`
- `add_deal_note(user_id, deal_id, note_text, stage_change)`: creates HubSpot note engagement via `crm.objects.notes.basic_api.create()` with deal association, optionally triggers `push_deal_to_hubspot()` for stage change, updates `last_activity_at`

**`app/agents/tools/hubspot_tools.py`** — Three new agent-callable tools:
- `score_hubspot_lead(contact_name_or_email, score, framework, qualification_notes)`: looks up contact by name/email, pushes score to HubSpot if connected, logs `lead_scored` activity, degrades gracefully to local-only when no `hubspot_contact_id`
- `query_hubspot_crm(query_type, lifecycle_stage, source, limit)`: real query of local `contacts` or `hubspot_deals` tables with optional filters; returns results + aggregations (by-stage breakdown, total value for deals)
- `sync_deal_notes(deal_name_or_id, notes, next_steps, stage_change)`: looks up deal by name/UUID, pushes formatted notes as HubSpot engagement if connected, always updates local `properties.last_meeting_notes` and `last_activity_at`

**`HUBSPOT_TOOLS`** export updated from 5 to 8 entries.

Module-level imports (`HubSpotService`, `AdminService`, `_execute_async_query`) added for test patchability.

### Task 2: Retire degraded tools, update registry, guide agent

**`app/agents/tools/degraded_tools.py`**:
- Removed `create_contact`, `score_lead`, `query_crm` functions entirely
- Added module docstring note: "Phase 62 (SALES-06): create_contact, score_lead, query_crm moved to real HubSpot API tools"

**`app/agents/tools/registry.py`**:
- Replaced `from degraded_tools import create_contact as degraded_create_contact` with `from hubspot_tools import create_hubspot_contact as real_create_contact`
- Replaced `query_crm as degraded_query_crm` with `query_hubspot_crm as real_query_crm`
- Added `score_hubspot_lead as real_score_lead` import alongside
- TOOL_REGISTRY now maps `"create_contact" -> real_create_contact`, `"score_lead" -> real_score_lead`, `"query_crm" -> real_query_crm`
- Backward compatibility preserved: same string keys, now real API implementations

**`app/agents/sales/agent.py`**:
- Added `AUTO-SYNC BEHAVIOR` section to `SALES_AGENT_INSTRUCTION` directing the agent to use `sync_deal_notes`, `score_hubspot_lead`, and `query_hubspot_crm`

## Test Coverage

**`tests/unit/test_hubspot_tools_real.py`** — 11 tests, all passing:

| # | Tool | Path tested |
|---|------|-------------|
| 1 | `score_hubspot_lead` | HubSpot-connected: pushes score via `update_contact_score` |
| 2 | `score_hubspot_lead` | No `hubspot_contact_id`: local-only, `synced_to_hubspot=False` |
| 3 | `query_hubspot_crm` | Contacts query returns real data + count |
| 4 | `query_hubspot_crm` | Filters by lifecycle_stage and source |
| 5 | `sync_deal_notes` | HubSpot-connected: pushes note + stage change |
| 6 | `sync_deal_notes` | No `hubspot_deal_id`: local-only, `synced_to_hubspot=False` |
| 7a | `score_hubspot_lead` | No user_id: returns `{"error": "Authentication required"}` |
| 7b | `query_hubspot_crm` | No user_id: returns `{"error": "Authentication required"}` |
| 7c | `sync_deal_notes` | No user_id: returns `{"error": "Authentication required"}` |
| 8 | Export | `HUBSPOT_TOOLS` has exactly 8 entries |
| 9 | Export | All 3 new tools present in `HUBSPOT_TOOLS` by name |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `AdminService` not patchable via local import**
- **Found during:** Task 1 — first test run
- **Issue:** `score_hubspot_lead`, `query_hubspot_crm`, `sync_deal_notes` called `from app.services.base_service import AdminService` inside the function body, making `patch("app.agents.tools.hubspot_tools.AdminService")` fail to intercept it
- **Fix:** Added `AdminService` to the module-level try/except import block in `hubspot_tools.py`, alongside `HubSpotService` and `_execute_async_query`, so all three are patchable at the module level
- **Files modified:** `app/agents/tools/hubspot_tools.py`

**2. [Rule 3 - Blocking] `_execute_async_query` mock returns AsyncMock not awaitable result**
- **Found during:** Task 1 — test_query_crm_returns_contacts_from_local_table
- **Issue:** `patch(..., return_value=_mock_execute_async(contacts))` set return_value to an AsyncMock object, but calling the patched function returned the AsyncMock directly (not awaiting it), so `.data` was on the coroutine not the result
- **Fix:** Changed tests to use `new_callable=AsyncMock, return_value=_mock_result(data)` for single-call mocks; kept `side_effect=[_mock_execute_async(...), ...]` pattern for multi-call mocks
- **Files modified:** `tests/unit/test_hubspot_tools_real.py`

**3. [Rule 3 - Blocking] Task 2 edits lost by unintended git stash drop**
- **Found during:** Task 2 verification
- **Issue:** `git stash` during lint pre-check stashed Task 2 working tree changes; subsequent `git stash drop` discarded them
- **Fix:** Re-applied all three Task 2 edits (degraded_tools.py, registry.py, agent.py) from memory/plan spec
- **Files modified:** `app/agents/tools/degraded_tools.py`, `app/agents/tools/registry.py`, `app/agents/sales/agent.py`

**4. [Rule 1 - Deviation] `app/workflows/tool_registry.py` referenced in plan does not exist**
- **Found during:** Task 2 planning
- **Issue:** Plan mentions `app/workflows/tool_registry.py` as a file to update, but this file does not exist. The actual workflow tool registry is at `app/agents/tools/registry.py`
- **Fix:** Applied all registry changes to the correct file (`app/agents/tools/registry.py`)

## Self-Check: PASSED

- `tests/unit/test_hubspot_tools_real.py` — exists and has 11 tests
- Commit `e5fac860` — Task 1 (hubspot_tools.py, hubspot_service.py, tests)
- Commit `b5a27f4c` — Task 2 (degraded_tools.py, registry.py, agent.py)
- `HUBSPOT_TOOLS` has 8 entries (verified by test)
- `create_contact`, `score_lead`, `query_crm` removed from `degraded_tools.py` (verified by grep)
- Lint clean on all 4 modified app files

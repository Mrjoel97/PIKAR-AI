---
phase: 62-sales-agent-enhancement
plan: "01"
subsystem: sales-agent
tags: [sales, followup, email, hubspot, crm, tdd]
dependency_graph:
  requires:
    - app/agents/tools/hubspot_tools.py
    - app/services/hubspot_service.py
    - app/services/request_context.py
  provides:
    - app/agents/tools/sales_followup.py (generate_followup_email, SALES_FOLLOWUP_TOOLS)
  affects:
    - app/agents/sales/agent.py
tech_stack:
  added: []
  patterns:
    - lazy-import for HubSpotService (same pattern as hubspot_tools.py)
    - graceful CRM degradation via try/except in enrichment step
    - _get_user_id() helper for request-scoped auth
key_files:
  created:
    - app/agents/tools/sales_followup.py
    - tests/unit/test_sales_followup.py
  modified:
    - app/agents/sales/agent.py
decisions:
  - "Lazy import HubSpotService inside generate_followup_email to match existing tool pattern and avoid circular imports"
  - "CRM enrichment is non-fatal: ValueError/Exception from HubSpot is caught and logged at DEBUG; email generates from meeting context alone"
  - "Patch target for tests is app.services.hubspot_service.HubSpotService (lazy import path), not app.agents.tools.sales_followup.HubSpotService"
  - "Import sort fix (ruff I001) applied to agent.py when wiring new import"
metrics:
  duration: 11min
  completed: "2026-04-11"
  tasks_completed: 2
  files_changed: 3
---

# Phase 62 Plan 01: Sales Follow-Up Email Auto-Drafting Summary

**One-liner:** Post-meeting follow-up email tool with HubSpot CRM enrichment and graceful degradation when CRM is unavailable, wired into the Sales Agent.

## What Was Built

`generate_followup_email` is a new async agent tool in `app/agents/tools/sales_followup.py` that:

1. Extracts the authenticated user from request context (returns error dict if absent).
2. Attempts CRM enrichment by calling `HubSpotService().get_deal_context()` — any exception is caught and logged at DEBUG level, allowing the email to proceed without deal data.
3. Builds a multi-section plain-text email:
   - Greeting using the contact's first name
   - Meeting recap paragraph from `meeting_notes`
   - Deal context section (stage, formatted amount, pipeline) — only when HubSpot data is available
   - Numbered next-steps list from the `next_steps` parameter
   - CTA paragraph and professional sign-off
4. Returns `{"success": True, "email": {subject, to, body, suggested_cta}, "deal_context": <dict|None>}`.

The `SALES_FOLLOWUP_TOOLS` export is wired into `SALES_AGENT_TOOLS` in `app/agents/sales/agent.py`, and a POST-MEETING FOLLOW-UP instruction block was added to `SALES_AGENT_INSTRUCTION` to guide the agent to proactively offer follow-up drafts after call summaries.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 (RED) | Failing tests for generate_followup_email | c8dc5254 | tests/unit/test_sales_followup.py |
| 1 (GREEN) | Implement tool + fix test mock paths | ac3c9eff | app/agents/tools/sales_followup.py, tests/unit/test_sales_followup.py |
| 2 | Wire into Sales Agent + instruction update | a6e99e08 | app/agents/sales/agent.py |

## Verification Results

- `uv run pytest tests/unit/test_sales_followup.py -x -v` — 5/5 passed
- `uv run python -c "from app.agents.sales.agent import sales_agent; assert any('followup' in str(t) for t in sales_agent.tools)"` — PASSED (56 tools total)
- `uv run ruff check app/agents/tools/sales_followup.py app/agents/sales/agent.py` — All checks passed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test mock patch path corrected**
- **Found during:** Task 1 GREEN phase (first test run)
- **Issue:** Tests patched `app.agents.tools.sales_followup.HubSpotService` but the import is lazy (inside the function body), so the name doesn't exist at module scope — `AttributeError` on all 4 HubSpot-involving tests.
- **Fix:** Updated all 4 patch targets to `app.services.hubspot_service.HubSpotService`, which is where the class lives and where Python resolves the lazy import.
- **Files modified:** tests/unit/test_sales_followup.py
- **Commit:** ac3c9eff

**2. [Rule 3 - Blocking] Import sort in agent.py (ruff I001)**
- **Found during:** Task 2 lint check
- **Issue:** New `SALES_FOLLOWUP_TOOLS` import was placed after `SALES_IMPROVE_TOOLS`, violating alphabetical import order enforced by ruff.
- **Fix:** Moved import to alphabetically correct position (`sales_followup` before `self_improve`).
- **Files modified:** app/agents/sales/agent.py
- **Commit:** a6e99e08

## Self-Check: PASSED

| Item | Status |
|------|--------|
| app/agents/tools/sales_followup.py | FOUND |
| tests/unit/test_sales_followup.py | FOUND |
| .planning/phases/62-sales-agent-enhancement/62-01-SUMMARY.md | FOUND |
| commit c8dc5254 (RED tests) | FOUND |
| commit ac3c9eff (GREEN implementation) | FOUND |
| commit a6e99e08 (Task 2 wiring) | FOUND |

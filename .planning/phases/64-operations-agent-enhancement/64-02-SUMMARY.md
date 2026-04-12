---
phase: 64-operations-agent-enhancement
plan: 02
subsystem: api
tags: [fastapi, operations-agent, sop, integrations, token-expiry]

# Dependency graph
requires:
  - phase: 64-01
    provides: ops_tools.py with OPS_ANALYSIS_TOOLS, workflow bottleneck tools already wired into agent
provides:
  - generate_sop_document tool: structured SOP generation with purpose, scope, roles, steps, quality checks, revision history
  - GET /integrations/health endpoint: per-provider status enriched with token expiry detection
  - Operations Agent instruction: SOP generation + integration health guidance sections
affects: [64-03, 64-04, operations-agent-enhancement, agent-instructions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SOP document ID format: SOP-{DEPT[:3]}-{YYYYMMDDHHMMSS} for unique traceable identifiers"
    - "Token expiry enrichment: 7-day threshold for expiring_soon flagging, null for disconnected, valid otherwise"
    - "Sync tool pattern (no asyncio wrapper) for pure data-transformation tools like generate_sop_document"

key-files:
  created:
    - app/agents/tools/ops_tools.py (generate_sop_document + _format_sop_as_text added to existing file)
    - tests/unit/test_sop_generation_tool.py
    - tests/unit/test_integration_health_endpoint.py
  modified:
    - app/routers/integrations.py (GET /integrations/health endpoint + datetime imports)
    - app/agents/operations/agent.py (SOP Generation + Integration Health instruction sections)

key-decisions:
  - "generate_sop_document is a sync function (no DB/async calls) — no asyncio wrapper needed unlike inventory.py tools"
  - "Token expiry 7-day threshold for expiring_soon detection; credentials fetched per-provider via get_credentials"
  - "OPS_ANALYSIS_TOOLS already wired via *OPS_ANALYSIS_TOOLS from Plan 01 — generate_sop_document auto-included on append"
  - "GET /integrations/health placed before /{provider} DELETE route to avoid path ambiguity in FastAPI routing"

patterns-established:
  - "SOP structure: document_id + title + version + effective_date + department + purpose + scope + procedure + quality_checks + revision_history"
  - "Integration health enrichment: call get_integration_status for base list, then get_credentials per connected provider for expiry check"

requirements-completed: [OPS-02, OPS-05]

# Metrics
duration: 16min
completed: 2026-04-12
---

# Phase 64 Plan 02: Operations Agent Enhancement — SOP Generation and Integration Health Summary

**SOP generation tool producing structured ISO-style documents from conversational input, plus /integrations/health endpoint with 7-day token expiry detection**

## Performance

- **Duration:** 16 min
- **Started:** 2026-04-12T20:44:19Z
- **Completed:** 2026-04-12T21:00:24Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- `generate_sop_document` tool creates formal SOP documents with document ID, purpose, scope, roles, numbered procedure steps, quality checks, and revision history — plus a workflow template offer
- `GET /integrations/health` endpoint returns all providers with enriched token expiry status: `expiring_soon` (within 7 days with days remaining), `valid`, or `null` for disconnected
- Operations Agent instruction updated with SOP generation trigger phrases, workflow-template handoff pattern, and integration health guidance including proactive expiry warnings

## Task Commits

Each task was committed atomically:

1. **TDD RED — failing tests** - `5e7f9070` (test)
2. **TDD GREEN — SOP tool + health endpoint** - `6e0ed82c` (feat)
3. **Task 2 — agent wiring + instruction** - `a4b3ae51` (feat)

## Files Created/Modified
- `app/agents/tools/ops_tools.py` — Added `generate_sop_document`, `_format_sop_as_text` helper, updated `OPS_ANALYSIS_TOOLS`
- `app/routers/integrations.py` — Added `GET /integrations/health` with token expiry enrichment, added `datetime/timedelta/timezone` imports
- `app/agents/operations/agent.py` — Added SOP Generation and Integration Health sections to `OPERATIONS_AGENT_INSTRUCTION`
- `tests/unit/test_sop_generation_tool.py` — 8 tests covering structured output, minimal input, formatted text, suggestion, document ID format
- `tests/unit/test_integration_health_endpoint.py` — 6 tests covering provider list, expiring token, valid token, disconnected, unauthenticated, no-expiry

## Decisions Made
- `generate_sop_document` is a sync function (pure data transformation, no DB calls) — follows the simpler function pattern rather than asyncio-wrapped service calls
- Token expiry uses a 7-day threshold for `expiring_soon`, returning `expires_in_days` alongside the status flag so the UI can render a countdown
- `GET /integrations/health` placed before `DELETE /{provider}` in the router to prevent FastAPI matching `health` as a provider name
- `OPS_ANALYSIS_TOOLS` already included via `*OPS_ANALYSIS_TOOLS` from Plan 01 — appending `generate_sop_document` to the list auto-wires it without touching the agent tools list

## Deviations from Plan

None - plan executed exactly as written. `ops_tools.py` was already created by Plan 01 as anticipated; the plan's "if file already exists, append" branch was followed correctly.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- SOP generation and integration health are ready for Plan 03
- Operations Agent now handles the full OPS-02 and OPS-05 requirements
- Token expiry warnings surfaced at the API level; frontend integration health dashboard at `/settings/integrations` can consume the new endpoint

---
*Phase: 64-operations-agent-enhancement*
*Completed: 2026-04-12*

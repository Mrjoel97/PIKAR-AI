---
phase: 62-sales-agent-enhancement
plan: "03"
subsystem: api
tags: [pdf, jinja2, weasyprint, hubspot, document-service, sales]

# Dependency graph
requires:
  - phase: 62-01
    provides: sales_followup tool and HubSpotService.get_deal_context patterns
  - phase: 62-02
    provides: PIPELINE_DASHBOARD_TOOLS wiring pattern in sales agent
  - phase: 40
    provides: DocumentService.generate_pdf and VALID_TEMPLATES infrastructure
provides:
  - generate_sales_proposal tool with auto-population from HubSpot deal context
  - sales_proposal Jinja2 HTML template (branded PDF, all required sections)
  - PROPOSAL_TOOLS export for Sales Agent wiring
  - 6 unit tests covering success, enrichment, calculation, and error cases
affects: [sales-agent, document-service, proposal-generation, SALES-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Lazy service imports inside tool functions (same as sales_followup pattern)
    - Patch at service module level (app.services.X.ClassName) for lazy-import tools
    - PROPOSAL_TOOLS list export for agent wiring consistency
    - TDD red-green cycle with module-level patch paths

key-files:
  created:
    - app/agents/tools/proposal_generator.py
    - app/templates/pdf/sales_proposal.html
    - tests/unit/test_proposal_generator.py
  modified:
    - app/services/document_service.py
    - app/agents/sales/agent.py

key-decisions:
  - "Patch at service module level (app.services.document_service.DocumentService) not at tool module level — lazy imports inside tool functions require this approach"
  - "HubSpotService instantiated with no args (BaseService takes user_token not user_id); user_id passed to get_deal_context call directly"
  - "Line item totals auto-calculated (quantity * unit_price); subtotal and discount applied before deriving total_amount"
  - "Single As Quoted fallback line item when total_amount provided but no line_items — prevents empty table in template"
  - "HubSpot enrichment is non-fatal (try/except with warning log) — proposal generation degrades gracefully if CRM is unavailable"

patterns-established:
  - "Lazy import pattern for DocumentService and HubSpotService inside async tool functions — consistent with Phase 62-01 and 62-02"
  - "Test patch paths must match the import resolution path of the lazy import, not the tool module namespace"

requirements-completed: [SALES-03]

# Metrics
duration: 18min
completed: 2026-04-11
---

# Phase 62 Plan 03: Sales Proposal Generator Summary

**One-request branded PDF proposal generation from HubSpot deal context using DocumentService with sales_proposal Jinja2 template and automatic line-item calculation**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-11T18:45:00Z
- **Completed:** 2026-04-11T19:03:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Created `sales_proposal.html` Jinja2 template with all required sections: client info header, executive summary, line-items table with per-item totals, pricing summary (subtotal/discount/total), timeline, terms, validity notice, and dual signature block
- Implemented `generate_sales_proposal` tool with HubSpot auto-population when `deal_id` provided, line-item total calculation, discount application, and graceful fallback to manual input
- Wired `PROPOSAL_TOOLS` into `SALES_AGENT_TOOLS` with a PROPOSAL GENERATION instruction block guiding the agent on when and how to use the tool
- 6 unit tests (TDD red-green) covering all behavior paths: success, deal enrichment, explicit client, line item math, and both error cases

## Task Commits

Each task was committed atomically:

1. **Task 1: Create sales_proposal PDF template and register it** - `b0bddd71` (feat)
2. **Task 2 RED: Failing tests for generate_sales_proposal** - `e3196beb` (test)
3. **Task 2 GREEN: Implement tool + wire into Sales Agent** - `65e5f8c3` (feat)

## Files Created/Modified

- `app/templates/pdf/sales_proposal.html` - Jinja2 HTML template with 8 sections: client header, executive summary, line-items table, pricing summary, timeline, terms, validity, signature block
- `app/agents/tools/proposal_generator.py` - `generate_sales_proposal` async tool with HubSpot enrichment, line-item calculation, DocumentService PDF generation; exports `PROPOSAL_TOOLS`
- `tests/unit/test_proposal_generator.py` - 6 unit tests with mocked DocumentService and HubSpotService
- `app/services/document_service.py` - Added `"sales_proposal"` to `VALID_TEMPLATES`
- `app/agents/sales/agent.py` - Added `PROPOSAL_TOOLS` import, wired into `SALES_AGENT_TOOLS`, added PROPOSAL GENERATION instruction block

## Decisions Made

- Patch at service module level (`app.services.document_service.DocumentService`) not at tool module level — lazy imports inside tool functions require this approach (same lesson as Phase 62-01)
- `HubSpotService()` takes no constructor args; `user_id` is passed to `get_deal_context()` directly
- HubSpot enrichment wrapped in `try/except` — CRM unavailability should not block proposal generation
- Single "As Quoted" fallback line item when `total_amount` given without `line_items` — keeps template table populated

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] HubSpotService constructor called without user_id arg**
- **Found during:** Task 2 (implementation)
- **Issue:** Plan showed `HubSpotService(user_id=user_id)` but `BaseService.__init__` takes `user_token`, not `user_id`
- **Fix:** Changed to `HubSpotService()` with `user_id` passed to `get_deal_context()` call
- **Files modified:** app/agents/tools/proposal_generator.py
- **Verification:** Agent loads cleanly, tests pass
- **Committed in:** 65e5f8c3

**2. [Rule 1 - Bug] Test patch paths wrong for lazy-import pattern**
- **Found during:** Task 2 RED phase (tests ran but AttributeError on missing `DocumentService` attr)
- **Issue:** Tests patched `app.agents.tools.proposal_generator.DocumentService` but that name doesn't exist at module level due to lazy imports
- **Fix:** Changed all patches to `app.services.document_service.DocumentService` and `app.services.hubspot_service.HubSpotService`
- **Files modified:** tests/unit/test_proposal_generator.py
- **Verification:** All 6 tests pass GREEN
- **Committed in:** 65e5f8c3

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs)
**Impact on plan:** Both fixes required for correctness. No scope creep.

## Issues Encountered

- `uv` not on PATH in shell — located at `/c/Users/expert/AppData/Roaming/Python/Python313/Scripts/uv.exe` and used full path throughout. No impact on deliverables.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `generate_sales_proposal` is live in the Sales Agent — users can request proposals immediately
- 62-04 (HubSpot real tools) runs in parallel and adds `score_hubspot_lead`, `query_hubspot_crm`, `sync_deal_notes` to the same agent — no conflicts observed
- The `sales_proposal` template can be extended with additional sections (e.g., case studies, team bios) without touching the tool

---
*Phase: 62-sales-agent-enhancement*
*Completed: 2026-04-11*

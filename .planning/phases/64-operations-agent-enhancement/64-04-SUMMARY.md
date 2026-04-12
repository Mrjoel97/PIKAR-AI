---
phase: 64-operations-agent-enhancement
plan: 04
subsystem: api
tags: [python, supabase, inventory, vendor, purchase-order, degraded-tools, ops]

# Dependency graph
requires:
  - phase: 64-03
    provides: vendor_subscriptions table schema (id, user_id, name, category, monthly_cost, billing_cycle, etc.)
  - phase: 64-01
    provides: WorkflowBottleneckService, OPS_ANALYSIS_TOOLS wiring pattern
provides:
  - VendorOpsService with real update_inventory_real, create_vendor_record, create_purchase_order
  - Module-level create_vendor / update_inventory / create_po wrappers (drop-in registry replacements)
  - Tool registry entries for create_vendor, update_inventory, create_po now point to VendorOpsService
  - 14 unit tests covering all paths including backward compat and status assertions
affects: [70-degraded-tool-cleanup, ops-agent, workflow-engine]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level _get_service_client() wrapper for testable lazy Supabase client access"
    - "Module-level create_task wrapper for patchable lazy agent tool imports"
    - "module-level get_current_user_id import (request_context has no heavy deps) for test patchability"
    - "Commented-out degraded imports follow established Phase 60/62 DEPRECATED pattern"

key-files:
  created:
    - app/services/vendor_ops_service.py
    - tests/unit/test_real_ops_tools.py
  modified:
    - app/agents/tools/registry.py
    - app/agents/tools/degraded_tools.py

key-decisions:
  - "VendorOpsService uses lazy import for InventoryService (avoids supabase.Client at module load) but module-level wrapper functions for get_current_user_id and create_task to ensure test patchability"
  - "_get_service_client() module-level wrapper isolates get_service_client from the import-time Supabase chain — tests patch this one name instead of the entire supabase module"
  - "update_inventory does NOT fall back to ShopifyService — Shopify inventory is managed via the separate Shopify sync; this tool wraps the internal InventoryService only"
  - "create_purchase_order uses PO-YYMMDD-NNNN format with random 4-digit suffix for same-day uniqueness without requiring a DB sequence"
  - "Degraded functions in degraded_tools.py preserved with DEPRECATED comments — same pattern as Phase 60 FIN-06 and Phase 62 SALES-06"

patterns-established:
  - "Module-level lazy-import wrapper pattern (_get_service_client, create_task) for services that need patchable test hooks without triggering full import chains"
  - "sys.modules supabase stub in test file header allows InventoryService (which does from supabase import Client) to import cleanly without the real SDK"

requirements-completed: [OPS-06]

# Metrics
duration: 19min
completed: 2026-04-12
---

# Phase 64 Plan 04: Operations Agent Enhancement — Degraded Tool Replacement Summary

**VendorOpsService replaces three OPS-06 degraded placeholders: update_inventory delegates to InventoryService.update_stock, create_vendor inserts into vendor_subscriptions, create_po generates a PO-YYMMDD-NNNN reference and tracked task — all returning status="completed" instead of "degraded_completed"**

## Performance

- **Duration:** 19 min
- **Started:** 2026-04-12T21:05:35Z
- **Completed:** 2026-04-12T21:24:37Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `VendorOpsService` with three real business-logic methods replacing the three OPS-06 degraded stubs
- `update_inventory` now calls `InventoryService.update_stock` with a product_id fast-path and a name-search fallback — real stock changes instead of task creation
- `create_vendor` inserts a real row into the `vendor_subscriptions` table (created in Plan 03) instead of creating a degraded task
- `create_po` generates a structured PO reference (PO-YYMMDD-NNNN) and a tracked task with the PO reference in the description
- Tool registry updated: all three entries now point to `real_*` functions from VendorOpsService, following the Phase 60/62 DEPRECATED pattern
- 14 unit tests covering direct path, name-search found/not-found, minimal/full inputs, PO reference format, backward compat kwargs, and status assertions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create VendorOpsService with real implementations (TDD)** - `4401a5cc` (feat)
2. **Task 2: Wire real implementations into tool registry** - `db2fb2ac` (feat)

## Files Created/Modified

- `app/services/vendor_ops_service.py` — VendorOpsService class + module-level wrappers matching degraded tool signatures
- `tests/unit/test_real_ops_tools.py` — 14 unit tests covering all three tools end-to-end
- `app/agents/tools/registry.py` — Degraded imports commented out, real VendorOpsService imports added, tool map updated
- `app/agents/tools/degraded_tools.py` — DEPRECATED comments added to create_vendor, update_inventory, create_po

## Decisions Made

- `_get_service_client()` module-level wrapper isolates `get_service_client` from the Supabase import chain — tests patch this one name without triggering supabase._async.client
- Module-level `create_task` wrapper (delegates to lazy `from app.agents.sales.tools import create_task`) makes the PO creation step patchable in tests without full agent import chain
- `update_inventory` does NOT delegate to `ShopifyService` — Shopify inventory is managed via the separate Shopify sync path; this tool wraps only the internal `InventoryService`
- PO reference format `PO-YYMMDD-NNNN` with 4-digit random suffix chosen for uniqueness without requiring a DB sequence or separate PO table

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Lazy import pattern required for InventoryService to avoid supabase.Client at module load**
- **Found during:** Task 1 (TDD GREEN phase)
- **Issue:** `from app.commerce.inventory_service import InventoryService` at module level triggers `from supabase import Client` which fails in test environment (`ImportError: cannot import name 'Client'`)
- **Fix:** Kept InventoryService as a lazy import inside the method; added supabase stub to test file header; updated test patch targets to `app.commerce.inventory_service.InventoryService`
- **Files modified:** `app/services/vendor_ops_service.py`, `tests/unit/test_real_ops_tools.py`
- **Verification:** All 14 tests pass
- **Committed in:** `4401a5cc` (Task 1 commit)

**2. [Rule 1 - Bug] get_service_client lazy import chain fails in tests (supabase._async.client)**
- **Found during:** Task 1 (vendor record creation tests)
- **Fix:** Extracted `_get_service_client()` as a module-level patchable wrapper; tests patch `app.services.vendor_ops_service._get_service_client`; also pre-imports `get_current_user_id` at module level (request_context has no heavy deps) so tests can patch it without lazy-import escaping
- **Files modified:** `app/services/vendor_ops_service.py`, `tests/unit/test_real_ops_tools.py`
- **Verification:** All 14 tests pass
- **Committed in:** `4401a5cc` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — import chain bugs in test environment)
**Impact on plan:** Both fixes necessary to make the tests work correctly. No scope creep. Production code paths unchanged.

## Issues Encountered

- Registry verification `python -c "from app.agents.tools.registry import TOOL_MAP ..."` cannot run outside the full Docker environment because the registry import chain requires `google.adk`. Verification was confirmed through the unit test suite instead (which uses the conftest google stub). Pre-existing E402 lint errors in registry.py are out of scope (exist on base branch before this plan).

## User Setup Required

None — no external service configuration required. The `vendor_subscriptions` table was created in Plan 03. `InventoryService` uses the existing `products`/`inventory` tables.

## Next Phase Readiness

- OPS-06 complete: all three degraded ops tools replaced with real implementations
- Phase 64 Wave 2 complete (Plans 03 + 04)
- Phase 70 (degraded tool cleanup) will now find these three tools already migrated — reduces its scope by 3
- The pattern established here (`_get_service_client` wrapper, module-level `create_task` wrapper) is reusable for any future service that needs testable lazy Supabase + agent tool access

---
*Phase: 64-operations-agent-enhancement*
*Completed: 2026-04-12*

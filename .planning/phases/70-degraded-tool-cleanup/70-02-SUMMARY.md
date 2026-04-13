---
phase: 70-degraded-tool-cleanup
plan: "02"
subsystem: workflow-engine
tags: [degraded-tools, registry, cleanup, promotion, honest-errors]
dependency_graph:
  requires: [70-01]
  provides: [clean-tool-registry, honest-error-stubs, promoted-workflow-tools]
  affects: [app/agents/tools/registry.py, app/agents/tools/degraded_tools.py, app/workflows/execution_contracts.py]
tech_stack:
  added: []
  patterns: [factory-promotion, honest-error-stub, module-level-promoted-functions]
key_files:
  created:
    - tests/unit/test_degraded_tool_cleanup.py
  modified:
    - app/agents/tools/registry.py
    - app/agents/tools/degraded_tools.py
    - tests/unit/test_degraded_tools.py
decisions:
  - "Promoted 16 Category A tools directly into registry.py as promoted_* functions — avoids extra module files for thin wrappers"
  - "book_travel gets not_available_* prefix and success=False — clearly communicates unavailability without silent false success"
  - "_dt_props() helper uses json.dumps with default=str — consistent serialization for all promoted tool event tracking"
  - "degraded_tools.py stripped to empty by 70-01 (ran in parallel) — 70-02 removed all function bodies in anticipation"
  - "classify_tool() returns 'direct' for all promoted tools — execution_contracts trust classification now clean"
metrics:
  duration: "~21min"
  completed_date: "2026-04-13"
  tasks: 2
  files_modified: 4
  files_created: 1
---

# Phase 70 Plan 02: Degraded Tool Cleanup (Promotion + Honest Stubs) Summary

Promoted 16 functional-placeholder tools from `degraded_tools.py` into `registry.py` as honest `promoted_*` functions returning `success=True`, replaced `book_travel` with a `not_available_*` stub returning `success=False`, and removed all active degraded imports — leaving zero tools in `TOOL_REGISTRY` resolving to the `degraded_tools` module.

## What Was Built

### Task 1: Promoted tool functions + honest error stubs

Added 16 `promoted_*` async functions to `registry.py`, grouped by their underlying delegate:

- **save_content-backed (4):** `promoted_create_folder`, `promoted_record_notes`, `promoted_upload_document`, `promoted_upload_file`
- **create_initiative-backed (1):** `promoted_create_project`
- **create_audit-backed (1):** `promoted_run_audit`
- **track_event-backed (1):** `promoted_update_subscription`
- **create_task-backed (9):** `promoted_create_task_list`, `promoted_create_checklist`, `promoted_run_checklist`, `promoted_process_expense`, `promoted_log_shipment`, `promoted_verify_po`, `promoted_create_alert`, `promoted_run_test`, `promoted_test_scenario`

Added `not_available_book_travel` as an honest error stub — travel booking requires an external API not yet configured.

All promoted functions:
- Return `success=True` (never `"degraded_completed"`)
- Include `tool` field for identity
- Track an event via `track_event()` for observability
- Live in `app.agents.tools.registry` module (not `degraded_tools`)

Removed all active `degraded_*` imports from `registry.py`. Updated every `TOOL_REGISTRY` entry to use promoted versions.

`degraded_tools.py` was already stripped to empty by Phase 70-01 (which ran in parallel), so the file is now fully retired.

### Task 2: Tests updated and cleanup verified

- **Rewrote `test_degraded_tools.py`:** Tests now import `promoted_*` functions from `registry` and assert `success=True` (not `"degraded_completed"`). 19 tests covering all 16 promoted tools + `not_available_book_travel`.
- **Created `test_degraded_tool_cleanup.py`:** 57 tests verifying:
  - No TOOL_REGISTRY entry resolves to `degraded_tools` module (70-02 scope)
  - `classify_tool()` returns `"direct"` for all promoted tools
  - `book_travel` returns `success=False` with limitation message
  - All 27 previously-degraded tool names still accessible in registry

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan 70-01 ran in parallel and already replaced analyze_sentiment/ocr_document**
- **Found during:** Task 2 (test run failure after ruff format)
- **Issue:** My code left `degraded_analyze_sentiment` and `degraded_ocr_document` import stubs for 70-01 to handle, but 70-01 had already shipped — registry.py now imports `real_analyze_sentiment` and `real_ocr_document`
- **Fix:** Removed the two degraded placeholder imports entirely; updated cleanup tests to correctly exempt 70-01 scope tools (`analyze_sentiment`, `ocr_document`) using `phase_70_01_scope` set
- **Files modified:** `app/agents/tools/registry.py`, `tests/unit/test_degraded_tool_cleanup.py`
- **Commit:** c184f77e (Task 1 commit already handled this)

**2. [Rule 1 - Bug] import json as _json placed in middle of file caused E402 lint error**
- **Found during:** Task 1 (ruff check)
- **Fix:** Moved `import json` to the standard library import block at the top of registry.py
- **Files modified:** `app/agents/tools/registry.py`

**3. [Rule 1 - Bug] RUF013 implicit Optional in test fixture**
- **Found during:** Task 2 (ruff check)
- **Fix:** Changed `properties: str = None` to `properties: str | None = None`
- **Files modified:** `tests/unit/test_degraded_tools.py`

## Self-Check: PASSED

All files exist on disk and all commits verified in git history.

| Check | Result |
|-------|--------|
| `app/agents/tools/registry.py` | FOUND |
| `app/agents/tools/degraded_tools.py` | FOUND |
| `tests/unit/test_degraded_tool_cleanup.py` | FOUND |
| `tests/unit/test_degraded_tools.py` | FOUND |
| commit c184f77e (Task 1) | FOUND |
| commit e00a3a32 (Task 2) | FOUND |
| Zero degraded tools in registry (70-02 scope) | PASSED |
| 75 tests pass | PASSED |

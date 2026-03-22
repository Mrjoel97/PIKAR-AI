---
phase: 19-screen-generation
plan: "01"
subsystem: app-builder
tags: [screen-generation, stitch-mcp, sse, supabase, tdd]
dependency_graph:
  requires:
    - 18-design-brief-research (design_system, stitch_project_id pattern)
    - 16-foundation (app_builder schema, stitch_assets, stitch_mcp)
  provides:
    - screen_generation_service (generate_screen_variants, generate_device_variant)
    - 4 new app_builder router endpoints
    - stitch_project_id persisted per app_project
  affects:
    - app/routers/app_builder.py (4 new endpoints added)
    - supabase/migrations (stitch_project_id on app_projects, page_slug on app_screens)
tech_stack:
  added: []
  patterns:
    - async generator SSE streaming (matches existing research endpoint pattern)
    - TDD red/green for all new code
    - sequential await for Stitch calls (Lock deadlock prevention)
    - persist-before-yield pattern (permanent Supabase Storage URLs in events)
key_files:
  created:
    - supabase/migrations/20260322200000_app_projects_stitch_id.sql
    - app/services/screen_generation_service.py
    - tests/unit/app_builder/test_screen_generation_service.py
  modified:
    - app/routers/app_builder.py
    - tests/unit/app_builder/test_app_builder_router.py
decisions:
  - "generate_screen_variants uses sequential await per Stitch call -- asyncio.gather would deadlock the Lock inside StitchMCPService"
  - "persist_screen_assets called before yielding variant_generated event -- callers receive permanent Supabase Storage URLs, not short-lived Stitch signed URLs"
  - "stitch_project_id stored on app_projects (not app_screens) -- one Stitch project reused across all screens in an app project"
  - "First variant is_selected=True by default -- frontend can render immediately without explicit selection step"
  - "page_slug added to app_screens via migration -- needed for build_plan to screen mapping in Phase 19 Plan 02"
  - "_build_generation_prompt injects design system colors and typography into prompt string for Stitch"
metrics:
  duration: "10 min"
  completed_date: "2026-03-22"
  tasks_completed: 2
  files_changed: 5
---

# Phase 19 Plan 01: Screen Generation Backend Summary

Sequential Stitch MCP variant generation with SSE streaming, permanent asset persistence, and 4 new app_builder endpoints for screen generation, device variants, listing, and selection.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | DB migration + screen generation service | f282c0a | migration, screen_generation_service.py, test_screen_generation_service.py |
| 2 | Router endpoints for generation, listing, selection | 52b8019 | app_builder.py, test_app_builder_router.py |

## What Was Built

### Migration (20260322200000_app_projects_stitch_id.sql)
- `ALTER TABLE app_projects ADD COLUMN IF NOT EXISTS stitch_project_id TEXT` — one Stitch project per app project, reused across screens
- `ALTER TABLE app_screens ADD COLUMN IF NOT EXISTS page_slug TEXT` — build_plan page slug stored on each screen row for plan-to-screen mapping

### screen_generation_service.py
- `generate_screen_variants(project_id, user_id, screen_name, page_slug, prompt, stitch_project_id, num_variants=3)` — async generator producing `generating` + N x `variant_generated` + `ready` events. Each variant calls Stitch sequentially (no `asyncio.gather`), persists assets via `persist_screen_assets`, inserts a `screen_variants` row with `is_selected=(i==0)`.
- `generate_device_variant(screen_id, user_id, prompt, stitch_project_id, device_type, project_id)` — single Stitch call for MOBILE/TABLET, same persist-before-yield pattern, yields `generating` + `device_generated` + `ready`.

### app_builder.py (4 new endpoints)
- `POST /app-builder/projects/{id}/generate-screen` — fetches project design system, builds prompt via `_build_generation_prompt`, creates Stitch project on first call, streams `generate_screen_variants` as SSE
- `POST /app-builder/projects/{id}/screens/{sid}/generate-device-variant` — verifies screen ownership, streams `generate_device_variant` as SSE
- `GET /app-builder/projects/{id}/screens/{sid}/variants` — returns `screen_variants` ordered by `variant_index`
- `PATCH /app-builder/projects/{id}/screens/{sid}/variants/{vid}/select` — deselect-all then select-one atomic update pattern

## Test Results

```
tests/unit/app_builder/test_screen_generation_service.py — 6/6 passed
tests/unit/app_builder/test_app_builder_router.py — 17/17 passed (6 new + 11 existing)
Total app_builder suite (excluding integration smoke): 39/39 passed
```

## Deviations from Plan

None — plan executed exactly as written.

## Key Decisions Made

1. **Sequential Stitch calls** — `generate_screen_variants` uses sequential `await` per iteration, never `asyncio.gather`. The `StitchMCPService` serialises all calls through an `asyncio.Lock`; gathering would cause a deadlock.

2. **Persist before yield** — `persist_screen_assets` is awaited before each `variant_generated` event is yielded. This ensures callers (SSE clients) receive permanent Supabase Storage URLs, not short-lived Stitch signed URLs that expire in minutes.

3. **`stitch_project_id` on `app_projects`** — Moved from `app_screens` level to project level so a single Stitch project is reused across all screens. The `generate-screen` endpoint creates it on first call if absent and writes it back to the DB.

4. **`page_slug` added to `app_screens`** — Required for Phase 19 Plan 02 (building page) to map build_plan page entries to generated screen rows.

5. **First variant selected by default** — `is_selected=(i==0)` on insert. Frontend can render the first variant immediately without requiring an explicit selection step.

## Self-Check

- [x] Migration file: `supabase/migrations/20260322200000_app_projects_stitch_id.sql` — FOUND
- [x] Service file: `app/services/screen_generation_service.py` — FOUND (130 lines, exports `generate_screen_variants` and `generate_device_variant`)
- [x] Router updated: `app/routers/app_builder.py` — contains `generate-screen`
- [x] Service tests: `tests/unit/app_builder/test_screen_generation_service.py` — 6 tests, all pass
- [x] Router tests: `tests/unit/app_builder/test_app_builder_router.py` — contains `test_generate_screen`
- [x] Commits: 19b718a (RED tests), f282c0a (service + migration), 52b8019 (router)
- [x] Lint: `ruff check app/services/screen_generation_service.py app/routers/app_builder.py` — All checks passed

## Self-Check: PASSED

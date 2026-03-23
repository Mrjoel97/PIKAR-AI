---
phase: 21-multi-page-builder
plan: 01
subsystem: api
tags: [stitch-mcp, multi-page, html-parser, supabase, async-generator, tdd]

# Dependency graph
requires:
  - phase: 20-iteration-loop
    provides: iteration_service._get_locked_design_markdown, edit_screen_variant pattern
  - phase: 19-screen-generation
    provides: persist_screen_assets, get_stitch_service, sequential Stitch call pattern
  - phase: 16-foundation
    provides: StitchMCPService singleton, app_screens schema, screen_variants schema

provides:
  - build_all_pages async generator — baton-loop page generation with SSE events
  - _build_nav_baton helper — growing nav context string per page
  - _build_page_prompt helper — design system + page spec + nav baton assembly
  - NavLinkRewriter (HTMLParser) — rewrites /slug hrefs to absolute Supabase URLs
  - inject_navigation_links — download → rewrite → re-upload HTML post-processor
  - DB migration: page_slug TEXT column on app_screens (applied to remote Supabase)

affects:
  - 21-02 (multi-page router endpoints will import build_all_pages)
  - 21-03 (verifying page needs screen data produced by this service)
  - future phases using multi-page generation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Stitch baton loop: sequential await per page, never gather (Lock deadlock constraint)"
    - "Nav context accumulation: each page prompt includes slugs of prior pages"
    - "Design system injection: DESIGN SYSTEM:\\n{markdown} prepended to every page prompt"
    - "HTMLParser subclass for href rewriting with full HTML fidelity (decl/comment/entityref/charref handlers)"
    - "Non-fatal post-processing: inject_navigation_links logs warning and continues on error"
    - "B023 fix pattern: bind loop variables via lambda default args (p=_path, b=_html_bytes)"

key-files:
  created:
    - app/services/multi_page_service.py
    - tests/unit/app_builder/test_multi_page_service.py
    - supabase/migrations/20260323200000_add_page_slug.sql
  modified: []

key-decisions:
  - "21-01: Migration timestamp 20260323200000 used — 20260323100000 already taken by admin_knowledge_base"
  - "21-01: NavLinkRewriter handles handle_decl/comment/entityref/charref for full HTML fidelity — not just starttag/endtag/data"
  - "21-01: inject_navigation_links uses lambda default-arg binding (p=_path, b=_html_bytes) to satisfy ruff B023 (loop variable capture)"
  - "21-01: test_nav_link_rewriter asserts 'href=/about' not in output (not '/about') — URL contains /about as substring"

patterns-established:
  - "Pattern: baton loop yields page_started before Stitch call, page_complete after persist_screen_assets"
  - "Pattern: screens_built list grows as each page completes, passed to _build_nav_baton before next page"

requirements-completed: [PAGE-01, PAGE-02, PAGE-03]

# Metrics
duration: 6min
completed: 2026-03-23
---

# Phase 21 Plan 01: Multi-Page Builder Service Summary

**Sequential baton-loop generator (build_all_pages) with NavLinkRewriter post-processor: generates N-page sites via Stitch MCP with growing nav-context per page and /slug href rewriting to permanent Supabase Storage URLs**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-23T03:35:41Z
- **Completed:** 2026-03-23T03:41:07Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments

- `build_all_pages` async generator iterates sitemap entries sequentially, yielding `page_started` + `page_complete` per page and `build_complete` at end with full screens list
- Nav baton grows with each page: page 2 prompt includes page 1 slug/title, page 3 includes pages 1+2, ensuring consistent navigation structure across all generated pages
- `NavLinkRewriter` (stdlib HTMLParser subclass) rewrites `/slug` and `slug` style hrefs to absolute Supabase Storage public URLs with full HTML fidelity (decl, comment, entity/char refs preserved)
- `inject_navigation_links` downloads HTML from permanent URLs, runs NavLinkRewriter, re-uploads with upsert=true — non-fatal (warns and continues on error)
- DB migration applied to remote Supabase: `page_slug TEXT` column on `app_screens`
- 7 unit tests all passing, lint clean

## Task Commits

1. **Task 1: DB migration + multi_page_service.py with baton loop and nav injection** - `367b08b` (feat)

## Files Created/Modified

- `app/services/multi_page_service.py` — `build_all_pages`, `_build_nav_baton`, `_build_page_prompt`, `NavLinkRewriter`, `inject_navigation_links`
- `tests/unit/app_builder/test_multi_page_service.py` — 7 unit tests covering baton loop events, nav baton growth, design system injection, href rewriting, nav upload, and per-page design markdown
- `supabase/migrations/20260323200000_add_page_slug.sql` — `ALTER TABLE app_screens ADD COLUMN IF NOT EXISTS page_slug TEXT`

## Decisions Made

- Migration timestamp `20260323200000` used instead of plan's `20260323100000` — that timestamp was already occupied by the admin_knowledge_base migration from Phase 12.1
- `NavLinkRewriter` implements `handle_decl`, `handle_comment`, `handle_entityref`, `handle_charref` in addition to the core three — required for full HTML fidelity per plan spec
- Lambda default-arg binding `lambda p=_path, b=_html_bytes:` in `inject_navigation_links` to satisfy ruff B023 (loop variable not bound in closure)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed overly broad test assertion in test_nav_link_rewriter**
- **Found during:** Task 1 (GREEN phase — first test run)
- **Issue:** Assertion `"/about" not in output` always fails because the rewritten URL `https://supabase.co/storage/about.html` itself contains `/about` as a substring
- **Fix:** Changed to `'href="/about"' not in output` — checks the original href attribute value was replaced, not the substring
- **Files modified:** tests/unit/app_builder/test_multi_page_service.py
- **Verification:** All 7 tests pass
- **Committed in:** `367b08b` (part of task commit)

**2. [Rule 1 - Bug] Fixed ruff B023 loop variable capture in inject_navigation_links lambda**
- **Found during:** Task 1 (lint check after GREEN phase)
- **Issue:** Lambda inside `for screen in screens` loop captures `storage_path` and `new_html` by reference — ruff B023 flags this as a bug (all iterations would see the last value)
- **Fix:** Bound loop variables via lambda default args: `lambda p=_path, b=_html_bytes:`
- **Files modified:** app/services/multi_page_service.py
- **Verification:** `ruff check` passes with no errors
- **Committed in:** `367b08b` (part of task commit)

---

**Total deviations:** 2 auto-fixed (2x Rule 1 — bug)
**Impact on plan:** Both fixes required for correctness. Test assertion fix needed for accurate test coverage. B023 fix prevents silent late-binding bug in nav injection. No scope creep.

## Issues Encountered

- Plan specified migration filename `20260323100000_add_page_slug.sql` but that timestamp was already taken by `20260323100000_admin_knowledge_base.sql` (Phase 12.1). Used `20260323200000_add_page_slug.sql` instead. Migration applied successfully to remote Supabase via Management API.

## Next Phase Readiness

- `build_all_pages` and `inject_navigation_links` are fully tested and ready for router integration (Plan 21-02)
- `NavLinkRewriter` handles all standard HTML — no additional work needed before router integration
- DB column `page_slug` is live on remote Supabase — Plan 21-02 inserts will succeed immediately

---
*Phase: 21-multi-page-builder*
*Completed: 2026-03-23*

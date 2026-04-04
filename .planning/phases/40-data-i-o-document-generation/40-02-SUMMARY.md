---
phase: 40-data-i-o-document-generation
plan: 02
subsystem: api
tags: [weasyprint, jinja2, python-pptx, matplotlib, pdf, pptx, document-generation, branding]

# Dependency graph
requires:
  - phase: 39-integration-infrastructure
    provides: Supabase Storage upload patterns, brand_profile tool
provides:
  - DocumentService with generate_pdf and generate_pptx methods
  - 4 branded Jinja2 PDF templates (financial_report, project_proposal, meeting_summary, competitive_analysis)
  - Chart rendering via matplotlib embedded as base64 in PDFs
  - PPTX pitch deck generation with branded slides
  - Document upload to Supabase Storage with media_assets tracking
  - Widget dict return pattern for chat UI document display
affects: [40-03-document-generation-agent-tools, frontend-document-viewer]

# Tech tracking
tech-stack:
  added: [weasyprint, matplotlib, polars, jinja2-templates]
  patterns: [lazy-imports-for-system-deps, thread-pool-pdf-rendering, brand-injection-templates]

key-files:
  created:
    - app/services/document_service.py
    - app/templates/pdf/base.html
    - app/templates/pdf/css/report.css
    - app/templates/pdf/financial_report.html
    - app/templates/pdf/project_proposal.html
    - app/templates/pdf/meeting_summary.html
    - app/templates/pdf/competitive_analysis.html
    - tests/unit/services/test_document_service.py
  modified:
    - pyproject.toml
    - Dockerfile

key-decisions:
  - "Lazy imports for weasyprint and matplotlib — both require system C libraries unavailable on dev Windows; lazy loading prevents import-time failures while tests mock the loaders"
  - "PDF size limit of 5MB (~50 pages) enforced via byte-size heuristic rather than weasyprint page count metadata for simplicity"
  - "Brand fallback defaults to Pikar blue (#4F46E5) when user has no brand profile, ensuring documents always render cleanly"

patterns-established:
  - "Lazy import pattern: _get_weasyprint_html() and _get_matplotlib() for system-dep libraries that cannot be imported at module load time on all platforms"
  - "Document widget pattern: type=document with data.documentUrl, data.fileType, data.sizeBytes, data.templateName for chat UI rendering"
  - "Brand injection via Jinja2 template context: primary_color, secondary_color, accent_color, brand_name, logo_url extracted from brand profile"

requirements-completed: [DOC-01, DOC-02, DOC-03, DOC-04]

# Metrics
duration: 21min
completed: 2026-04-04
---

# Phase 40 Plan 02: Document Generation Summary

**PDF report generation via weasyprint/Jinja2 with 4 branded templates, PPTX pitch decks via python-pptx, and matplotlib chart embedding**

## Performance

- **Duration:** 21 min
- **Started:** 2026-04-04T14:12:00Z
- **Completed:** 2026-04-04T14:33:00Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- DocumentService with generate_pdf (4 templates), generate_pptx, and render_chart methods using thread-pool execution
- Professional Jinja2 HTML templates with brand color injection, logo placement, metric cards, SWOT grids, and zebra-striped tables
- Dockerfile updated with weasyprint system dependencies (libpango, libcairo, libharfbuzz, etc.)
- polars, weasyprint, and matplotlib added to pyproject.toml dependencies
- 14 unit tests covering all templates, branding fallback, PPTX generation, chart rendering, and upload tracking

## Task Commits

Each task was committed atomically:

1. **Task 1: DocumentService + Jinja2 templates + unit tests** - `a98f1da` (feat) -- pre-committed by 40-01 executor; verified 14/14 tests pass
2. **Task 2: Dockerfile + pyproject.toml dependency updates** - `d8145c8` (chore)

_Note: Task 1 files were committed by the 40-01 executor in its TDD RED phase (commit a98f1da). This plan verified correctness (14 tests passing, lint clean) and proceeded to Task 2._

## Files Created/Modified
- `app/services/document_service.py` - DocumentService class with PDF/PPTX generation, chart rendering, Supabase upload
- `app/templates/pdf/base.html` - Shared Jinja2 base template with brand color CSS variables and logo slot
- `app/templates/pdf/css/report.css` - Professional report styles (metric cards, SWOT grid, tables, typography)
- `app/templates/pdf/financial_report.html` - Financial report with metrics, revenue breakdown, chart section
- `app/templates/pdf/project_proposal.html` - Project proposal with objectives, milestones, budget, risks
- `app/templates/pdf/meeting_summary.html` - Meeting summary with attendees, decisions, action items
- `app/templates/pdf/competitive_analysis.html` - Competitive analysis with comparison table and SWOT grid
- `tests/unit/services/test_document_service.py` - 14 unit tests covering all generation paths
- `pyproject.toml` - Added polars>=1.0, weasyprint>=62.0, matplotlib>=3.8
- `Dockerfile` - Added libpango, libpangoft2, libharfbuzz-subset0, libcairo2, libgdk-pixbuf2.0-0, libffi-dev

## Decisions Made
- Used lazy imports for weasyprint and matplotlib since both require system C libraries not available on Windows dev machines; tests mock the lazy loaders
- PDF size limit enforced at 5MB byte threshold rather than page count for simplicity
- Brand fallback uses Pikar defaults (#4F46E5 primary) when no brand profile exists
- PPTX uses blank slide layout (index 6) with programmatic textbox placement for full control over branding

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Lazy imports for weasyprint and matplotlib**
- **Found during:** Task 1 (DocumentService implementation)
- **Issue:** weasyprint and matplotlib are not installable on Windows dev environment (require system C libraries). Top-level imports prevented module loading.
- **Fix:** Created `_get_weasyprint_html()` and `_get_matplotlib()` lazy import functions. Tests mock these functions instead of patching top-level module attributes.
- **Files modified:** app/services/document_service.py, tests/unit/services/test_document_service.py
- **Verification:** Module imports cleanly, all 14 tests pass
- **Committed in:** a98f1da (pre-committed by 40-01)

**2. [Rule 3 - Blocking] uv lock unavailable in shim environment**
- **Found during:** Task 2 (dependency updates)
- **Issue:** Local uv.cmd is a shim that only supports `uv run` -- `uv lock` is not available
- **Fix:** Deferred lock file regeneration to CI/deployment where full uv binary is available. pyproject.toml changes are correct and will resolve on next `uv lock` run.
- **Files modified:** pyproject.toml (changes committed without lock update)
- **Verification:** pyproject.toml syntax validated by ruff; lock will regenerate in CI

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both auto-fixes necessary for local development compatibility. No scope creep.

## Issues Encountered
- Task 1 files were already committed by the 40-01 executor (commit a98f1da included full document_service.py, all templates, and tests). Verified correctness and moved to Task 2 without creating a duplicate commit.

## User Setup Required
None - no external service configuration required. Weasyprint system deps are handled by Dockerfile.

## Next Phase Readiness
- DocumentService is ready for Plan 03 to wire agent tools that call generate_pdf/generate_pptx
- Frontend document viewer widget will need to handle the document widget type returned by the service
- uv.lock needs regeneration in an environment with full uv binary before deployment

---
*Phase: 40-data-i-o-document-generation*
*Completed: 2026-04-04*

## Self-Check: PASSED

All 8 created files verified present. Both commit hashes (a98f1da, d8145c8) confirmed in git log.

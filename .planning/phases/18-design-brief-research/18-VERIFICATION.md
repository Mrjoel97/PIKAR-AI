---
phase: 18-design-brief-research
verified: 2026-03-22T16:15:00Z
status: passed
score: 8/8 must-haves verified
gaps: []
human_verification:
  - test: "Navigate to /app-builder/{projectId}/research in a running dev stack"
    expected: "SSE progress steps animate sequentially (Researching → Synthesizing → Saving), DesignBriefCard and SitemapCard appear after 'ready' event, Approve button is disabled during research, BuildPlanView renders after approval"
    why_human: "SSE streaming animation, real Tavily + Gemini calls, and live Supabase writes require running servers with real credentials — cannot be verified statically"
  - test: "Edit a color hex value in DesignBriefCard before clicking Approve"
    expected: "Swatch background color updates in real time as the hex input changes"
    why_human: "Reactive color swatch update is a visual/DOM behavior not covered by existing vitest tests"
---

# Phase 18: Design Brief Research Verification Report

**Phase Goal:** Before any screens are generated, the system researches the design space and produces a user-approved design brief — users see a sitemap, a design system document, and a build plan before a single pixel is generated

**Verified:** 2026-03-22T16:15:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `run_design_research()` calls TavilySearchTool with brief-derived queries and returns structured research results | VERIFIED | `design_brief_service.py` lines 122-134: builds 2 queries from `creative_brief["what"]` and `creative_brief["vibe"]`, runs them via `asyncio.gather` with `TavilySearchTool`. Test `test_research_calls_tavily` asserts `search.call_count >= 2`. 15/15 backend tests pass. |
| 2 | Gemini Flash synthesizes research into a DESIGN.md markdown document and structured color/typography/spacing tokens | VERIFIED | `design_brief_service.py` lines 144-157: Gemini called with `DESIGN_SYSTEM_PROMPT` containing flattened research. `_parse_design_response` extracts `raw_markdown`, `colors`, `typography`, `spacing`, `sitemap`. `test_parse_design_response` asserts all 5 keys present and correct types. |
| 3 | POST /app-builder/projects/{id}/research streams SSE progress events (searching, synthesizing, saving, ready) | VERIFIED | `app_builder.py` lines 117-155: `StreamingResponse(event_generator(), media_type="text/event-stream", headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})`. `test_research_sse_steps` asserts status 200, content-type `text/event-stream`, body contains both `searching` and `ready` data lines. |
| 4 | POST /app-builder/projects/{id}/approve-brief locks design_systems row, generates build plan, advances stage to building | VERIFIED | `app_builder.py` lines 158-202: updates `design_systems` with `locked=True`, calls `_generate_build_plan`, updates `app_projects` with `stage="building"` and `build_plan`, updates `build_sessions`. `test_approve_brief_locks_and_advances` and `test_approve_brief_saves_build_plan` both pass. |
| 5 | `_generate_build_plan()` returns phase array with screens and dependency structure | VERIFIED | `design_brief_service.py` lines 298-357: Gemini called with `response_mime_type="application/json"`, validates each item has `phase`, `label`, `screens`, `dependencies`, falls back to deterministic plan if Gemini unavailable. `test_build_plan_structure` asserts 2 phases, each with required keys and `screens` list containing `name`/`page`/`device`. |
| 6 | User sees an editable DesignBriefCard with color palette, typography, and spacing they can modify | VERIFIED | `DesignBriefCard.tsx` 134 lines: color swatches with hex inputs (`data-testid="color-swatch"`), typography heading/body inputs, spacing base_unit input, raw_markdown textarea. All call `onChange` on edit. 3/3 vitest tests pass. |
| 7 | User must click an explicit Approve button to lock the design system — approval is never automatic | VERIFIED | `research/page.tsx` lines 145-186: Approve button rendered with `disabled` attribute while `isResearching === true`. Button click triggers `handleApprove()` which calls `approveBrief()`. `test_approve_button_is_disabled_during_research` passes. SSE `ready` event does not auto-call approve. |
| 8 | GsdProgressBar shows dynamic stage matching the project's actual stage | VERIFIED | `[projectId]/layout.tsx` lines 4-35: server component, `fetchProjectStage` fetches `/app-builder/projects/{projectId}` with `cache: 'no-store'`, passes `project.stage` to `<GsdProgressBar currentStage={stage} />`. Falls back to `'research'` on error. |

**Score:** 8/8 truths verified

---

## Required Artifacts

| Artifact | Provided | Status | Details |
|----------|----------|--------|---------|
| `supabase/migrations/20260322000000_design_brief_unique.sql` | UNIQUE constraint on design_systems(project_id) | VERIFIED | 9 lines, contains `ALTER TABLE design_systems ADD CONSTRAINT design_systems_project_id_unique UNIQUE (project_id)`. Note: filename differs from plan spec (`20260321700000`) — SUMMARY documents the auto-resolution (timestamp conflict with analytics migration). Functionality is identical. |
| `app/services/design_brief_service.py` | Design research orchestration service | VERIFIED | 392 lines (well above 80-line minimum). Exports `run_design_research`, `_parse_design_response`, `_generate_build_plan`. Also exports `_persist_design_draft` and `_flatten_search_results`. |
| `app/routers/app_builder.py` | Research SSE and approve-brief endpoints | VERIFIED | 203 lines. Contains `approve-brief` at line 158. Both new endpoints present alongside existing 3 Phase-16/17 endpoints. |
| `tests/unit/app_builder/test_design_brief_service.py` | Unit tests for service functions | VERIFIED | 255 lines (above 40-line minimum). 4 tests: `test_research_calls_tavily`, `test_synthesis_uses_research`, `test_parse_design_response`, `test_build_plan_structure`. All pass. |
| `frontend/src/types/app-builder.ts` | DesignBrief, SitemapPage, BuildPlanPhase, ResearchEvent interfaces | VERIFIED | Contains all 4 interfaces. `AppProject` extended with `design_system?`, `sitemap?`, `build_plan?` optional fields. |
| `frontend/src/services/app-builder.ts` | startResearch (SSE), approveBrief service functions | VERIFIED | `startResearch` at line 80 uses fetch ReadableStream; `approveBrief` at line 112 POSTs to `/approve-brief`. |
| `frontend/src/app/app-builder/[projectId]/layout.tsx` | Dynamic GsdProgressBar reading project stage | VERIFIED | Server component, awaits `params` Promise, fetches stage with `cache: 'no-store'`, renders `<GsdProgressBar currentStage={stage} />`. |
| `frontend/src/app/app-builder/[projectId]/research/page.tsx` | Research page with SSE progress, editable cards, approve button | VERIFIED | 189 lines (above 60-line minimum). Full SSE progress UI with framer-motion, editable DesignBriefCard/SitemapCard grid, disabled approve button during research, BuildPlanView post-approval. |
| `frontend/src/components/app-builder/DesignBriefCard.tsx` | Editable design system preview card | VERIFIED | 134 lines (above 40-line minimum). `data-testid="design-brief-card"`, color swatches, typography inputs, spacing input, raw_markdown textarea. |
| `frontend/src/components/app-builder/SitemapCard.tsx` | Editable sitemap preview card | VERIFIED | 102 lines (above 30-line minimum). `data-testid="sitemap-card"`, page titles, sections as comma-separated, device target checkboxes, Add Page button. |
| `frontend/src/components/app-builder/BuildPlanView.tsx` | Build plan display with phase/dependency visualization | VERIFIED | 59 lines (above 30-line minimum). `data-testid="build-plan-view"`, phase number badges, screen name chips, dependency labels. |
| `frontend/src/__tests__/components/DesignBriefCard.test.tsx` | Unit tests for editable design brief card | VERIFIED | 43 lines (above 20-line minimum). 3 tests: color swatches, typography fields, onChange call. All pass. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `app/routers/app_builder.py` | `app/services/design_brief_service.py` | `from app.services.design_brief_service import` | WIRED | Line 13: `from app.services.design_brief_service import _generate_build_plan, run_design_research`. Both imported and used in endpoints. |
| `app/services/design_brief_service.py` | `app/mcp/tools/web_search.py` | `TavilySearchTool` | WIRED | Line 22: `from app.mcp.tools.web_search import TavilySearchTool`. Line 127: `search_tool = TavilySearchTool()` then used in `asyncio.gather`. |
| `app/services/design_brief_service.py` | `google.genai` | `client.aio.models.generate_content` | WIRED | Lines 149 and 331: `await client.aio.models.generate_content(model="gemini-2.5-flash", ...)` called in both `run_design_research` and `_generate_build_plan`. |
| `frontend/src/app/app-builder/[projectId]/research/page.tsx` | `frontend/src/services/app-builder.ts` | `startResearch` and `approveBrief` | WIRED | Line 7: both imported. Lines 46, 77: both called with real projectId and handler/payload arguments. |
| `frontend/src/app/app-builder/[projectId]/layout.tsx` | `frontend/src/services/app-builder.ts` | `getProject` | PARTIAL — NOTE | Plan spec said `getProject` via service; actual implementation uses a local `fetchProjectStage` function calling the API directly with `fetch`. The GsdProgressBar receives the dynamic stage correctly — goal achieved. Not a functional gap. |
| `frontend/src/app/app-builder/[projectId]/research/page.tsx` | `frontend/src/components/app-builder/DesignBriefCard.tsx` | `DesignBriefCard` | WIRED | Line 8: imported. Line 140: `<DesignBriefCard brief={brief} onChange={setBrief} />` rendered conditionally when `researchStep === 'ready' && brief`. |

---

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| FLOW-02 | 18-01, 18-02, 18-03 | System performs design research — analyzes competitors/inspiration, suggests palettes, layouts, and typography patterns | SATISFIED | Tavily parallel search (competitor + inspiration queries), Gemini synthesis producing color palettes, typography, and spacing tokens. DesignBriefCard displays results to user. |
| FLOW-03 | 18-01, 18-02, 18-03 | System generates a design brief with sitemap, DESIGN.md (colors, fonts, spacing), features per page, and device targets — user approves before building | SATISFIED | `DESIGN_SYSTEM_PROMPT` generates `DESIGN_SYSTEM_MARKDOWN` (the DESIGN.md), `PALETTE`, `TYPOGRAPHY`, `SPACING`, `SITEMAP_JSON` with device_targets. POST `/approve-brief` is the explicit user gate — approval is never automatic. SitemapCard shows features per page. |
| FLOW-04 | 18-01, 18-02, 18-03 | System creates a build plan breaking the app into phases per page/screen group with dependencies | SATISFIED | `_generate_build_plan()` produces phase array with `phase`, `label`, `screens` (per page/device), `dependencies`. BuildPlanView renders it post-approval. Fallback plan ensures reliability. |

No orphaned requirements — all three FLOW-02/03/04 requirements are claimed in all three plan frontmatter sections and verified implemented.

---

## Anti-Patterns Found

None. Scan of all Phase 18 implementation files found zero occurrences of:
- TODO/FIXME/HACK/PLACEHOLDER comments
- Empty implementations (`return null`, `return {}`, `return []` without logic)
- Console.log-only handlers
- Stub patterns in components or API routes

---

## Human Verification Required

### 1. End-to-end SSE Research Flow

**Test:** Start `make local-backend` (port 8000) and `cd frontend && npm run dev` (port 3000). Navigate to `/app-builder/{projectId}/research` for a project that has a `creative_brief` set.

**Expected:** The page shows animated step transitions: Search icon + "Researching" → Sparkles + "Synthesizing" → Save + "Saving". After the SSE stream emits `ready`, DesignBriefCard and SitemapCard appear side by side. The Approve button changes from disabled to enabled.

**Why human:** SSE streaming with real Tavily and Gemini API calls, framer-motion animations, and live Supabase upsert require running servers with valid API credentials.

### 2. Approve Flow and Build Plan Display

**Test:** After research completes, click "Approve & Generate Build Plan".

**Expected:** A loading state shows ("Generating Build Plan..."). BuildPlanView appears below the cards, showing numbered phases with screen chips and dependency labels. A "Continue to Building" button appears.

**Why human:** Requires live `_generate_build_plan` Gemini call and real Supabase write of `locked=True` on design_systems row.

---

## Gaps Summary

No gaps found. All 8 observable truths are verified, all artifacts exist and are substantive, all key links are wired. The one noted deviation (layout uses direct `fetch` instead of the service module's `getProject`) achieves the same goal and is not a gap.

The 15 backend tests (pytest) all pass. The 7 frontend tests (vitest) all pass. Migration file exists with correct UNIQUE constraint SQL.

---

_Verified: 2026-03-22T16:15:00Z_
_Verifier: Claude (gsd-verifier)_

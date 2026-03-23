---
phase: 21
slug: multi-page-builder
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest 8.4.2 |
| **Framework (frontend)** | vitest |
| **Backend config** | `pyproject.toml` |
| **Frontend config** | `frontend/vitest.config.*` |
| **Quick run command** | `uv run pytest tests/unit/app_builder/test_multi_page_service.py -x -v` |
| **Full suite command** | `uv run pytest tests/unit/app_builder/ -x -v && cd frontend && npx vitest run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/app_builder/test_multi_page_service.py -x -v`
- **After every plan wave:** Run `uv run pytest tests/unit/app_builder/ -x -v && cd frontend && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 0 | INFRA | migration | `uv run pytest tests/unit/app_builder/test_multi_page_service.py -x` | ❌ W0 | ⬜ pending |
| 21-01-02 | 01 | 1 | PAGE-01 | unit | `uv run pytest tests/unit/app_builder/test_multi_page_service.py::test_baton_loop_yields_correct_events -x` | ❌ W0 | ⬜ pending |
| 21-01-03 | 01 | 1 | PAGE-01 | unit | `uv run pytest tests/unit/app_builder/test_multi_page_service.py::test_nav_baton_accumulates -x` | ❌ W0 | ⬜ pending |
| 21-01-04 | 01 | 1 | PAGE-02 | unit | `uv run pytest tests/unit/app_builder/test_multi_page_service.py::test_nav_link_rewriter -x` | ❌ W0 | ⬜ pending |
| 21-01-05 | 01 | 1 | PAGE-02 | unit | `uv run pytest tests/unit/app_builder/test_multi_page_service.py::test_nav_injection_uploads -x` | ❌ W0 | ⬜ pending |
| 21-01-06 | 01 | 1 | PAGE-03 | unit | `uv run pytest tests/unit/app_builder/test_multi_page_service.py::test_design_system_injected_in_prompt -x` | ❌ W0 | ⬜ pending |
| 21-02-01 | 02 | 1 | PAGE-04 | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_update_sitemap -x` | ❌ W0 | ⬜ pending |
| 21-02-02 | 02 | 1 | FLOW-06 | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_list_project_screens -x` | ❌ W0 | ⬜ pending |
| 21-03-01 | 03 | 2 | FLOW-06 | unit | `cd frontend && npx vitest run src/__tests__/components/VerifyingPage.test.tsx` | ❌ W0 | ⬜ pending |
| 21-03-02 | 03 | 2 | PAGE-04 | unit | `cd frontend && npx vitest run src/__tests__/components/SitemapEditor.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `supabase/migrations/YYYYMMDD_add_page_slug.sql` — ALTER TABLE app_screens ADD COLUMN IF NOT EXISTS page_slug TEXT
- [ ] `tests/unit/app_builder/test_multi_page_service.py` — stubs for PAGE-01, PAGE-02, PAGE-03
- [ ] `frontend/src/__tests__/components/VerifyingPage.test.tsx` — stubs for FLOW-06
- [ ] `frontend/src/__tests__/components/SitemapEditor.test.tsx` — stubs for PAGE-04

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Multi-page Stitch generation via baton loop | PAGE-01 | Requires Stitch MCP + API key | Start backend, trigger multi-page build, verify sequential SSE events |
| Navigation links work between pages in preview | PAGE-02 | Browser rendering in iframe | Click nav links in preview, confirm correct page loads |
| Visual consistency across pages | PAGE-03 | Visual comparison | Compare header/footer/colors across generated pages |
| Verification stage multi-page preview | FLOW-06 | Browser tab switching + iframe | Navigate between pages via tabs in verifying page |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

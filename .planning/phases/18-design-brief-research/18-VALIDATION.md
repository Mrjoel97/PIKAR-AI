---
phase: 18
slug: design-brief-research
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend), vitest 4.0.18 (frontend) |
| **Config file** | `pytest.ini` (backend), `frontend/scripts/run-vitest.mjs` (frontend) |
| **Quick run command** | `uv run pytest tests/unit/app_builder/ -x` |
| **Full suite command** | `uv run pytest tests/unit/ -x && cd frontend && node scripts/run-vitest.mjs` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/app_builder/ -x`
- **After every plan wave:** Run `uv run pytest tests/unit/ -x && cd frontend && node scripts/run-vitest.mjs`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 1 | FLOW-02 | unit | `uv run pytest tests/unit/app_builder/test_design_brief_service.py::test_research_calls_tavily -x` | Wave 0 | pending |
| 18-01-02 | 01 | 1 | FLOW-02 | unit | `uv run pytest tests/unit/app_builder/test_design_brief_service.py::test_synthesis_uses_research -x` | Wave 0 | pending |
| 18-01-03 | 01 | 1 | FLOW-02 | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_research_sse_steps -x` | Wave 0 | pending |
| 18-02-01 | 02 | 1 | FLOW-03 | unit | `uv run pytest tests/unit/app_builder/test_design_brief_service.py::test_parse_design_response -x` | Wave 0 | pending |
| 18-02-02 | 02 | 1 | FLOW-03 | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_approve_brief_locks_and_advances -x` | Wave 0 | pending |
| 18-02-03 | 02 | 2 | FLOW-03 | unit | `cd frontend && node scripts/run-vitest.mjs src/__tests__/components/DesignBriefCard.test.tsx` | Wave 0 | pending |
| 18-02-04 | 02 | 2 | FLOW-03 | unit | `cd frontend && node scripts/run-vitest.mjs src/__tests__/components/ResearchPage.test.tsx` | Wave 0 | pending |
| 18-03-01 | 03 | 1 | FLOW-04 | unit | `uv run pytest tests/unit/app_builder/test_design_brief_service.py::test_build_plan_structure -x` | Wave 0 | pending |
| 18-03-02 | 03 | 1 | FLOW-04 | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_approve_brief_saves_build_plan -x` | Wave 0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/app_builder/test_design_brief_service.py` — stubs for FLOW-02, FLOW-03, FLOW-04 (new file; mock TavilySearchTool and genai.Client)
- [ ] `frontend/src/__tests__/components/DesignBriefCard.test.tsx` — covers FLOW-03 (editable card rendering)
- [ ] `frontend/src/__tests__/components/ResearchPage.test.tsx` — covers FLOW-03 (SSE progress + approval flow)
- [ ] `supabase/migrations/20260321700000_design_brief_unique.sql` — adds UNIQUE(project_id) on design_systems
- [ ] Extend existing `tests/unit/app_builder/test_app_builder_router.py` with new endpoint tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE streaming progress updates render in browser | FLOW-02 | Browser-specific EventSource/fetch behavior | Start dev server, create project, trigger research, verify progress cards appear |
| Design brief cards are visually editable | FLOW-03 | Visual layout verification | Open research page, verify color/typography/spacing fields are editable inputs |
| Build plan dependency tree renders correctly | FLOW-04 | Visual tree/graph rendering | Approve brief, verify build plan shows phases with dependency arrows |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

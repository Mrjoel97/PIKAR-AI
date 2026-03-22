---
phase: 19
slug: screen-generation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend), vitest (frontend) |
| **Config file** | `pytest.ini` (backend), `frontend/vitest.config.mts` (frontend) |
| **Quick run command** | `uv run pytest tests/unit/app_builder/test_screen_generation_service.py -x` |
| **Full suite command** | `uv run pytest tests/unit/app_builder/ -x && cd frontend && npx vitest run` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/app_builder/ -x`
- **After every plan wave:** Run `uv run pytest tests/unit/app_builder/ -x && cd frontend && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | SCRN-01 | unit | `uv run pytest tests/unit/app_builder/test_screen_generation_service.py -x` | Wave 0 | pending |
| 19-01-02 | 01 | 1 | SCRN-01 | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_generate_screen_sse -x` | Wave 0 | pending |
| 19-01-03 | 01 | 1 | SCRN-04 | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_generate_device_variant -x` | Wave 0 | pending |
| 19-01-04 | 01 | 1 | FOUN-05 | unit | `uv run pytest tests/unit/app_builder/test_screen_generation_service.py::test_persists_before_yield -x` | Wave 0 | pending |
| 19-02-01 | 02 | 1 | SCRN-02 | unit | `cd frontend && npx vitest run src/__tests__/components/VariantComparisonGrid.test.tsx` | Wave 0 | pending |
| 19-02-02 | 02 | 1 | SCRN-03 | unit | `cd frontend && npx vitest run src/__tests__/components/DevicePreviewFrame.test.tsx` | Wave 0 | pending |
| 19-02-03 | 02 | 1 | BLDR-02 | unit | `cd frontend && npx vitest run src/__tests__/components/BuildingPage.test.tsx` | Wave 0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/app_builder/test_screen_generation_service.py` — stubs for SCRN-01, FOUN-05 (new file; mock StitchMCPService and persist_screen_assets)
- [ ] `tests/unit/app_builder/test_app_builder_router.py` — extend with generate-screen SSE + device variant tests (SCRN-01, SCRN-04)
- [ ] `frontend/src/__tests__/components/VariantComparisonGrid.test.tsx` — covers SCRN-02 (side-by-side variant display + selection)
- [ ] `frontend/src/__tests__/components/DevicePreviewFrame.test.tsx` — covers SCRN-03 (iframe + device tab switcher)
- [ ] `frontend/src/__tests__/components/BuildingPage.test.tsx` — covers BLDR-02 (building page renders variant grid after generation)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Stitch MCP generates actual variant HTML | SCRN-01 | Requires live Stitch API key | Start backend with STITCH_API_KEY, trigger generation, verify HTML files in Supabase Storage |
| iframe renders interactive live HTML | FOUN-05, BLDR-02 | Browser-specific rendering behavior | Open building page, click a variant, verify iframe shows interactive HTML |
| Device-specific layouts look correct | SCRN-04 | Visual layout verification | Generate MOBILE/TABLET variants, verify they differ from DESKTOP (not just scaled) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

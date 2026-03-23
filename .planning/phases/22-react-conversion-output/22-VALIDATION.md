---
phase: 22
slug: react-conversion-output
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with pytest-asyncio |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/unit/app_builder/test_react_converter.py -x -v` |
| **Full suite command** | `uv run pytest tests/unit/app_builder/ -x -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/app_builder/ -x -v`
- **After every plan wave:** Run `uv run pytest tests/unit/app_builder/ tests/unit/services/test_remotion_render_service.py -x -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 22-01-01 | 01 | 1 | OUTP-01 | unit | `uv run pytest tests/unit/app_builder/test_react_converter.py -x` | ❌ W0 | ⬜ pending |
| 22-01-02 | 01 | 1 | OUTP-05 | unit | `uv run pytest tests/unit/app_builder/test_react_converter.py::test_resolve_npm_version -x` | ❌ W0 | ⬜ pending |
| 22-01-03 | 01 | 1 | OUTP-02 | unit | `uv run pytest tests/unit/app_builder/test_pwa_generator.py -x` | ❌ W0 | ⬜ pending |
| 22-01-04 | 01 | 1 | OUTP-03 | unit | `uv run pytest tests/unit/app_builder/test_capacitor_generator.py -x` | ❌ W0 | ⬜ pending |
| 22-02-01 | 02 | 1 | OUTP-04 | unit | `uv run pytest tests/unit/app_builder/test_ship_service.py::test_build_walkthrough_scenes -x` | ❌ W0 | ⬜ pending |
| 22-02-02 | 02 | 1 | FLOW-07 | unit | `uv run pytest tests/unit/app_builder/test_ship_service.py::test_ship_events -x` | ❌ W0 | ⬜ pending |
| 22-02-03 | 02 | 1 | FLOW-07 | unit | `uv run pytest tests/unit/app_builder/test_ship_service.py::test_ship_partial_failure -x` | ❌ W0 | ⬜ pending |
| 22-03-01 | 03 | 2 | FLOW-07 | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_ship_endpoint -x` | ❌ W0 | ⬜ pending |
| 22-04-01 | 04 | 3 | FLOW-07 | unit | `cd frontend && npx vitest run src/__tests__/components/ShipPage.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `supabase/migrations/20260324000000_stitch_assets_allow_video.sql` — add video/mp4 to stitch-assets MIME types
- [ ] `tests/unit/app_builder/test_react_converter.py` — stubs for OUTP-01, OUTP-05
- [ ] `tests/unit/app_builder/test_pwa_generator.py` — stubs for OUTP-02
- [ ] `tests/unit/app_builder/test_capacitor_generator.py` — stubs for OUTP-03
- [ ] `tests/unit/app_builder/test_ship_service.py` — stubs for OUTP-04, FLOW-07

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Gemini HTML→React conversion quality | OUTP-01 | Requires API key + real Stitch HTML | Convert a real screen, check .tsx output compiles |
| PWA installability on mobile | OUTP-02 | Requires mobile device/emulator | Open PWA URL in Chrome Android, verify install prompt |
| Capacitor project builds | OUTP-03 | Requires Xcode/Android Studio | Download ZIP, run `npx cap add ios`, verify build |
| Remotion video render quality | OUTP-04 | Visual inspection of MP4 | Download rendered video, check transitions and overlays |
| npm version freshness | OUTP-05 | Network call to registry.npmjs.org | Verify package.json versions match latest stable |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

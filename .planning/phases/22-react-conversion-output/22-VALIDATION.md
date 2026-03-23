---
phase: 22
slug: react-conversion-output
status: draft
nyquist_compliant: true
wave_0_complete: true
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

## Wave 0 Strategy

All plans in this phase use **inline TDD** (`tdd="true"` on tasks). Each task creates its own
test file as the FIRST step before writing production code. This means:

- Test files are created within each task's execution (not as a separate Wave 0 step)
- The RED-GREEN cycle happens within the task itself
- No separate Wave 0 plan is needed

This satisfies the Nyquist contract because every code-producing task has `<automated>` verify
commands that run the tests created within that same task. There are no MISSING test file references.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Inline TDD | Status |
|---------|------|------|-------------|-----------|-------------------|------------|--------|
| 22-01-01 | 01 | 1 | OUTP-01, OUTP-05 | unit | `uv run pytest tests/unit/app_builder/test_react_converter.py -x` | Yes | pending |
| 22-02-01 | 02 | 1 | OUTP-02 | unit | `uv run pytest tests/unit/app_builder/test_pwa_generator.py -x` | Yes | pending |
| 22-02-02 | 02 | 1 | OUTP-03 | unit | `uv run pytest tests/unit/app_builder/test_capacitor_generator.py -x` | Yes | pending |
| 22-03-01 | 03 | 2 | OUTP-04, FLOW-07 | verify | `python -c "from app.services.remotion_render_service import render_scenes_direct_to_mp4"` | No (config) | pending |
| 22-03-02 | 03 | 2 | OUTP-04, FLOW-07 | unit | `uv run pytest tests/unit/app_builder/test_ship_service.py -x` | Yes | pending |
| 22-04-01 | 04 | 3 | FLOW-07 | tsc | `cd frontend && npx tsc --noEmit --pretty` | No (UI) | pending |
| 22-04-02 | 04 | 3 | FLOW-07 | visual | Human checkpoint — verify shipping page UI | N/A | pending |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Gemini HTML-to-React conversion quality | OUTP-01 | Requires API key + real Stitch HTML | Convert a real screen, check .tsx output compiles |
| PWA installability on mobile | OUTP-02 | Requires mobile device/emulator | Open PWA URL in Chrome Android, verify install prompt |
| Capacitor project builds | OUTP-03 | Requires Xcode/Android Studio | Download ZIP, run `npx cap add ios`, verify build |
| Remotion video render quality | OUTP-04 | Visual inspection of MP4 | Download rendered video, check transitions and overlays |
| npm version freshness | OUTP-05 | Network call to registry.npmjs.org | Verify package.json versions match latest stable |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify — inline TDD creates tests within each task
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 satisfied by inline TDD approach (no separate Wave 0 needed)
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (inline TDD satisfies Nyquist contract)

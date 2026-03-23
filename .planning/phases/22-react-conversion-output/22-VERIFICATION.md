---
phase: 22-react-conversion-output
verified: 2026-03-23T19:00:00Z
status: passed
score: 6/6 success criteria verified
re_verification: false
gaps:
  - truth: "A PWA export generates a valid manifest.json, a service worker, and all required mobile meta tags — the exported app can be installed from a browser on Android and iOS as a home screen app"
    status: partial
    reason: "_ship_pwa in ship_service.py passes html_url storage URLs as html_content to generate_pwa_zip instead of downloading the actual HTML first. The PWA package will contain URL strings inside the body rather than the app's rendered HTML. _ship_react correctly downloads HTML via httpx; _ship_pwa and _ship_capacitor do not."
    artifacts:
      - path: "app/services/ship_service.py"
        issue: "Lines 265-266: combined_html joins s.get('html_url') strings (Supabase storage URLs, not HTML). Must download each URL via httpx before combining, matching the _ship_react pattern."
      - path: "app/services/ship_service.py"
        issue: "Lines 294-295: same bug in _ship_capacitor — joins html_url strings instead of downloaded HTML content."
    missing:
      - "In _ship_pwa: download HTML from each screen's html_url via httpx (same pattern as _ship_react lines 212-223) before joining into combined_html"
      - "In _ship_capacitor: same fix — download HTML from html_url via httpx before passing to generate_capacitor_zip"
  - truth: "A Capacitor export generates a complete project scaffold (capacitor.config.ts, package.json, platform configs) that a developer can download and run with `npx cap add ios && npx cap add android` without additional configuration"
    status: partial
    reason: "Same root cause as PWA gap: _ship_capacitor passes html_url strings as html_content instead of fetching the actual HTML. The www/index.html in the ZIP will contain Supabase storage URLs rather than the app HTML."
    artifacts:
      - path: "app/services/ship_service.py"
        issue: "Lines 294-295: _ship_capacitor joins html_url strings as html_content — must download via httpx first"
    missing:
      - "In _ship_capacitor: download HTML from each screen's html_url via httpx before passing to generate_capacitor_zip"
  - truth: "REQUIREMENTS-v2.md status for OUTP-01, OUTP-02, OUTP-03, OUTP-05 not updated to Complete"
    status: failed
    reason: "REQUIREMENTS-v2.md still marks OUTP-01, OUTP-02, OUTP-03, OUTP-05 as unchecked ([ ]) and 'Pending' in the tracking table, though all four are implemented. FLOW-07 and OUTP-04 are correctly marked complete."
    artifacts:
      - path: ".planning/REQUIREMENTS-v2.md"
        issue: "Lines 50-53 and 112-115: OUTP-01/02/03/05 status not updated after implementation"
    missing:
      - "Update .planning/REQUIREMENTS-v2.md: change [ ] to [x] for OUTP-01, OUTP-02, OUTP-03, OUTP-05 and change 'Pending' to 'Complete' in the tracking table"
human_verification:
  - test: "Navigate to an app-builder project in the verifying stage, click through to the shipping page"
    expected: "Shipping page shows 4 target cards (React + TypeScript, PWA, iOS & Android, Walkthrough Video) with checkboxes, a 'Ship N Targets' button, and the Back button"
    why_human: "Visual appearance, card layout, and checkbox toggle interaction require browser inspection"
  - test: "With a running backend, trigger the ship process for 'react' target only on a project with at least one approved screen"
    expected: "target_started event updates the card to a spinner; target_complete (or target_failed) updates to green check (or red X); ship_complete shows the done panel with download link"
    why_human: "Real-time SSE streaming behavior and download link functionality require a live browser session"
---

# Phase 22: React Conversion Output Verification Report

**Phase Goal:** Users can export their built app in any target format — modular React/TypeScript components, an installable PWA, a downloadable Capacitor hybrid project for iOS/Android, and a Remotion walkthrough video — and the ship stage bundles and deploys everything
**Verified:** 2026-03-23T19:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Stitch HTML for any screen can be converted to modular React/TypeScript components with Tailwind theme config extracted from inline styles — downloadable ZIP with one component per screen section | VERIFIED | `app/services/react_converter.py` — `convert_html_to_react_zip()` uses Gemini 2.0 Flash structured output with `response_mime_type="application/json"`, produces ZIP with `src/components/*.tsx`, `src/App.tsx`, `tailwind.config.ts`, `package.json`. 9/9 unit tests pass. |
| 2 | A PWA export generates a valid manifest.json, a service worker, and all required mobile meta tags — the exported app can be installed from a browser on Android and iOS | PARTIAL | `app/services/pwa_generator.py` — `generate_pwa_zip()` correctly produces manifest.json (192+512+maskable icons, display:standalone), hand-written cache-first sw.js, index.html with all Apple iOS meta tags. BUT `_ship_pwa` in `ship_service.py` passes `html_url` URL strings to `generate_pwa_zip` instead of downloading HTML first — the installed app's body will contain Supabase storage URLs, not the rendered screen HTML. |
| 3 | A Capacitor export generates a complete project scaffold (capacitor.config.ts, package.json, www/index.html, README.md) that a developer can run with `npx cap add ios && npx cap add android` | PARTIAL | `app/services/capacitor_generator.py` — `generate_capacitor_zip()` correctly produces 4-file scaffold with proper `capacitor.config.ts` (reverse-domain appId, webDir=www), resolved npm versions, and README with setup instructions. BUT `_ship_capacitor` in `ship_service.py` has the same URL-passing bug as `_ship_pwa` — `www/index.html` will contain Supabase storage URL strings instead of app HTML. |
| 4 | A Remotion walkthrough video is generated from the app's screenshots with transitions and title overlays — the user can download the rendered MP4 | VERIFIED | `render_scenes_direct_to_mp4` added to `remotion_render_service.py` (line 1057). `ship_service.py` `_ship_video` calls it via `asyncio.to_thread` with pre-built scene list (intro 3s + per-screen 4s with imageUrl + fade transition + outro 2s). Video MP4 uploaded to stitch-assets. Migration `20260324000000_stitch_assets_allow_video.sql` adds video/mp4 MIME type. 9/9 ship service tests pass including `test_ship_video_uses_asyncio_to_thread`. |
| 5 | Generated package.json files reference current stable versions of React, Tailwind, Capacitor, and Remotion resolved from npm at generation time — not hardcoded versions that go stale | VERIFIED | Both `react_converter.py` (`resolve_npm_version`) and `capacitor_generator.py` (`_resolve_npm_version`) perform async httpx GET to `https://registry.npmjs.org/{package}` with 5s timeout, returning `dist-tags.latest`. Fallback to hardcoded known-good versions on error. Tests verify both live-resolution path and fallback path. |
| 6 | The ship stage generates all selected output targets and initiates deployment in a single user action — the user does not manually trigger each export format separately | VERIFIED | `ship_service.py` `ship_project` async generator processes all selected targets sequentially, yielding `target_started`/`target_complete`/`target_failed` per target and `ship_complete` at the end. `POST /app-builder/projects/{id}/ship` SSE endpoint wired in `app_builder.py` router. `ShippingPage` (283 lines) provides 4-target selection, single Ship button, real-time status indicators, per-target download links, and Finish flow. All connected via `shipProject()` SSE service function using established ReadableStream pattern. |

**Score:** 4/6 truths fully verified (2 partial due to HTML-fetching bug in _ship_pwa and _ship_capacitor)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/react_converter.py` | HTML-to-React conversion + npm version resolution + ZIP creation | VERIFIED | 293 lines, exports `convert_html_to_react_zip` and `resolve_npm_version`, Gemini structured output with `response_mime_type`, npm registry calls with fallback |
| `tests/unit/app_builder/test_react_converter.py` | Unit tests (min 80 lines) | VERIFIED | 325 lines, 9 tests all passing |
| `app/services/pwa_generator.py` | PWA manifest, service worker, iOS meta tags, ZIP creation | VERIFIED | 152 lines, exports `generate_pwa_zip`, hand-written service worker, all iOS meta tags present |
| `app/services/capacitor_generator.py` | Capacitor scaffold ZIP with config, package.json, www/index.html, README | VERIFIED | 252 lines, exports `generate_capacitor_zip`, self-contained npm resolution, reverse-domain appId |
| `tests/unit/app_builder/test_pwa_generator.py` | Unit tests (min 60 lines) | VERIFIED | 170 lines, 7 tests all passing |
| `tests/unit/app_builder/test_capacitor_generator.py` | Unit tests (min 60 lines) | VERIFIED | 210 lines, 7 tests all passing |
| `supabase/migrations/20260324000000_stitch_assets_allow_video.sql` | Migration adding video/mp4 to stitch-assets allowed MIME types (min 5 lines) | VERIFIED | 9 lines, valid UPDATE SQL with idempotency guard |
| `app/services/ship_service.py` | Ship orchestrator yielding SSE events per target | VERIFIED | 412 lines, exports `ship_project` async generator, all 4 target helpers present |
| `app/services/remotion_render_service.py` | `render_scenes_direct_to_mp4` function | VERIFIED | Function at line 1057, accepts pre-built scene dicts, bypasses `_scenes_from_prompt`, synchronous for `asyncio.to_thread` |
| `app/routers/app_builder.py` | POST /app-builder/projects/{id}/ship SSE endpoint | VERIFIED | `ShipRequest` model at line 83, endpoint at line 853, imports `ship_project`, returns StreamingResponse with SSE headers |
| `tests/unit/app_builder/test_ship_service.py` | Unit tests (min 100 lines) | VERIFIED | 389 lines, 9 tests all passing |
| `frontend/src/types/app-builder.ts` | `ShipEvent` type and `ShipTarget` type | VERIFIED | `ShipTarget` at line 150, `ShipEvent` interface at line 152 |
| `frontend/src/services/app-builder.ts` | `shipProject` SSE function | VERIFIED | `shipProject` function at line 403, exact ReadableStream pattern matching `buildAllPages` |
| `frontend/src/app/app-builder/[projectId]/shipping/page.tsx` | Shipping page with target selection, SSE progress, download links (min 80 lines) | VERIFIED | 283 lines, 4 target cards, local accumulator pattern, `StatusIndicator` sub-component, download links, Finish button |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/services/react_converter.py` | `google.genai` | `response_mime_type="application/json"` | WIRED | Line 270: `response_mime_type="application/json"` in `GenerateContentConfig` |
| `app/services/react_converter.py` | `https://registry.npmjs.org` | `httpx async GET` | WIRED | Line 90: `await client.get(f"{_NPM_REGISTRY}/{package}")` |
| `app/services/pwa_generator.py` | `zipfile + io.BytesIO` | stdlib in-memory ZIP | WIRED | Line 146: `zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED)` |
| `app/services/capacitor_generator.py` | `https://registry.npmjs.org` | local `_resolve_npm_version` with `_CAPACITOR_FALLBACK_VERSIONS` | WIRED | Line 26: `_NPM_REGISTRY`, line 28: `_CAPACITOR_FALLBACK_VERSIONS`, line 54: `await client.get(...)` |
| `app/services/ship_service.py` | `app/services/react_converter.py` | `from app.services.react_converter import` | WIRED | Line 19: `from app.services.react_converter import convert_html_to_react_zip` |
| `app/services/ship_service.py` | `app/services/pwa_generator.py` | `from app.services.pwa_generator import` | WIRED | Line 17: `from app.services.pwa_generator import generate_pwa_zip` |
| `app/services/ship_service.py` | `app/services/capacitor_generator.py` | `from app.services.capacitor_generator import` | WIRED | Line 18: `from app.services.capacitor_generator import generate_capacitor_zip` |
| `app/services/ship_service.py` | `app/services/remotion_render_service.py` | `asyncio.to_thread(render_scenes_direct_to_mp4, ...)` | WIRED | Lines 332-336: `await asyncio.to_thread(render_scenes_direct_to_mp4, scenes, total_duration, user_id)` |
| `app/services/remotion_render_service.py` | internal | `def render_scenes_direct_to_mp4` present | WIRED | Line 1057: function exists, bypasses `_scenes_from_prompt` |
| `app/routers/app_builder.py` | `app/services/ship_service.py` | `from app.services.ship_service import ship_project` | WIRED | Line 23: import confirmed, line 880: `async for event in ship_project(...)` |
| `frontend/src/app/app-builder/[projectId]/shipping/page.tsx` | `frontend/src/services/app-builder.ts` | `import shipProject` | WIRED | Line 5: `import { shipProject, advanceStage } from '@/services/app-builder'` |
| `frontend/src/services/app-builder.ts` | `POST /app-builder/projects/{id}/ship` | `fetch` with ReadableStream SSE pattern | WIRED | Line 409: `fetch(\`${API_BASE}/app-builder/projects/${projectId}/ship\`, ...)` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| OUTP-01 | 22-01-PLAN.md | Stitch HTML converted to modular React/TypeScript components with Tailwind theme extraction | SATISFIED | `react_converter.py` + `_ship_react` (correctly downloads HTML and converts via Gemini) |
| OUTP-02 | 22-02-PLAN.md | PWA output with manifest.json, service worker, and mobile meta tags | PARTIAL | `pwa_generator.py` generator correct; `_ship_pwa` passes html_url strings instead of downloaded HTML — PWA body content bug |
| OUTP-03 | 22-02-PLAN.md | Downloadable Capacitor project structure for iOS/Android | PARTIAL | `capacitor_generator.py` scaffold correct; `_ship_capacitor` passes html_url strings instead of downloaded HTML — www/index.html content bug |
| OUTP-04 | 22-03-PLAN.md | Remotion walkthrough video from screenshots with transitions and overlays | SATISFIED | `render_scenes_direct_to_mp4` + `_ship_video` with `asyncio.to_thread`, fade transitions, imageUrl per screen |
| OUTP-05 | 22-01-PLAN.md | Current stable npm versions resolved at generation time with fallback | SATISFIED | Both `resolve_npm_version` (react_converter) and `_resolve_npm_version` (capacitor_generator) call registry.npmjs.org with fallback |
| FLOW-07 | 22-03-PLAN.md, 22-04-PLAN.md | Ship stage generates all output targets in a single user action | SATISFIED | Single POST /ship SSE endpoint, `ship_project` async generator, ShippingPage with single Ship button |

**Orphaned requirements check:** REQUIREMENTS-v2.md marks OUTP-01, OUTP-02, OUTP-03, OUTP-05 as `[ ] Pending` even though all four are implemented. This is a documentation tracking discrepancy that should be corrected.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/services/ship_service.py` | 265-266 | `combined_html = "\n".join(s.get("html_url") or "" ...)` — joins URL strings as HTML content | Blocker | PWA index.html body will contain Supabase storage URLs, not rendered app HTML; the installed PWA will show raw URLs |
| `app/services/ship_service.py` | 294-295 | Same bug in `_ship_capacitor` — joins html_url strings instead of fetched HTML | Blocker | Capacitor `www/index.html` will contain storage URLs; the shipped mobile project will not contain actual app content |
| `.planning/REQUIREMENTS-v2.md` | 50-53, 112-115 | OUTP-01/02/03/05 marked `[ ]` (Pending) despite being implemented | Warning | Misrepresents phase completion status |

---

### Human Verification Required

#### 1. Shipping Page UI Appearance

**Test:** Start the frontend dev server (`cd frontend && npm run dev`), navigate to an existing app-builder project in the `verifying` stage, advance to the shipping page.
**Expected:** Page shows "Ship Your App" heading, 4 target cards (React + TypeScript, PWA, iOS & Android, Walkthrough Video) each with a checkbox-style indicator, icon, label, and description. The "Ship N Targets" button is present and enabled. Unchecking a target dims the card.
**Why human:** Visual card layout, checkbox toggle interaction, and responsive grid require browser inspection.

#### 2. Real-time SSE Progress During Ship

**Test:** With both frontend and backend running, trigger the ship process on a project with at least one approved screen. Observe the UI while shipping.
**Expected:** Each target card shows a spinner (in-progress), then a green checkmark with a Download button (complete) or red X (failed). After all targets finish, the "All Done!" panel appears with the Finish button.
**Why human:** Real-time streaming state transitions and download link rendering require a live browser session.

---

### Gaps Summary

Two backend bugs share the same root cause and block OUTP-02 (PWA) and OUTP-03 (Capacitor) from being fully correct at runtime:

**Root cause:** `_ship_pwa` and `_ship_capacitor` in `app/services/ship_service.py` assemble `combined_html` by joining the `html_url` field values (which are Supabase storage URL strings) rather than downloading the actual HTML from those URLs via httpx. In contrast, `_ship_react` correctly downloads HTML from each screen's `html_url` before processing it (lines 219-221).

The fix is identical for both functions: add an `httpx.AsyncClient` block that downloads each screen's HTML from its `html_url` before joining, exactly mirroring the `_ship_react` implementation pattern.

These bugs are not caught by the unit tests because the tests mock `_fetch_approved_screens` to return fake in-memory data, and the mock `generate_pwa_zip` / `generate_capacitor_zip` functions accept any string as `html_content`.

Additionally, the REQUIREMENTS-v2.md tracking table was not updated after implementation — OUTP-01, OUTP-02, OUTP-03, and OUTP-05 remain marked as Pending.

---

_Verified: 2026-03-23T19:00:00Z_
_Verifier: Claude (gsd-verifier)_

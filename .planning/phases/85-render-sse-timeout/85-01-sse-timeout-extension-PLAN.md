---
phase: 85-render-sse-timeout
plan: 01
type: tdd
wave: 0
depends_on: []
files_modified:
  - app/routers/admin/chat.py
  - app/fast_api_app.py
  - app/.env.example
  - tests/unit/admin/test_admin_chat.py
  - tests/unit/test_sse_max_duration.py
  - tests/integration/test_sse_endpoint.py
  - .planning/phases/85-render-sse-timeout/deferred-items.md
  - .planning/STATE.md
  - .planning/ROADMAP.md
  - .planning/REQUIREMENTS.md
autonomous: true
requirements:
  - HOTFIX-03
must_haves:
  truths:
    - "_SSE_MAX_DURATION_S in app/routers/admin/chat.py reads os.getenv('SSE_MAX_DURATION_S', '570') — no longer hardcoded 300"
    - "SSE_MAX_DURATION_S in app/fast_api_app.py reads os.getenv('SSE_MAX_DURATION_S', '570') — default raised from 300"
    - "Both modules use the SAME env var name (SSE_MAX_DURATION_S) so a single Cloud Run env override governs both endpoints"
    - "A simulated 7-minute (420s) SSE stream completes without emitting the 'Stream timeout' error (mock-time integration test)"
    - "Heartbeat ': keepalive\\n\\n' is emitted at least once during a >10s no-event window (regression test)"
    - "Heartbeat is suppressed when real events arrive faster than every 10s (regression test guarding the last_keepalive reset path)"
    - "When the deadline IS hit (>570s), the error string remains EXACTLY 'Stream timeout — please retry your request.' — frontend match logic stays valid"
    - ".env.example documents SSE_MAX_DURATION_S=570 with a comment about the Cloud Run --timeout coupling"
    - "deferred-items.md exists at .planning/phases/85-render-sse-timeout/deferred-items.md and documents the >570s render case as an async-job-queue follow-up (SC4)"
    - "make lint passes (ruff check, ruff format, ty check, codespell) — no new lint failures introduced"
    - "All 7 new/extended tests are GREEN after Task 2; the 6 that fail at the start of Task 2 (RED state) all pass post-fix"
  artifacts:
    - path: "app/routers/admin/chat.py"
      provides: "Admin SSE generator now env-driven, default 570s"
      contains: "os.getenv(\"SSE_MAX_DURATION_S\", \"570\")"
    - path: "app/fast_api_app.py"
      provides: "User-facing SSE generator default raised to 570s"
      contains: "os.getenv(\"SSE_MAX_DURATION_S\", \"570\")"
    - path: "app/.env.example"
      provides: "SSE_MAX_DURATION_S documented with Cloud Run coupling note"
      contains: "SSE_MAX_DURATION_S=570"
    - path: "tests/unit/test_sse_max_duration.py"
      provides: "Env default + env override propagation tests for both SSE modules"
      exports: ["test_env_default", "test_env_override"]
    - path: "tests/unit/admin/test_admin_chat.py"
      provides: "Constant assertion for admin _SSE_MAX_DURATION_S >= 570"
      exports: ["test_sse_max_duration_constant"]
    - path: "tests/integration/test_sse_endpoint.py"
      provides: "Long-stream + heartbeat + error-string regression tests"
      exports: ["test_long_stream_does_not_timeout", "test_heartbeat_during_slow_render", "test_heartbeat_suppressed_when_events_flow", "test_timeout_error_string_unchanged"]
    - path: ".planning/phases/85-render-sse-timeout/deferred-items.md"
      provides: "SC4 deferred-work documentation (renders >570s require async job queue)"
      contains: "async job queue"
  key_links:
    - from: "app/routers/admin/chat.py"
      to: "SSE_MAX_DURATION_S env var"
      via: "module-level os.getenv at line 41"
      pattern: "os\\.getenv\\(\"SSE_MAX_DURATION_S\""
    - from: "app/fast_api_app.py"
      to: "SSE_MAX_DURATION_S env var"
      via: "module-level os.getenv at line 1954-1956"
      pattern: "os\\.getenv\\(\"SSE_MAX_DURATION_S\", \"570\"\\)"
    - from: "tests/unit/test_sse_max_duration.py"
      to: "Both SSE modules"
      via: "monkeypatch.setenv + importlib.reload"
      pattern: "importlib\\.reload"
---

<objective>
Phase 85 / Plan 01 — Raise the SSE stream maximum duration in BOTH the admin chat router AND the user-facing run_sse endpoint from 300s → 570s, governed by a single `SSE_MAX_DURATION_S` env var. This unblocks long video renders (typical 7-9 min) that currently die at 300s with a "Stream timeout — please retry your request." error while the render continues server-side.

Purpose:
  - Close HOTFIX-03 (Phase 85 SC1, SC2, SC3, SC4) — long renders surface their final asset URL to users without a stream timeout, while keeping a 30s safety margin under Cloud Run's 600s --timeout so SSE always wins the race and the user sees the friendly app error instead of a raw 504.
  - Preserve the heartbeat keepalive logic (SC3) — verified via two regression tests so any future refactor can't quietly break it.
  - Document the >570s render case as an async-job-queue follow-up (SC4 deferred-items).

Output:
  - Two source files patched (admin/chat.py + fast_api_app.py) — single env-var contract.
  - One env-example update (app/.env.example) — operators can override.
  - Seven test cases (1 admin constant + 2 env-propagation + 4 integration) — RED→GREEN cycle.
  - One deferred-items.md — SC4 documentation.
  - Updated STATE.md, ROADMAP.md, REQUIREMENTS.md, and SUMMARY with the SC1 literal-vs-engineering tradeoff prominently noted.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/85-render-sse-timeout/85-RESEARCH.md
@.planning/phases/85-render-sse-timeout/85-VALIDATION.md
@.planning/phases/83-document-upload-bypass/deferred-items.md

# Source files to be patched
@app/routers/admin/chat.py
@app/fast_api_app.py
@app/.env.example

# Existing test infrastructure to extend
@tests/unit/admin/test_admin_chat.py
@tests/integration/test_sse_endpoint.py

# Reference (do NOT modify — these confirm the 600s Cloud Run ceiling)
@Makefile
@cloud-run-service.yaml
@cloudrun.yaml
@scripts/deploy-fast.ps1

<interfaces>
<!-- Key file:line anchors. Executor uses these directly — no codebase exploration needed. -->

From `app/routers/admin/chat.py`:
- Line 17-21: imports — `import asyncio, json, logging, time` and `from collections.abc import AsyncGenerator`. NO `import os` currently — Task 2 must add it (ruff `I` will sort it correctly).
- Line 40-41 (CURRENT — to be replaced):
  ```python
  # SSE stream maximum duration (seconds)
  _SSE_MAX_DURATION_S = 300
  ```
- Line 41 (TARGET):
  ```python
  # SSE stream maximum duration (seconds). Keep < Cloud Run's 600s
  # `--timeout` (Makefile:107, scripts/deploy-fast.ps1:124,
  # cloud-run-service.yaml:118, cloudrun.yaml:20) by a 30s safety margin
  # so SSE wins the race and the user always sees the friendly
  # 'Stream timeout' message instead of a raw 504. Override via the
  # SSE_MAX_DURATION_S env var; if you raise this >= 600, also raise the
  # Cloud Run --timeout in lockstep.
  _SSE_MAX_DURATION_S = int(os.getenv("SSE_MAX_DURATION_S", "570"))
  ```
- Line 356: `deadline = time.monotonic() + _SSE_MAX_DURATION_S` (no change needed)
- Line 364-366: `Stream timeout — please retry your request.` literal (must remain string-equal)
- Line 373-375: heartbeat `: keepalive\n\n` every 10s of inactivity (no change)

From `app/fast_api_app.py`:
- Line 1954-1956 (CURRENT):
  ```python
  SSE_MAX_DURATION_S = int(
      os.getenv("SSE_MAX_DURATION_S", "300")
  )  # 5 min default
  ```
- Line 1955 (TARGET — change literal `"300"` → `"570"` and update comment):
  ```python
  SSE_MAX_DURATION_S = int(
      os.getenv("SSE_MAX_DURATION_S", "570")
  )  # 9.5 min default; sized for Cloud Run --timeout 600 (30s safety margin)
  ```
- Line 1972-1978: same `Stream timeout` literal — must remain unchanged
- Line 1992-1994: heartbeat path — must remain unchanged
- `import os` is ALREADY present at the top of this file (no new import)

From `app/.env.example`:
- Section `# STREAMING AND UPLOAD GUARDRAILS` ends near line 92 (per RESEARCH § Files Involved)
- The variable `SSE_MAX_DURATION_S` is currently NOT documented — Task 2 appends it after that section

From `tests/integration/test_sse_endpoint.py`:
- Lines 19-20: `os.environ["LOCAL_DEV_BYPASS"] = "1"` set BEFORE app import — same pattern for Task 1 new tests.
- Lines 30-86: `test_app` fixture builds a minimal FastAPI app with mocked session/runner. **New integration tests in Task 1 should follow this fixture pattern** — do NOT spin up the real `app/fast_api_app.py` (that pulls Supabase/ADK).
- For testing module-level constants like `SSE_MAX_DURATION_S` (read at import time): use `monkeypatch.setenv("SSE_MAX_DURATION_S", "X")` BEFORE `importlib.reload(app.fast_api_app)` / `importlib.reload(app.routers.admin.chat)`. See VALIDATION.md § Wave 0 Requirements.

Frontend SSE consumer (DO NOT TOUCH — confirms the error string contract):
- `frontend/src/hooks/useBackgroundStream.ts` — does NOT auto-retry on `data: {error}` events. The `Stream timeout — please retry your request.` literal MUST remain byte-identical.
- `frontend/src/hooks/useAdminChat.ts` — same constraint.
</interfaces>

<scope_boundary>
**MUST NOT** in this plan:
- Touch any file in `frontend/` — none of the SC require frontend changes
- Modify `Makefile`, `cloudrun.yaml`, `cloud-run-service.yaml`, or `scripts/deploy-fast.ps1` — Cloud Run --timeout=600 is the deliberate ceiling for this phase
- Modify the `Stream timeout — please retry your request.` literal in either SSE generator (frontend match logic depends on it)
- Touch `app/services/director_service.py` or `app/services/remotion_render_service.py` — those budgets are independent
- Increase the value beyond 570 (would erode the safety margin under the 600s Cloud Run ceiling)
- Move the SSE generator to an async job queue — that's the SC4 deferred work, not in scope
</scope_boundary>
</context>

<sc1_tradeoff_note>
**SC1 Literal-vs-Engineering Tradeoff (locked by user decision; documented prominently in SUMMARY + ROADMAP):**

- ROADMAP SC1 verbatim: *"`_SSE_MAX_DURATION_S` in `app/routers/admin/chat.py` is raised from 300s to **at least 600s**."*
- This plan implements **570s**, technically below the literal "at least 600s".
- **Why:** Cloud Run's request `--timeout` is exactly 600s. If SSE deadline = 600s and Cloud Run = 600s, the platform may close the connection while the SSE generator is mid-final-yield, producing a raw 504 instead of the friendly app error. 570s gives a 30s safety margin so SSE always wins the race.
- **Locked by user decision (planning context):** value = 570s, scope = both files (admin/chat.py AND fast_api_app.py — the goal text says "users", which is the fast_api_app.py path).
- **Where this is documented:** plan SUMMARY (must include a prominent "SC1 Literal-vs-Engineering Tradeoff" section) AND ROADMAP Phase 85 entry (Task 2 updates the SC1 status note).
</sc1_tradeoff_note>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: RED — write all 7 failing tests + draft deferred-items.md</name>
  <files>tests/unit/test_sse_max_duration.py, tests/unit/admin/test_admin_chat.py, tests/integration/test_sse_endpoint.py, .planning/phases/85-render-sse-timeout/deferred-items.md</files>
  <behavior>
    Write seven test cases that FAIL today (because the source still has 300s) and will PASS after Task 2's edits. Drop a draft `deferred-items.md` documenting the SC4 case. After this task, the test suite is RED in exactly the predicted ways.

    **Tests to add (verbatim test names — do not rename; VALIDATION.md per-task table depends on them):**

    1. `tests/unit/admin/test_admin_chat.py` (extend existing file) — add `test_sse_max_duration_constant`:
       - Imports `_SSE_MAX_DURATION_S` from `app.routers.admin.chat`.
       - Asserts `_SSE_MAX_DURATION_S == 570` when env var unset.
       - Uses `monkeypatch.delenv("SSE_MAX_DURATION_S", raising=False)` + `importlib.reload(app.routers.admin.chat)` for hermeticity.
       - Currently FAILS because the constant is hardcoded `300`.

    2. `tests/unit/test_sse_max_duration.py` (NEW file) — add `test_env_default`:
       - Hermetically reload BOTH `app.fast_api_app` and `app.routers.admin.chat` after `monkeypatch.delenv("SSE_MAX_DURATION_S", raising=False)`.
       - Assert `app.fast_api_app.SSE_MAX_DURATION_S == 570`.
       - Assert `app.routers.admin.chat._SSE_MAX_DURATION_S == 570`.
       - Currently FAILS — admin is hardcoded 300; fast_api_app default is "300".
       - **Note:** Reloading `app.fast_api_app` triggers heavy imports (Supabase, ADK). If that's prohibitive, fall back to a sub-process-style approach: `importlib.import_module` in a fresh sys.modules context, OR — simpler — just reload `app.routers.admin.chat` and read the literal default of `app.fast_api_app.SSE_MAX_DURATION_S` via a static text grep helper as documented in VALIDATION.md. Pick whichever pattern keeps the test under 5s. Document the choice in the test's docstring.

    3. `tests/unit/test_sse_max_duration.py` — add `test_env_override`:
       - `monkeypatch.setenv("SSE_MAX_DURATION_S", "999")` then reload both modules.
       - Assert both `SSE_MAX_DURATION_S` and `_SSE_MAX_DURATION_S` equal 999.
       - Currently FAILS for admin (hardcoded — env var ignored); PASSES for fast_api_app.
       - This test is the contract-binder: post-fix BOTH must read the env var.

    4. `tests/integration/test_sse_endpoint.py` (extend existing file) — add `test_long_stream_does_not_timeout`:
       - Build a minimal SSE generator following the existing `test_app` fixture pattern (lines 30-86).
       - Use `monkeypatch.setattr("time.monotonic", <fake_clock>)` to simulate elapsed time advancing in the loop. Run the generator until it would have exited at 300s under the old code.
       - Drive the fake clock to 500s (under 570s). Assert NO `data: {"error": "Stream timeout` chunk appears in the captured output.
       - Then drive the clock to 580s. Assert the timeout chunk DOES appear.
       - Currently FAILS — under the 300s default the timeout fires at 300s, not 570s.
       - **Implementation hint:** the existing `test_app` mocks the `runner` and uses `mock_event_generator`. Either (a) replicate the deadline loop inline in the test using the same `_SSE_MAX_DURATION_S` constant pattern (cleanest), or (b) import the actual generator factory if it exists. Refer to RESEARCH § Validation Architecture for the monkeypatch approach.

    5. `tests/integration/test_sse_endpoint.py` — add `test_heartbeat_during_slow_render`:
       - Same fixture pattern. Drive the fake clock so 12s passes with NO event in either queue.
       - Assert at least one `: keepalive\n\n` chunk is yielded (SSE comment, not `data:`).
       - Currently FAILS only if heartbeat is broken; PASSES today — this is a regression guard so any future refactor can't quietly remove it.
       - It's fine for this test to PASS at the start of Task 2 (it's a regression-prevention test, not strictly RED).

    6. `tests/integration/test_sse_endpoint.py` — add `test_heartbeat_suppressed_when_events_flow`:
       - Drive the generator with a real event arriving every 1s for 30s.
       - Assert ZERO `: keepalive\n\n` chunks are yielded (because `last_keepalive` resets on every event).
       - Same regression-guard intent as #5. Likely PASSES today; FAILS only if heartbeat reset path is broken.

    7. `tests/integration/test_sse_endpoint.py` — add `test_timeout_error_string_unchanged`:
       - When deadline IS hit, assert the emitted JSON parses to `{"error": "Stream timeout — please retry your request."}` — byte-exact, including the em-dash.
       - This test PASSES today; serves as a contract-lock so Task 2's edits don't accidentally drift the literal.

    **Also create** `.planning/phases/85-render-sse-timeout/deferred-items.md`:
       - Mirror the Phase 83 file's structure (read it first via the @-reference above).
       - Document the >570s render case as the SC4 deferred work:
         - **Trigger:** any render where `total_duration_seconds > 8` (Veo per-scene ~80s × 8 scenes = 640s).
         - **What goes wrong:** SSE deadline fires at 570s; the user sees `Stream timeout — please retry your request.`; the render continues server-side up to `DIRECTOR_TOTAL_TIMEOUT_SECONDS=1200` and the asset DOES land in the `generated-videos` bucket — but the user has lost the URL.
         - **Why deferred:** requires async job queue (Cloud Tasks or pub/sub) + persistent render-status storage + frontend polling/SSE-resume — multi-phase work, not a hotfix.
         - **Existing mitigations:** Phase 89 (Knowledge Vault Auto Sync) auto-ingests the bucket asset so it's still searchable; Sentry warning logs flag the case via the existing `logger.warning` in `app/fast_api_app.py:1973-1976`.

    **Order of operations inside this task (DO this sequentially):**
    1. Read `tests/integration/test_sse_endpoint.py` lines 1-100 to confirm the `test_app` fixture API and the `monkeypatch` pattern.
    2. Read `tests/unit/admin/test_admin_chat.py` lines 1-80 to find the import block and the existing test class/module style.
    3. Read `.planning/phases/83-document-upload-bypass/deferred-items.md` to mirror its tone/structure.
    4. Create `tests/unit/test_sse_max_duration.py` (NEW file — 2 tests, ~50-80 lines).
    5. Edit `tests/unit/admin/test_admin_chat.py` — add `test_sse_max_duration_constant` near the top of the test list (after imports). DO NOT modify any existing test.
    6. Edit `tests/integration/test_sse_endpoint.py` — append the 4 new tests at the end of the file. DO NOT modify any existing test.
    7. Create `.planning/phases/85-render-sse-timeout/deferred-items.md` (~40-60 lines, mirror Phase 83 structure).
    8. Run the focused suite to confirm RED state:
       ```
       uv run pytest tests/unit/admin/test_admin_chat.py::test_sse_max_duration_constant tests/unit/test_sse_max_duration.py tests/integration/test_sse_endpoint.py::test_long_stream_does_not_timeout tests/integration/test_sse_endpoint.py::test_heartbeat_during_slow_render tests/integration/test_sse_endpoint.py::test_heartbeat_suppressed_when_events_flow tests/integration/test_sse_endpoint.py::test_timeout_error_string_unchanged -x --no-header
       ```
       Expected: at least `test_sse_max_duration_constant`, `test_env_default`, `test_env_override` (admin reload path), and `test_long_stream_does_not_timeout` FAIL. The two heartbeat tests and the error-string test may PASS — that's fine; they're regression guards.
    9. Commit RED: `node "$HOME/.claude/get-shit-done/bin/gsd-tools.cjs" commit "test(85-01): add 7 failing tests for SSE timeout extension and SC4 deferred-items doc" --files tests/unit/test_sse_max_duration.py tests/unit/admin/test_admin_chat.py tests/integration/test_sse_endpoint.py .planning/phases/85-render-sse-timeout/deferred-items.md`

    **Use Pikar-AI conventions:** no `print()` (use `logging` if anything), no bare `except`, no mutable default arguments, ruff-clean. Imports sorted (ruff `I`).
  </behavior>
  <action>
    Execute the 9 sequential steps in <behavior>. The test file paths and test names are LOCKED — VALIDATION.md's per-task table references them by exact name; do not rename.

    Use the `Read` tool to inspect existing test fixture patterns before writing new tests. Do NOT spin up the real `app/fast_api_app.py` in tests — extend the existing minimal `test_app` fixture pattern (lines 30-86 of test_sse_endpoint.py).

    For module-reload tests, use `importlib.reload` after `monkeypatch.setenv` / `monkeypatch.delenv`. Reloading `app.fast_api_app` is heavy (Supabase imports); if it makes the test exceed 5s wall-clock, document the tradeoff in the test docstring and use a textual-default-extraction fallback (read the file's source via `inspect.getsource` and assert the default literal is `"570"`).

    DO NOT modify any source code in `app/` during this task — only tests and the deferred-items doc. The whole point of RED is that the source is unchanged.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/admin/test_admin_chat.py::test_sse_max_duration_constant tests/unit/test_sse_max_duration.py tests/integration/test_sse_endpoint.py -x --no-header 2>&1 | tail -40</automated>
    Expected output: at least 4 of the 7 new tests show `FAILED` (constant assertion, env default, env override on admin path, long-stream-no-timeout). Heartbeat regression guards may pass — acceptable. NO existing test in either file should regress (existing test count must equal pre-task count + 0 net failures from existing tests).

    Also verify file existence:
    - `ls .planning/phases/85-render-sse-timeout/deferred-items.md` returns the file
    - `ls tests/unit/test_sse_max_duration.py` returns the file
  </verify>
  <done>
    - `tests/unit/test_sse_max_duration.py` exists with `test_env_default` and `test_env_override`.
    - `tests/unit/admin/test_admin_chat.py` has a new `test_sse_max_duration_constant` test (no existing tests modified).
    - `tests/integration/test_sse_endpoint.py` has 4 new tests appended (no existing tests modified).
    - `.planning/phases/85-render-sse-timeout/deferred-items.md` exists and documents the SC4 >570s render case with the trigger conditions, why-deferred rationale, and existing mitigations (Phase 89 + Sentry log).
    - Focused pytest run shows ≥4 of the 7 new tests FAILING in exactly the predicted ways (this is the RED commit).
    - One git commit landed: `test(85-01): add 7 failing tests for SSE timeout extension and SC4 deferred-items doc`.
    - Source files in `app/` are UNCHANGED (verify with `git diff --name-only HEAD~1 HEAD -- app/` returns empty for app/).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: GREEN — patch both SSE generators + .env.example, drive tests to green, lint, finalize docs</name>
  <files>app/routers/admin/chat.py, app/fast_api_app.py, app/.env.example, .planning/STATE.md, .planning/ROADMAP.md, .planning/REQUIREMENTS.md, .planning/phases/85-render-sse-timeout/85-01-sse-timeout-extension-SUMMARY.md</files>
  <behavior>
    Apply the three minimal source edits, drive all 7 tests to GREEN, run `make lint`, then update planning docs and write the plan SUMMARY with the SC1 tradeoff prominently called out.

    **Edit 1 — `app/routers/admin/chat.py`:**
    - Add `import os` to the import block (line 17-21). Ruff `I` will sort it before `import asyncio`.
    - Replace lines 40-41 with:
      ```python
      # SSE stream maximum duration (seconds). Keep < Cloud Run's 600s
      # `--timeout` (Makefile:107, scripts/deploy-fast.ps1:124,
      # cloud-run-service.yaml:118, cloudrun.yaml:20) by a 30s safety margin
      # so SSE wins the race and the user always sees the friendly
      # 'Stream timeout' message instead of a raw 504. Override via the
      # SSE_MAX_DURATION_S env var; if you raise this >= 600, also raise the
      # Cloud Run --timeout in lockstep.
      _SSE_MAX_DURATION_S = int(os.getenv("SSE_MAX_DURATION_S", "570"))
      ```
    - DO NOT change line 356 (`deadline = time.monotonic() + _SSE_MAX_DURATION_S`) — it already references the constant.
    - DO NOT change the `Stream timeout — please retry your request.` literal at lines 364-366.
    - DO NOT touch the heartbeat code at lines 373-375.

    **Edit 2 — `app/fast_api_app.py`:**
    - Replace lines 1954-1956 with:
      ```python
      SSE_MAX_DURATION_S = int(
          os.getenv("SSE_MAX_DURATION_S", "570")
      )  # 9.5 min default; sized for Cloud Run --timeout 600 (30s safety margin)
      ```
    - The only literal change is `"300"` → `"570"` and the trailing comment.
    - `import os` is ALREADY present in this file (verify before editing — do not add a duplicate).
    - DO NOT change the `Stream timeout — please retry your request.` literal at line 1977.
    - DO NOT touch the heartbeat code at lines 1992-1994.

    **Edit 3 — `app/.env.example`:**
    - In the section `# STREAMING AND UPLOAD GUARDRAILS` (ends near line 92), append (do NOT remove or reorder existing vars):
      ```
      # SSE stream maximum duration in seconds. Default 570 = 30s safety
      # margin under Cloud Run's 600s --timeout. If raised >= 600, also raise
      # the Cloud Run --timeout in Makefile:107, cloud-run-service.yaml:118,
      # cloudrun.yaml:20, and scripts/deploy-fast.ps1:124 in lockstep,
      # otherwise the platform may close the connection mid-response (raw 504).
      SSE_MAX_DURATION_S=570
      ```
    - Verify with: `grep -n SSE_MAX_DURATION_S app/.env.example` → returns one line.

    **Drive tests to GREEN:**
    1. Run focused suite:
       ```
       uv run pytest tests/unit/admin/test_admin_chat.py::test_sse_max_duration_constant tests/unit/test_sse_max_duration.py tests/integration/test_sse_endpoint.py -x
       ```
       Expected: ALL 7 new tests PASS. If any fail, fix the test (not the source — the source is locked). Common stumbles: `importlib.reload` order, `monkeypatch.setenv` vs `monkeypatch.delenv` for the unset case.
    2. Run a broader sanity check (no need for full make test yet):
       ```
       uv run pytest tests/unit/admin/ tests/integration/test_sse_endpoint.py -x
       ```
       Expected: green. If a previously-passing test in `tests/unit/admin/test_admin_chat.py` now fails, your edit accidentally broke something — investigate.
    3. Run `make lint` and fix any new ruff/codespell/ty issues introduced by the three source edits. Likely zero — the edits are tiny — but `import os` ordering and the multi-line comment formatting can trip ruff `D` if you indent the comment block oddly.
    4. Run `make test` (full suite) — confirm no regression elsewhere. This may take 60-120s.

    **Update planning docs (after tests are green):**

    1. `.planning/STATE.md` — append a new frontmatter snapshot at the top (do NOT delete prior snapshots):
       ```yaml
       ---
       gsd_state_version: 1.0
       milestone: v10.0
       milestone_name: Platform Hardening & Quality
       status: planning
       stopped_at: Completed 85-render-sse-timeout 85-01-sse-timeout-extension-PLAN.md
       last_updated: "<ISO 8601 timestamp now>"
       last_activity: 2026-04-30 — Phase 85 SSE timeout raised to 570s in both admin/chat.py and fast_api_app.py via SSE_MAX_DURATION_S env var
       progress:
         total_phases: 16
         completed_phases: 10
         total_plans: 21
         completed_plans: 17
       ---
       ```
       Also append to the "Decisions" list under "Accumulated Context":
       ```
       - [Phase 85-render-sse-timeout]: SSE_MAX_DURATION_S env var raised from 300 → 570 (NOT 600 — 30s safety margin under Cloud Run's 600s --timeout so SSE wins the race and emits the friendly error instead of raw 504). Single env var governs both app/routers/admin/chat.py:_SSE_MAX_DURATION_S and app/fast_api_app.py:SSE_MAX_DURATION_S. SC1 literally said "≥ 600s"; we chose 570s — engineering tradeoff documented in plan SUMMARY and ROADMAP. SC4 (>570s renders) deferred to async-job-queue work, documented in deferred-items.md.
       ```
       Append to the velocity table inside Performance Metrics:
       ```
       | Phase 85-render-sse-timeout P01 | <minutes> | 2 tasks | 7 files |
       ```

    2. `.planning/ROADMAP.md` — Phase 85 section (currently at lines 120-133):
       - Change `**Plans:** 0 plans` → `**Plans:** 1/1 plans complete`
       - Replace the `- [ ] TBD (run /gsd:plan-phase 85 to break down)` line with:
         ```
         Plans:
         - [x] 85-01-sse-timeout-extension-PLAN.md — Raise SSE timeout from 300s → 570s in both admin/chat.py and fast_api_app.py via SSE_MAX_DURATION_S env var (HOTFIX-03)

         **SC1 Status:** Implemented at 570s, NOT the literal "≥ 600s" — engineering tradeoff for a 30s safety margin under Cloud Run's 600s --timeout (so SSE wins the race and the user sees the friendly error, not a raw 504). See 85-01-sse-timeout-extension-SUMMARY.md § "SC1 Literal-vs-Engineering Tradeoff" for full rationale.
         **SC4 Status:** Deferred to a future async-job-queue phase. See `.planning/phases/85-render-sse-timeout/deferred-items.md`.
         ```
       - Append to the bottom of the Progress table at the end of the file:
         ```
         | 85. Render SSE Timeout | v10.0-hotfix | 1/1 | Complete | 2026-04-30 |
         ```

    3. `.planning/REQUIREMENTS.md` — currently has no HOTFIX-03 entry (only v10.0 SEC/PERF/ARCH/AGT requirements). Add a new section AFTER "Future Requirements" or in a new "Hotfix Requirements" section header (mirror however Phase 83 / 84 handled this — read REQUIREMENTS.md if a hotfix block already exists, otherwise create one):
       ```markdown
       ## Hotfix Requirements

       Production-bug requirements added after v10.0 milestone planning.

       - [x] **HOTFIX-03** (Phase 85): SSE stream maximum duration extended from 300s → 570s in both `app/routers/admin/chat.py:_SSE_MAX_DURATION_S` and `app/fast_api_app.py:SSE_MAX_DURATION_S`, governed by single `SSE_MAX_DURATION_S` env var. 570s gives a 30s safety margin under Cloud Run's 600s --timeout. Long video renders (typical 7-9 min) now surface their final asset URL instead of dying mid-stream. SC4 (>570s renders) deferred to async-job-queue work.
       ```
       Also add to the traceability table at the bottom of the file:
       ```
       | HOTFIX-03 | Phase 85 | Complete |
       ```
       (Adjust the section heading if Phase 83/84's HOTFIX-01/02 are already in REQUIREMENTS.md; integrate consistently. If they're NOT in REQUIREMENTS.md, this is the first hotfix entry — that's fine, just create the section.)

    4. **CREATE** `.planning/phases/85-render-sse-timeout/85-01-sse-timeout-extension-SUMMARY.md`:
       Use the GSD template at `~/.claude/get-shit-done/templates/summary.md` as a starting structure. The SUMMARY MUST include a top-level prominent section titled exactly `## SC1 Literal-vs-Engineering Tradeoff` containing:
       - The literal SC1 wording from ROADMAP: *"`_SSE_MAX_DURATION_S` ... is raised from 300s to **at least 600s**."*
       - What we shipped: 570s (BOTH files) governed by a single `SSE_MAX_DURATION_S` env var.
       - **Why divergence:** Cloud Run's request `--timeout` is exactly 600s. SSE = 600 + Cloud Run = 600 → race condition where the platform may close the connection mid-final-yield, producing a raw 504 instead of the friendly error. 570 gives a 30s safety margin so SSE always wins.
       - **Risk if reverted to literal 600:** raw 504 on the borderline case; user sees a generic Cloud Run error page, frontend retry logic doesn't recognize it as a stream timeout.
       - **Lock condition:** if Cloud Run --timeout is ever raised (Makefile:107, cloud-run-service.yaml:118, cloudrun.yaml:20, scripts/deploy-fast.ps1:124), `SSE_MAX_DURATION_S` should be raised in lockstep, keeping the ~30s buffer.

       Other required SUMMARY sections (per template):
       - Objective recap
       - What changed (file table: chat.py, fast_api_app.py, .env.example, 7 tests, deferred-items.md)
       - Test results (focused run output)
       - SC verification (one row per SC1/SC2/SC3/SC4 with the test that verifies it)
       - Deviations / surprises
       - Manual UAT plan (the post-deploy 30s video render check from VALIDATION.md § Manual-Only Verifications) — flagged as a follow-up, NOT a CI gate
       - Next phase: Phase 86 (Document Generation Skills Exposure)

    **Final commit:**
    ```
    node "$HOME/.claude/get-shit-done/bin/gsd-tools.cjs" commit "feat(85-01): raise SSE timeout to 570s in both admin/chat.py and fast_api_app.py via SSE_MAX_DURATION_S env var (HOTFIX-03)" --files app/routers/admin/chat.py app/fast_api_app.py app/.env.example .planning/STATE.md .planning/ROADMAP.md .planning/REQUIREMENTS.md .planning/phases/85-render-sse-timeout/85-01-sse-timeout-extension-SUMMARY.md
    ```
  </behavior>
  <action>
    Execute the three source edits exactly as specified. Run the focused test suite to confirm GREEN. Run `make lint`. Run `make test` for the full-suite regression check. Update the four planning docs (STATE, ROADMAP, REQUIREMENTS, SUMMARY) with the SC1 tradeoff prominently noted in BOTH ROADMAP and SUMMARY. Commit once with the feat-scoped message.

    **CRITICAL constraints:**
    - The two `Stream timeout — please retry your request.` literals (admin/chat.py:364-366 and fast_api_app.py:1977) MUST remain byte-identical post-edit. Frontend match logic in `useBackgroundStream.ts` and `useAdminChat.ts` depends on the exact string.
    - The numeric value is `570` — not 600, not 600s, not "10 minutes". Do not round to a "nicer" number.
    - The env var name is `SSE_MAX_DURATION_S` (singular `S` suffix, matching the existing `fast_api_app.py` convention). Do not introduce a parallel name.
    - If `make lint` flags any pre-existing issue NOT introduced by these edits, leave it alone (out of scope) — only fix issues caused by the three source edits.
    - If `make test` shows pre-existing failures unrelated to SSE, document them in `deferred-items.md` (extend the file) but do not block plan completion on them.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/admin/test_admin_chat.py::test_sse_max_duration_constant tests/unit/test_sse_max_duration.py tests/integration/test_sse_endpoint.py -x --no-header 2>&1 | tail -20</automated>
    Expected: all 7 tests pass (`7 passed` in pytest summary).

    Additional verifications (run after the focused suite is green):
    - `grep -n "SSE_MAX_DURATION_S" app/routers/admin/chat.py app/fast_api_app.py app/.env.example` → at least 3 hits, all reading `os.getenv` or `SSE_MAX_DURATION_S=570`.
    - `grep -c "Stream timeout — please retry your request." app/routers/admin/chat.py app/fast_api_app.py` → returns 1 per file (literal preserved).
    - `make lint` exits 0.
    - `make test` exits 0 (or only fails on pre-existing-and-documented issues).
    - `git log --oneline -2` shows the GREEN commit on top of the RED commit from Task 1.
    - `.planning/phases/85-render-sse-timeout/85-01-sse-timeout-extension-SUMMARY.md` exists and contains the literal heading `## SC1 Literal-vs-Engineering Tradeoff`.
  </verify>
  <done>
    - `app/routers/admin/chat.py` line 41 reads `_SSE_MAX_DURATION_S = int(os.getenv("SSE_MAX_DURATION_S", "570"))` with the multi-line Cloud Run coupling comment above it.
    - `app/fast_api_app.py` line 1955 default is `"570"` with the updated `9.5 min default; sized for Cloud Run --timeout 600` comment.
    - `app/.env.example` contains `SSE_MAX_DURATION_S=570` with the operational comment.
    - All 7 tests in the focused suite are GREEN.
    - `make lint` and `make test` both exit 0 (or only with documented pre-existing failures).
    - `.planning/STATE.md` has a new frontmatter snapshot reflecting Phase 85 completion + a Decisions entry.
    - `.planning/ROADMAP.md` Phase 85 section shows `**Plans:** 1/1 plans complete` with the `[x]` plan entry, the SC1 tradeoff note, and the SC4 deferral note. The Progress table at the bottom has a "Phase 85 Complete 2026-04-30" row.
    - `.planning/REQUIREMENTS.md` has a HOTFIX-03 entry (in a Hotfix Requirements section, integrating with HOTFIX-01/02 if they exist) and a traceability row.
    - `.planning/phases/85-render-sse-timeout/85-01-sse-timeout-extension-SUMMARY.md` exists and prominently includes the `## SC1 Literal-vs-Engineering Tradeoff` section, plus all standard SUMMARY sections from the template.
    - One git commit landed: `feat(85-01): raise SSE timeout to 570s in both admin/chat.py and fast_api_app.py via SSE_MAX_DURATION_S env var (HOTFIX-03)`.
    - `git diff HEAD~2 HEAD -- frontend/` is empty (no frontend touched).
  </done>
</task>

</tasks>

<verification>
Plan-level success: HOTFIX-03 closes when:
- (SC1) Both `_SSE_MAX_DURATION_S` (admin) and `SSE_MAX_DURATION_S` (user) read `os.getenv("SSE_MAX_DURATION_S", "570")`. Verified by `test_sse_max_duration_constant` + `test_env_default` + `test_env_override`. **Note:** 570s, not literal "≥ 600s" — engineering tradeoff documented in SUMMARY and ROADMAP.
- (SC2) A simulated 7-min stream completes without timeout error. Verified by `test_long_stream_does_not_timeout` (mock-time integration). **Manual UAT** (`pwsh scripts/deploy-fast.ps1` then a real 30s video render through chat) is the user-deliverable confirmation, not a CI gate.
- (SC3) Heartbeat keepalive intact — fires when quiet, suppressed when events flow. Verified by `test_heartbeat_during_slow_render` + `test_heartbeat_suppressed_when_events_flow`.
- (SC4) >570s renders surface the unchanged `Stream timeout — please retry your request.` error string. Verified by `test_timeout_error_string_unchanged`. Documented as deferred work in `.planning/phases/85-render-sse-timeout/deferred-items.md`.

Linting + full test suite: `make lint && make test` both exit 0 (modulo pre-existing failures documented in deferred-items.md).
</verification>

<success_criteria>
1. Two source files patched: `app/routers/admin/chat.py:41` (now env-driven, default 570) and `app/fast_api_app.py:1954-1956` (default raised 300 → 570). Both read the SAME `SSE_MAX_DURATION_S` env var.
2. `app/.env.example` documents `SSE_MAX_DURATION_S=570` with the Cloud Run --timeout coupling comment.
3. All 7 new tests are GREEN: 1 in `tests/unit/admin/test_admin_chat.py`, 2 in `tests/unit/test_sse_max_duration.py` (NEW file), 4 in `tests/integration/test_sse_endpoint.py`.
4. `make lint` clean. `make test` clean (or pre-existing failures only).
5. `.planning/phases/85-render-sse-timeout/deferred-items.md` exists and documents the SC4 case (>570s renders need async job queue).
6. `.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md` updated to reflect HOTFIX-03 close.
7. Plan SUMMARY exists at `.planning/phases/85-render-sse-timeout/85-01-sse-timeout-extension-SUMMARY.md` with a prominent `## SC1 Literal-vs-Engineering Tradeoff` section explaining the 570 vs 600 decision.
8. Two git commits: `test(85-01): ...` (RED) followed by `feat(85-01): ...` (GREEN).
9. Frontend is untouched: `git diff HEAD~2 HEAD -- frontend/` returns empty.
</success_criteria>

<output>
After completion, create `.planning/phases/85-render-sse-timeout/85-01-sse-timeout-extension-SUMMARY.md` containing:
- Objective recap (HOTFIX-03)
- **`## SC1 Literal-vs-Engineering Tradeoff` section (PROMINENT)** — full rationale for 570 vs 600
- File-change table (3 source files, 7 tests, deferred-items.md)
- Test results (focused suite output, lint, full make test)
- SC verification table (one row per SC1/SC2/SC3/SC4 → test name)
- Deviations / surprises
- Manual UAT plan (the post-deploy 30s video render — follow-up action, not a CI gate)
- Next phase: Phase 86 (Document Generation Skills Exposure)
</output>

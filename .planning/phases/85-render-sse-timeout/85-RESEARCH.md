# Phase 85: Render SSE Timeout — Research

**Researched:** 2026-04-30
**Domain:** FastAPI SSE streaming + Cloud Run request timeout coordination
**Confidence:** HIGH

---

## Phase Summary

Long video renders (e.g. a 30s clip taking 7-9 min) trip a 300s SSE wall-clock cap and the user sees `Stream timeout — please retry your request.` while the render continues server-side. The fix is to raise the cap to fit inside Cloud Run's 600s request ceiling — but the success criterion as written points at `app/routers/admin/chat.py` (admin-only), while the actual user-facing render path is `app/fast_api_app.py:1954` (regular `/a2a/app/run_sse`). **Both files contain the identical timeout pattern**; planner must decide whether to fix one or both.

**Primary recommendation:** Raise BOTH timeouts to **570s** (a 30s safety margin under Cloud Run's 600s `--timeout`). Make `_SSE_MAX_DURATION_S` in `app/routers/admin/chat.py` read from the same `SSE_MAX_DURATION_S` env var that `app/fast_api_app.py:1954-1955` already uses, with the default raised from `300` → `570`. Single source of truth, single env override, both endpoints fixed.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HOTFIX-03 | Long video renders complete and surface results to users by extending the chat SSE stream timeout. Renders that finish within Cloud Run's 600s request timeout should NOT trigger "Stream timeout — please retry your request." | Cloud Run timeout confirmed 600s (`Makefile:107`, `cloud-run-service.yaml:118`, `cloudrun.yaml:20`, `scripts/deploy-fast.ps1:124`). Two SSE generators identified with the bug: admin chat (`app/routers/admin/chat.py:41,356,365`) and main user chat (`app/fast_api_app.py:1954-1977`). Heartbeat (`: keepalive\n\n`) verified intact in both, every 10s of inactivity. |

---

## Current Implementation

### Two SSE generators with the same timeout bug

**1. Admin chat (named explicitly in SC1):** `app/routers/admin/chat.py`
- `Line 41`: `_SSE_MAX_DURATION_S = 300`  *(hardcoded constant, no env override)*
- `Line 356`: `deadline = time.monotonic() + _SSE_MAX_DURATION_S`
- `Line 364-366`: deadline check emits `{'error': 'Stream timeout — please retry your request.'}` and breaks
- `Line 369`: `asyncio.wait_for(adk_event_queue.get(), timeout=0.5)` → poll cycle
- `Line 373-375`: heartbeat `: keepalive\n\n` every 10s of inactivity (`time.monotonic() - last_keepalive >= 10`)
- Endpoint: `POST /admin/chat` → drives `AdminAgent` only (`app/agents/admin/agent.py`). **AdminAgent has NO video tools** (verified — its tools are analytics, billing, config, governance, health, integrations, knowledge, monitoring, users). So this constant being 300s does NOT cause the user-facing video timeout described in the goal text.

**2. User chat (NOT named in SC1, but where the actual bug lives):** `app/fast_api_app.py`
- `Line 1954-1956`: `SSE_MAX_DURATION_S = int(os.getenv("SSE_MAX_DURATION_S", "300"))  # 5 min default`  *(env-overridable, but default 300)*
- `Line 1961`: `stream_deadline = time.monotonic() + SSE_MAX_DURATION_S`
- `Line 1972-1978`: deadline check, identical error string `'Stream timeout — please retry your request.'`
- `Line 1992-1994`: heartbeat `: keepalive\n\n` every 10s
- `Line 1980-1985`: dual-queue race (`adk_event_queue` + `progress_queue`) via `asyncio.wait` with 0.5s timeout
- Endpoint: `POST /a2a/app/run_sse` → drives Executive Agent → routes to Content/Marketing → calls `app/agents/tools/media.py` → `app/services/director_service.py` → `remotion_render_service.render_programmatic_video` (in `asyncio.to_thread`). **THIS is the path long video renders take.**

### Frontend SSE consumer

**Regular user (video path):** `frontend/src/hooks/useBackgroundStream.ts:262`
- Uses `@microsoft/fetch-event-source` (`fetchEventSource`) hitting `${API_URL}/a2a/app/run_sse`
- `Line 229-230`: `MAX_RETRIES = 3`, `RETRY_DELAYS = [1000, 2000, 4000]` (exponential backoff)
- `Line 268`: relies on `AbortController` signal — no client-side fetch timeout (the SSE keepalive prevents browser/proxy idle disconnect)
- On `Stream timeout` server error event: `parseResult.errorText` → renders `Error: Stream timeout — please retry your request.` to the user. **No client-side reconnect attempt** because the server cleanly closed the stream — the retry loop only reactivates on connection-drop errors, not on a `data: {error}` event.

**Admin user (no video path):** `frontend/src/hooks/useAdminChat.ts:227,378`
- Same `fetchEventSource` pattern, hits `/admin/chat`
- Renders the error string the same way

### Cloud Run deployment timeout

Verified across all four deploy configs (HIGH confidence):
- `Makefile:107` → `--timeout 600`
- `scripts/deploy-fast.ps1:124` → `--timeout 600`
- `cloud-run-service.yaml:118` → `timeoutSeconds: 600`
- `cloudrun.yaml:20` → `timeoutSeconds: 600`

Cloud Run's hard ceiling is 3600s, but the deploy is currently pinned at the lower 600s. **Anything above 600s in app code is wasted — Cloud Run will kill the request first.**

### Downstream render budget (the trap)

`app/services/director_service.py:248-252`:
- `DIRECTOR_SCENE_TIMEOUT_SECONDS = 240` (per-scene)
- `DIRECTOR_TOTAL_TIMEOUT_SECONDS = 1200` (total — **20 min**)

`app/services/remotion_render_service.py:30,38`:
- `REMOTION_RENDER_TIMEOUT = 120` (per render attempt)
- `FFMPEG_RENDER_TIMEOUT = 180`
- `REMOTION_RENDER_RETRY_ON_TIMEOUT = 1` (retries enabled)

The director's TOTAL budget (1200s) is configured to allow renders that already exceed Cloud Run's 600s wall-clock limit. The 7-9 min user complaint maps to ~420-540s — comfortably under 600s but well above the 300s SSE cap. Raising SSE to 570s closes the reported gap. **Going beyond 600s requires Cloud Run timeout increase (separate decision) OR the deferred async-job-queue per SC4.**

### Heartbeat keepalive (SC3 verification)

Both SSE generators send `: keepalive\n\n` (SSE comment per W3C spec — clients ignore it but proxies treat it as activity). Confirmed:
- Both wake every 0.5s (no idle blocking)
- Both reset `last_keepalive = time.monotonic()` on EITHER a real event OR a keepalive emit
- Cadence: 10s of no-event → emit keepalive → reset timer
- Headers `Cache-Control: no-cache, no-transform`, `X-Accel-Buffering: no` already set in `app/routers/admin/chat.py:459-463` (correct — disables proxy buffering on the admin endpoint)
- Cloud Run frontend has a documented **no-traffic-during-15min** idle disconnect; 10s heartbeat is well under this.

**The keepalive logic is independent of `_SSE_MAX_DURATION_S`** — raising the deadline does not touch the heartbeat path. SC3 holds for free.

---

## Recommended Fix

### Pick a value: **570s**

| Candidate | Rationale | Verdict |
|-----------|-----------|---------|
| 300 (current) | Status quo | ❌ The bug |
| 600 | Matches Cloud Run timeout exactly | ❌ Race: SSE deadline + Cloud Run ceiling fire near-simultaneously; user gets either the friendly app error or a raw Cloud Run 504 depending on which lands first |
| **570** | 30s safety margin under Cloud Run's 600s. SSE always wins the race; user always sees the deliberate `Stream timeout` message, never a raw 504. | ✅ **Recommended** |
| 900 / 1800 | Requires raising Cloud Run `--timeout` first; out of scope for hotfix | ❌ Defer to async-job-queue work |

The 30s buffer covers: (a) the `0.5s` queue poll cycle, (b) any final `await runner_task` cleanup, (c) the audit log + persist agent message (`_persist_message` is sync Supabase — could take 1-3s on cold connections per the `project_cloud_run_startup_probe.md` memory), (d) network egress for the final SSE chunks before the connection closes.

### Architectural choice: single source of truth

**Current state:** Two timeouts, two patterns:
- `app/routers/admin/chat.py:41` → hardcoded `300`
- `app/fast_api_app.py:1954-1955` → env-overridable, default `300`

**Recommended:** Make `_SSE_MAX_DURATION_S` read the SAME env var, with the SAME new default. Patch:

```python
# app/routers/admin/chat.py
import os
# SSE stream maximum duration (seconds). Keep < Cloud Run's 600s --timeout
# (deploy: Makefile:107) by a 30s safety margin so SSE wins the race and
# the user always sees the friendly 'Stream timeout' message instead of a
# raw 504. Override via SSE_MAX_DURATION_S env var.
_SSE_MAX_DURATION_S = int(os.getenv("SSE_MAX_DURATION_S", "570"))
```

```python
# app/fast_api_app.py:1954-1956 — change the default literal only
SSE_MAX_DURATION_S = int(
    os.getenv("SSE_MAX_DURATION_S", "570")
)  # 9.5 min default; sized for Cloud Run --timeout 600
```

Two minimal edits. One env var. One default. Both endpoints fixed in lockstep.

### Other timeouts that need synchronizing (priority order)

1. **`SSE_MAX_DURATION_S` env override (operations).** If anyone sets `SSE_MAX_DURATION_S=600` (or higher) in `cloud-run-service.yaml` or in the deploy command, they must ALSO bump `--timeout`. Document this co-dependency in the constant's docstring AND in `app/.env.example` (currently the var is not even mentioned in `.env.example` lines 84-92 — only the connection-limit vars are). **Action:** add `SSE_MAX_DURATION_S=570` line to `app/.env.example` § STREAMING AND UPLOAD GUARDRAILS.

2. **Director total timeout (`DIRECTOR_TOTAL_TIMEOUT_SECONDS=1200`).** This is **already higher** than even the proposed 570s SSE cap. Renders that take 600-1200s will be killed by Cloud Run before the director gives up. This is the SC4 case — keep as-is, document deferral.

3. **Frontend `useBackgroundStream` retry loop.** `MAX_RETRIES=3` with `[1s, 2s, 4s]` backoff, only triggers on connection-drop. A `Stream timeout` data event is treated as a final error, not a retryable drop. **No change needed** — current behavior is correct (don't auto-retry a deliberate timeout).

4. **Cloud Run startup probe.** Per `project_cloud_run_startup_probe.md`, the Makefile still uses `/health/startup` (sync Supabase, can hang 10-30s on cold containers) — `Makefile:108`. **Out of scope for this phase** but worth flagging: the SSE-generator's first call (`runner.run_async`) on a cold container may consume part of the 570s budget for cold-start and Supabase init. Memory says `scripts/deploy-fast.ps1:125` already correctly uses `/health/live`. Don't touch the Makefile in this phase, but mention in deferred-items if cold-start latency becomes the limiting factor.

5. **Heartbeat interval (10s).** Already correct. Cloud Run idle-disconnect threshold is far higher (15 min). No change.

---

## Files Involved

### Must modify

| File | Lines | Change |
|------|-------|--------|
| `app/routers/admin/chat.py` | 41 (also `import os` if not present — it isn't, line 17 imports asyncio/json/logging/time only) | Convert hardcoded `300` to env-driven `int(os.getenv("SSE_MAX_DURATION_S", "570"))` + update docstring |
| `app/fast_api_app.py` | 1955 | Change literal `"300"` → `"570"` (env-driven path already exists) |
| `app/.env.example` | After line 92 (in STREAMING AND UPLOAD GUARDRAILS block) | Add `SSE_MAX_DURATION_S=570` with comment explaining Cloud Run --timeout coupling |

### Must read (no changes)

| File | Why |
|------|-----|
| `Makefile` | Line 107 `--timeout 600` — confirms Cloud Run ceiling, do NOT change in this phase |
| `cloud-run-service.yaml` | Line 118 — same |
| `cloudrun.yaml` | Line 20 — same |
| `scripts/deploy-fast.ps1` | Line 124 — same |
| `app/services/director_service.py` | Lines 248-252 — confirms downstream budget; informs SC4 deferred-work |
| `app/services/remotion_render_service.py` | Lines 30, 38 — render timeouts are independent of SSE cap |
| `frontend/src/hooks/useBackgroundStream.ts` | Lines 229-230, 262 — confirms no client-side reconnect on data error events; no change needed |

### Tests (must touch)

| File | Status | What |
|------|--------|------|
| `tests/unit/admin/test_admin_chat.py` | exists | Add `test_sse_max_duration_default_value` — assert `_SSE_MAX_DURATION_S >= 600` reads correctly when env unset (after fix); plus an env-override sanity test |
| `tests/integration/test_sse_endpoint.py` | exists | Add `test_sse_deadline_extended_to_570s` — fake-time test (monotonic patched) that confirms a stream lasting 500s does NOT emit timeout, but a stream lasting 580s does. Use existing test_app fixture pattern. |
| `tests/unit/test_sse_max_duration.py` | NEW (Wave 0) | Lightweight: import `app.fast_api_app` module, assert env-default reads `570`. Mirror in `test_admin_chat.py` for the admin constant. |

No changes needed to: `frontend/src/hooks/useBackgroundStream.ts`, `useAdminChat.ts` (consumer is already keepalive-tolerant; only the server max changes).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Pytest 8.x (backend, per `.planning/config.json` workflow.preferences.testing) |
| Config file | `pyproject.toml` (project-standard) |
| Quick run command | `uv run pytest tests/unit/admin/test_admin_chat.py tests/unit/test_sse_max_duration.py -x` |
| Full suite command | `make test` |

### Phase Requirements → Test Map

| Req ID | Behavior (success criterion) | Test Type | Automated Command | File Exists? |
|--------|-----------------------------|-----------|-------------------|-------------|
| HOTFIX-03 SC1 | `_SSE_MAX_DURATION_S` (admin) and env-default (user) are both ≥ 600 (we use 570 — SC1 says ≥ 600 but research recommends 570 for the safety margin; **planner must reconcile this with stakeholder before locking — see Open Questions Q1**) | unit | `uv run pytest tests/unit/admin/test_admin_chat.py::test_sse_max_duration_constant -x` | ❌ Wave 0 (NEW test in existing file) |
| HOTFIX-03 SC1 (env path) | `SSE_MAX_DURATION_S` env override propagates to user SSE generator | unit | `uv run pytest tests/unit/test_sse_max_duration.py::test_env_override -x` | ❌ Wave 0 (new file) |
| HOTFIX-03 SC2 | A simulated 7-min stream completes without timeout error | integration (mock-time) | `uv run pytest tests/integration/test_sse_endpoint.py::test_long_stream_does_not_timeout -x` | ❌ Wave 0 (NEW test in existing file, monkeypatch `time.monotonic`) |
| HOTFIX-03 SC3 | Heartbeat `: keepalive\n\n` is emitted at least once during a 12s no-event window | integration | `uv run pytest tests/integration/test_sse_endpoint.py::test_heartbeat_during_slow_render -x` | ❌ Wave 0 (NEW test, count `: keepalive` in stream) |
| HOTFIX-03 SC3 | Heartbeat is NOT emitted when events arrive faster than 10s | integration | `uv run pytest tests/integration/test_sse_endpoint.py::test_heartbeat_suppressed_when_events_flow -x` | ❌ Wave 0 (NEW test) |
| HOTFIX-03 SC4 | When deadline hits, error string is unchanged: `'Stream timeout — please retry your request.'` | unit | `uv run pytest tests/integration/test_sse_endpoint.py::test_timeout_error_string_unchanged -x` | ❌ Wave 0 (NEW test) |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/unit/admin/test_admin_chat.py tests/unit/test_sse_max_duration.py tests/integration/test_sse_endpoint.py -x` (~5-10s)
- **Per wave merge:** `make test`
- **Phase gate:** Full suite green before `/gsd:verify-work`; manual UAT performed against deployed Cloud Run

### Wave 0 Gaps

- [ ] `tests/unit/test_sse_max_duration.py` — new file. Asserts `app.fast_api_app.SSE_MAX_DURATION_S` (read at module init via `os.getenv`) defaults to 570 when env unset; asserts override path. Tiny — likely one fixture, two tests.
- [ ] `tests/unit/admin/test_admin_chat.py` extension — add `test_sse_max_duration_constant` that imports `_SSE_MAX_DURATION_S` and asserts `>= 570` (and env-override path).
- [ ] `tests/integration/test_sse_endpoint.py` extension — add 4 new tests:
  - long-stream-no-timeout (monkeypatch `time.monotonic`)
  - heartbeat-during-quiet-window
  - heartbeat-suppressed-when-events-flow
  - timeout-error-string-stable
- [ ] No new framework or config files needed. `pytest`, `pytest-asyncio`, `httpx.AsyncClient`, `unittest.mock` already in use throughout `tests/`.

### Manual-Only Verifications (UAT)

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 30s video render completes end-to-end through SSE | HOTFIX-03 SC2 (full path) | Real Vertex AI Veo + real Remotion + real Cloud Run; cannot mock the render's 7-9 min wall-clock | (1) Deploy via `pwsh scripts/deploy-fast.ps1`. (2) Open https://pikar-ai.com chat as a logged-in user. (3) Prompt: "Render me a 30-second product demo video for an AI scheduling app." (4) Wait. Watch chat panel for streaming events + workspace for video preview. (5) **Expected:** within 7-12 min, the asset URL streams in and the video plays. **No `Stream timeout` error.** |
| Cloud Run logs confirm SSE close path | HOTFIX-03 SC2 ops | Cloud Run telemetry only available post-deploy | After UAT above, in Cloud Run logs filter on `session_id`. Expected log sequence: `Calling runner.run_async` → multiple `progress` events → `Stream finished normally` → `interaction_id`. Pre-fix pattern: `SSE stream hit max duration (300s), closing` |
| Render that legitimately exceeds 600s (SC4 deferred case) | HOTFIX-03 SC4 | Behavior must remain unchanged on the long-tail | Trigger a render that pushes past 570s (e.g. 8-scene video). **Expected:** server emits `Stream timeout` data event; user sees `Error: Stream timeout — please retry your request.` Render may still complete server-side (Director total budget is 1200s) but the user has lost the asset URL. **This is the documented deferred case.** Sentry/logs should capture the orphan render. |

---

## Open Questions / Risks

### Q1 — SC1 says "at least 600s" but recommendation is 570s (HIGH IMPACT)

The success criterion verbatim: *"`_SSE_MAX_DURATION_S` ... is raised from 300s to at least 600s."*

But Cloud Run's request timeout is exactly 600s. If SSE deadline = 600s and Cloud Run = 600s, the platform may close the connection while the SSE generator is mid-final-yield, producing a raw 504 instead of the friendly app error. **570s is strictly better** for the user-facing experience.

**Recommendation:** Planner should propose 570s with the safety-margin justification. If stakeholder insists on ≥600s verbatim, take the literal path (600s) and add a deferred-items note acknowledging the race. Both are defensible; 570s is the engineering call.

### Q2 — Goal text vs SC1 file path mismatch (HIGH IMPACT)

- **Goal text:** "Long video renders complete and surface results to **users**" — implies regular `/a2a/app/run_sse` (`fast_api_app.py:1954`).
- **SC1:** Names `app/routers/admin/chat.py:_SSE_MAX_DURATION_S` — admin only.

**The admin chat does NOT render videos.** Patching only `chat.py` (literal SC1) does not satisfy the goal text. Patching both is the only way to satisfy both. This RESEARCH recommends **both**, with the env-driven single-source pattern.

**Open for planner:** Decide whether to (a) patch both, or (b) patch only `chat.py` per literal SC1 and explicitly defer `fast_api_app.py` to a separate phase. Recommend (a) — the change is two literals + one env-example line, the risk is identical, and "users" is named in the goal.

### Q3 — Sentry/observability for orphaned long renders (SC4)

When a render exceeds 570s, the SSE closes but the director thread may keep working until 1200s. Three sub-questions:
- Does the rendered MP4 still get uploaded to `generated-videos` bucket? **Yes** — `director_service.py:430-435` runs in `asyncio.to_thread`; the SSE-generator's `runner_task.cancel()` does NOT abort the in-flight thread. Asset is produced but URL never reaches user.
- Does Phase 89 (Knowledge Vault Auto Sync) catch these orphans? Yes per Phase 89 SC1 — vault auto-ingests on bucket upload regardless of SSE state. **Mitigation already in roadmap.**
- Should we emit a Sentry breadcrumb on deadline-hit? Recommend yes (`logger.warning` already exists at `fast_api_app.py:1973-1976`; Sentry SDK auto-captures warnings if configured). No action needed — existing log path is sufficient.

### Q4 — Memory leaks from longer-held SSE streams (LOW)

Each SSE connection holds: one `asyncio.Queue`, one `asyncio.Event`, one running `Runner` task, accumulator lists. At 570s vs 300s, peak concurrent streams ~doubles. With `SSE_MAX_CONNECTIONS_PER_USER=3` and `SSE_MAX_TOTAL_CONNECTIONS=500` (`app/.env.example:88-92`), the 500-connection ceiling is the binding constraint. At ~500MB/replica with `min-instances=2`, head-room is fine. **No code change required.** Re-verify if traffic grows.

### Q5 — Cost (LOW)

Cloud Run bills CPU+memory by active request seconds. Doubling the 95th-percentile SSE duration ~doubles cost on slow renders. With `--no-cpu-throttling` (Makefile:102) the meter runs full-rate the whole time. Estimate: a slow render that previously cost ~$0.001 per request now costs ~$0.002. Negligible against the user-experience win, but document for the FinOps team.

### Q6 — Frontend race on disconnect (LOW)

`useBackgroundStream.ts:229-230` retries on connection drops 3 times with exponential backoff up to 4s. If the network drops at 569s and the SSE has 1s left server-side, the retry hits a fresh 570s deadline on the new connection — but the underlying ADK runner is already complete. This is the same race as today, just shifted. No new failure mode.

---

## Implementation Notes

### Order of operations

1. Add `import os` to `app/routers/admin/chat.py` (currently absent — `line 17-21` imports `asyncio, json, logging, time, AsyncGenerator`)
2. Patch `_SSE_MAX_DURATION_S = 300` → env-driven default 570 (one line + docstring)
3. Patch `SSE_MAX_DURATION_S` default literal in `fast_api_app.py:1955` (`"300"` → `"570"`)
4. Append `SSE_MAX_DURATION_S=570` to `app/.env.example` after line 92, with explanatory comment
5. Add new tests (Wave 0): one test for the constant, four for the integration path
6. Run `make test` — full suite green
7. Manual UAT against deployed Cloud Run
8. Update Phase 85 `RETROSPECTIVE.md` if anything surprised

### Gotchas

- **`import os` is missing** in `app/routers/admin/chat.py`. Plan must add it. Linter (ruff `I` rule) will sort it correctly.
- **`SSE_MAX_DURATION_S` is module-level** in both files — it's read once at import time, not per-request. Tests must use `monkeypatch.setenv` BEFORE importing the module, OR must directly patch the module attribute. The existing pattern in `tests/integration/test_sse_endpoint.py` builds a separate test FastAPI app, sidestepping the issue; new tests can follow that pattern.
- **Two error-string emit sites use the SAME literal** (`Stream timeout — please retry your request.`). Don't accidentally change this — frontend match logic is fragile. Both sites must remain string-equal post-fix.
- **The `_admin_sse_generator` does `await runner_task` AFTER `break`** (`chat.py:377`). If break fires from the deadline, the runner is still running; `await` waits for it; only then does `finally` run. This is correct but means the deadline-trigger path actually waits up to the runner's natural termination before closing — typically fast, but a hung runner could overrun the 30s safety margin. **Consider:** add a final `asyncio.wait_for(runner_task, timeout=5.0)` in the post-break path to bound cleanup. Out of scope for the literal hotfix but worth flagging.
- **`ruff D` (docstring rule)** — the `_SSE_MAX_DURATION_S` line currently has a one-line `# SSE stream maximum duration (seconds)` comment. The expanded docstring should keep it as a comment (constants don't need docstrings per Google style), but the rationale comment must include the Cloud Run coupling explicitly.
- **Per-task verification commands must be `< 30s`** (Nyquist sampling). The new integration tests using monkeypatched `time.monotonic` should run in milliseconds — no real waits.

### Why this is a one-task plan, not a multi-wave plan

- Three file edits, ~10 LOC total
- One env-example update
- Five small tests (mostly extensions of existing files)
- No data migration, no config schema change, no new dependency

Recommend **Plan 01** as the only plan, single wave. Estimated 7-12 minutes per the v9.0/v10.0 baseline averages in `STATE.md`.

---

## SC4 Deferred-Work Documentation Plan

SC4 verbatim: *"If render still exceeds 600s, the error is unchanged but **documented as a known case requiring async-job-queue work** (deferred to a later phase)."*

Two recommended landing spots — pick one (planner discretion):

### Option A (RECOMMENDED): `.planning/phases/85-render-sse-timeout/deferred-items.md`

Mirror the Phase 83 pattern (`.planning/phases/83-document-upload-bypass/deferred-items.md`). Single markdown file, in-tree with the phase, lifts cleanly into the next milestone's RETROSPECTIVE roll-up. Document:
- The 600-1200s render case (renders that legitimately exceed Cloud Run timeout)
- Why we didn't fix it now: requires async job queue (Cloud Tasks or pub/sub) + persistent render-status storage + frontend polling/SSE-resume — multi-phase work
- Trigger conditions: any render where `total_duration_seconds > 8` (typical Veo per-scene cost ~80s × 8 scenes = 640s)
- Mitigations already in place: Director total budget = 1200s (asset still produced); Phase 89 vault auto-sync (asset still searchable); Sentry warning logs flag the case

### Option B: New entry in `.planning/REQUIREMENTS.md` § Future Requirements

Add a `PERF-F04: Async job queue for long-running renders (>10 min)` line. Less work, but loses the in-context narrative.

### Option C (NOT recommended): TODO comment in `app/services/director_service.py`

Code TODOs decay — no one greps `# TODO` during planning. Skip.

**Recommendation:** Option A. Plan should create `.planning/phases/85-render-sse-timeout/deferred-items.md` as the final task of Plan 01, using the Phase 83 file as the template.

---

## Sources

### Primary (HIGH confidence — direct file inspection)

- `app/routers/admin/chat.py` (full read, all 557 lines) — admin SSE generator
- `app/fast_api_app.py:1600-2030` — user SSE generator (`run_sse` endpoint)
- `app/services/director_service.py:240-460` — director timeouts and render dispatch
- `app/services/remotion_render_service.py:25-55` — render-level timeouts
- `frontend/src/hooks/useBackgroundStream.ts:225-340` — frontend SSE retry behavior
- `frontend/src/hooks/useAdminChat.ts:80-380` — admin SSE consumer
- `Makefile:90-118` — Cloud Run deploy timeout
- `scripts/deploy-fast.ps1:100-140` — alt deploy path with same timeout
- `cloud-run-service.yaml:115-122`, `cloudrun.yaml:18-25` — knative service yaml timeouts
- `app/.env.example:75-100` — current env-var coverage (note: `SSE_MAX_DURATION_S` not yet documented here)
- `tests/integration/test_sse_endpoint.py:1-60` — existing test infrastructure

### Secondary (HIGH confidence — project memory)

- `project_director_render_visibility.md` — render thread now wraps in try/except (already shipped 2026-04-29)
- `project_cloud_run_startup_probe.md` — `/health/live` vs `/health/startup` cold-container behavior
- `.planning/STATE.md` — Phase 84 just completed, Phase 85 ready to plan
- `.planning/ROADMAP.md:120-133` — Phase 85 entry, success criteria
- `.planning/phases/84-voice-gate-deadlock-fix/84-VALIDATION.md` — VALIDATION.md template pattern
- `.planning/phases/83-document-upload-bypass/deferred-items.md` — deferred-items.md template pattern

### Cloud Run docs (MEDIUM confidence — claims align with project memory and deploy configs)

- Cloud Run request timeout maximum: 3600s (60 min); default and current deploy: 600s
- Cloud Run idle disconnect: ~15 min for streamed responses with no activity (heartbeat at 10s is well under)
- `--no-cpu-throttling`: keeps full CPU during request, including idle SSE wait time

*No external WebFetch/WebSearch needed — all critical claims verified by direct file inspection.*

---

## Metadata

**Confidence breakdown:**
- Current implementation: HIGH — every cited line read directly
- Cloud Run timeout = 600s: HIGH — confirmed in 4 separate deploy configs
- Two-file scope (admin + user): HIGH — direct inspection of `_SSE_MAX_DURATION_S` and `SSE_MAX_DURATION_S` references via Grep
- Heartbeat intact (SC3): HIGH — code inspection of both generators
- Recommended value 570s: MEDIUM-HIGH — engineering judgement on the safety margin; SC1 specifies "at least 600s" verbatim, see Q1
- Downstream director budget interaction: HIGH — direct read of `director_service.py:248-252`
- SC4 deferred-work landing: MEDIUM — three viable options, recommendation based on Phase 83 precedent

**Research date:** 2026-04-30
**Valid until:** 2026-05-30 (30 days — stable infrastructure code, slow-moving)

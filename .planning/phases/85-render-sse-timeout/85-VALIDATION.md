---
phase: 85
slug: render-sse-timeout
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-30
sc1_value: 570
sc1_value_rationale: "User-decision: 570s gives a 30s safety margin under Cloud Run's 600s timeout so the SSE always wins the race and surfaces the friendly 'Stream timeout' error. Technically lower than SC1's literal 'at least 600s' wording — engineering tradeoff documented in plan SUMMARY and ROADMAP."
sc1_scope: both_files
sc1_scope_rationale: "User-decision: patch admin/chat.py AND fast_api_app.py. The goal text says 'users' — fast_api_app.py is the user video path. Single env var SSE_MAX_DURATION_S read by both files."
---

# Phase 85 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source of truth: `85-RESEARCH.md` § Validation Architecture.
> **User decisions locked:** value = 570s, scope = both files via env var.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Pytest 8.x (backend, per `.planning/config.json`) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/unit/admin/test_admin_chat.py tests/unit/test_sse_max_duration.py tests/integration/test_sse_endpoint.py -x` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~5–10s focused · ~60–120s full suite |

---

## Sampling Rate

- **After every task commit:** `uv run pytest tests/unit/admin/test_admin_chat.py tests/unit/test_sse_max_duration.py tests/integration/test_sse_endpoint.py -x`
- **After every plan wave:** `make test`
- **Before `/gsd:verify-work`:** Full suite green + manual UAT (30s video render through deployed Cloud Run) + log assertion
- **Max feedback latency:** ~10 seconds for the focused run

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 85-01-01 | 01 | 0 | HOTFIX-03 SC1 (admin) | unit | `uv run pytest tests/unit/admin/test_admin_chat.py::test_sse_max_duration_constant -x` | ✅ extend | ⬜ pending |
| 85-01-02 | 01 | 0 | HOTFIX-03 SC1 (env propagation) | unit | `uv run pytest tests/unit/test_sse_max_duration.py::test_env_default -x` | ❌ W0 | ⬜ pending |
| 85-01-03 | 01 | 0 | HOTFIX-03 SC1 (env override) | unit | `uv run pytest tests/unit/test_sse_max_duration.py::test_env_override -x` | ❌ W0 | ⬜ pending |
| 85-01-04 | 01 | 0 | HOTFIX-03 SC2 (long stream) | integration | `uv run pytest tests/integration/test_sse_endpoint.py::test_long_stream_does_not_timeout -x` | ✅ extend | ⬜ pending |
| 85-01-05 | 01 | 0 | HOTFIX-03 SC3 (heartbeat fires) | integration | `uv run pytest tests/integration/test_sse_endpoint.py::test_heartbeat_during_slow_render -x` | ✅ extend | ⬜ pending |
| 85-01-06 | 01 | 0 | HOTFIX-03 SC3 (heartbeat suppressed) | integration | `uv run pytest tests/integration/test_sse_endpoint.py::test_heartbeat_suppressed_when_events_flow -x` | ✅ extend | ⬜ pending |
| 85-01-07 | 01 | 0 | HOTFIX-03 SC4 (error string stable) | unit | `uv run pytest tests/integration/test_sse_endpoint.py::test_timeout_error_string_unchanged -x` | ✅ extend | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_sse_max_duration.py` — NEW file. Two tests: env default = 570 when unset; env override propagates to both `app.fast_api_app.SSE_MAX_DURATION_S` and `app.routers.admin.chat._SSE_MAX_DURATION_S`.
- [ ] `tests/unit/admin/test_admin_chat.py` extension — add `test_sse_max_duration_constant` (asserts `_SSE_MAX_DURATION_S >= 570`, default = 570).
- [ ] `tests/integration/test_sse_endpoint.py` extension — add 4 tests: long-stream-no-timeout (monkeypatch `time.monotonic`), heartbeat-during-quiet-window, heartbeat-suppressed-when-events-flow, timeout-error-string-stable.

*No framework install needed — pytest, pytest-asyncio, httpx.AsyncClient, unittest.mock all in use across tests/.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 30s video render streams asset URL through SSE | HOTFIX-03 SC2 | Real Vertex AI Veo + Remotion + deployed Cloud Run; cannot mock 7–9 min wall-clock | (1) `pwsh scripts/deploy-fast.ps1` to push to Cloud Run. (2) Open `https://pikar-ai.com` chat as a logged-in user. (3) Prompt: "Render me a 30-second product demo video for an AI scheduling app." (4) Watch chat for streaming events + workspace for preview. **Expected:** within 7–12 min, asset URL streams in and video plays. **No "Stream timeout" error.** |
| Cloud Run log assertion | HOTFIX-03 SC2 ops | Telemetry only post-deploy | Filter Cloud Run logs by `session_id`. Expected sequence: `Calling runner.run_async` → multiple `progress` events → `Stream finished normally` → `interaction_id`. Pre-fix pattern: `SSE stream hit max duration (300s), closing`. |
| Render exceeding 570s (SC4 deferred case) | HOTFIX-03 SC4 | Long-tail behavior must remain unchanged | Trigger a render likely to exceed 570s (e.g. 8-scene video). **Expected:** server emits `Stream timeout` data event; user sees `Error: Stream timeout — please retry your request.` Render may still complete server-side (Director budget = 1200s) but user has lost the URL. Sentry/logs should capture the orphan. **This is the documented deferred case** — see `deferred-items.md`. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`tests/unit/test_sse_max_duration.py`)
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s for focused run
- [ ] `nyquist_compliant: true` set in frontmatter (flip after planner & checker confirm coverage)
- [ ] SC1 literal-vs-engineering tradeoff documented in plan SUMMARY + ROADMAP
- [ ] SC4 deferred-work doc landed at `.planning/phases/85-render-sse-timeout/deferred-items.md`

**Approval:** pending

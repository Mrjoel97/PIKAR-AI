# Codex Build-App Remediation Plan (Parallel Agent Workstreams)

## Goal

Fix the identified build/runtime blockers and high-risk integration issues in the `codex/build-app` worktree, then verify backend + frontend build/run readiness.

Worktree:
- `.tmp/codex-parallel/worktrees/wt-build-app`
- Branch: `codex/build-app`

## Scope (Issues Identified)

### P0 Blockers (Must Fix First)

1. Workflow approval endpoint mismatch
- `app/routers/workflows.py` calls `engine.approve_step(..., feedback=...)`
- `app/workflows/engine.py` expects `step_message`
- Result: approval route fails at runtime

2. `/feedback` logger crash risk
- `app/fast_api_app.py` uses stdlib logger and calls `logger.log_struct(...)`
- `log_struct` is not available on stdlib logger
- Result: `/feedback` can raise `AttributeError`

3. SSE auth/session ownership gap
- `app/fast_api_app.py` `/a2a/app/run_sse` trusts client-provided `user_id`
- frontend sends bearer token but backend endpoint does not verify it
- Result: session spoofing / cross-user access risk

4. CORS configuration invalid for credentialed requests
- `allow_origins=["*"]` with `allow_credentials=True`
- Result: browser credentialed requests can fail / misbehave

5. Root frontend build script path stale
- root `package.json` scripts target `apps/frontend` but app lives in `frontend`
- Result: root `npm run build/dev/start` broken

### P1 High-Value Stabilization (Fix in Same Sweep)

6. Blocking sync Supabase calls inside async code paths
- `app/workflows/engine.py`, `app/persistence/supabase_session_service.py`, others
- Risk: event-loop blocking under load

7. Production code contains planning/AI comments
- `app/routers/onboarding.py`, `app/routers/workflows.py`
- Risk: maintainability, review noise, hidden contradictory intent

8. Chat message duplication risk (SSE + realtime)
- `frontend/src/hooks/useAgentChat.ts` + `frontend/src/components/chat/ChatInterface.tsx` + `frontend/src/hooks/useRealtimeSession.ts`
- Risk: duplicate agent/user messages in UI

9. Duplicate Supabase auth verification logic
- `app/routers/onboarding.py` duplicates logic similar to `app/app_utils/auth.py`
- Risk: drift and inconsistent auth behavior

10. Mutable default arg in workflow engine
- `app/workflows/engine.py` `context: Dict[str, Any] = {}`
- Risk: shared mutable state bug

## Parallel Agent Workstreams

Use 5 parallel agents (human or AI workers) with one integration agent owning final merge verification.

### Agent A: Workflow/API Runtime Fixes
- Owns workflow router/engine correctness
- Primary files:
  - `app/routers/workflows.py`
  - `app/workflows/engine.py`

### Agent B: Security/Auth/SSE Hardening
- Owns token verification, user identity extraction, SSE ownership checks, shared auth reuse
- Primary files:
  - `app/fast_api_app.py`
  - `app/app_utils/auth.py`
  - `app/routers/onboarding.py`

### Agent C: Frontend Chat Integration Stability
- Owns SSE/realtime dedupe behavior and client integration checks
- Primary files:
  - `frontend/src/hooks/useAgentChat.ts`
  - `frontend/src/components/chat/ChatInterface.tsx`
  - `frontend/src/hooks/useRealtimeSession.ts`

### Agent D: Build/Config/DevEx Fixes
- Owns root scripts, CORS env-driven config, feedback logger fallback
- Primary files:
  - `package.json`
  - `app/fast_api_app.py`
  - optional `.env.example` / docs if present

### Agent E: QA/Verification/Test Harness
- Owns targeted tests, regression checks, verification docs
- Primary files:
  - `tests/*`
  - `frontend/src/**/*.test.tsx` (if UI tests added)

## Dependency Graph (Execution Order)

- `P0-03` (SSE auth) and `P0-04` (CORS) should land before frontend end-to-end validation.
- `P0-01` (workflow approve mismatch) should land before workflow route tests.
- `P0-05` (root scripts) can run in parallel with all backend fixes.
- `P1-08` (chat dedupe) depends on confirmed SSE auth behavior (`P0-03`).
- `P1-09` (shared auth reuse) can be refactor-only after `P0-03` or done as part of it.

## Trackable Task Board

Status legend:
- `TODO`
- `IN PROGRESS`
- `BLOCKED`
- `DONE`

| ID | Priority | Task | Owner | Depends | Status | Acceptance Criteria |
|---|---|---|---|---|---|---|
| P0-01 | P0 | Fix workflow approval parameter mismatch (`feedback` vs `step_message`) | Agent A | None | DONE | `POST /workflows/executions/{id}/approve` calls engine successfully and returns 200 on valid waiting step |
| P0-02 | P0 | Make `/feedback` logger safe with stdlib logger fallback | Agent D | None | DONE | `/feedback` does not raise `AttributeError`; logs feedback via supported path |
| P0-03 | P0 | Enforce bearer token verification and derive `user_id` server-side for `/a2a/app/run_sse` | Agent B | None | DONE | Backend ignores client-supplied `user_id` (or validates exact match), unauthorized requests get 401 |
| P0-04 | P0 | Replace wildcard CORS + credentials with env-configured origin allowlist | Agent D | None | TODO | Browser auth requests work with configured origin(s); config is explicit and documented |
| P0-05 | P0 | Fix root `package.json` frontend script path (`apps/frontend` -> `frontend`) | Agent D | None | DONE | `npm run build` from repo root invokes `frontend` build script |
| P1-06 | P1 | Remove mutable default arg in workflow engine `start_workflow` | Agent A | None | TODO | Function signature uses `None`; behavior unchanged in tests |
| P1-07 | P1 | Remove planning/AI comments from production routers; keep concise actionable comments only | Agent A | None | TODO | `app/routers/onboarding.py` and `app/routers/workflows.py` contain no planning narrative comments |
| P1-08 | P1 | Add dedupe strategy for chat messages arriving via SSE + realtime | Agent C | P0-03 | TODO | No duplicate messages for same event/turn in common chat flow |
| P1-09 | P1 | Consolidate auth verification logic to shared helper/dependency | Agent B | P0-03 (recommended) | TODO | Onboarding and SSE endpoints use shared verification path or thin wrappers |
| P1-10 | P1 | Audit/contain sync Supabase calls in async hot paths (targeted) | Agent A + B | None | TODO | Documented hotspots + at least P0 routes avoid avoidable blocking or are explicitly deferred |
| T-01 | Test | Add/adjust backend tests for workflow approve route success path and bad auth/path mismatch regression | Agent E | P0-01 | TODO | Test fails before fix / passes after fix |
| T-02 | Test | Add backend tests for `/feedback` logging path and `/a2a/app/run_sse` auth rejection | Agent E | P0-02, P0-03 | TODO | Unauthorized SSE returns 401; `/feedback` returns success |
| T-03 | Test | Frontend check for root build scripts + chat dedupe behavior (targeted) | Agent E + Agent C | P0-05, P1-08 | TODO | Root script works; dedupe logic validated with unit/integration test or manual repro script |
| V-01 | Verify | Run targeted backend tests + lint on touched files | Agent E | P0 tasks | TODO | Tests pass; no new lint failures in touched files |
| V-02 | Verify | Run `frontend` build and smoke route checks | Agent E | P0-04, P0-05 | TODO | `frontend` builds; auth + chat boot path smoke-tested |

## Detailed Task Breakdown

### Agent A Tasks (Workflow/API Runtime)

- [ ] `P0-01` Fix approval route/engine call mismatch
  - Preferred fix: align router call to engine signature or rename engine arg to `feedback` and support backward compatibility
  - Confirm route still returns consistent response schema
  - Verify no other callers rely on old name

- [ ] `P1-06` Fix mutable default arg
  - Change `context` default to `None`
  - Normalize with `context = context or {}`

- [ ] `P1-07` Cleanup production comments
  - Remove planning narrative comments
  - Keep brief rationale comments only where needed

- [ ] `P1-10` Async blocking audit (workflow/session hot paths)
  - Inventory blocking `.execute()` calls in async methods
  - For immediate scope: document hotspots and patch P0-critical paths if easy
  - If larger refactor needed, split into follow-up ticket with benchmarks

### Agent B Tasks (Security/Auth/SSE)

- [ ] `P0-03` SSE auth hardening
  - Verify bearer token on `/a2a/app/run_sse`
  - Derive `user_id` from token, do not trust request body
  - Optional: reject if request body `user_id` present and mismatched
  - Ensure session create/get uses verified user id only

- [ ] `P1-09` Shared auth dependency reuse
  - Reuse `app/app_utils/auth.py` helper(s) or create unified dependency
  - Reduce duplicated `create_client` auth verification in onboarding router
  - Keep endpoint signatures clean

- [ ] `P1-10` Async blocking audit support
  - Identify auth/session verification paths using sync network I/O inside async handlers
  - Note if `run_in_threadpool` or sync route conversion is warranted

### Agent C Tasks (Frontend Chat Stability)

- [ ] `P1-08` Dedupe SSE + realtime messages
  - Define dedupe key (candidate: `session_event.id`, `event_index`, or normalized event hash)
  - Prevent duplicate rendering in `ChatInterface` when realtime echoes local/SSE updates
  - Preserve optimistic UI and streaming partials behavior
  - Avoid regressing widget persistence and traces

- [ ] `T-03` Add test or reproducible manual verification notes
  - Unit test preferred for dedupe utility/state path
  - If hard to unit test quickly, add deterministic manual repro checklist

### Agent D Tasks (Build/Config/DevEx)

- [ ] `P0-02` `/feedback` logging fallback
  - Use stdlib `logger.info(...)` or guard `hasattr(logger, "log_struct")`
  - Preserve structured payload logging when cloud logger is actually configured

- [ ] `P0-04` CORS allowlist config
  - Introduce env-driven origin parsing (comma-separated)
  - Safe local defaults (`http://localhost:3000` etc.)
  - Preserve non-browser API usability

- [ ] `P0-05` Root script path fix
  - Update root `package.json` scripts to `frontend`
  - Optionally add `frontend:*` aliases for clarity (`dev:frontend`, `build:frontend`)

### Agent E Tasks (QA / Verification)

- [ ] `T-01` Workflow approval regression test
  - Reproduce current failure mode
  - Assert fixed route passes through feedback / approval message

- [ ] `T-02` SSE + feedback endpoint tests
  - Unauthorized `/a2a/app/run_sse` should return 401
  - `/feedback` should return success and not crash

- [ ] `V-01` Backend verification run
  - Run targeted pytest selection for touched areas
  - Run lint on touched Python files

- [ ] `V-02` Frontend verification run
  - `npm run build` from repo root
  - `npm run build` in `frontend`
  - Smoke auth/chat page boot (manual if no test harness)

## Parallel Execution Plan (Suggested)

### Wave 1 (Parallel)
- Agent A: `P0-01`, `P1-06`
- Agent B: `P0-03` (start with shared auth helper decisions)
- Agent D: `P0-02`, `P0-05`

### Wave 2 (Parallel)
- Agent D: `P0-04`
- Agent A: `P1-07`, `P1-10` hotspot inventory
- Agent B: `P1-09`
- Agent C: prep dedupe design / test harness

### Wave 3 (Parallel)
- Agent C: `P1-08`
- Agent E: `T-01`, `T-02`, `T-03`

### Wave 4 (Integration)
- Agent E: `V-01`, `V-02`
- Integration owner: resolve merge conflicts and finalize change log

## Verification Commands (Targeted)

Adjust to available tooling in the worktree.

Backend:
```bash
uv run pytest tests/unit -k "workflow or onboarding or auth" -v
uv run pytest tests/integration -k "workflow or sse or onboarding" -v
uv run ruff check app/fast_api_app.py app/routers/onboarding.py app/routers/workflows.py app/workflows/engine.py app/app_utils/auth.py
```

Frontend:
```bash
npm run build
cd frontend && npm run build
cd frontend && npm run test -- --run
```

Manual smoke checks:
```bash
make local-backend
# In separate terminal:
cd frontend && npm run dev
```

## Exit Criteria (Definition of Done)

- All P0 tasks marked `DONE`
- P1-06, P1-07, P1-08, P1-09 completed (P1-10 can be split if refactor is large, but hotspots documented)
- Targeted tests pass for changed areas
- Root and frontend build commands work
- Chat SSE path enforces auth and does not trust client `user_id`
- Workflow approval route successfully advances/approves a waiting step

## Notes for Coordination

- Keep each agent scoped to its file set to reduce merge conflicts.
- Prefer compatibility-preserving changes on shared interfaces (`approve_step`, auth helpers).
- If `P1-10` expands beyond targeted fixes, record remaining items as a separate performance hardening plan rather than blocking P0 completion.

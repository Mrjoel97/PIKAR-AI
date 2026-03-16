# Plan: Phase 6 - Configuration and Deployment

**Objective:** Close the final production-readiness gaps by removing dead config drift, hardening backend deployment signals, and enforcing active SSE connection guardrails without changing the user-facing product contract.

## Scope Rules
- Remove or collapse dead config surfaces instead of layering new abstractions on top of them.
- Keep Redis naming on the existing `REDIS_*` contract everywhere.
- Add deployment guardrails in the smallest place that actually protects runtime behavior.
- Preserve current SSE payload/event semantics; only add admission control and cleanup.
- Back every Phase 6 claim with targeted regression coverage.

## 1. Unify Configuration And Runtime Guardrails
**Goal:** close CFG-01 through CFG-03 together by eliminating the stale config path and aligning deployment/runtime documentation.

**Tasks:**
- Replace the dead `AppSettings` export surface in `app/config/settings.py` and `app/config/__init__.py` with validation-only exports from `app.config.validation`.
- Remove the last implicit `CACHE_*` config path by deleting the unused Pydantic cache/database settings tree.
- Add a backend `HEALTHCHECK` instruction to `Dockerfile` that probes `/health/live` on the active `PORT`.
- Document the SSE/upload guardrail env vars in `app/.env.example` and `.env.example`.

**Files:**
- `app/config/settings.py`
- `app/config/__init__.py`
- `Dockerfile`
- `app/.env.example`
- `.env.example`

## 2. Add SSE Connection Admission Control
**Goal:** close CFG-04 and lock in CFG-05 with explicit regression coverage.

**Tasks:**
- Add a shared per-process SSE connection limiter keyed by user id.
- Enforce that limiter in both `POST /a2a/app/run_sse` and `GET /workflows/executions/{execution_id}/events`.
- Return 429 when a user exceeds the configured active stream limit.
- Release connection slots reliably on disconnect/error/normal completion.
- Add regression tests that prove production Terraform does not enable `LOCAL_DEV_BYPASS` or `SKIP_ENV_VALIDATION`.

**Files:**
- `app/services/sse_connection_limits.py`
- `app/fast_api_app.py`
- `app/routers/workflows.py`
- `tests/unit/test_configuration_deployment.py`
- `deployment/terraform/service.tf`
- `deployment/terraform/vars/env.tfvars`

## 3. Verification
**Backend checks:**
- `uv run python -` with `py_compile.compile(...)` for the changed backend/test modules
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_configuration_deployment.py tests/unit/test_product_truth_guards.py tests/unit/test_security_hardening.py -q`

**Manual/contract checks:**
- confirm `app.config` no longer exports `AppSettings` or a `CACHE_*` path
- confirm the backend `Dockerfile` contains a healthcheck against `/health/live`
- confirm `/a2a/app/run_sse` rejects excess active connections with 429
- confirm workflow SSE releases slots on disconnect/completion and uses the same limiter
- confirm production Terraform files do not set `LOCAL_DEV_BYPASS` or `SKIP_ENV_VALIDATION`

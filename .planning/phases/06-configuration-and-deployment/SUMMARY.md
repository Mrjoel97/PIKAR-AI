# Phase 6 Summary: Configuration and Deployment

## Outcome

Completed the final production-readiness phase. The codebase no longer carries the dead `AppSettings`/`CACHE_*` config surface, the backend Docker image now declares its own healthcheck, SSE routes enforce a shared per-user active connection limit with 429 responses, and the production Terraform bypass-flag policy is covered by regression tests.

## What Changed

- Replaced the unused settings tree in `app/config/settings.py` and `app/config/__init__.py` with validation-only exports from `app.config.validation`, removing the stale `AppSettings`/`CacheSettings` path and leaving `REDIS_*` as the only live Redis env contract.
- Added `app/services/sse_connection_limits.py` as the shared in-memory SSE admission-control helper.
- Updated `app/fast_api_app.py` so `POST /a2a/app/run_sse` rejects excess active streams with 429, checks for disconnects while streaming, and releases user slots in all exit paths.
- Updated `app/routers/workflows.py` so workflow status SSE uses the same user-level connection limiter and releases slots when the stream ends.
- Added a first-class backend `HEALTHCHECK` instruction to `Dockerfile` against `/health/live`.
- Documented `SSE_MAX_CONNECTIONS_PER_USER` and `MAX_UPLOAD_SIZE_BYTES` in both env examples:
  - `app/.env.example`
  - `.env.example`
- Added targeted regression coverage in `tests/unit/test_configuration_deployment.py` for:
  - removal of the legacy config surface
  - per-user SSE admission control
  - Dockerfile healthcheck presence
  - env-example guardrail documentation
  - production Terraform bypass-flag policy

## Verification

Passed checks:
- `uv run python -` with `py_compile.compile(...)` for:
  - `app/services/sse_connection_limits.py`
  - `app/config/settings.py`
  - `app/config/__init__.py`
  - `app/fast_api_app.py`
  - `app/routers/workflows.py`
  - `tests/unit/test_configuration_deployment.py`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_configuration_deployment.py tests/unit/test_product_truth_guards.py tests/unit/test_security_hardening.py -q`

Notes:
- The targeted pytest slice passed only after running outside the sandbox because the local `.venv` remains permission-sensitive during collection.
- The same pytest run emitted three unrelated existing deprecation warnings tied to `datetime.utcnow()` in `app/fast_api_app.py` and `app/exceptions.py`.

## Follow-up

- Milestone v1.1 is now code-complete across Phases 2 through 6.
- The next planning step is milestone closeout and routing into v2.0 work.
- Refresh `uv.lock` in an environment with full `uv lock` support.

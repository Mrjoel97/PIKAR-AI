# Phase 6 Context: Configuration and Deployment

## Why This Phase Exists

Phases 2 through 5 aligned the schema, async boundaries, frontend contracts, and request-path security, but the production-readiness milestone still had deployment drift. The remaining gaps were not new product features; they were operational seams: an unused alternate config surface (`AppSettings` with `CACHE_*` prefixes), no first-class backend Docker healthcheck, no active per-user SSE connection cap, and no explicit regression evidence that production Terraform avoids dev-only bypass flags.

## Requirement Mapping

- CFG-01: Config system unified: remove the dead `AppSettings` surface and keep `app.config` focused on runtime validation helpers
- CFG-02: Redis env var naming aligned on `REDIS_*` only
- CFG-03: Backend Docker image declares a `HEALTHCHECK` against `/health/live`
- CFG-04: SSE endpoints enforce a per-user active connection limit with 429 responses
- CFG-05: Production Terraform remains free of `LOCAL_DEV_BYPASS` and `SKIP_ENV_VALIDATION` enablement, with regression coverage

## What The Audit Found

1. The only remaining `AppSettings`/`CacheSettings` surface was dead code.
   - `app/config/settings.py` and `app/config/__init__.py` exported a Pydantic settings tree that no live caller imported, and that tree still implied a `CACHE_*` env-prefix path even though the runtime already uses `REDIS_*`.

2. Redis naming was already consistent everywhere that mattered at runtime.
   - `app/services/cache.py`, the env examples, `docker-compose.yml`, and both Terraform service definitions all use `REDIS_HOST`, `REDIS_PORT`, and `REDIS_DB`. The only conflicting surface was the dead `CacheSettings` wrapper.

3. The backend container still relied on compose-only health metadata.
   - `docker-compose.yml` had a backend healthcheck, but the root `Dockerfile` itself had no `HEALTHCHECK` instruction.

4. SSE routes still allowed unlimited concurrent streams per user.
   - `POST /a2a/app/run_sse` in `app/fast_api_app.py` and `GET /workflows/executions/{execution_id}/events` in `app/routers/workflows.py` had heartbeat/streaming logic but no active connection accounting or 429 guard.

5. Production Terraform already avoided dev bypass flags, but that guarantee was implicit.
   - `deployment/terraform/service.tf` and `deployment/terraform/vars/env.tfvars` did not enable `LOCAL_DEV_BYPASS` or `SKIP_ENV_VALIDATION`, yet there was no regression test to keep that true.

## Files In Scope

- `app/config/settings.py`
- `app/config/__init__.py`
- `app/services/sse_connection_limits.py`
- `app/fast_api_app.py`
- `app/routers/workflows.py`
- `Dockerfile`
- `app/.env.example`
- `.env.example`
- `deployment/terraform/service.tf`
- `deployment/terraform/vars/env.tfvars`
- `tests/unit/test_configuration_deployment.py`

## Planning Notes

- Prefer removing dead config surfaces over introducing yet another central settings abstraction.
- Keep the SSE connection cap dependency-free and per-process so it does not add Redis or database latency to the hot stream path.
- Preserve existing SSE wire format; the new limit should fail fast with a 429 before stream startup.
- Treat Terraform bypass-flag work as a regression guarantee problem: validate the production files rather than inventing new no-op runtime vars.

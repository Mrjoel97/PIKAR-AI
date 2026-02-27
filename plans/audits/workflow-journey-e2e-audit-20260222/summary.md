# Workflow + Journey E2E Audit Summary

- Timestamp (UTC): `2026-02-22T19:30:03+00:00`
- Workflows audited: `68`
- Journeys audited: `160`
- Backend base URL: `http://localhost:8000`

## Preflight
- `/health/live`: `alive`
- `/health/connections`: `healthy`
- `/health/workflows/readiness`: `not_ready`
- Workflow templates in readiness: `68`
- Journeys in readiness view: `160`
- Failing readiness checks: `backend_api_url_configured, fallback_simulation_disabled, readiness_gate_enabled, strict_critical_tool_guard_enabled, strict_tool_resolution_enabled, workflow_service_secret_configured`

## Workflow Results
- Manual `BLOCKED_ENV_CONFIG`: 48
- Manual `PARTIAL_START_ONLY`: 20
- Autonomous `BLOCKED_AUTONOMY_ENV_CONFIG`: 68
- Workflow starts without observed terminal/gate status in exhaustive pass (per-item polling skipped): `20`

## Journey Results
- Manual `PARTIAL_START_ONLY`: 160
- Autonomous `BLOCKED_AUTONOMY_ENV_CONFIG`: 160
- Journey workflow starts without observed terminal/gate status in exhaustive pass (per-item polling skipped): `160`

## Stack Accommodation
- Frontend, backend, schema, and API infrastructure were statically traced against the journey/workflow paths.
- Core stack files present: `True`
- Frontend journey flow endpoints wired: `True`
- Backend journey workflow routes present: `True`
- Workflow engine triggers edge-function execution callback: `True`
- Workflow start/approve/events API routes present: `True`

- Workflow stack status `SUPPORTED_WITH_ENV_SETUP`: 60
- Workflow stack status `SUPPORTED_WITH_GATES`: 8
- Journey stack status `SUPPORTED_WITH_ENV_SETUP`: 160

## Primary Findings
- Workflow executions commonly start successfully but remain `pending` because the edge-function callback path is not fully configured (`BACKEND_API_URL` / `WORKFLOW_SERVICE_SECRET` missing).
- Readiness registry is populated (68 rows) but enforcement is disabled in this environment (`WORKFLOW_ENFORCE_READINESS_GATE=false`).
- Journey UI collects outcomes/timeline conditionally via `outcomes_prompt`; backend journey workflow start requires both fields for all journeys, which is a UX/API contract mismatch risk for journeys lacking `outcomes_prompt`.
- Exhaustive per-item classification in this pass is based on preflight readiness + start/create/start API outcomes (per-item polling disabled for runtime feasibility in this environment).
- Browser subset UI execution was not run in this terminal-only pass; `browser_subset_results.md` documents the gap.

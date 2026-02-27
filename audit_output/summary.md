# Workflow + Journey E2E Audit Summary

- Timestamp (UTC): `2026-02-23T15:48:47+00:00`
- Workflows audited: `68`
- Journeys audited: `160`
- Backend base URL: `http://localhost:8000`

## Preflight
- `/health/live`: `alive`
- `/health/connections`: `healthy`
- `/health/workflows/readiness`: `not_ready`
- Workflow templates in readiness: `68`
- Journeys in readiness view: `160`
- Failing readiness checks: `fallback_simulation_disabled`

## Workflow Results
- Manual `BLOCKED_ENV_CONFIG`: 68
- Autonomous `BLOCKED_AUTONOMY_ENV_CONFIG`: 68
- Workflow starts without observed terminal/gate status in exhaustive pass (per-item polling skipped): `0`

## Journey Results
- Manual `BLOCKED_ENV_CONFIG`: 160
- Autonomous `BLOCKED_AUTONOMY_ENV_CONFIG`: 160
- Journey workflow starts without observed terminal/gate status in exhaustive pass (per-item polling skipped): `0`

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
- Journey UI collects outcomes/timeline conditionally via `outcomes_prompt`; backend journey workflow start requires both fields for all journeys, which is a UX/API contract mismatch risk for journeys lacking `outcomes_prompt`.
- Exhaustive per-item classification in this pass is based on preflight readiness + start/create/start API outcomes (per-item polling disabled for runtime feasibility in this environment).
- Browser subset UI execution was not run in this terminal-only pass; `browser_subset_results.md` documents the gap.

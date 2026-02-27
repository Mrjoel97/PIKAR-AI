# Blocker Catalog

## Root Cause Counts
- `env`: 228

## Environment / Infrastructure Findings
- Failing readiness check: `backend_api_url_configured`
- Failing readiness check: `fallback_simulation_disabled`
- Failing readiness check: `readiness_gate_enabled`
- Failing readiness check: `strict_critical_tool_guard_enabled`
- Failing readiness check: `strict_tool_resolution_enabled`
- Failing readiness check: `workflow_service_secret_configured`
- `backend_api_url_configured` = `False`
- `workflow_service_secret_configured` = `False`
- `readiness_gate_enabled` = `False`
- `strict_tool_resolution_enabled` = `False`
- `strict_critical_tool_guard_enabled` = `False`
- `fallback_simulation_disabled` = `False`

## Stack Mismatches
- Journey UI collects outcomes/timeline conditionally via `outcomes_prompt`, but backend `start-journey-workflow` enforces both inputs universally.

## High-Impact Blockers (Fix Once, Unblock Many)
- Configure `BACKEND_API_URL` and `WORKFLOW_SERVICE_SECRET` for the workflow edge-function callback path.
- Enable readiness gate in environments where strict operational validation is required.
- Enable strict tool resolution / critical tool guard to reduce silent degradation in workflow steps.

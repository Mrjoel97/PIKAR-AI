# Blocker Catalog

## Root Cause Counts
- `env`: 228

## Environment / Infrastructure Findings
- Failing readiness check: `fallback_simulation_disabled`
- `backend_api_url_configured` = `True`
- `workflow_service_secret_configured` = `True`
- `readiness_gate_enabled` = `True`
- `strict_tool_resolution_enabled` = `True`
- `strict_critical_tool_guard_enabled` = `True`
- `fallback_simulation_disabled` = `False`

## Stack Mismatches
- Journey UI collects outcomes/timeline conditionally via `outcomes_prompt`, but backend `start-journey-workflow` enforces both inputs universally.

## High-Impact Blockers (Fix Once, Unblock Many)

---
status: testing
phase: 51-observability-monitoring
source: [51-01-SUMMARY.md, 51-02-SUMMARY.md, 51-03-SUMMARY.md, 51-04-SUMMARY.md]
started: 2026-04-09T17:00:00Z
updated: 2026-04-09T17:00:00Z
---

## Current Test

number: 1
name: Automated Test Suite
expected: |
  All 37+ automated tests pass: 3 Sentry init (pytest), 12 health endpoint shape (pytest),
  14 observability service (pytest), 5 observability API (pytest), 6 dashboard UI (vitest).
  Run: `uv run pytest tests/unit/test_sentry_init.py tests/unit/test_health_endpoints.py tests/unit/services/test_observability_metrics_service.py tests/unit/admin/test_observability_api.py -v`
  and: `cd frontend && npx vitest run __tests__/pages/ObservabilityPage.test.tsx --reporter=verbose`
awaiting: user response

## Tests

### 1. Automated Test Suite
expected: All 37+ automated tests pass (pytest + vitest) covering Sentry init, health endpoint shapes, observability metrics service, admin API routes, and dashboard UI rendering
result: [pending]

### 2. Health Endpoint Canonical Shape
expected: `curl http://localhost:8000/health/live` returns JSON with exactly these fields: `status` ("ok"), `version` ("1"), `service` ("live"), `latency_ms` (number), `details` (object), `checked_at` (ISO timestamp). No extra fields. Shape is uniform across all 5 /health/* endpoints.
result: [pending]

### 3. Health Connections Integrations Subkey
expected: `curl http://localhost:8000/health/connections` returns the canonical shape PLUS an `integrations` key containing a dict of integration provider names (hubspot, stripe, etc.) with their last_sync_at and status sourced from integration_sync_state table.
result: [pending]

### 4. Admin Observability Summary Endpoint
expected: `curl -H "Authorization: Bearer <admin-token>" http://localhost:8000/admin/observability/summary` returns JSON with error_rate_24h, mtd_ai_spend_usd, projected_monthly_usd, p95_latency_ms, active_agents, and system_health fields. Requires admin auth.
result: [pending]

### 5. Admin Observability Dashboard Page
expected: Navigate to `/admin/observability` in browser as admin. Page shows: (1) hero metrics row with error rate sparkline, MTD AI spend, p95 latency, system health traffic light, (2) four tabs labeled Errors/Performance/AI Cost/Health, (3) time-range picker with 1h/24h/7d/30d options, (4) Refresh button. Default tab is Errors.
result: [pending]

### 6. Admin Nav Observability Link
expected: Admin sidebar navigation shows an "Observability" item with an Eye icon, positioned after "Monitor" and before "Analytics". Clicking it navigates to /admin/observability.
result: [pending]

### 7. Sentry Backend Error Capture
expected: With SENTRY_DSN_BACKEND set to a real Sentry DSN, trigger an unhandled exception in the backend. Sentry dashboard shows a new event with: stack trace, user context (user_id UUID only, no email), request metadata. Without DSN set, Sentry is a no-op (no errors, no crashes).
result: [pending]

### 8. Sentry Frontend Error Capture
expected: With NEXT_PUBLIC_SENTRY_DSN set, trigger a React component error in the browser. RootErrorBoundary catches it, Sentry.captureException fires, event appears in Sentry frontend project with componentStack in extras. Without DSN, error boundary still catches but no Sentry event.
result: [pending]

## Summary

total: 8
passed: 0
issues: 0
pending: 8
skipped: 0

## Gaps

[none yet]

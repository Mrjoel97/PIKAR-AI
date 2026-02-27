# Workflow Wave Rollout Gates

Last Updated: 2026-02-19
Owner: Platform Engineering

## SLO Gates
- Start Success Rate: `>= 99.0%` over trailing 24h
- Completion Rate: `>= 95.0%` over trailing 24h
- Step Error Rate: `<= 2.0%` over trailing 24h
- MTTR (P0/P1): `<= 60 minutes` over trailing 7d

## Promotion Rules
- Internal -> Canary:
  - All canary path tests pass (`start`, `advance`, `approve`, `cancel`, `retry`, `422` gating)
  - No open P0/P1 defects
- Canary -> 25%:
  - SLO gates pass for 24h
  - No open P0/P1 defects
- 25% -> 50%:
  - SLO gates pass for 24h
  - No open P0/P1 defects
- 50% -> 100%:
  - SLO gates pass for 24h
  - No open P0/P1 defects

## Operational Checks
- Runtime contract:
  - `WORKFLOW_STRICT_TOOL_RESOLUTION=true`
  - `WORKFLOW_ALLOW_FALLBACK_SIMULATION=false`
  - `WORKFLOW_ENFORCE_READINESS_GATE=true`
  - Valid `BACKEND_API_URL`
  - Strong `WORKFLOW_SERVICE_SECRET`
- Health:
  - `/health/connections` status healthy
  - `/health/workflows/readiness` status ready
- Alerts:
  - Run `scripts/rollout/workflow_health_alerts.py`
  - Trigger webhook via `WORKFLOW_ALERT_WEBHOOK_URL` if configured

## Signoff Requirement
- Engineering signoff required
- Product signoff required
- Operations signoff required

---
phase: 36-enterprise-governance
plan: "02"
subsystem: governance
tags: [api-router, audit-trail, approval-chains, portfolio-health, feature-gate, enterprise]
dependency_graph:
  requires: [GovernanceService, governance_audit_log table, approval_chains table, approval_chain_steps table]
  provides: [GET /governance/audit-log, GET /governance/portfolio-health, POST /governance/approval-chains, GET /governance/approval-chains, GET /governance/approval-chains/{chain_id}, POST /governance/approval-chains/{chain_id}/steps/{step_order}/decide]
  affects: [36-03-dashboard, fast_api_app.py router registry]
tech_stack:
  added: []
  patterns: [feature-gate dependency, require_role admin gate, fire-and-forget audit logging, Pydantic response models]
key_files:
  created:
    - app/routers/governance.py
  modified:
    - app/fast_api_app.py
    - app/routers/initiatives.py
    - app/routers/teams.py
    - app/routers/workflows.py
decisions:
  - "Audit logging in existing routers is fire-and-forget — log_event never raises so it cannot break action responses"
  - "create_approval_chain endpoint also calls log_event directly to record chain creation in the audit trail"
  - "Pre-existing B904/F811 lint errors in initiatives.py and workflows.py are out of scope — 39 existed before, none introduced by these changes"
metrics:
  duration: "12 minutes"
  completed_date: "2026-04-03"
  tasks_completed: 2
  files_created: 1
  files_modified: 4
requirements_satisfied: [GOV-01, GOV-04]
---

# Phase 36 Plan 02: Governance API Router + Audit Wiring Summary

**One-liner:** Governance REST API with 6 feature-gated endpoints (audit log, portfolio health, approval chain CRUD) plus fire-and-forget audit logging wired into initiatives, teams, and workflows routers.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Governance API router | cda63d4 | app/routers/governance.py, app/fast_api_app.py |
| 2 | Wire audit logging into existing routers | 5a0bd1f | app/routers/initiatives.py, app/routers/teams.py, app/routers/workflows.py |

## What Was Built

### Task 1: Governance API Router

File: `app/routers/governance.py`

**Router setup:**
- Prefix: `/governance`, tags: `["Governance"]`
- Feature gate: `require_feature("governance")` — enterprise tier only
- Follows exact same pattern as `app/routers/teams.py` (copyright header, Google-style docstrings, identical import layout)

**5 Pydantic models:**

| Model | Purpose |
|-------|---------|
| `AuditLogEntry` | id, user_id, action_type, resource_type, resource_id, details, created_at |
| `PortfolioHealthResponse` | score (int 0-100), components (dict) |
| `ApprovalChainResponse` | id, user_id, action_type, resource_id, resource_label, status, steps, created_at, resolved_at |
| `CreateChainRequest` | action_type, resource_id, resource_label, steps (list[dict] or None) |
| `DecideStepRequest` | decision (approved\|rejected pattern), comment (optional) |

**6 Endpoints:**

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/governance/audit-log` | user | Paginated audit log, limit/offset/action_type query params |
| GET | `/governance/portfolio-health` | user | Weighted portfolio health score 0-100 |
| POST | `/governance/approval-chains` | admin | Create chain (logs audit event for creation) |
| GET | `/governance/approval-chains` | user | List pending chains |
| GET | `/governance/approval-chains/{chain_id}` | user | Get chain status (404 if not found) |
| POST | `/governance/approval-chains/{chain_id}/steps/{step_order}/decide` | user | Approve or reject a step |

**Registration in fast_api_app.py:**
```python
from app.routers.governance import router as governance_router
app.include_router(governance_router, tags=["Governance"])
```

### Task 2: Audit Logging in Existing Routers

All three files add `from app.services.governance_service import get_governance_service` and call `log_event` after successful operations.

**app/routers/initiatives.py — 3 log_event calls:**

| Endpoint | action_type | details |
|----------|-------------|---------|
| POST /initiatives/from-template | `initiative.created` | title, source: "template" |
| POST /initiatives/from-journey | `initiative.created` | title, source: "user_journey" |
| DELETE /initiatives/{id} | `initiative.deleted` | {} |

**app/routers/teams.py — 3 log_event calls:**

| Endpoint | action_type | details |
|----------|-------------|---------|
| POST /teams/invites/accept | `member.joined` | workspace_id |
| PATCH /teams/members/{id}/role | `role.changed` | new_role |
| DELETE /teams/members/{id} | `member.removed` | workspace_id |

**app/routers/workflows.py — 1 log_event call:**

| Endpoint | action_type | details |
|----------|-------------|---------|
| POST /workflows/start | `workflow.executed` | workflow_name |

## Verification Results

- `app/routers/governance.py`: `ruff check` → `All checks passed!`
- `governance_router` registered in `fast_api_app.py` at lines 897 + 931
- `governance_service` import confirmed in all 3 modified routers
- `log_event` call counts: initiatives.py=3, teams.py=3, workflows.py=1
- 6 route decorators present in governance.py: `/audit-log`, `/portfolio-health`, `/approval-chains` (POST+GET), `/approval-chains/{chain_id}` (GET), `/approval-chains/{chain_id}/steps/{step_order}/decide`

## Deviations from Plan

None — plan executed exactly as written. Pre-existing B904/F811 lint errors in initiatives.py and workflows.py (39 errors total before this plan's changes) are out of scope per scope boundary rules and logged to deferred-items.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| app/routers/governance.py | FOUND |
| app/fast_api_app.py (governance_router import + include_router) | FOUND |
| app/routers/initiatives.py (governance_service import, 3 log_event calls) | FOUND |
| app/routers/teams.py (governance_service import, 3 log_event calls) | FOUND |
| app/routers/workflows.py (governance_service import, 1 log_event call) | FOUND |
| Commit cda63d4 (Task 1 — governance router) | FOUND |
| Commit 5a0bd1f (Task 2 — audit wiring) | FOUND |

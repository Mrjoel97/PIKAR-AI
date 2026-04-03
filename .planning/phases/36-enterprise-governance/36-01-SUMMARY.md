---
phase: 36-enterprise-governance
plan: "01"
subsystem: governance
tags: [database, migration, service, audit-trail, approval-chains, portfolio-health]
dependency_graph:
  requires: []
  provides: [governance_audit_log table, approval_chains table, approval_chain_steps table, GovernanceService]
  affects: [36-02-api-router, 36-03-dashboard]
tech_stack:
  added: []
  patterns: [service-role client, execute_async, singleton factory, try/except audit pattern]
key_files:
  created:
    - supabase/migrations/20260403300000_enterprise_governance.sql
    - app/services/governance_service.py
  modified: []
decisions:
  - "BLE001 noqa suppression removed — rule not enabled in this project; bare except is handled by Ruff's existing B config"
  - "Three-step default approval chain (reviewer/approver/executive) stored as module constant for reuse"
  - "Portfolio health uses independent try/except per sub-query so a missing table (e.g. compliance_risks) returns 0 for that component rather than crashing the entire computation"
metrics:
  duration: "7 minutes"
  completed_date: "2026-04-03"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
requirements_satisfied: [GOV-01, GOV-02, GOV-04]
---

# Phase 36 Plan 01: Enterprise Governance — DB Schema + GovernanceService Summary

**One-liner:** Supabase migration with three governance tables (audit log, approval chains, steps) plus GovernanceService providing audit logging, weighted portfolio health (0-100), and multi-level approval chain CRUD.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Database migration for governance tables | 61e7f54 | supabase/migrations/20260403300000_enterprise_governance.sql |
| 2 | GovernanceService class | e08fb57 | app/services/governance_service.py |

## What Was Built

### Task 1: Database Migration

File: `supabase/migrations/20260403300000_enterprise_governance.sql`

Three tables created:

**`governance_audit_log`**
- Columns: id, user_id, action_type, resource_type, resource_id (nullable), details (JSONB default {}), ip_address (nullable), created_at
- Indexes: user_id, action_type, created_at DESC, composite (user_id, created_at DESC)
- RLS: owner SELECT via `auth.uid() = user_id`

**`approval_chains`**
- Columns: id, user_id, action_type, resource_id, resource_label, status (enum: pending/approved/rejected/expired), created_at, updated_at, resolved_at, expires_at
- Indexes: user_id, status, composite (user_id, status)
- RLS: owner SELECT; updated_at trigger via `_governance_set_updated_at()`

**`approval_chain_steps`**
- Columns: id, chain_id (FK cascade), step_order, role_label, approver_user_id (nullable), status (enum: pending/approved/rejected/skipped), decided_at, comment
- UNIQUE(chain_id, step_order); Index: chain_id
- RLS: owner SELECT via subquery join to approval_chains

### Task 2: GovernanceService

File: `app/services/governance_service.py`

**7 public methods:**

| Method | Purpose | Requirement |
|--------|---------|------------|
| `log_event(user_id, action_type, resource_type, ...)` | Insert audit row, never raises | GOV-01 |
| `get_audit_log(user_id, limit, offset, action_type)` | Paginated SELECT with optional filter | GOV-01 |
| `compute_portfolio_health(user_id)` | Weighted score: initiative 40% + risk 30% + allocation 30% | GOV-02 |
| `create_approval_chain(user_id, action_type, ...)` | Insert chain + steps (default 3-step or custom) | GOV-04 |
| `get_pending_chains(user_id)` | List pending chains with nested steps | GOV-04 |
| `decide_step(chain_id, step_order, ...)` | Record approve/reject, cascade to chain status + audit | GOV-04 |
| `get_chain_status(chain_id)` | Full chain + steps by ID | GOV-04 |

**`get_governance_service()`** — module-level singleton factory matching `get_kpi_service()` pattern.

## Verification Results

- Migration: 3 CREATE TABLE statements confirmed
- GovernanceService: 7 public methods (`compute_portfolio_health`, `create_approval_chain`, `decide_step`, `get_audit_log`, `get_chain_status`, `get_governance_service`, `get_pending_chains`, `log_event`)
- Ruff: `All checks passed!`
- Audit pattern: `log_event` uses try/except and `logger.error`, never re-raises
- Portfolio health: three independent try/except blocks per sub-query component

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused `noqa: BLE001` and `noqa: PLW0603` directives**
- **Found during:** Task 2 ruff lint
- **Issue:** These rules (BLE001 = blind exception, PLW0603 = global statement) are not enabled in this project's ruff config, so the noqa comments were flagged as RUF100 (unused directive)
- **Fix:** Ran `ruff check --fix` to strip all 5 unused noqa comments automatically
- **Files modified:** app/services/governance_service.py
- **Commit:** e08fb57 (included in task commit)

## Self-Check: PASSED

| Item | Status |
|------|--------|
| supabase/migrations/20260403300000_enterprise_governance.sql | FOUND |
| app/services/governance_service.py | FOUND |
| .planning/phases/36-enterprise-governance/36-01-SUMMARY.md | FOUND |
| Commit 61e7f54 (migration) | FOUND |
| Commit e08fb57 (service) | FOUND |

---
phase: 52-persona-feature-gating
plan: "04"
subsystem: governance-ui
tags: [portfolio-health, departments, executive-agent, sme-routing, enterprise-dashboard, tdd]

requires:
  - phase: 52-persona-feature-gating
    plan: "01"
    provides: persona-aware agent factories and subscription-first persona resolution

provides:
  - Enriched compute_portfolio_health with initiative_breakdown, workflow_success_rate, revenue_trend
  - Enterprise portfolio health dashboard at /dashboard/portfolio
  - SME DEPARTMENT COORDINATION section in ExecutiveAgent prompt
  - Department dashboard at /dashboard/departments with 8-department filter dropdown

affects:
  - app/services/governance_service.py
  - frontend/src/services/governance.ts
  - frontend/src/app/dashboard/portfolio/page.tsx
  - frontend/src/app/dashboard/departments/page.tsx
  - app/prompts/executive_instruction.txt

tech-stack:
  added: []
  patterns:
    - "TDD RED/GREEN for compute_portfolio_health enrichment — mock execute_async via op_name dispatch"
    - "Portfolio health returns initiative_breakdown + workflow_success_rate + revenue_trend as enrichment (non-weighted)"
    - "Department filter: All Departments default, expands selected dept card to full-width detail view"
    - "SME routing via natural language instructions in executive prompt, not code changes"

key-files:
  created:
    - tests/unit/app/services/test_governance_portfolio.py
    - frontend/src/app/dashboard/portfolio/page.tsx
    - frontend/src/app/dashboard/departments/page.tsx
  modified:
    - app/services/governance_service.py
    - frontend/src/services/governance.ts
    - app/prompts/executive_instruction.txt

key-decisions:
  - "Enrichment metrics (initiative_breakdown, workflow_success_rate, revenue_trend) appended to components dict — non-weighted, preserves existing score computation"
  - "Revenue trend queries orders table with paid status, current vs prior calendar month boundaries"
  - "Departments page not behind GatedPage — departments router has no require_feature dependency, available to all authenticated users"
  - "SME department routing via prompt instructions rather than code — consistent with CONTEXT.md decision and keeps agent factories clean"

requirements-completed: [GATE-03, GATE-04]

duration: 16min
completed: "2026-04-09"
---

# Phase 52 Plan 04: Portfolio Health Dashboard & SME Department Routing Summary

**Enriched portfolio health service with initiative breakdown, workflow success rate, and revenue trend; enterprise dashboard page at /dashboard/portfolio; SME department coordination instructions in ExecutiveAgent; departments dashboard with 8-department filter at /dashboard/departments**

## Performance

- **Duration:** ~16 min
- **Started:** 2026-04-09T22:33:00Z
- **Completed:** 2026-04-09T22:49:01Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Extended `compute_portfolio_health()` with three new enrichment components: `initiative_breakdown` (counts per status), `workflow_success_rate` (% of completed workflow_executions), and `revenue_trend` (current and prior month revenue from orders table)
- Written 4 TDD tests (RED then GREEN) covering all new components including graceful degradation when no data exists
- Created `/dashboard/portfolio` page — enterprise-gated via backend, shows score gauge, initiative breakdown cards, workflow success bar, risk exposure, and revenue trend with month-over-month comparison
- Appended `SME DEPARTMENT COORDINATION` section to `executive_instruction.txt` with the 8-department-to-agent mapping and routing rules
- Created `/dashboard/departments` page — accessible to all authenticated users, shows department health cards with 30-day task completion rates, an "All Departments" default filter dropdown, expanded detail view when a single department is selected

## Task Commits

1. **Task 1: Portfolio health enrichment and dashboard (TDD)** — `21053844` (feat)
2. **Task 2: SME department routing and departments page** — `590b3544` (feat)

## Files Created/Modified

- `app/services/governance_service.py` — Added initiative_breakdown loop over initiative rows, workflow_success_rate query against workflow_executions, revenue_trend queries against orders with calendar month boundaries
- `frontend/src/services/governance.ts` — Extended PortfolioHealth interface with InitiativeBreakdown, RevenueTrend, and PortfolioHealthComponents types
- `frontend/src/app/dashboard/portfolio/page.tsx` — New enterprise portfolio dashboard with score gauge (green/yellow/red), initiative breakdown 4-card grid, workflow success rate bar, risk exposure percentage, revenue trend with prior-month comparison
- `tests/unit/app/services/test_governance_portfolio.py` — 4 tests: initiative_breakdown by status, workflow_success_rate computation, revenue_trend summing, graceful degradation (all zeros) when no data
- `app/prompts/executive_instruction.txt` — Appended SME DEPARTMENT COORDINATION section with Engineering/Marketing/Sales/Finance/HR/Operations/Compliance/Support → agent mapping, routing rules, cross-department default
- `frontend/src/app/dashboard/departments/page.tsx` — New departments page with getDepartmentHealth() data, 8-department filter dropdown (All Departments default), health cards with 30-day completion bars, expanded detail on single-dept selection

## Decisions Made

- Enrichment metrics appended to `components` dict rather than modifying the weighted score formula — backward-compatible, `PortfolioHealthResponse` already uses `dict` type so no model change needed.
- Revenue trend uses `orders` table with `status = 'paid'` filter and calendar month boundaries (1st of current/prior month) — consistent with KpiService pattern.
- Departments page does not use `GatedPage` — the `/departments` backend router has no `require_feature("...")` dependency, so all authenticated users can access it. Gating at the backend level is sufficient.
- SME department routing added as a prompt instruction section rather than code changes — keeps agent factory signatures clean and aligns with CONTEXT.md decision that "department routing is via enhanced routing instructions in the executive prompt."

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- app/services/governance_service.py — FOUND
- frontend/src/app/dashboard/portfolio/page.tsx — FOUND
- tests/unit/app/services/test_governance_portfolio.py — FOUND
- app/prompts/executive_instruction.txt — FOUND (1 occurrence of "Department-to-Agent Mapping")
- frontend/src/app/dashboard/departments/page.tsx — FOUND
- Commit 21053844 — FOUND
- Commit 590b3544 — FOUND

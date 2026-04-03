---
phase: 37-sme-department-coordination
verified: 2026-04-03T23:45:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Create a cross-department handoff task via the UI"
    expected: "Task appears in receiving department's task list with originating department name, status badge, and due date"
    why_human: "Cannot drive a browser session; requires authenticated SME-persona user to submit the form"
  - test: "Ask the agent 'what's our payroll this month?' in the SME chat"
    expected: "Response acknowledges delegation to HRRecruitmentAgent without user specifying the agent"
    why_human: "ExecutiveAgent LLM routing behaviour at runtime cannot be verified statically"
  - test: "Verify green/yellow/red health badges update after task completion"
    expected: "Completing tasks increments completed_30d and may flip badge from red/yellow to green"
    why_human: "Requires live Supabase data; the SQL view is correct but runtime rendering needs end-to-end smoke test"
---

# Phase 37: SME Department Coordination — Verification Report

**Phase Goal:** SME users can route tasks between departments, each department has a visible health dashboard, and the AI automatically routes department-specific questions to the right specialized agent
**Verified:** 2026-04-03T23:45:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | An SME user can assign a workflow task to a different department with originating dept, status, and due date visible in the receiving dept's task list | VERIFIED | `CreateTaskForm` in `[deptId]/page.tsx` calls `createDepartmentTask()` with `from_department_id`/`to_department_id`; `list_tasks()` enriches rows with dept names; `TaskCard` renders `from_department_name`, `StatusBadge`, and due date |
| 2 | Each department has a dashboard page showing active tasks, KPI indicators, and green/yellow/red health status | VERIFIED | `/departments/[deptId]/page.tsx` (665 lines): `HealthBadge` component, 4 `MetricCard` KPIs (Active Tasks, Completed 30d, Completion Rate, Health Status), inbound/outbound task tabs |
| 3 | Health status is green/yellow/red based on 30-day task completion rate | VERIFIED | `department_health_summary` SQL view in migration: green (>80% or no tasks), yellow (50-80%), red (<50%) — pure SQL with FILTER aggregates |
| 4 | Department list page shows health badges per department | VERIFIED | `departments/page.tsx` calls `getDepartmentHealth()` in parallel with `listDepartments()`; `OverviewTab` renders health dot + "Health: X" label + active task count |
| 5 | Department names on the list page link to the detail page | VERIFIED | `<Link href={\`/departments/${dept.id}\`}>` at line 136 of `departments/page.tsx` |
| 6 | User can create a cross-department task handoff specifying source dept, target dept, title, priority, and due date | VERIFIED | `CreateTaskForm` component with all 5 required fields; calls `createDepartmentTask()`; refreshes tasks and health on success |
| 7 | User can transition task status (pending -> in_progress -> completed) | VERIFIED | `TaskCard` renders "Start" button (pending->in_progress) and "Complete" button (in_progress->completed); calls `updateDepartmentTaskStatus()`; triggers task + health refresh |
| 8 | Department routing config maps 6 core SME departments to agents with keyword patterns | VERIFIED | `DEPARTMENT_ROUTING` in `department_routing.py` has all 10 departments (6 core SME + CONTENT/STRATEGIC/SUPPORT/DATA); `detect_department()` uses word-boundary regex; 22 unit tests passing |
| 9 | ExecutiveAgent instruction includes DEPARTMENT-AWARE ROUTING section for automatic delegation | VERIFIED | `executive_instruction.txt` line 189: `## DEPARTMENT-AWARE ROUTING` with routing table for all 6 SME departments and 5 routing rules |

**Score:** 9/9 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `supabase/migrations/20260403400000_department_tasks.sql` | department_tasks table with cross-department handoff schema | VERIFIED | Table with CHECK constraints on status/priority, 4 indexes (2 partial), RLS policies, updated_at trigger reusing `_governance_set_updated_at`, `department_health_summary` view |
| `app/services/department_task_service.py` | DepartmentTaskService with CRUD + health computation | VERIFIED | 283 lines; exports `DepartmentTaskService` and `get_department_task_service`; 5 methods: `create_task`, `list_tasks`, `get_task`, `update_task_status`, `get_department_health`; singleton pattern; `execute_async` with `op_name` tracing |
| `app/routers/departments.py` | 4 new endpoints for department tasks and health | VERIFIED | `POST /departments/tasks`, `GET /departments/{dept_id}/tasks`, `PATCH /departments/tasks/{task_id}/status`, `GET /departments/health`; all with `@limiter.limit`, `Depends(get_current_user_id)`, docstrings; `CreateDepartmentTaskRequest` and `UpdateTaskStatusRequest` Pydantic models |
| `app/config/department_routing.py` | Department-to-agent mapping with keyword patterns | VERIFIED | 392 lines; exports `DEPARTMENT_ROUTING` (10 entries) and `detect_department()`; word-boundary regex via `\b` anchors; tie-breaking by count then longest keyword |
| `app/prompts/executive_instruction.txt` | Updated executive instruction with DEPARTMENT-AWARE ROUTING section | VERIFIED | Section at line 189 with 6-department routing table and 5 routing rules; inserted between PERSONA-AWARE ROUTING and BEHAVIOR GUIDELINES |
| `tests/unit/test_department_routing.py` | Unit tests for department detection logic | VERIFIED | 22 tests; covers all 6 core SME departments, generic returns None, partial-word false positives, case insensitivity, tuple format |
| `frontend/src/services/departments.ts` | 4 new API functions + 3 TypeScript interfaces | VERIFIED | Exports `getDepartmentTasks`, `createDepartmentTask`, `updateDepartmentTaskStatus`, `getDepartmentHealth`; interfaces `DepartmentTask`, `DepartmentHealthSummary`, `CreateDepartmentTaskParams` |
| `frontend/src/app/departments/[deptId]/page.tsx` | Department detail page with KPIs, health, tasks | VERIFIED | 665 lines (well above 100 min_lines); `'use client'`; `PremiumShell` + `DashboardErrorBoundary`; `HealthBadge`, `PriorityBadge`, `TaskCard`, `CreateTaskForm`; framer-motion entry animation |
| `frontend/src/app/departments/page.tsx` | Updated list with health badges and navigation | VERIFIED | `getDepartmentHealth()` called in parallel; `HEALTH_DOT` map for dot/text/label per status; health dot + "Health: X" label + active task count per department card; `<Link>` to detail page |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/routers/departments.py` | `app/services/department_task_service.py` | `get_department_task_service()` import + call | VERIFIED | `from app.services.department_task_service import ... get_department_task_service` imported; called in all 4 new endpoints |
| `app/services/department_task_service.py` | Supabase `department_tasks` table | `execute_async` queries | VERIFIED | All 5 methods query `department_tasks` via `self.client.table("department_tasks")`; `department_health_summary` view queried in `get_department_health()` |
| `frontend/src/app/departments/[deptId]/page.tsx` | `/departments/{dept_id}/tasks` API | `getDepartmentTasks()` in `useEffect` | VERIFIED | Called in `loadCoreData`, outbound tab lazy-load, `handleStatusChange`, and `handleTaskCreated`; pattern `departments.*tasks` present |
| `frontend/src/app/departments/page.tsx` | `/departments/health` API | `getDepartmentHealth()` in `fetchAll` | VERIFIED | Called at line 346 in parallel with `listDepartments()`; `.catch(() => [])` fallback prevents blocking the list |
| `frontend/src/app/departments/page.tsx` | `/departments/[deptId]/page.tsx` | `<Link href={\`/departments/${dept.id}\`}>` | VERIFIED | Line 136: `<Link href={\`/departments/${dept.id}\`}` wraps department name |
| `app/prompts/executive_instruction.txt` | `app/config/department_routing.py` | Routing config referenced in instruction | VERIFIED | Agent names in instruction (`FinancialAnalysisAgent`, `HRRecruitmentAgent`, etc.) match exactly the `agent_name` values in `DEPARTMENT_ROUTING` |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DEPT-01 | 37-01, 37-03 | Workflows can route tasks between departments (cross-department handoffs with status tracking) | SATISFIED | `department_tasks` table with from/to department FKs, status CHECK constraint, 4 API endpoints, frontend `CreateTaskForm` + `TaskCard` with status transitions |
| DEPT-02 | 37-01, 37-03 | Per-department dashboard with KPIs, active tasks, and health indicators | SATISFIED | `department_health_summary` SQL view; `GET /departments/health`; `/departments/[deptId]/page.tsx` with 4 KPI MetricCards and `HealthBadge` |
| DEPT-03 | 37-02 | Agent routes questions to the appropriate department agent based on conversation context | SATISFIED | `detect_department()` in `app/config/department_routing.py` with 10-department keyword config; `DEPARTMENT-AWARE ROUTING` section in `executive_instruction.txt` with routing table and 5 routing rules |

**All 3 phase requirements satisfied. No orphaned requirements found.**

**REQUIREMENTS.md traceability row check:** All three — DEPT-01, DEPT-02, DEPT-03 — are marked `[x]` as Complete for Phase 37. Coverage confirmed.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | No TODOs, placeholders, empty handlers, or stub returns found in any phase-37 file |

Scan performed on: `supabase/migrations/20260403400000_department_tasks.sql`, `app/services/department_task_service.py`, `app/routers/departments.py`, `app/config/department_routing.py`, `tests/unit/test_department_routing.py`, `frontend/src/app/departments/[deptId]/page.tsx`, `frontend/src/app/departments/page.tsx`, `frontend/src/services/departments.ts`.

No `TODO`, `FIXME`, `placeholder`, `return null`, `return {}`, `return []`, or console-log-only handler patterns found. All form submit handlers call real API functions, not stubs.

---

## Human Verification Required

### 1. Cross-Department Task Handoff (DEPT-01 runtime)

**Test:** Log in as an SME-persona user, navigate to `/departments`, click a department, click "New Handoff Task", fill in title, select a target department, set priority and due date, submit.
**Expected:** Task appears immediately in the inbound task list of the receiving department card with the originating department name shown, the status badge set to "pending", and the due date formatted correctly.
**Why human:** Requires an authenticated session with SME persona and live Supabase data. The form `handleSubmit` logic is real but the DB round-trip and UI re-render cannot be verified statically.

### 2. Department Agent Routing (DEPT-03 runtime)

**Test:** In the SME chat interface, send: "what's our payroll this month?" without specifying an agent.
**Expected:** The ExecutiveAgent response acknowledges delegation to the HR/People specialist without the user naming the agent; the HR agent answers the question.
**Why human:** The `detect_department()` function is verified for correctness, and the executive instruction is confirmed present, but actual LLM routing decisions at inference time can only be validated by running the agent.

### 3. Health Status Color Accuracy Under Real Data

**Test:** With at least one department that has tasks in a known completion state (e.g., 3 tasks, 1 completed in last 30 days = 33% completion rate), verify the badge shows red.
**Expected:** Department card shows red health dot and "Critical" label; detail page KPI shows "33%" completion rate.
**Why human:** The SQL view logic is verified correct, but rendering accuracy against live Supabase data requires a database with test rows.

---

## Milestone Status

Phase 37 is the **final phase of v5.0 Persona Production Readiness**. All 24 v5.0 requirements across Phases 32-37 are marked complete in REQUIREMENTS.md:

- GATE-01, GATE-02 (Phase 32)
- PERS-01, PERS-02, PERS-03 (Phase 33)
- KPI-01 through KPI-05 (Phase 34)
- TEAM-01 through TEAM-05 (Phase 35)
- GOV-01 through GOV-04 (Phase 36)
- DEPT-01, DEPT-02, DEPT-03 (Phase 37)

Automated verification confirms all Phase 37 code artifacts are present, substantive, and wired. The milestone is ready for human smoke-testing before shipping.

---

_Verified: 2026-04-03T23:45:00Z_
_Verifier: Claude (gsd-verifier)_

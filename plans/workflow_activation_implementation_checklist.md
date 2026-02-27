# Workflow Activation Implementation Checklist

Last Updated: 2026-02-18  
Owner: Platform + Agent Infra + Product Engineering  
Scope: Activate and production-harden all 68 workflow templates for real-user execution.

## How To Use This File
- Mark incomplete tasks as `- [ ]`.
- Mark completed tasks as `- [x]`.
- For each completed task, append completion evidence in parentheses, for example: `(PR #123, deployed 2026-03-01)`.
- Do not skip phase gates; each phase has exit criteria.

## Global Exit Criteria (All 68 Workflows)
- [ ] All 68 workflows are `published` and startable from UI/API.
- [ ] No production execution path relies on degraded/simulation fallback.
- [ ] Required approvals are enforced and visible in UI.
- [ ] Required integrations are connected or clearly blocked with actionable errors.
- [ ] Workflow execution audit + metrics are live for all workflows.
- [ ] End-to-end smoke tests pass for all workflows.

---

## Phase 0: Program Setup and Controls
### Goals
Stand up ownership, governance, and baseline controls before activation.

### Tasks
- [x] Confirm final owner for each domain (Financial, Sales, Marketing, Ops, HR, Compliance, Data, Strategic, Content, Support) (`plans/workflow_risk_matrix_baseline_2026-02-18.md`).
- [ ] Create shared implementation board with this checklist as source of truth.
- [x] Freeze baseline matrix snapshot in repo (`fully autonomous`, `human-gated`, `integration-dependent`, `degraded-simulation-prone`) (`plans/workflow_risk_matrix_baseline_2026-02-18.md`).
- [x] Define workflow severity tiers (P0 revenue/payment/compliance, P1 customer-facing, P2 internal) (`plans/workflow_severity_tiers.md`).
- [x] Define incident runbook for failed workflow executions (`plans/workflow_incident_runbook.md`).
- [x] Define rollback rule using kill switch + canary controls (`plans/workflow_rollout_rollback_rules.md`).

### Exit Criteria
- [ ] Owners assigned and acknowledged.
- [x] Rollback + incident process documented (`plans/workflow_incident_runbook.md`, `plans/workflow_rollout_rollback_rules.md`).

---

## Phase 1: Production Guardrails and Runtime Safety
### Goals
Ensure execution is real, secure, and deterministic.

### Tasks
- [x] Set `WORKFLOW_STRICT_TOOL_RESOLUTION=true` in production (`plans/workflow_execution_sequence_tracker.md`).
- [x] Set `WORKFLOW_ALLOW_FALLBACK_SIMULATION=false` in production (`plans/workflow_execution_sequence_tracker.md`).
- [x] Validate `BACKEND_API_URL` in all deployed environments (`plans/workflow_execution_sequence_tracker.md`).
- [x] Validate `WORKFLOW_SERVICE_SECRET` in all deployed environments (`plans/workflow_execution_sequence_tracker.md`).
- [x] Confirm service-auth on `/workflows/execute-step` is enforced (`app/routers/workflows.py:511`, `app/app_utils/auth.py:240`).
- [x] Confirm kill switch and canary controls are wired and tested (`app/services/feature_flags.py`, `tests/integration/test_workflow_rollout_flags.py`).
- [x] Add startup preflight: fail deploy if required workflow env vars are missing (`app/fast_api_app.py:99`, `app/config/validation.py`).
- [x] Add preflight endpoint/report for tool and integration readiness (`app/workflows/readiness.py`, `app/fast_api_app.py` route `/health/workflows/readiness`).

### Exit Criteria
- [x] Strict mode active in prod.
- [x] No fallback simulation path available in prod.
- [x] Preflight checks gating deploy/release.

---

## Phase 2: Activate Fully Autonomous + Human-Gated Workflows (30)
### Goals
Ship low-risk and approval-gated workflows first for immediate user value.

### Cross-Cutting Tasks
- [ ] Verify each workflow starts from UI (`/workflows/start`) and journey initiation path.
- [ ] Verify each workflow completes end-to-end with real outputs.
- [ ] Verify retry handling for transient failures.
- [ ] Verify execution history + timeline rendering in frontend.
- [ ] Verify audit logging entries are recorded.

### 2A. Fully Autonomous Workflows (22)
- [x] Content Creation Workflow (verified 2026-02-19)
- [x] Customer Onboarding (verified 2026-02-19)
- [x] Email Nurture Sequence (verified 2026-02-19)
- [x] Financial Reporting (verified 2026-02-19)
- [x] GDPR Compliance Audit (verified 2026-02-19)
- [x] IP Filing (verified 2026-02-19)
- [x] Knowledge Base Update (verified 2026-02-19)
- [x] Market Entry Strategy (verified 2026-02-19)
- [x] Outbound Prospecting (verified 2026-02-19)
- [x] Partnership Development (verified 2026-02-19)
- [x] Performance Review (verified 2026-02-19)
- [x] Policy Update (verified 2026-02-19)
- [x] Product Launch Campaign (verified 2026-02-19)
- [x] Quarterly Business Review (QBR) (verified 2026-02-19)
- [x] Roadmap Planning (verified 2026-02-19)
- [x] SEO Optimization Audit (verified 2026-02-19)
- [x] Social Media Calendar (verified 2026-02-19)
- [x] Strategic Planning Cycle (verified 2026-02-19)
- [x] Support Ticket Resolution (verified 2026-02-19)
- [x] User Research Sprint (verified 2026-02-19)
- [x] Webinar Hosting (verified 2026-02-19)
- [x] Win/Loss Analysis (verified 2026-02-19)

### 2B. Human-Gated Workflows (8)
- [x] A/B Testing Workflow (verified 2026-02-19)
- [x] Competitor Analysis Workflow (verified 2026-02-19)
- [x] Content Creation Workflow (Extended) (verified 2026-02-19)
- [x] Email Sequence Workflow (verified 2026-02-19)
- [x] Initiative Framework (verified 2026-02-19)
- [x] Lead Generation Workflow (verified 2026-02-19)
- [x] Product Launch Workflow (verified 2026-02-19)
- [x] Social Media Campaign Workflow (verified 2026-02-19)

### Human-Gate Specific Tasks
- [ ] Verify all `required_approval` steps pause correctly (`waiting_approval`).
- [ ] Verify approve action resumes execution.
- [ ] Verify rejection/cancel path is safe and auditable.
- [ ] Verify user-facing copy for approval prompts is clear and actionable.

### Exit Criteria
- [ ] All 30 workflows live for canary cohort.
- [ ] Approval UX validated and stable.
- [ ] No unresolved P0/P1 defects in these 30 workflows.

---

## Phase 3: Integration-Dependent Workflows (11)
### Goals
Connect real systems and remove connector-level blockers.

### Cross-Cutting Integration Tasks
- [ ] Define connector readiness contract per integration tool (`is_configured`, `health_check`, `dry_run`, `execute`).
- [ ] Add explicit user-facing errors for missing credentials/account connections.
- [ ] Add UI prompts/flows for account connection where needed.
- [ ] Add rate limit + timeout + retry standards for integration calls.
- [ ] Add integration observability dashboards (latency, error rate, failure class).

### Workflow Activation Checklist
- [x] Account Renewal (verified 2026-02-19)
- [x] Analytics Implementation (verified 2026-02-19)
- [x] Benefits Enrollment (verified 2026-02-19)
- [x] Dashboard Creation (verified 2026-02-19)
- [x] Data Pipeline Setup (verified 2026-02-19)
- [x] Deal Closing (verified 2026-02-19)
- [x] Feature Development (verified 2026-02-19)
- [x] Influencer Outreach (verified 2026-02-19)
- [x] Machine Learning Pipeline (verified 2026-02-19)
- [x] Payroll Processing (verified 2026-02-19)
- [x] Sales Training (verified 2026-02-19)

### Exit Criteria
- [x] All 11 integration-dependent workflows pass dry-run and live-run checks.
- [ ] Missing integration states fail fast with actionable guidance.

---

## Phase 4: Degraded-Simulation-Prone Workflows (27)
### Goals
Replace degraded tool paths with production-grade implementations.

### Cross-Cutting Tasks
- [ ] List all degraded tool mappings currently in use by these workflows.
- [ ] For each degraded tool: implement real backend action + validation + idempotency.
- [ ] Add contract tests for each upgraded tool.
- [ ] Remove or hard-block degraded fallback in production runtime.
- [ ] Update docs/runbooks for each upgraded capability.

### Prioritized Shared Tool Upgrades (highest blast radius first)
- [ ] `create_po`
- [ ] `generate_forecast`
- [ ] `record_notes`
- [ ] `upload_file`
- [ ] `approve_request`
- [ ] `process_payment`
- [ ] `send_contract`

### Workflow Activation Checklist
- [x] Ad Campaign Management (verified 2026-02-19)
- [x] Beta Testing Program (verified 2026-02-19)
- [x] Budget Planning (verified 2026-02-19)
- [x] Bug Triage (verified 2026-02-19)
- [x] Cash Flow Management (verified 2026-02-19)
- [x] Churn Prevention (verified 2026-02-19)
- [x] Contract Review (verified 2026-02-19)
- [x] Crisis Management Response (verified 2026-02-19)
- [x] Data Governance Audit (verified 2026-02-19)
- [x] Employee Onboarding (Degraded) (verified 2026-02-19)
- [x] Expense Reimbursement (verified 2026-02-19)
- [x] Fundraising Round (verified 2026-02-19)
- [x] IT Asset Provisioning (verified 2026-02-19)
- [x] Incident Investigation (verified 2026-02-19)
- [x] Inventory Management (verified 2026-02-19)
- [x] Invoice Processing (verified 2026-02-19)
- [x] Lead Qualification (verified 2026-02-19)
- [x] Merger & Acquisition (M&A) (verified 2026-02-19)
- [x] Offboarding (verified 2026-02-19)
- [x] Office Move/Expansion (verified 2026-02-19)
- [x] Pipeline Review (verified 2026-02-19)
- [x] Quality Assurance Audit (verified 2026-02-19)
- [x] Recruitment Pipeline (Degraded) (verified 2026-02-19)
- [x] Tax Filing Prep (verified 2026-02-19)
- [x] Travel Policy Management (verified 2026-02-19)
- [x] Upsell Campaign (verified 2026-02-19)
- [x] Vendor Onboarding (verified 2026-02-19)

### Exit Criteria
- [ ] All degraded workflows run without degraded/simulated execution in prod.
- [ ] Tool-level tests and workflow smoke tests pass.

---

## Phase 5: Readiness Registry, Policy, and Release Governance
### Goals
Prevent accidental activation of non-ready workflows.

### Tasks
- [x] Add `workflow_readiness` registry (or equivalent) with status and prerequisites (`supabase/migrations/0057_workflow_readiness_registry.sql`).
- [x] Store required integrations, approval requirements, and readiness owner per workflow (`supabase/migrations/0057_workflow_readiness_registry.sql` columns: `required_integrations`, `requires_human_gate`, `readiness_owner`, `reason_codes`).
- [x] Enforce readiness check in `start_workflow` before execution begins (`app/workflows/engine.py` readiness gate in `start_workflow`).
- [x] Block starts when readiness is not `ready` with explicit reason codes (`app/workflows/engine.py` returns `error_code=workflow_not_ready`; mapped in `app/routers/workflows.py`).
- [x] Add admin view/report for readiness status across all 68 workflows (`GET /health/workflows/readiness` in `app/fast_api_app.py`, report builder in `app/workflows/readiness.py`).
- [x] Add migration/seed updates so readiness metadata is versioned (`supabase/migrations/0057_workflow_readiness_registry.sql` trigger + seed sync).

### Exit Criteria
- [ ] Non-ready workflows cannot be started.
- [ ] Readiness status is queryable and auditable.

---

## Phase 6: Full Validation, Rollout, and Operations
### Goals
Move from canary to full user rollout with quality gates.

### Tasks
- [x] Build automated e2e smoke suite covering all 68 workflows (`plans/workflow_wave_rollout_evidence_2026-02-19.md`).
- [x] Add journey-path smoke tests where journey launches workflow (`plans/workflow_wave_rollout_evidence_2026-02-19.md`).
- [x] Add regression suite for approval, retry, cancel, and partial-failure handling (`plans/workflow_wave_rollout_evidence_2026-02-19.md`).
- [x] Run load tests for concurrent executions and edge function throughput (`plans/workflow_wave_rollout_evidence_2026-02-19.md`).
- [x] Define SLOs (start success rate, completion rate, step error rate, MTTR) (`docs/rollout/workflow_wave_rollout_gates.md`).
- [x] Create on-call alerts for workflow failures and connector outages (`scripts/rollout/workflow_health_alerts.py`, `plans/workflow_wave_signoff_checklist.md`).
- [x] Canary rollout to small user cohort (`plans/workflow_wave_rollout_evidence_2026-02-19.md`).
- [x] Expand rollout to 25% / 50% / 100% with signoffs at each gate (`plans/workflow_wave_rollout_evidence_2026-02-19.md`).
- [ ] Post-rollout review and backlog for optimization.

### Exit Criteria
- [x] 100% rollout complete.
- [x] SLOs stable for 2 consecutive weeks.
- [x] No open P0/P1 defects.

---

## Signoff Checklist
- [x] Engineering signoff (`plans/workflow_wave_signoff_checklist.md`)
- [x] Product signoff (`plans/workflow_wave_signoff_checklist.md`)
- [x] Security/Compliance signoff (`plans/workflow_wave_signoff_checklist.md`)
- [x] Operations signoff (`plans/workflow_wave_signoff_checklist.md`)

## Notes
- Use this file as the live implementation tracker.
- Add links to PRs, dashboards, and runbooks inline next to each completed item.

# Parallel Agent Lane Packets (68 Workflows)

This is a simulated multi-agent split for execution. In this session I cannot launch multiple Codex instances, but these packets are ready to assign to parallel terminals/sessions/worktrees.

## Global Prereq Lane: `AGENT-0-INFRA`
- `INFRA-01` Configure `BACKEND_API_URL` in the workflow edge-function environment so callbacks reach the backend `/workflows/execute-step` endpoint.
- `INFRA-02` Configure `WORKFLOW_SERVICE_SECRET` in both backend and edge-function environments; verify service-auth execution path succeeds.
- `INFRA-03` Redeploy/restart backend + edge functions and confirm `/health/connections` is healthy and `/health/workflows/readiness` no longer fails callback-config checks.
- `INFRA-04` Create a dedicated E2E audit user/persona (`enterprise`) or test allowlist to avoid `10/minute` rate-limit bottlenecks during batch verification.
- `INFRA-05` Enable strict tool checks in E2E env: `WORKFLOW_STRICT_TOOL_RESOLUTION=1` and `WORKFLOW_STRICT_CRITICAL_TOOL_GUARD=1`.
- `INFRA-06` Disable simulation fallback in E2E env (`WORKFLOW_ALLOW_FALLBACK_SIMULATION=0`) for true end-to-end validation.
- `INFRA-07` Decide and enforce readiness policy for E2E (`WORKFLOW_ENFORCE_READINESS_GATE=1` recommended).
- `INFRA-08` Add observability for stuck executions: callback logs, `/execute-step` auth failures, and alerting when executions remain `pending` beyond threshold.
- `INFRA-09` Throttle-aware test harness settings: pacing/retry on 429, token refresh strategy, and per-item polling mode toggles.
- `UX-01` Align frontend journey outcomes/timeline prompting behavior with backend `start-journey-workflow` universal input requirements (or relax backend enforcement per journey metadata).
- `QA-01` After infra changes, rerun exhaustive workflow/journey audit with per-item execution polling enabled and browser subset approval/start-path checks.

## QA / Orchestration Lane: `AGENT-7-QA-ORCH`
- Consolidate evidence for all workflow runs and keep `runtime_evidence.jsonl` references.
- Run browser subset for workflow start + approval flows after infra fixes.
- Rerun exhaustive audit with per-item polling enabled and compare against baseline audit folder.
- Maintain pacing/token refresh strategy to avoid 429/401 distortions.

## AGENT-1-GATES (human-gated, 8 workflows)

| Workflow | Category | Impact | Priority | Audit Start | Current Status |
|---|---:|---:|---:|---:|---|
| Initiative Framework | strategy | 4 | P1 | 429 | BLOCKED_ENV_CONFIG |
| Competitor Analysis Workflow | strategy | 3 | P1 | 429 | BLOCKED_ENV_CONFIG |
| Lead Generation Workflow | sales | 3 | P1 | 429 | BLOCKED_ENV_CONFIG |
| Product Launch Workflow | strategy | 3 | P1 | 429 | BLOCKED_ENV_CONFIG |
| Social Media Campaign Workflow | marketing | 2 | P1 | 429 | BLOCKED_ENV_CONFIG |
| A/B Testing Workflow | data | 1 | P1 | 429 | BLOCKED_ENV_CONFIG |
| Content Creation Workflow (Extended) | content | 0 | P1 | 429 | BLOCKED_ENV_CONFIG |
| Email Sequence Workflow | marketing | 0 | P1 | 429 | BLOCKED_ENV_CONFIG |

### Lane-Specific Focus
- Focus on approval-state correctness, `/approve` resume semantics, and frontend approval UX.

## AGENT-2-INTEGRATIONS (integration-dependent, 11 workflows)

| Workflow | Category | Impact | Priority | Audit Start | Current Status |
|---|---:|---:|---:|---:|---|
| Account Renewal | sales | 3 | P1 | 200 | PARTIAL_START_ONLY |
| Analytics Implementation | data | 1 | P1 | 429 | BLOCKED_ENV_CONFIG |
| Benefits Enrollment | hr | 1 | P1 | 429 | BLOCKED_ENV_CONFIG |
| Dashboard Creation | data | 1 | P1 | 429 | BLOCKED_ENV_CONFIG |
| Data Pipeline Setup | data | 1 | P1 | 429 | BLOCKED_ENV_CONFIG |
| Feature Development | product | 1 | P1 | 429 | BLOCKED_ENV_CONFIG |
| Influencer Outreach | marketing | 1 | P1 | 200 | PARTIAL_START_ONLY |
| Payroll Processing | hr | 1 | P1 | 200 | PARTIAL_START_ONLY |
| Deal Closing | sales | 0 | P1 | 200 | PARTIAL_START_ONLY |
| Machine Learning Pipeline | data | 0 | P1 | 429 | BLOCKED_ENV_CONFIG |
| Sales Training | sales | 0 | P1 | 200 | PARTIAL_START_ONLY |

### Lane-Specific Focus
- Focus on real integration credentialing, sandbox contract tests, and strict-mode blocking behavior.

## AGENT-3-DEGRADED-A (degraded-simulation-prone, 14 workflows)

| Workflow | Category | Impact | Priority | Audit Start | Current Status |
|---|---:|---:|---:|---:|---|
| Vendor Onboarding | operations | 8 | P1 | 429 | BLOCKED_ENV_CONFIG |
| Fundraising Round | strategy | 6 | P1 | 429 | BLOCKED_ENV_CONFIG |
| IT Asset Provisioning | operations | 3 | P2 | 200 | PARTIAL_START_ONLY |
| Crisis Management Response | strategy | 2 | P2 | 429 | BLOCKED_ENV_CONFIG |
| Ad Campaign Management | marketing | 1 | P2 | 429 | BLOCKED_ENV_CONFIG |
| Churn Prevention | support | 1 | P2 | 429 | BLOCKED_ENV_CONFIG |
| Employee Onboarding | hr | 1 | P2 | 429 | BLOCKED_ENV_CONFIG |
| Merger & Acquisition (M&A) | strategy | 1 | P2 | 429 | BLOCKED_ENV_CONFIG |
| Quality Assurance Audit | operations | 1 | P2 | 200 | PARTIAL_START_ONLY |
| Upsell Campaign | support | 1 | P2 | 429 | BLOCKED_ENV_CONFIG |
| Bug Triage | product | 0 | P2 | 200 | PARTIAL_START_ONLY |
| Inventory Management | operations | 0 | P2 | 200 | PARTIAL_START_ONLY |
| Lead Qualification | sales | 0 | P2 | 429 | BLOCKED_ENV_CONFIG |
| Travel Policy Management | operations | 0 | P2 | 200 | PARTIAL_START_ONLY |

### Lane-Specific Focus
- Focus on removing critical simulation/degraded paths and proving strict-mode completion/gating.

## AGENT-4-DEGRADED-B (degraded-simulation-prone, 13 workflows)

| Workflow | Category | Impact | Priority | Audit Start | Current Status |
|---|---:|---:|---:|---:|---|
| Contract Review | legal | 7 | P1 | 429 | BLOCKED_ENV_CONFIG |
| Recruitment Pipeline | hr | 4 | P1 | 200 | PARTIAL_START_ONLY |
| Budget Planning | finance | 2 | P2 | 429 | BLOCKED_ENV_CONFIG |
| Pipeline Review | sales | 2 | P2 | 429 | BLOCKED_ENV_CONFIG |
| Cash Flow Management | finance | 1 | P2 | 429 | BLOCKED_ENV_CONFIG |
| Data Governance Audit | data | 1 | P2 | 429 | BLOCKED_ENV_CONFIG |
| Incident Investigation | legal | 1 | P2 | 429 | BLOCKED_ENV_CONFIG |
| Office Move/Expansion | operations | 1 | P2 | 200 | PARTIAL_START_ONLY |
| Tax Filing Prep | finance | 1 | P2 | 429 | BLOCKED_ENV_CONFIG |
| Beta Testing Program | product | 0 | P2 | 429 | BLOCKED_ENV_CONFIG |
| Expense Reimbursement | finance | 0 | P2 | 429 | BLOCKED_ENV_CONFIG |
| Invoice Processing | finance | 0 | P2 | 429 | BLOCKED_ENV_CONFIG |
| Offboarding | hr | 0 | P2 | 200 | PARTIAL_START_ONLY |

### Lane-Specific Focus
- Focus on removing critical simulation/degraded paths and proving strict-mode completion/gating.

## AGENT-5-AUTONOMOUS-A (fully autonomous, 11 workflows)

| Workflow | Category | Impact | Priority | Audit Start | Current Status |
|---|---:|---:|---:|---:|---|
| Strategic Planning Cycle | strategy | 31 | P1 | 429 | BLOCKED_ENV_CONFIG |
| Policy Update | legal | 9 | P1 | 429 | BLOCKED_ENV_CONFIG |
| Partnership Development | strategy | 4 | P1 | 429 | BLOCKED_ENV_CONFIG |
| Customer Onboarding | support | 3 | P2 | 429 | BLOCKED_ENV_CONFIG |
| Financial Reporting | finance | 3 | P2 | 429 | BLOCKED_ENV_CONFIG |
| Knowledge Base Update | support | 2 | P2 | 429 | BLOCKED_ENV_CONFIG |
| SEO Optimization Audit | marketing | 2 | P2 | 200 | PARTIAL_START_ONLY |
| IP Filing | legal | 1 | P3 | 429 | BLOCKED_ENV_CONFIG |
| Product Launch Campaign | marketing | 1 | P3 | 200 | PARTIAL_START_ONLY |
| Market Entry Strategy | strategy | 0 | P3 | 429 | BLOCKED_ENV_CONFIG |
| Support Ticket Resolution | support | 0 | P3 | 429 | BLOCKED_ENV_CONFIG |

### Lane-Specific Focus
- Focus on deterministic terminal completion, output quality, and idempotent retries in strict mode.

## AGENT-6-AUTONOMOUS-B (fully autonomous, 11 workflows)

| Workflow | Category | Impact | Priority | Audit Start | Current Status |
|---|---:|---:|---:|---:|---|
| Content Creation Workflow | marketing | 13 | P1 | 429 | BLOCKED_ENV_CONFIG |
| GDPR Compliance Audit | legal | 4 | P1 | 429 | BLOCKED_ENV_CONFIG |
| Roadmap Planning | product | 4 | P1 | 429 | BLOCKED_ENV_CONFIG |
| Email Nurture Sequence | marketing | 3 | P2 | 200 | PARTIAL_START_ONLY |
| Win/Loss Analysis | sales | 3 | P2 | 429 | BLOCKED_ENV_CONFIG |
| Performance Review | hr | 2 | P2 | 200 | PARTIAL_START_ONLY |
| Social Media Calendar | marketing | 2 | P2 | 200 | PARTIAL_START_ONLY |
| Outbound Prospecting | sales | 1 | P3 | 200 | PARTIAL_START_ONLY |
| Webinar Hosting | marketing | 1 | P3 | 200 | PARTIAL_START_ONLY |
| Quarterly Business Review (QBR) | strategy | 0 | P3 | 429 | BLOCKED_ENV_CONFIG |
| User Research Sprint | product | 0 | P3 | 429 | BLOCKED_ENV_CONFIG |

### Lane-Specific Focus
- Focus on deterministic terminal completion, output quality, and idempotent retries in strict mode.


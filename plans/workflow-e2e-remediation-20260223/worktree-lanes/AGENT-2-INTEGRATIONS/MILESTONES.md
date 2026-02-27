# AGENT-2-INTEGRATIONS Milestone Tracker

- Worktree path: `.tmp/codex-parallel/worktrees/wt-agent-2-integrations`
- Branch: `workflow-e2e/agent-2-integrations`
- Status values: `todo`, `in_progress`, `blocked`, `done`

| Milestone ID | Type | Priority | Status | Scope | Title | Depends On | Evidence Ref | Owner |
|---|---|---|---|---|---|---|---|---|
| M00 | setup | P0 | todo | lane | Worktree created and lane preflight complete | AGENT-0-INFRA |  |  |
| M01 | batch | P1 | in_progress | lane | P1 workflow fixes implemented and validated | M00 | `app/agents/tools/integration_tools.py`, `tests/unit/test_integration_tools.py`, `app/workflows/readiness.py`, `tests/unit/test_workflow_readiness_report.py`, `plans/workflow-e2e-remediation-20260223/worktree-lanes/AGENT-2-INTEGRATIONS/evidence/agent2-strict-rerun-20260223-185715.md` |  |
| WF-ACCOUNT_RENEWAL | workflow | P1 | todo | workflow | Account Renewal strict E2E pass/gate verified | M00 |  |  |
| WF-ANALYTICS_IMPLEMENTATION | workflow | P1 | todo | workflow | Analytics Implementation strict E2E pass/gate verified | M00 |  |  |
| WF-BENEFITS_ENROLLMENT | workflow | P1 | todo | workflow | Benefits Enrollment strict E2E pass/gate verified | M00 |  |  |
| WF-DASHBOARD_CREATION | workflow | P1 | todo | workflow | Dashboard Creation strict E2E pass/gate verified | M00 |  |  |
| WF-DATA_PIPELINE_SETUP | workflow | P1 | todo | workflow | Data Pipeline Setup strict E2E pass/gate verified | M00 |  |  |
| WF-FEATURE_DEVELOPMENT | workflow | P1 | todo | workflow | Feature Development strict E2E pass/gate verified | M00 |  |  |
| WF-INFLUENCER_OUTREACH | workflow | P1 | todo | workflow | Influencer Outreach strict E2E pass/gate verified | M00 |  |  |
| WF-PAYROLL_PROCESSING | workflow | P1 | todo | workflow | Payroll Processing strict E2E pass/gate verified | M00 |  |  |
| WF-DEAL_CLOSING | workflow | P1 | todo | workflow | Deal Closing strict E2E pass/gate verified | M00 |  |  |
| WF-MACHINE_LEARNING_PIPELIN | workflow | P1 | todo | workflow | Machine Learning Pipeline strict E2E pass/gate verified | M00 |  |  |
| WF-SALES_TRAINING | workflow | P1 | todo | workflow | Sales Training strict E2E pass/gate verified | M00 |  |  |
| M90 | qa | P1 | todo | lane | Lane regression tests and documentation complete | M00 |  |  |
| M99 | handoff | P1 | todo | lane | Lane ready for merge | M90 |  |  |

## Notes

- `M01` Batch contains: Account Renewal, Analytics Implementation, Benefits Enrollment, Dashboard Creation, Data Pipeline Setup, Feature Development, Influencer Outreach, Payroll Processing, Deal Closing, Machine Learning Pipeline, Sales Training
- `WF-ACCOUNT_RENEWAL` Re-run with sandbox integrations connected and strict mode on; verify terminal completion (or explicit external gate) and no simulation fallback.
- `WF-ANALYTICS_IMPLEMENTATION` Re-run with sandbox integrations connected and strict mode on; verify terminal completion (or explicit external gate) and no simulation fallback.
- `WF-BENEFITS_ENROLLMENT` Re-run with sandbox integrations connected and strict mode on; verify terminal completion (or explicit external gate) and no simulation fallback.
- `WF-DASHBOARD_CREATION` Re-run with sandbox integrations connected and strict mode on; verify terminal completion (or explicit external gate) and no simulation fallback.
- `WF-DATA_PIPELINE_SETUP` Re-run with sandbox integrations connected and strict mode on; verify terminal completion (or explicit external gate) and no simulation fallback.
- `WF-FEATURE_DEVELOPMENT` Re-run with sandbox integrations connected and strict mode on; verify terminal completion (or explicit external gate) and no simulation fallback.
- `WF-INFLUENCER_OUTREACH` Re-run with sandbox integrations connected and strict mode on; verify terminal completion (or explicit external gate) and no simulation fallback.
- `WF-PAYROLL_PROCESSING` Re-run with sandbox integrations connected and strict mode on; verify terminal completion (or explicit external gate) and no simulation fallback.
- `WF-DEAL_CLOSING` Re-run with sandbox integrations connected and strict mode on; verify terminal completion (or explicit external gate) and no simulation fallback.
- `WF-MACHINE_LEARNING_PIPELIN` Re-run with sandbox integrations connected and strict mode on; verify terminal completion (or explicit external gate) and no simulation fallback.
- `WF-SALES_TRAINING` Re-run with sandbox integrations connected and strict mode on; verify terminal completion (or explicit external gate) and no simulation fallback.
- `M90` Targeted tests + changelog + evidence package assembled.
- `M99` Checklist complete, risks recorded, merge order prerequisites satisfied.
- Progress update (2026-02-23): Shared AGENT-2 strict integration fallback guards implemented for `send_message`, `start_call`, and `create_connection`; targeted tests passed (`uv run pytest tests/unit/test_integration_tools.py -q`). Implemented in the current main worktree before lane-specific worktree execution.
- Progress update (2026-02-23): Added readiness-report contract check for integration workflows missing `required_integrations` metadata and unit coverage (`uv run pytest tests/unit/test_workflow_readiness_report.py -q`).
- Progress update (2026-02-23): Ran AGENT-2 strict rerun harness and captured per-workflow evidence for all 11 assigned workflows; all were blocked in this terminal environment with socket access error (`WinError 10013`) and no sandbox/dev env credentials present (`BACKEND_API_URL`, `WORKFLOW_SERVICE_SECRET`, `SUPABASE_*` unset). Evidence: `worktree-lanes/AGENT-2-INTEGRATIONS/evidence/agent2-strict-rerun-20260223-185715.md`.

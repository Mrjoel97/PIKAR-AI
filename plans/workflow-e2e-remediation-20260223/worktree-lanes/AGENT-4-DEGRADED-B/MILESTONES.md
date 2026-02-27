# AGENT-4-DEGRADED-B Milestone Tracker

- Worktree path: `.tmp/codex-parallel/worktrees/wt-agent-4-degraded-b`
- Branch: `workflow-e2e/agent-4-degraded-b`
- Status values: `todo`, `in_progress`, `blocked`, `done`

| Milestone ID | Type | Priority | Status | Scope | Title | Depends On | Evidence Ref | Owner |
|---|---|---|---|---|---|---|---|---|
| M00 | setup | P0 | todo | lane | Worktree created and lane preflight complete | AGENT-0-INFRA |  |  |
| M01 | batch | P1 | todo | lane | P1 workflow fixes implemented and validated | M00 |  |  |
| M02 | batch | P2 | todo | lane | P2 workflow fixes implemented and validated | M00 |  |  |
| WF-CONTRACT_REVIEW | workflow | P1 | todo | workflow | Contract Review strict E2E pass/gate verified | M00 |  |  |
| WF-RECRUITMENT_PIPELINE | workflow | P1 | todo | workflow | Recruitment Pipeline strict E2E pass/gate verified | M00 |  |  |
| WF-BUDGET_PLANNING | workflow | P2 | todo | workflow | Budget Planning strict E2E pass/gate verified | M00 |  |  |
| WF-PIPELINE_REVIEW | workflow | P2 | todo | workflow | Pipeline Review strict E2E pass/gate verified | M00 |  |  |
| WF-CASH_FLOW_MANAGEMENT | workflow | P2 | todo | workflow | Cash Flow Management strict E2E pass/gate verified | M00 |  |  |
| WF-DATA_GOVERNANCE_AUDIT | workflow | P2 | todo | workflow | Data Governance Audit strict E2E pass/gate verified | M00 |  |  |
| WF-INCIDENT_INVESTIGATION | workflow | P2 | todo | workflow | Incident Investigation strict E2E pass/gate verified | M00 |  |  |
| WF-OFFICE_MOVE_EXPANSION | workflow | P2 | todo | workflow | Office Move/Expansion strict E2E pass/gate verified | M00 |  |  |
| WF-TAX_FILING_PREP | workflow | P2 | todo | workflow | Tax Filing Prep strict E2E pass/gate verified | M00 |  |  |
| WF-BETA_TESTING_PROGRAM | workflow | P2 | todo | workflow | Beta Testing Program strict E2E pass/gate verified | M00 |  |  |
| WF-EXPENSE_REIMBURSEMENT | workflow | P2 | todo | workflow | Expense Reimbursement strict E2E pass/gate verified | M00 |  |  |
| WF-INVOICE_PROCESSING | workflow | P2 | todo | workflow | Invoice Processing strict E2E pass/gate verified | M00 |  |  |
| WF-OFFBOARDING | workflow | P2 | todo | workflow | Offboarding strict E2E pass/gate verified | M00 |  |  |
| M90 | qa | P1 | todo | lane | Lane regression tests and documentation complete | M00 |  |  |
| M99 | handoff | P1 | todo | lane | Lane ready for merge | M90 |  |  |

## Notes

- `M01` Batch contains: Contract Review, Recruitment Pipeline
- `M02` Batch contains: Budget Planning, Pipeline Review, Cash Flow Management, Data Governance Audit, Incident Investigation, Office Move/Expansion, Tax Filing Prep, Beta Testing Program, Expense Reimbursement, Invoice Processing, Offboarding
- `WF-CONTRACT_REVIEW` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-RECRUITMENT_PIPELINE` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-BUDGET_PLANNING` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-PIPELINE_REVIEW` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-CASH_FLOW_MANAGEMENT` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-DATA_GOVERNANCE_AUDIT` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-INCIDENT_INVESTIGATION` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-OFFICE_MOVE_EXPANSION` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-TAX_FILING_PREP` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-BETA_TESTING_PROGRAM` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-EXPENSE_REIMBURSEMENT` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-INVOICE_PROCESSING` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-OFFBOARDING` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `M90` Targeted tests + changelog + evidence package assembled.
- `M99` Checklist complete, risks recorded, merge order prerequisites satisfied.

# AGENT-3-DEGRADED-A Milestone Tracker

- Worktree path: `.tmp/codex-parallel/worktrees/wt-agent-3-degraded-a`
- Branch: `workflow-e2e/agent-3-degraded-a`
- Status values: `todo`, `in_progress`, `blocked`, `done`

| Milestone ID | Type | Priority | Status | Scope | Title | Depends On | Evidence Ref | Owner |
|---|---|---|---|---|---|---|---|---|
| M00 | setup | P0 | todo | lane | Worktree created and lane preflight complete | AGENT-0-INFRA |  |  |
| M01 | batch | P1 | todo | lane | P1 workflow fixes implemented and validated | M00 |  |  |
| M02 | batch | P2 | todo | lane | P2 workflow fixes implemented and validated | M00 |  |  |
| WF-VENDOR_ONBOARDING | workflow | P1 | todo | workflow | Vendor Onboarding strict E2E pass/gate verified | M00 |  |  |
| WF-FUNDRAISING_ROUND | workflow | P1 | todo | workflow | Fundraising Round strict E2E pass/gate verified | M00 |  |  |
| WF-IT_ASSET_PROVISIONING | workflow | P2 | todo | workflow | IT Asset Provisioning strict E2E pass/gate verified | M00 |  |  |
| WF-CRISIS_MANAGEMENT_RESPON | workflow | P2 | todo | workflow | Crisis Management Response strict E2E pass/gate verified | M00 |  |  |
| WF-AD_CAMPAIGN_MANAGEMENT | workflow | P2 | todo | workflow | Ad Campaign Management strict E2E pass/gate verified | M00 |  |  |
| WF-CHURN_PREVENTION | workflow | P2 | todo | workflow | Churn Prevention strict E2E pass/gate verified | M00 |  |  |
| WF-EMPLOYEE_ONBOARDING | workflow | P2 | todo | workflow | Employee Onboarding strict E2E pass/gate verified | M00 |  |  |
| WF-MERGER_AND_ACQUISITION_MAND | workflow | P2 | todo | workflow | Merger & Acquisition (M&A) strict E2E pass/gate verified | M00 |  |  |
| WF-QUALITY_ASSURANCE_AUDIT | workflow | P2 | todo | workflow | Quality Assurance Audit strict E2E pass/gate verified | M00 |  |  |
| WF-UPSELL_CAMPAIGN | workflow | P2 | todo | workflow | Upsell Campaign strict E2E pass/gate verified | M00 |  |  |
| WF-BUG_TRIAGE | workflow | P2 | todo | workflow | Bug Triage strict E2E pass/gate verified | M00 |  |  |
| WF-INVENTORY_MANAGEMENT | workflow | P2 | todo | workflow | Inventory Management strict E2E pass/gate verified | M00 |  |  |
| WF-LEAD_QUALIFICATION | workflow | P2 | todo | workflow | Lead Qualification strict E2E pass/gate verified | M00 |  |  |
| WF-TRAVEL_POLICY_MANAGEMENT | workflow | P2 | todo | workflow | Travel Policy Management strict E2E pass/gate verified | M00 |  |  |
| M90 | qa | P1 | todo | lane | Lane regression tests and documentation complete | M00 |  |  |
| M99 | handoff | P1 | todo | lane | Lane ready for merge | M90 |  |  |

## Notes

- `M01` Batch contains: Vendor Onboarding, Fundraising Round
- `M02` Batch contains: IT Asset Provisioning, Crisis Management Response, Ad Campaign Management, Churn Prevention, Employee Onboarding, Merger & Acquisition (M&A), Quality Assurance Audit, Upsell Campaign, Bug Triage, Inventory Management, Lead Qualification, Travel Policy Management
- `WF-VENDOR_ONBOARDING` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-FUNDRAISING_ROUND` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-IT_ASSET_PROVISIONING` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-CRISIS_MANAGEMENT_RESPON` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-AD_CAMPAIGN_MANAGEMENT` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-CHURN_PREVENTION` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-EMPLOYEE_ONBOARDING` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-MERGER_AND_ACQUISITION_MAND` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-QUALITY_ASSURANCE_AUDIT` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-UPSELL_CAMPAIGN` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-BUG_TRIAGE` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-INVENTORY_MANAGEMENT` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-LEAD_QUALIFICATION` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `WF-TRAVEL_POLICY_MANAGEMENT` Re-run with simulation disabled and strict guards on; verify completion/gate with no degraded critical-step fallback.
- `M90` Targeted tests + changelog + evidence package assembled.
- `M99` Checklist complete, risks recorded, merge order prerequisites satisfied.

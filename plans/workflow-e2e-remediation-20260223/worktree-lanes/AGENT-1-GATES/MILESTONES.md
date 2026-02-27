# AGENT-1-GATES Milestone Tracker

- Worktree path: `.tmp/codex-parallel/worktrees/wt-agent-1-gates`
- Branch: `workflow-e2e/agent-1-gates`
- Status values: `todo`, `in_progress`, `blocked`, `done`

| Milestone ID | Type | Priority | Status | Scope | Title | Depends On | Evidence Ref | Owner |
|---|---|---|---|---|---|---|---|---|
| M00 | setup | P0 | todo | lane | Worktree created and lane preflight complete | AGENT-0-INFRA |  |  |
| M01 | batch | P1 | todo | lane | P1 workflow fixes implemented and validated | M00 |  |  |
| WF-INITIATIVE_FRAMEWORK | workflow | P1 | todo | workflow | Initiative Framework strict E2E pass/gate verified | M00 |  |  |
| WF-COMPETITOR_ANALYSIS_WORK | workflow | P1 | todo | workflow | Competitor Analysis Workflow strict E2E pass/gate verified | M00 |  |  |
| WF-LEAD_GENERATION_WORKFLOW | workflow | P1 | todo | workflow | Lead Generation Workflow strict E2E pass/gate verified | M00 |  |  |
| WF-PRODUCT_LAUNCH_WORKFLOW | workflow | P1 | todo | workflow | Product Launch Workflow strict E2E pass/gate verified | M00 |  |  |
| WF-SOCIAL_MEDIA_CAMPAIGN_WO | workflow | P1 | todo | workflow | Social Media Campaign Workflow strict E2E pass/gate verified | M00 |  |  |
| WF-A_B_TESTING_WORKFLOW | workflow | P1 | todo | workflow | A/B Testing Workflow strict E2E pass/gate verified | M00 |  |  |
| WF-CONTENT_CREATION_WORKFLO | workflow | P1 | todo | workflow | Content Creation Workflow (Extended) strict E2E pass/gate verified | M00 |  |  |
| WF-EMAIL_SEQUENCE_WORKFLOW | workflow | P1 | todo | workflow | Email Sequence Workflow strict E2E pass/gate verified | M00 |  |  |
| M90 | qa | P1 | todo | lane | Lane regression tests and documentation complete | M00 |  |  |
| M99 | handoff | P1 | todo | lane | Lane ready for merge | M90 |  |  |

## Notes

- `M01` Batch contains: Initiative Framework, Competitor Analysis Workflow, Lead Generation Workflow, Product Launch Workflow, Social Media Campaign Workflow, A/B Testing Workflow, Content Creation Workflow (Extended), Email Sequence Workflow
- `WF-INITIATIVE_FRAMEWORK` Re-run in strict E2E env and verify status path `pending/running -> waiting_approval -> running/completed` with SSE + approval endpoint + UI path.
- `WF-COMPETITOR_ANALYSIS_WORK` Re-run in strict E2E env and verify status path `pending/running -> waiting_approval -> running/completed` with SSE + approval endpoint + UI path.
- `WF-LEAD_GENERATION_WORKFLOW` Re-run in strict E2E env and verify status path `pending/running -> waiting_approval -> running/completed` with SSE + approval endpoint + UI path.
- `WF-PRODUCT_LAUNCH_WORKFLOW` Re-run in strict E2E env and verify status path `pending/running -> waiting_approval -> running/completed` with SSE + approval endpoint + UI path.
- `WF-SOCIAL_MEDIA_CAMPAIGN_WO` Re-run in strict E2E env and verify status path `pending/running -> waiting_approval -> running/completed` with SSE + approval endpoint + UI path.
- `WF-A_B_TESTING_WORKFLOW` Re-run in strict E2E env and verify status path `pending/running -> waiting_approval -> running/completed` with SSE + approval endpoint + UI path.
- `WF-CONTENT_CREATION_WORKFLO` Re-run in strict E2E env and verify status path `pending/running -> waiting_approval -> running/completed` with SSE + approval endpoint + UI path.
- `WF-EMAIL_SEQUENCE_WORKFLOW` Re-run in strict E2E env and verify status path `pending/running -> waiting_approval -> running/completed` with SSE + approval endpoint + UI path.
- `M90` Targeted tests + changelog + evidence package assembled.
- `M99` Checklist complete, risks recorded, merge order prerequisites satisfied.

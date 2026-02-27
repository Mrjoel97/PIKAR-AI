# 68-Workflow End-to-End Remediation Plan (Parallel Agent Execution)

Date: **2026-02-23**

## Objective
Make all **68 workflow templates** executable end-to-end for users manually and by agents autonomously (after acquiring required info), with strict E2E validation and evidence.

## Inputs Used
- Audit baseline: `plans/audits/workflow-journey-e2e-audit-20260222/summary.md`
- Per-workflow matrix: `plans/audits/workflow-journey-e2e-audit-20260222/workflow_matrix.csv`
- Per-journey matrix: `plans/audits/workflow-journey-e2e-audit-20260222/journey_matrix.csv`

## Current Baseline Constraints (from audit)
- Global environment blockers on workflow callback path: missing `BACKEND_API_URL` and `WORKFLOW_SERVICE_SECRET`.
- Strict E2E validation flags are currently disabled (readiness gate / strict tool guards / simulation disabled).
- Batch verification can be distorted by API rate limits (`429`) and token expiry (`401`) unless pacing/token refresh are managed.
- Journey UI/API mismatch exists for outcomes/timeline prompting vs backend universal enforcement.

## Workflow Inventory Breakdown
- `degraded-simulation-prone`: 27
- `fully autonomous`: 22
- `integration-dependent`: 11
- `human-gated`: 8

## Parallel Agent Lanes (simulated packets)
- `AGENT-0-INFRA` (global blockers and env hardening)
- `AGENT-1-GATES` (8 human-gated workflows)
- `AGENT-2-INTEGRATIONS` (11 integration-dependent workflows)
- `AGENT-3-DEGRADED-A` + `AGENT-4-DEGRADED-B` (27 degraded-simulation-prone workflows split across 2 lanes)
- `AGENT-5-AUTONOMOUS-A` + `AGENT-6-AUTONOMOUS-B` (22 fully autonomous workflows split across 2 lanes)
- `AGENT-7-QA-ORCH` (evidence, browser subset, reruns, and regression gating)

## Execution Sequence (Recommended)
1. Complete `AGENT-0-INFRA` global prerequisites.
2. Run `AGENT-1-GATES` and `AGENT-2-INTEGRATIONS` first (highest workflow risk and contract complexity).
3. Run `AGENT-3/4-DEGRADED-*` next to eliminate strict-mode simulation failures.
4. Run `AGENT-5/6-AUTONOMOUS-*` to finish deterministic completions and output quality verification.
5. `AGENT-7-QA-ORCH` runs browser subset + exhaustive rerun with per-item polling enabled.

## High-Impact Workflows by Journey Coverage (top 15)
- `Strategic Planning Cycle`: referenced by 31 journeys
- `Content Creation Workflow`: referenced by 13 journeys
- `Policy Update`: referenced by 9 journeys
- `Vendor Onboarding`: referenced by 8 journeys
- `Contract Review`: referenced by 7 journeys
- `Fundraising Round`: referenced by 6 journeys
- `GDPR Compliance Audit`: referenced by 4 journeys
- `Initiative Framework`: referenced by 4 journeys
- `Partnership Development`: referenced by 4 journeys
- `Recruitment Pipeline`: referenced by 4 journeys
- `Roadmap Planning`: referenced by 4 journeys
- `Account Renewal`: referenced by 3 journeys
- `Competitor Analysis Workflow`: referenced by 3 journeys
- `Customer Onboarding`: referenced by 3 journeys
- `Email Nurture Sequence`: referenced by 3 journeys

## Deliverables in This Folder
- `workflow_tasklist_68.csv` (one row per workflow with tasks + lane assignment)
- `workflow_tasklist_68.json` (same data in JSON)
- `agent_lane_packets.md` (parallel execution packets for multiple agents)

## Definition of Done (Program-Level)
- All 68 workflows can start in strict E2E env without 429/401 audit artifacts.
- Each workflow leaves `pending` and reaches terminal completion or valid human/integration gate with observable history/SSE evidence.
- Human-gated workflows have verified `/approve` + UI approval path.
- Integration-dependent workflows are validated with sandbox credentials and strict-mode no-simulation behavior.
- Degraded-simulation-prone workflows pass with simulation disabled and strict critical tool guard enabled.
- Exhaustive audit rerun produces per-workflow evidence with no env-blocker classifications except intentional gates.

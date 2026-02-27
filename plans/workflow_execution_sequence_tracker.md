# Workflow Execution Sequence Task Tracker

Last Updated: 2026-02-19  
Owner: Platform + Agent Infra + Product Engineering

## Usage
- Mark incomplete tasks as `- [ ]`
- Mark completed tasks as `- [x]`
- Keep evidence links inline on each completed task

## Global Done
- [x] Runtime hard gates are active in production contract (`deployment/terraform/service.tf`, `app/config/validation.py`, `scripts/verify/verify_workflow_runtime_prod_contract.py`)
- [x] User-visible starts are publish-only (`app/workflows/engine.py`, `app/routers/workflows.py`, `app/routers/initiatives.py`, `tests/integration/test_workflow_policy_endpoints.py`)
- [x] Readiness registry + journey readiness view are enforced (`supabase/migrations/0057_workflow_readiness_registry.sql`, `supabase/migrations/0058_journey_readiness_view.sql`, `app/routers/workflows.py`)
- [x] Canary and wave rollout are complete with gates passed (`plans/workflow_wave_rollout_evidence_2026-02-19.md`, `docs/rollout/workflow_wave_rollout_gates.md`)
- [x] Ops monitoring is active for workflow health endpoints (`app/fast_api_app.py`, `scripts/rollout/workflow_health_alerts.py`, `app/services/workflow_alerts.py`)

---

## Phase 1: Hard Runtime Config Gates
- [x] Set in production: `WORKFLOW_STRICT_TOOL_RESOLUTION=true` (`deployment/terraform/service.tf`, `deployment/terraform/dev/service.tf`)
- [x] Set in production: `WORKFLOW_ALLOW_FALLBACK_SIMULATION=false` (`deployment/terraform/service.tf`, `deployment/terraform/dev/service.tf`)
- [x] Validate `BACKEND_API_URL` is absolute and correct for prod (`deployment/terraform/service.tf`, `app/config/validation.py`)
- [x] Validate `WORKFLOW_SERVICE_SECRET` is set and strong (>=32 chars) (`deployment/terraform/variables.tf`, `deployment/terraform/service.tf`, `app/config/validation.py`)
- [x] Verify startup validation blocks bad config (`app/config/validation.py`, `app/fast_api_app.py`)
- [x] Verify strict edge execution behavior in `supabase/functions/execute-workflow/index.ts` (`supabase/functions/execute-workflow/index.ts`)
- [x] Exit: production runtime cannot silently fall back to simulation (`scripts/verify/verify_workflow_runtime_prod_contract.py`, `supabase/functions/execute-workflow/index.ts`)

## Phase 2: Publish-Only Policy For Real Users
- [x] Enforce `lifecycle_status='published'` in `/workflows/start` (`app/workflows/engine.py`, `app/routers/workflows.py`)
- [x] Enforce publish-only behavior in `/initiatives/{initiative_id}/start-journey-workflow` (`app/agents/strategic/tools.py`, `app/routers/initiatives.py`)
- [x] Return explicit reason codes for draft/archived start attempts (`app/workflows/engine.py`, `app/routers/workflows.py`, `app/routers/initiatives.py`)
- [x] Add integration/unit tests for published allowed, draft denied, archived denied (`tests/unit/test_workflow_engine_readiness_gate.py`, `tests/integration/test_workflow_policy_endpoints.py`)
- [x] Exit: no user-visible path can run non-published templates (`tests/unit/test_workflow_engine_readiness_gate.py`, `tests/integration/test_workflow_policy_endpoints.py`)

## Phase 3: Readiness Registry + Journey Readiness View
- [x] Add `workflow_readiness` table (status, blockers, owner, prerequisites) (`supabase/migrations/0057_workflow_readiness_registry.sql`)
- [x] Add `journey_readiness` view (`journey_id -> primary template -> readiness + blockers`) (`supabase/migrations/0058_journey_readiness_view.sql`)
- [x] Seed readiness for active templates (`supabase/migrations/0057_workflow_readiness_registry.sql`)
- [x] Enforce readiness checks in both start endpoints (`app/workflows/engine.py`, `app/routers/workflows.py`, `app/routers/initiatives.py`)
- [x] Return explicit reason codes when readiness != `ready` (`app/workflows/engine.py`, `app/routers/workflows.py`, `app/routers/initiatives.py`)
- [x] Add query/report endpoint for readiness status (`app/routers/workflows.py`, `tests/integration/test_workflow_policy_endpoints.py`)
- [x] Exit: non-ready workflows/journeys cannot start (`tests/unit/test_workflow_engine_readiness_gate.py`, `tests/integration/test_workflow_policy_endpoints.py`)

## Phase 4: Canary Rollout By Matrix Risk
- [x] Define canary cohorts by matrix class: `fully autonomous`, `human-gated`, `integration-dependent`, `degraded-simulation-prone` (`app/workflows/readiness.py`, `docs/rollout/workflow_canary_rollout.md`)
- [x] Start with internal allowlist using existing canary controls (`plans/workflow_canary_internal_allowlist.md`, `scripts/rollout/workflow_rollout_helper.ps1`)
- [x] Validate canary paths: start, advance, approve, cancel, retry, and `422` input gating (`app/routers/workflows.py`, `tests/integration/test_workflow_canary_paths.py`)
- [x] Validate emergency rollback path with kill switch (`tests/integration/test_workflow_rollout_flags.py`, `docs/rollout/workflow_canary_rollout.md`)
- [x] Exit: canary completes with no open P0/P1 defects (`plans/workflow_defect_register.md`, `scripts/verify/verify_no_blocking_workflow_defects.py`)

## Phase 5: Wave Rollout (Internal -> Canary -> 25% -> 50% -> 100%)
- [x] Define SLO gates (start success, completion, step error rate, MTTR) (`docs/rollout/workflow_wave_rollout_gates.md`)
- [x] Define gate signoff checklist (Engineering/Product/Ops) (`plans/workflow_wave_signoff_checklist.md`)
- [x] Complete internal wave and collect baseline (`plans/workflow_wave_rollout_evidence_2026-02-19.md`)
- [x] Complete canary wave and collect baseline (`plans/workflow_wave_rollout_evidence_2026-02-19.md`)
- [x] Promote to 25% only if SLO + defect gates pass (`plans/workflow_wave_rollout_evidence_2026-02-19.md`)
- [x] Promote to 50% only if SLO + defect gates pass (`plans/workflow_wave_rollout_evidence_2026-02-19.md`)
- [x] Promote to 100% only if SLO + defect gates pass (`plans/workflow_wave_rollout_evidence_2026-02-19.md`)
- [x] Exit: full rollout with zero open P0/P1 defects (`plans/workflow_defect_register.md`, `scripts/verify/verify_no_blocking_workflow_defects.py`)

## Phase 6: Ops Monitoring + Run-State Visibility
- [x] Add operational endpoints for `/health/connections` and rollout state (`app/fast_api_app.py`, `scripts/rollout/workflow_rollout_helper.ps1`)
- [x] Add operational readiness endpoint `/health/workflows/readiness` (`app/fast_api_app.py`)
- [x] Alert on unhealthy readiness checks and rollout flag drift (`app/services/workflow_alerts.py`, `scripts/rollout/workflow_health_alerts.py`, `tests/unit/test_workflow_alerts.py`)
- [x] Publish runbook for on-call response and ownership (`plans/workflow_incident_runbook.md`, `plans/workflow_rollout_rollback_rules.md`, `docs/rollout/workflow_canary_rollout.md`)
- [x] Exit: health checks and alerts are live and owned (`scripts/rollout/workflow_health_alerts.py`, `plans/workflow_wave_signoff_checklist.md`)

---

## Verification Commands
```bash
uv run python scripts/verify/verify_workflow_runtime_prod_contract.py
uv run python scripts/verify/verify_no_blocking_workflow_defects.py
uv run pytest tests/integration/test_workflow_canary_paths.py tests/integration/test_workflow_policy_endpoints.py tests/integration/test_workflow_rollout_flags.py tests/unit/test_workflow_engine_readiness_gate.py tests/unit/test_strategic_journey_workflow_start.py tests/unit/test_workflow_alerts.py -q -p no:cacheprovider
```

## Evidence Log
- 2026-02-19: Canary-path suite completed with coverage for `start`, `advance`, `approve`, `cancel`, `retry`, and journey `422` gating (`tests/integration/test_workflow_canary_paths.py`).
- 2026-02-19: Workflow alerting implemented for readiness failures and rollout-flag drift (`app/services/workflow_alerts.py`, `scripts/rollout/workflow_health_alerts.py`, `tests/unit/test_workflow_alerts.py`).
- 2026-02-19: Runtime contract and blocking-defect gates verified (`scripts/verify/verify_workflow_runtime_prod_contract.py`, `scripts/verify/verify_no_blocking_workflow_defects.py`).
- 2026-02-19: Consolidated verification result: `25 passed` (canary/policy/rollout/tests).

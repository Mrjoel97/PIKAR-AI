# Google Agent Runtime Stabilization Checklist

This document is the canonical finish-up checklist for the remaining
post-cutover Google-hosted backend work.

Use this after the Cloudflare migration is considered functionally complete.
The remaining goal is not route migration anymore. It is to make the narrowed
Google surface correct, healthy, and operational:

- `Cloudflare`: public API and edge traffic
- `Google Cloud Run`: agent runtime, workflow execution, Vertex-backed model work,
  and internal scheduled/runtime workloads

## Current Live State

As of April 19, 2026:

- Cloud Run auth/runtime secret contamination has been repaired.
- `/health/connections` is healthy again.
- `/health/workflows/readiness` is reachable but reports `not_ready`.
- `/health/video` is reachable but reports `degraded`.
- The remaining highest-value work is:
  - workflow readiness correctness
  - video runtime/config correctness

## Done Definition

This stabilization work is complete only when all of the following are true:

- `/health/workflows/readiness` no longer fails on:
  - `integration_workflows_have_required_integrations_metadata`
  - `user_visible_templates_have_strict_step_contracts`
- published user-visible workflow templates satisfy the strict execution
  contract expected by runtime validators
- the remaining agent/runtime tools referenced by published workflows expose
  typed input schemas where required
- `/health/video` reflects the intentional production architecture instead of
  reporting a false or misleading degradation
- Cloud Run runtime env and health checks agree on whether video generation is:
  - `Vertex-only`
  - `Vertex + Remotion`
  - or intentionally `degraded / disabled`
- deployment docs match the live Google runtime shape exactly

## Priority 1: Workflow Readiness

### 1. Capture and freeze the current failure baseline

- [ ] Record the current readiness payload and validator output as the baseline
- [ ] Preserve the failing check names, affected templates, and repeated error
      categories in this document or a linked evidence note
- [ ] Confirm whether the source of truth for remediation is:
  - workflow definition YAMLs under `app/workflows/definitions`
  - `workflow_readiness` rows in Supabase
  - generated defaults in `app/workflows/contract_defaults.py`
  - or a mix of the three

Files and surfaces:
- `app/workflows/readiness.py`
- `app/workflows/execution_contracts.py`
- `app/workflows/contract_defaults.py`
- `app/workflows/definitions/*.yaml`
- `docs/plans/workflow_schema_contract_v1.md`

Acceptance:
- We have one stable before-state snapshot to compare against after each fix wave.

### 2. Fix missing `required_integrations` metadata for integration-dependent workflows

- [ ] Repair the `workflow_readiness.required_integrations` metadata for the
      currently affected integration-dependent templates
- [ ] Confirm the metadata is non-empty and semantically correct, not just a
      placeholder list
- [ ] Re-run readiness and confirm the
      `integration_workflows_have_required_integrations_metadata` check clears

Current affected templates from live readiness:
- `Expense Reimbursement`
- `Invoice Processing`
- `Machine Learning Pipeline`
- `Offboarding`
- `Sales Training`
- `Travel Policy Management`

Likely touch points:
- `app/workflows/readiness.py`
- `app/workflows/definitions/*.yaml`
- any sync/backfill script or DB write path that populates `workflow_readiness`

Acceptance:
- No published integration-dependent workflow remains with
  `required_integrations_empty`.

### 3. Reconcile strict step-contract gaps for published templates

- [ ] Backfill or author the repeated required step fields across published
      user-visible templates:
  - `input_bindings`
  - `risk_level`
  - `required_integrations`
  - `verification_checks`
  - `expected_outputs`
  - `allow_parallel`
- [ ] Prefer a durable authoring/backfill path over one-off manual patching
      where possible
- [ ] Verify that contract defaults do not silently hide malformed templates in
      a way that disagrees with published runtime behavior

Primary files:
- `app/workflows/execution_contracts.py`
- `app/workflows/contract_defaults.py`
- `app/workflows/generator.py`
- `app/workflows/definitions/*.yaml`

Acceptance:
- `user_visible_templates_have_strict_step_contracts` clears in the live
  readiness report.

### 4. Add or reconcile typed input schemas for workflow tools

- [ ] Identify every tool named in live readiness gaps that still lacks a typed
      input schema
- [ ] Add or register schemas where the tool is real and should remain usable
- [ ] Remove or replace tool references where the tool is not actually valid for
      published execution

Known examples observed in live readiness:
- `send_email`
- `query_analytics`
- `test_scenario`
- `update_ticket`
- `approve_request`
- `book_travel`
- `record_video`
- `listen_call`
- `get_media_deliverable_templates`
- `execute_content_pipeline`

Likely files:
- `app/agents/tools/registry.py`
- `app/agents/tools/*.py`
- `app/workflows/execution_contracts.py`
- `app/workflows/definitions/*.yaml`

Acceptance:
- Published workflows no longer fail readiness because referenced tools are
  missing typed input schemas.

### 5. Tighten tests and verification around workflow publication/readiness

- [ ] Add or update tests that fail when published templates regress on strict
      contract requirements
- [ ] Add or update tests for integration metadata expectations
- [ ] Make the relevant validator or readiness check part of the normal
      verification path before deploys

Relevant tests and scripts:
- `tests/unit/test_workflow_readiness_report.py`
- `scripts/verify/validate_workflow_templates.py`
- any workflow contract/unit coverage already tied to the builder/runtime

Acceptance:
- Local verification can catch the same class of failures before production.

### 6. Re-run live readiness and document the clean state

- [ ] Re-check `/health/workflows/readiness`
- [ ] Update workflow planning or deployment docs if the production contract
      changed in a meaningful way
- [ ] Record the cleared checks and any intentionally accepted remaining gaps

Acceptance:
- Live readiness is either clean or any remaining non-clean state is explicitly
  documented and intentionally accepted.

## Priority 2: Video Runtime and Health Alignment

### 7. Align video readiness with the intended production architecture

- [ ] Decide what `healthy video` means in production for the narrowed Google
      runtime:
  - `Vertex-only`
  - `Vertex + Remotion`
  - or `video generation intentionally limited`
- [ ] Update the readiness logic so it reflects Vertex-first production instead
      of using `GOOGLE_API_KEY` as the primary signal when service-account /
      Vertex auth is the real path
- [ ] Make sure the health response distinguishes between:
  - Veo/API credential availability
  - Remotion server-render availability
  - intentional disablement

Primary files:
- `app/services/video_readiness.py`
- `app/services/vertex_video_service.py`
- `app/fast_api_app.py`
- `app/config/validation.py`
- `docs/deployment/google-agent-service.md`

Acceptance:
- `/health/video` tells the truth about the production runtime shape instead of
  flagging a misleading degradation.

### 8. Reconcile `REMOTION_RENDER_ENABLED` with actual runtime intent

- [ ] Decide whether server-side Remotion should be enabled on production Cloud Run
- [ ] If `yes`, enable the runtime env and verify the render directory and
      dependencies are actually usable in Cloud Run
- [ ] If `no`, document that long/programmatic video generation is intentionally
      disabled or handled differently, and make the health/reporting path say so

Primary files and config:
- `deployment/terraform/service.tf`
- `deployment/terraform/dev/service.tf`
- `app/services/remotion_render_service.py`
- `app/services/video_readiness.py`
- `docs/plans/UNIFIED_MEDIA_CREATION_PLAN.md`

Acceptance:
- The runtime env, health check, and media plan no longer disagree about whether
  Remotion is live in production.

### 9. Verify the real user-facing video path, not just the health endpoint

- [ ] Exercise the current video creation path through the backend tools or a
      representative endpoint
- [ ] Confirm whether short-video generation, long-video routing, and fallback
      behavior match the documented plan
- [ ] Confirm that generated media still lands in the expected storage/vault
      path and can be surfaced back to the app

Relevant code:
- `app/agents/tools/media.py`
- `app/mcp/tools/canva_media.py`
- `app/services/vertex_video_service.py`
- `app/services/remotion_render_service.py`

Acceptance:
- A real video generation path works as documented for the production mode we
  claim to support.

### 10. Reconcile docs and deployment config after the fix

- [ ] Update deployment docs to reflect the actual production video mode
- [ ] Update Terraform/runtime docs if production is intentionally using env
      settings that differ from the checked-in defaults
- [ ] Re-run `/health/video` and capture the final expected output state

Acceptance:
- The docs no longer imply a different video runtime from the one that is
  actually deployed.

## Recommended Execution Order

Run this work in order:

1. Baseline workflow readiness failures
2. Fix `required_integrations` metadata gaps
3. Fix repeated strict step-contract gaps
4. Fix remaining typed-schema workflow tool gaps
5. Re-run workflow readiness until clean
6. Align video readiness with Vertex-first production
7. Decide and reconcile Remotion runtime intent
8. Verify a real video generation flow end to end
9. Update docs/config to match the final production truth

## Verification Commands

Use these after each significant wave:

```bash
uv run pytest tests/unit/test_workflow_readiness_report.py
```

```bash
curl https://pikar-ai-917671810739.us-central1.run.app/health/workflows/readiness
```

```bash
curl https://pikar-ai-917671810739.us-central1.run.app/health/video
```

## Canonical Tracking Rules

- Keep this file as the single finish-up checklist for the remaining
  Google-hosted runtime stabilization work.
- Keep `docs/deployment/cloudflare-finish-checklist.md` focused on migration
  completion, not post-cutover runtime correctness.
- Keep `docs/deployment/google-agent-service.md` as the reference for the
  intended Google production shape.

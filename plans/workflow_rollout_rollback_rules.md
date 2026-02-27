# Workflow Rollout and Rollback Rules

Purpose: consistent rollout safety controls for workflow activation.

## Rollout Rules
- Use canary rollout first (`WORKFLOW_CANARY_ENABLED=true`) with explicit `WORKFLOW_CANARY_USER_IDS`.
- Expand cohorts in staged percentages only after error-rate review.
- Do not widen rollout while P0/P1 defects remain open.

## Rollback Rules

### Immediate Stop (Hard Rollback)
Use `WORKFLOW_KILL_SWITCH=true` when:
- SEV-1 incident is active
- unknown critical tool behavior is detected
- authentication/security control failure is detected

### Controlled Rollback (Soft Rollback)
Use canary restriction when:
- issue is scoped to subset of users/workflows
- mitigation/fix is in progress

Actions:
1. Set `WORKFLOW_CANARY_ENABLED=true`
2. Restrict `WORKFLOW_CANARY_USER_IDS` to internal testers
3. Validate fix in canary
4. Re-expand gradually

## Runtime Safety Baseline
- `WORKFLOW_STRICT_TOOL_RESOLUTION=true`
- `WORKFLOW_STRICT_CRITICAL_TOOL_GUARD=true`
- `WORKFLOW_ALLOW_FALLBACK_SIMULATION=false`
- `BACKEND_API_URL` configured
- `WORKFLOW_SERVICE_SECRET` configured

## Verification Steps After Rollback
1. Start workflow smoke check passes
2. Step execution auth check passes
3. Error rate returns below threshold
4. No approval-queue stalls


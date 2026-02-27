# Workflow Canary Internal Allowlist

Last Updated: 2026-02-19
Owner: Platform Engineering

## Internal Canary Users
- `00000000-0000-0000-0000-000000000001`
- `00000000-0000-0000-0000-000000000002`
- `00000000-0000-0000-0000-000000000003`

## Apply
```powershell
pwsh scripts/rollout/workflow_rollout_helper.ps1 -Action canary-on -CanaryUsers "00000000-0000-0000-0000-000000000001,00000000-0000-0000-0000-000000000002,00000000-0000-0000-0000-000000000003"
pwsh scripts/rollout/workflow_rollout_helper.ps1 -Action status
```

## Verification
- `tests/integration/test_workflow_rollout_flags.py`
- `/health/connections` -> `workflow_rollout.canary_enabled=true`

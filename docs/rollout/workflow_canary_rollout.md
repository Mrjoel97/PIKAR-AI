# Workflow Canary Rollout Playbook

## Feature Flags

- `WORKFLOW_KILL_SWITCH`
  - `true`: blocks `/workflows/start` with `503`.
  - `false`: normal behavior.

- `WORKFLOW_CANARY_ENABLED`
  - `true`: only users in `WORKFLOW_CANARY_USER_IDS` can start workflows.
  - `false`: all authenticated users can start workflows.

- `WORKFLOW_CANARY_USER_IDS`
  - Comma-separated allowlist of user UUIDs.

## Recommended Rollout Sequence

1. Deploy with:
   - `WORKFLOW_KILL_SWITCH=false`
   - `WORKFLOW_CANARY_ENABLED=true`
   - `WORKFLOW_CANARY_USER_IDS=<internal-test-users>`
2. Validate:
   - start/advance/approve paths
   - journey input gating (`422`)
   - no fallback simulation in production (`WORKFLOW_ALLOW_FALLBACK_SIMULATION=false`)
3. Expand canary allowlist in batches.
4. Disable canary mode (`WORKFLOW_CANARY_ENABLED=false`) for full rollout.

## Operational Helper

Use the shell helper to toggle rollout flags and verify runtime status:

```powershell
pwsh scripts/rollout/workflow_rollout_helper.ps1 -Action status
pwsh scripts/rollout/workflow_rollout_helper.ps1 -Action canary-on -CanaryUsers "uuid-1,uuid-2"
pwsh scripts/rollout/workflow_rollout_helper.ps1 -Action kill-on
```

The helper reads `/health/connections` and prints `workflow_rollout`:
- `kill_switch_enabled`
- `canary_enabled`
- `canary_user_count`

## Alerting Check

Run the workflow health monitor to alert on readiness failures and rollout flag drift:

```powershell
uv run python scripts/rollout/workflow_health_alerts.py --base-url http://localhost:8000
```

Optional:
- Set `EXPECTED_WORKFLOW_CANARY_ENABLED` and `EXPECTED_WORKFLOW_KILL_SWITCH` for drift checks.
- Set `WORKFLOW_ALERT_WEBHOOK_URL` to send alert payloads to Slack/Teams/webhook receiver.

## Emergency Rollback

1. Set `WORKFLOW_KILL_SWITCH=true`.
2. Confirm `/workflows/start` returns `503`.
3. Investigate, patch, redeploy.
4. Re-enable traffic with `WORKFLOW_KILL_SWITCH=false`.

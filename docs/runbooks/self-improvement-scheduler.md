# Self-Improvement Scheduler Runbook

## Overview

The self-improvement cycle is a daily automated process that evaluates skill effectiveness from interaction data, identifies underperforming or unused skills, and triggers autonomous improvements. It runs via Cloud Scheduler calling `POST /scheduled/self-improvement-cycle`.

**Risk-tiered execution:** Low-risk actions (skill_demoted, pattern_extract) auto-execute when `auto_execute_enabled` is true. High-risk actions (skill_refined, skill_created) are queued as `pending_approval` for admin review regardless of the setting.

## Cloud Scheduler Configuration

Create the scheduler job:

```bash
gcloud scheduler jobs create http self-improvement-daily \
  --schedule="0 3 * * *" \
  --uri="https://<SERVICE_URL>/scheduled/self-improvement-cycle" \
  --http-method=POST \
  --headers="X-Scheduler-Secret=<SCHEDULER_SECRET>,Content-Type=application/json" \
  --time-zone="UTC" \
  --description="Daily self-improvement evaluation cycle" \
  --attempt-deadline=300s
```

The job fires at **03:00 UTC daily**, outside peak business hours.

## Environment Variable

`SCHEDULER_SECRET` must be set in Cloud Run. This is the same secret used by all `/scheduled/*` endpoints (daily-report, weekly-digest, etc.) and was introduced in Phase 57.

To verify it is set:

```bash
gcloud run services describe pikar-ai --region=us-central1 \
  --format="value(spec.template.spec.containers[0].env)" | grep SCHEDULER_SECRET
```

## Manual Trigger

```bash
curl -X POST https://<SERVICE_URL>/scheduled/self-improvement-cycle \
  -H "X-Scheduler-Secret: $SCHEDULER_SECRET" \
  -H "Content-Type: application/json"
```

## Admin Settings

The engine reads from the `self_improvement_settings` table:

| Key | Default | Description |
|-----|---------|-------------|
| `auto_execute_enabled` | `false` | Whether low-risk actions auto-execute |
| `auto_execute_risk_tiers` | `["skill_demoted","pattern_extract"]` | Action types eligible for auto-execution |

To enable auto-execution, update via the settings service or directly:

```sql
UPDATE self_improvement_settings
SET value = 'true'::jsonb, updated_at = now(), updated_by = 'admin'
WHERE key = 'auto_execute_enabled';
```

## Monitoring

Check Cloud Logging for structured log entries:

- `self_improvement.cycle_complete` -- emitted at the end of every cycle with timing and action counts
- Filter: `jsonPayload.message =~ "self_improvement.cycle_complete"`

Key metrics in the log:
- `cycle_duration_ms` -- total wall-clock time
- `gemini_call_latency_ms` -- time spent in LLM calls
- `actions_executed_total` -- number of auto-executed actions
- `actions_pending_approval` -- number of actions queued for review

## Safety

- **Authentication gate:** Requests without a valid `X-Scheduler-Secret` header receive HTTP 401.
- **Risk tiers:** Only explicitly listed action types can auto-execute. New action types default to requiring approval.
- **Circuit breaker:** Plan 75-02 introduces an automatic circuit breaker that disables `auto_execute_enabled` on detected regression (score decline after an auto-executed action).

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| HTTP 503 from endpoint | `SCHEDULER_SECRET` not set | Set env var in Cloud Run |
| HTTP 401 from endpoint | Secret mismatch | Verify secret matches between Scheduler and Cloud Run |
| 0 actions executed | `auto_execute_enabled` is false | Update setting in DB if desired |
| Cycle completes but no scores | No interaction_logs in the evaluation window | Ensure interaction logging is active |

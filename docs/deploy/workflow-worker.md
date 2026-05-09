# WorkflowWorker — Cloud Run Job Operator Runbook

The `WorkflowWorker` (`app/workflows/worker.py`) is deployed as a **Cloud Run Job**, triggered every 5 minutes by **Cloud Scheduler**. Each invocation polls Supabase for pending workflow steps, `ai_jobs`, scheduled reports, webhook deliveries, and email sequences.

## Prerequisites

- `gcloud` CLI installed and authenticated: `gcloud auth login`
- Project access to `pikar-ai-project` (default) and the `agents@pikar-ai-project.iam.gserviceaccount.com` service account
- Docker Desktop running (only needed for the local-fallback path inside `cloud_run_job.ps1`)
- One-time auth helper: `gcloud auth configure-docker us-central1-docker.pkg.dev`
- The FastAPI service `pikar-ai` must already be deployed in the same project — the script inherits `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `REDIS_HOST`, `REDIS_PORT`, and `GOOGLE_CLOUD_PROJECT` from it.

## First-time deploy

From the repo root, on Windows PowerShell:

```powershell
.\scripts\deploy\cloud_run_job.ps1
```

This will:

1. Verify gcloud auth and project access
2. Build `Dockerfile.worker` and push it to Artifact Registry (`cloud-run-source-deploy/workflow-worker`)
3. Mirror env vars from the live `pikar-ai` service and add `ENABLE_CONVERSATION_SUMMARIZER=true`, `SESSION_MAX_EVENTS=200`
4. Create or update the Cloud Run Job `workflow-worker` with: 1Gi memory, 1 CPU, max-retries 2, parallelism 1, task-timeout 3600s
5. Create or update Cloud Scheduler job `worker-trigger` to run `*/5 * * * *` against the job's `:run` API

Override defaults if needed:

```powershell
.\scripts\deploy\cloud_run_job.ps1 -Project my-proj -Region europe-west1 -ImageTag v1.2.3
```

## Subsequent deploys

Pushes to `main` that touch any of:

- `app/workflows/**`
- `Dockerfile.worker`
- `pyproject.toml`

trigger `cloudbuild.yaml`, which rebuilds the image with BuildKit caching, pushes both the `$SHORT_SHA` and `:latest` tags, then runs `gcloud run jobs update workflow-worker --image <new>`.

To register the trigger one time:

```bash
gcloud builds triggers create github \
  --name=workflow-worker-main \
  --repo-name=pikar-ai \
  --repo-owner=<github-org> \
  --branch-pattern=^main$ \
  --build-config=cloudbuild.yaml \
  --included-files="app/workflows/**","Dockerfile.worker","pyproject.toml" \
  --substitutions=_REGION=us-central1,_PROJECT_ID=pikar-ai-project,_REPOSITORY=cloud-run-source-deploy
```

## Manual trigger

```bash
gcloud run jobs execute workflow-worker --region us-central1 --project pikar-ai-project
```

This kicks off a one-shot execution outside the 5-minute schedule. Useful when you've just promoted a fix and want to drain the backlog immediately.

## Logs

```bash
# Tail the latest execution
gcloud run jobs logs read workflow-worker --region us-central1 --project pikar-ai-project

# Cloud Console UI:
# https://console.cloud.google.com/run/jobs/details/us-central1/workflow-worker/executions
```

Logs are also routed to Cloud Logging under resource type `cloud_run_job` with `resource.labels.job_name="workflow-worker"`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `gcloud is not authenticated` | No active account | `gcloud auth login` then re-run |
| `Cannot describe project ...` | Wrong project or no IAM | Check `gcloud config get-value project` and access on Cloud Console |
| Build fails on `--file=Dockerfile.worker` | Older gcloud SDK | Script auto-falls-back to local `docker build`+`docker push` — make sure Docker Desktop is up |
| Job runs but every task exits with `Missing SUPABASE_URL` | Reference service didn't resolve env | Re-run script after confirming `pikar-ai` exists in the same region, OR pass `--set-env-vars` manually via `gcloud run jobs update` |
| `Permission denied` when scheduler invokes job | Service account missing `roles/run.invoker` on the job | `gcloud run jobs add-iam-policy-binding workflow-worker --region=us-central1 --member=serviceAccount:agents@pikar-ai-project.iam.gserviceaccount.com --role=roles/run.invoker` |
| Scheduler creates 401s | OAuth scope wrong | Confirm `--oauth-token-scope=https://www.googleapis.com/auth/cloud-platform` is set on the scheduler job |
| `claim_next_ai_job` errors in logs | Migration not applied | Verify migrations in `supabase/migrations` are up to date on the linked Supabase project |

## Related code

- Worker entrypoint: `app/workflows/worker.py` — `WorkflowWorker.start()`
- Local dev runner: `scripts/dev/run_worker.py`
- FastAPI handoff (`run_as_long_job`): wired via Wave 4's LONGTASK-01
- Async Supabase migration: Wave 2's LONGTASK-03

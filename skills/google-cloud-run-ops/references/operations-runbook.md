# Google Cloud Run Ops Runbook

Use this file for concrete command patterns after you know the target project, region, and service.

## Preflight

Run local checks first:

```powershell
gcloud --version
gcloud auth list
gcloud config get-value project
```

If you need to switch projects:

```powershell
gcloud config set project PROJECT_ID
```

## Deploy

Use the repo's existing entrypoint when it exists.

Direct deployment in this repo:

```powershell
make deploy
```

Manual Cloud Run deployment pattern:

```powershell
gcloud run deploy SERVICE `
  --source . `
  --region REGION `
  --project PROJECT_ID
```

Trigger a Cloud Build-based rollout when the repo already uses triggers:

```powershell
gcloud beta builds triggers run TRIGGER_NAME `
  --region REGION `
  --project PROJECT_ID `
  --branch main
```

## Observe

Describe the service:

```powershell
gcloud run services describe SERVICE `
  --region REGION `
  --project PROJECT_ID
```

List recent revisions:

```powershell
gcloud run revisions list `
  --service SERVICE `
  --region REGION `
  --project PROJECT_ID
```

List recent builds:

```powershell
gcloud builds list `
  --project PROJECT_ID `
  --region REGION `
  --limit 10
```

Read recent logs:

```powershell
gcloud logging read `
  "resource.type=cloud_run_revision AND resource.labels.service_name=SERVICE" `
  --project PROJECT_ID `
  --limit 50 `
  --format json
```

## Maintain

Update plain env vars:

```powershell
gcloud run services update SERVICE `
  --region REGION `
  --project PROJECT_ID `
  --update-env-vars KEY=VALUE
```

Update secret-backed vars:

```powershell
gcloud run services update SERVICE `
  --region REGION `
  --project PROJECT_ID `
  --update-secrets KEY=SECRET_NAME:latest
```

Adjust runtime sizing:

```powershell
gcloud run services update SERVICE `
  --region REGION `
  --project PROJECT_ID `
  --min-instances 2 `
  --max-instances 20 `
  --cpu 4 `
  --memory 8Gi
```

Inspect IAM policy:

```powershell
gcloud run services get-iam-policy SERVICE `
  --region REGION `
  --project PROJECT_ID
```

## Roll Back

Shift traffic to a known-good revision:

```powershell
gcloud run services update-traffic SERVICE `
  --region REGION `
  --project PROJECT_ID `
  --to-revisions GOOD_REVISION=100
```

Prefer rollback over ad hoc config churn during an active incident.

## Troubleshooting Cues

- Build fails before deploy:
  Check Cloud Build status, Artifact Registry permissions, and image tags.
- New revision is unhealthy:
  Compare memory, CPU, env vars, secrets, and startup behavior against the last good revision.
- Requests return `401` on internal workflow calls:
  Verify `WORKFLOW_SERVICE_SECRET` matches in Cloud Run and Supabase Edge Functions.
- Requests return `403` or users cannot call the service:
  Inspect invoker IAM, IAP posture, and whether the service is intentionally private.
- Traffic did not move:
  Check whether a new revision became ready and whether manual traffic rules are in place.

## Reporting Template

When you finish an ops task, summarize:

1. Target project, region, and service
2. Action taken or commands inspected
3. Evidence found
4. Current health or failure mode
5. Next fix or risk

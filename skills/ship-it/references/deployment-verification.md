# Deployment Verification Reference

This document contains health check endpoints, retry strategies, rollback automation, canary deployment patterns, environment variable diffing, and performance baseline collection for verifying deployments on both Vercel and Cloud Run.

---

## Backend — Cloud Run Health Endpoints

The backend exposes multiple health endpoints at different depths. Check them in order from lightest to deepest.

### Tier 1: Liveness (no dependencies)
```
GET /health/live
```
Expected: `200 OK` with JSON body.
This proves the container is running. If this fails, the deployment itself is broken (crash loop, OOM, bad image).

### Tier 2: Connection Health (Supabase + Cache)
```
GET /health/connections
```
Expected: `200 OK` with:
```json
{
  "status": "healthy",
  "supabase": { ... },
  "cache": { "status": "healthy" | "unhealthy", ... }
}
```
If cache is unhealthy but supabase is fine, the service still works (circuit breaker degrades gracefully). If supabase is unhealthy, the service is effectively down.

### Tier 3: Cache Diagnostics
```
GET /health/cache
```
Expected: detailed Redis health with circuit breaker state.
Check `circuit_breaker_state` — if it's "open", Redis has been failing consistently. The service still works but with degraded performance.

### Tier 4: Workflow Readiness
```
GET /health/workflows/readiness
```
Expected: workflow engine ready state. Important for workflow-dependent features.

### Tier 5: Embeddings
```
GET /health/embeddings
```
Expected: Gemini embedding service availability. Non-critical for basic operations.

### Tier 6: Video
```
GET /health/video
```
Expected: Video generation config status. Non-critical for basic operations.

### Authentication for Cloud Run

The service requires authentication. All health check requests must include a bearer token:
```bash
TOKEN=$(gcloud auth print-identity-token)
curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/live"
```

---

## Frontend — Vercel Verification

### Basic Availability
```bash
curl -s -o /dev/null -w "%{http_code}" <vercel-deployment-url>
```
Expected: `200`

### Deployment Status
```bash
vercel inspect <deployment-url>
# or
vercel ls --prod
```
Look for: `State: READY`, no error messages.

### Build Logs (if deployment failed)
```bash
vercel logs <deployment-url>
```

---

## Performance Baseline

### Why Baselines Matter

Deployment verification is not just "does it respond?" — it's "does it respond as well as before?" A deployment that passes health checks but doubles response times is a regression that will impact users.

### Collecting Baselines (Phase 10)

Before deploying, collect response times from current production:

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe pikar-ai --region us-central1 --format="value(status.url)")
TOKEN=$(gcloud auth print-identity-token)

# Collect 3 samples per endpoint
for i in 1 2 3; do
  echo "Sample $i:"
  curl -s -o /dev/null -w "  /health/live: %{time_total}s\n" \
    -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/live"
  curl -s -o /dev/null -w "  /health/connections: %{time_total}s\n" \
    -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/connections"
  curl -s -o /dev/null -w "  /health/cache: %{time_total}s\n" \
    -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/cache"
done
```

### Expected Baseline Ranges

| Endpoint | Expected P50 | Warning Threshold (2x) | Critical Threshold (5x) |
|----------|-------------|----------------------|------------------------|
| `/health/live` | <50ms | >100ms | >250ms |
| `/health/connections` | <200ms | >400ms | >1000ms |
| `/health/cache` | <100ms | >200ms | >500ms |
| `/health/workflows/readiness` | <300ms | >600ms | >1500ms |

### Comparing Post-Deploy (Phase 12)

After deployment, collect the same 3 samples and compare:
- **OK**: new time within 1.5x of baseline
- **Warning**: new time between 1.5x and 3x of baseline — report but don't block
- **Regression**: new time >3x of baseline — flag prominently, investigate before signing off
- **Critical**: new time >5x or endpoint timing out — consider rollback

Note: the first request after deployment may be slow (cold start). Discard the first sample and use samples 2 and 3 for comparison.

---

## Environment Variable Diffing

### Backend — Cloud Run

```bash
# Get current production env vars
gcloud run services describe pikar-ai \
  --region us-central1 \
  --format="yaml(spec.template.spec.containers[0].env)"
```

Compare against `.env.example`:
```bash
# Extract var names from .env.example
grep -E '^[A-Z_]+=' .env.example | cut -d= -f1 | sort

# Extract var names from Cloud Run
gcloud run services describe pikar-ai \
  --region us-central1 \
  --format="json(spec.template.spec.containers[0].env[].name)" | \
  python3 -c "import sys,json; [print(e['name']) for e in json.load(sys.stdin)]" | sort
```

### Frontend — Vercel

```bash
# List Vercel env vars
cd frontend && vercel env ls

# Extract expected vars from .env.example
grep -E '^[A-Z_]+=' frontend/.env.example 2>/dev/null | cut -d= -f1 | sort
```

### What to Flag

| Scenario | Severity | Action |
|----------|----------|--------|
| Var in `.env.example` but not in prod | HIGH | Warn user — may cause runtime crash |
| New `NEXT_PUBLIC_*` var missing in Vercel | CRITICAL | Frontend will break — must set before deploy |
| Var in prod but not in `.env.example` | LOW | May be legacy — note but don't block |
| Secret var value changed locally | HIGH | Never commit — warn user |

### Setting Missing Env Vars

For non-secret variables, you can set them:
```bash
# Cloud Run
gcloud run services update pikar-ai \
  --region us-central1 \
  --update-env-vars "VAR_NAME=value"

# Vercel
cd frontend && vercel env add VAR_NAME production
```

For secrets: always ask the user to set them manually through the console or CLI.

---

## Canary Deployment

### Cloud Run Canary Strategy

Cloud Run supports traffic splitting between revisions, making canary deploys straightforward.

**Step 1: Deploy without traffic**
```bash
# Deploy new revision but don't route any traffic to it
PROJECT_ID=$(gcloud config get-value project)
gcloud beta run deploy pikar-ai \
  --source . \
  --memory "4Gi" \
  --project $PROJECT_ID \
  --region "us-central1" \
  --no-allow-unauthenticated \
  --no-cpu-throttling \
  --labels "created-by=adk" \
  --no-traffic
```

**Step 2: Get the new revision name**
```bash
gcloud run revisions list \
  --service pikar-ai \
  --region us-central1 \
  --limit 1 \
  --format="value(REVISION)"
```

**Step 3: Canary at 10%**
```bash
gcloud run services update-traffic pikar-ai \
  --region us-central1 \
  --to-revisions=<new-revision>=10
```

Verify at 10%: hit health endpoints multiple times, check error rates in logs.
```bash
gcloud run logs read pikar-ai \
  --region us-central1 \
  --limit 20 \
  --log-filter="severity>=ERROR AND timestamp>=\"$(date -u -d '2 minutes ago' +%Y-%m-%dT%H:%M:%SZ)\""
```

**Step 4: Ramp to 50%**
```bash
gcloud run services update-traffic pikar-ai \
  --region us-central1 \
  --to-revisions=<new-revision>=50
```

Wait 30 seconds. Check logs again for errors.

**Step 5: Ramp to 100%**
```bash
gcloud run services update-traffic pikar-ai \
  --region us-central1 \
  --to-revisions=<new-revision>=100
```

**Abort at any stage**: If errors are detected, immediately send all traffic back:
```bash
gcloud run services update-traffic pikar-ai \
  --region us-central1 \
  --to-revisions=<previous-revision>=100
```

### Vercel Canary

Vercel does not natively support traffic splitting for production deployments. Deployments are atomic — the new version replaces the old one. However, you can use preview deployments as a canary:

1. Deploy as preview first: `vercel` (without `--prod`)
2. Verify the preview URL manually or with health checks.
3. If healthy, promote to production: `vercel promote <preview-url>`

---

## Rollback Automation

### When to Rollback

Trigger automatic rollback when:
- 5 consecutive health check failures after deployment
- Critical error rate spike in logs (>10 errors in 2 minutes)
- Service is returning 500/503 consistently
- Performance degradation >5x baseline (endpoints timing out)

### Cloud Run Rollback

**Step 1: Find the previous good revision**
```bash
gcloud run revisions list \
  --service pikar-ai \
  --region us-central1 \
  --limit 5 \
  --format="table(REVISION, ACTIVE, DEPLOYED)"
```

The previous revision is typically the second one in the list (the first is the failed new one).

**Step 2: Route all traffic to the previous revision**
```bash
gcloud run services update-traffic pikar-ai \
  --region us-central1 \
  --to-revisions=<previous-revision>=100
```

**Step 3: Verify rollback**
```bash
TOKEN=$(gcloud auth print-identity-token)
SERVICE_URL=$(gcloud run services describe pikar-ai --region us-central1 --format="value(status.url)")
curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/live"
curl -s -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health/connections"
```

**Step 4: Clean up the failed revision (optional)**
```bash
gcloud run revisions delete <failed-revision> \
  --service pikar-ai \
  --region us-central1 \
  --quiet
```

### Vercel Rollback

**Step 1: List recent production deployments**
```bash
vercel ls --prod
```

**Step 2: Promote the previous deployment**
```bash
# Use the URL of the last known-good deployment
vercel promote <previous-deployment-url>
```

Or use the Vercel CLI rollback:
```bash
vercel rollback
```

**Step 3: Verify rollback**
```bash
curl -s -o /dev/null -w "%{http_code}" <production-url>
```

### Post-Rollback Protocol

After any rollback:
1. Confirm both platforms are healthy again.
2. Document what failed: specific error messages, log entries, health check responses.
3. Tag the failed commit: `git tag rollback/<date>-<short-hash>`
4. Report to the user with full diagnosis.
5. Do NOT attempt automatic re-deployment after rollback — let the user decide next steps.

---

## Retry Strategy

### Timing
- Wait 10 seconds after deployment before first health check (cold start buffer).
- Wait 15 seconds between retries for Cloud Run (revision propagation).
- Wait 10 seconds between retries for Vercel (edge propagation).
- Discard first health check sample after cold start — use subsequent samples.

### Retry Classification

**Transient (just retry):**
- 503 Service Unavailable — revision still starting
- Connection timeout — cold start
- DNS resolution failure — propagation delay

**Config issue (fix then retry):**
- 500 Internal Server Error — check logs for stack trace
- Health check returns "unhealthy" for a specific service — check env vars
- Build failed — check build logs for missing dependencies

**Code issue (fix, commit, re-deploy):**
- Import errors in logs
- Syntax errors
- Test failures that slipped through
- Runtime type errors

### Maximum Retries
- Transient retries: up to 5, with exponential backoff (10s, 20s, 40s, 60s, 60s)
- After fixing a config/code issue: reset retry counter for that platform
- Hard limit: 5 fix-and-retry cycles per platform before triggering auto-rollback

---

## Cloud Run Diagnostic Commands

```bash
# Recent logs (last 50 entries)
gcloud run logs read pikar-ai --region us-central1 --limit 50

# Error-level logs only
gcloud run logs read pikar-ai --region us-central1 --limit 50 --log-filter="severity>=ERROR"

# Recent errors (last 5 minutes)
gcloud run logs read pikar-ai --region us-central1 --limit 20 \
  --log-filter="severity>=ERROR AND timestamp>=\"$(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%SZ)\""

# Service status and conditions
gcloud run services describe pikar-ai --region us-central1 --format="value(status.conditions)"

# Latest revisions
gcloud run revisions list --service pikar-ai --region us-central1 --limit 5

# Current traffic split
gcloud run services describe pikar-ai --region us-central1 --format="yaml(status.traffic)"

# Container resource usage
gcloud run services describe pikar-ai --region us-central1 \
  --format="yaml(spec.template.spec.containers[0].resources)"
```

## Vercel Diagnostic Commands

```bash
# List recent deployments
vercel ls --prod

# Inspect a specific deployment
vercel inspect <url>

# View deployment logs
vercel logs <url>

# Check project status
vercel project ls

# View env vars
vercel env ls
```

---

## Common Failure Patterns

### Cloud Run: "Container failed to start"
- Missing required env var (check GOOGLE_API_KEY, SUPABASE_URL, REDIS_HOST)
- Python import error (missing dependency in pyproject.toml)
- Port binding issue (service must listen on PORT env var, defaults to 8080)

### Cloud Run: "Revision not ready"
- Build still in progress — wait and check again
- Previous build failed — check Cloud Build logs
- Quota exceeded — check billing/quota page

### Cloud Run: "503 Service Unavailable"
- All instances are starting up (cold start) — wait 30s
- Instance crashed — check logs for stack trace
- Memory limit exceeded — increase `--memory`

### Vercel: "Build failed"
- TypeScript errors not caught locally (stricter CI tsconfig)
- Missing env vars in Vercel project settings
- Node.js version mismatch
- next.config issues

### Vercel: "Function timeout"
- API route exceeding max duration
- Unresolved promise in Server Component
- External service timeout (Supabase, backend API)

### Vercel: "Edge function error"
- Using Node.js APIs in edge runtime
- Importing incompatible packages
- Environment variable not set for edge runtime

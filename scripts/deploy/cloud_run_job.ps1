# Deploy WorkflowWorker as a Cloud Run Job + Cloud Scheduler trigger.
#
# Usage (from repo root):
#   pwsh scripts/deploy/cloud_run_job.ps1
#   pwsh scripts/deploy/cloud_run_job.ps1 -Project pikar-ai-project -Region us-central1
#   pwsh scripts/deploy/cloud_run_job.ps1 -ImageTag v1.2.3
#
# Per memory note project_cloud_run_source_rebuild_broken_2026_05_07:
# PowerShell will eat unquoted commas inside flag values (--startup-probe etc).
# All flag values containing commas in this script are stored in $variables and
# passed by reference, never inlined.

param(
    [string]$Project = "pikar-ai-project",
    [string]$Region = "us-central1",
    [string]$ImageTag = "latest",
    [string]$Repository = "cloud-run-source-deploy",
    [string]$JobName = "workflow-worker",
    [string]$SchedulerJobName = "worker-trigger",
    [string]$ServiceAccount = "agents@pikar-ai-project.iam.gserviceaccount.com",
    [string]$ReferenceService = "pikar-ai",
    [string]$Schedule = "*/5 * * * *"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot

# --- preflight: gcloud auth --------------------------------------------------

Write-Output "============================================================"
Write-Output "  Pikar-AI WorkflowWorker — Cloud Run Job deploy"
Write-Output "  Project        : $Project"
Write-Output "  Region         : $Region"
Write-Output "  Job name       : $JobName"
Write-Output "  Service acct   : $ServiceAccount"
Write-Output "  Schedule       : $Schedule"
Write-Output "============================================================"

$activeAccount = (gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null)
if (-not $activeAccount) {
    Write-Error "gcloud is not authenticated. Run: gcloud auth login"
    exit 1
}
Write-Output "  Authed as      : $activeAccount"

# Ensure project is reachable
$projectNumber = (gcloud projects describe $Project --format="value(projectNumber)" 2>$null)
if (-not $projectNumber) {
    Write-Error "Cannot describe project '$Project'. Check access or run: gcloud auth application-default login"
    exit 1
}
Write-Output "  Project number : $projectNumber"

# --- build image -------------------------------------------------------------

$image = "$Region-docker.pkg.dev/$Project/$Repository/$JobName" + ":" + $ImageTag

# Worker dockerfile must exist (created alongside this script in LONGTASK-02).
$workerDockerfile = Join-Path $repoRoot "Dockerfile.worker"
if (-not (Test-Path $workerDockerfile)) {
    Write-Error "Dockerfile.worker not found at $workerDockerfile. Did you forget to commit it?"
    exit 1
}

Write-Output ""
Write-Output "[1/3] Submitting build to Cloud Build -> $image"

# Use cloudbuild.build-only.yaml — `gcloud builds submit --tag X` is broken
# for non-root Dockerfiles (always uses Dockerfile, ignores --file overrides).
# The build-only config explicitly runs `docker build --file Dockerfile.worker`.
$buildOnlyConfig = Join-Path $repoRoot "cloudbuild.build-only.yaml"
if (-not (Test-Path $buildOnlyConfig)) {
    Write-Error "cloudbuild.build-only.yaml not found at $buildOnlyConfig. Did you forget to commit it?"
    exit 1
}

# Comma-bearing substitutions value stored in a $variable per the comma-eating note.
$substitutions = "_REGION=$Region,_PROJECT_ID=$Project,_REPOSITORY=$Repository,_JOB_NAME=$JobName,_IMAGE_TAG=$ImageTag"

gcloud builds submit `
    --project $Project `
    --config $buildOnlyConfig `
    --substitutions $substitutions `
    $repoRoot

if ($LASTEXITCODE -ne 0) {
    Write-Output ""
    Write-Output "  Cloud Build failed. Falling back to local docker build + push."
    Write-Output "  Prerequisites:"
    Write-Output "    1. Docker Desktop running (`docker version` must succeed)"
    Write-Output "    2. gcloud auth configure-docker $Region-docker.pkg.dev"

    docker version 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Error "docker daemon is not running. Start Docker Desktop and re-run, or fix the Cloud Build error above."
        exit 1
    }

    docker build -f Dockerfile.worker -t $image $repoRoot
    if ($LASTEXITCODE -ne 0) { Write-Error "docker build failed"; exit 1 }

    docker push $image
    if ($LASTEXITCODE -ne 0) {
        Write-Error "docker push failed. Run: gcloud auth configure-docker $Region-docker.pkg.dev"
        exit 1
    }
}

# --- mirror env vars from the live FastAPI service --------------------------

Write-Output ""
Write-Output "[2/3] Inheriting env vars from service '$ReferenceService'..."

$envKeys = @(
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "REDIS_HOST",
    "REDIS_PORT",
    "GOOGLE_CLOUD_PROJECT"
)

# Pull existing env from the FastAPI service so the worker sees the same
# Supabase/Redis/etc. We only forward the keys the worker needs.
$serviceEnvRaw = (gcloud run services describe $ReferenceService `
    --project $Project `
    --region $Region `
    --format="value(spec.template.spec.containers[0].env)" 2>$null)

$inheritedEnv = @{}
if ($serviceEnvRaw) {
    # gcloud emits semi-structured "[{name=FOO,value=BAR}, {name=BAZ,value=QUX}]" — parse loosely.
    $matches = [regex]::Matches($serviceEnvRaw, "name=([A-Z_][A-Z0-9_]*)\s*[,;]\s*value=([^}]+)\}")
    foreach ($m in $matches) {
        $key = $m.Groups[1].Value
        $val = $m.Groups[2].Value.TrimEnd(',', ' ', '}', ']')
        if ($envKeys -contains $key) {
            $inheritedEnv[$key] = $val
        }
    }
}

foreach ($k in $envKeys) {
    if (-not $inheritedEnv.ContainsKey($k)) {
        Write-Warning "  Could not inherit env var '$k' from $ReferenceService — set it manually before running the job."
    } else {
        $shown = if ($k -match "KEY|SECRET|TOKEN") { "<redacted>" } else { $inheritedEnv[$k] }
        Write-Output "    $k = $shown"
    }
}

# Merge with worker-only overrides (these came from the LONGTASK-01/02 spec).
$workerOverrides = @{
    "ENABLE_CONVERSATION_SUMMARIZER" = "true"
    "SESSION_MAX_EVENTS"             = "200"
}

$envPairs = @()
foreach ($entry in $inheritedEnv.GetEnumerator()) {
    $envPairs += ("{0}={1}" -f $entry.Key, $entry.Value)
}
foreach ($entry in $workerOverrides.GetEnumerator()) {
    $envPairs += ("{0}={1}" -f $entry.Key, $entry.Value)
}

# IMPORTANT: --set-env-vars uses "," as separator by default. Use a custom
# delimiter prefix "^@^" to safely embed values that may contain commas.
# This is exactly the gcloud workaround referenced by the memory note.
$envFlag = "^@@^" + ($envPairs -join "@@")

# --- deploy / update Cloud Run Job ------------------------------------------

Write-Output ""
Write-Output "[3/3] Deploying Cloud Run Job '$JobName'..."

$existing = (gcloud run jobs describe $JobName `
    --project $Project `
    --region $Region `
    --format="value(metadata.name)" 2>$null)

$jobAction = if ($existing) { "update" } else { "create" }

# Memory + CPU + retry config kept in $variables so commas never see the bare CLI.
$memory       = "1Gi"
$cpu          = "1"
$maxRetries   = "2"
$parallelism  = "1"
$taskTimeout  = "3600s"

if ($jobAction -eq "create") {
    gcloud run jobs create $JobName `
        --project $Project `
        --region $Region `
        --image $image `
        --service-account $ServiceAccount `
        --memory $memory `
        --cpu $cpu `
        --max-retries $maxRetries `
        --parallelism $parallelism `
        --task-timeout $taskTimeout `
        --set-env-vars $envFlag
} else {
    gcloud run jobs update $JobName `
        --project $Project `
        --region $Region `
        --image $image `
        --service-account $ServiceAccount `
        --memory $memory `
        --cpu $cpu `
        --max-retries $maxRetries `
        --parallelism $parallelism `
        --task-timeout $taskTimeout `
        --set-env-vars $envFlag
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "gcloud run jobs $jobAction failed"
    exit 1
}

# --- scheduler trigger -------------------------------------------------------

Write-Output ""
Write-Output "[scheduler] Configuring Cloud Scheduler '$SchedulerJobName' -> job '$JobName'..."

$jobUri = "https://run.googleapis.com/v2/projects/$Project/locations/$Region/jobs/$JobName" + ":run"

$existingScheduler = (gcloud scheduler jobs describe $SchedulerJobName `
    --project $Project `
    --location $Region `
    --format="value(name)" 2>$null)

$schedAction = if ($existingScheduler) { "update" } else { "create" }

if ($schedAction -eq "create") {
    gcloud scheduler jobs create http $SchedulerJobName `
        --project $Project `
        --location $Region `
        --schedule $Schedule `
        --uri $jobUri `
        --http-method POST `
        --oauth-service-account-email $ServiceAccount `
        --oauth-token-scope "https://www.googleapis.com/auth/cloud-platform"
} else {
    gcloud scheduler jobs update http $SchedulerJobName `
        --project $Project `
        --location $Region `
        --schedule $Schedule `
        --uri $jobUri `
        --http-method POST `
        --oauth-service-account-email $ServiceAccount `
        --oauth-token-scope "https://www.googleapis.com/auth/cloud-platform"
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "gcloud scheduler jobs $schedAction failed"
    exit 1
}

# --- success -----------------------------------------------------------------

Write-Output ""
Write-Output "============================================================"
Write-Output "  SUCCESS"
Write-Output "============================================================"
Write-Output "  Job             : $JobName ($jobAction)"
Write-Output "  Image           : $image"
Write-Output "  Schedule        : $Schedule (every 5 min)"
Write-Output "  Scheduler job   : $SchedulerJobName ($schedAction)"
Write-Output ""
Write-Output "Manual trigger:"
Write-Output "  gcloud run jobs execute $JobName --region $Region --project $Project"
Write-Output ""
Write-Output "Tail logs:"
Write-Output "  gcloud run jobs logs read $JobName --region $Region --project $Project"
Write-Output ""

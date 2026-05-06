# Fast Cloud Run deploy: build image locally + push to Artifact Registry + deploy.
# Skips Cloud Build entirely (saves ~6-10 min vs `gcloud run deploy --source`).
#
# Prerequisites:
#   - Docker Desktop running
#   - gcloud auth login + project set
#   - One-time: gcloud auth configure-docker us-central1-docker.pkg.dev
#
# Usage (from repo root):
#   pwsh scripts/deploy-fast.ps1                # build + push + deploy
#   pwsh scripts/deploy-fast.ps1 -SkipBuild     # just deploy the latest tag (re-deploy without rebuild)
#   pwsh scripts/deploy-fast.ps1 -Tag custom    # use an explicit image tag instead of git SHA

param(
    [switch]$SkipBuild,
    [string]$Tag = ""
)

$ErrorActionPreference = 'Stop'

# Resolve repo root (script lives in scripts/, so parent is repo root)
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

# --- preflight ---------------------------------------------------------------

# Docker daemon
$dockerOk = $false
try {
    $info = docker info --format '{{.ServerVersion}}' 2>&1
    if ($LASTEXITCODE -eq 0 -and $info) { $dockerOk = $true }
} catch { $dockerOk = $false }
if (-not $dockerOk) {
    Write-Error "Docker daemon is not running. Start Docker Desktop and retry."
    exit 1
}

# gcloud auth
$projectId = (gcloud config get-value project 2>$null).Trim()
if (-not $projectId) {
    Write-Error "gcloud project is not set. Run: gcloud config set project <id>"
    exit 1
}
$projectNumber = (gcloud projects describe $projectId --format='value(projectNumber)' 2>$null).Trim()
if (-not $projectNumber) {
    Write-Error "Failed to resolve project number for $projectId. Check gcloud auth."
    exit 1
}

# Image tag — git short SHA by default, or override
if (-not $Tag) {
    $Tag = (git rev-parse --short HEAD 2>$null).Trim()
    if (-not $Tag) { $Tag = "manual-$(Get-Date -Format 'yyyyMMdd-HHmmss')" }
}
$registry = "us-central1-docker.pkg.dev/$projectId/cloud-run-source-deploy/pikar-ai"
$imageTagged = "$registry`:$Tag"
$imageLatest = "$registry`:latest"

# Read version from pyproject.toml so the deployed container reports it
$version = (Select-String -Path "$repoRoot\pyproject.toml" -Pattern '^version = "(.*)"' |
    ForEach-Object { $_.Matches[0].Groups[1].Value })
if (-not $version) { $version = '0.0.0' }

Write-Output "============================================================"
Write-Output "  Project        : $projectId  ($projectNumber)"
Write-Output "  Image          : $imageTagged"
Write-Output "  Version        : $version"
Write-Output "  Skip build     : $SkipBuild"
Write-Output "============================================================"

# --- build + push ------------------------------------------------------------

if (-not $SkipBuild) {
    Write-Output ""
    Write-Output "[1/3] Building image (this is the slow part — local Docker)..."
    $buildStart = Get-Date
    docker build `
        --tag $imageTagged `
        --tag $imageLatest `
        --build-arg "AGENT_VERSION=$version" `
        --build-arg "COMMIT_SHA=$Tag" `
        $repoRoot
    if ($LASTEXITCODE -ne 0) { Write-Error "docker build failed"; exit 1 }
    $buildDur = [int]((Get-Date) - $buildStart).TotalSeconds
    Write-Output "[1/3] Build complete in ${buildDur}s"

    Write-Output ""
    Write-Output "[2/3] Pushing image to Artifact Registry..."
    $pushStart = Get-Date
    docker push $imageTagged
    if ($LASTEXITCODE -ne 0) {
        Write-Error "docker push failed. If this is the first push, run: gcloud auth configure-docker us-central1-docker.pkg.dev"
        exit 1
    }
    docker push $imageLatest
    $pushDur = [int]((Get-Date) - $pushStart).TotalSeconds
    Write-Output "[2/3] Push complete in ${pushDur}s"
} else {
    Write-Output "[1/3 + 2/3] Skipped (re-deploying existing tag $Tag)"
}

# --- deploy ------------------------------------------------------------------

Write-Output ""
Write-Output "[3/3] Deploying revision via gcloud run deploy --image..."
$deployStart = Get-Date

$envVars = "^;^APP_URL=https://pikar-ai-$projectNumber.us-central1.run.app" +
           ";ALLOWED_ORIGINS=https://pikar-ai.com,https://www.pikar-ai.com,https://admin.pikar-ai.com,https://pikar-ai.vercel.app,https://pikar-ai-joelferuzi-gmailcoms-projects.vercel.app,https://pikar-ai-git-main-joelferuzi-gmailcoms-projects.vercel.app" +
           ";AGENT_VERSION=$version" +
           ";COMMIT_SHA=$Tag"

gcloud beta run deploy pikar-ai `
    --image $imageTagged `
    --memory 4Gi `
    --project $projectId `
    --region us-central1 `
    --port 8000 `
    --no-cpu-throttling `
    --min-instances 2 `
    --max-instances 10 `
    --concurrency 250 `
    --cpu 2 `
    --timeout 1800 `
    --startup-probe "httpGet.path=/health/live,httpGet.port=8000,initialDelaySeconds=10,timeoutSeconds=10,periodSeconds=10,failureThreshold=12" `
    --liveness-probe "httpGet.path=/health/live,httpGet.port=8000,initialDelaySeconds=15,timeoutSeconds=5,periodSeconds=30,failureThreshold=3" `
    --labels "created-by=adk" `
    --update-env-vars $envVars `
    --allow-unauthenticated

if ($LASTEXITCODE -ne 0) {
    Write-Error "gcloud deploy failed"
    exit 1
}
$deployDur = [int]((Get-Date) - $deployStart).TotalSeconds
Write-Output ""
Write-Output "[3/3] Deploy complete in ${deployDur}s"

Write-Output ""
Write-Output "Done. Image: $imageTagged"

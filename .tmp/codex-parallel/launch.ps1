param(
  [string[]]$Ids,
  [switch]$RecreateWorktrees,
  [string]$BaseRef = 'HEAD',
  [switch]$Oss,
  [ValidateSet('ollama','lmstudio')]
  [string]$LocalProvider,
  [string]$Model,
  [string]$Profile,
  [string]$HttpProxy,
  [string]$HttpsProxy
)
$ErrorActionPreference = 'Stop'
$repo = (Get-Location).Path
$base = Join-Path $repo '.tmp/codex-parallel'
$promptsDir = Join-Path $base 'prompts'
$runsDir = Join-Path $base 'runs'
$wtsDir = Join-Path $base 'worktrees'
New-Item -ItemType Directory -Force $wtsDir | Out-Null
New-Item -ItemType Directory -Force $runsDir | Out-Null

# Optional cleanup of earlier feasibility test worktree
$testWt = Join-Path $base 'test-worktree'
if (Test-Path $testWt) {
  try {
    git worktree remove --force $testWt | Out-Null
  } catch {
    Write-Warning "Could not remove feasibility test worktree: $($_.Exception.Message)"
  }
}
try {
  git branch -D codex/test-worktree 2>$null | Out-Null
} catch {}

$tasks = @(
  @{ id='pr0'; branch='codex/pr0-hygiene'; wt='wt-pr0'; prompt='pr0.txt' },
  @{ id='pr1'; branch='codex/pr1-workflow-async'; wt='wt-pr1'; prompt='pr1.txt' },
  @{ id='pr2'; branch='codex/pr2-cache-breaker'; wt='wt-pr2'; prompt='pr2.txt' },
  @{ id='pr3'; branch='codex/pr3-ci-hardening'; wt='wt-pr3'; prompt='pr3.txt' },
  @{ id='pr4'; branch='codex/pr4-fastapi-split'; wt='wt-pr4'; prompt='pr4.txt' },
  @{ id='pr5'; branch='codex/pr5-chat-split'; wt='wt-pr5'; prompt='pr5.txt' },
  @{ id='pr6'; branch='codex/pr6-import-cleanup'; wt='wt-pr6'; prompt='pr6.txt' }
)

if ($Ids -and $Ids.Count -gt 0) {
  $wanted = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
  foreach ($id in $Ids) {
    if ($id) { [void]$wanted.Add($id) }
  }
  $tasks = @($tasks | Where-Object { $wanted.Contains($_.id) })
  if ($tasks.Count -eq 0) {
    throw "No matching task ids found. Valid ids: pr0, pr1, pr2, pr3, pr4, pr5, pr6"
  }
}

$launched = @()
foreach ($t in $tasks) {
  $wtPath = Join-Path $wtsDir $t.wt
  $runPath = Join-Path $runsDir $t.id
  $codexHome = Join-Path $base (Join-Path 'codex-home' $t.id)
  New-Item -ItemType Directory -Force $runPath | Out-Null
  New-Item -ItemType Directory -Force $codexHome | Out-Null
  $promptPath = Join-Path $promptsDir $t.prompt
  $resultPath = Join-Path $runPath 'result.txt'
  $eventsPath = Join-Path $runPath 'events.jsonl'
  $stderrPath = Join-Path $runPath 'stderr.log'
  if ($RecreateWorktrees -and (Test-Path -LiteralPath $wtPath)) {
    try {
      & git worktree remove --force $wtPath | Out-Null
    } catch {
      throw "Failed to recreate worktree '$wtPath'. Run reset.ps1 first. Error: $($_.Exception.Message)"
    }
  }

  if (-not (Test-Path -LiteralPath $wtPath)) {
    $branchExists = $false
    & git show-ref --verify --quiet ("refs/heads/{0}" -f $t.branch)
    if ($LASTEXITCODE -eq 0) { $branchExists = $true }
    if ($branchExists) {
      & git worktree add $wtPath $t.branch
    } else {
      & git worktree add -b $t.branch $wtPath $BaseRef
    }
  }

  $cmd = @"
Set-Location -LiteralPath '$wtPath'
$env:CODEX_HOME = '$codexHome'
"@
  if ($HttpProxy) {
    $cmd += "`r`n`$env:HTTP_PROXY = '$HttpProxy'"
  }
  if ($HttpsProxy) {
    $cmd += "`r`n`$env:HTTPS_PROXY = '$HttpsProxy'"
  }
  $cmd += @"
`$codexArgs = @('exec','-a','never','-s','workspace-write','--color','never','--json','-o','$resultPath','-')
"@
  if ($Profile) {
    $cmd += "`r`n`$codexArgs += @('-p','$Profile')"
  }
  if ($Model) {
    $cmd += "`r`n`$codexArgs += @('-m','$Model')"
  }
  if ($Oss) {
    $cmd += "`r`n`$codexArgs += '--oss'"
  }
  if ($LocalProvider) {
    $cmd += "`r`n`$codexArgs += @('--local-provider','$LocalProvider')"
  }
  $cmd += @"
Get-Content -LiteralPath '$promptPath' -Raw | & codex @codexArgs 1> '$eventsPath' 2> '$stderrPath'
"@

  $proc = Start-Process -FilePath 'C:\Program Files\PowerShell\7\pwsh.exe' -ArgumentList @('-NoLogo','-NoProfile','-Command',$cmd) -WorkingDirectory $wtPath -PassThru

  $launched += [pscustomobject]@{
    id = $t.id
    branch = $t.branch
    worktree = $wtPath
    prompt = $promptPath
    codex_home = $codexHome
    mode = if ($Oss) { 'oss' } else { 'remote' }
    local_provider = $LocalProvider
    model = $Model
    pid = $proc.Id
    result = $resultPath
    events = $eventsPath
    stderr = $stderrPath
    launched_at = (Get-Date).ToString('o')
  }
}

$launched | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $base 'launch-status.json')
$launched | Format-Table -AutoSize | Out-String -Width 4096 | Set-Content -LiteralPath (Join-Path $base 'launch-status.txt')
$launched | Format-Table -AutoSize



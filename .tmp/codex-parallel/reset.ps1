param(
  [switch]$DropBranches,
  [switch]$KeepRuns,
  [switch]$KeepCodexHome
)

$ErrorActionPreference = 'Stop'
$repo = (Get-Location).Path
$base = Join-Path $repo '.tmp/codex-parallel'
$statusPath = Join-Path $base 'launch-status.json'
$wtsDir = Join-Path $base 'worktrees'
$runsDir = Join-Path $base 'runs'
$codexHomeDir = Join-Path $base 'codex-home'

if (-not (Test-Path -LiteralPath $base)) {
  Write-Host "Nothing to reset: $base does not exist."
  return
}

if (Test-Path -LiteralPath $statusPath) {
  try {
    $status = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
    foreach ($row in @($status)) {
      if (-not $row.pid) { continue }
      $proc = Get-Process -Id $row.pid -ErrorAction SilentlyContinue
      if ($proc) {
        Write-Host "Stopping worker $($row.id) (PID $($row.pid))..."
        Stop-Process -Id $row.pid -Force -ErrorAction SilentlyContinue
      }
    }
  } catch {
    Write-Warning "Could not parse $statusPath: $($_.Exception.Message)"
  }
}

if (Test-Path -LiteralPath $wtsDir) {
  Get-ChildItem -LiteralPath $wtsDir -Directory | ForEach-Object {
    try {
      Write-Host "Removing worktree $($_.FullName)..."
      & git worktree remove --force $_.FullName | Out-Null
    } catch {
      Write-Warning "Failed to remove worktree $($_.FullName): $($_.Exception.Message)"
    }
  }
}

$testWt = Join-Path $base 'test-worktree'
if (Test-Path -LiteralPath $testWt) {
  try {
    & git worktree remove --force $testWt | Out-Null
  } catch {
    Write-Warning "Failed to remove feasibility test worktree: $($_.Exception.Message)"
  }
}

if ($DropBranches) {
  $branchPatterns = @('refs/heads/codex/pr0-*','refs/heads/codex/pr1-*','refs/heads/codex/pr2-*','refs/heads/codex/pr3-*','refs/heads/codex/pr4-*','refs/heads/codex/pr5-*','refs/heads/codex/pr6-*','refs/heads/codex/test-worktree')
  $refs = @()
  foreach ($pattern in $branchPatterns) {
    $refs += @(& git for-each-ref --format='%(refname:short)' $pattern 2>$null)
  }
  $refs = @($refs | Where-Object { $_ } | Sort-Object -Unique)
  foreach ($branch in $refs) {
    try {
      Write-Host "Deleting branch $branch..."
      & git branch -D $branch | Out-Null
    } catch {
      Write-Warning "Failed to delete branch $branch: $($_.Exception.Message)"
    }
  }
}

foreach ($file in @('launch-status.json','launch-status.txt')) {
  $p = Join-Path $base $file
  if (Test-Path -LiteralPath $p) {
    Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
  }
}

if (-not $KeepRuns -and (Test-Path -LiteralPath $runsDir)) {
  Get-ChildItem -LiteralPath $runsDir -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

if (-not $KeepCodexHome -and (Test-Path -LiteralPath $codexHomeDir)) {
  Get-ChildItem -LiteralPath $codexHomeDir -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Reset complete."


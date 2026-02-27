param(
  [switch]$ShowDiff,
  [int]$ResultPreviewLines = 30
)

$ErrorActionPreference = 'Stop'
$repo = (Get-Location).Path
$base = Join-Path $repo '.tmp/codex-parallel'
$statusPath = Join-Path $base 'launch-status.json'

if (-not (Test-Path -LiteralPath $statusPath)) {
  throw "No launch status found at $statusPath. Run launch.ps1 first."
}

$rows = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json

foreach ($row in @($rows)) {
  Write-Host "`n=== $($row.id) | $($row.branch) ==="
  Write-Host "Worktree: $($row.worktree)"

  if (Test-Path -LiteralPath $row.worktree) {
    Write-Host "-- git status --"
    & git -C $row.worktree status --short
    Write-Host "-- diff stat --"
    & git -C $row.worktree diff --stat
    if ($ShowDiff) {
      Write-Host "-- diff --"
      & git -C $row.worktree diff
    }
  } else {
    Write-Host "<worktree missing>"
  }

  Write-Host "-- result preview --"
  if (Test-Path -LiteralPath $row.result) {
    Get-Content -LiteralPath $row.result -TotalCount $ResultPreviewLines
  } else {
    Write-Host "<no result file>"
  }

  Write-Host "-- stderr tail --"
  if (Test-Path -LiteralPath $row.stderr) {
    Get-Content -LiteralPath $row.stderr -Tail 10
  } else {
    Write-Host "<no stderr file>"
  }
}


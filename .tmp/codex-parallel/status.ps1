param(
  [switch]$VerboseErrors
)

$ErrorActionPreference = 'Stop'
$repo = (Get-Location).Path
$base = Join-Path $repo '.tmp/codex-parallel'
$statusPath = Join-Path $base 'launch-status.json'

if (-not (Test-Path -LiteralPath $statusPath)) {
  throw "No launch status found at $statusPath. Run launch.ps1 first."
}

$rows = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
$out = foreach ($row in @($rows)) {
  $proc = Get-Process -Id $row.pid -ErrorAction SilentlyContinue
  $alive = [bool]$proc
  $changes = 0
  $branch = ''
  $state = if ($alive) { 'running' } else { 'exited' }
  $message = ''

  if (Test-Path -LiteralPath $row.worktree) {
    $branch = (& git -C $row.worktree rev-parse --abbrev-ref HEAD 2>$null)
    $statusLines = @(& git -C $row.worktree status --porcelain 2>$null)
    $changes = ($statusLines | Where-Object { $_ }).Count
  }

  if (Test-Path -LiteralPath $row.events) {
    $events = @()
    foreach ($line in Get-Content -LiteralPath $row.events) {
      try { $events += ($line | ConvertFrom-Json) } catch {}
    }
    $failed = $events | Where-Object { $_.type -eq 'turn.failed' } | Select-Object -Last 1
    $completed = $events | Where-Object { $_.type -eq 'turn.completed' } | Select-Object -Last 1
    if ($failed) {
      $state = 'failed'
      $message = $failed.error.message
    } elseif (-not $alive -and $completed) {
      $state = 'completed'
      $message = 'turn.completed'
    }
  }

  if (-not $message -and (Test-Path -LiteralPath $row.stderr)) {
    $tail = Get-Content -LiteralPath $row.stderr -Tail 5 -ErrorAction SilentlyContinue
    $tailLine = @($tail | Where-Object { $_ }) | Select-Object -Last 1
    if ($tailLine) { $message = $tailLine }
  }

  [pscustomobject]@{
    id = $row.id
    pid = $row.pid
    alive = $alive
    state = $state
    branch = $branch
    changes = $changes
    result_bytes = if (Test-Path -LiteralPath $row.result) { (Get-Item -LiteralPath $row.result).Length } else { 0 }
    message = $message
  }
}

$out | Sort-Object id | Format-Table -Wrap -AutoSize

if ($VerboseErrors) {
  foreach ($row in @($rows)) {
    Write-Host "`n=== $($row.id) stderr (tail) ==="
    if (Test-Path -LiteralPath $row.stderr) {
      Get-Content -LiteralPath $row.stderr -Tail 20
    } else {
      Write-Host "<no stderr>"
    }
  }
}


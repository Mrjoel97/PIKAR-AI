param(
  [switch]$Oss,
  [ValidateSet('ollama','lmstudio')]
  [string]$LocalProvider,
  [switch]$CheckRemoteApi
)

$ErrorActionPreference = 'Stop'

function Test-TcpPort {
  param(
    [Parameter(Mandatory=$true)][string]$Hostname,
    [Parameter(Mandatory=$true)][int]$Port,
    [int]$TimeoutMs = 3000
  )
  try {
    $client = [System.Net.Sockets.TcpClient]::new()
    $iar = $client.BeginConnect($Hostname, $Port, $null, $null)
    if (-not $iar.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) {
      $client.Close()
      return $false
    }
    $client.EndConnect($iar)
    $client.Close()
    return $true
  } catch {
    return $false
  }
}

function Test-HttpEndpoint {
  param(
    [Parameter(Mandatory=$true)][string]$Uri,
    [int]$TimeoutSec = 5
  )
  try {
    $resp = Invoke-WebRequest -Uri $Uri -Method GET -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
    return [pscustomobject]@{ ok = $true; status = [int]$resp.StatusCode; note = 'ok' }
  } catch {
    $e = $_.Exception
    $status = $null
    if ($e.PSObject.Properties.Name -contains 'Response' -and $e.Response) {
      try { $status = [int]$e.Response.StatusCode.value__ } catch {}
    }
    if ($status) {
      return [pscustomobject]@{ ok = $true; status = $status; note = 'reachable (HTTP error status is acceptable for preflight)' }
    }
    return [pscustomobject]@{ ok = $false; status = $null; note = $e.Message }
  }
}

$rows = @()

$codexCmd = Get-Command codex -ErrorAction SilentlyContinue
$rows += [pscustomobject]@{
  Check = 'codex CLI installed'
  Status = if ($codexCmd) { 'PASS' } else { 'FAIL' }
  Details = if ($codexCmd) { $codexCmd.Source } else { 'codex not found in PATH' }
}

if ($codexCmd) {
  try {
    $version = (& codex --version 2>$null | Select-Object -First 1)
    $rows += [pscustomobject]@{
      Check = 'codex version'
      Status = if ($version) { 'PASS' } else { 'WARN' }
      Details = if ($version) { $version } else { 'No version output captured' }
    }
  } catch {
    $rows += [pscustomobject]@{
      Check = 'codex version'
      Status = 'WARN'
      Details = $_.Exception.Message
    }
  }
}

$rows += [pscustomobject]@{
  Check = 'HTTP_PROXY'
  Status = if ($env:HTTP_PROXY) { 'INFO' } else { 'INFO' }
  Details = if ($env:HTTP_PROXY) { $env:HTTP_PROXY } else { '<not set>' }
}
$rows += [pscustomobject]@{
  Check = 'HTTPS_PROXY'
  Status = if ($env:HTTPS_PROXY) { 'INFO' } else { 'INFO' }
  Details = if ($env:HTTPS_PROXY) { $env:HTTPS_PROXY } else { '<not set>' }
}

$shouldCheckRemote = $CheckRemoteApi -or (-not $Oss)
if ($shouldCheckRemote) {
  $tcpOk = Test-TcpPort -Hostname 'api.openai.com' -Port 443
  $rows += [pscustomobject]@{
    Check = 'TCP api.openai.com:443'
    Status = if ($tcpOk) { 'PASS' } else { 'FAIL' }
    Details = if ($tcpOk) { 'reachable' } else { 'blocked/unreachable from this environment' }
  }

  $http = Test-HttpEndpoint -Uri 'https://api.openai.com/v1/models'
  $rows += [pscustomobject]@{
    Check = 'HTTPS api.openai.com'
    Status = if ($http.ok) { 'PASS' } else { 'FAIL' }
    Details = if ($http.status) { "status=$($http.status); $($http.note)" } else { $http.note }
  }
}

if ($Oss -or $LocalProvider) {
  $provider = if ($LocalProvider) { $LocalProvider } else { 'ollama' }
  if ($provider -eq 'ollama') {
    $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
    $rows += [pscustomobject]@{
      Check = 'ollama CLI installed'
      Status = if ($ollamaCmd) { 'PASS' } else { 'FAIL' }
      Details = if ($ollamaCmd) { $ollamaCmd.Source } else { 'ollama not found in PATH' }
    }
    $ollamaTcp = Test-TcpPort -Hostname '127.0.0.1' -Port 11434
    $rows += [pscustomobject]@{
      Check = 'Ollama localhost:11434'
      Status = if ($ollamaTcp) { 'PASS' } else { 'FAIL' }
      Details = if ($ollamaTcp) { 'reachable' } else { 'Ollama server not listening on 11434' }
    }
    if ($ollamaTcp) {
      $tags = Test-HttpEndpoint -Uri 'http://127.0.0.1:11434/api/tags'
      $rows += [pscustomobject]@{
        Check = 'Ollama /api/tags'
        Status = if ($tags.ok) { 'PASS' } else { 'FAIL' }
        Details = if ($tags.status) { "status=$($tags.status); $($tags.note)" } else { $tags.note }
      }
    }
  }

  if ($provider -eq 'lmstudio') {
    $lmTcp = Test-TcpPort -Hostname '127.0.0.1' -Port 1234
    $rows += [pscustomobject]@{
      Check = 'LM Studio localhost:1234'
      Status = if ($lmTcp) { 'PASS' } else { 'FAIL' }
      Details = if ($lmTcp) { 'reachable' } else { 'LM Studio API not listening on 1234' }
    }
    if ($lmTcp) {
      $models = Test-HttpEndpoint -Uri 'http://127.0.0.1:1234/v1/models'
      $rows += [pscustomobject]@{
        Check = 'LM Studio /v1/models'
        Status = if ($models.ok) { 'PASS' } else { 'FAIL' }
        Details = if ($models.status) { "status=$($models.status); $($models.note)" } else { $models.note }
      }
    }
  }
}

$rows | Format-Table -Wrap -AutoSize

$fails = @($rows | Where-Object { $_.Status -eq 'FAIL' })
if ($fails.Count -gt 0) {
  Write-Host ""
  Write-Host "Recommended next steps:" -ForegroundColor Yellow
  if ($Oss -or $LocalProvider) {
    Write-Host "1. Start your local provider (Ollama or LM Studio) and rerun doctor.ps1."
    Write-Host "2. Then launch workers with -Oss and optionally -LocalProvider."
  } else {
    Write-Host "1. Run this outside a network-restricted sandbox (or configure proxy)."
    Write-Host "2. Or use local model mode: launch.ps1 -Oss -LocalProvider ollama (or lmstudio)."
  }
  exit 1
}

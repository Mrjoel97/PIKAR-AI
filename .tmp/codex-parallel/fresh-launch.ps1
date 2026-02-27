param(
  [string[]]$Ids,
  [switch]$DropBranches,
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
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$reset = Join-Path $root 'reset.ps1'
$launch = Join-Path $root 'launch.ps1'

Write-Host "Resetting previous parallel run state..."
& $reset -DropBranches:$DropBranches

Write-Host "Launching Codex workers..."
if ($Ids -and $Ids.Count -gt 0) {
  & $launch -Ids $Ids -BaseRef $BaseRef -Oss:$Oss -LocalProvider $LocalProvider -Model $Model -Profile $Profile -HttpProxy $HttpProxy -HttpsProxy $HttpsProxy
} else {
  & $launch -BaseRef $BaseRef -Oss:$Oss -LocalProvider $LocalProvider -Model $Model -Profile $Profile -HttpProxy $HttpProxy -HttpsProxy $HttpsProxy
}

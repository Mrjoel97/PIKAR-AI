param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("status", "canary-on", "canary-off", "kill-on", "kill-off")]
    [string]$Action,
    [string]$ApiBase = "http://localhost:8000",
    [string]$CanaryUsers = ""
)

<#
Usage:
  pwsh scripts/rollout/workflow_rollout_helper.ps1 -Action status
  pwsh scripts/rollout/workflow_rollout_helper.ps1 -Action canary-on -CanaryUsers "uuid-1,uuid-2"
  pwsh scripts/rollout/workflow_rollout_helper.ps1 -Action canary-off
  pwsh scripts/rollout/workflow_rollout_helper.ps1 -Action kill-on
  pwsh scripts/rollout/workflow_rollout_helper.ps1 -Action kill-off

This helper updates current shell env flags and prints verification from /health/connections.
#>

function Show-Status {
    Write-Host "WORKFLOW_KILL_SWITCH=$env:WORKFLOW_KILL_SWITCH"
    Write-Host "WORKFLOW_CANARY_ENABLED=$env:WORKFLOW_CANARY_ENABLED"
    Write-Host "WORKFLOW_CANARY_USER_IDS=$env:WORKFLOW_CANARY_USER_IDS"
    try {
        $health = Invoke-RestMethod -Uri "$ApiBase/health/connections" -Method GET
        Write-Host ""
        Write-Host "Health.workflow_rollout:"
        $health.workflow_rollout | ConvertTo-Json -Depth 4
    } catch {
        Write-Warning "Unable to read $ApiBase/health/connections. Ensure backend is running."
    }
}

switch ($Action) {
    "status" {
        Show-Status
        break
    }
    "canary-on" {
        if ([string]::IsNullOrWhiteSpace($CanaryUsers)) {
            throw "Provide -CanaryUsers for canary-on"
        }
        $env:WORKFLOW_CANARY_ENABLED = "true"
        $env:WORKFLOW_CANARY_USER_IDS = $CanaryUsers
        Write-Host "Enabled canary mode for users: $CanaryUsers"
        Show-Status
        break
    }
    "canary-off" {
        $env:WORKFLOW_CANARY_ENABLED = "false"
        $env:WORKFLOW_CANARY_USER_IDS = ""
        Write-Host "Disabled canary mode."
        Show-Status
        break
    }
    "kill-on" {
        $env:WORKFLOW_KILL_SWITCH = "true"
        Write-Host "Enabled workflow kill switch."
        Show-Status
        break
    }
    "kill-off" {
        $env:WORKFLOW_KILL_SWITCH = "false"
        Write-Host "Disabled workflow kill switch."
        Show-Status
        break
    }
}

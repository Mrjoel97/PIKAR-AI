# Workflow Incident Runbook

Purpose: standardized response for workflow execution incidents in production.

## Incident Triggers
- Start failures above threshold
- Completion failures above threshold
- Repeated step failures for a workflow
- Integration outage impacting workflow execution
- Approval queue stuck or not progressing

## Severity
- `SEV-1`: payment/payroll/compliance/customer-contract impact
- `SEV-2`: customer-facing degradation without data-loss/compliance risk
- `SEV-3`: internal workflow degradation only

## Response Process
1. Detect and acknowledge incident.
2. Triage scope:
   - impacted workflows
   - impacted users
   - failure class (tool error, integration outage, auth/config error)
3. Stabilize:
   - stop or limit rollout (kill switch/canary)
   - pause problematic workflow starts
4. Mitigate:
   - apply config hotfix or rollback
   - route users to alternative path if available
5. Recover:
   - validate successful starts/completions
   - monitor for recurrence
6. Post-incident:
   - root cause analysis
   - preventive fix
   - checklist/task updates

## Required Artifacts Per Incident
- Timeline (UTC)
- Root cause
- Detection method
- Affected workflows/users
- Mitigation actions
- Permanent corrective actions

## Escalation
- SEV-1: immediate engineering lead + product lead + on-call
- SEV-2: on-call + owning team
- SEV-3: owning team during business hours


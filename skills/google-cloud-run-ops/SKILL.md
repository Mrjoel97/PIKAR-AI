---
name: google-cloud-run-ops
description: Deploy, monitor, troubleshoot, and maintain applications on Google Cloud Run and related Google Cloud services. Use when Codex needs to push a repo to Cloud Run, inspect Cloud Build or Artifact Registry state, review Cloud Run revisions or logs, manage runtime env vars, secrets, scaling, or IAM, perform rollback, or keep a Google Cloud hosted app healthy over time.
---

# Google Cloud Run Ops

Use this skill to operate an app on Google Cloud Run from an existing repository. Prefer the repo's current deployment entrypoints, infrastructure code, and secret-management path before inventing new commands or changing live settings.

## Core Workflow

1. Inspect the repository for the existing deployment surface before taking action.
2. Prefer the least surprising path:
   `make deploy` or an existing deploy script for direct rollouts,
   Cloud Build triggers for CI/CD-driven rollouts,
   Terraform for infrastructure changes that should remain codified.
3. Treat production actions, IAM changes, traffic shifts, and secret rotation as high risk. Pause for confirmation before making those changes unless the user clearly asked for them.
4. Start with read-only inspection when debugging. Change config only after you have evidence from service state, build state, or logs.
5. Report exact project, region, service, revision, and evidence when you finish. Do not claim success without those details.

## Tooling Rules

- Read the repo-specific map in `references/pikar-ai-deploy-map.md` when working in this repository.
- Read `references/operations-runbook.md` when you need concrete command patterns for deploy, monitoring, rollback, or maintenance.
- Prefer local inspection first. Any `gcloud`, `docker`, or remote verification command may need escalated shell permissions because it reaches Google Cloud.
- If a networked command fails because of sandboxing, rerun that command with escalation instead of switching to a different workflow.
- Preserve private-service defaults unless the user explicitly asks to make a service public.

## Deploy

1. Inspect the deploy surface and choose the path that matches the repo.
2. Verify the active project, region, service name, and auth context before deployment.
3. Use the existing workflow:
   direct source deploy for a one-off rollout,
   Cloud Build triggers for staged or approval-based delivery,
   Terraform for service shape, IAM, secret wiring, or networking changes.
4. After deployment, collect:
   service URL,
   latest ready revision,
   traffic allocation,
   recent build status,
   immediate warnings from logs or health checks.
5. Summarize what changed and any follow-up risks.

## Monitor And Diagnose

Start with evidence in this order:

1. Cloud Run service and revision state.
2. Cloud Build history and current trigger runs.
3. Request and application logs.
4. Secret, IAM, or networking drift only if the earlier layers point there.

Focus on:

- failed builds or missing images
- crash loops, cold starts, memory pressure, or timeouts
- 401 or 403 errors from service-to-service auth or invoker policy
- broken environment variables or secret versions
- unexpected traffic splits or a bad latest revision

For this repository, pay extra attention to `WORKFLOW_SERVICE_SECRET`, Supabase-to-backend service auth, Redis connectivity, Vertex configuration, and Cloud Build substitutions.

## Maintain Safely

- Prefer updating Terraform-managed settings in Terraform, then applying them, instead of making console-only edits.
- Use one-off Cloud Run updates only for urgent mitigation, and note that the change should be back-ported to code if it must persist.
- For secrets, prefer Secret Manager-backed configuration over plain environment variables when the repo already uses it.
- For rollback, prefer sending traffic to a known-good revision or redeploying a known-good image instead of making unrelated config changes during an incident.
- When you fix an incident, include the likely root cause, the evidence you used, and the follow-up action that should prevent recurrence.

## Response Expectations

Return a short operational summary that includes:

- target project, region, and service
- action taken or observation made
- evidence gathered
- current status
- remaining risks or next steps

If you are blocked, say exactly what is missing, such as auth, roles, project ID, service name, or approval for an escalated command.

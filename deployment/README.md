# Deployment

This directory contains the Terraform configurations for provisioning the necessary Google Cloud infrastructure for your agent.

The recommended way to deploy the infrastructure and set up the CI/CD pipeline is by using the `agent-starter-pack setup-cicd` command from the root of your project.

However, for a more hands-on approach, you can always apply the Terraform configurations manually for a do-it-yourself setup.

For detailed information on the deployment process, infrastructure, and CI/CD pipelines, please refer to the official documentation:

**[Agent Starter Pack Deployment Guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/deployment.html)**

## Service-to-Service Authentication

`WORKFLOW_SERVICE_SECRET` secures internal calls from Supabase Edge Functions to the FastAPI backend (not end-user auth).

### Purpose

- Protects internal endpoint access such as `/workflows/execute-step`
- Prevents unauthorized external callers from invoking workflow tools directly
- Keeps service auth separate from user JWT auth

### Generate a secure secret

- OpenSSL: `openssl rand -hex 32`
- Python: `python -c "import secrets; print(secrets.token_hex(32))"`

Both commands produce a high-entropy value suitable for shared-service authentication.

### Configure in both systems

- Backend (Cloud Run): set `WORKFLOW_SERVICE_SECRET` as an environment variable (prefer Secret Manager)
- Supabase Edge Functions: set `WORKFLOW_SERVICE_SECRET` in Supabase project secrets:
  `Settings -> Edge Functions -> Secrets`

Both values must match exactly.

### Rotation procedure

1. Generate a new secret value.
2. Update backend secret/configuration.
3. Update Supabase Edge Function secret.
4. Deploy backend and redeploy edge functions in the same change window.
5. Verify workflow execution calls succeed and no 401 auth errors appear.

### Troubleshooting 401 errors

- Confirm `WORKFLOW_SERVICE_SECRET` exists in both backend and Supabase edge environments.
- Confirm values are identical (no whitespace/newline differences).
- Check backend logs for service-auth rejection messages.
- Check edge function logs for:
  `Backend rejected service authentication - check WORKFLOW_SERVICE_SECRET configuration`.

### Validation checklist

- Call `/workflows/execute-step` without `X-Service-Secret` -> expect `401`.
- Call `/workflows/execute-step` with incorrect `X-Service-Secret` -> expect `401`.
- Call `/workflows/execute-step` with correct `X-Service-Secret` -> expect successful step execution.
- Run edge function workflow execution end-to-end and confirm backend execution succeeds.
- Verify backend logs for successful service-authenticated step execution and rejected attempts.

### Test integration notes

- Any integration tests that call `/workflows/execute-step` must include `X-Service-Secret`.
- Test environments should set `WORKFLOW_SERVICE_SECRET` explicitly.
- Add negative-path tests for missing/incorrect service secret where applicable.

## Current Production Runtime

The live Google runtime currently operates as:

- Cloud Run service: `pikar-ai`
- Project: `pikar-ai-project`
- Region: `us-central1`
- Redis: Memorystore Redis 7.0 (`${project_name}-cache`)
- VPC connector: `${project_name}-connector`

Operational expectation:

- Cloudflare serves the public/backend edge surface
- Cloud Run is limited to agent execution, Vertex-backed generation, and internal scheduled/runtime workloads
- Terraform remains the canonical infrastructure shape, but any manual production changes should be reconciled here immediately so infra does not drift silently

## Runtime Secret Wiring

Cloud Run should not carry sensitive production credentials as plain env vars.

The Terraform deployment surface now treats these as Secret Manager-backed runtime values:

- Core secrets from first-class variables:
  `WORKFLOW_SERVICE_SECRET`, `SCHEDULER_SECRET`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`
- Additional provider and app secrets from `runtime_secret_values`

Use `runtime_secret_values` for sensitive provider credentials such as:

- `ADMIN_ENCRYPTION_KEY`
- search/research API keys
- email/provider webhook secrets
- OAuth client secrets

Public values such as URLs, allowed origins, and publishable/anon keys can remain plain env vars unless there is a specific reason to hide them.

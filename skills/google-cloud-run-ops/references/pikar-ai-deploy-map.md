# Pikar-AI Google Cloud Map

Use this file when the task is specific to this repository.

## Quick File Map

- `CLAUDE.md`
  Declares the stack and states that the app is deployed to Google Cloud Run.
- `Makefile`
  `make deploy` uses `gcloud beta run deploy pikar-ai --source .` in `us-central1`, sets `--no-allow-unauthenticated`, disables CPU throttling, and derives `APP_URL` from the project number.
- `Dockerfile`
  Builds the runtime image for the backend, installs `uv`, Node.js, npm, and Remotion-related system dependencies, and runs as a non-root user.
- `.cloudbuild/staging.yaml`
  Builds and pushes the image to Artifact Registry, deploys staging `pikar-ai`, fetches the staging URL and identity token, runs load tests, exports load-test results to GCS, and triggers the production deployment workflow.
- `.cloudbuild/deploy-to-prod.yaml`
  Deploys the existing Artifact Registry image to the production `pikar-ai` service.
- `deployment/terraform/build_triggers.tf`
  Creates PR checks, the staging CD trigger, and the production deployment trigger with approval.
- `deployment/terraform/service.tf`
  Defines the Cloud Run v2 service in staging and prod, including image placeholder behavior, env vars, Secret Manager wiring, Redis, VPC connector, scaling, and traffic-to-latest.
- `deployment/terraform/locals.tf`
  Lists the required Google APIs, including Cloud Run, Artifact Registry, Logging, Trace, Secret Manager, Redis, and VPC Access.
- `deployment/terraform/iam.tf`
  Grants CI/CD and app service accounts the roles needed for deployment and runtime access.
- `deployment/README.md`
  Documents `WORKFLOW_SERVICE_SECRET`, rotation steps, and the expected behavior for `/workflows/execute-step`.
- `tests/load_test/README.md`
  Describes how to load test a remote Cloud Run service with an identity token.

## Operational Hotspots

- `WORKFLOW_SERVICE_SECRET`
  Must match between Cloud Run and Supabase Edge Functions. A mismatch causes internal workflow calls to fail with `401`.
- `SUPABASE_*`
  Runtime depends on multiple Supabase values being present and aligned with the target environment.
- `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GOOGLE_GENAI_USE_VERTEXAI`
  These control the Google runtime context and Vertex-backed behavior.
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`
  Redis is provisioned through Terraform and injected into Cloud Run.
- `LOGS_BUCKET_NAME`
  Staging and prod load-test and build artifacts are pushed to GCS buckets.
- Cloud Run auth posture
  `make deploy` uses `--no-allow-unauthenticated`, so invoker access and identity-token testing matter.

## Decision Guide

- Use `make deploy` for a fast, direct deployment from the current checkout.
- Use Cloud Build triggers when the task is about the normal CI/CD path, staged rollout, approvals, or post-deploy load testing.
- Use Terraform when changing service configuration that is already codified, such as scaling, networking, IAM, secrets, or supporting infrastructure.
- Check `deployment/README.md` first when debugging internal workflow authentication failures.

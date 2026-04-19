# Google Agent Service

This document covers the Google-only part of the split deployment model.

## Purpose

Google should only host the agent runtime and Vertex-backed model activity:

- ADK / A2A execution
- Gemini generation through Vertex AI
- long-running agent workflows
- voice or SSE endpoints that are not a good fit for edge runtimes

Everything public-facing should move toward Cloudflare and Vercel.

## Current Production Shape

As of April 19, 2026, the Google side is intentionally narrow:

- Google Cloud project: `pikar-ai-project`
- Region: `us-central1`
- Cloud Run service: `pikar-ai`
- Vertex AI: enabled and used for agent/model execution
- Redis: Google Memorystore Redis 7.0, 1 GiB BASIC tier
- VPC connector: `pikar-ai-connector`

This means:

- Cloudflare owns the public API and edge-facing request surface.
- Cloud Run remains the agent runtime and Vertex bridge.
- Redis-backed cache and coordination now run through managed Memorystore instead of a localhost fallback.

## Required Environment

Set these on the Google-hosted agent service:

```env
GOOGLE_CLOUD_PROJECT=your_vertex_project_id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=./secrets/your-vertex-service-account.json
GOOGLE_GENAI_USE_VERTEXAI=1
GEMINI_AGENT_MODEL_PRIMARY=gemini-2.5-pro
GEMINI_AGENT_MODEL_FALLBACK=gemini-2.5-flash
REDIS_ENABLED=1
REDIS_HOST=memorystore-private-ip
REDIS_PORT=6379
REDIS_DB=0
SKILL_EMBEDDING_WARMUP_ENABLED=0
EMBEDDING_QUOTA_COOLDOWN_SECONDS=900
```

### Runtime Notes

- `REDIS_ENABLED=1` should only be used when `REDIS_HOST` points at managed Redis reachable from Cloud Run over VPC.
- On Cloud Run, `REDIS_HOST=localhost` is treated as an invalid production fallback and the cache service disables itself instead of repeatedly failing.
- `SKILL_EMBEDDING_WARMUP_ENABLED=0` keeps Cloud Run startup from burning Vertex embedding quota during cold starts.
- `EMBEDDING_QUOTA_COOLDOWN_SECONDS` gives the embedding layer a cooldown window after quota exhaustion so the app degrades cleanly instead of hammering Vertex.

## Credential Source

Do not rely on a checked-in credential file for production.

Use one of these instead:

- mount the service-account JSON from a secure local secret path for local development
- inject it through Secret Manager or the deployment environment for production

For local or containerized startup, point `GOOGLE_APPLICATION_CREDENTIALS` at that secure file location.

## Model Guidance

Use the app's existing model env surface:

- `GEMINI_AGENT_MODEL_PRIMARY`
- `GEMINI_AGENT_MODEL_FALLBACK`

Recommended stable values for now:

- primary: `gemini-2.5-pro`
- fallback: `gemini-2.5-flash`

Optional lightweight fallback for latency-sensitive tasks:

- `gemini-2.5-flash-lite`

## Notes

- The FastAPI app already prefers Vertex mode when both `GOOGLE_CLOUD_PROJECT` and `GOOGLE_APPLICATION_CREDENTIALS` are set.
- `GOOGLE_API_KEY` should be treated as a local fallback, not the primary production path for the split architecture.
- Keep the Google service scoped to agent execution rather than public API responsibility.
- The production service is expected to use Serverless VPC Access with private-ranges egress so Redis stays on an internal address.

## Verification

Use these checks after a deployment or env change:

```bash
gcloud run services describe pikar-ai \
  --project=pikar-ai-project \
  --region=us-central1
```

```bash
curl https://pikar-ai-917671810739.us-central1.run.app/health/cache
```

```bash
curl https://pikar-ai-917671810739.us-central1.run.app/health/embeddings
```

Healthy expectations:

- `/health/cache` returns `status: ok` and reports Redis server metadata
- `/health/embeddings` returns `status: ok` and a valid embedding dimension

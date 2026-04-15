# Google Agent Service

This document covers the Google-only part of the split deployment model.

## Purpose

Google should only host the agent runtime and Vertex-backed model activity:

- ADK / A2A execution
- Gemini generation through Vertex AI
- long-running agent workflows
- voice or SSE endpoints that are not a good fit for edge runtimes

Everything public-facing should move toward Cloudflare and Vercel.

## Required Environment

Set these on the Google-hosted agent service:

```env
GOOGLE_CLOUD_PROJECT=your_vertex_project_id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=./secrets/your-vertex-service-account.json
GOOGLE_GENAI_USE_VERTEXAI=1
GEMINI_AGENT_MODEL_PRIMARY=gemini-2.5-pro
GEMINI_AGENT_MODEL_FALLBACK=gemini-2.5-flash
```

## Credential Source

The service-account JSON currently present in this repo is:

- `secrets/pikar-ai-project-23f5ed8873e1.json`

For local or containerized startup, point `GOOGLE_APPLICATION_CREDENTIALS` at that file or mount it into the runtime.

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

# External Integrations

**Analysis Date:** 2026-03-13

## Integration Model

Pikar-Ai is built around a small number of deep infrastructure dependencies and a wider ring of optional business connectors.

- Core production dependencies: Google AI/Vertex, Supabase, Redis, Google Cloud deployment services.
- Core user-facing productivity connectors: Google Workspace APIs and Supabase Auth.
- Optional or partial connectors: Stripe, Tavily, Firecrawl, SendGrid, HubSpot, Google Stitch, social publishing APIs.
- Real-time transport surfaces: Server-Sent Events and WebSockets.

## AI and Agent Runtime Integrations

### Google Gemini / Vertex AI

**Primary role**
- Main reasoning engine for agents, workflows, embeddings, and media generation.

**Where it is wired**
- `app/fast_api_app.py` decides between Vertex credentials and API-key mode.
- `app/agents/shared.py` centralizes Gemini model selection.
- `app/workflows/generator.py` uses Gemini to generate workflow templates.
- `app/routers/voice_session.py` uses Gemini Live for streaming voice sessions.
- `app/services/vertex_image_service.py` and `app/services/vertex_video_service.py` provide media generation paths.
- `app/rag/embedding_service.py` depends on Gemini embeddings.

**Auth/config**
- Vertex mode: `GOOGLE_APPLICATION_CREDENTIALS` + `GOOGLE_CLOUD_PROJECT`
- Fallback mode: `GOOGLE_API_KEY`
- Runtime switch: `GOOGLE_GENAI_USE_VERTEXAI`

**Operational note**
- This is a mature, first-class integration. It is foundational to the product, not optional.

### Agent2Agent (A2A)

**Primary role**
- Standards-based agent interoperability and agent-card exposure.

**Where it is wired**
- `app/fast_api_app.py` mounts A2A app routes and builds the dynamic agent card.
- The SSE chat entry point lives at `POST /a2a/app/run_sse` in `app/fast_api_app.py`.

**Operational note**
- A2A is active in the runtime architecture and is one of the clearest signals that the product already aims for agentic interoperability.

## Productivity and Workspace Connectors

### Google Workspace APIs

**Services present**
- Google Sheets: `app/integrations/google/sheets.py`
- Google Docs: `app/integrations/google/docs.py`
- Google Forms: `app/integrations/google/forms.py`
- Gmail: `app/integrations/google/gmail.py`
- Google Calendar: `app/integrations/google/calendar.py`
- Shared Google credential helpers: `app/integrations/google/client.py`

**Authentication model**
- OAuth tokens come from Supabase-authenticated Google sessions.
- `provider_token` and `provider_refresh_token` are converted into Google credentials in `app/integrations/google/client.py`.

**Where used**
- Agent tools under `app/agents/tools/google_sheets.py`, `app/agents/tools/gmail.py`, `app/agents/tools/forms.py`, `app/agents/tools/docs.py`, and `app/agents/tools/calendar_tool.py`.
- Reporting agent instructions in `app/agents/reporting/agent.py` explicitly depend on these connectors.

**Operational note**
- This is one of the strongest business-operations integration areas in the codebase. It directly supports non-technical operator workflows.

## Data Platform Integrations

### Supabase

**Primary role**
- Auth, Postgres, storage, persistent sessions, task storage, workflow data, custom skills, onboarding, and more.

**Where it is wired**
- Central client singleton: `app/services/supabase_client.py`
- Auth helpers: `app/app_utils/auth.py`
- Persistent sessions: `app/persistence/supabase_session_service.py`
- Persistent tasks: `app/persistence/supabase_task_store.py`
- Workflow engine and user workflow services: `app/workflows/engine.py`, `app/workflows/user_workflow_service.py`
- Many business services and routers import `supabase.Client` directly, which means Supabase is application-wide infrastructure, not a narrow adapter.

**Storage surfaces detected**
- Knowledge vault access in `app/routers/vault.py`
- User-content setup in `app/services/user_onboarding_service.py`
- Generated media bucket setup in recent storage migrations under `supabase/migrations/`

**Schema breadth**
- Supabase migrations show active investment in:
  - workflow templates and executions
  - marketplace tables
  - knowledge/memory storage
  - reporting and briefing runs
  - storage/RLS hardening

**Operational note**
- Supabase is the single most important non-AI integration in the platform.

### Redis

**Primary role**
- Cache-aside acceleration and resilience buffer.

**Where it is wired**
- `app/services/cache.py`
- Startup prewarm in `app/fast_api_app.py`
- Infra in `docker-compose.yml` and `deployment/terraform/redis.tf`

**Operational note**
- Redis is treated seriously: pooled connections, circuit breaker logic, TTL policies, and health checks are already present.

## Media, Voice, and Content Integrations

### Remotion

**Primary role**
- Programmatic long-form video rendering and richer multi-scene video assembly.

**Where it is wired**
- `app/services/remotion_render_service.py`
- `app/services/director_service.py`
- `app/agents/tools/media.py`
- Frontend playback in `frontend/src/components/widgets/VideoSpecWidget.tsx`

**Runtime dependencies**
- Node.js/npm
- FFmpeg
- the `remotion-render/` workspace

**Operational note**
- This is a real production path, not just a prototype utility.

### Google Cloud Speech and Text-to-Speech

**Primary role**
- Speech fallback and generated voiceovers.

**Where it is wired**
- Speech-to-text: `app/services/speech_to_text_service.py`
- Text-to-speech: `app/services/voiceover_service.py`
- Voice-session bridge: `app/routers/voice_session.py`

**Operational note**
- Voice is more mature than a simple browser mic demo because the backend supports transcription cleanup, live audio, and artifact finalization.

## Optional MCP and Business Connectors

### Tavily and Firecrawl

**Primary role**
- Search and web-scraping support for MCP tools.

**Where it is wired**
- Config surface: `app/mcp/config.py`
- Env examples: `.env.example`, `app/.env.example`

**Operational note**
- These are optional and configuration-driven. They extend research ability but are not required for core product operation.

### SendGrid, HubSpot, Google Stitch

**Primary role**
- Respectively email notifications, CRM integration, and landing-page generation support.

**Where it is wired**
- Config surface only is clearly visible in `app/mcp/config.py`.

**Operational note**
- Current evidence suggests these are planned/optional integrations rather than heavily exercised product paths.

### Stripe

**Primary role**
- Payment links, checkout sessions, and subscription scaffolding.

**Where it is wired**
- `app/mcp/tools/stripe_payments.py`
- configuration references in `app/agents/tools/configuration.py`
- frontend configuration UI references in `frontend/src/app/dashboard/configuration/page.tsx`

**Operational note**
- Stripe is present and useful, but it appears less central and less integrated than Supabase or Google Workspace.

## Social Platform Integrations

### OAuth connection layer

**Platforms detected**
- LinkedIn
- Twitter/X
- Facebook
- Instagram
- YouTube
- TikTok

**Where it is wired**
- OAuth connection management: `app/social/connector.py`
- Publishing abstraction: `app/social/publisher.py`

**Maturity assessment from source**
- Connection setup is real and stores linked accounts in Supabase.
- Publishing support exists, but several branches are clearly partial or simplified:
  - LinkedIn uses a placeholder author URN.
  - TikTok posting assumes a pull-from-URL video path that is not fully assembled there.
  - Instagram and media-upload paths are incomplete or simplified.

**Operational note**
- This is a promising capability area, but today it should be documented as partial integration rather than fully production-hardened omnichannel publishing.

## Frontend Integration Surfaces

### Supabase in the browser

- Frontend auth/session state relies on Supabase via `@supabase/supabase-js`, `@supabase/auth-helpers-nextjs`, and `@supabase/ssr`.
- Protected routes and server/client auth boundaries are enforced in frontend code such as `frontend/src/proxy.ts` and route handlers under `frontend/src/app/api/`.

### Real-time transport

- Chat and workflow progress use SSE from the frontend through `@microsoft/fetch-event-source`.
- Voice uses WebSockets through `frontend/src/hooks/useVoiceSession.ts` and the backend `/ws/voice/{session_id}` endpoint.

## Deployment and Ops Integrations

### Google Cloud Run / Cloud Build / Terraform / GCS / BigQuery / Cloud Logging

**Where it is wired**
- Cloud Build definitions: `.cloudbuild/pr_checks.yaml`, `.cloudbuild/staging.yaml`, `.cloudbuild/deploy-to-prod.yaml`
- Terraform modules: `deployment/terraform/`
- Telemetry infra: `deployment/terraform/telemetry.tf`
- Storage infra: `deployment/terraform/storage.tf`

**Capabilities detected**
- Cloud Run service deployment
- Redis infra provisioning
- secret and IAM management
- logs bucket + telemetry datasets/views
- GitHub-to-Cloud-Build connectivity

**Operational note**
- The project is already set up for enterprise-style cloud operations rather than hobby deployment.

## Internal Service-to-Service Integration

### Protected workflow execution path

- Supabase Edge Functions are expected to call the FastAPI backend using `WORKFLOW_SERVICE_SECRET`.
- The contract is documented in `.env.example`, `app/.env.example`, and `deployment/README.md`.
- `app/routers/workflows.py` contains the service-authenticated workflow step execution path.

**Operational note**
- This is an important architectural seam because it enables background or scheduled workflow execution without exposing privileged workflow actions directly to the browser.

## Health and Observability Surfaces

### Health endpoints

The backend exposes concrete health surfaces referenced in `README.md` and implemented in `app/fast_api_app.py` and related services:

- `/health/live`
- `/health/connections`
- `/health/cache`
- `/health/embeddings`
- `/health/video`
- workflow readiness endpoints in `app/routers/workflows.py`

### Observability stack

- Cloud Trace / OpenTelemetry support is configured for the Google AI stack.
- GCS, BigQuery, and Cloud Logging telemetry infra exists in Terraform and project docs.
- No dedicated Sentry-style error tracking integration was clearly detected in the current source pass.

## Summary by Maturity

### Strong and deeply integrated

- Gemini / Vertex AI
- Google ADK + A2A runtime
- Supabase
- Redis
- Google Workspace APIs
- Remotion and media generation
- Cloud Run / Cloud Build / Terraform deployment stack

### Useful but less central or partially mature

- Voice add-ons around Gemini Live
- Stripe
- Tavily / Firecrawl
- SendGrid / HubSpot / Stitch

### Present but clearly partial

- Social publishing across LinkedIn, TikTok, Instagram, and other platforms
- Some landing-page and MCP business connectors that are configured at the env/config layer more than the end-to-end UX layer

---

*Integration audit refreshed from source files on 2026-03-13.*

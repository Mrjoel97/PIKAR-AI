# Technology Stack

**Analysis Date:** 2026-03-13

## Runtime Snapshot

- Backend language/runtime: Python 3.10-3.13 per `pyproject.toml`, with production images built from `python:3.11-slim` in `Dockerfile`.
- Frontend language/runtime: TypeScript on Next.js 16 + React 19 from `frontend/package.json`.
- Secondary runtime: Node.js/npm inside the backend image for server-side Remotion rendering and inside the frontend app for Next builds.
- Local orchestration: `docker-compose.yml` runs `backend`, optional `frontend`, and `redis`.
- Production target: Google Cloud Run and Google Cloud Build, as declared in `pyproject.toml` and implemented under `deployment/terraform/` and `.cloudbuild/`.

## Core Backend Stack

### API and application shell

- FastAPI is the main HTTP surface in `app/fast_api_app.py`.
- `uvicorn` is the ASGI server in both `docker-compose.yml` and `Dockerfile`.
- `slowapi` and `app/middleware/rate_limiter.py` provide request throttling.
- `app/middleware/security_headers.py` adds browser-facing hardening headers.
- `python-multipart` supports file upload flows used by routers such as `app/routers/files.py`.

### Agent and workflow framework

- Google ADK is the core agent runtime, imported broadly from files such as `app/agent.py`, `app/agents/shared.py`, `app/workflows/dynamic.py`, and `app/workflows/generator.py`.
- `a2a-sdk` underpins the Agent2Agent surface exposed by `app/fast_api_app.py`.
- The main application is a multi-agent executive system, not a single-chat bot:
  - `app/agent.py` wires the executive app and context cache.
  - `app/agents/` contains specialist agents and tool wrappers.
  - `app/workflows/` contains predefined and dynamic workflow engines.
- Dynamic workflow generation is first-class:
  - `app/workflows/generator.py` uses `Gemini` to synthesize workflow JSON.
  - `app/agents/workflow_creator_agent.py` exposes a dedicated workflow-creation agent.
  - `app/routers/workflows.py` exposes `/workflows/generate` plus workflow execution and readiness APIs.

### AI model stack

- `google-genai` is the direct Gemini/Vertex SDK used across the app.
- `google-cloud-aiplatform[evaluation]` is present for Vertex AI and evaluation workflows.
- Model routing is centralized in `app/agents/shared.py`:
  - Primary agent model defaults to Gemini 2.5 Pro.
  - Fallback and fast-path routing default to Gemini 2.5 Flash.
- Voice sessions use Gemini Live in `app/routers/voice_session.py`.
- Telemetry for model calls uses `opentelemetry-instrumentation-google-genai`.

## Data, State, and Persistence Stack

### Supabase-centric persistence

- Supabase is the primary application data platform, used directly throughout:
  - `app/services/supabase_client.py`
  - `app/persistence/supabase_session_service.py`
  - `app/persistence/supabase_task_store.py`
  - `app/workflows/engine.py`
  - many routers/services under `app/services/` and `app/routers/`
- The project uses Supabase for more than auth:
  - relational data in Postgres
  - session persistence
  - task persistence
  - storage buckets
  - workflow metadata
  - user-defined skills/workflows
  - marketplace and memory tables via `supabase/migrations/`
- `asyncpg` is available for direct Postgres access where needed.

### Cache and operational state

- Redis is the cache tier through `app/services/cache.py`.
- The cache layer includes connection pooling and a circuit breaker, which is a meaningful architectural choice rather than a thin key-value wrapper.
- Docker uses `redis:alpine`; production infra is represented in `deployment/terraform/redis.tf`.

### Files and generated artifacts

- Document/file handling uses:
  - `reportlab` for PDF generation
  - `pypdf` for PDF reads
  - `python-docx` for DOCX reads/writes
  - `python-pptx` for report decks
  - `openpyxl` for spreadsheet output
- Knowledge-vault and generated media storage are wired through Supabase storage access in routers and migrations, including `app/routers/vault.py` and recent storage migrations under `supabase/migrations/`.

## Frontend Stack

- Next.js 16.1.4 with the App Router is the frontend platform in `frontend/`.
- React 19.2.3 powers the UI layer.
- TypeScript 5 is used throughout the frontend codebase.
- Tailwind CSS 4 is the styling foundation.
- Frontend auth/data access is Supabase-based:
  - `@supabase/supabase-js`
  - `@supabase/auth-helpers-nextjs`
  - `@supabase/ssr`
- Real-time UX is implemented with:
  - `@microsoft/fetch-event-source` for SSE chat/workflow streams
  - native WebSocket flows for voice sessions in `frontend/src/hooks/useVoiceSession.ts`
- Workflow and generated-media UX rely on:
  - `reactflow` for workflow-like graph experiences
  - `@remotion/player` and `remotion` for browser-side playback/previews
- UI/utility libraries include `framer-motion`, `lucide-react`, `@heroicons/react`, `react-markdown`, `remark-gfm`, and `sonner`.

## Media and Multimodal Stack

- Short-form video generation is routed through Vertex/Gemini video services such as `app/services/vertex_video_service.py`.
- Long-form/programmatic video generation uses Remotion via `app/services/remotion_render_service.py`.
- AI-directed video composition is orchestrated in `app/services/director_service.py`.
- Voice flows combine:
  - Gemini Live in `app/routers/voice_session.py`
  - Google Cloud Speech fallback in `app/services/speech_to_text_service.py`
  - Google Cloud Text-to-Speech in `app/services/voiceover_service.py`
- The backend image explicitly installs `ffmpeg` and Chrome-adjacent libraries in `Dockerfile`, which confirms server-side media rendering is a runtime expectation rather than a stub.

## Tooling, Quality, and Build

### Python quality toolchain

- Dependency/build management: `uv`, `hatchling`, `uv.lock`
- Linting: `ruff`
- Type checking: `ty`
- Spell checking: `codespell`
- Tests: `pytest`, `pytest-asyncio`, `pytest-cov`

### Frontend quality toolchain

- Linting: `eslint`, `eslint-config-next`
- Tests: `vitest`, `@testing-library/react`, `@testing-library/dom`, `jsdom`
- React compiler plugin is enabled through `babel-plugin-react-compiler`

### Build/config entry points

- `pyproject.toml` is the authoritative Python manifest.
- `frontend/package.json` is the authoritative frontend manifest.
- `package.json` at repo root is a thin convenience wrapper around frontend scripts.
- Backend/runtime env validation is implemented in `app/config/validation.py`.
- Runtime env loading currently happens in `app/fast_api_app.py`, while `app/config/settings.py` now re-exports validation helpers rather than owning settings.

## Deployment and Ops Stack

- Cloud Run deployment infrastructure is defined in:
  - `deployment/terraform/service.tf`
  - `deployment/terraform/dev/service.tf`
- CI/CD automation is defined in:
  - `.cloudbuild/pr_checks.yaml`
  - `.cloudbuild/staging.yaml`
  - `.cloudbuild/deploy-to-prod.yaml`
- Supporting infra is represented in Terraform for:
  - Redis
  - storage buckets
  - IAM/service accounts
  - secrets
  - telemetry datasets and views
  - GitHub/Cloud Build connectivity

## Configuration Surface

### Primary config files

- Root runtime example: `.env.example`
- Backend-focused runtime example: `app/.env.example`
- Local container orchestration: `docker-compose.yml`
- Container image definition: `Dockerfile`

### Important config domains

- AI auth and routing:
  - `GOOGLE_API_KEY`
  - `GOOGLE_APPLICATION_CREDENTIALS`
  - `GOOGLE_CLOUD_PROJECT`
  - `GOOGLE_CLOUD_LOCATION`
  - `GEMINI_AGENT_MODEL_PRIMARY`
  - `GEMINI_AGENT_MODEL_FALLBACK`
- Platform/auth:
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `SUPABASE_JWT_SECRET`
- Workflow execution safety:
  - `WORKFLOW_SERVICE_SECRET`
  - `WORKFLOW_STRICT_TOOL_RESOLUTION`
  - `WORKFLOW_STRICT_CRITICAL_TOOL_GUARD`
  - `WORKFLOW_ALLOW_FALLBACK_SIMULATION`
  - `WORKFLOW_ENFORCE_READINESS_GATE`
- Cache/stream guardrails:
  - `REDIS_*`
  - `SSE_MAX_CONNECTIONS_PER_USER`
  - `MAX_UPLOAD_SIZE_BYTES`
- Media/voice:
  - `REMOTION_RENDER_*`
  - `DIRECTOR_*`
  - `GEMINI_LIVE_MODEL`
  - `GEMINI_VOICE_NAME`

## Notable Stack Conclusions

- Pikar-Ai is already architected as an agentic operations platform, not just a chat interface.
- The backend stack is opinionated around Google ADK + Gemini/Vertex + Supabase.
- The workflow layer is substantial and includes both predefined flows and LLM-generated workflow templates.
- The media stack is unusually rich for a business assistant product, with voice, image/video, and report generation all in-repo.
- The current stack has meaningful operational complexity: Cloud Run, Supabase, Redis, SSE, WebSockets, voice, and video rendering are all active concerns.

---

*Stack analysis refreshed from source files on 2026-03-13.*

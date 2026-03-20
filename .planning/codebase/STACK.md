# Technology Stack

**Analysis Date:** 2026-03-20

## Languages

**Primary:**
- Python 3.10+ (target 3.10, Docker image uses 3.11-slim) - Backend, AI agents, API, workflows
- TypeScript 5.9.3 - Frontend application, Supabase edge functions, Remotion video rendering

**Secondary:**
- SQL - Supabase migrations (110 migration files in `supabase/migrations/`)
- HCL (Terraform) - Infrastructure provisioning in `deployment/terraform/`
- Deno (TypeScript) - Supabase Edge Functions runtime in `supabase/functions/`

## Runtime

**Backend:**
- Python 3.11 (Docker: `python:3.11-slim`)
- uvicorn ASGI server (port 8000)
- Full async throughout (asyncpg, aioredis)

**Frontend:**
- Node.js (managed via Vercel for production, local npm for dev)
- Next.js 16.1.4 dev server with Turbopack (port 3000)

**Edge Functions:**
- Deno runtime (Supabase Edge Functions)
- Functions: `execute-workflow`, `send-notification`, `generate-widget`, `cleanup-sessions`, `page-analytics-track`

**Package Managers:**
- uv 0.8.13 (Astral) - Python. Always use `uv run` or `uv sync`, never raw pip
- npm - Frontend and Remotion packages
- Lockfiles: `uv.lock` (Python), `package-lock.json` (frontend, remotion-render)

## Frameworks

**Core:**
- FastAPI ~0.115.8 - Backend REST API and SSE streaming (`app/fast_api_app.py`)
- Google ADK >=1.16.0 - Agent Development Kit for multi-agent orchestration (`app/agent.py`)
- A2A SDK ~0.3.9 - Agent-to-Agent protocol support
- Next.js 16.1.4 - Frontend with App Router (`frontend/src/app/`)
- React 19.2.3 - UI framework with React Compiler enabled

**AI/ML:**
- Google Gemini 2.5 Pro (primary agent model, env: `GEMINI_AGENT_MODEL_PRIMARY`)
- Google Gemini 2.5 Flash (fallback model, env: `GEMINI_AGENT_MODEL_FALLBACK`)
- Vertex AI Imagen 4.0 (image generation via `app/services/vertex_image_service.py`)
- Vertex AI Veo 3.1 (video generation via `app/services/vertex_video_service.py`)
- Google GenAI text-embedding-004 (vector embeddings via `app/rag/embedding_service.py`)

**Testing:**
- pytest >=8.3.4 + pytest-asyncio >=0.23.8 - Backend tests
- pytest-cov >=5.0.0 - Coverage
- Vitest >=4.0.18 - Frontend tests
- Testing Library (React) >=16.3.2 - React component testing
- jsdom >=27.4.0 - DOM environment for frontend tests

**Build/Dev:**
- Turbopack - Next.js dev bundler (configured in `frontend/next.config.ts`)
- React Compiler (babel-plugin-react-compiler 1.0.0) - Automatic memoization
- Ruff >=0.4.6 - Python linting and formatting
- ty >=0.0.1a0 - Astral's Rust-based Python type checker
- codespell >=2.2.0 - Spell checking
- ESLint 9 + eslint-config-next 16.1.4 - Frontend linting
- Docker + Docker Compose - Containerized development
- Terraform - Infrastructure as code (`deployment/terraform/`)
- Remotion 4.0.421 + @remotion/cli - Server-side video rendering (`remotion-render/`)

**Middleware:**
- slowapi >=0.1.9 - Rate limiting with persona-based tiers (`app/middleware/rate_limiter.py`)
- Custom SecurityHeadersMiddleware (`app/middleware/security_headers.py`)
- Custom OnboardingGuardMiddleware (`app/middleware/onboarding_guard.py`)
- Custom RequestLoggingMiddleware (inline in `app/fast_api_app.py`)
- CORSMiddleware (Starlette) - Cross-origin request handling

## Key Dependencies

**Critical (Backend):**
- `google-adk>=1.16.0` - Core agent orchestration framework
- `a2a-sdk~=0.3.9` - Agent-to-Agent protocol
- `google-genai>=0.2.0` - Gemini model API client
- `google-cloud-aiplatform[evaluation]>=1.118.0` - Vertex AI (images, video, embeddings)
- `supabase>=2.27.2` - Database client (PostgreSQL via PostgREST)
- `redis>=5.0.0` - Async Redis caching with circuit breaker
- `fastapi~=0.115.8` - Web framework
- `uvicorn~=0.34.0` - ASGI server
- `asyncpg>=0.30.0` - Async PostgreSQL driver

**Critical (Frontend):**
- `next@16.1.4` - App framework
- `react@19.2.3` / `react-dom@19.2.3` - UI framework
- `@supabase/supabase-js@^2.91.1` - Supabase client
- `@supabase/ssr@^0.8.0` - Supabase SSR helpers
- `@supabase/auth-helpers-nextjs@^0.15.0` - Auth integration
- `@microsoft/fetch-event-source@^2.0.1` - SSE client for chat streaming

**Infrastructure:**
- `stripe>=7.0.0` - Payment processing
- `google-api-python-client>=2.187.0` - Google Workspace APIs (Gmail, Calendar, Sheets, Docs)
- `google-auth>=2.45.0` - Google OAuth
- `google-cloud-logging>=3.12.0` - Cloud Logging
- `google-cloud-speech>=2.33.0` - Speech-to-Text
- `google-cloud-texttospeech>=2.33.0` - Text-to-Speech voiceover
- `gcsfs>=2024.11.0` - Google Cloud Storage access
- `opentelemetry-instrumentation-google-genai>=0.1.0` - GenAI telemetry
- `PyJWT>=2.8.0` - JWT token verification
- `cryptography>=46.0.3` - Cryptographic operations
- `pydantic-settings>=2.0.0` - Settings management
- `httpx` - Async HTTP client (used throughout for external API calls)

**Document Generation:**
- `reportlab>=4.4.9` - PDF generation
- `pypdf>=6.6.2` - PDF reading
- `python-docx>=1.1.0` - Word document generation
- `python-pptx>=1.0.2` - PowerPoint generation
- `openpyxl>=3.1.0` - Excel file handling
- `jspdf@^4.1.0` - Client-side PDF generation (frontend)

**UI/Frontend:**
- `framer-motion@^12.29.0` - Animations
- `lucide-react@^0.563.0` - Icons (tree-shaken via modularizeImports)
- `@heroicons/react@^2.2.0` - Additional icons
- `reactflow@^11.11.4` - Flow/graph visualization
- `react-markdown@^10.1.0` + `remark-gfm@^4.0.1` - Markdown rendering
- `sonner@^2.0.7` - Toast notifications
- `@remotion/player@^4.0.421` + `remotion@^4.0.421` - Video player
- `@tailwindcss/postcss@^4` + `tailwindcss@^4` - Styling

## Configuration

**Environment:**
- `.env` file at project root (loaded via `python-dotenv` in `app/fast_api_app.py`)
- `.env.example` exists for reference (do not read actual `.env` contents)
- Environment detection: `ENVIRONMENT` or `ENV` var (development/staging/production/test)
- Startup validation in `app/config/validation.py` (fail-fast in production)

**Critical env vars (required in all environments):**
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` - Backend service key
- `SUPABASE_ANON_KEY` - Client-side key

**AI Configuration (one required):**
- `GOOGLE_APPLICATION_CREDENTIALS` + `GOOGLE_CLOUD_PROJECT` (Vertex AI mode)
- `GOOGLE_API_KEY` (Gemini API key mode, local dev fallback)

**Production-only required:**
- `SUPABASE_JWT_SECRET` - JWT verification (min 32 chars)
- `WORKFLOW_SERVICE_SECRET` - Service-to-service auth (min 32 chars)
- `SCHEDULER_SECRET` - Cloud Scheduler auth
- `APP_URL`, `ALLOWED_ORIGINS`, `BACKEND_API_URL`
- Workflow flags: `WORKFLOW_STRICT_TOOL_RESOLUTION=true`, `WORKFLOW_STRICT_CRITICAL_TOOL_GUARD=true`, `WORKFLOW_ALLOW_FALLBACK_SIMULATION=false`, `WORKFLOW_ENFORCE_READINESS_GATE=true`

**Build Configuration:**
- `pyproject.toml` - Python project config, Ruff, ty, pytest, hatch build
- `frontend/next.config.ts` - Next.js config (Turbopack, React Compiler, image optimization)
- `frontend/tsconfig.json` - TypeScript config (strict mode, path alias `@/*` -> `./src/*`)
- `vercel.json` - Vercel deployment (rewrites `/api/backend/*` to backend URL)
- `Dockerfile` - Backend container (Python 3.11 + Node.js for Remotion)
- `docker-compose.yml` - Local dev (backend + Redis; frontend optional profile)

## Platform Requirements

**Development:**
- Python 3.10+ with uv package manager
- Node.js + npm (for frontend and Remotion)
- Docker + Docker Compose (for backend + Redis)
- Supabase CLI (for local DB, migrations, edge functions)
- ffmpeg (for video rendering, included in Docker image)

**Production:**
- Backend: Google Cloud Run (us-central1, 4Gi memory, no CPU throttling)
- Frontend: Vercel (Next.js deployment)
- Database: Supabase (hosted PostgreSQL)
- Cache: Google Cloud Memorystore for Redis (REDIS_7_0, 1GB BASIC tier)
- Storage: Google Cloud Storage (artifact bucket, telemetry logs)
- CI/CD: Google Cloud Build (Terraform-managed)
- Container Registry: Google Artifact Registry
- Telemetry: BigQuery dataset for GenAI telemetry data
- Networking: VPC Access Connector for Cloud Run to Redis

---

*Stack analysis: 2026-03-20*

# Technology Stack

**Analysis Date:** 2026-03-04

## Languages

**Primary:**
- Python 3.10-3.13 runtime target (`requires-python = ">=3.10,<3.14"` in `pyproject.toml`) for backend services, agents, workflows, and API
- TypeScript for frontend app/router code and Supabase Edge Functions (`frontend/src/`, `supabase/functions/`)

**Secondary:**
- SQL for Supabase schema and migrations (`supabase/migrations/*.sql`)
- YAML for workflow definitions (`app/workflows/definitions/*.yaml`)
- Markdown for operational and planning docs (`README.md`, `AGENTS.md`, `.planning/`)

## Runtime

**Environment:**
- Backend container: Python 3.11 slim (`Dockerfile`)
- ASGI server: Uvicorn (`app.fast_api_app:app`)
- Frontend runtime: Next.js 16 / React 19 (`frontend/package.json`)
- Edge runtime: Deno for Supabase Functions (`supabase/functions/*/deno.json`)

**Package Manager:**
- Python: `uv` with lockfile (`uv.lock`)
- Node: `npm` with lockfiles (`frontend/package-lock.json`, `remotion-render/package-lock.json`)
- Lockfile coverage: Python + frontend + remotion render present

## Frameworks

**Core:**
- Google ADK (`google-adk>=1.16.0`) for multi-agent orchestration (`app/agent.py`, `app/agents/*`)
- A2A SDK (`a2a-sdk~=0.3.9`) for agent protocol routes (`app/fast_api_app.py`)
- FastAPI (`fastapi~=0.115.8`) for HTTP/SSE APIs (`app/fast_api_app.py`, `app/routers/*`)
- Next.js (`next@16.1.4`) for web UI (`frontend/src/app/*`)

**Testing:**
- Pytest + pytest-asyncio for backend tests (`tests/unit`, `tests/integration`)
- Vitest + Testing Library + jsdom for frontend tests (`frontend/vitest.config.mts`, `frontend/src/**/*.test.tsx`)

**Build/Dev:**
- Docker + Docker Compose (`Dockerfile`, `docker-compose.yml`)
- Terraform for environment provisioning (`deployment/terraform/`)
- Cloud Build and GitHub Actions for CI/CD (`.cloudbuild/*.yaml`, `.github/workflows/ci.yml`)

## Key Dependencies

**Critical:**
- `google-adk` - agent runtime, orchestration, sub-agent delegation
- `google-genai` / Vertex AI libs - Gemini/Veo model access (`app/agents/shared.py`, `app/services/vertex_video_service.py`)
- `supabase` + `asyncpg` - persistence, session/event storage, app data access (`app/services/supabase_client.py`, `app/persistence/`)
- `redis` - cache layer and circuit breaker (`app/services/cache.py`)
- `stripe` - payments and revenue ingestion (`app/services/stripe_revenue_service.py`, `app/routers/webhooks.py`)

**Infrastructure:**
- `uvicorn` - API serving
- `slowapi` - request throttling (`app/middleware/rate_limiter.py`)
- `@supabase/supabase-js` + `@supabase/ssr` - frontend auth/session data access (`frontend/src/lib/supabase/*`)
- `remotion` + `@remotion/player` - video render pipeline (`frontend/package.json`, `remotion-render/`)

## Configuration

**Environment:**
- Root environment template (`.env.example`) + app-specific template (`app/.env.example`)
- Core required variables for production paths: Supabase, Google AI credentials, workflow service secret, Redis host/port
- Runtime controls include strict auth and workflow readiness/guard flags (`app/app_utils/auth.py`, `app/workflows/engine.py`)

**Build:**
- Backend: `pyproject.toml`, `uv.lock`, `Dockerfile`
- Frontend: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/next.config.ts`
- Quality tooling: Ruff/Ty/Codespell in `pyproject.toml`, hook orchestration in `.pre-commit-config.yaml`

## Platform Requirements

**Development:**
- Python + `uv` for backend iteration
- Node.js + npm for frontend and Remotion package workflows
- Optional local infra: Docker (backend/redis), local Supabase CLI for edge function testing

**Production:**
- Cloud Run deployment target (`Makefile` deploy target)
- Supabase project (Postgres/Auth/Functions/Storage)
- Redis service (local or managed) for cache-aside behavior
- Google Cloud project with Vertex AI enabled for primary model/video generation paths

---

*Stack analysis: 2026-03-04*
*Update after major dependency changes*

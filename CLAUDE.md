# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pikar-AI is a multi-agent AI executive system built on Google's Agent Development Kit (ADK) with A2A Protocol support. It orchestrates 10 specialized AI agents (financial, content, strategic, sales, marketing, operations, HR, compliance, customer support, data) through a central ExecutiveAgent to handle business operations.

**Stack:** Python 3.10+ (FastAPI backend), TypeScript/React 19 (Next.js frontend), Supabase (PostgreSQL), Redis caching, Google ADK + Gemini models, deployed to Google Cloud Run.

## Common Commands

```bash
make install          # Install Python deps with uv
make local-backend    # FastAPI dev server with hot-reload (port 8000)
make playground       # ADK web playground (port 8501, select 'app' folder)
make test             # Run unit + integration tests and workflow validation
make lint             # codespell, ruff check, ruff format, ty check, workflow validation
make deploy           # Deploy to Cloud Run

# Docker (backend + Redis, frontend runs natively for better HMR on Windows)
docker compose up             # backend + redis only (frontend in "frontend" profile)
cd frontend && npm run dev    # native frontend dev server

# Running a single test
uv run pytest tests/unit/path/to/test.py -k "test_name"

# Linting subset
uv run ruff check app/ --fix   # lint with autofix
uv run ruff format app/        # format
uv run ty check .              # type checking

# Database migrations (Supabase CLI)
supabase start            # start the local Supabase stack
supabase db push --local  # apply SQL migrations from supabase/migrations
supabase db reset --local # rebuild local DB from migrations + seed
```

## Architecture

### Agent Hierarchy
- **ExecutiveAgent** (`app/agent.py`) — Main orchestrator, routes to specialized sub-agents, manages context caching
- **10 Specialized Agents** (`app/agents/<domain>/agent.py`) — Each has its own tools and instructions. Factory functions (e.g. `create_financial_agent()`) support workflow pipelines. Re-exported via `app/agents/specialized_agents.py` for backward compat.
- **Shared config** in `app/agents/shared.py` (model configs, retry options) and `app/agents/shared_instructions.py`

### Backend (`app/`)
- `fast_api_app.py` — FastAPI entry point, A2A protocol endpoints, SSE streaming at `POST /a2a/app/run_sse`
- `agents/tools/` — 20+ tool modules (calendar, docs, gmail, sheets, media, workflows, brain_dump, deep_research, etc.)
- `services/` — Business logic (cache with circuit breaker, workflows, campaigns, tasks, analytics, director/video)
- `workflows/` — Workflow engine (`engine.py`), adaptive generator, execution contracts with trust classification
- `mcp/` — Model Context Protocol integrations (Canva, Stripe, web search/scrape)
- `routers/` — API route handlers (approvals, initiatives, workflows, departments, briefing)
- `config/settings.py` — Pydantic BaseSettings configuration
- `supabase/migrations/` — canonical SQL migration chain for schema and seed changes

### Frontend (`frontend/`)
- Next.js 16 with App Router, React 19, Tailwind CSS 4
- Persona-based layouts in `src/app/(personas)/`
- SSE chat streaming, OAuth integration, approval workflows UI
- Remotion video player integration

### Key Patterns
- **Circuit breaker on Redis** — graceful degradation to direct DB queries when Redis is unavailable (`app/services/cache.py`)
- **Model fallback** — Primary Gemini 2.5 Pro falls back to Gemini 2.5 Flash
- **Retry strategy** — 5 attempts, exponential backoff (2s initial, 2x multiplier, 60s max)
- **Context caching** — Vertex AI context cache for token efficiency (configurable via `ENABLE_CONTEXT_CACHE`)
- **Async throughout** — Full async Python with asyncpg, aioredis

### Health Endpoints
- `/health/live` — Liveness (no deps)
- `/health/connections` — Supabase + cache
- `/health/cache` — Redis + circuit breaker status
- `/health/embeddings` — Gemini embedding availability
- `/health/video` — Video generation config

## Code Quality

- **Linter:** Ruff (rules: E, W, F, I, N, D, UP, B, C4, SIM, ARG, PIE, PERF, RUF)
- **Type checker:** ty (also mypy via pre-commit)
- **Pre-commit hooks:** no bare except, no print statements in production code, no mutable default arguments, bandit security scanning, interrogate docstring coverage (80%+)
- **Package manager:** uv (Astral) — always use `uv run` or `uv sync`, never raw pip

## Environment

Key env vars (see `.env.example`): `GOOGLE_API_KEY` (dev) or `GOOGLE_APPLICATION_CREDENTIALS` + `GOOGLE_CLOUD_PROJECT` (prod), `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `REDIS_HOST`/`REDIS_PORT`, `WORKFLOW_SERVICE_SECRET`.


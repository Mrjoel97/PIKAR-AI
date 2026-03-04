# Codebase Structure

**Analysis Date:** 2026-03-04

## Directory Layout

```
Pikar-Ai/
├── app/                    # Backend API, agent system, workflow engine, services
├── frontend/               # Next.js web app and UI tests
├── supabase/               # SQL migrations and edge functions
├── tests/                  # Python unit/integration/eval/load tests
├── scripts/                # Verification, rollout, seeding, and utility scripts
├── deployment/             # Terraform and deployment docs
├── docs/                   # Product/architecture/rollout documentation
├── remotion-render/        # Server-side Remotion video rendering package
├── .cloudbuild/            # Cloud Build pipeline definitions
├── .github/                # GitHub Actions workflows
├── .planning/              # Planning and generated codebase map docs
├── pyproject.toml          # Python project config/dependencies/tooling
├── uv.lock                 # Python dependency lockfile
├── Makefile                # Canonical local commands
└── docker-compose.yml      # Local backend/frontend/redis orchestration
```

## Directory Purposes

**app/**
- Purpose: Backend application source
- Contains: agents, routers, services, persistence, middleware, workflows, MCP tools
- Key files: `app/fast_api_app.py`, `app/agent.py`, `app/agents/specialized_agents.py`
- Subdirectories: `agents/`, `routers/`, `services/`, `workflows/`, `mcp/`, `persistence/`, `rag/`

**frontend/**
- Purpose: Next.js frontend and client API layer
- Contains: App Router pages, components, hooks, context providers, vitest tests
- Key files: `frontend/src/app/layout.tsx`, `frontend/src/services/api.ts`, `frontend/vitest.config.mts`
- Subdirectories: `src/app/`, `src/components/`, `src/hooks/`, `src/lib/supabase/`, `src/services/`

**supabase/**
- Purpose: Database and edge compute boundary
- Contains: ordered SQL migrations, edge functions, shared function helpers
- Key files: `supabase/migrations/*.sql`, `supabase/functions/execute-workflow/index.ts`
- Subdirectories: `migrations/`, `functions/`

**tests/**
- Purpose: Backend verification and evaluation assets
- Contains: `unit/`, `integration/`, `eval_datasets/`, `load_test/`, golden fixtures
- Key files: `tests/unit/conftest.py`, `tests/integration/test_server_e2e.py`
- Subdirectories: `unit/`, `integration/`, `eval_datasets/`, `load_test/`

**scripts/**
- Purpose: operational scripts for verification, rollout, seeding, and debugging
- Contains: python helper scripts grouped by domain folders
- Key files: `scripts/verify/validate_workflow_templates.py`

## Key File Locations

**Entry Points:**
- `app/fast_api_app.py`: FastAPI startup, middleware, router registration, ADK runner wiring
- `app/agent.py`: Executive agent graph and ADK app object
- `frontend/src/app/page.tsx`: frontend root landing route
- `supabase/functions/execute-workflow/index.ts`: edge workflow execution entry

**Configuration:**
- `pyproject.toml`: Python deps + Ruff/Ty/Pytest settings
- `.env.example` and `app/.env.example`: env contracts
- `frontend/package.json`: frontend deps/scripts
- `docker-compose.yml`: local container topology
- `.pre-commit-config.yaml`: commit-time quality/security hooks

**Core Logic:**
- `app/agents/*`: domain-specific agent definitions and tools
- `app/routers/*`: API route modules
- `app/services/*`: business logic and integration clients
- `app/workflows/*`: workflow lifecycle and template execution

**Testing:**
- `tests/unit/*`: backend unit tests
- `tests/integration/*`: backend integration tests
- `frontend/src/**/*.test.tsx`: frontend component/service tests
- `frontend/__tests__/*`: additional frontend test suites

**Documentation:**
- `README.md`: top-level usage and architecture summary
- `AGENTS.md`: contributor/agent workflow guidance
- `docs/*`: product and rollout documentation

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (example: `financial_service.py`)
- Python tests: `test_*.py` (example: `test_financial_service.py`)
- React components: `PascalCase.tsx` (example: `ChatInterface.tsx`)
- Frontend tests: `*.test.ts` / `*.test.tsx`
- SQL migrations: numeric prefix + description (example: `0058_journey_readiness_view.sql`)

**Directories:**
- Backend domain folders are mostly lowercase and domain-named (`agents`, `routers`, `services`)
- Frontend feature folders follow App Router route hierarchy in `src/app/`

**Special Patterns:**
- Agent modules export singleton and factory constructors (`agent.py` + `create_*_agent`)
- Tool modules expose grouped tool lists (`*_TOOLS`)
- Workflow templates stored as YAML in `app/workflows/definitions/`

## Where to Add New Code

**New Backend Feature:**
- API contract: `app/routers/<feature>.py`
- Domain logic: `app/services/<feature>_service.py`
- Agent tools (if needed): `app/agents/tools/<feature>.py`
- Tests: `tests/unit/test_<feature>.py` + targeted integration tests in `tests/integration/`

**New Agent Capability:**
- Domain tool implementation: `app/agents/<domain>/tools.py` or `app/agents/tools/<tool>.py`
- Registration: agent-local tool list + executive merge in `app/agent.py`
- Tests: add/update unit tests under `tests/unit/`

**New Frontend Feature:**
- Page route: `frontend/src/app/<route>/page.tsx`
- Shared UI: `frontend/src/components/<area>/`
- Client integration: `frontend/src/services/<feature>.ts`
- Tests: collocated `*.test.tsx` or `frontend/__tests__/`

**New Workflow Template:**
- Template YAML: `app/workflows/definitions/<template>.yaml`
- Validation baseline: run workflow verify scripts and add integration tests where relevant

## Special Directories

**.planning/**
- Purpose: planning artifacts and generated codebase docs
- Source: GSD workflows and manual planning updates
- Committed: typically yes (project process artifacts)

**remotion-render/**
- Purpose: Node/Remotion render package invoked by backend services
- Source: maintained subproject in same repo
- Committed: yes

**Transient/local-only folders:**
- Examples: `.venv/`, `.tmp/`, `.pytest_cache/`, `frontend/.next/`, `htmlcov/`
- Purpose: local development/test artifacts
- Committed: no (gitignored)

---

*Structure analysis: 2026-03-04*
*Update when directory structure changes*

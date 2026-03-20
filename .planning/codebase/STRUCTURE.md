# Codebase Structure

**Analysis Date:** 2026-03-20

## Directory Layout

```
pikar-ai/
├── app/                        # Python backend (FastAPI + ADK agents)
│   ├── agent.py                # ExecutiveAgent definition, ADK App creation
│   ├── fast_api_app.py         # FastAPI entry point, SSE, A2A, middleware, health
│   ├── exceptions.py           # Custom exception hierarchy (PikarError + subtypes)
│   ├── sse_utils.py            # SSE event post-processing (widget/trace extraction)
│   ├── a2a/                    # A2A Protocol client/registry
│   ├── agents/                 # Agent definitions and tools
│   │   ├── base_agent.py       # PikarAgent (ADK Agent subclass)
│   │   ├── shared.py           # Model configs, retry options, content config profiles
│   │   ├── shared_instructions.py  # Reusable instruction blocks for all agents
│   │   ├── specialized_agents.py   # Re-export layer for all 10 agents
│   │   ├── context_extractor.py    # ADK callbacks for context memory/personalization
│   │   ├── schemas.py          # Pydantic schemas for structured agent output
│   │   ├── enhanced_tools.py   # Legacy tool wrappers
│   │   ├── financial/          # Financial Agent (agent.py, tools.py)
│   │   ├── content/            # Content Agent
│   │   ├── strategic/          # Strategic Agent
│   │   ├── sales/              # Sales Agent
│   │   ├── marketing/          # Marketing Agent
│   │   ├── operations/         # Operations Agent
│   │   ├── hr/                 # HR Agent
│   │   ├── compliance/         # Compliance Agent
│   │   ├── customer_support/   # Customer Support Agent
│   │   ├── data/               # Data Agent
│   │   ├── reporting/          # Reporting Agent
│   │   └── tools/              # 45+ tool modules shared across agents
│   ├── app_utils/              # Auth, telemetry, typing helpers
│   ├── autonomy/               # Autonomous agent kernel
│   ├── commerce/               # Commerce services (inventory, invoicing)
│   ├── config/                 # Settings, env validation, OpenAPI config
│   ├── integrations/           # External service integrations
│   │   └── google/             # Google Workspace (Calendar, Docs, Forms, Gmail, Sheets)
│   ├── mcp/                    # Model Context Protocol layer
│   │   ├── tools/              # MCP tool implementations (Stripe, Canva, web, SEO, social)
│   │   ├── integrations/       # MCP integration services (CRM, email)
│   │   └── security/           # PII filter, audit logger, external call guard
│   ├── middleware/             # Rate limiter, security headers, onboarding guard
│   ├── models/                 # Pydantic data models (profile, user, widgets)
│   ├── notifications/          # Notification service
│   ├── orchestration/          # Knowledge injection tools
│   ├── persistence/            # ADK session/task storage (Supabase-backed)
│   ├── personas/               # Persona system (models, policy registry, runtime, prompts)
│   ├── prompts/                # External prompt templates (executive_instruction.txt)
│   ├── rag/                    # Knowledge Vault (embeddings, ingestion, search)
│   ├── routers/                # FastAPI route handlers (24 router modules)
│   ├── services/               # Business logic services (55+ modules)
│   ├── skills/                 # Skills system (library, registry, loader, creator, validation)
│   ├── social/                 # Social media (analytics, connector, publisher, webhooks)
│   └── workflows/              # Workflow engine, executor, contracts, templates
├── frontend/                   # Next.js frontend application
│   ├── src/
│   │   ├── app/                # App Router pages and layouts
│   │   │   ├── layout.tsx      # Root layout (PersonaProvider, ChatSessionProvider)
│   │   │   ├── page.tsx        # Landing page
│   │   │   ├── (personas)/     # Persona-based route group
│   │   │   │   ├── solopreneur/
│   │   │   │   ├── startup/
│   │   │   │   ├── sme/
│   │   │   │   └── enterprise/
│   │   │   ├── api/            # Next.js API routes (configuration, vault, waitlist, webhooks)
│   │   │   ├── approval/       # Approval flow pages
│   │   │   ├── auth/           # Auth pages (callback)
│   │   │   ├── dashboard/      # Dashboard page
│   │   │   ├── departments/    # Department pages
│   │   │   ├── onboarding/     # Onboarding flow
│   │   │   ├── org-chart/      # Org chart page
│   │   │   ├── settings/       # Settings pages
│   │   │   └── components/     # Page-level shared components
│   │   ├── components/         # Reusable React components
│   │   │   ├── auth/           # Auth components
│   │   │   ├── braindump/      # Voice braindump components
│   │   │   ├── chat/           # Chat UI components
│   │   │   ├── dashboard/      # Dashboard widgets
│   │   │   ├── knowledge-vault/ # Knowledge Vault UI
│   │   │   ├── layout/         # Layout components (sidebar, header)
│   │   │   ├── org-chart/      # Org chart components
│   │   │   ├── personas/       # Persona selection components
│   │   │   ├── reports/        # Report viewer components
│   │   │   ├── skills/         # Skill browser components
│   │   │   ├── ui/             # Shared UI primitives
│   │   │   ├── vault/          # Vault components
│   │   │   ├── widgets/        # Widget renderer components (WidgetRegistry)
│   │   │   ├── workflow-builder/ # Visual workflow builder
│   │   │   └── workflows/      # Workflow list/detail components
│   │   ├── contexts/           # React contexts
│   │   │   ├── ChatSessionContext.tsx
│   │   │   ├── NotificationContext.tsx
│   │   │   └── PersonaContext.tsx
│   │   ├── hooks/              # Custom React hooks
│   │   │   ├── useAgentChat.ts         # SSE chat hook (primary)
│   │   │   ├── useVoiceSession.ts      # Voice session hook
│   │   │   ├── useSpeechRecognition.ts # Speech recognition
│   │   │   ├── useFileUpload.ts        # File upload
│   │   │   ├── usePendingApprovals.ts  # Approval polling
│   │   │   ├── usePresence.ts          # Realtime presence
│   │   │   ├── useRealtimeNotifications.ts
│   │   │   ├── useRealtimeSession.ts
│   │   │   ├── useRealtimeWorkflow.ts
│   │   │   ├── useSessionHistory.ts
│   │   │   ├── useSwipeGesture.ts
│   │   │   └── useTextToSpeech.ts
│   │   ├── lib/                # Utility libraries
│   │   │   ├── chatMetadata.ts # Chat metadata extraction
│   │   │   └── supabase/       # Supabase client config
│   │   ├── services/           # Frontend service modules
│   │   │   ├── api.ts          # HTTP client (fetchWithAuth, retry, timeout)
│   │   │   ├── widgetDisplay.ts # Widget rendering service
│   │   │   ├── workflows.ts    # Workflow API client
│   │   │   ├── initiatives.ts  # Initiative API client
│   │   │   ├── onboarding.ts   # Onboarding API client
│   │   │   ├── briefing.ts     # Daily briefing API client
│   │   │   └── [12 more domain services]
│   │   ├── types/              # TypeScript type definitions
│   │   │   └── widgets.ts      # Widget type system
│   │   └── data/               # Static data files
│   ├── __tests__/              # Test files (components, hooks, pages)
│   ├── public/                 # Static assets
│   ├── package.json
│   ├── tsconfig.json
│   └── next.config.ts
├── supabase/                   # Supabase project config
│   ├── migrations/             # 60+ SQL migration files (schema + seeds)
│   └── functions/              # Supabase Edge Functions (Deno)
│       ├── execute-workflow/   # Workflow execution via edge
│       ├── send-notification/  # Push notification delivery
│       ├── generate-widget/    # Server-side widget generation
│       ├── cleanup-sessions/   # Session garbage collection
│       ├── page-analytics-track/ # Page view tracking
│       └── _shared/            # Shared utilities for edge functions
├── remotion-render/            # Remotion video rendering service
│   └── src/                    # Video composition source
├── tests/                      # Python test suite
│   ├── unit/                   # Unit tests
│   │   └── app/                # Mirror of app/ structure
│   ├── integration/            # Integration tests
│   ├── eval_datasets/          # Agent evaluation datasets
│   ├── load_test/              # Load testing scripts
│   └── skills/                 # Skill-specific tests
├── scripts/                    # Utility scripts
│   ├── audit/                  # Audit scripts
│   ├── debug/                  # Debug utilities
│   ├── dev/                    # Dev helper scripts
│   ├── rollout/                # Deployment rollout scripts
│   ├── seed/                   # Database seeding scripts
│   └── verify/                 # Verification scripts
├── deployment/                 # Infrastructure-as-code
│   └── terraform/              # Terraform configs (dev, vars, SQL)
├── docs/                       # Documentation
│   ├── product/                # Product specs, standards, code style guides
│   │   ├── tracks/             # Development track archives
│   │   └── standards/          # Engineering standards
│   ├── rollout/                # Rollout documentation
│   └── superpowers/            # Superpower feature docs
├── skills/                     # Claude Code skills (project-specific)
│   ├── google-cloud-run-ops/   # Cloud Run operations skill
│   ├── marketing/              # Marketing skill with evals
│   └── ship-it/                # Ship-it deployment skill
├── .planning/                  # Planning documents
│   ├── codebase/               # Codebase analysis (this file)
│   ├── phases/                 # Implementation phase plans
│   └── milestones/             # Milestone tracking
├── docker-compose.yml          # Docker orchestration (backend + Redis)
├── Dockerfile                  # Backend container image
├── Makefile                    # Project commands (install, test, lint, deploy)
├── pyproject.toml              # Python project config (uv)
└── CLAUDE.md                   # Claude Code project instructions
```

## Directory Purposes

**`app/agents/`:**
- Purpose: All AI agent definitions and their associated tools
- Contains: 10 domain agent packages (each with `agent.py`), shared config, 45+ tool modules
- Key files: `app/agents/shared.py` (model configs), `app/agents/specialized_agents.py` (re-export layer), `app/agents/tools/registry.py` (tool registry)

**`app/agents/tools/`:**
- Purpose: Tool functions callable by agents during LLM inference
- Contains: Calendar, docs, forms, Gmail, sheets, media, brain dump, deep research, UI widgets, workflows, skills, notifications, configuration, social, SEO tools
- Key files: `app/agents/tools/ui_widgets.py` (agent-to-UI widgets), `app/agents/tools/registry.py` (central tool registry), `app/agents/tools/base.py` (sanitize_tools utility)

**`app/routers/`:**
- Purpose: FastAPI route handlers organized by domain
- Contains: 24 router modules
- Key files: `app/routers/workflows.py` (45k lines, largest router), `app/routers/voice_session.py` (39k lines), `app/routers/initiatives.py`, `app/routers/files.py`

**`app/services/`:**
- Purpose: Business logic and external service integrations
- Contains: 55+ service modules
- Key files: `app/services/cache.py` (Redis + circuit breaker), `app/services/department_runner.py` (41k lines), `app/services/director_service.py` (video direction), `app/services/self_improvement_engine.py` (42k lines)

**`app/workflows/`:**
- Purpose: Structured workflow engine with phases, steps, approval gates
- Contains: Engine, step executor, worker, contract defaults, trust classification, template definitions
- Key files: `app/workflows/engine.py` (52k lines, core engine), `app/workflows/step_executor.py`, `app/workflows/worker.py`

**`app/skills/`:**
- Purpose: Agent skill library and management
- Contains: Built-in professional skill libraries (450k+ lines across 4 modules), registry, loader, creator, custom skills service
- Key files: `app/skills/library.py` (core skills), `app/skills/professional_*.py` (domain-specific professional skills), `app/skills/registry.py` (skill lookup)

**`app/mcp/`:**
- Purpose: Model Context Protocol tool implementations for external services
- Contains: Tool connectors, security layer, integration services
- Key files: `app/mcp/tools/stripe_payments.py`, `app/mcp/tools/canva_media.py`, `app/mcp/tools/stitch.py`, `app/mcp/security/external_call_guard.py`

**`app/persistence/`:**
- Purpose: ADK runtime persistence (sessions + tasks)
- Contains: Supabase-backed implementations of ADK interfaces
- Key files: `app/persistence/supabase_session_service.py` (33k lines, session CRUD), `app/persistence/supabase_task_store.py`

**`frontend/src/hooks/`:**
- Purpose: Custom React hooks for agent chat, voice, realtime, file upload
- Key files: `frontend/src/hooks/useAgentChat.ts` (29k lines, SSE chat), `frontend/src/hooks/useVoiceSession.ts` (27k lines)

**`frontend/src/services/`:**
- Purpose: Frontend API client modules organized by domain
- Key files: `frontend/src/services/api.ts` (core HTTP client with auth + retry), `frontend/src/services/widgetDisplay.ts` (23k lines, widget rendering), `frontend/src/services/workflows.ts` (18k lines)

**`supabase/migrations/`:**
- Purpose: Canonical SQL migration chain for all schema changes
- Contains: 60+ migrations from `0001_initial_schema.sql` to latest
- Pattern: Numbered migrations (legacy: `0001_*` format, current: `YYYYMMDDHHMMSS_*` format)

## Key File Locations

**Entry Points:**
- `app/fast_api_app.py`: FastAPI application entry point
- `app/agent.py`: ADK App and ExecutiveAgent definition
- `frontend/src/app/layout.tsx`: Next.js root layout
- `frontend/src/app/page.tsx`: Landing page

**Configuration:**
- `app/config/settings.py`: Pydantic BaseSettings (re-exports from validation)
- `app/config/validation.py`: Environment validation at startup
- `app/agents/shared.py`: Agent model configs and retry options
- `frontend/next.config.ts`: Next.js configuration
- `docker-compose.yml`: Docker orchestration
- `Makefile`: Build/dev/deploy commands
- `pyproject.toml`: Python project + dependency config

**Core Logic:**
- `app/agent.py`: Executive agent composition and tool registration
- `app/agents/specialized_agents.py`: All 10 specialized agent exports
- `app/workflows/engine.py`: Workflow execution engine
- `app/services/cache.py`: Redis cache with circuit breaker
- `app/sse_utils.py`: SSE event processing pipeline
- `app/exceptions.py`: Error handling hierarchy

**Testing:**
- `tests/unit/`: Unit tests (mirrors `app/` structure)
- `tests/integration/`: Integration tests
- `tests/eval_datasets/`: Agent evaluation data
- `frontend/__tests__/`: Frontend tests

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `cache.py`, `workflow_engine.py`)
- Agent definitions: `app/agents/<domain>/agent.py` (each domain has its own package)
- Tool modules: `app/agents/tools/<tool_name>.py` (e.g., `calendar_tool.py`, `ui_widgets.py`)
- Router modules: `app/routers/<domain>.py` (e.g., `workflows.py`, `approvals.py`)
- Service modules: `app/services/<domain>_service.py` (e.g., `cache.py`, `campaign_service.py`)
- React components: `PascalCase.tsx` (e.g., `NotificationCenter.tsx`)
- React hooks: `useCamelCase.ts` (e.g., `useAgentChat.ts`)
- Frontend services: `camelCase.ts` (e.g., `widgetDisplay.ts`, `api.ts`)
- SQL migrations: `YYYYMMDDHHMMSS_description.sql` or `NNNN_description.sql` (legacy)

**Directories:**
- Python packages: `snake_case/` (e.g., `customer_support/`, `workflow_builder/`)
- Frontend component dirs: `kebab-case/` (e.g., `knowledge-vault/`, `workflow-builder/`)
- Next.js route groups: `(groupName)/` (e.g., `(personas)/`)

## Where to Add New Code

**New Specialized Agent:**
- Agent definition: `app/agents/<domain>/agent.py`
- Agent-specific tools: `app/agents/<domain>/tools.py`
- Register in: `app/agents/specialized_agents.py` (add to `SPECIALIZED_AGENTS` list)
- Add factory function: `create_<domain>_agent()` for workflow support

**New Agent Tool:**
- Implementation: `app/agents/tools/<tool_name>.py`
- Export as: `<TOOL_NAME>_TOOLS` list
- Register in target agent's tool list (in `agent.py`)
- If used by ExecutiveAgent: add to `_EXECUTIVE_TOOLS` in `app/agent.py`

**New API Router:**
- Implementation: `app/routers/<domain>.py`
- Register in: `app/fast_api_app.py` (import + `app.include_router()`)
- Use `verify_token` dependency for authenticated endpoints

**New Service:**
- Implementation: `app/services/<domain>_service.py`
- Pattern: Async functions or class with `get_service_client()` for Supabase access

**New Frontend Page:**
- Persona-scoped: `frontend/src/app/(personas)/<persona>/<page>/page.tsx`
- Global: `frontend/src/app/<page>/page.tsx`

**New Frontend Component:**
- Shared component: `frontend/src/components/<category>/<ComponentName>.tsx`
- Page-specific: `frontend/src/app/<page>/components/<ComponentName>.tsx`

**New Frontend Hook:**
- Implementation: `frontend/src/hooks/use<HookName>.ts`

**New Frontend Service:**
- Implementation: `frontend/src/services/<domain>.ts`
- Use `fetchWithAuth()` from `frontend/src/services/api.ts` for authenticated calls

**New Widget Type:**
- Backend definition: Add to `app/models/widgets.py` and `app/agents/tools/ui_widgets.py`
- SSE registration: Add type to `RENDERABLE_WIDGET_TYPES` in `app/sse_utils.py`
- Frontend type: Add to `frontend/src/types/widgets.ts`
- Frontend renderer: Add component to `frontend/src/components/widgets/`
- Frontend display: Register in `frontend/src/services/widgetDisplay.ts`

**New Database Table:**
- Migration: `supabase/migrations/YYYYMMDDHHMMSS_description.sql`
- Include RLS policies in the migration

**New Workflow Template:**
- Definition: `app/workflows/definitions/<name>.py` or seed via migration
- Register in workflow template seed migration

**New MCP Tool:**
- Implementation: `app/mcp/tools/<tool_name>.py`
- Register in agent tool list or MCP connector

**New Skill:**
- Built-in: Add to `app/skills/library.py` or appropriate `app/skills/professional_*.py`
- Custom (runtime): Created via `create_custom_skill` agent tool, stored in Supabase

## Special Directories

**`app/prompts/`:**
- Purpose: External prompt template files loaded at agent initialization
- Contains: `executive_instruction.txt` (18k lines, ExecutiveAgent system prompt)
- Generated: No
- Committed: Yes

**`supabase/migrations/`:**
- Purpose: Schema migration chain (source of truth for database structure)
- Contains: 60+ SQL files with schema DDL, RLS policies, seed data
- Generated: No
- Committed: Yes

**`app/skills/professional_*.py`:**
- Purpose: Large professional skill knowledge bases
- Contains: 4 files totaling 450k+ lines of structured skill content
- Generated: Partially (curated and edited)
- Committed: Yes

**`supabase/functions/`:**
- Purpose: Deno-based Supabase Edge Functions
- Contains: 5 functions + shared utilities
- Generated: No
- Committed: Yes

**`remotion-render/`:**
- Purpose: Remotion video rendering service (Node.js)
- Contains: Video composition source code
- Generated: No
- Committed: Yes (node_modules excluded)

**`.planning/`:**
- Purpose: Project planning and analysis documents
- Contains: Codebase analysis, phase plans, milestones
- Generated: Yes (by Claude Code)
- Committed: Yes

**`deployment/terraform/`:**
- Purpose: Infrastructure-as-code for Google Cloud
- Contains: Terraform configs for Cloud Run, networking, SQL
- Generated: No
- Committed: Yes

---

*Structure analysis: 2026-03-20*

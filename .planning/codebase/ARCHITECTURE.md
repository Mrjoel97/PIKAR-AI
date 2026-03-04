# Architecture

**Analysis Date:** 2026-03-04

## Pattern Overview

**Overall:** Hybrid multi-agent backend + API platform + Next.js client + Supabase orchestration

**Key Characteristics:**
- Executive orchestrator agent delegates to specialized domain agents
- Tool-first architecture where business capabilities are exposed as callable tool functions
- API and workflow layers are separated (FastAPI routes + workflow engine + Supabase edge functions)
- Stateful chat/session continuity backed by Supabase with cache acceleration

## Layers

**Experience Layer (HTTP + UI):**
- Purpose: user entry points, API routing, SSE streaming, web UI
- Contains: FastAPI app/routers, Next.js pages/components
- Location: `app/fast_api_app.py`, `app/routers/*`, `frontend/src/app/*`, `frontend/src/components/*`
- Depends on: orchestration and service layers
- Used by: browser clients, A2A clients, internal scheduled callers

**Agent Orchestration Layer:**
- Purpose: route user intent, delegate to specialists, coordinate tool/sub-agent execution
- Contains: Executive agent, specialized agents, ADK app wiring, shared model configs
- Location: `app/agent.py`, `app/agents/*`, `app/agents/specialized_agents.py`
- Depends on: tools, services, persistence
- Used by: SSE chat route and A2A execution runner

**Workflow Orchestration Layer:**
- Purpose: execute template-driven multi-step workflows with readiness and lifecycle gates
- Contains: workflow engine, worker, template validation, registry, readiness checks
- Location: `app/workflows/*`, `app/services/edge_functions.py`, `supabase/functions/execute-workflow/index.ts`
- Depends on: Supabase tables/functions and tool registry
- Used by: workflow API routes and scheduled operations

**Domain Services Layer:**
- Purpose: business logic and integration adapters
- Contains: finance, CRM, analytics, media/video, vault, notification, onboarding services
- Location: `app/services/*`, `app/rag/*`, `app/commerce/*`
- Depends on: integrations/data layer
- Used by: routers and tool functions

**Integrations & Data Layer:**
- Purpose: external systems access, persistence, cache, auth/session state
- Contains: Supabase clients, session/task stores, Redis cache, MCP integrations
- Location: `app/services/supabase_client.py`, `app/persistence/*`, `app/services/cache.py`, `app/mcp/*`, `supabase/*`
- Depends on: environment configuration + external providers
- Used by: all upper layers

## Data Flow

**Interactive Chat (SSE):**
1. Client posts to `POST /a2a/app/run_sse` (`app/routers/chat.py`)
2. Router validates token and resolves `effective_user_id`
3. Session is loaded/created via `SupabaseSessionService` (`app/persistence/supabase_session_service.py`)
4. ADK `Runner.run_async` executes the executive agent tree (`app/fast_api_app.py`, `app/agent.py`)
5. Agent delegates to sub-agents/tools as needed
6. Events and widget payloads are streamed back via SSE
7. Session events/state persist to Supabase; cache metadata is updated/invalidate-on-write

**Workflow Execution:**
1. Client starts workflow via workflow route/service
2. `WorkflowEngine.start_workflow` validates template lifecycle/readiness (`app/workflows/engine.py`)
3. Execution record is created in `workflow_executions`
4. Engine asynchronously triggers Supabase edge function `execute-workflow`
5. Steps progress through DB + edge callbacks + tool invocation
6. Status/history are queried via workflow endpoints

**State Management:**
- Persistent state: Supabase sessions/events/workflow tables
- Cached state: Redis user/session/persona keys (cache-aside)
- Context window control: session event load capped by `SESSION_MAX_EVENTS` (default 80)

## Key Abstractions

**PikarAgent Wrapper:**
- Purpose: local ADK subclass for path resolution and consistent agent construction
- Location: `app/agents/base_agent.py`
- Pattern: adapter/subclass around ADK `Agent`

**Singleton + Factory Agent Pattern:**
- Purpose: support delegation ownership constraints and workflow-local agent instances
- Examples: singleton agents + `create_*_agent` in `app/agents/*/agent.py`
- Pattern: singleton for executive tree, factory for independent workflow contexts

**Tool Registry Contract:**
- Purpose: expose capabilities to agents and workflow steps with explicit naming/validation
- Examples: `app/agents/tools/*`, `app/agents/tools/registry.py`, `app/workflows/template_validation.py`
- Pattern: declarative lists (`*_TOOLS`) merged into orchestrator/tool registries

**Canonical Financial Snapshot:**
- Purpose: normalize multi-source finance data into stable reportable schema
- Location: `app/services/financial_service.py`, `app/services/finance_dto.py`
- Pattern: adapter aggregation + source metadata provenance

## Entry Points

**Backend API Entry:**
- Location: `app/fast_api_app.py`
- Triggers: HTTP requests, SSE requests, A2A protocol endpoints
- Responsibilities: app startup, middleware, router registration, runner/session service wiring

**Agent Graph Entry:**
- Location: `app/agent.py`
- Triggers: ADK runner invocation
- Responsibilities: executive agent composition, tool registration, fallback model app

**Frontend Entry:**
- Location: `frontend/src/app/layout.tsx`, `frontend/src/app/page.tsx`
- Triggers: browser navigation
- Responsibilities: route rendering, auth session bootstrapping, API calls

**Edge Workflow Entry:**
- Location: `supabase/functions/execute-workflow/index.ts`
- Triggers: backend edge invocation/webhooks
- Responsibilities: workflow step progression and callback handling

## Error Handling

**Strategy:** Boundary-level exception handling with structured fallbacks

**Patterns:**
- Global exception registration in FastAPI (`register_exception_handlers`)
- Auth failures mapped to HTTP 401/500 paths (`app/app_utils/auth.py`)
- Integration calls return structured error payloads instead of raising to user-facing surface when possible
- Model fallback runner for unavailable primary model in SSE path (`app/routers/chat.py`)

## Cross-Cutting Concerns

**Logging:**
- Module-level loggers throughout backend modules
- Request logging middleware (`app/middleware/logging_middleware.py`)

**Validation:**
- Startup env validation + optional bypass modes (`app/config/validation.py`, `app/fast_api_app.py`)
- Workflow phase/designer validation (`app/workflows/template_validation.py`)

**Authentication:**
- Supabase bearer token verification for user routes
- Optional strict auth mode (`REQUIRE_STRICT_AUTH`)
- Internal service secret auth for workflow callbacks

**Rate Limiting:**
- SlowAPI middleware + persona-aware limits (`app/middleware/rate_limiter.py`)

**Caching & Resilience:**
- Redis cache service with circuit breaker (`app/services/cache.py`)
- Connection fallbacks for optional components (A2A/core services)

---

*Architecture analysis: 2026-03-04*
*Update when major patterns change*

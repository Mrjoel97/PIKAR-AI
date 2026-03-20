# Architecture

**Analysis Date:** 2026-03-20

## Pattern Overview

**Overall:** Multi-Agent Orchestration with Layered Monolith Backend + Next.js Frontend

**Key Characteristics:**
- Central ExecutiveAgent delegates tasks to 10 domain-specialized sub-agents via Google ADK
- FastAPI backend serves as API gateway, SSE streaming hub, and A2A Protocol endpoint
- Next.js App Router frontend communicates via SSE for chat and REST for CRUD
- Supabase (PostgreSQL) as primary datastore with Redis caching layer and circuit breaker
- Persona-based UI routing with 4 business profiles (solopreneur, startup, sme, enterprise)
- Skills system provides extensible domain knowledge to agents at runtime

## Layers

**Agent Layer (Orchestration):**
- Purpose: AI-powered task routing, execution, and multi-agent coordination
- Location: `app/agents/`
- Contains: Agent definitions, shared configs, instruction templates, tools, context extraction
- Depends on: Google ADK, Gemini models, Skills layer, Tool layer, MCP layer
- Used by: FastAPI SSE endpoint, Workflow engine

**API Layer (HTTP):**
- Purpose: REST endpoints, SSE streaming, A2A protocol, middleware, auth
- Location: `app/fast_api_app.py`, `app/routers/`
- Contains: 20+ routers, SSE chat endpoint, health checks, admin endpoints
- Depends on: Agent layer (via Runner), Services layer, Auth utilities
- Used by: Frontend (Next.js), external A2A clients

**Service Layer (Business Logic):**
- Purpose: Domain-specific business operations, caching, scheduling, analytics
- Location: `app/services/`
- Contains: 55+ service modules covering cache, workflows, campaigns, initiatives, reporting
- Depends on: Supabase client, Redis, external APIs
- Used by: API layer, Agent tools, Workflow engine

**Workflow Layer:**
- Purpose: Structured multi-step workflow execution with approval gates
- Location: `app/workflows/`
- Contains: Engine, step executor, worker, contract defaults, trust classification, readiness checks
- Depends on: Service layer, Supabase, Agent layer (for step execution)
- Used by: API routers, Agent tools, Scheduled endpoints

**Persistence Layer:**
- Purpose: Session and task storage for ADK runtime
- Location: `app/persistence/`
- Contains: `supabase_session_service.py` (ADK session persistence), `supabase_task_store.py` (A2A tasks)
- Depends on: Supabase client
- Used by: ADK Runner, A2A request handler

**RAG Layer (Knowledge):**
- Purpose: Retrieval-augmented generation via Knowledge Vault
- Location: `app/rag/`
- Contains: Embedding service (Gemini), ingestion pipeline, search service, knowledge vault
- Depends on: Supabase (pgvector), Gemini embeddings
- Used by: Agent tools, Orchestration layer

**MCP Layer (Model Context Protocol):**
- Purpose: External tool integrations via MCP standard
- Location: `app/mcp/`
- Contains: Tool connectors (Stripe, Canva, web search/scrape, SEO, social listening), security guards (PII filter, audit logger, external call guard), integration services (CRM, email)
- Depends on: External APIs, security layer
- Used by: Agent tools

**Skills Layer:**
- Purpose: Extensible domain knowledge library accessible by agents
- Location: `app/skills/`
- Contains: Skill library (71k+ lines of professional skills), registry, loader, skill creator, validation, custom skills service
- Depends on: Supabase (skill storage), Gemini (embeddings for search)
- Used by: Agent tools (`use_skill`, `search_skills`)

**Frontend Layer:**
- Purpose: User interface for chat, dashboards, workflows, settings
- Location: `frontend/src/`
- Contains: Next.js App Router pages, React components, hooks, services, contexts
- Depends on: Backend API (REST + SSE), Supabase (auth, realtime)
- Used by: End users via browser

## Data Flow

**Chat Interaction (Primary Flow):**

1. User sends message via frontend `useAgentChat` hook -> `POST /a2a/app/run_sse`
2. `fast_api_app.py` authenticates via Supabase JWT, resolves user_id, checks SSE connection limits
3. Session is created/loaded via `SupabaseSessionService`, user personalization preloaded
4. `Runner.run_async()` dispatches to `ExecutiveAgent` with ADK message
5. ExecutiveAgent uses tools directly or delegates to specialized sub-agents
6. ADK events stream back, post-processed by `sse_utils.py` (widget extraction, trace extraction)
7. Frontend parses SSE events, renders messages and widgets via `WidgetDisplayService`

**Workflow Execution:**

1. Workflow triggered via API (`POST /workflows/execute`), agent tool, or scheduled endpoint
2. `WorkflowEngine` loads template from Supabase, enriches with contract defaults
3. Trust classification determines approval requirements (auto-approve, human-review, restricted)
4. Steps execute via `StepExecutor`, which may invoke agent tools or edge functions
5. Approval gates pause execution and notify users via notification service
6. Progress events stream to frontend via SSE progress queue

**Request Context Propagation:**

1. SSE endpoint sets `user_id`, `session_id`, `agent_mode` via contextvars (`request_context.py`)
2. Agent tools access context via `get_current_user_id()`, `get_current_agent_mode()`
3. Progress updates flow back via `emit_progress_update()` -> progress queue -> SSE stream

**State Management:**
- Backend sessions: `SupabaseSessionService` persists ADK session state to PostgreSQL
- User context: `context_extractor.py` callbacks auto-extract and inject user facts into model prompts
- Frontend state: React contexts (`PersonaContext`, `ChatSessionContext`, `NotificationContext`)
- Cache: Redis with circuit breaker (`app/services/cache.py`) for user config, session meta, persona data
- Request-scoped: Python `contextvars` in `app/services/request_context.py`

## Key Abstractions

**PikarAgent (Agent Wrapper):**
- Purpose: Custom ADK Agent subclass for path resolution
- Location: `app/agents/base_agent.py`
- Pattern: All agents use `PikarAgent` (aliased as `Agent`) instead of `google.adk.agents.Agent`

**Specialized Agent Pattern:**
- Purpose: Domain-specific AI agents with tools, instructions, and sub-agents
- Examples: `app/agents/financial/agent.py`, `app/agents/content/agent.py`, `app/agents/marketing/agent.py`
- Pattern: Each agent module exports a singleton instance + `create_*_agent()` factory function. Singletons are used by ExecutiveAgent; factories create fresh instances for workflows (ADK enforces single-parent constraint).

**GenerateContentConfig Profiles:**
- Purpose: Performance-tuned LLM configs per agent type
- Location: `app/agents/shared.py`
- Pattern: 4 profiles - `FAST_AGENT_CONFIG` (routing/delegation), `ROUTING_AGENT_CONFIG` (executive), `DEEP_AGENT_CONFIG` (analysis), `CREATIVE_AGENT_CONFIG` (content generation)

**Tool Sanitization:**
- Purpose: Validates and normalizes tool lists before agent construction
- Location: `app/agents/tools/base.py`
- Pattern: `sanitize_tools()` called on every tool list before passing to agent constructor

**Shared Instructions:**
- Purpose: Reusable instruction blocks composed into agent prompts
- Location: `app/agents/shared_instructions.py`
- Pattern: `SKILLS_REGISTRY_INSTRUCTIONS`, `CONVERSATION_MEMORY_INSTRUCTIONS`, `SELF_IMPROVEMENT_INSTRUCTIONS`, `get_error_and_escalation_instructions()` are appended to each agent's base instruction

**CacheService with Circuit Breaker:**
- Purpose: Redis cache that degrades gracefully when Redis is unavailable
- Location: `app/services/cache.py`
- Pattern: `@with_circuit_breaker` decorator tracks failures, opens circuit after threshold, auto-recovers. `CacheResult` dataclass distinguishes hits, misses, and errors.

**Widget System:**
- Purpose: Agent-to-UI interactive widget rendering
- Location: Backend `app/agents/tools/ui_widgets.py`, `app/models/widgets.py`; Frontend `frontend/src/types/widgets.ts`, `frontend/src/services/widgetDisplay.ts`, `frontend/src/components/widgets/`
- Pattern: Agents create widget definitions via tools -> SSE extracts widgets from tool results -> frontend `WidgetDisplayService` validates and renders via `WidgetRegistry`

**Custom Exception Hierarchy:**
- Purpose: Structured error handling with error codes and HTTP status mapping
- Location: `app/exceptions.py`
- Pattern: `PikarError` base class with `ErrorCode` enum. Specialized exceptions: `ValidationError`, `DatabaseError`, `CacheError`, `WorkflowError`, `AgentError`, `SkillError`. Global handlers in `fast_api_app.py` convert to `ErrorResponse` JSON.

**Persona System:**
- Purpose: Business-profile-aware UI routing and agent behavior
- Location: Backend `app/personas/`; Frontend `frontend/src/app/(personas)/`, `frontend/src/contexts/PersonaContext.tsx`
- Pattern: 4 personas (solopreneur, startup, sme, enterprise) control workflow visibility, prompt fragments, UI layout. Backend enforces persona-scoped workflow access.

## Entry Points

**FastAPI Application:**
- Location: `app/fast_api_app.py`
- Triggers: `uvicorn` (dev), Docker container (prod), Cloud Run
- Responsibilities: HTTP server, SSE streaming, A2A protocol, middleware stack, health checks

**ADK App:**
- Location: `app/agent.py`
- Triggers: Imported by `fast_api_app.py`, used by ADK Runner
- Responsibilities: Defines ExecutiveAgent, composes tool lists, creates primary + fallback App instances with context cache and events compaction

**Frontend App:**
- Location: `frontend/src/app/layout.tsx`, `frontend/src/app/page.tsx`
- Triggers: `next dev` / `next start`
- Responsibilities: Root layout with PersonaProvider + ChatSessionProvider, persona-based routing

**Workflow Worker:**
- Location: `app/workflows/worker.py`
- Triggers: Background tasks, scheduled endpoints
- Responsibilities: Asynchronous workflow step execution

**Supabase Edge Functions:**
- Location: `supabase/functions/`
- Triggers: Database webhooks, HTTP calls
- Responsibilities: `execute-workflow`, `send-notification`, `generate-widget`, `cleanup-sessions`, `page-analytics-track`

**Scheduled Endpoints:**
- Location: `app/services/scheduled_endpoints.py`
- Triggers: Cloud Scheduler (cron)
- Responsibilities: Periodic tasks (report scheduling, session cleanup)

## Error Handling

**Strategy:** Layered exception handling with structured error responses

**Patterns:**
- Custom exception hierarchy rooted at `PikarError` (`app/exceptions.py`) with error codes mapped to HTTP status codes
- Global FastAPI exception handlers convert `PikarError`, `HTTPException`, `RequestValidationError`, and generic `Exception` to structured `ErrorResponse` JSON
- CORS headers injected into all error responses to prevent browser blocking
- Debug mode (via `DEBUG` env var) exposes exception details; production sanitizes
- Agent model fallback: primary Gemini 2.5 Pro -> fallback Gemini 2.5 Flash on model unavailability
- Redis circuit breaker: tracks consecutive failures, opens circuit to prevent cascading errors, auto-recovers after cooldown
- SSE stream: max duration timeout (`SSE_MAX_DURATION_S`), keepalive pings, graceful task cancellation on disconnect

## Cross-Cutting Concerns

**Logging:** Python `logging` module throughout backend. `RequestLoggingMiddleware` adds request_id, user_id, session_id to all request/response logs. Health check endpoints exempt from verbose logging.

**Validation:** Pydantic models for request validation (`ChatRequest`, `Feedback`). Environment validation at startup via `app/config/validation.py`. Workflow template validation via `app/workflows/template_validation.py`. Tool input validation via `app/agents/tools/validation.py`.

**Authentication:** Supabase JWT tokens verified via `app/app_utils/auth.py`. Two modes: strict (production) and permissive (development). Frontend passes tokens via `Authorization: Bearer` header. Persona header (`x-pikar-persona`) attached to all API calls.

**Rate Limiting:** `slowapi` middleware with configurable limits (`app/middleware/rate_limiter.py`). Per-user SSE connection limits (`app/services/sse_connection_limits.py`).

**Security:** Security headers middleware (`app/middleware/security_headers.py`). MCP external call guard (`app/mcp/security/external_call_guard.py`). PII filter (`app/mcp/security/pii_filter.py`). MCP audit logger (`app/mcp/security/audit_logger.py`). CORS configured via `ALLOWED_ORIGINS` env var with wildcard blocked in production.

**Onboarding:** `OnboardingGuardMiddleware` (`app/middleware/onboarding_guard.py`) enforces onboarding completion before accessing protected routes.

---

*Architecture analysis: 2026-03-20*

# Architecture

**Analysis Date:** 2026-03-11

## Pattern Overview

**Overall:** Multi-Agent Orchestration with FastAPI Backend

The codebase follows a hierarchical agent-based architecture where a central Executive Agent orchestrates specialized domain agents. Built on Google's ADK (Agent Development Kit) framework, the system implements the A2A (Agent-to-Agent) protocol for interoperability.

**Key Characteristics:**
- **Hierarchical agent delegation:** Executive Agent dispatches tasks to specialized agents (Financial, Content, Strategic, Sales, Marketing, Operations, HR, Compliance, Customer Support, Data)
- **Service-oriented architecture:** Business logic abstracted into reusable services (cache, database, RAG, video generation, external integrations)
- **Persistent session management:** Supabase-backed session and task stores for multi-turn conversations
- **Resilience patterns:** Circuit breaker for Redis, fallback models, graceful degradation
- **Modular tool ecosystem:** Tools grouped by domain (Google Workspace, media, MCP integrations, custom workflows)

## Layers

**Agent Layer (Orchestration):**
- Purpose: Central intelligence and task delegation across business domains
- Location: `app/agent.py`, `app/agents/`
- Contains: Executive Agent definition, specialized agent definitions, agent context memory, callbacks
- Depends on: Google ADK framework, tool implementations, services
- Used by: FastAPI application for request handling, A2A protocol executor

**Tool Layer (Capability Binding):**
- Purpose: Expose specific functionalities to agents as callable tools
- Location: `app/agents/tools/`, `app/mcp/tools/`, `app/orchestration/`
- Contains: Tool implementations (media, calendar, docs, Gmail, workflows, notifications, UI widgets, knowledge injection, Canva, Stripe, Supabase, etc.)
- Depends on: External APIs (Google Workspace, MCP servers), service layer
- Used by: Agent instances for task execution

**Service Layer (Business Logic):**
- Purpose: Encapsulate domain-specific logic and external integrations
- Location: `app/services/`
- Contains: Cache service, task service, initiative service, RAG services, video generation, financial/compliance/content/campaign services, notification/alert services
- Depends on: Database layer, external APIs, configuration
- Used by: Tools, routers, agents

**Database Layer (Persistence):**
- Purpose: Store and retrieve application state
- Location: `app/database/`, `app/persistence/`
- Contains: SQLAlchemy ORM models, session factory, Supabase client wrappers, session/task stores
- Depends on: Supabase API, environment configuration
- Used by: Services, routers, session management

**API Layer (Request/Response Handling):**
- Purpose: Expose agent capabilities over HTTP
- Location: `app/fast_api_app.py`, `app/routers/`
- Contains: FastAPI application, A2A protocol endpoints, feature-specific routers (initiatives, workflows, approvals, etc.), request handlers, authentication middleware
- Depends on: Agent layer, service layer, middleware, authentication
- Used by: External clients, A2A protocol agents

**Configuration Layer (Environment & Validation):**
- Purpose: Manage environment variables, validation, and startup configuration
- Location: `app/config/`, `.env` files
- Contains: Environment validation, OpenAPI config, settings, feature flags
- Depends on: Environment variables
- Used by: All layers during initialization

**Infrastructure Layer (Caching & Resilience):**
- Purpose: Provide infrastructure-level reliability and performance
- Location: `app/services/cache.py`, `app/middleware/`
- Contains: Redis cache with circuit breaker pattern, rate limiting, request logging
- Depends on: Redis (with fallback), external rate limit tracking
- Used by: Services, API layer

## Data Flow

**User Request to Agent Response:**

1. Client sends HTTP request to FastAPI endpoint (`POST /a2a/app/run_sse` for streaming chat)
2. Request passes through:
   - Rate limiting middleware (`SlowAPIMiddleware`)
   - Request logging middleware (`RequestLoggingMiddleware`)
   - Authentication verification via JWT token
3. FastAPI router extracts request context and user information
4. For A2A protocol requests: `DefaultRequestHandler` creates execution context
5. `Runner` (ADK) instantiates executive agent with context
6. Executive Agent processes message:
   - Checks context memory for relevant user facts (before_model_callback)
   - Calls LLM (routing model, with fallback if primary unavailable)
   - Receives tool calls from LLM
7. Tool execution:
   - If tool is specialized agent delegation: Creates agent instance from factory function
   - If tool is standard tool: Calls tool function directly
   - Tool function queries services or external APIs
8. Service interaction:
   - Services check cache first (Redis with circuit breaker)
   - If cache miss or error: Query database or external API
   - Results stored back in cache if applicable
9. Agent context updated (after_tool_callback)
10. Response streamed back via SSE (Server-Sent Events) or returned as JSON

**Session Management:**
1. User creates session via A2A request or feature endpoint
2. `SupabaseSessionService` creates session record in Supabase
3. Session ID returned to client
4. Client includes session ID in subsequent requests
5. `Runner` retrieves session state for conversation continuity
6. Multi-turn conversations maintain context through session store

**Cache-Aside Pattern:**
1. Service receives query request
2. Calls `CacheService.get_cached(key)`
3. If cache hit: Return cached value
4. If cache miss or circuit open: Query primary source (database/API)
5. If successful: Store result in cache with TTL
6. Return result

## Key Abstractions

**Agent Abstraction:**
- Purpose: Autonomous units that can process requests and delegate to tools/sub-agents
- Examples: `ExecutiveAgent` (`app/agent.py`), `FinancialAgent` (`app/agents/financial`), `ContentAgent` (`app/agents/content`)
- Pattern: Google ADK `Agent` class with instruction, tools, and optional sub_agents list

**Tool Abstraction:**
- Purpose: Discrete capabilities callable by agents
- Examples: `create_task()`, `search_business_knowledge()`, `GMAIL_TOOLS`, `MEDIA_TOOLS`
- Pattern: Python functions with docstrings (used as tool descriptions), grouped in tool modules/tools lists

**Service Abstraction:**
- Purpose: Reusable business logic abstraction
- Examples: `CacheService`, `TaskService`, `InitiativeService`, `VideoReadinessService`
- Pattern: Class-based services with async methods, often using `BaseService` for Supabase authentication

**Router Abstraction:**
- Purpose: Feature-specific HTTP endpoints
- Examples: `app/routers/initiatives.py`, `app/routers/workflows.py`, `app/routers/approvals.py`
- Pattern: FastAPI `APIRouter` with dependency injection for authentication/context

**Session Store Abstraction:**
- Purpose: Multi-turn conversation state persistence
- Examples: `SupabaseSessionService`, `InMemorySessionService`
- Pattern: ADK-compatible service implementing session CRUD operations

**Task Store Abstraction:**
- Purpose: Persist async task execution results
- Examples: `SupabaseTaskStore`
- Pattern: ADK-compatible service for storing A2A task states

## Entry Points

**HTTP Server:**
- Location: `app/fast_api_app.py::lifespan()`, `FastAPI()` instance initialization
- Triggers: Application startup via `make local-backend` or `make deploy`
- Responsibilities: Initialize FastAPI app, configure CORS, register routers, set up middleware, build A2A handler

**Agent Execution:**
- Location: `app/agent.py::_build_executive_agent()`, `Runner.run_stream()`
- Triggers: A2A protocol request or feature endpoint call
- Responsibilities: Create/reuse agent instances, execute LLM calls, orchestrate tool execution, manage context

**A2A Protocol Endpoint:**
- Location: `app/fast_api_app.py` (via `A2AFastAPIApplication`), registered at `/a2a/{app_name}/`
- Triggers: Agent-to-agent RPC requests with A2A protocol compliance
- Responsibilities: Accept A2A-formatted requests, route to `DefaultRequestHandler`, return A2A-formatted responses

**Feature Routers:**
- Location: `app/routers/` (initiatives, workflows, approvals, etc.)
- Triggers: HTTP requests to `/initiatives/`, `/workflows/`, etc.
- Responsibilities: Handle feature-specific business logic, interact with services, return structured responses

**Startup Validation:**
- Location: `app/config/validation.py::validate_startup()`
- Triggers: Application initialization (before first request)
- Responsibilities: Validate required environment variables, check credentials, verify external service accessibility

## Error Handling

**Strategy:** Layered error handling with graceful degradation

**Patterns:**
- **Cache failures:** Circuit breaker pattern - if Redis unavailable, services fall back to direct database/API queries
- **Model unavailability:** Fallback model routing - if primary LLM unavailable, uses fallback model via retry mechanism
- **External API failures:** Exception wrapping in domain-specific exceptions (`app/exceptions.py`)
- **Database errors:** SQLAlchemy session rollback with retry logic
- **Validation errors:** FastAPI automatic JSON validation response generation
- **Auth failures:** JWT verification returns 401 Unauthorized, requests without token return 403 Forbidden
- **Rate limiting:** SlowAPI returns 429 Too Many Requests with retry headers
- **A2A protocol errors:** Returns A2A-compliant error responses with error codes and messages

**Exception Hierarchy:**
- `PikarAIException` (base)
  - `CacheError`, `CacheConnectionError`, `CacheMissError`
  - `DatabaseError`, `ValidationError`
  - `AuthenticationError`, `AuthorizationError`
  - Domain-specific exceptions

## Cross-Cutting Concerns

**Logging:**
- Framework: Python standard `logging` module
- Approach: Contextual logging with request ID tracking (`RequestLoggingMiddleware`), Google Cloud Logging integration
- Pattern: `logger = logging.getLogger(__name__)` in each module, structured logging with context

**Validation:**
- Approach: Environment validation at startup, Pydantic model validation for requests, custom validators in service layer
- Pattern: `validate_startup()` checks credentials/config early, Pydantic `BaseModel` enforces request schemas

**Authentication:**
- Approach: JWT token verification via `app/app_utils/auth.py::verify_token()`, token included in Supabase clients for RLS enforcement
- Pattern: Tokens extracted from request headers, validated, and injected into services for user-scoped queries

**Rate Limiting:**
- Approach: `SlowAPIMiddleware` from slowapi library
- Pattern: Configured limits per endpoint, fallback to default limits, returns 429 with retry headers

**Telemetry:**
- Approach: OpenTelemetry integration with Google Cloud Trace (always enabled), optional prompt-response logging to BigQuery/GCS
- Pattern: Automatic instrumentation of ADK execution, manual span creation in services

---

*Architecture analysis: 2026-03-11*

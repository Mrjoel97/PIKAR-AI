# Codebase Structure

**Analysis Date:** 2026-03-11

## Directory Layout

```
pikar-ai/
├── app/                          # Core application code (Python)
│   ├── agent.py                  # Executive Agent and ADK App definition
│   ├── fast_api_app.py          # FastAPI application and routes
│   ├── sse_utils.py             # Server-Sent Events streaming utilities
│   ├── exceptions.py            # Domain-specific exception classes
│   ├── __init__.py              # Package initialization
│   │
│   ├── agents/                  # Multi-agent system
│   │   ├── base_agent.py        # Base agent class (PikarAgent)
│   │   ├── shared_instructions.py    # Common instructions for all agents
│   │   ├── shared.py            # Shared utilities (model selection, config)
│   │   ├── context_extractor.py # Context memory callbacks
│   │   ├── schemas.py           # Pydantic models for agents
│   │   ├── enhanced_tools.py    # Enhanced tool implementations
│   │   ├── specialized_agents.py # Re-export of all specialized agents
│   │   ├── workflow_creator_agent.py # Workflow-specific agent
│   │   │
│   │   ├── tools/               # Agent-callable tools
│   │   │   ├── agent_skills.py  # Skill management tools
│   │   │   ├── calendar_tool.py # Google Calendar integration
│   │   │   ├── configuration.py # MCP tool configuration
│   │   │   ├── deep_research.py # Intelligent research tools
│   │   │   ├── docs.py          # Google Docs tools
│   │   │   ├── forms.py         # Google Forms tools
│   │   │   ├── gmail.py         # Gmail integration tools
│   │   │   ├── google_sheets.py # Google Sheets tools
│   │   │   ├── media.py         # Media generation tools
│   │   │   ├── notifications.py # Notification tools
│   │   │   ├── ui_widgets.py    # UI widget tools
│   │   │   ├── workflows.py     # Workflow orchestration tools
│   │   │   ├── brain_dump.py    # Brain dump document tools
│   │   │   ├── context_memory.py# Context memory tools
│   │   │   ├── registry.py      # Tool registry
│   │   │   └── test_ui_widgets.py # UI widget tests
│   │   │
│   │   ├── compliance/          # Compliance agent and tools
│   │   ├── content/             # Content agent and tools
│   │   ├── customer_support/    # Customer Support agent and tools
│   │   ├── data/                # Data agent and tools
│   │   ├── financial/           # Financial agent and tools
│   │   ├── hr/                  # HR agent and tools
│   │   ├── marketing/           # Marketing agent and tools
│   │   ├── operations/          # Operations agent and tools
│   │   ├── reporting/           # Reporting agent and tools
│   │   ├── sales/               # Sales agent and tools
│   │   └── strategic/           # Strategic agent and tools
│   │
│   ├── database/                # Database layer
│   │   ├── __init__.py          # Session factory and utilities
│   │   ├── run_migration.py     # Alembic migration runner
│   │   ├── migrations/          # Alembic migrations directory
│   │   │   └── versions/        # Individual migration files
│   │   └── models/              # SQLAlchemy ORM models
│   │
│   ├── services/                # Business logic and external integrations
│   │   ├── base_service.py      # Base service with Supabase auth
│   │   ├── crud_base.py         # CRUD base for common operations
│   │   ├── cache.py             # Redis cache service with circuit breaker
│   │   ├── supabase.py          # Supabase client wrapper
│   │   ├── supabase_async.py    # Async Supabase utilities
│   │   ├── supabase_client.py   # Advanced Supabase client
│   │   │
│   │   ├── task_service.py      # Task management service
│   │   ├── initiative_service.py# Initiative management service
│   │   ├── initiative_operational_state.py # Initiative state management
│   │   ├── user_onboarding_service.py # Onboarding service
│   │   ├── user_agent_factory.py # Agent factory per user
│   │   ├── request_context.py   # Request-scoped context
│   │   │
│   │   ├── financial_service.py # Financial calculations
│   │   ├── compliance_service.py# Compliance checks
│   │   ├── recruitment_service.py # Recruitment operations
│   │   ├── campaign_service.py  # Campaign management
│   │   ├── analytics_service.py # Analytics generation
│   │   ├── content_service.py   # Content operations
│   │   ├── content_bundle_service.py # Content bundle management
│   │   │
│   │   ├── video_readiness.py   # Video generation readiness
│   │   ├── vertex_video_service.py # Vertex AI video service
│   │   ├── vertex_image_service.py # Vertex AI image service
│   │   ├── director_service.py  # Director API integration
│   │   ├── remotion_render_service.py # Remotion rendering
│   │   ├── long_video_benchmark.py # Long video benchmarking
│   │   │
│   │   ├── voiceover_service.py # Voiceover generation
│   │   ├── audio_music_service.py # Audio and music service
│   │   ├── pptx_generator.py    # PowerPoint generation
│   │   │
│   │   ├── journey_discovery.py # User journey discovery
│   │   ├── journey_audit.py     # Journey auditing
│   │   ├── department_runner.py # Department workflow runner
│   │   ├── semantic_workflow_matcher.py # Workflow matching
│   │   │
│   │   ├── support_ticket_service.py # Support ticket management
│   │   ├── workflow_alerts.py   # Workflow alerts
│   │   ├── feature_flags.py     # Feature flag management
│   │   ├── scheduled_endpoints.py # Scheduled task endpoints
│   │   ├── report_scheduler.py  # Report scheduling
│   │   ├── edge_functions.py    # Edge function integration
│   │   └── video_readiness.py   # Video readiness check
│   │
│   ├── routers/                 # FastAPI route handlers
│   │   ├── initiatives.py       # Initiative endpoints
│   │   ├── workflows.py         # Workflow endpoints
│   │   ├── approvals.py         # Approval flow endpoints
│   │   ├── briefing.py          # Briefing endpoints
│   │   ├── departments.py       # Department endpoints
│   │   ├── org.py               # Organization endpoints
│   │   ├── pages.py             # Page/content endpoints
│   │   ├── onboarding.py        # Onboarding flow endpoints
│   │   ├── configuration.py     # Configuration endpoints
│   │   ├── vault.py             # Knowledge vault endpoints
│   │   ├── reports.py           # Reporting endpoints
│   │   ├── files.py             # File management endpoints
│   │   └── voice_session.py     # Voice session endpoints
│   │
│   ├── orchestration/           # Agent orchestration tools
│   │   ├── knowledge_tools.py   # Knowledge injection tools
│   │   └── tools.py             # General orchestration tools
│   │
│   ├── rag/                     # Retrieval-Augmented Generation
│   │   ├── knowledge_vault.py   # Knowledge base search
│   │   ├── embedding_service.py # Embedding generation
│   │   ├── search_service.py    # Semantic search
│   │   └── ingestion_service.py # Document ingestion
│   │
│   ├── persistence/             # Persistence layer
│   │   ├── supabase_session_service.py # Multi-turn session management
│   │   └── supabase_task_store.py # A2A task persistence
│   │
│   ├── mcp/                     # Model Context Protocol integrations
│   │   ├── integrations/        # MCP service integrations
│   │   ├── security/
│   │   │   └── audit_logger.py  # Audit logging
│   │   └── tools/               # MCP tool implementations
│   │       ├── canva_media.py   # Canva integration
│   │       ├── stripe_payments.py # Stripe integration
│   │       ├── supabase_landing.py # Supabase landing pages
│   │       ├── web_search.py    # Web search via MCP
│   │       └── web_scrape.py    # Web scraping via MCP
│   │
│   ├── middleware/              # FastAPI middleware
│   │   └── rate_limiter.py      # Rate limiting configuration
│   │
│   ├── config/                  # Configuration and validation
│   │   ├── validation.py        # Environment validation at startup
│   │   ├── settings.py          # Settings management
│   │   └── openapi.py           # OpenAPI configuration
│   │
│   ├── models/                  # Pydantic data models
│   │   ├── profile.py           # User profile model
│   │   ├── user.py              # User model
│   │   └── widgets.py           # UI widget models
│   │
│   ├── app_utils/               # Utility functions
│   │   ├── auth.py              # Authentication utilities
│   │   └── typing.py            # Type definitions
│   │
│   ├── integrations/            # External service integrations
│   │   └── google/              # Google services integration
│   │
│   ├── personas/                # User personas
│   ├── prompts/                 # Agent prompts and instructions
│   ├── skills/                  # Custom and restricted skills
│   │   ├── custom/              # User-defined skills
│   │   └── restricted/          # Security-restricted skills
│   ├── notifications/           # Notification system
│   ├── social/                  # Social media integration
│   ├── commerce/                # Commerce operations
│   ├── autonomy/                # Autonomous operations
│   │
│   ├── Docs/                    # Documentation
│   ├── __pycache__/             # Python bytecode cache (gitignored)
│   └── .env.example             # Example environment variables
│
├── tests/                       # Test suite
├── notebooks/                   # Jupyter notebooks for prototyping
├── deployment/                  # Infrastructure as Code (Terraform)
├── .cloudbuild/                 # Google Cloud Build CI/CD
├── .github/workflows/           # GitHub Actions workflows
│
├── pyproject.toml              # Project dependencies (uv)
├── Dockerfile                  # Container image definition
├── Makefile                    # Development commands
├── README.md                   # Project overview
├── GEMINI.md                   # AI-assisted development guide
├── CLAUDE.md                   # Claude development context
└── .env                        # Local environment variables (gitignored)
```

## Directory Purposes

**app/agents/:**
- Purpose: Defines all agent types in the multi-agent system
- Contains: Agent classes, tool definitions, domain-specific logic
- Key files: `specialized_agents.py` (factory/re-export), domain-specific `agent.py` files

**app/agents/tools/:**
- Purpose: Implements tools available to agents
- Contains: Callable tool functions, tool grouping by capability
- Key files: Integration-specific tools (Gmail, Docs, Sheets), workflow tools, knowledge tools

**app/database/:**
- Purpose: Database abstraction and ORM
- Contains: Session factory, SQLAlchemy models, migrations
- Key files: `__init__.py` (session management), `models/` (table definitions)

**app/services/:**
- Purpose: Business logic and external API integration
- Contains: Service classes for each domain and capability
- Key files: `base_service.py` (Supabase auth base), domain-specific services

**app/routers/:**
- Purpose: HTTP API endpoints grouped by feature
- Contains: FastAPI route definitions, request handlers
- Key files: Each router handles one feature domain (initiatives, workflows, etc.)

**app/mcp/:**
- Purpose: Model Context Protocol server implementations
- Contains: MCP integrations (external tools accessible to agents)
- Key files: Integration-specific tool implementations (Canva, Stripe, web search)

**app/rag/:**
- Purpose: Knowledge retrieval and augmentation
- Contains: Embedding, search, ingestion services
- Key files: `knowledge_vault.py` (main interface), `embedding_service.py` (vector ops)

**app/persistence/:**
- Purpose: ADK-compatible persistence layers
- Contains: Session and task store implementations
- Key files: `supabase_session_service.py` (multi-turn conversations), `supabase_task_store.py` (async tasks)

**app/config/:**
- Purpose: Application configuration and validation
- Contains: Environment variable validation, startup checks
- Key files: `validation.py` (startup checks), `settings.py` (config management)

## Key File Locations

**Entry Points:**
- `app/agent.py`: Executive Agent definition and ADK App instantiation
- `app/fast_api_app.py`: FastAPI application, lifespan, middleware, route registration
- `app/agents/specialized_agents.py`: Agent factory imports (backward compatibility)

**Configuration:**
- `app/config/validation.py`: Environment validation at application startup
- `app/config/settings.py`: Application settings and feature flags
- `.env` (root and `app/`): Environment variables
- `pyproject.toml`: Dependencies and project metadata

**Core Logic:**
- `app/agent.py`: Agent instantiation, tool registration, context management
- `app/agents/tools/`: Tool implementations for specific capabilities
- `app/services/`: Business logic and external integrations

**Testing:**
- `tests/`: Unit and integration tests (pytest-based)
- `notebooks/`: Prototyping and evaluation notebooks

## Naming Conventions

**Files:**
- `agent.py`: Agent class definition
- `*_service.py`: Service classes (business logic)
- `*_tools.py`: Tool collections for agents
- `*_router.py` or just in `routers/`: FastAPI route handlers
- `*_model.py` or in `models/`: Pydantic data models
- `*_test.py`: Test files (pytest convention)

**Directories:**
- `app/{agent_type}/`: Specialized agent implementations (e.g., `financial/`, `content/`, `sales/`)
- `app/agents/tools/`: Tool implementations grouped by capability
- `app/services/`: Service classes (never plural at file level, but plural directory)
- `app/routers/`: Feature-specific route handlers
- `app/mcp/`: Model Context Protocol integrations

**Python Classes:**
- `PascalCase`: All classes (services, agents, models, exceptions)
- Examples: `CacheService`, `ExecutiveAgent`, `InitiativeService`, `UserProfile`

**Python Functions:**
- `snake_case`: All functions including tools
- Examples: `create_task()`, `search_business_knowledge()`, `get_cache_service()`

**Python Variables:**
- `snake_case`: Module-level and local variables
- Examples: `logger`, `_instance`, `specialized_agents`

**Tool Collections:**
- `UPPERCASE`: Tool lists exported from tool modules
- Examples: `GMAIL_TOOLS`, `DOCS_TOOLS`, `MEDIA_TOOLS`, `SPECIALIZED_AGENTS`

## Where to Add New Code

**New Feature (Tool-enabled workflow):**
- Primary code: `app/routers/{feature_name}.py` (HTTP endpoint)
- Tool implementations: `app/agents/tools/{tool_name}.py` (if tool-callable)
- Business logic: `app/services/{feature_name}_service.py`
- Database models: `app/database/models/{table_name}.py`
- Tests: `tests/routers/test_{feature_name}.py`

**New Specialized Agent:**
- Implementation: `app/agents/{domain_name}/agent.py` (define factory and singleton)
- Tools for agent: `app/agents/{domain_name}/tools.py` (if domain-specific tools)
- Instructions: `app/agents/{domain_name}/instructions.txt`
- Export: Add to `app/agents/specialized_agents.py` for re-export
- Tests: `tests/agents/test_{domain_name}_agent.py`

**New Tool (Callable by agents):**
- Implementation: `app/agents/tools/{tool_category}.py`
- Organization: Group related tools in same file (e.g., all Gmail tools together)
- Export: Add to tool list in module (e.g., `GMAIL_TOOLS = [list of functions]`)
- Registration: Import and add to agent's tool list in `app/agent.py`
- Documentation: Docstring with clear description and parameters

**New Service (Business logic):**
- Implementation: `app/services/{service_name}.py`
- Base class: Inherit from `BaseService` if using Supabase with RLS, else `object`
- Async methods: Use async/await for I/O operations (database, cache, external APIs)
- Cache usage: Call `CacheService.get_cached()` before database queries
- Tests: `tests/services/test_{service_name}.py`

**New Router (HTTP endpoints):**
- Implementation: `app/routers/{feature_name}.py`
- Pattern: Create `APIRouter`, define `@router.get/post/etc.` endpoints
- Authentication: Use `verify_token()` dependency to extract user JWT
- Response models: Define Pydantic models for request/response validation
- Registration: Import and include in `app/fast_api_app.py` via `app.include_router()`

**Utilities & Helpers:**
- Shared helpers: `app/app_utils/{utility_name}.py`
- Type definitions: `app/app_utils/typing.py`
- Auth utilities: `app/app_utils/auth.py`
- Service exceptions: `app/exceptions.py`

## Special Directories

**app/prompts/:**
- Purpose: Agent instruction templates and system prompts
- Generated: No (manually created)
- Committed: Yes
- Usage: Loaded by agents at initialization, modifiable for fine-tuning behavior

**app/skills/:**
- Purpose: Custom skills and restricted operations
- Generated: Partially (user skills may be generated)
- Committed: Yes (`custom/` and `restricted/` subdirectories)
- Usage: Extended capabilities beyond core tools

**app/personas/:**
- Purpose: User persona configurations
- Generated: No
- Committed: Yes
- Usage: Templates for user types and roles

**app/Docs/:**
- Purpose: Documentation and guides
- Generated: No
- Committed: Yes
- Usage: Internal documentation and developer guides

**tests/:**
- Purpose: Test suite (unit, integration, load tests)
- Generated: No (written by developers)
- Committed: Yes
- Usage: Run with `make test`, evaluated in CI/CD

**notebooks/:**
- Purpose: Jupyter notebooks for prototyping and evaluation
- Generated: Possibly (from prototyping)
- Committed: Yes (production evaluation notebooks only)
- Usage: Quick iteration before production implementation

**.tmp/:**
- Purpose: Temporary files, caches, pip/uv caches
- Generated: Yes (automatic)
- Committed: No (.gitignore)
- Usage: Development scratch space, ignored in version control

**deployment/:**
- Purpose: Infrastructure as Code (Terraform)
- Generated: No
- Committed: Yes
- Usage: Provision cloud resources (Cloud Run, Supabase, Redis, BigQuery)

---

*Structure analysis: 2026-03-11*

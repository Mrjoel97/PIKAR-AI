# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

Pikar AI is a multi-agent executive system built on Google's Agent Development Kit (ADK) with the A2A Protocol (Agent-to-Agent). It serves as a "Chief of Staff" for business operations, orchestrating specialized agents for various business functions.

## Architecture

### Multi-Agent Hierarchy
```
ExecutiveAgent (Root Orchestrator)
├── FinancialAnalysisAgent
├── ContentCreationAgent
├── StrategicPlanningAgent
├── SalesIntelligenceAgent
├── MarketingAutomationAgent
├── OperationsOptimizationAgent
├── HRRecruitmentAgent
├── ComplianceRiskAgent
├── CustomerSupportAgent
└── DataAnalysisAgent
```

### Key Architectural Decisions
- **Agent Pattern**: All agents extend `PikarAgent` (in `app/agents/base_agent.py`) which wraps ADK's `Agent` class for correct path resolution
- **Singleton vs Factory**: Agents have both singleton instances (for ExecutiveAgent delegation) and factory functions (`create_*_agent`) for workflow pipelines
- **Tool Organization**: Tools are grouped by domain in `app/agents/tools/` and `app/mcp/tools/`
- **Session Persistence**: Uses `SupabaseSessionService` with fallback to `InMemorySessionService`
- **Caching**: Redis with Cache-Aside pattern (user config: 1hr, sessions: 30min, personas: 2hr)

### Core Files
- `app/agent.py` - Executive Agent definition, tool registry, ADK App setup
- `app/fast_api_app.py` - FastAPI server with SSE streaming, A2A integration, health checks
- `app/agents/specialized_agents.py` - Re-exports all specialized agents
- `app/agents/shared.py` - Shared utilities including `get_model()` and `get_fallback_model()`
- `app/persistence/supabase_session_service.py` - Async PostgreSQL session persistence
- `app/services/cache.py` - Redis caching service

## Build & Development Commands

```bash
# Install dependencies (uses uv package manager)
make install

# Launch ADK playground (web UI on port 8501)
make playground

# Run FastAPI backend with hot-reload (port 8000)
make local-backend

# Run unit and integration tests
make test

# Run linting (codespell, ruff, ty)
make lint

# Deploy to Cloud Run
make deploy

# Launch A2A Protocol Inspector (port 5001)
make inspector

# Set up dev environment with Terraform
make setup-dev-env
```

### Docker Development
```bash
# Start backend + redis only (recommended for Windows - run frontend natively)
docker compose up backend redis

# Start with frontend included
docker compose --profile full up
```

### Running Single Tests
```bash
# Run a specific test file
uv run pytest tests/unit/test_agent_factories.py -v

# Run a specific test function
uv run pytest tests/unit/test_agent_factories.py::test_function_name -v

# Run tests matching a pattern
uv run pytest -k "test_financial" -v

# Run integration tests only
uv run pytest tests/integration -v
```

## Environment Configuration

Required environment variables (in `app/.env` or project root `.env`):
- **Vertex AI** (production): `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`
- **Gemini API** (dev fallback): `GOOGLE_API_KEY`
- **Supabase**: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_ANON_KEY`
- **Redis**: `REDIS_HOST`, `REDIS_PORT` (defaults: localhost:6379)

Google credentials file should be placed in `secrets/` directory.

## Code Patterns

### Adding a New Tool
1. Create tool function in appropriate `app/agents/tools/` or `app/mcp/tools/` module
2. Tool functions must return `dict` with at minimum a `status` key
3. Use type hints for all parameters (ADK uses these for function declarations)
4. Add comprehensive docstrings (sent to LLM for tool understanding)
5. Export in the module's `*_TOOLS` list
6. Import and spread into `_EXECUTIVE_TOOLS` in `app/agent.py`

### Adding a New Specialized Agent
1. Create module in `app/agents/<domain>/` (see existing patterns like `app/agents/financial/`)
2. Define instructions, tools list, and create both singleton and factory function
3. Add to `SPECIALIZED_AGENTS` list in `app/agents/specialized_agents.py`
4. ADK automatically enables delegation from ExecutiveAgent to sub-agents

### Creating UI Widgets
Agents can render interactive widgets using tools from `app/agents/tools/ui_widgets.py`. Widget data is extracted from SSE events and rendered in the frontend.

## Testing

### Test Structure
- `tests/unit/` - Unit tests for services and tools
- `tests/integration/` - Integration tests for agents and workflows
- `tests/eval_datasets/` - ADK evaluation datasets (`.evalset.json`)
- `tests/load_test/` - Load testing scripts

### Evaluation
```bash
# Run ADK evaluation on an agent
adk eval app tests/eval_datasets/executive_eval.json
```

## Key Dependencies
- `google-adk>=1.16.0` - Google Agent Development Kit
- `a2a-sdk~=0.3.9` - A2A Protocol SDK
- `fastapi~=0.115.8` - Web framework
- `supabase>=2.27.2` - Database client
- `redis>=5.0.0` - Caching
- `asyncpg>=0.30.0` - Async PostgreSQL driver

## Model Configuration

Models are configured via environment variables:
- `GEMINI_AGENT_MODEL_PRIMARY` - Primary model (default: gemini-2.5-flash or gemini-2.5-pro)
- `GEMINI_AGENT_MODEL_FALLBACK` - Fallback when primary fails

The system automatically retries with fallback model on 404/429 errors.

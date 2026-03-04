# Coding Conventions

**Analysis Date:** 2026-03-04

## Naming Patterns

**Files:**
- Python implementation files use `snake_case.py` (`app/services/financial_service.py`, `app/routers/business_health.py`)
- Python tests use `test_*.py` and are split by scope (`tests/unit/`, `tests/integration/`)
- React components use `PascalCase.tsx` (`frontend/src/components/chat/ChatInterface.tsx`)
- Frontend tests use `*.test.ts` or `*.test.tsx`
- Workflow templates use descriptive `snake_case.yaml` names (`app/workflows/definitions/product_launch.yaml`)

**Functions:**
- Python functions and methods are `snake_case`
- Async function naming does not require special prefixes (standard `async def`)
- Tool functions generally read as action verbs (`get_revenue_stats`, `create_video_with_veo`)

**Variables:**
- Local variables are lowercase snake_case in Python
- Constants are UPPER_SNAKE_CASE (`SESSION_MAX_EVENTS`, `PERSONA_LIMITS`)
- TypeScript locals use camelCase, React components/props use standard TS/React patterns

**Types:**
- Python class names use PascalCase (`FinancialService`, `SupabaseSessionService`)
- Pydantic schemas and DTOs use PascalCase classes
- TypeScript component and type names use PascalCase

## Code Style

**Formatting:**
- Python formatting and linting are Ruff-driven (`pyproject.toml`)
- Python target line length: 88
- Frontend linting uses Next ESLint config (`frontend/eslint.config.mjs`)
- TypeScript strict mode is enabled in frontend (`frontend/tsconfig.json`)

**Linting:**
- Backend lint command path: `uv run ruff check . --diff` and `uv run ruff format . --check --diff`
- Additional backend checks: `ty check`, `codespell`, workflow verification scripts (`Makefile`)
- Pre-commit adds mypy, bandit, docstring coverage, and custom hooks (`.pre-commit-config.yaml`)

## Import Organization

**Order:**
1. Standard library imports
2. Third-party dependencies
3. First-party modules (`app.*` and frontend alias paths)

**Grouping:**
- Python import order enforced by Ruff isort settings (`known-first-party = ["app", "frontend"]`)
- Frontend commonly uses alias imports via `@/*` (configured in `frontend/tsconfig.json`)

**Path Aliases:**
- Frontend alias: `@/* -> frontend/src/*`

## Error Handling

**Patterns:**
- API boundaries use explicit `HTTPException` responses where appropriate
- Global exception handlers registered centrally (`app/middleware/exception_handlers.py`)
- Service and tool layers often return structured dicts with `status`/`success` and error details
- External integration failures usually degrade gracefully rather than crash process startup

**Error Types:**
- Domain-specific exceptions live in `app/exceptions.py`
- Validation and configuration failures are surfaced early at startup unless bypass flags are enabled
- Workflow and connector methods return explicit machine-readable error codes where possible

## Logging

**Framework:**
- Standard Python logging (`logging.getLogger(__name__)`) is used throughout backend modules
- Middleware request logging is centralized in `app/middleware/logging_middleware.py`

**Patterns:**
- Context-rich log messages for integrations, fallbacks, and health checks
- Warning logs for degraded/non-fatal states; error logs for hard failures
- Structured logging helper pattern exists for feedback payload logging in `app/fast_api_app.py`

## Comments

**When to Comment:**
- Modules commonly include top-level docstrings with intent and safety notes
- Non-obvious behavior (fallbacks, security flags, limits) is documented inline
- Comments emphasize why decisions exist (for example strict/permissive auth and readiness gating)

**Docstrings:**
- Public functions and classes are usually documented with args/returns behavior
- Tool functions include descriptive docstrings for LLM tool understanding

**TODO Comments:**
- TODO/FIXME markers exist and highlight active debt (example: argument mapping FIXME in `app/workflows/worker.py`)

## Function Design

**Size:**
- Service methods vary from small helpers to larger orchestration methods
- Complex flows are typically decomposed into helper methods (normalization, metadata shaping, fallback logic)

**Parameters:**
- Backend code uses type hints broadly (including optional and union types)
- Keyword-only parameters are common in service methods for clarity

**Return Values:**
- Tool/service methods commonly return serializable dictionaries for API and agent compatibility
- Financial services normalize outputs into canonical DTO shapes where possible

## Module Design

**Exports:**
- Domain modules expose singleton accessors (`get_*_service`) to centralize client creation
- Agent modules expose singleton instances for delegation and `create_*_agent` factories for fresh workflow contexts

**Barrel/Registry Patterns:**
- Specialized agent re-exports in `app/agents/specialized_agents.py`
- Tool group constants (`*_TOOLS`) are composed into executive tool lists in `app/agent.py`
- Workflow tool name validation routes through registry + template validation helpers

---

*Convention analysis: 2026-03-04*
*Update when patterns change*

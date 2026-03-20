# Coding Conventions

**Analysis Date:** 2026-03-20

## Languages and Stack

**Backend:** Python 3.10+ (async throughout)
**Frontend:** TypeScript (strict mode) with React 19, Next.js 16, Tailwind CSS 4

## Naming Patterns

**Python Files:**
- Use `snake_case.py` for all modules: `financial_service.py`, `cache.py`, `agent_skills.py`
- Agent definition files: `app/agents/<domain>/agent.py`
- Agent tool modules: `app/agents/tools/<tool_name>.py`
- Service classes: `app/services/<service_name>.py`
- Router modules: `app/routers/<domain>.py`

**Python Functions:**
- Use `snake_case` for all functions: `get_revenue_stats`, `create_workflow_template`
- Async functions: same naming, always use `async def`
- Private/internal helpers: prefix with underscore: `_get_calendar_service`, `_parse_dict_kwargs`
- Factory functions: `create_<agent_name>_agent()` pattern for agents

**Python Classes:**
- Use `PascalCase`: `CacheService`, `WorkflowEngine`, `PikarError`
- Service classes: `<Domain>Service` (e.g., `FinancialService`, `CampaignService`, `TaskService`)
- Error classes: `<Domain>Error` (e.g., `DatabaseError`, `CacheError`, `WorkflowError`)
- Pydantic models: `PascalCase` (e.g., `CalendarEvent`, `StartWorkflowRequest`)
- Agent classes: `<Domain>Agent` naming in `name` kwarg (e.g., `"FinancialAnalysisAgent"`)

**Python Variables:**
- Constants: `UPPER_SNAKE_CASE` (e.g., `GEMINI_AGENT_MODEL_PRIMARY`, `TOOL_REGISTRY`, `SPECIALIZED_AGENTS`)
- Tool lists: `<DOMAIN>_TOOLS` (e.g., `CALENDAR_TOOLS`, `GMAIL_TOOLS`, `MEDIA_TOOLS`)
- Config objects: `<PROFILE>_AGENT_CONFIG` (e.g., `FAST_AGENT_CONFIG`, `DEEP_AGENT_CONFIG`)
- Logger: always `logger = logging.getLogger(__name__)` at module level

**TypeScript/React Files:**
- Components: `PascalCase.tsx` (e.g., `ChatInterface.tsx`, `RevenueChart.tsx`, `WidgetRegistry.tsx`)
- Services: `camelCase.ts` (e.g., `api.ts`, `workflows.ts`, `widgetDisplay.ts`)
- Test files: `<Component>.test.tsx` or `<module>.test.ts` co-located with source
- Hooks: `use<Name>.ts` (e.g., `useAgentChat.ts`)

**TypeScript Functions/Variables:**
- Functions: `camelCase` (e.g., `fetchWithAuth`, `getClientPersonaHeader`, `buildHttpError`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `API_BASE_URL`, `MAX_RETRIES`, `RETRYABLE_STATUS_CODES`)
- React components: `PascalCase` function names (e.g., `function SimpleBarChart(...)`)
- Types/Interfaces: `PascalCase` (e.g., `WidgetDefinition`, `RevenueData`, `FetchOptions`)

## Code Style

**Python Formatting:**
- Tool: Ruff (`ruff format`)
- Line length: 88 characters (E501 ignored so longer lines are tolerated)
- Config: `pyproject.toml` under `[tool.ruff]`

**Python Linting:**
- Tool: Ruff (`ruff check`)
- Rules: E, F, W, I, C, B, UP, RUF
- Ignored: E501 (line length), C901 (complexity), B006 (mutable defaults)
- Config: `pyproject.toml` under `[tool.ruff.lint]`

**Python Type Checking:**
- Tool: ty (Astral's Rust-based checker)
- Rules: `unresolved-import` and `unresolved-attribute` set to "ignore" (for dynamic libraries)
- `invalid-argument-type`, `invalid-assignment`, `invalid-return-type` set to "warn"
- Config: `pyproject.toml` under `[tool.ty]`

**TypeScript Linting:**
- Tool: ESLint 9 with `eslint-config-next` (core-web-vitals + typescript)
- Config: `frontend/eslint.config.mjs`

**TypeScript Compilation:**
- Strict mode enabled
- Target: ES2017
- Module resolution: bundler
- Path alias: `@/*` maps to `./src/*`
- Config: `frontend/tsconfig.json`

**Spell Checking:**
- Tool: codespell
- Ignore words: "rouge"
- Skips: lockfiles, `.venv`, `frontend/`, notebooks

## Pre-Commit Hooks

Configured in `.pre-commit-config.yaml`. Key hooks:
- **No bare except clauses** (custom hook at `.pre-commit-hooks/check-bare-except.py`)
- **No print statements** in production code (custom hook at `.pre-commit-hooks/check-print-statements.py`)
- **No mutable default arguments** (custom hook at `.pre-commit-hooks/check-mutable-defaults.py`)
- **Ruff lint + format** on Python files
- **mypy** type checking (excludes tests, migrations, scripts)
- **interrogate** docstring coverage (80%+ required, excludes init/magic/property methods)
- **bandit** security scanning (medium severity, skips B101/B311/B105)
- **hadolint** for Dockerfile linting
- **codespell** for spelling
- **No commit to main/master** branches

## Import Organization

**Python Import Order (enforced by Ruff isort):**
1. Standard library (`import os`, `import logging`, `from typing import ...`)
2. Third-party packages (`from fastapi import ...`, `from pydantic import ...`)
3. First-party (`from app.services.cache import ...`, `from app.agents.tools.registry import ...`)

**Known first-party packages:** `app`, `frontend` (configured in `pyproject.toml` under `[tool.ruff.lint.isort]`)

**Python Import Patterns:**
- Lazy imports inside functions for heavy dependencies:
  ```python
  async def start_workflow(...):
      from app.workflows.engine import get_workflow_engine
      engine = get_workflow_engine()
  ```
- Group related tool imports into lists:
  ```python
  from app.agents.tools.calendar_tool import CALENDAR_TOOLS
  from app.agents.tools.gmail import GMAIL_TOOLS
  ```

**TypeScript Import Order:**
1. Framework imports (`import React from 'react'`, `import { ... } from 'next/...'`)
2. Third-party libraries (`import { fetchEventSource } from '@microsoft/fetch-event-source'`)
3. Internal aliases (`import { ... } from '@/services/api'`, `import { ... } from '@/types/widgets'`)
4. Relative imports (`import { WidgetProps } from './WidgetRegistry'`)

**TypeScript Path Alias:**
- `@/*` maps to `frontend/src/*` (configured in `frontend/tsconfig.json`)

## Error Handling

**Python Exception Hierarchy:**
- All custom exceptions inherit from `PikarError` (defined in `app/exceptions.py`)
- `PikarError` carries: `message`, `code` (ErrorCode enum), `details` (dict), `status_code` (int), `original_exception`
- Domain-specific subclasses: `ValidationError`, `DatabaseError`, `CacheError`, `NotFoundError`, `WorkflowError`, `AgentError`, `SkillError`, `AuthenticationError`, `AuthorizationError`
- Error codes use `PIKAR_<DOMAIN>_<CODE>` convention (e.g., `PIKAR_VALIDATION_ERROR`, `PIKAR_CACHE_CONNECTION_FAILED`)
- HTTP status mapping in `ERROR_CODE_TO_HTTP_STATUS` dict

**Error Code Convention:**
```python
class ErrorCode(Enum):
    VALIDATION_ERROR = "PIKAR_VALIDATION_ERROR"
    DATABASE_ERROR = "PIKAR_DATABASE_ERROR"
    CACHE_CONNECTION_FAILED = "PIKAR_CACHE_CONNECTION_FAILED"
```

**Structured Error Responses:**
- Use `ErrorResponse.from_exception(exception)` for consistent API error responses
- `ValidationErrorResponse` for multi-field validation failures
- Always include `code`, `message`, and optional `details`

**Service Error Patterns:**
- Services return sentinel values on errors (not raise): `None` for get, `False` for set, `0` for count
- Cache operations return `CacheResult` dataclass distinguishing hit/miss/error
- Circuit breaker pattern on Redis via `@with_circuit_breaker` decorator in `app/services/cache.py`

**Tool Error Patterns:**
- Agent tools return error dicts instead of raising: `{"error": "Missing user context"}`
- Wrap exceptions in try/except returning status dicts: `{"status": "success", ...}` or `{"status": "error", ...}`

**Frontend Error Patterns:**
- `buildHttpError(response)` creates Error objects from HTTP responses in `frontend/src/services/api.ts`
- Retry logic with exponential backoff for status codes 408, 429, 500, 502, 503, 504
- AbortController timeout (15s default) on all API calls

## Logging

**Framework:** Python `logging` module (no third-party logging library)

**Logger Declaration:**
```python
import logging
logger = logging.getLogger(__name__)
```

**Patterns:**
- Use `logger.info()` for successful operations and configuration messages
- Use `logger.warning()` for recoverable errors and fallback behavior
- Use `logger.error()` for unrecoverable errors
- Use `logger.debug()` for verbose diagnostic info
- Include context in messages: `logger.warning("CRUD create failed for %s: %s", self.table_name, exc)`
- Never use `print()` in production code (enforced by pre-commit hook)

## Comments and Documentation

**Module Docstrings:**
- Every Python module has a module-level docstring (enforced by interrogate at 80%+)
- Format: Triple-quoted string describing purpose
  ```python
  """Cache service for Pikar AI using Redis.

  This module provides async Redis caching operations with connection pooling,
  user config caching, session caching, and persona caching.
  """
  ```

**Function Docstrings:**
- Google-style docstrings with Args/Returns/Raises sections:
  ```python
  def get_model(model_name: str | None = None) -> Gemini:
      """Get a configured Gemini model instance with retry options.

      Args:
          model_name: Optional model name. If None, uses primary from env.

      Returns:
          A configured Gemini model instance with retry options.
      """
  ```

**Class Docstrings:**
- Describe purpose and usage, include Attributes section for important fields

**TypeScript Comments:**
- JSDoc-style block comments for components:
  ```typescript
  /**
   * Revenue Chart Widget
   *
   * Displays revenue metrics with visual indicators and period selection.
   */
  ```

**Section Separators:**
- Use comment blocks with `=` separators for major sections in Python:
  ```python
  # =============================================================================
  # Performance-tuned GenerateContentConfig profiles
  # =============================================================================
  ```

## Function Design

**Async Pattern:**
- All service methods are `async def` (full async Python with asyncpg, aioredis)
- Agent tools are `async def` because ADK runs inside an async event loop
- Use `from __future__ import annotations` at top of async-heavy modules
- Wrap sync Supabase calls with `execute_async()` from `app/services/supabase_async.py`

**Parameters:**
- Use type hints for all parameters and return types
- Use `str | None` (modern union syntax, Python 3.10+) instead of `Optional[str]`
- Use default parameter values: `period: str = "current_month"`
- Use keyword-only arguments with `*` where appropriate

**Return Values:**
- Services return `dict` (not Pydantic models) for flexibility
- Agent tools return `Dict[str, Any]` with status fields
- Use `CacheResult` dataclass for cache operations (distinguishes hit/miss/error)

## Module Design

**Exports:**
- Use `__all__` lists in modules that serve as public APIs: `app/exceptions.py`, `app/agents/specialized_agents.py`
- Tool modules export uppercase constant lists: `CALENDAR_TOOLS = [list_events, create_event, ...]`

**Barrel Files / Re-exports:**
- `app/agents/specialized_agents.py` re-exports all agents for backward compatibility
- `app/config/settings.py` re-exports from `app/config/validation.py`
- Prefer direct imports for new code: `from app.agents.financial import create_financial_agent`

**Service Initialization:**
- Services initialize Supabase client lazily via `@property` or in constructor
- Use `get_service_client()` singleton for service-role access
- Use `BaseService(user_token=...)` for RLS-scoped user access

**Singleton Patterns:**
- `get_workflow_engine()` returns singleton WorkflowEngine
- `get_agent_kernel()` returns shared kernel
- `CacheService` uses connection pooling

**Configuration:**
- Environment variables via `os.getenv()` with defaults
- Pydantic BaseSettings for structured config (`app/config/validation.py`)
- Agent model configs as module-level constants in `app/agents/shared.py`

## Frontend Component Conventions

**Component Declaration:**
- Use `'use client'` directive at top of client components
- Function components (no class components)
- Named exports for components imported elsewhere; default exports for page components

**Styling:**
- Tailwind CSS 4 utility classes inline
- Dark mode support via `dark:` prefix
- Color palette: slate, indigo, emerald, red tones

**State Management:**
- React hooks (`useState`, `useEffect`) for local state
- Custom hooks in `frontend/src/hooks/` for shared logic
- Supabase realtime for server state

---

*Convention analysis: 2026-03-20*

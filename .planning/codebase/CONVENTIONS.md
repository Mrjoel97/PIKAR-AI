# Coding Conventions

**Analysis Date:** 2026-03-11

## Naming Patterns

**Files:**
- Python modules: lowercase with underscores (`financial_service.py`, `cache_service.py`)
- TypeScript components: PascalCase for React components (`ChatInterface.tsx`, `MessageItem.tsx`)
- TypeScript files: camelCase for utilities and services (`useAgentChat.ts`, `chatMetadata.ts`)
- Test files: `test_<name>.py` or `<name>.test.ts` prefix/suffix pattern

**Functions:**
- Python: snake_case (`get_revenue_stats`, `validate_startup`, `create_service_client`)
- TypeScript: camelCase (`fetchEventSource`, `extractMessageMetadata`, `dispatchFocusWidget`)
- Async functions: same pattern with `async` keyword prefix

**Variables:**
- Python: snake_case for module-level and local variables (`user_token`, `start_date`, `is_streaming`)
- TypeScript: camelCase (`isStreaming`, `sessionId`, `customAgentName`)
- Constants: UPPER_SNAKE_CASE (`ROUTING_AGENT_CONFIG`, `TOOL_REGISTRY`)
- React hooks: always prefix with `use` (`useAgentChat`, `useFileUpload`, `useTextToSpeech`)

**Types:**
- Python: PascalCase for classes and enums (`UserProfile`, `ErrorCode`, `CacheResult`, `DirectorService`)
- TypeScript: PascalCase for interfaces, types, and classes (`Message`, `ChatInterfaceProps`, `AgentMode`)
- Type unions: descriptive names (`'user' | 'agent' | 'system'`)

**Pydantic Models:**
- Inherit from `BaseModel` and use `Field()` for documentation
- Example: `class UserProfile(BaseModel)` with `Field(default_factory=...)` for defaults

## Code Style

**Formatting:**
- **Python:** Line length 88 (configured via `ruff` in `pyproject.toml`)
- **TypeScript:** Line length 100 (implicit via ESLint config)
- **Indentation:** 2 spaces for TypeScript/JavaScript, 4 spaces for Python

**Linting:**
- **Python Tool:** `ruff` (version >=0.4.6)
  - Selected rules: E (pycodestyle), F (pyflakes), W (warnings), I (isort), C (comprehensions), B (bugbear), UP (pyupgrade), RUF (ruff-specific)
  - Ignored rules: E501 (line too long), C901 (too complex), B006 (mutable default arguments)
  - Target Python version: 3.10

- **TypeScript Tool:** ESLint (version ^9) with `eslint-config-next`
  - Rules: Next.js core web vitals + TypeScript-specific rules
  - Strict mode enabled in `tsconfig.json`

- **Type Checking (Python):** `ty` (Astral's Rust-based type checker)
  - Rules: unresolved-import and unresolved-attribute set to "ignore" (common with dynamic libraries)
  - Enabled checks: invalid-argument-type, invalid-assignment, invalid-return-type (as warnings)

**Documentation:**
- **Python:** Use docstrings with triple quotes (`"""..."""`) at module, class, and function level
  - Include parameter descriptions and return type documentation
  - Example:
    ```python
    def get_revenue_stats(self, period: str = "current_month") -> dict:
        """Fetch revenue statistics from the database for the specified period.

        Queries the financial_records table and aggregates revenue data based
        on the period parameter. Falls back to 0 if no data exists.

        Args:
            period: Time period for stats - 'current_month', 'last_month', etc.

        Returns:
            Dictionary with revenue, currency, period, transaction count, and status.
        """
    ```

- **TypeScript:** Use JSDoc-style comments for complex logic
  - Include type annotations in function signatures (no need for JSDoc if types are explicit)
  - Example:
    ```typescript
    /**
     * Chat message representing user input, agent response, or system notification.
     * Messages can optionally contain a widget for interactive UI display.
     */
    export type Message = {
      id?: string;
      role: 'user' | 'agent' | 'system';
      text?: string;
    };
    ```

## Import Organization

**Order:**

1. **Standard library imports** (Python only)
   - `import os`, `import sys`, `import logging`, `import asyncio`

2. **Third-party imports**
   - External packages: `import redis`, `from fastapi import FastAPI`
   - Google Cloud/ADK: `from google.adk.agents import Agent`

3. **Local/relative imports**
   - `from app.services import CacheService`
   - `from app.exceptions import ValidationError`

**Path Aliases:**
- **Python:** Known first-party packages in `ruff.lint.isort` config: `["app", "frontend"]`
- **TypeScript:** `"@/*": ["./src/*"]` (defined in `tsconfig.json` and Vitest config)
  - Usage: `import { Message } from '@/types/widgets'`

**Examples:**
```python
# Python import ordering
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from google.adk.agents import Agent
from pydantic import BaseModel, Field
import redis.asyncio as redis

from app.services.base_service import BaseService
from app.exceptions import ValidationError, CacheError
```

```typescript
// TypeScript import ordering
import { useState, useCallback, useRef } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { createClient } from '@supabase/supabase-js';

import { extractMessageMetadata } from '@/lib/chatMetadata';
import { WidgetDisplayService } from '@/services/widgetDisplay';
import type { Message, AgentMode } from '@/types/widgets';
```

## Error Handling

**Patterns:**

1. **Python: Custom Exception Hierarchy**
   - Base class: `PikarError` (all custom exceptions inherit from this)
   - Category-specific subclasses: `ValidationError`, `DatabaseError`, `CacheError`, `WorkflowError`, `AgentError`, `SkillError`
   - Specialized variants: `CacheConnectionError`, `DatabaseQueryError`, `NotFoundError`, `ConflictError`
   - Location: `app/exceptions.py`
   - Usage:
     ```python
     raise ValidationError(
         message="Invalid input",
         details={"field": "email", "reason": "invalid_format"}
     )
     ```

2. **Error Codes and HTTP Status Mapping**
   - Error codes format: `PIKAR_{DOMAIN}_{CODE}` (e.g., `PIKAR_VALIDATION_ERROR`)
   - HTTP status mapping defined in `ERROR_CODE_TO_HTTP_STATUS` dict
   - Example: `ValidationError` → 400, `CacheConnectionError` → 503, `NotFoundError` → 404

3. **Error Response Models**
   - `ErrorResponse`: Structured error response with code, message, details, request_id, timestamp
   - `ValidationErrorResponse`: Specialized for validation with list of `ErrorDetail` objects
   - Used in FastAPI exception handlers for consistent API error format

4. **Try-Catch with Logging**
   - Log at appropriate level: `logger.error()` for critical errors, `logger.warning()` for recoverable issues
   - Include context in error messages (user ID, resource ID, operation type)
   - Example:
     ```python
     try:
         result = await cache.get(key)
     except CacheConnectionError as e:
         logger.warning(f"Cache unavailable for {key}: {e}")
         # Fall back to database
         return await database.get(key)
     except Exception as e:
         logger.error(f"Unexpected cache error: {e}", exc_info=True)
         raise
     ```

5. **TypeScript: Error Handling**
   - Use try-catch blocks for async operations
   - Throw `Error` with descriptive messages
   - No custom error hierarchy in TypeScript currently
   - Example from `useAgentChat.ts`:
     ```typescript
     try {
       const response = await fetch('/api/chat', { ... });
       if (!response.ok) throw new Error(`HTTP ${response.status}`);
     } catch (error) {
       setError(error.message);
     }
     ```

## Logging

**Framework:**
- **Python:** `logging` module (standard library) with logger instances per module
  - Logger name pattern: `logger = logging.getLogger(__name__)`
  - Configured via `logging.basicConfig()` in `fast_api_app.py`

- **TypeScript:** `console` API for development, structured logging frameworks not currently in use

**Patterns:**

1. **Python Logging Levels:**
   - `logger.debug()`: Detailed diagnostic info during development
   - `logger.info()`: Informational messages for key operations (service startup, successful completions)
   - `logger.warning()`: Recoverable issues (cache miss, fallback to alternative service)
   - `logger.error()`: Error conditions that should be logged but might be handled
   - Include `exc_info=True` when logging exceptions: `logger.error("Operation failed", exc_info=True)`

2. **When to Log:**
   - Service initialization and shutdown
   - Configuration validation (especially in `fast_api_app.py`: "Vertex AI mode enabled", "Environment validation failed")
   - External service calls (cache operations, database queries)
   - Error conditions and fallback behavior
   - Request/response lifecycle (in routers and middleware)

3. **Examples:**
   ```python
   logger.info(f"Vertex AI mode enabled using service account credentials. Project: {has_cloud_project}")
   logger.warning(f"Redis connection error in {func.__name__}: {e}")
   logger.error(f"Environment validation failed: {e}")
   ```

## Comments

**When to Comment:**
- Explain **why**, not **what** (code should be self-documenting for what)
- Non-obvious algorithms or business logic
- Workarounds for known issues or external API quirks
- Complex conditional logic
- References to external documentation or issues

**What NOT to Comment:**
- Self-explanatory variable assignments
- Obvious loop or conditional logic
- Method names that clearly describe their purpose

**JSDoc/TSDoc:**
- Use for public API surfaces in both Python and TypeScript
- Required for: exported functions, classes, interfaces, type definitions
- Optional for: internal implementation details, private methods
- Format: Standard JSDoc for TypeScript, docstrings for Python (as shown above)

**Examples:**
```python
# Good: Explains the "why"
# ADK uses inspect.getfile() on the Agent class to determine app_name.
# By subclassing Agent here, the class definition is in the user's project,
# allowing ADK to correctly infer the app name from the directory.
class PikarAgent(BaseAgent):
    pass

# Avoid: Just repeats what the code does
# Get the user
user = await get_user(user_id)  # Not helpful
```

## Function Design

**Size:**
- Keep functions focused on a single responsibility
- Prefer functions under 50 lines when practical
- Complex business logic may span longer if coherent

**Parameters:**
- Use type hints in all functions (Python and TypeScript)
- Prefer positional arguments for required parameters, keyword arguments for optional
- Use `Optional[Type]` for nullable parameters in Python
- Default values for commonly used optional parameters

**Return Values:**
- Always specify return type (Python type hints, TypeScript return type annotations)
- Prefer returning concrete values over `None` when possible (use empty collections instead)
- For errors, use exceptions (not error codes in return values)
- Example patterns:
  ```python
  async def get_revenue_stats(self, period: str = "current_month") -> dict:
      # Returns dict, not Optional[dict] - fails with exception if error
  ```

## Module Design

**Exports:**
- Use `__all__` in Python modules to define public API
- Export classes, functions, and constants meant for external use
- Prefix internal helpers with `_` (single underscore)
- Example from `exceptions.py`:
  ```python
  __all__ = [
      "ErrorCode",
      "PikarError",
      "ValidationError",
      "DatabaseError",
      # ... etc
  ]
  ```

**Barrel Files:**
- **Python:** Use `__init__.py` to re-export from submodules:
  ```python
  # app/services/__init__.py
  from app.services.cache import CacheService
  from app.services.financial_service import FinancialService
  __all__ = ["CacheService", "FinancialService"]
  ```
- **TypeScript:** Create index files with named exports, but avoid deeply nested re-exports

**Service Pattern:**
- Services handle business logic and external interactions
- Inherit from base classes when provided (`BaseService`)
- Constructor accepts configuration and dependencies
- Methods are async when they perform I/O
- Use Singleton pattern for services that manage shared state (e.g., `CacheService`)

**Example Service Structure:**
```python
class FinancialService(BaseService):
    """Service for financial data operations."""

    def __init__(self, user_token: Optional[str] = None):
        super().__init__(user_token)

    async def get_revenue_stats(self, period: str = "current_month") -> dict:
        """Docstring..."""
        try:
            # Implementation
        except Exception as e:
            logger.error(f"Error: {e}")
            raise ValidationError(...)
```

---

*Convention analysis: 2026-03-11*

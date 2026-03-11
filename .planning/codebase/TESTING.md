# Testing Patterns

**Analysis Date:** 2026-03-11

## Test Framework

**Runner:**
- **Python:** pytest (version >=8.3.4, <9.0.0)
- **TypeScript:** vitest (version ^4.0.18)

**Config Files:**
- Python: `pyproject.toml` ([tool.pytest.ini_options])
- TypeScript: `frontend/vitest.config.mts`

**Assertion Library:**
- **Python:** pytest's built-in assertion syntax (no separate library required)
- **TypeScript:** vitest assertions (compatible with Jest)

**Run Commands:**

```bash
# Python - all tests
pytest

# Python - watch mode (not standard in pytest, use pytest-watch if needed)
pytest --watch

# Python - coverage
pytest --cov=app --cov-report=html

# TypeScript - all tests
npm test

# TypeScript - watch mode
npm test -- --watch

# TypeScript - coverage
npm test -- --coverage
```

## Test File Organization

**Location:**
- **Python:** Co-located with source code OR in centralized `tests/` directory
  - `tests/unit/` for unit tests
  - `tests/integration/` for integration tests
  - `tests/load_test/` for load/performance tests
  - Subdirectories mirror app structure: `tests/unit/app/routers/`, `tests/unit/app/agents/`

- **TypeScript:** `frontend/src/__tests__/` (co-located with source)
  - Or alongside source files: `__tests__/` subdirectories

**Naming:**
- **Python:** `test_<module_name>.py` (e.g., `test_cache_service.py`, `test_director_service.py`)
- **TypeScript:** `<module>.test.ts` or `<module>.spec.ts`

**Directory Structure:**

```
tests/
├── unit/
│   ├── conftest.py                           # Pytest fixtures and mocks
│   ├── test_smoke.py                         # Import and basic functionality tests
│   ├── test_error_handling.py
│   ├── test_cache_service.py
│   ├── app/
│   │   ├── routers/
│   │   │   └── test_initiatives.py
│   │   └── agents/
│   │       └── strategic/
│   │           └── test_tools.py
├── integration/
│   └── (integration test files)
├── eval_datasets/
│   └── (evaluation dataset tests)
└── load_test/
    └── (load/performance tests, ignored by default)

frontend/src/__tests__/
└── (TypeScript test files)
```

## Test Structure

**Suite Organization:**

**Python Example:**
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

class TestDirectorService:
    """Group related tests for DirectorService."""

    @pytest.fixture
    def director(self):
        """Fixture providing a DirectorService instance."""
        with patch("app.services.director_service.get_service_client", return_value=_SupabaseStub()):
            return DirectorService()

    def test_clamp_scene_duration(self):
        """Test scene duration clamping logic."""
        assert _clamp_scene_duration(None) == 4
        assert _clamp_scene_duration(5) == 6

    @pytest.mark.asyncio
    async def test_create_pro_video_sets_duration_frames(self, director):
        """Test that video creation sets correct duration."""
        storyboard_mock = AsyncMock(return_value={"scenes": [...]})
        with patch.object(director, "_generate_storyboard", storyboard_mock):
            # Test implementation
            pass
```

**TypeScript Example (similar structure with Vitest):**
```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('MessageItem Component', () => {
  let props;

  beforeEach(() => {
    props = { /* setup */ };
  });

  it('renders user message', () => {
    // Test implementation
  });

  it('handles widget display', async () => {
    // Async test
  });
});
```

**Patterns:**

- **Setup pattern:** Use `@pytest.fixture` (Python) or `beforeEach` (TypeScript) for test initialization
- **Teardown pattern:** Fixtures with `yield` (Python), `afterEach` hooks (TypeScript)
- **Assertion pattern:** Clear, single assertion per test preferred; group related assertions only when testing complex state

## Mocking

**Framework:**
- **Python:** `unittest.mock` (standard library)
- **TypeScript:** vitest's built-in mocking (`vi.mock()`, `vi.fn()`)

**Patterns:**

**Python Mocking Examples:**

```python
from unittest.mock import AsyncMock, MagicMock, patch

# Mock a service dependency
@pytest.fixture
def director(self):
    with patch("app.services.director_service.get_service_client", return_value=_SupabaseStub()):
        return DirectorService()

# Create a stub class for complex objects
class _SupabaseStub:
    storage = _StorageStub()  # Nested mocks

# Async mock
storyboard_mock = AsyncMock(return_value={"scenes": [...]})

# Patch methods on instances
with patch.object(director, "_generate_storyboard", storyboard_mock):
    # Test code
    pass

# Verify mock was called
storyboard_mock.assert_called_once_with(expected_arg)
```

**TypeScript Mocking Examples:**

```typescript
import { vi } from 'vitest';

// Mock a module
vi.mock('@/lib/supabase/client', () => ({
  createClient: vi.fn(() => mockSupabaseClient)
}));

// Create a spy
const fetchSpy = vi.spyOn(global, 'fetch');

// Verify call
expect(fetchSpy).toHaveBeenCalledWith('/api/endpoint');
```

## What to Mock

**Mock these:**
- External service calls (Supabase, Redis, API endpoints)
- File system operations
- Time-dependent operations (`datetime.now()`, `setTimeout`)
- Heavy computations or network calls
- Third-party library calls that are hard to set up

**Don't mock these:**
- Core application logic
- Internal method calls between related components
- Simple utility functions
- Database queries in integration tests (may use test database instead)

**Example from conftest.py:**
```python
# Mock heavy Google ADK dependencies
mock_adk_agents.Agent = MockAgent  # Custom lightweight mock
mock_adk_models.Gemini = MagicMock()  # Lazy mock

# But allow real imports of google.cloud for mixed test runs
google_pkg = sys.modules.get("google")  # Preserve google.cloud imports
```

## Fixtures and Factories

**Test Data:**

**Python Fixture Pattern:**
```python
@pytest.fixture
def director():
    """Fixture that provides a DirectorService with mocked dependencies."""
    with patch("app.services.director_service.get_service_client", ...):
        return DirectorService()

@pytest.fixture
async def cache_service():
    """Async fixture for CacheService."""
    service = CacheService()
    yield service
    await service.cleanup()  # Teardown
```

**Stub Objects Pattern:**
```python
class _StorageBucketStub:
    """Stub for Supabase storage operations."""
    def upload(self, *args, **kwargs):
        return {"ok": True}

    def get_public_url(self, path: str):
        return f"https://example.com/{path}"
```

**Location:**
- Fixtures: In `conftest.py` (pytest auto-discovers and makes available to all tests in directory)
- Factory classes: In test files or separate `factories.py` in test directory

**conftest.py Structure:**
- Global mocks (external libraries)
- Shared fixtures (database, cache service)
- Mock setup for all tests (`pytest_configure` hook in `tests/unit/conftest.py`)

## Coverage

**Requirements:**
- No coverage target enforced (not enforced in pytest config)
- Coverage report generation supported via `pytest-cov` (available in dev dependencies)

**View Coverage:**

```bash
# Python: Generate HTML coverage report
pytest --cov=app --cov-report=html

# Open report
open htmlcov/index.html

# Terminal report
pytest --cov=app --cov-report=term-missing
```

## Test Types

**Unit Tests:**
- **Scope:** Single function, method, or class in isolation
- **Approach:** Mock all external dependencies
- **Location:** `tests/unit/`
- **Example:** `tests/unit/test_cache_service.py` - tests CacheService methods with mocked Redis
- **Characteristics:** Fast (milliseconds), deterministic, no I/O

**Integration Tests:**
- **Scope:** Multiple components working together
- **Approach:** Use real or test instances of external services when possible
- **Location:** `tests/integration/`
- **Example:** Test workflow execution with real database (or test database)
- **Characteristics:** Slower (seconds), may depend on external resources

**E2E Tests:**
- **Framework:** Not yet implemented (no `cypress`, `playwright`, or similar in devDependencies)
- **Could be added:** TypeScript/browser testing would use `playwright` or `cypress`
- **Scope:** Full user workflows through UI and API

**Smoke Tests:**
- **Purpose:** Verify critical system components can start and import
- **Location:** `tests/unit/test_smoke.py`
- **Examples:**
  ```python
  def test_core_modules_importable(self):
      """Verify core application modules can be imported without errors."""
      from app.agent import ExecutiveAgent
      from app.fast_api_app import app
      from app.workflows.engine import WorkflowEngine
  ```

## Common Patterns

**Async Testing:**

```python
import pytest

@pytest.mark.asyncio
async def test_cache_get_operation(cache_service):
    """Test async cache get operation."""
    # Mock setup
    cache_service.get = AsyncMock(return_value={"key": "value"})

    # Call async function
    result = await cache_service.get("my_key")

    # Assert
    assert result["key"] == "value"
```

**Error Testing:**

```python
def test_validation_error_on_invalid_input():
    """Test that validation error is raised for invalid input."""
    with pytest.raises(ValidationError) as exc_info:
        validate_user_input(invalid_data)

    # Verify error details
    assert exc_info.value.code == ErrorCode.INVALID_INPUT
    assert exc_info.value.details["field"] == "email"

def test_database_error_fallback():
    """Test fallback behavior when database operation fails."""
    service = FinancialService()
    with patch.object(service, 'database') as mock_db:
        mock_db.query.side_effect = DatabaseError("Connection failed")

        # Should fall back gracefully
        result = service.get_data()
        assert result == default_value
```

**Parametrized Testing:**

```python
import pytest

@pytest.mark.parametrize("scene_duration,expected", [
    (None, 4),
    (1, 4),
    (5, 6),
    (9, 8),
])
def test_clamp_scene_duration(scene_duration, expected):
    """Test scene duration clamping with multiple inputs."""
    assert _clamp_scene_duration(scene_duration) == expected
```

**Class-based Test Organization:**

```python
class TestDirectorService:
    """Group all DirectorService tests together."""

    @pytest.fixture
    def director(self):
        """Shared setup for all tests in this class."""
        return DirectorService()

    def test_method_one(self, director):
        """Test first behavior."""
        pass

    def test_method_two(self, director):
        """Test second behavior."""
        pass
```

## Test Execution Configuration

**Pytest Options (pyproject.toml):**
```toml
[tool.pytest.ini_options]
addopts = "--ignore=tests/load_test"  # Ignore load tests by default
filterwarnings = [
    "ignore:'enablePackrat' deprecated...",  # Suppress known warnings
]
```

**Vitest Config:**
```typescript
export default defineConfig({
  test: {
    environment: 'jsdom',  // Use jsdom for DOM testing
    globals: true,          // Global test functions (describe, it, etc)
  },
})
```

## Test Dependencies

**Available in pyproject.toml [dependency-groups.dev]:**
- `pytest>=8.3.4` - Test runner
- `pytest-asyncio>=0.23.8` - Async test support
- `nest-asyncio>=1.6.0` - Nested async event loop handling
- `pytest-cov>=5.0.0` - Coverage reporting

**Available in frontend package.json [devDependencies]:**
- `vitest@^4.0.18` - Test runner
- `@testing-library/react@^16.3.2` - React component testing
- `@testing-library/dom@^10.4.1` - DOM testing utilities
- `jsdom@^27.4.0` - JavaScript DOM implementation for testing

---

*Testing analysis: 2026-03-11*

# Testing Patterns

**Analysis Date:** 2026-03-20

## Test Frameworks

### Python (Backend)

**Runner:**
- pytest 8.x
- pytest-asyncio for async tests
- pytest-cov for coverage
- Config: `pyproject.toml` under `[tool.pytest.ini_options]`

**Run Commands:**
```bash
make test                                           # Full suite: workflow validation + unit + integration
uv run pytest tests/unit                            # Unit tests only
uv run pytest tests/integration                     # Integration tests only
uv run pytest tests/unit/test_cache_service.py      # Single file
uv run pytest tests/unit/test_cache_service.py -k "test_name"  # Single test
```

### TypeScript (Frontend)

**Runner:**
- Vitest 4.x with jsdom environment
- @testing-library/react 16.x for component testing
- @testing-library/dom 10.x
- Config: `frontend/vitest.config.mts`

**Run Commands:**
```bash
cd frontend && npm test                             # Run all frontend tests
cd frontend && npm test -- --watch                  # Watch mode
```

**Custom Runner:**
- `frontend/scripts/run-vitest.mjs` provides a custom Vitest runner
- Handles Windows esbuild path resolution
- Ensures correct working directory
- Configured as `"test": "node ./scripts/run-vitest.mjs"` in `frontend/package.json`

## Test File Organization

### Python Tests

**Location:** Separate `tests/` directory at project root

**Structure:**
```
tests/
├── unit/                                    # Isolated tests with mocked dependencies
│   ├── conftest.py                          # ADK/GenAI mock setup (critical)
│   ├── app/
│   │   ├── agents/strategic/test_tools.py   # Nested by source path
│   │   └── routers/test_initiatives.py
│   ├── test_agent_factories.py              # Flat files for most tests
│   ├── test_campaign_service.py
│   ├── test_error_handling.py
│   ├── test_workflow_engine_validation.py
│   └── ... (~100 test files)
├── integration/                             # Tests requiring FastAPI TestClient
│   ├── conftest.py                          # Env var setup for test isolation
│   ├── test_a2a_protocol.py
│   ├── test_sse_endpoint.py
│   └── ... (~35 test files)
├── load_test/                               # Load tests (excluded from default run)
│   └── load_test.py
├── skills/custom/                           # Skill-specific tests
│   └── test_test_math_skill.py
├── test_cache_integration.py                # Root-level tests (legacy)
├── test_cache_service.py
└── test_mcp_live_apis.py
```

**Naming:**
- Test files: `test_<module_or_feature>.py`
- Test classes: `Test<Feature>` (e.g., `TestCacheErrorHandling`, `TestAgentFactoryFunctions`)
- Test functions: `test_<what_is_tested>` (e.g., `test_cache_miss_returns_miss_result`)

### TypeScript Tests

**Location:** Mixed -- co-located with source AND in `__tests__/` directories

**Structure:**
```
frontend/
├── __tests__/                               # Root-level integration tests
│   ├── auth.test.ts
│   ├── components/
│   │   ├── AuthForms.test.tsx
│   │   └── ProtectedRoute.test.tsx
│   ├── hooks/
│   │   └── useAgentChat.test.ts
│   └── pages/
│       ├── LoginPage.test.tsx
│       └── SettingsPage.test.tsx
├── src/
│   ├── __tests__/                           # Service-level tests
│   │   ├── services/api.test.ts
│   │   └── services/workflows.executions.test.ts
│   ├── components/
│   │   ├── chat/ChatInterface.test.tsx      # Co-located with component
│   │   ├── widgets/RevenueChart.test.tsx
│   │   └── workflows/automationUtils.test.ts
│   ├── lib/chatMetadata.test.ts             # Co-located with lib
│   └── services/widgetDisplay.test.ts       # Co-located with service
```

**Naming:**
- Test files: `<Component>.test.tsx` or `<module>.test.ts`
- Test suites: `describe('<ComponentName>', ...)` or `describe('<module> <context>', ...)`
- Test cases: `it('describes expected behavior', ...)`

## Python Test Structure

### Unit Test Conftest (Critical)

The unit test conftest at `tests/unit/conftest.py` mocks the entire Google ADK/GenAI module hierarchy before any test imports. This is essential because:
- ADK requires Google Cloud credentials at import time
- Unit tests must run without any external dependencies

**Mock hierarchy:**
```python
# In pytest_configure() hook:
sys.modules["google.adk"] = mock_adk
sys.modules["google.adk.agents"] = mock_adk_agents
sys.modules["google.adk.runners"] = mock_adk_runners
sys.modules["google.adk.sessions"] = mock_adk_sessions
sys.modules["google.genai"] = mock_genai
sys.modules["vertexai"] = MagicMock()
# ... 20+ mocked modules
```

**MockAgent class** captures constructor kwargs as attributes for assertion:
```python
class MockAgent:
    def __init__(self, **kwargs):
        self.name = kwargs.get("name", "MockAgent")
        self.model = kwargs.get("model", "mock-model")
        self.tools = kwargs.get("tools", [])
        # ...
```

### Integration Test Conftest

The integration conftest at `tests/integration/conftest.py` sets environment variables:
```python
os.environ.setdefault("LOCAL_DEV_BYPASS", "1")
os.environ.setdefault("SKIP_ENV_VALIDATION", "1")
os.environ.setdefault("ENVIRONMENT", "test")
```

### Suite Organization Patterns

**Pattern 1: Test class with fixtures (preferred for services):**
```python
class TestCampaignService:
    """Test suite for CampaignService."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client."""
        mock_client = MagicMock()
        return mock_client

    @pytest.fixture
    def service(self, mock_supabase_client):
        """Create CampaignService with mocked dependencies."""
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_ROLE_KEY': 'test-key'
        }):
            with patch('app.services.campaign_service.create_client') as mock_create:
                mock_create.return_value = mock_supabase_client
                from app.services.campaign_service import CampaignService
                return CampaignService()

    @pytest.mark.asyncio
    async def test_create_campaign(self, service, mock_supabase_client):
        # ... test body
```

**Pattern 2: Module-level functions with decorators (for simpler tests):**
```python
@patch("app.services.task_service.create_client")
@patch.dict("os.environ", {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_ROLE_KEY": "test"})
@pytest.mark.asyncio
async def test_create_task(mock_create_client):
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    # ... Setup, Act, Assert
```

**Pattern 3: Parametrized tests (for repeated patterns):**
```python
@pytest.mark.parametrize("factory_name,expected_agent_name", AGENT_FACTORIES)
def test_factory_creates_agent_with_correct_name(self, factory_name, expected_agent_name):
    from app.agents import specialized_agents
    factory_fn = getattr(specialized_agents, factory_name)
    agent = factory_fn()
    assert agent.name == expected_agent_name
```

**Pattern 4: Pure function tests (for validators/contracts):**
```python
def test_validate_template_phases_accepts_valid_schema():
    phases = [{"name": "Plan", "steps": [_strict_step("create_task")]}]
    errors = validate_template_phases(phases, {"create_task", "mcp_web_search"})
    assert errors == []
```

## Mocking

### Python Mocking

**Framework:** `unittest.mock` (MagicMock, AsyncMock, patch)

**Supabase Client Mocking (most common pattern):**
```python
@pytest.fixture
def mock_supabase_client(self):
    mock_client = MagicMock()
    return mock_client

# Mock the Supabase chain: table().insert().execute()
mock_table = MagicMock()
mock_insert = MagicMock()
mock_execute = MagicMock()
mock_client.table.return_value = mock_table
mock_table.insert.return_value = mock_insert
mock_insert.execute.return_value = mock_execute
mock_execute.data = [{"id": "123", "status": "pending"}]
```

**Environment Variable Mocking:**
```python
with patch.dict('os.environ', {'SUPABASE_URL': 'http://test', 'SUPABASE_SERVICE_ROLE_KEY': 'test'}):
    # test code
```

**Module-level Patching:**
```python
@patch("app.services.task_service.create_client")
def test_something(mock_create_client):
    mock_create_client.return_value = MagicMock()
```

**Async Mocking:**
```python
mock_redis = AsyncMock()
mock_redis.get = AsyncMock(return_value=None)
service._redis = mock_redis
```

**monkeypatch for Integration Tests:**
```python
def test_something(monkeypatch):
    monkeypatch.setenv('LOCAL_DEV_BYPASS', '1')
    monkeypatch.delenv('SUPABASE_JWT_SECRET', raising=False)
    monkeypatch.setattr(jwt_module, 'decode', fake_decode)
```

### TypeScript Mocking

**Framework:** Vitest (`vi.mock`, `vi.fn`, `vi.mocked`)

**Module Mocking:**
```typescript
vi.mock('@/lib/supabase/client', () => ({
  createClient: vi.fn(() => ({
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'mock-token' } }
      })
    }
  }))
}))
```

**Component Mocking (lazy-loaded):**
```typescript
vi.mock('./InitiativeDashboard', () => ({
    default: ({ definition }: { definition: { title?: string } }) => (
        <div data-testid="initiative-dashboard">Initiative Dashboard: {definition.title}</div>
    )
}))
```

**Hook Mocking:**
```typescript
vi.mock('@/hooks/useAgentChat', () => ({
  useAgentChat: vi.fn()
}))

// In test:
vi.mocked(useAgentChat).mockReturnValue({
    messages: mockMessages,
    sendMessage: mockSendMessage,
    isStreaming: false,
    // ...
})
```

**Global Stubbing:**
```typescript
vi.stubGlobal('fetch', fetchSpy)
// Cleanup:
vi.unstubAllGlobals()
```

**What to Mock:**
- External services (Supabase, Redis, Google APIs)
- Environment variables
- Heavy framework imports (ADK, GenAI)
- Browser APIs not available in jsdom (scrollIntoView)
- Fetch calls and SSE event sources

**What NOT to Mock:**
- The code under test itself
- Pure business logic functions
- Pydantic model validation
- Data transformation functions

## Fixtures and Factories

### Python Test Data Patterns

**Inline fixtures via pytest fixtures:**
```python
@pytest.fixture
def service(self, mock_supabase_client):
    """Create service with mocked dependencies."""
    with patch.dict('os.environ', {...}):
        with patch('app.services.campaign_service.create_client') as mock:
            mock.return_value = mock_supabase_client
            from app.services.campaign_service import CampaignService
            return CampaignService()
```

**Factory data constants:**
```python
AGENT_FACTORIES = [
    ("create_financial_agent", "FinancialAnalysisAgent"),
    ("create_content_agent", "ContentCreationAgent"),
    # ... parametrize data
]
```

**Helper functions for test data:**
```python
def _strict_step(tool: str, *, risk_level: str = "medium", required_approval: bool = False):
    return {
        "name": "Step",
        "tool": tool,
        "required_approval": required_approval,
        # ...
    }
```

**Request builders for integration tests:**
```python
def _build_request(headers=None):
    headers = headers or {}
    scope = {
        'type': 'http', 'method': 'GET', 'path': '/',
        'headers': [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        # ...
    }
    return Request(scope)
```

### TypeScript Test Data

**Mock data objects inline:**
```typescript
const mockMessages = [
    { role: 'agent' as const, text: 'Hello!', agentName: 'ExecutiveAgent' }
]
```

**Location:** Test data is inline in test files (no separate fixture directory)

## Coverage

**Requirements:** No enforced coverage threshold in CI
**Docstring coverage:** 80%+ enforced by interrogate (pre-commit hook, excludes tests)

**View Coverage:**
```bash
uv run pytest tests/unit --cov=app --cov-report=html
```

## Test Types

### Smoke Tests
- Location: `tests/unit/test_smoke.py`
- Purpose: Verify all core modules import without errors
- Pattern: Try import, assert no ImportError
- Classes: `TestApplicationSmoke`, `TestConfigurationSmoke`, `TestFastAPIAppSmoke`

### Unit Tests
- Location: `tests/unit/`
- Scope: Individual functions, classes, services
- Dependencies: All external deps mocked via conftest.py
- Async: Use `@pytest.mark.asyncio` decorator
- Run: `uv run pytest tests/unit`

### Integration Tests
- Location: `tests/integration/`
- Scope: FastAPI endpoints, multi-component flows
- Dependencies: Uses `fastapi.testclient.TestClient` with real FastAPI app
- Env: Sets `LOCAL_DEV_BYPASS=1`, `SKIP_ENV_VALIDATION=1`, `ENVIRONMENT=test`
- Some tests skip without credentials: `@pytest.mark.skipif(not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"), ...)`
- Run: `uv run pytest tests/integration`

### Workflow Validation Tests
- Not pytest-based; standalone scripts
- `scripts/verify/validate_workflow_templates.py` - validates template schemas
- `scripts/verify/generate_workflow_baseline.py` - generates baseline snapshots
- Run before pytest in `make test` and `make lint`

### Load Tests
- Location: `tests/load_test/load_test.py`
- Excluded from default test runs via `addopts = "--ignore=tests/load_test"` in pytest config

### Frontend Tests
- Component rendering tests via @testing-library/react
- Hook behavior tests via `renderHook` from @testing-library/react
- Service/utility tests (pure logic, no rendering)
- All run in jsdom environment

## Common Patterns

### Async Testing (Python)
```python
@pytest.mark.asyncio
async def test_cache_miss_returns_miss_result(self):
    service = CacheService()
    service._redis = AsyncMock()
    service._redis.get = AsyncMock(return_value=None)
    service._connected = True

    result = await service.get_user_config("test_user")

    assert isinstance(result, CacheResult)
    assert result.is_miss is True
```

### Error Testing (Python)
```python
def test_validation_error_with_code(self):
    error = ValidationError(message="Invalid input")
    assert error.message == "Invalid input"
    assert error.code == ErrorCode.VALIDATION_ERROR

def test_validation_error_http_status(self):
    error = ValidationError(message="test")
    assert error.status_code == 400
```

### Exception Testing (Python)
```python
def test_build_tool_kwargs_rejects_user_visible_missing_schema():
    with pytest.raises(WorkflowContractError) as exc:
        build_tool_kwargs(...)
    assert exc.value.reason_code == "missing_schema"
```

### Conditional Skipping (Python)
```python
@pytest.mark.skipif(
    not (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GOOGLE_CLOUD_PROJECT")),
    reason="Requires Google Cloud credentials or Project ID"
)
def test_agent_stream() -> None:
    # ... test requiring real credentials
```

### Component Testing (TypeScript)
```typescript
it('renders initial greeting', () => {
    render(<ChatInterface />)
    expect(screen.getByText(/Hello! I am Pikar AI/i)).toBeTruthy()
})

it('calls sendMessage when clicking send', async () => {
    render(<ChatInterface />)
    const input = screen.getByPlaceholderText(/Type your message/i)
    fireEvent.change(input, { target: { value: 'Test message' } })
    fireEvent.click(screen.getByRole('button'))
    expect(mockSendMessage).toHaveBeenCalledWith('Test message')
})
```

### Hook Testing (TypeScript)
```typescript
it('initializes with default state', () => {
    const { result } = renderHook(() => useAgentChat())
    expect(result.current.messages).toHaveLength(1)
    expect(result.current.isStreaming).toBe(false)
})

it('sends message correctly', async () => {
    const { result } = renderHook(() => useAgentChat())
    await act(async () => {
        await result.current.sendMessage('Hello Agent')
    })
    expect(fetchEventSource).toHaveBeenCalledWith(
        'http://test-api.com/a2a/app/run_sse',
        expect.objectContaining({ method: 'POST' })
    )
})
```

### Frontend Test Setup/Teardown
```typescript
beforeEach(() => {
    vi.clearAllMocks()
    window.HTMLElement.prototype.scrollIntoView = vi.fn()
})

afterEach(() => {
    cleanup()
    vi.clearAllMocks()
})
```

## Integration Test Pattern: FastAPI TestClient

```python
from fastapi.testclient import TestClient
from app.fast_api_app import app

client = TestClient(app)

class TestA2AProtocol:
    def test_agent_card_retrieval(self):
        with TestClient(app) as local_client:
            card_url = next((r.path for r in app.routes if r.path.endswith("agent-card.json")), None)
            response = local_client.get(card_url)
            assert response.status_code == 200
            card = response.json()
            assert "name" in card
```

## Key Test Configuration

**pytest.ini_options (in pyproject.toml):**
```toml
[tool.pytest.ini_options]
addopts = "--ignore=tests/load_test"
filterwarnings = [
    "ignore:'enablePackrat' deprecated...:DeprecationWarning:pyiceberg",
    # ... suppressed third-party deprecation warnings
]
```

**Vitest config (frontend/vitest.config.mts):**
```typescript
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
  },
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
})
```

---

*Testing analysis: 2026-03-20*

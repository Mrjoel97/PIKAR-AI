# Testing Patterns

**Analysis Date:** 2026-03-04

## Test Framework

**Runner:**
- Backend: Pytest + pytest-asyncio (`pyproject.toml`, `tests/`)
- Frontend: Vitest with jsdom (`frontend/vitest.config.mts`)

**Assertion Library:**
- Backend: native `assert` with pytest helpers and marks
- Frontend: Vitest `expect` with Testing Library match/DOM patterns

**Run Commands:**
```bash
make test
uv run pytest tests/unit -v
uv run pytest tests/integration -v
uv run pytest tests/unit/test_financial_service.py -v
npm run test --prefix frontend
npm run test -- --run --prefix frontend
```

## Test File Organization

**Location:**
- Backend unit tests: `tests/unit/`
- Backend integration tests: `tests/integration/`
- Evaluation datasets: `tests/eval_datasets/*.json`
- Frontend tests: both `frontend/src/**/*.test.tsx` and `frontend/__tests__/`

**Naming:**
- Python: `test_<feature>.py`
- Frontend: `<module>.test.ts` / `<component>.test.tsx`
- Integration tests often use explicit endpoint/flow names (for example `test_workflow_template_marketplace_endpoints.py`)

**Structure:**
```
tests/
  unit/
    conftest.py
    test_financial_service.py
  integration/
    test_server_e2e.py
    test_workflow_template_marketplace_endpoints.py
frontend/
  src/components/chat/ChatInterface.test.tsx
  src/services/workflows.test.ts
  __tests__/pages/LoginPage.test.tsx
```

## Test Structure

**Suite Organization (Backend):**
```python
import pytest

@pytest.mark.asyncio
async def test_behavior(monkeypatch):
    # arrange
    # act
    # assert
```

**Suite Organization (Frontend):**
```typescript
describe('ChatInterface', () => {
  beforeEach(() => {
    vi.mocked(useAgentChat).mockReturnValue(...)
  })

  it('calls sendMessage when clicking send', async () => {
    // arrange/act/assert
  })
})
```

**Patterns:**
- Backend async tests are common and use `@pytest.mark.asyncio`
- Frontend tests use Testing Library render/fireEvent/waitFor patterns
- Integration tests frequently use `fastapi.testclient.TestClient`

## Mocking

**Framework:**
- Backend: `monkeypatch`, `MagicMock`, fixture overrides
- Frontend: `vi.mock`, `vi.fn`, `vi.mocked`

**Patterns:**
```python
monkeypatch.setattr(module, 'factory', lambda: fake_impl)
mock_client = MagicMock()
```

```typescript
vi.mock('@/hooks/useAgentChat', () => ({ useAgentChat: vi.fn() }))
vi.mocked(useAgentChat).mockReturnValue(mockValue)
```

**What to Mock:**
- External API clients (Stripe, Supabase, ADK, Google integrations)
- Network-dependent boundaries in integration tests
- Browser-only hooks/services in frontend unit tests

**What NOT to Mock (generally):**
- Core transformation logic where deterministic assertions are possible
- DTO normalization and utility functions when testing pure behavior

## Fixtures and Factories

**Test Data:**
- Backend uses custom builders and inline fixtures (example `_build_mock_financial_client`)
- Global backend test scaffolding/mocks live in `tests/unit/conftest.py`
- Integration tests use stub service classes for route-level behavior injection

**Location:**
- Shared pytest fixtures in `tests/unit/conftest.py` and `tests/integration/conftest.py`
- Frontend test doubles are usually declared in-file with `vi.mock`

## Coverage

**Requirements:**
- No strict code coverage threshold is enforced in CI currently
- Coverage artifacts can be generated locally (`htmlcov/` present)

**Configuration:**
- Pytest options in `pyproject.toml`
- Frontend test environment configured in `frontend/vitest.config.mts`

**View Coverage:**
```bash
uv run pytest --cov app
npm run test --prefix frontend -- --coverage
```

## Test Types

**Unit Tests:**
- Dominant backend test type (`tests/unit/`)
- Focused service/router/tool behavior with mocked external dependencies

**Integration Tests:**
- API/workflow/edge path validation (`tests/integration/`)
- Includes A2A, SSE, RLS, memory, workflow lifecycle scenarios

**Evaluation/Golden Tests:**
- Agent eval datasets in `tests/eval_datasets/`
- Golden output artifacts in `tests/golden/`

**Load Tests:**
- Present in `tests/load_test/` for manual/perf scenarios

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_get_revenue_stats_uses_stripe_when_configured(monkeypatch):
    result = await service.get_revenue_stats('mtd')
    assert result['status'] == 'connected'
```

**Error Testing:**
```python
result = await service.get_revenue_stats('custom', start_date='2026-02-14', end_date='2026-02-01')
assert result['status'] == 'error'
```

**Route Testing:**
```python
with TestClient(fast_api_app.app) as client:
    response = client.get('/workflows/marketplace/templates')
    assert response.status_code == 200
```

**Snapshot Testing:**
- Not a primary pattern in backend tests
- Frontend favors explicit behavioral assertions over snapshots

---

*Testing analysis: 2026-03-04*
*Update when test patterns change*

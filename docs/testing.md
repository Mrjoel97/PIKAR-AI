# Testing Notes

## Mixed-Run Safe Mocking Rules

When writing or updating test mocks, assume `app/tests` and `tests/unit` may be executed in the same pytest run.

1. Do not replace top-level packages in `sys.modules` with plain mocks.
   - Avoid patterns like `sys.modules["google"] = MagicMock()`.
   - If a package must be stubbed, keep it package-shaped (`__path__`) and only override the minimum submodules.

2. Mock narrow submodules, not global namespaces.
   - Good: `google.adk.events`, `google.adk.runners`.
   - Bad: entire `google` tree unless absolutely required.

3. Provide import-time symbols used by other suites.
   - If a mocked module is imported at app startup, ensure expected names exist (for example `Event`, `Runner`, `InMemorySessionService`).

4. Prefer dependency injection/monkeypatch over global `sys.modules` hacks in test cases.
   - Patch function boundaries (for example `get_cache_service`, auth helpers) rather than replacing broad packages.

5. Keep endpoint assertions focused on behavior owned by the endpoint.
   - For auth-gate tests, assert status/validation behavior.
   - Avoid coupling to downstream runtime internals that may differ under unit mocks.

## Recommended Smoke Command

Run this after changing shared mocks or `conftest.py`:

```bash
uv run pytest app/tests/test_pr3_endpoints.py tests/unit/test_tools.py -q
```

If this mixed command fails while individual suites pass, treat it as a mock isolation regression.

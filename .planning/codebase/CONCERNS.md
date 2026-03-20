# Codebase Concerns

**Analysis Date:** 2026-03-20

## Tech Debt

**Deprecated import shim `app/services/supabase.py` still widely used:**
- Issue: `app/services/supabase.py` is an explicit backward-compatibility re-export layer that warns on import. Over 30 files still import from it instead of the canonical `app/services/supabase_client.py`.
- Files: `app/services/supabase.py`, `app/workflows/engine.py`, `app/app_utils/auth.py`, `app/social/connector.py`, `app/skills/custom_skills_service.py`, `app/agents/tools/brain_dump.py`, `app/agents/tools/media.py`, `app/middleware/onboarding_guard.py`, `app/routers/workflows.py`, and 20+ others.
- Impact: Adds an unnecessary indirection layer. The deprecation warning is gated behind `PIKAR_ENABLE_DEPRECATED_IMPORT_WARNINGS=1` so it is invisible by default.
- Fix approach: Global find-replace of `from app.services.supabase import` to `from app.services.supabase_client import`. Then remove `app/services/supabase.py`.

**Loose temporary/debug files in project root:**
- Issue: Multiple throwaway scripts are committed at the project root: `test_import.py`, `test_live.py`, `test_ws.py`, `tmp_import_check.py`, `tmp_syntax_check.py`, `create_template_directly.py`, `inspect_tools.py`, `list_workflows.py`, `run_workflow_creator.py`, and a `tmpmmtjcyle` file/directory.
- Files: All at project root `C:/Users/expert/documents/pka/pikar-ai/`
- Impact: Clutters the repo, confuses discoverability, and some scripts import production modules directly without test harnesses.
- Fix approach: Delete or move to `scripts/` if reusable. Add a `.gitignore` rule for `tmp*` files.

**Multiple `logging.basicConfig()` calls:**
- Issue: Three different modules call `logging.basicConfig()` at module level, which can silently override the root logger configuration depending on import order.
- Files: `app/fast_api_app.py:73`, `app/workflows/engine.py:38`, `app/workflows/worker.py:23`
- Impact: Logging behavior is non-deterministic based on which module is imported first. Can cause missing log output in production.
- Fix approach: Remove all `logging.basicConfig()` calls except the one in `app/fast_api_app.py` (the entry point). Configure the root logger once at startup.

**Backward compatibility aliases in `app/fast_api_app.py`:**
- Issue: Lines 918-924 create underscore-prefixed aliases like `_is_model_unavailable_error = is_model_unavailable_error` for functions that were already refactored to `app/sse_utils.py`. Comment says "for existing imports from this module" but these should have been migrated.
- Files: `app/fast_api_app.py:918-924`
- Impact: Dead code that bloats the already-large entry point (1255 lines).
- Fix approach: Grep for any remaining imports of these `_` prefixed names and update them, then remove the aliases.

**`datetime.utcnow()` used instead of timezone-aware datetimes:**
- Issue: Over 20 call sites use the deprecated `datetime.utcnow()` (deprecated since Python 3.12). It returns a naive datetime without timezone information, which can cause subtle bugs when comparing with timezone-aware timestamps from the database.
- Files: `app/fast_api_app.py` (7 occurrences), `app/agents/financial/tools.py`, `app/services/report_scheduler.py`, `app/exceptions.py`, `app/integrations/google/calendar.py`, `app/social/linkedin_webhook.py`, `app/skills/custom_skills_service.py`, `app/mcp/user_config.py`
- Impact: Potential timestamp comparison bugs and Python 3.12+ deprecation warnings in logs.
- Fix approach: Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)` (already used correctly in `app/services/request_context.py` and `app/services/self_improvement_engine.py`).

**Oversized `fast_api_app.py` entry point (1255 lines):**
- Issue: The main FastAPI application file mixes credential bootstrapping, environment validation, session/runner initialization, CORS configuration, exception handlers, middleware registration, 20+ router imports, health endpoints, admin endpoints, and the core SSE chat endpoint all in a single file.
- Files: `app/fast_api_app.py`
- Impact: Hard to navigate, test in isolation, or review changes. The SSE `run_sse` endpoint alone spans lines 940-1241 (~300 lines of nested async logic).
- Fix approach: Extract health endpoints to `app/routers/health.py`, extract the SSE chat handler to `app/routers/chat.py` or `app/sse_handler.py`, and move startup initialization to a dedicated `app/startup.py`.

**Tool registry file is 1122 lines with inline tool wrappers:**
- Issue: `app/agents/tools/registry.py` is a monolithic file that imports from every tool module, defines inline async wrapper functions for aliases/promotions, and contains the entire `TOOL_REGISTRY` dict literal.
- Files: `app/agents/tools/registry.py`
- Impact: Any new tool requires editing this single file. Import errors in any tool module prevent the entire registry from loading.
- Fix approach: Move to a declarative registration pattern (decorator-based or auto-discovery) so tools self-register.

## Known Bugs

**PKCE verifier stored in process memory, lost on restart/scale:**
- Symptoms: OAuth callback fails with "PKCE verifier not found. Session may have expired." after a server restart or when the callback hits a different process instance.
- Files: `app/social/connector.py:89` (`self._pkce_verifiers: Dict[str, str] = {}`)
- Trigger: User starts an OAuth flow, server restarts or load balancer routes the callback to a different instance.
- Workaround: None. Users must retry the OAuth flow.
- Fix: Persist PKCE verifiers in Redis or Supabase with a short TTL.

**OnboardingGuardMiddleware makes blocking Supabase calls on every request:**
- Symptoms: Dashboard API latency increases by 100-300ms per request due to synchronous DB lookups in middleware.
- Files: `app/middleware/onboarding_guard.py:66-93`
- Trigger: Every authenticated request to protected paths triggers two blocking Supabase queries (`users_profile` and `user_executive_agents`).
- Workaround: Queries succeed but add latency on every request.
- Fix: Cache the onboarding status in Redis (already available) or in-memory with TTL. Or move the check to the frontend middleware and remove backend enforcement.

## Security Considerations

**Auth permissive mode is the default:**
- Risk: The `REQUIRE_STRICT_AUTH` env var defaults to `0` (permissive mode). In this mode, invalid tokens log warnings but do NOT reject requests if `ALLOW_ANONYMOUS_CHAT=1` is also set. A misconfigured production deployment could allow anonymous access.
- Files: `app/app_utils/auth.py:42-44`, `app/fast_api_app.py:950`
- Current mitigation: The docstring documents the risk. Environment validation (`app/config/validation.py`) warns about missing `SUPABASE_JWT_SECRET` in production.
- Recommendations: Flip the default to strict mode (`REQUIRE_STRICT_AUTH=1`) and require explicit opt-out for development. Add a startup check that blocks `ALLOW_ANONYMOUS_CHAT=1` in production environments.

**Audience verification disabled in JWT decoding:**
- Risk: All JWT decode calls use `options={'verify_aud': False}`, which skips audience claim validation. A token issued for a different Supabase project/audience would be accepted.
- Files: `app/app_utils/auth.py:93`, `app/app_utils/auth.py:120`, `app/app_utils/auth.py:172`, `app/middleware/rate_limiter.py:100`
- Current mitigation: Tokens are additionally verified against Supabase `auth.get_user()` in the primary `verify_token` path.
- Recommendations: Set `verify_aud: True` and configure the expected audience claim. This prevents cross-project token reuse.

**Health endpoints exposed without authentication:**
- Risk: `/health/connections`, `/health/cache`, `/health/workflows/readiness` expose internal configuration details (Redis connection strings, circuit breaker state, missing env vars, canary user counts) to unauthenticated callers.
- Files: `app/fast_api_app.py:637-830`
- Current mitigation: `/health/live` is intentionally unauthenticated for container probes. But detailed endpoints leak internal topology.
- Recommendations: Add authentication to detailed health endpoints (except `/health/live`). Or restrict them to internal network access via middleware.

**`x-user-id` header trusted without verification:**
- Risk: The `RequestLoggingMiddleware` reads and stores `x-user-id` from request headers, and the CORS config explicitly allows this header. If any downstream code trusts `request.state.user_id` set by the middleware instead of the JWT-verified user, it could be spoofed.
- Files: `app/fast_api_app.py:448-451`, `app/fast_api_app.py:540-541`
- Current mitigation: The SSE endpoint independently verifies the user from the Bearer token.
- Recommendations: Remove `x-user-id` and `user-id` from allowed CORS headers. Only set `request.state.user_id` from verified JWT claims.

**`ALLOW_ANY_AUTH_ADMIN_ENDPOINT` bypasses all admin auth:**
- Risk: Setting `ALLOW_ANY_AUTH_ADMIN_ENDPOINT=1` allows any authenticated user to invoke `/admin/cache/invalidate`, which can `flushdb()` the entire Redis cache.
- Files: `app/fast_api_app.py:844`
- Current mitigation: Still requires a valid Bearer token. The flag name is explicit about the risk.
- Recommendations: Remove this flag entirely. Use the `ADMIN_USER_IDS` or `ADMIN_USER_EMAILS` allowlists instead.

## Performance Bottlenecks

**Blocking Supabase client wrapped with `asyncio.to_thread`:**
- Problem: The Supabase Python client is synchronous. Every database call goes through `app/services/supabase_async.py:execute_async()` which wraps `query.execute()` in `asyncio.to_thread()`. This consumes a thread from the default ThreadPoolExecutor (usually 5-40 threads).
- Files: `app/services/supabase_async.py`, used by all services via `execute_async()`
- Cause: The `supabase-py` SDK is blocking. Under load, all threads can be consumed by DB calls, blocking all other async operations.
- Improvement path: Use `asyncpg` directly for performance-critical paths, or switch to the async Supabase client when it stabilizes. In the meantime, increase the thread pool size via `asyncio.get_event_loop().set_default_executor(ThreadPoolExecutor(max_workers=N))`.

**Session event loading without pagination:**
- Problem: Loading a session loads up to `SESSION_MAX_EVENTS` (default 80) events and processes each through `_compact_event_for_context()` with `copy.deepcopy()` and recursive traversal. For sessions with large events, this can take seconds.
- Files: `app/persistence/supabase_session_service.py:25-26` (constants), the `_compact_value_for_context` function at line 62
- Cause: Deep copy + recursive compaction of every event on every session load.
- Improvement path: Cache compacted events in Redis. Only compact new events incrementally.

**SSE connection limits are per-process only:**
- Problem: The SSE connection limiter (`_active_connection_counts` dict) is stored in process memory. When running multiple Cloud Run instances, each instance maintains its own count. A user could open 3 x N connections across N instances.
- Files: `app/services/sse_connection_limits.py:15`
- Cause: In-memory dict is not shared across processes.
- Improvement path: Use Redis `INCR`/`DECR` with a TTL for cross-process tracking. Accept that per-process is "good enough" as a guardrail until traffic justifies the Redis overhead.

**Rate limiter persona lookup falls back to default for uncached users:**
- Problem: The rate limiter (`app/middleware/rate_limiter.py`) checks an in-memory cache for user persona. If the user is not cached, it falls back to the default limit (10/min) rather than querying the database. This means new users always get the lowest rate limit until something else populates the cache.
- Files: `app/middleware/rate_limiter.py:121-123`
- Cause: The DB lookup was intentionally removed from the hot path (line 121 comment: "Avoid DB/network lookups here").
- Improvement path: Populate the persona cache on login or session creation, or use a background task to warm it.

## Fragile Areas

**`app/fast_api_app.py` startup initialization sequence:**
- Files: `app/fast_api_app.py:15-217`
- Why fragile: The file uses conditional imports gated on `BYPASS_IMPORT`, `A2A_AVAILABLE`, `ADK_CORE_AVAILABLE`, and `A2A_COMPONENTS_AVAILABLE` flags. Mock classes are defined inline when imports fail. The initialization order matters - `_app_dir` is defined twice (lines 22 and 40). Environment variables must be loaded before any Google SDK import.
- Safe modification: Test any changes with `LOCAL_DEV_BYPASS=1` and without it. Check that the lifespan function still initializes A2A routes.
- Test coverage: Integration tests exist (`tests/integration/test_server_e2e.py`, `tests/integration/test_a2a_protocol.py`) but they bypass much of the startup logic.

**Workflow engine concurrent execution guard:**
- Files: `app/workflows/engine.py:48-50`, `app/workflows/engine.py:487-600`
- Why fragile: The `MAX_CONCURRENT_EXECUTIONS_PER_USER` check queries Supabase for active executions, but there is no database-level lock. Two near-simultaneous requests could both pass the check before either creates a new execution, exceeding the limit.
- Safe modification: Add a `SELECT ... FOR UPDATE` or use a Supabase RPC with advisory locks for the concurrency check.
- Test coverage: `tests/integration/test_end_to_end_workflow.py` covers basic flows but does not test concurrent starts.

**In-memory singleton pattern across services:**
- Files: `app/services/cache.py` (CacheService singleton), `app/services/supabase_client.py` (SupabaseService singleton), `app/skills/registry.py` (SkillsRegistry singleton), `app/workflows/registry.py` (WorkflowRegistry singleton), `app/social/connector.py:89` (PKCE verifiers), `app/social/publisher.py` (global publisher), `app/social/analytics.py` (global analytics service)
- Why fragile: Multiple singletons use class-level `_instance` or module-level globals with manual locking. Tests that need to reset state must call `invalidate_*()` functions. If any singleton initialization fails on first access, recovery requires knowing to call the invalidation function.
- Safe modification: Always call `invalidate_*()` in test teardown. Never store request-scoped data in singletons.
- Test coverage: `app/services/supabase_client.py:invalidate_client()` exists but not all singletons have invalidation methods.

**SSE chat endpoint (`run_sse`) nesting depth:**
- Files: `app/fast_api_app.py:940-1241`
- Why fragile: The endpoint defines an `event_generator()` async generator inside the route handler, which defines `_runner_to_queue()` inside itself. State is shared via closures (`nonlocal _responding_agent`). The function manages session creation, skill loading, runner fallback, event extraction, progress multiplexing, keepalive heartbeats, timeout enforcement, and interaction logging in a single 300-line function.
- Safe modification: Extract `_runner_to_queue` and the event multiplexing loop into separate functions. Test with WebSocket disconnect scenarios.
- Test coverage: `tests/integration/test_sse_endpoint.py`, `tests/integration/test_sse_crash.py`, `tests/integration/test_sse_injection.py` exist but cannot easily exercise all failure paths in the nested closures.

## Scaling Limits

**Supabase client thread pool saturation:**
- Current capacity: Default `asyncio.to_thread` pool size (typically min(32, os.cpu_count() + 4) threads).
- Limit: Under heavy concurrent load, all threads blocked on Supabase HTTP calls starve other async operations.
- Scaling path: Increase pool size explicitly. Move to an async database client. Add connection pooling via PgBouncer.

**110 SQL migration files:**
- Current capacity: 110 migration files in `supabase/migrations/`.
- Limit: `supabase db reset` execution time grows linearly. Development iteration slows.
- Scaling path: Squash old migrations periodically. Create a baseline schema snapshot.

## Dependencies at Risk

**InMemoryArtifactService/InMemorySessionService fallback:**
- Risk: When `GcsArtifactService` or `SupabaseSessionService` fail to initialize, the system silently falls back to in-memory implementations. These lose all data on restart with no user-visible warning.
- Impact: Sessions and artifacts appear to work but are silently volatile. Users lose conversation history.
- Files: `app/fast_api_app.py:171-175`, `app/fast_api_app.py:188-193`, `app/fast_api_app.py:221-225`
- Migration plan: Fail hard in production if persistent services cannot initialize. Only allow in-memory fallback when `ENVIRONMENT=development`.

**Synchronous Supabase Python SDK:**
- Risk: The `supabase-py` SDK is synchronous and all calls must be wrapped in `asyncio.to_thread()`. The async Supabase client (`supabase-py` v3) is still maturing.
- Impact: Thread pool exhaustion under load. Cannot use connection multiplexing.
- Files: `app/services/supabase_async.py`, `app/services/supabase_client.py`
- Migration plan: Monitor `supabase-py` async client progress. Consider using `asyncpg` + `PostgREST` directly for hot paths.

## Missing Critical Features

**No structured logging:**
- Problem: All logging uses Python's built-in `logging` module with string formatting. No structured JSON logging is configured for production, making log aggregation and querying in Cloud Logging difficult.
- Blocks: Effective debugging of production issues, correlation of requests across services.
- Files: `app/fast_api_app.py:73` (basicConfig), every `logger.info(f"...")` call throughout the codebase.

**No database connection health recovery:**
- Problem: If the Supabase client's underlying HTTP connection pool enters a bad state (e.g., after a network partition), there is no automatic reconnection. The `invalidate_client()` function exists but is only callable via the admin endpoint.
- Blocks: Automatic recovery from transient network issues.
- Files: `app/services/supabase_client.py:179-198`

## Test Coverage Gaps

**Frontend has only 29 test files across the entire codebase:**
- What's not tested: Most page components (`dashboard/`, `settings/`, `onboarding/`), all API route handlers (`app/api/`), all hooks except partial coverage of `useAgentChat`.
- Files: `frontend/src/__tests__/` (2 files), `frontend/src/components/widgets/__tests__/` (partial), `frontend/src/components/workflows/` (2 test files)
- Risk: UI regressions go unnoticed. Widget rendering bugs in `ChatInterface.tsx` (1570 lines), `VaultInterface.tsx` (1017 lines), or `ActiveWorkspace.tsx` (677 lines) have no safety net.
- Priority: High - the frontend is the primary user-facing surface.

**Workflow engine lacks concurrent execution tests:**
- What's not tested: Race conditions in concurrent workflow starts, concurrent step execution, circuit breaker recovery paths.
- Files: `app/workflows/engine.py`, `app/workflows/step_executor.py`, `app/workflows/worker.py`
- Risk: Data corruption or duplicate executions under concurrent load.
- Priority: High - workflows are a core feature with financial implications.

**Social OAuth connector has no test coverage:**
- What's not tested: OAuth flow initiation, callback handling, token refresh, PKCE verification, platform-specific token exchange.
- Files: `app/social/connector.py` (350+ lines), `app/social/publisher.py`, `app/social/analytics.py` (450+ lines)
- Risk: OAuth integration breakage goes undetected. Token handling bugs could leak credentials.
- Priority: Medium - social integrations are a secondary feature but handle sensitive tokens.

**Agent tools (44 files) have minimal direct unit tests:**
- What's not tested: Most individual tool functions in `app/agents/tools/` are tested only indirectly through integration tests that run the full agent pipeline.
- Files: `app/agents/tools/*.py` (44 files), `tests/unit/app/agents/` (very few files)
- Risk: Tool behavior changes are only caught by expensive integration tests, slowing CI.
- Priority: Medium - tools are the primary interface between agents and the system.

**No load/stress testing in CI:**
- What's not tested: The `tests/load_test/` directory exists but is not part of the CI pipeline (`make test` runs unit + integration only).
- Files: `tests/load_test/`
- Risk: Performance regressions and thread pool saturation under load are only discovered in production.
- Priority: Medium - important as user base grows.

---

*Concerns audit: 2026-03-20*

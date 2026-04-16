---
status: testing
phase: 71-engine-runtime-fixes
source: [71-01-SUMMARY.md, 71-02-SUMMARY.md, 71-03-SUMMARY.md]
started: 2026-04-12T06:50:00Z
updated: 2026-04-12T06:50:00Z
---

## Current Test

number: 1
name: Cold Start Smoke Test
expected: |
  Kill any running backend. Run `uv run pytest tests/unit/test_self_improvement_engine.py tests/unit/test_skill_embeddings.py tests/unit/test_skill_creator.py tests/integration/test_self_improvement_nonblocking.py -v` — all tests pass without errors.
  This verifies the lifespan hook change (build_index in fast_api_app.py) and all three plan deliverables are importable and functional.
awaiting: user response

## Tests

### 1. Cold Start Smoke Test
expected: Run `uv run pytest tests/unit/test_self_improvement_engine.py tests/unit/test_skill_embeddings.py tests/unit/test_skill_creator.py tests/integration/test_self_improvement_nonblocking.py -v` — all Phase 71 tests pass green.
result: [pending]

### 2. Async Gemini Client (FIX-01)
expected: `app/services/self_improvement_engine.py` `_generate_with_gemini` method uses `client.aio.models.generate_content` (async API) instead of the sync `client.models.generate_content`. The method is `async def` and `await`s the Gemini call. No `asyncio.to_thread` wrapper needed because the native async API is used directly.
result: [pending]

### 3. Event Bus Await Fix (FIX-02)
expected: In `app/services/self_improvement_engine.py` `identify_improvements`, the coverage-gap event bus call uses `await bus.emit(...)` directly — NOT `asyncio.get_event_loop().run_until_complete(bus.emit(...))`. The old import of `asyncio as _aio` in that section is removed or unused.
result: [pending]

### 4. Telemetry Metrics (FIX-05)
expected: `run_improvement_cycle` return dict includes three new keys: `cycle_duration_ms` (float), `gemini_call_latency_ms` (float), `actions_executed_total` (int). A structured logger.info line emits these for observability pipeline pickup.
result: [pending]

### 5. Skill Embedding Startup Hook (FIX-04)
expected: `app/skills/skill_embeddings.py` exports an async `build_index()` function. `app/fast_api_app.py` lifespan calls `asyncio.create_task(build_index())` as a fire-and-forget background task so server startup is never blocked by embedding warmup.
result: [pending]

### 6. Semantic Skill Similarity (FIX-03)
expected: `app/skills/skill_creator.py` `find_similar_skills` checks `is_warmed()` from skill_embeddings. When warmed, it uses `search_similar()` for cosine-similarity ranking. When cold, it falls back to keyword overlap. A synonym query (e.g., "revenue forecasting") surfaces semantically related skills (e.g., "financial projection"), not just keyword matches.
result: [pending]

### 7. Non-Blocking Integration Test (FIX-06)
expected: `tests/integration/test_self_improvement_nonblocking.py` exists with an asyncio scheduling probe test. The probe records timestamps at 100ms intervals during `run_improvement_cycle` and asserts max gap < 500ms, proving the engine yields to the event loop.
result: [pending]

## Summary

total: 7
passed: 0
issues: 0
pending: 7
skipped: 0

## Gaps

[none yet]

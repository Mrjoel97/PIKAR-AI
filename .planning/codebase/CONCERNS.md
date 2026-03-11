# Codebase Concerns

**Analysis Date:** 2026-03-11

## Tech Debt

**Rate Limiting Not Implemented:**
- Issue: MCP Connector has TODO comment for rate limiting on line 10 of `app/mcp/connector.py`
- Files: `app/mcp/connector.py`
- Impact: External API calls from MCPConnector can overwhelm rate limits, causing cascading failures and blocked access to external services (web search, scraping, form handlers)
- Fix approach: Implement token bucket or sliding window rate limiter with configurable limits per tool and per minute; add circuit breaker pattern similar to existing Redis circuit breaker in `app/services/cache.py`

**PDF and XLSX Report Generation Stubbed:**
- Issue: PDF and XLSX generation not implemented; placeholder returns empty string
- Files: `app/services/report_scheduler.py` (line 368-369)
- Impact: Reports scheduled with PDF or XLSX format silently fail with empty file paths; users get broken deliverables without error notification
- Fix approach: Implement PDF generation using reportlab or pypdf, XLSX using openpyxl; add validation before report scheduling to reject unsupported formats early; add proper error handling and user notification

**Report Delivery Not Implemented:**
- Issue: Email and Drive upload delivery mechanisms are stubbed as TODO
- Files: `app/services/report_scheduler.py` (line 389)
- Impact: Generated reports are never delivered to users; scheduled reports appear to complete successfully but users never receive them
- Fix approach: Integrate email service (SendGrid or Gmail API) for email delivery; integrate Google Drive API for file uploads; add delivery status tracking to database with retry logic

**Incomplete Brain Dump Context Handling:**
- Issue: Tool doesn't receive user_id directly; context extraction relies on assumptions about file paths containing user_id
- Files: `app/agents/tools/brain_dump.py` (lines 38-44)
- Impact: Brain dump data may not be correctly associated with users; data could be lost or assigned to wrong user when tool context is uncertain
- Fix approach: Pass user_id explicitly through tool context or session context; validate user_id before database operations; add logging to detect context mismatches

## Known Bugs

**Empty Exception Handlers Masking Errors:**
- Symptoms: Silent failures where exceptions are caught but not logged or handled; users experience "nothing happened" without error messages
- Files:
  - `app/agents/context_extractor.py` (lines catching json.JSONDecodeError, returning empty dict)
  - `app/agents/content/tools.py` (returns empty results list)
  - `app/agents/enhanced_tools.py` (bare pass in except ValueError)
  - `app/agents/strategic/tools.py` (multiple bare pass statements)
- Trigger: When invalid data formats reach tools or JSON parsing fails; occurs in production when malformed responses from external APIs are processed
- Workaround: Enable debug logging to see actual exceptions; check application logs before assuming features work; test with invalid input data

**Broad Exception Catching:**
- Symptoms: Multiple `except Exception:` blocks that catch all exceptions including system errors and shutdowns
- Files: 15+ locations including:
  - `app/agent.py` (line with Exception catch for Knowledge Vault fallback)
  - `app/fast_api_app.py` (Exception catch for Google Cloud Logging)
  - `app/database/__init__.py` (Exception catch during session cleanup)
  - `app/integrations/google/sheets.py` (Exception catch returning empty list)
- Trigger: When unexpected errors occur, they're swallowed without proper handling or logging
- Workaround: Add structured logging with exception traceback before broad catches; use specific exception types where possible

**Database Transaction Handling in Uncertain State:**
- Symptoms: Database transactions may be rolled back on exception, but connection state unclear if exception occurs during rollback itself
- Files: `app/database/__init__.py` (line with `session.rollback()` in bare except block)
- Trigger: When database connection is lost mid-transaction or when rollback fails
- Workaround: Ensure connection pooling is properly configured; test with simulated connection failures

## Security Considerations

**Environment Variable Exposure Risk:**
- Risk: Multiple sensitive env vars loaded from `.env` file at startup; if `.env` is ever committed (despite `.gitignore`), credentials become exposed
- Files: `app/fast_api_app.py` (lines 15-26 loading .env), multiple config files
- Current mitigation: `.gitignore` blocks `.env` files; `.env.example` provided as template
- Recommendations:
  1. Add pre-commit hook to detect `.env` file commits (implement as validation in pre-commit)
  2. Rotate all credentials in the repository's deployment history (ensure no past commits contain secrets)
  3. Implement secret scanning in CI/CD (enable GitHub security scanning or similar)
  4. Audit all service account credentials and API keys for appropriate scopes
  5. Consider switching to external secret manager (Google Cloud Secret Manager, Vault) instead of file-based `.env`

**PII Filtering Implemented But Not Enforced Everywhere:**
- Risk: `PIIFilter` exists in `app/mcp/security/pii_filter.py` but is only applied in MCPConnector; other tools and agent calls may leak sensitive data to external services
- Files: `app/mcp/connector.py` (has PII filtering), but `app/mcp/tools/web_search.py`, `app/mcp/tools/web_scrape.py` and other external integrations may not use it
- Current mitigation: Audit logging in `app/mcp/security/audit_logger.py` tracks what goes where
- Recommendations:
  1. Enforce PII filtering middleware at agent tool invocation layer, not just MCPConnector
  2. Add automated PII detection testing for all external API calls
  3. Implement opt-in user consent for external data sharing (web search, scraping)
  4. Add data anonymization for analytics and logging

**Vertex AI Context Cache Configuration:**
- Risk: Context cache stores sensitive user data and prompt context in Google Cloud infrastructure; cache invalidation on credential rotation unclear
- Files: `app/fast_api_app.py`, `CLAUDE.md` mentions context caching is configurable via `ENABLE_CONTEXT_CACHE`
- Current mitigation: Controlled via environment flag
- Recommendations:
  1. Document cache TTL and eviction policies
  2. Implement cache purge endpoint for when user requests data deletion
  3. Add audit logging of what data is cached
  4. Test cache behavior across credential rotation scenarios

## Performance Bottlenecks

**Supabase Query Timeouts in list_templates:**
- Problem: Template listing can timeout after 3 seconds, falls back to seed data; repeated failures degrade user experience
- Files: `app/workflows/engine.py` (lines 46-88)
- Cause: Remote database queries over network may exceed 3s timeout, especially on high latency connections or during database slow queries
- Improvement path:
  1. Add database index on `workflow_templates.lifecycle_status` and `workflow_templates.personas_allowed`
  2. Implement client-side caching of template list with conditional TTL
  3. Increase timeout to 5s with metrics collection to understand actual p95 latencies
  4. Move frequently-accessed templates to Redis cache layer
  5. Pre-compute and cache template metadata on application startup

**Session Event Loading Unbounded:**
- Problem: Session events can reach 80 items by default (SESSION_MAX_EVENTS), compacted for context but still large payload
- Files: `app/persistence/supabase_session_service.py` (lines 20-32)
- Cause: No limit on event payload size; large binary data (images, videos) in events causes context window bloat even after truncation
- Improvement path:
  1. Implement streaming/pagination for session events instead of loading all at once
  2. Add separate storage for binary assets outside session event payload
  3. Implement semantic compression of old events (summarize conversations)
  4. Set max single-event payload size limit to prevent runaway data

**Skills Auto-Mapped Large File:**
- Problem: Auto-generated skills file is 1721 lines and grows with each new skill addition
- Files: `app/skills/custom/auto_mapped_skills.py`
- Cause: All skill metadata inlined in single file; no lazy loading or dynamic skill discovery
- Improvement path:
  1. Split into per-skill files with dynamic import on demand
  2. Implement lazy skill loading from database instead of in-memory structures
  3. Add skill metadata caching with invalidation strategy
  4. Move skill knowledge content to separate markdown files (CDN or object storage)

**Director Service Multi-Step Processing:**
- Problem: Video director service orchestrates multiple async calls (rendering, voiceovers, music) but has no batching or optimization
- Files: `app/services/director_service.py` (760 lines), `app/services/remotion_render_service.py` (892 lines)
- Cause: Sequential or poorly parallelized service calls; repeated re-computation of storyboards
- Improvement path:
  1. Add batch processing for multiple scenes in one render call
  2. Implement memoization of storyboard generation results
  3. Add job queueing (Bull/RQ) for async rendering instead of inline await
  4. Profile service to identify slowest steps (likely Remotion renders)

## Fragile Areas

**Workflow Template Fallback Chain:**
- Files: `app/workflows/engine.py` (lines 46-107)
- Why fragile: Triple fallback (main query → legacy columns → seed data) with schema detection via error message parsing; if schema changes slightly, detection fails silently and uses wrong fallback
- Safe modification:
  1. Query database schema metadata first to determine available columns
  2. Test all three fallback paths independently in CI
  3. Add version field to track migration status
  4. Log which fallback was used for debugging
- Test coverage: No test coverage visible for fallback paths

**Auto-Mapped Skills Generation:**
- Files: `app/skills/custom/auto_mapped_skills.py`
- Why fragile: Entire file is machine-generated; manual edits are lost on regeneration; skill descriptions contain TODOs that may confuse users; no schema validation
- Safe modification: Never manually edit; regenerate via skill mapping tool; if custom logic needed, move to separate file
- Test coverage: No tests verify skill definitions match schema

**MCP Connector Tool Access:**
- Files: `app/mcp/connector.py` (lines 173-199)
- Why fragile: get_mcp_tools() function references tools by name as strings; if tool is refactored or renamed, import fails with cryptic error; no validation that tools are actually loadable
- Safe modification:
  1. Add import-time validation of all tool modules
  2. Test that tool names match available functions
  3. Add try-except around imports with clear error messages
- Test coverage: No import validation tests

**Report Format Support Hardcoded:**
- Files: `app/services/report_scheduler.py`
- Why fragile: Only PPTX is actually implemented; PDF/XLSX are stubs that return empty strings; no validation at schedule creation time means users create schedules that silently fail
- Safe modification:
  1. Validate report format is implemented before accepting schedule
  2. Add unit tests for each format
  3. Implement all formats or explicitly reject unsupported ones
- Test coverage: Stub implementations untested

**Context Extractor Silent Failures:**
- Files: `app/agents/context_extractor.py` (multiple empty try-except blocks)
- Why fragile: Returns empty dict/None on any JSON error; caller can't distinguish between "no context found" and "JSON parsing failed"; could be processing malformed data repeatedly
- Safe modification:
  1. Create specific exception types for different failure modes
  2. Add logging before fallback
  3. Add metrics to detect parsing failures
- Test coverage: No tests for error cases

## Scaling Limits

**Redis Circuit Breaker Dependency:**
- Current capacity: Circuit breaker gracefully degrades, but if Redis is unavailable, every cache access attempts connection, causing latency spike
- Limit: Connection pool size (default likely 10-50) limits concurrent cache operations
- Scaling path:
  1. Increase Redis connection pool size based on concurrency metrics
  2. Implement request queuing when pool is exhausted
  3. Add Redis cluster for horizontal scaling
  4. Monitor cache hit rates and adjust TTLs

**Session Event Storage Unbounded Growth:**
- Current capacity: SESSION_MAX_EVENTS = 80, but database can accumulate unlimited old events
- Limit: Supabase storage quota and query performance degrade as sessions accumulate years of events
- Scaling path:
  1. Implement event archival to cold storage after 90 days
  2. Add hard retention policy (e.g., max 5000 events per session)
  3. Implement event summarization/compression
  4. Archive to Google Cloud Storage with periodic cleanup

**Database Query Timeout on Growth:**
- Current capacity: 3-second timeout acceptable at current query volumes
- Limit: As template/workflow tables grow, queries will exceed timeout
- Scaling path:
  1. Add database indexes on frequently-filtered columns
  2. Implement query pagination
  3. Move to read replicas for list queries
  4. Cache template metadata externally

## Dependencies at Risk

**Google Gemini API Fallback Chain:**
- Risk: Code assumes Gemini 2.5 Pro availability; fallback to Flash is hard-coded; if both are unavailable, agent fails with generic error
- Impact: Any Gemini API deprecation or quota exhaustion breaks agent execution
- Files: `app/fast_api_app.py`, `CLAUDE.md` mentions model fallback
- Migration plan:
  1. Add pluggable LLM provider interface to support Claude, OpenAI, etc.
  2. Implement graceful degradation with smaller models
  3. Add request-level model selection based on task complexity
  4. Test fallback paths regularly

**Supabase PostgreSQL Schema Migrations:**
- Risk: Alembic migrations may fail to roll back cleanly; no documented rollback procedure
- Impact: Database schema mismatch can cause complete service failure
- Files: `app/database/migrations/`
- Migration plan:
  1. Implement pre-migration validation (check schema state)
  2. Add automatic rollback on migration failure
  3. Test all migrations on staging with production-like data volumes
  4. Document manual rollback procedures

**Google Cloud Dependencies:**
- Risk: Vertex AI, Google Sheets API, Google Drive API, Cloud Run, Secret Manager all have service outages or quota limits
- Impact: Multi-region outage could affect Sheets/Drive integrations, video services, LLM inference
- Migration plan:
  1. Implement multi-cloud fallbacks for critical services
  2. Add quota monitoring and graceful degradation
  3. Cache external API responses aggressively
  4. Implement circuit breakers for all external services

## Missing Critical Features

**No Observability for Long-Running Workflows:**
- Problem: Workflow execution can take hours but has no progress visibility, ETA, or cancellation support
- Blocks: Users can't monitor/cancel stuck workflows; can't estimate completion time for planning
- Missing: Progress webhooks, workflow status API, cancellation endpoints
- Recommendation: Add workflow state machine with step-level status updates; implement Server-Sent Events for real-time progress

**No User Consent/Privacy Controls:**
- Problem: Agents can access user data (Gmail, Drive, Sheets) without explicit per-use consent
- Blocks: Compliance with privacy regulations (GDPR, CCPA); users can't audit what data agents access
- Missing: Data access logs, per-agent permission controls, data deletion workflows
- Recommendation: Implement access audit trail in database; add approval UI for first-time integrations

**No Workflow Version Control or Rollback:**
- Problem: Workflow templates are immutable once deployed; if a template has a bug, all executions fail until fixed
- Blocks: Can't safely iterate on templates; no audit trail of template changes
- Missing: Template versioning, rollback endpoints, change history
- Recommendation: Add version field to workflow_templates; implement semantic versioning; add UI for rolling back to previous versions

**No Cost Tracking or Budgeting:**
- Problem: Multiple expensive API calls (LLM, video rendering, image generation) have no cost visibility
- Blocks: Can't identify cost-saving opportunities; no alerting when spending exceeds budget
- Missing: API cost logging, cost aggregation dashboards, spending alerts
- Recommendation: Instrument all external API calls with cost tracking; add cost estimation before expensive operations

## Test Coverage Gaps

**No Tests for Fallback Paths:**
- What's not tested: Workflow template fallback chain (lines 77-107 of engine.py), MCP tool import failures, database connection pool exhaustion
- Files: `app/workflows/engine.py`
- Risk: Fallback logic may be broken and never discovered until production incident
- Priority: High - fallbacks are critical failure recovery paths

**No Error Case Testing in Services:**
- What's not tested: Report scheduler error handling, director service failures during rendering, session service database errors
- Files: `app/services/report_scheduler.py`, `app/services/director_service.py`, `app/persistence/supabase_session_service.py`
- Risk: Error handling code is untested; will fail or behave unexpectedly under error conditions
- Priority: High - error paths determine production reliability

**Skills Definition Validation Missing:**
- What's not tested: Auto-mapped skills definitions schema compliance, tool schema correctness, agent_ids references
- Files: `app/skills/custom/auto_mapped_skills.py`
- Risk: Invalid skill definitions silently fail at runtime; agent tool invocation fails with cryptic errors
- Priority: Medium - validation would catch generation errors early

**No Integration Tests for External APIs:**
- What's not tested: Web search, web scraping, form handler, MCP tool actual functionality with real external services
- Files: `app/mcp/tools/web_search.py`, `app/mcp/tools/web_scrape.py`
- Risk: External APIs may change interface; mocks may not catch breaking changes
- Priority: Medium - integration tests expensive but necessary for critical paths

---

*Concerns audit: 2026-03-11*

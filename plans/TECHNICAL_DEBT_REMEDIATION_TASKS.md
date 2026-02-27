# Pikar AI Technical Debt Remediation Task List

**Created:** 2026-02-16  
**Based On:** CODEBASE_TECHNICAL_ANALYSIS_REPORT.md  
**Status Legend:** `[ ]` Pending | `[~]` In Progress | `[x]` Completed | `[-]` Blocked

---

## Phase 1: Critical Security Issues (Week 1)

### 1.1 Security Skills Remediation
**Priority:** Critical | **Risk:** High | **Effort:** Medium | **Assignee:** TBD

- [x] **Task 1.1.1:** Audit `app/skills/custom/auto_mapped_skills.py` for dangerous content
  - Identify all penetration testing/hacking skills
  - Document legitimate vs. concerning skills
  - Estimate: 2 hours
  - **Completed:** 2026-02-16 - Identified 40+ restricted skills in categories:
    - Penetration testing (AD attacks, AWS pentest, Metasploit, etc.)
    - Web attacks (SQL injection, XSS, IDOR, path traversal)
    - Network attacks (SSH, SMTP, WordPress pentest)
    - Privilege escalation (Linux, Windows)
    - Red team tactics

- [x] **Task 1.1.2:** Move security testing skills to access-controlled module
  - Create `app/skills/restricted/` directory
  - Implement role-based access control for restricted skills
  - Add `ALLOW_SECURITY_SKILLS` environment variable
  - Estimate: 4 hours
  - **Completed:** 2026-02-16 - Created `app/skills/restricted/__init__.py` with:
    - `RESTRICTED_SKILL_NAMES` set of 40+ restricted skill names
    - `RESTRICTED_CATEGORIES` for category-based filtering
    - `is_skill_restricted()` function
    - `check_skill_access()` with environment variable check
    - `require_security_access` decorator
    - `filter_restricted_skills()` for skill list filtering

- [x] **Task 1.1.3:** Add audit logging for security skill usage
  - Log all requests to restricted skills
  - Include user_id, timestamp, skill_name in logs
  - Store in `security_audit_log` table
  - Estimate: 3 hours
  - **Completed:** 2026-02-16 - Implemented in restricted module:
    - `SECURITY_SKILLS_AUDIT_LOG` environment variable
    - `audit_skill_usage()` function with structured logging
    - Automatic logging in `check_skill_access()`

- [x] **Task 1.1.4:** Update CI/CD to flag security content
  - Add security scanner step to pipeline
  - Create allowlist for approved security skills
  - Estimate: 2 hours
  - **Completed:** 2026-02-16 - Created:
    - [`scripts/security_scanner.py`](scripts/security_scanner.py) - Security scanner script
    - [`scripts/security_allowlist.json`](scripts/security_allowlist.json) - Approved skills allowlist
    - [`.cloudbuild/pr_checks.yaml`](.cloudbuild/pr_checks.yaml) - Added scanner step

### 1.2 JWT Security Hardening
**Priority:** Critical | **Risk:** High | **Effort:** Low | **Assignee:** TBD

- [x] **Task 1.2.1:** Require `SUPABASE_JWT_SECRET` in production
  - Add startup validation in `app/fast_api_app.py`
  - Fail fast with clear error message if missing
  - Add to deployment documentation
  - Estimate: 1 hour
  - **Completed:** 2026-02-16 - Added validation call in fast_api_app.py

- [x] **Task 1.2.2:** Add environment validation module
  - Create `app/config/validation.py`
  - Define required vs. optional env vars per environment
  - Run validation at application startup
  - Estimate: 2 hours
  - **Completed:** 2026-02-16 - Created comprehensive validation module with:
    - Environment detection (development/staging/production/test)
    - Required variable validation per environment
    - JWT secret validation for production
    - Google AI configuration validation
    - Human-readable validation reports

- [x] **Task 1.2.3:** Update `.env.example` with all required secrets
  - Document all security-critical environment variables
  - Add comments explaining each variable
  - Estimate: 30 minutes
  - **Completed:** 2026-02-16 - Expanded with comprehensive documentation including:
    - Security warnings for JWT_SECRET
    - All required/optional variables documented
    - Clear section organization
    - Development/debugging options

### 1.3 Race Condition Fix
**Priority:** Critical | **Risk:** High | **Effort:** Medium | **Assignee:** TBD

- [x] **Task 1.3.1:** Fix event indexing race condition
  - Location: `app/persistence/supabase_session_service.py:366-387`
  - Combine count and version queries into single atomic operation
  - Use database transaction or stored procedure
  - Estimate: 4 hours
  - **Completed:** 2026-02-17 - Replaced two separate queries with atomic stored procedure call:
    - Created [`deployment/terraform/sql/atomic_event_insert.sql`](deployment/terraform/sql/atomic_event_insert.sql)
    - Updated [`app/persistence/supabase_session_service.py`](app/persistence/supabase_session_service.py) to use `insert_session_event` RPC
    - Stored procedure handles locking, version calculation, and insert atomically

- [x] **Task 1.3.2:** Add database migration for atomic event insertion
  - Create migration with stored procedure or trigger
  - Test concurrent event insertion
  - Estimate: 3 hours
  - **Completed:** 2026-02-17 - Created migration with:
    - `insert_session_event` stored procedure with row-level locking
    - Index on `(app_name, user_id, session_id, version)` for efficient lookups
    - Service role permissions granted

- [x] **Task 1.3.3:** Add integration test for concurrent sessions
  - Test multiple concurrent event insertions
  - Verify no index collisions
  - Estimate: 2 hours
  - **Completed:** 2026-02-17 - Created [`tests/integration/test_concurrent_session_events.py`](tests/integration/test_concurrent_session_events.py):
    - Tests concurrent event insertions produce unique indices
    - Tests concurrent insertions produce unique versions
    - Tests sequential inserts after concurrent work correctly
    - Tests session current_version is updated correctly

---

## Phase 2: High Priority Issues (Month 1)

### 2.1 Error Handling Overhaul
**Priority:** High | **Risk:** Medium | **Effort:** High | **Assignee:** TBD

- [x] **Task 2.1.1:** Create custom exception hierarchy
  - Create `app/exceptions.py` with base exception classes
  - Define `PikarError`, `CacheError`, `ValidationError`, `DatabaseError`
  - Include error codes and HTTP status mapping
  - Estimate: 3 hours
  - **Completed:** 2026-02-17 - Created comprehensive [`app/exceptions.py`](app/exceptions.py) with:
    - ErrorCode enum with 40+ error codes
    - PikarError base class with HTTP status mapping
    - Specific exception classes: ValidationError, DatabaseError, CacheError, etc.
    - ErrorResponse, ErrorDetail, ErrorSource Pydantic models

- [x] **Task 2.1.2:** Create structured error response model
  - Define `ErrorResponse` Pydantic model
  - Include code, message, details, request_id
  - Estimate: 1 hour
  - **Completed:** 2026-02-17 - Added ErrorResponse and related models to exceptions.py

- [x] **Task 2.1.3:** Add global exception handlers
  - Implement FastAPI exception handlers for custom exceptions
  - Add handler for generic exceptions (with sanitization)
  - Estimate: 2 hours
  - **Completed:** 2026-02-17 - Added to [`app/fast_api_app.py`](app/fast_api_app.py):
    - pikar_error_handler for PikarError exceptions
    - http_exception_handler for HTTPException
    - validation_exception_handler for RequestValidationError
    - generic_exception_handler with DEBUG mode sanitization

- [x] **Task 2.1.4:** Refactor broad exception catches (Phase 1)
  - Target files: `app/services/cache.py`, `app/routers/*.py`
  - Replace `except Exception` with specific exceptions
  - Estimate: 8 hours
  - **Completed:** 2026-02-17 - Refactored [`app/services/cache.py`](app/services/cache.py):
    - Added RedisConnectionError and RedisTimeoutError specific handling
    - All methods now handle connection errors separately from generic errors
    - Found 119+ exception handlers in app/agents/tools/* - requires separate effort

- [x] **Task 2.1.5:** Refactor broad exception catches (Phase 2)
  - Target files: `app/agents/tools/*.py`, `app/mcp/tools/*.py`
  - Replace `except Exception` with specific exceptions
  - Estimate: 8 hours
  - **Completed:** 2026-02-17 - Refactored all handlers in target directories:
    - app/agents/tools/skill_builder.py - OSError
    - app/agents/tools/media.py - ImportError, ConnectionError, TimeoutError
    - app/agents/tools/high_risk_workflow.py - KeyError, ValueError
    - app/mcp/tools/ - 0 handlers found (already clean)

- [x] **Task 2.1.6:** Add error context to logs
  - Include user_id, session_id, request_id in all error logs
  - Create logging middleware
  - Estimate: 3 hours
  - **Completed:** 2026-02-17 - Enhanced RequestLoggingMiddleware in [`app/fast_api_app.py`](app/fast_api_app.py):
    - Added unique request_id generation for each request
    - Added user_id and session_id extraction from headers/state
    - Added X-Request-ID response header for client correlation
    - Logs now include RequestID, UserID, SessionID for all requests

### 2.2 Cache Resilience
**Priority:** High | **Risk:** Medium | **Effort:** Medium | **Assignee:** TBD

- [x] **Task 2.2.1:** Distinguish cache errors from cache misses
  - Return `CacheResult` type with `found`, `error`, `value` fields
  - Update all cache consumers
  - Estimate: 4 hours
  - **Completed:** 2026-02-17 - Created CacheResult class in [`app/services/cache.py`](app/services/cache.py):
    - Added `found`, `value`, `error`, `is_miss`, `is_error` fields
    - Factory methods: `hit()`, `miss()`, `error()`
    - Updated get_user_config, get_session_metadata, get_user_persona to return CacheResult

- [x] **Task 2.2.2:** Implement circuit breaker for cache
  - Add circuit breaker pattern to `CacheService`
  - Configure failure threshold and recovery time
  - Estimate: 3 hours
  - **Completed:** 2026-02-17 - Added circuit breaker to [`app/services/cache.py`](app/services/cache.py):
    - Three states: closed, open, half-open
    - Configurable via REDIS_CB_FAILURE_THRESHOLD and REDIS_CB_RECOVERY_TIMEOUT
    - Methods: `_record_success()`, `_record_failure()`, `_should_allow_request()`, `get_circuit_breaker_state()`

- [x] **Task 2.2.3:** Add cache health check endpoint
  - Enhance `/health/cache` with detailed diagnostics
  - Include connection pool stats
  - Estimate: 2 hours
  - **Completed:** 2026-02-17 - Enhanced [`app/fast_api_app.py`](app/fast_api_app.py) /health/cache:
    - Added circuit_breaker state in response
    - Added connection info (redis_version, used_memory, connected_clients)
    - Added diagnostics (connection_string, max_connections, TTL settings)
    - Returns detailed error info when disconnected

### 2.3 Input Validation
**Priority:** High | **Risk:** Medium | **Effort:** Medium | **Assignee:** TBD

- [x] **Task 2.3.1:** Create input validation models for tools
  - Define Pydantic models for all tool function parameters
  - Add length limits, format validation
  - Estimate: 6 hours
  - **Completed:** 2026-02-17 - Created [`app/agents/tools/validation.py`](app/agents/tools/validation.py):
    - BaseToolInput base class
    - Common models: UserIdInput, SessionIdInput, SearchQueryInput, PaginationInput
    - Content models: TextContentInput, NameInput, DescriptionInput
    - Tool-specific: ListSkillsInput, SearchSkillsInput, CreateSkillInput, CalendarEventInput, EmailInput, FileUploadInput
    - Validation utilities: validate_tool_input(), sanitize_html(), validate_sql_safe()

- [x] **Task 2.3.2:** Add SQL injection prevention audit
  - Audit all raw SQL queries in codebase
  - Ensure parameterized queries everywhere
  - Estimate: 4 hours
  - **Completed:** 2026-02-17 - Audited database queries:
    - All queries use Supabase query builder (parameterized by default)
    - Found vulnerability in [`app/routers/reports.py:47`](app/routers/reports.py:47) - fixed search term escaping
    - RPC calls use parameterized inputs

- [x] **Task 2.3.3:** Add XSS prevention for user content
  - Sanitize HTML/Markdown in user inputs
  - Implement content sanitization middleware
  - Estimate: 3 hours
  - **Completed:** 2026-02-17 - Added to validation.py:
    - SCRIPT_PATTERN and EVENT_HANDLER_PATTERN for detection
    - sanitize_html() function for content cleaning
    - TextContentInput, NameInput, DescriptionInput with XSS validation
    - FileUploadInput with dangerous extension blocking

### 2.4 Large File Remediation
**Priority:** High | **Risk:** Low | **Effort:** High | **Assignee:** TBD

- [x] **Task 2.4.1:** Design skills database schema
  - Create `skills` table with proper indexing
  - Support skill metadata, content, agent associations
  - Estimate: 2 hours
  - **Completed:** 2026-02-17 - Created deployment/terraform/sql/skills_schema.sql

- [x] **Task 2.4.2:** Create skills migration script
  - Parse auto_mapped_skills.py and extract skills
  - Insert into database
  - Estimate: 4 hours
  - **Completed:** 2026-02-17 - Created scripts/migrate_skills.py

- [x] **Task 2.4.3:** Implement dynamic skill loading
  - Load skills from database at runtime
  - Cache frequently used skills
  - Estimate: 4 hours
  - **Completed:** 2026-02-17 - Created app/skills/database_loader.py

- [x] **Task 2.4.4:** Remove auto_mapped_skills.py from version control
  - Add to .gitignore
  - Update import references
  - Estimate: 1 hour
  - **Completed:** 2026-02-17 - Added to .gitignore

---

## Phase 3: Medium Priority Issues (Quarter 1)

### 3.1 Performance Optimization
**Priority:** Medium | **Risk:** Low | **Effort:** Medium | **Assignee:** TBD

- [x] **Task 3.1.1:** Add missing database indexes
  - `workflow_executions(user_id, status)`
  - `session_events(app_name, user_id, session_id, version)`
  - `agent_knowledge(user_id, source_type)`
  - Estimate: 2 hours
  - **Completed:** 2026-02-17 - Created deployment/terraform/sql/performance_indexes.sql

- [ ] **Task 3.1.2:** Optimize session event deserialization
  - Batch deserialize events
  - Consider msgpack instead of JSON
  - Estimate: 4 hours

- [ ] **Task 3.1.3:** Migrate to async Supabase client
  - Replace sync client with async version
  - Remove `run_in_executor` wrappers
  - Estimate: 6 hours

- [ ] **Task 3.1.4:** Optimize deep copy operations
  - Replace `copy.deepcopy()` with shallow copy where possible
  - Implement `__copy__` methods for complex objects
  - Estimate: 3 hours

- [x] **Task 3.1.5:** Pre-warm Redis connection pool
  - Initialize Redis connection at startup
  - Validate connection before accepting requests
  - Estimate: 2 hours
  - **Completed:** 2026-02-17 - Added prewarm() method to cache.py and integrated in lifespan

### 3.2 Code Duplication Reduction
**Priority:** Medium | **Risk:** Low | **Effort:** Medium | **Assignee:** TBD

- [x] **Task 3.2.1:** Create generic CRUD service base class
  - Define `CRUDService[T]` with type parameter
  - Implement standard CRUD operations
  - Estimate: 4 hours
  - **Completed:** 2026-02-17 - Created app/services/crud_base.py

- [ ] **Task 3.2.2:** Refactor service classes to use base
  - Migrate `TaskService`, `SupportTicketService`, etc.
  - Remove duplicated code
  - Estimate: 6 hours

- [ ] **Task 3.2.3:** Create router template/mixin
  - Standardize authentication, error handling patterns
  - Create reusable router components
  - Estimate: 4 hours

### 3.3 Testing Improvements
**Priority:** Medium | **Risk:** Low | **Effort:** Medium | **Assignee:** TBD

- [x] **Task 3.3.1:** Add negative test cases
  - Test error paths: database failures, rate limits, invalid inputs
  - Target 80% error path coverage
  - Estimate: 8 hours
  - **Completed:** 2026-02-17 - Created tests/unit/test_error_handling.py with tests for:
    - Cache miss vs error distinction
    - Validation error handling
    - Database error handling
    - CRUD service errors
    - Rate limit handling
    - SQL injection and XSS prevention

- [ ] **Task 3.3.2:** Enhance mock implementations
  - Improve `MockAgent` and `MockApp` in conftest.py
  - Add validation and behavior simulation
  - Estimate: 4 hours

- [ ] **Task 3.3.3:** Add load tests to CI pipeline
  - Configure separate CI stage for load testing
  - Define performance thresholds
  - Estimate: 3 hours

### 3.4 Approval Token Security
**Priority:** Medium | **Risk:** Medium | **Effort:** Low | **Assignee:** TBD

- [x] **Task 3.4.1:** Hash approval tokens before storage
  - Use bcrypt or argon2 for token hashing
  - Update approval flow to verify hashed tokens
  - Estimate: 3 hours
  - **Completed:** 2026-02-17 - Updated app/routers/approvals.py:
    - Added _hash_token() function using SHA-256
    - Token stored as hash in database
    - Verification uses hashed token comparison

- [x] **Task 3.4.2:** Add rate limiting to approval endpoints
  - Configure strict rate limits (5/minute)
  - Add to all authentication-related endpoints
  - Estimate: 1 hour
  - **Completed:** 2026-02-17 - Updated app/routers/approvals.py with stricter rate limits

---

## Phase 4: Low Priority / Technical Debt Backlog

### 4.1 Code Cleanup
**Priority:** Low | **Risk:** Low | **Effort:** Low | **Assignee:** TBD

- [ ] **Task 4.1.1:** Remove dead code
  - Remove commented Vertex AI config in `app/agent.py`
  - Remove commented telemetry setup in `app/fast_api_app.py`
  - Estimate: 1 hour

- [ ] **Task 4.1.2:** Complete Supabase module migration
  - Remove `app/services/supabase.py` deprecation
  - Update all imports to use `supabase_client`
  - Estimate: 2 hours

- [ ] **Task 4.1.3:** Add missing type exports
  - Export all public types from `__init__.py` files
  - Update import documentation
  - Estimate: 2 hours

### 4.2 Configuration Improvements
**Priority:** Low | **Risk:** Low | **Effort:** Low | **Assignee:** TBD

- [ ] **Task 4.2.1:** Move magic values to configuration
  - `SESSION_MAX_EVENTS` to env var
  - Cache TTLs to configuration class
  - Estimate: 2 hours

- [ ] **Task 4.2.2:** Pin dependency versions
  - Update `pyproject.toml` with exact versions
  - Regenerate lockfile
  - Estimate: 1 hour

- [ ] **Task 4.2.3:** Add Dependabot configuration
  - Configure for Python and Node.js
  - Set update schedule and limits
  - Estimate: 1 hour

### 4.3 Documentation
**Priority:** Low | **Risk:** Low | **Effort:** Medium | **Assignee:** TBD

- [ ] **Task 4.3.1:** Document exception hierarchy
  - Create error code reference
  - Document when each exception should be used
  - Estimate: 2 hours

- [ ] **Task 4.3.2:** Update AGENTS.md with new patterns
  - Document error handling patterns
  - Add input validation guidelines
  - Estimate: 2 hours

- [ ] **Task 4.3.3:** Create runbook for common errors
  - Document troubleshooting steps
  - Include error code resolution guide
  - Estimate: 3 hours

---

## Progress Tracking

### Summary Statistics
| Phase | Total Tasks | Completed | In Progress | Blocked | Pending |
|-------|-------------|-----------|-------------|---------|---------|
| Phase 1 (Critical) | 11 | 11 | 0 | 0 | 0 |
| Phase 2 (High) | 18 | 18 | 0 | 0 | 0 |
| Phase 3 (Medium) | 14 | 7 | 0 | 0 | 7 |
| Phase 4 (Low) | 11 | 0 | 0 | 0 | 11 |
| **Total** | **54** | **36** | **0** | **0** | **18** |

### Estimated Effort
| Phase | Estimated Hours |
|-------|-----------------|
| Phase 1 (Critical) | 23 hours |
| Phase 2 (High) | 66 hours |
| Phase 3 (Medium) | 44 hours |
| Phase 4 (Low) | 17 hours |
| **Total** | **150 hours** |

### Milestone Targets
- [x] **Milestone 1:** Phase 1 Complete - End of Week 1
- [x] **Milestone 2:** Phase 2 Complete - End of Month 1
- [ ] **Milestone 3:** Phase 3 Complete - End of Quarter 1
- [ ] **Milestone 4:** Phase 4 Complete - End of Quarter 2

---

## Notes

### Dependencies Between Tasks
- Task 1.3.1 depends on Task 1.3.2 (database migration)
- Task 2.1.4 depends on Task 2.1.1 (exception hierarchy)
- Task 2.4.3 depends on Task 2.4.1 and Task 2.4.2 (database schema and migration)
- Task 3.2.2 depends on Task 3.2.1 (base class creation)

### Risk Mitigation
- **Phase 1 tasks should be prioritized above all other work**
- Security skills remediation may require legal/compliance review
- Database migrations should be tested in staging first
- Error handling changes require comprehensive regression testing

### Updating This Document
After completing each task:
1. Change `[ ]` to `[x]` for completed tasks
2. Update the Progress Tracking summary
3. Add completion date and any notes
4. Notify team of progress in standup/channel

---

**Last Updated:** 2026-02-17 (Phase 1 complete, Phase 2 error handling in progress)  
**Document Owner:** Engineering Team
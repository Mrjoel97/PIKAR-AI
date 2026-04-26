# Requirements: pikar-ai v10.0

**Defined:** 2026-04-26
**Core Value:** Users describe what they want in natural language and the system autonomously generates, manages, and grows their business operations

## v10.0 Requirements

Requirements for Platform Hardening & Quality milestone. Each maps to roadmap phases.

### Security

- [ ] **SEC-01**: Webhook endpoints return HTTP 500 when signing secret is unconfigured instead of processing unauthenticated payloads (Linear, Asana)
- [ ] **SEC-02**: Slack interact handler validates response_url against *.slack.com allowlist before issuing outbound POST (SSRF prevention)
- [ ] **SEC-03**: resolve_request_user_id defaults allow_header_fallback=False; x-user-id header never used for authorization decisions
- [ ] **SEC-04**: dompurify added as explicit frontend dependency with typeof window guard for SSR safety

### Performance

- [ ] **PERF-01**: 20+ sync tool wrappers converted from ThreadPoolExecutor+asyncio.run to native async def with direct await
- [ ] **PERF-02**: N+1 sequential writes in workflow engine resume, session rollback, and session fork replaced with batch operations
- [ ] **PERF-03**: Analytics aggregator uses SQL COUNT(DISTINCT) or Supabase count aggregate instead of fetching full rows to count in Python
- [ ] **PERF-04**: Tool cache uses bounded TTLCache with maxsize; Redis key namespace enforced via REDIS_KEY_PREFIXES constants; generic cache methods guard connection

### Architecture

- [ ] **ARCH-01**: SupabaseSessionService methods wrapped with circuit breaker; retry set expanded to cover httpx.HTTPStatusError (5xx responses)
- [ ] **ARCH-02**: Rate limiting falls back to in-process SlowAPI limiter when Redis circuit breaker opens; CRITICAL alert logged
- [ ] **ARCH-03**: Workflow concurrent-execution check made atomic via Postgres advisory lock, DB constraint, or single INSERT...WHERE subquery
- [ ] **ARCH-04**: OpenAPI-to-TypeScript codegen established in CI pipeline; manually maintained frontend types in services/*.ts replaced with generated types

### Agent Quality

- [ ] **AGT-01**: Sales agent parent model upgraded from get_fast_model() (Flash) to get_model() (Pro) with DEEP_AGENT_CONFIG
- [ ] **AGT-02**: Admin agent decomposed into 4-5 focused sub-agents (SystemHealth, UserManagement, Billing, Governance); context callbacks added
- [ ] **AGT-03**: HR, Operations, and Customer Support agents upgraded from ROUTING_AGENT_CONFIG (max_output_tokens=1024) to DEEP_AGENT_CONFIG (max_output_tokens=4096)
- [ ] **AGT-04**: Missing shared instruction blocks (escalation, skills registry, self-improvement) added to Sales, Operations, Compliance, Customer Support, Reporting, and Research agents
- [ ] **AGT-05**: search_knowledge moved from app.agents.content.tools to app.agents.tools/knowledge.py; cross-agent tool duplication (blog pipeline, video generation, start_initiative_from_idea) resolved

## Future Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Deeper Performance

- **PERF-F01**: SSE event loop optimized (merged queue pattern replacing dual-task polling)
- **PERF-F02**: Session state update optimized (lightweight get_session_state instead of full session+events fetch)
- **PERF-F03**: SSE connection counter moved from Redis SCAN to atomic INCR/DECR counter

### Deeper Architecture

- **ARCH-F01**: API versioning with /v1/ prefix on all routes
- **ARCH-F02**: Database migration naming standardized (exclusively timestamp-based)
- **ARCH-F03**: Pre-SSE-stream Supabase calls parallelized with asyncio.gather

### Deeper Agent Quality

- **AGT-F01**: Orphaned financial tools (save_finance_assumption, list_finance_assumptions) wired or removed
- **AGT-F02**: Dead shared instruction blocks (TLDR, INTENT_CLARIFICATION, CROSS_AGENT_HELP) removed or adopted
- **AGT-F03**: Research agent factory updated with persona parameter for consistency
- **AGT-F04**: Deep research daily quota per user via Redis counter

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full SSE architecture rewrite | Current SSE works; optimizations are incremental, not rewrite |
| Gemini 3 migration | Planned separately per memory (Oct 2026+); different scope entirely |
| New feature development | v10.0 is hardening only; no new user-facing capabilities |
| Frontend redesign | Styling/UX not in scope for hardening milestone |
| Admin agent UI changes | Backend decomposition only; admin frontend unchanged |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SEC-01 | TBD | Pending |
| SEC-02 | TBD | Pending |
| SEC-03 | TBD | Pending |
| SEC-04 | TBD | Pending |
| PERF-01 | TBD | Pending |
| PERF-02 | TBD | Pending |
| PERF-03 | TBD | Pending |
| PERF-04 | TBD | Pending |
| ARCH-01 | TBD | Pending |
| ARCH-02 | TBD | Pending |
| ARCH-03 | TBD | Pending |
| ARCH-04 | TBD | Pending |
| AGT-01 | TBD | Pending |
| AGT-02 | TBD | Pending |
| AGT-03 | TBD | Pending |
| AGT-04 | TBD | Pending |
| AGT-05 | TBD | Pending |

**Coverage:**
- v10.0 requirements: 17 total
- Mapped to phases: 0
- Unmapped: 17

---
*Requirements defined: 2026-04-26*
*Last updated: 2026-04-26 after initial definition*

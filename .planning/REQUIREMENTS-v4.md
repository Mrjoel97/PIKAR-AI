# Requirements: pikar-ai v4.0 Production Scale & Persona Readiness

**Defined:** 2026-03-25
**Core Value:** Users describe what they want and the system autonomously generates and manages business operations

## v4.0 Requirements

Requirements for production scale targeting 1000+ concurrent users. Each maps to roadmap phases.

### App Server

- [ ] **SERV-01**: Backend runs with multiple uvicorn workers (4+ by default, configurable via WEB_CONCURRENCY)
- [ ] **SERV-02**: Gunicorn process manager wraps uvicorn workers with automatic restart on crash
- [ ] **SERV-03**: Concurrency limit configured per worker to prevent connection exhaustion (--limit-concurrency)
- [ ] **SERV-04**: Request timeout configured to prevent hanging connections (--timeout-keep-alive)
- [ ] **SERV-05**: Graceful shutdown drains active SSE connections before worker termination

### Database Scalability

- [ ] **DBSC-01**: Default thread pool executor sized to 200+ workers for asyncio.to_thread Supabase calls
- [ ] **DBSC-02**: Supabase connection pool configurable and increased to 200 for production
- [ ] **DBSC-03**: JWT verification uses fast local-only path (no Supabase network call) for hot-path auth
- [ ] **DBSC-04**: Connection pool health metrics exposed via /health/connections endpoint

### SSE Streaming

- [ ] **SSES-01**: SSE connection tracking backed by Redis (not in-memory) for multi-replica awareness
- [ ] **SSES-02**: Per-user SSE connection limit enforced across all Cloud Run replicas via Redis
- [ ] **SSES-03**: Backpressure mechanism rejects new SSE connections when server load exceeds threshold
- [ ] **SSES-04**: Stale SSE connections automatically cleaned up on process crash/restart via Redis TTL
- [ ] **SSES-05**: Total active SSE connection count exposed via health endpoint

### Distributed Rate Limiting

- [ ] **RATE-01**: API rate limiting backed by Redis sliding window (replacing per-process slowapi)
- [ ] **RATE-02**: SSE connection rate limiting backed by Redis
- [ ] **RATE-03**: MCP external API rate limiting backed by Redis (replacing per-process token bucket)
- [ ] **RATE-04**: Persona-tier rate limits enforced consistently across all replicas
- [ ] **RATE-05**: Rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining, Retry-After) included in responses

### Authentication Optimization

- [ ] **AUTH-01**: Validated JWT tokens cached in LRU cache with 60-second TTL to avoid repeated verification
- [ ] **AUTH-02**: verify_token() uses fast local JWT validation only — eliminates per-request supabase.auth.get_user() network call
- [ ] **AUTH-03**: Frontend session monitor polling interval increased from 60s to 5min to reduce auth API load
- [ ] **AUTH-04**: Token refresh failure triggers graceful re-login flow (not hard redirect)

### Security Hardening

- [ ] **SECU-01**: Content-Security-Policy header configured with appropriate directives for the application
- [ ] **SECU-02**: Referrer-Policy header set to strict-origin-when-cross-origin
- [ ] **SECU-03**: Request body size limit enforced (10MB default, configurable) via FastAPI middleware
- [ ] **SECU-04**: CORS allowed origins restricted to explicit production domains (no wildcard in production)
- [ ] **SECU-05**: X-XSS-Protection header added for legacy browser protection

### Observability

- [ ] **OBSV-01**: Sentry SDK integrated in Python backend with automatic exception capture and performance tracing
- [ ] **OBSV-02**: Sentry SDK integrated in Next.js frontend with error boundary integration
- [ ] **OBSV-03**: OpenTelemetry traces exported to Cloud Trace with request-level span correlation
- [ ] **OBSV-04**: Request duration histograms tracked per endpoint for latency percentile monitoring
- [ ] **OBSV-05**: Alerting webhooks configured to notify Slack/email on health check failures and error spikes
- [ ] **OBSV-06**: Structured JSON logging with consistent field names for log aggregation

### Feature Flags

- [ ] **FLAG-01**: Feature flag store backed by Redis with configurable TTL and fallback defaults
- [ ] **FLAG-02**: Flags support per-user and per-persona targeting rules
- [ ] **FLAG-03**: Gradual rollout support with percentage-based user bucketing
- [ ] **FLAG-04**: Feature flag management API (CRUD) accessible from admin panel
- [ ] **FLAG-05**: Feature flag changes logged to audit trail with before/after values

### Persona Frontend

- [ ] **PFUI-01**: Each persona has a distinct dashboard layout with persona-specific widget sets and ordering
- [ ] **PFUI-02**: Sidebar navigation items differ by persona (solopreneur sees fewer items than enterprise)
- [ ] **PFUI-03**: Features gated by persona — enterprise-only features hidden for solopreneur users
- [ ] **PFUI-04**: Persona-specific onboarding flow with tailored first-action suggestions
- [ ] **PFUI-05**: Persona shell components provide distinct visual identity (beyond header color)

### LLM Cost Control

- [ ] **COST-01**: Per-user daily token budget tracked and enforced across all agent interactions
- [ ] **COST-02**: Token usage and estimated cost recorded per request in database
- [ ] **COST-03**: Burst queue throttles concurrent Gemini API calls to prevent quota exhaustion
- [ ] **COST-04**: Usage dashboard shows per-user token consumption and cost trends
- [ ] **COST-05**: Budget threshold alerts notify user when approaching daily limit

### Redis Scaling

- [ ] **RDSC-01**: Redis connection pool increased to 200 max connections for production
- [ ] **RDSC-02**: Per-operation Redis latency tracked and exposed via health endpoint
- [ ] **RDSC-03**: Redis memory usage monitoring with alert threshold
- [ ] **RDSC-04**: Key namespace documented and consistent prefix conventions enforced

### Persona Backend Enforcement

- [ ] **PBEN-01**: Persona-tier enforcement middleware validates feature access against persona policy
- [ ] **PBEN-02**: Subscription/billing hooks gate persona tier upgrades (prepare integration points)
- [ ] **PBEN-03**: Agent tool availability gated by persona (solopreneur sees subset of tools)
- [ ] **PBEN-04**: Persona usage analytics tracked per interaction for capacity planning

## v5.0 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Load Testing

- **LOAD-01**: Automated load test suite simulating 1000+ concurrent SSE connections
- **LOAD-02**: Performance regression tests integrated into CI pipeline

### Advanced Scaling

- **ASCL-01**: Horizontal auto-scaling policies for Cloud Run based on SSE connection count
- **ASCL-02**: Database read replicas for query-heavy analytics endpoints

## Out of Scope

| Feature | Reason |
|---------|--------|
| WebSocket migration | SSE with Redis-backed tracking sufficient for current scale target |
| Database sharding | Supabase single-instance sufficient for 1000+ users |
| CDN for API responses | Not needed — dynamic content, CDN only for static assets (already handled by Next.js) |
| GraphQL layer | REST + SSE sufficient, GraphQL adds complexity without proportional benefit |
| Multi-region deployment | Single-region Cloud Run sufficient for initial 1000+ target |
| Custom APM solution | Sentry + OpenTelemetry covers needs; no need to build custom |

## Traceability

Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SERV-01 | Phase 24 | Pending |
| SERV-02 | Phase 24 | Pending |
| SERV-03 | Phase 24 | Pending |
| SERV-04 | Phase 24 | Pending |
| SERV-05 | Phase 24 | Pending |
| DBSC-01 | Phase 24 | Pending |
| DBSC-02 | Phase 24 | Pending |
| DBSC-03 | Phase 24 | Pending |
| DBSC-04 | Phase 24 | Pending |
| RDSC-01 | Phase 24 | Pending |
| RDSC-02 | Phase 24 | Pending |
| RDSC-03 | Phase 24 | Pending |
| RDSC-04 | Phase 24 | Pending |
| SSES-01 | Phase 25 | Pending |
| SSES-02 | Phase 25 | Pending |
| SSES-03 | Phase 25 | Pending |
| SSES-04 | Phase 25 | Pending |
| SSES-05 | Phase 25 | Pending |
| RATE-01 | Phase 25 | Pending |
| RATE-02 | Phase 25 | Pending |
| RATE-03 | Phase 25 | Pending |
| RATE-04 | Phase 25 | Pending |
| RATE-05 | Phase 25 | Pending |
| AUTH-01 | Phase 26 | Pending |
| AUTH-02 | Phase 26 | Pending |
| AUTH-03 | Phase 26 | Pending |
| AUTH-04 | Phase 26 | Pending |
| SECU-01 | Phase 26 | Pending |
| SECU-02 | Phase 26 | Pending |
| SECU-03 | Phase 26 | Pending |
| SECU-04 | Phase 26 | Pending |
| SECU-05 | Phase 26 | Pending |
| OBSV-01 | Phase 27 | Pending |
| OBSV-02 | Phase 27 | Pending |
| OBSV-03 | Phase 27 | Pending |
| OBSV-04 | Phase 27 | Pending |
| OBSV-05 | Phase 27 | Pending |
| OBSV-06 | Phase 27 | Pending |
| FLAG-01 | Phase 28 | Pending |
| FLAG-02 | Phase 28 | Pending |
| FLAG-03 | Phase 28 | Pending |
| FLAG-04 | Phase 28 | Pending |
| FLAG-05 | Phase 28 | Pending |
| PFUI-01 | Phase 29 | Pending |
| PFUI-02 | Phase 29 | Pending |
| PFUI-03 | Phase 29 | Pending |
| PFUI-04 | Phase 29 | Pending |
| PFUI-05 | Phase 29 | Pending |
| COST-01 | Phase 30 | Pending |
| COST-02 | Phase 30 | Pending |
| COST-03 | Phase 30 | Pending |
| COST-04 | Phase 30 | Pending |
| COST-05 | Phase 30 | Pending |
| PBEN-01 | Phase 31 | Pending |
| PBEN-02 | Phase 31 | Pending |
| PBEN-03 | Phase 31 | Pending |
| PBEN-04 | Phase 31 | Pending |

**Coverage:**
- v4.0 requirements: 57 total
- Mapped to phases: 57
- Unmapped: 0

---
*Requirements defined: 2026-03-25*
*Last updated: 2026-03-25 after roadmap creation — all 57 requirements mapped to phases 24-31*

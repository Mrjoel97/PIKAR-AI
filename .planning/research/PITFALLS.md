# Pitfalls Research

**Domain:** Adding 16 real-world integrations to existing async Python/FastAPI multi-agent system
**Researched:** 2026-04-04
**Confidence:** HIGH (OAuth pitfalls from OWASP guidelines; real-money API risks from Google Ads/Meta docs; async patterns from existing codebase audit)

## Critical Pitfalls (Security / Money)

### P1: Real-Money API Safety (Google Ads, Meta Ads)
**Risk:** Agent autonomously sets ad budget to $10,000/day without human approval
**Prevention:**
- ALL budget-changing operations MUST go through existing approval system (magic links)
- Hard budget cap stored in DB per user — API calls that exceed cap are rejected pre-flight
- Daily spend alerts via notification service
- Read-only mode by default — write access requires explicit "I understand this costs real money" confirmation
**Phase:** 43 (Ad Platforms)

### P2: OAuth Token Refresh Race Conditions
**Risk:** Multiple concurrent agent calls refresh the same token simultaneously → one gets invalidated
**Prevention:**
- Single `OAuthTokenManager` with async lock per user+provider combo
- Refresh token stored separately from access token
- Token refresh happens proactively (refresh when <5 min remaining, not on 401)
- Retry-after-refresh pattern: if 401 → acquire lock → check if already refreshed → refresh if not → retry
**Phase:** 39 (Integration Infrastructure)

### P3: Stripe Webhook Replay / Duplicate Processing
**Risk:** Stripe sends same webhook multiple times → duplicate financial records
**Prevention:**
- Idempotency key: store `event.id` in `webhook_events` with UNIQUE constraint
- INSERT ... ON CONFLICT DO NOTHING pattern
- Process only `event.type` values we explicitly handle (allowlist, not blocklist)
**Phase:** 41 (Financial Integrations)

### P4: SQL Injection via External Database Connectors
**Risk:** User or agent constructs SQL with unsanitized input against external database
**Prevention:**
- NEVER use string formatting for SQL — always parameterized queries
- Connection is READ-ONLY (set `default_transaction_read_only = true` at connection level)
- Query timeout enforced at connection level (30s max)
- Allowlist of permitted operations (SELECT only, no DDL/DML)
- Log all queries to audit trail
**Phase:** 46 (Analytics + Intelligence)

### P5: Email Sequence Reputation Damage
**Risk:** Automated email sequences without warm-up destroy sender reputation → all emails go to spam
**Prevention:**
- Daily send limit per user (start at 50/day, increase gradually)
- Bounce rate monitoring — pause sequence if bounce rate >5%
- Unsubscribe handling (CAN-SPAM compliance, one-click unsubscribe header)
- Domain warming guidance in onboarding
- Never send from shared IP — use user's own Resend/Gmail credentials
**Phase:** 42 (CRM + Email)

## High Pitfalls (Data Integrity / UX)

### P6: Bidirectional Sync Conflicts
**Risk:** User updates contact in both HubSpot and Pikar simultaneously → which wins?
**Prevention:**
- Last-write-wins with timestamp comparison (use HubSpot's `hs_lastmodifieddate`)
- Conflict detection: if both modified since last sync, flag for user resolution
- Sync direction configurable per field (HubSpot→Pikar, Pikar→HubSpot, bidirectional)
- Never auto-delete — only soft-delete with "deleted in HubSpot" flag
**Phase:** 42 (CRM + Email)

### P7: CSV Import Partial Failures
**Risk:** 5000-row CSV import fails at row 3000 → user doesn't know which rows succeeded
**Prevention:**
- Wrap in transaction with savepoints — rollback failed rows, commit good ones
- Return detailed error report: row number, field, error message
- Preview mode: validate first 100 rows before committing
- Progress tracking via SSE (not polling)
- Max file size limit (50MB) to prevent memory issues
**Phase:** 40 (Data I/O)

### P8: Webhook Delivery Failures
**Risk:** Outbound webhook target is down → events pile up → memory/storage issues
**Prevention:**
- Exponential backoff: 1s, 5s, 30s, 5min, 30min (5 attempts max)
- Dead letter queue: after 5 failures, move to `webhook_deliveries_failed` with reason
- Per-endpoint circuit breaker: after 10 consecutive failures, disable endpoint with notification
- Delivery retention: 30 days, then archive
**Phase:** 39 (Integration Infrastructure)

### P9: Shopify Rate Limiting (2 req/sec REST)
**Risk:** Agent makes 10 rapid Shopify calls → all get rate-limited → cascading failures
**Prevention:**
- Use GraphQL API (1000 points/sec) instead of REST (2/sec) — much more efficient
- Request queue with token bucket rate limiter
- Bulk operations for large data sets (Shopify's `bulkOperationRunQuery`)
- Cache product/order data locally with short TTL (5 min)
**Phase:** 41 (Financial Integrations)

### P10: Feature Gating Backward Compatibility (Solopreneur Unlock)
**Risk:** Changing feature_gating.py breaks existing persona behavior or stored user preferences
**Prevention:**
- Only ADD features to solopreneur tier — never remove from other tiers
- Feature gating changes are config-only (no migration needed)
- Test: existing startup/sme/enterprise users see no change
- The ONLY features restricted for solopreneur: team_management, shared_workspaces, team_analytics
**Phase:** 38 (Solopreneur Unlock)

### P11: Tool Rename Backward Compatibility
**Risk:** Stored references to old tool names (in workflows, session history) break
**Prevention:**
- Check if any workflow templates reference old tool names → update them
- Session history is display-only — old names in history are fine (cosmetic)
- Add aliases in tool registry: old_name → new_name for transition period
- Update org-chart display to show new names
**Phase:** 38 (Tool Rename)

## Medium Pitfalls (Performance / Cost)

### P12: External Database Connection Pool Exhaustion
**Risk:** Many users connecting to external databases → connection pool limits exceeded
**Prevention:**
- Max 3 connections per user per external database
- Connection idle timeout: 5 minutes
- Total pool limit per Pikar instance: 50 external connections
- Connection health check before query execution
**Phase:** 46

### P13: Continuous Intelligence API Cost
**Risk:** Scheduled monitoring burns through Tavily/Firecrawl API credits
**Prevention:**
- Cost tracking per monitoring job (`research_cost_tracker` pattern exists)
- Daily API budget limit per user
- Deduplication: don't re-scrape pages that haven't changed (use ETags/Last-Modified)
- Configurable frequency: hourly/daily/weekly per monitor
**Phase:** 46

### P14: PDF Generation Memory
**Risk:** WeasyPrint rendering large documents consumes excessive memory
**Prevention:**
- Page limit: max 50 pages per document
- Render in subprocess with memory limit (`resource.setrlimit`)
- Queue PDF generation through ai_jobs (not inline in request)
- Cache generated PDFs in Supabase Storage with TTL
**Phase:** 40

### P15: HubSpot API Rate Limit Handling
**Risk:** Burst of sync operations hits 100/10s limit → operations fail silently
**Prevention:**
- Token bucket rate limiter specific to HubSpot (matches their 100/10s limit)
- Use HubSpot's batch APIs for bulk operations (up to 100 records per batch)
- Respect `Retry-After` header on 429 responses
- Background sync jobs run at reduced rate (50/10s) to leave headroom for real-time ops
**Phase:** 42

### P16: Slack/Teams Message Formatting Divergence
**Risk:** Building messages for Slack Block Kit that don't translate to Teams Adaptive Cards
**Prevention:**
- Abstract notification as structured data (title, body, actions, fields)
- Platform-specific formatters: `slack_formatter.py`, `teams_formatter.py`
- Test both platforms in integration tests
- Graceful degradation: if rich formatting fails, fall back to plain text
**Phase:** 45

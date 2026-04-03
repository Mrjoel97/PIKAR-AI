# Architecture Research

**Domain:** Real-world integrations into existing FastAPI/ADK/Next.js system
**Researched:** 2026-04-04
**Confidence:** HIGH (all patterns derived from existing codebase audit; integration points verified against actual file paths)

## Integration Pattern

All new integrations follow the existing MCP tools pattern:
```
app/mcp/tools/<integration>.py     — HTTP/SDK calls, rate limiting, PII filtering
app/agents/tools/<integration>.py  — Agent-facing tool functions
app/services/<integration>.py      — Business logic, sync state, caching
supabase/migrations/               — Tables for sync state, credentials, cached data
```

### Shared Infrastructure (New)

**Credential Manager:** `app/services/integration_manager.py`
- Extends existing Fernet encryption from `app/services/encryption_service.py`
- `integration_credentials` table: per-user, per-provider OAuth tokens (encrypted)
- Shared `OAuthTokenManager`: token refresh, expiry tracking, race condition prevention
- Health check per integration (is token valid? is API reachable?)

**Sync State Tracker:** `integration_sync_state` table
- Last sync timestamp per integration per user
- Cursor/pagination token for incremental sync
- Error count + exponential backoff state

**Webhook Infrastructure:** `webhook_endpoints` + `webhook_events` + `webhook_deliveries` tables
- Inbound: FastAPI endpoint → HMAC verify → insert `webhook_events` → process via `ai_jobs`
- Outbound: Event trigger → queue in `webhook_deliveries` → deliver with retry (3 attempts, exponential backoff)

## New Components

| Component | Type | Purpose |
|-----------|------|---------|
| `app/services/integration_manager.py` | Service | Shared OAuth token management, credential CRUD, health checks |
| `app/services/hubspot_service.py` | Service | HubSpot CRUD: contacts, deals, pipelines, activities |
| `app/services/stripe_sync_service.py` | Service | Stripe transaction history import, reconciliation |
| `app/services/linear_service.py` | Service | Linear GraphQL: issues, projects, webhook processing |
| `app/services/asana_service.py` | Service | Asana REST: tasks, projects, webhook processing |
| `app/services/email_sequence_service.py` | Service | Sequence FSM, scheduling, tracking pixel processing |
| `app/services/google_ads_service.py` | Service | Google Ads: campaigns, ad groups, reporting |
| `app/services/meta_ads_service.py` | Service | Meta Marketing: campaigns, ad sets, insights |
| `app/services/shopify_service.py` | Service | Shopify GraphQL: orders, products, inventory, analytics |
| `app/services/document_generator.py` | Service | HTML→PDF (weasyprint), slides (python-pptx) |
| `app/services/data_import_service.py` | Service | CSV parse, validate, bulk upsert, progress tracking |
| `app/services/webhook_service.py` | Service | Webhook endpoint CRUD, delivery queue, retry logic |
| `app/services/slack_service.py` | Service | Slack: messages, channels, Block Kit, interactive components |
| `app/services/teams_service.py` | Service | MS Teams via Graph API: messages, channels |
| `app/services/external_db_service.py` | Service | External DB pool management, read-only query, timeout |
| `app/services/intelligence_scheduler.py` | Service | Scheduled research jobs, deduplication, cost tracking |
| `app/routers/integrations.py` | Router | Integration CRUD, OAuth callbacks, test connection |
| `app/routers/webhooks_general.py` | Router | Inbound webhook receiver with HMAC verification |
| `app/routers/data_io.py` | Router | CSV upload/download endpoints |
| `app/agents/tools/crm_tools.py` | Tools | HubSpot agent tools for SalesIntelligenceAgent |
| `app/agents/tools/stripe_sync_tools.py` | Tools | Revenue sync tools for FinancialAnalysisAgent |
| `app/agents/tools/pm_tools.py` | Tools | Linear/Asana tools for OperationsAgent |
| `app/agents/tools/email_sequence_tools.py` | Tools | Sequence tools for MarketingAutomationAgent |
| `app/agents/tools/ads_tools.py` | Tools | Google Ads + Meta tools for MarketingAutomationAgent |
| `app/agents/tools/shopify_tools.py` | Tools | Shopify tools for FinancialAnalysisAgent + MarketingAgent |
| `app/agents/tools/document_tools.py` | Tools | PDF/deck generation for all agents |
| `app/agents/tools/data_io_tools.py` | Tools | Import/export tools for DataAnalysisAgent |
| `app/agents/tools/webhook_tools.py` | Tools | Webhook management for OperationsAgent |
| `app/agents/tools/team_chat_tools.py` | Tools | Slack/Teams for CustomerSupportAgent + notifications |

## Modified Components

| Component | Changes |
|-----------|---------|
| `app/config/feature_gating.py` | Unlock solopreneur: add workflows, approvals, sales, reports, compliance, financial_forecasting |
| `frontend/src/config/featureGating.ts` | Mirror backend solopreneur unlock |
| `app/personas/behavioral_instructions.py` | Update solopreneur behavioral instructions for full-featured single user |
| `app/personas/policy_registry.py` | Update solopreneur policy (approval_posture, delegation_style, planning_horizon) |
| `app/agents/sales/agent.py` | Replace fake `manage_hubspot` with real CRM tools |
| `app/agents/financial/agent.py` | Add Stripe sync + Shopify revenue tools |
| `app/agents/marketing/agent.py` | Add real ads tools, email sequence tools |
| `app/agents/operations/agent.py` | Rename misleading tools, add webhook management |
| `app/agents/data/agent.py` | Add external DB tools, import/export tools |
| `app/agents/strategic/agent.py` | Add continuous intelligence tools |
| `app/agents/customer_support/agent.py` | Add Slack/Teams notification tools |
| `app/services/notification_service.py` | Add Slack/Teams delivery channels |
| `app/services/briefing_service.py` | Add Slack/Teams daily briefing delivery |
| `frontend/src/app/dashboard/configuration/page.tsx` | Add integration connection UIs for all new providers |
| Multiple agent instruction files | Update to reference new real tools instead of knowledge wrappers |

## Build Order (Dependency-Aware)

```
Phase 38: Solopreneur Unlock + Tool Rename (no deps, immediate trust improvement)
Phase 39: Integration Infrastructure (credential manager, webhook system, sync state)
Phase 40: Data I/O (CSV import/export, document generation — no external API deps)
Phase 41: Financial Integrations (Stripe sync, Shopify — extends existing Stripe)
Phase 42: CRM + Email (HubSpot, email sequences — needs credential infra)
Phase 43: Ad Platforms (Google Ads, Meta — needs credential infra + approval gates)
Phase 44: Project Management (Linear, Asana — needs credential infra + webhook system)
Phase 45: Communication (Slack, Teams notifications — needs webhook system)
Phase 46: Analytics + Intelligence (external DB, calendar automation, continuous monitoring)
Phase 47: Team Collaboration + Integration Polish (Zapier compat, team features, health dashboard)
```

## Data Flow: Sync Pattern

```
External Service → webhook → FastAPI endpoint → HMAC verify → webhook_events → ai_jobs → Integration Service → local tables → Agent notification (SSE)
```

```
Agent tool call → Integration Service → external API → update sync state → audit log → return to agent
```

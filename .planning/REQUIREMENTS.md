# Requirements: Pikar-AI v6.0

**Defined:** 2026-04-04
**Core Value:** Users describe what they want in natural language and the system autonomously executes real-world business actions — not just generates advice

## v6.0 Requirements

### Persona Unlock (SOLO)
- [x] **SOLO-01**: Solopreneur persona has full access to workflows, dynamic workflow generator, and workflow templates
- [x] **SOLO-02**: Solopreneur persona has full access to approvals, sales pipeline, and reports
- [x] **SOLO-03**: Solopreneur persona has full access to compliance suite and financial forecasting
- [x] **SOLO-04**: Solopreneur behavioral instructions updated to reflect full-featured single-user (not limited tier)
- [x] **SOLO-05**: Only team_management, shared_workspaces, and team_analytics remain restricted for solopreneur
- [x] **SOLO-06**: Frontend feature gating mirrors backend — solopreneur sees all non-team features without upgrade prompts

### Tool Honesty (TOOL)
- [x] **TOOL-01**: `manage_hubspot` renamed to `hubspot_setup_guide` (or replaced by real CRM tools)
- [x] **TOOL-02**: `run_security_audit` renamed to `security_checklist`
- [x] **TOOL-03**: `deploy_container` renamed to `container_deployment_guide`
- [x] **TOOL-04**: `architect_cloud_solution` renamed to `cloud_architecture_guide`
- [x] **TOOL-05**: `perform_seo_audit` renamed to `seo_fundamentals_guide`
- [x] **TOOL-06**: `generate_product_roadmap` renamed to `product_roadmap_guide`
- [x] **TOOL-07**: `design_rag_pipeline` renamed to `rag_architecture_guide`
- [x] **TOOL-08**: Org chart / agent capabilities display separates "Tools" (actions) from "Knowledge" (frameworks)

### Integration Infrastructure (INFRA)
- [x] **INFRA-01**: Integration credential manager stores OAuth tokens encrypted (Fernet) per user per provider
- [x] **INFRA-02**: OAuth token refresh manager handles concurrent refresh with async locking
- [x] **INFRA-03**: Integration health check endpoint reports status per connected service
- [x] **INFRA-04**: Webhook inbound receiver with HMAC-SHA256 verification and idempotency
- [x] **INFRA-05**: Webhook outbound delivery queue with exponential backoff retry (5 attempts)
- [x] **INFRA-06**: Webhook dead letter queue with per-endpoint circuit breaker
- [x] **INFRA-07**: Integration sync state tracking (cursor, last sync, error count per user per provider)
- [x] **INFRA-08**: Frontend integration configuration page shows connection status for all providers

### CRM Integration (CRM)
- [x] **CRM-01**: User can connect HubSpot account via OAuth from configuration page
- [x] **CRM-02**: Bidirectional contact sync between HubSpot and Pikar contacts table
- [x] **CRM-03**: User can view HubSpot deals and pipeline stages in Pikar dashboard
- [ ] **CRM-04**: Agent can create/update HubSpot contacts and deals via chat commands
- [ ] **CRM-05**: Agent responses are CRM-aware (agent sees deal context before responding to sales queries)
- [x] **CRM-06**: HubSpot webhook processing for real-time sync on contact/deal changes

### Financial Sync (FIN)
- [x] **FIN-01**: Stripe transaction history auto-imported into financial_records table
- [x] **FIN-02**: Revenue dashboard shows real Stripe data (payments, invoices, balance)
- [x] **FIN-03**: Stripe webhook handler creates financial_records on payment_intent.succeeded
- [x] **FIN-04**: Transaction categorization (revenue, refund, fee, payout) applied automatically
- [x] **FIN-05**: User can trigger manual full sync of Stripe history from configuration page

### E-commerce (SHOP)
- [x] **SHOP-01**: User can connect Shopify store via OAuth from configuration page
- [x] **SHOP-02**: Agent can list orders, products, and inventory from Shopify
- [x] **SHOP-03**: Sales analytics (revenue, orders, AOV, top products) available to FinancialAnalysisAgent
- [x] **SHOP-04**: Inventory alerts when stock falls below configurable threshold
- [x] **SHOP-05**: Shopify webhook processing for real-time order and inventory updates

### Project Management (PM)
- [x] **PM-01**: User can connect Linear account via OAuth from configuration page
- [x] **PM-02**: User can connect Asana account via OAuth from configuration page
- [x] **PM-03**: Bidirectional task sync — creating task in Pikar creates issue in Linear/Asana
- [x] **PM-04**: Status mapping between Pikar task states and Linear/Asana states
- [x] **PM-05**: Agent can list, create, and update Linear/Asana tasks via chat commands

### Email Automation (EMAIL)
- [x] **EMAIL-01**: User can create multi-step email sequences with templates and variables
- [x] **EMAIL-02**: Sequence scheduling with timezone-aware send times
- [x] **EMAIL-03**: Open and click tracking via tracking pixels and link wrapping
- [x] **EMAIL-04**: Sequence pause/resume on bounce rate threshold (>5%)
- [x] **EMAIL-05**: Daily send limit per user (configurable, default 50/day for warm-up)
- [ ] **EMAIL-06**: Agent can generate email sequence content based on campaign context

### Ad Platforms (ADS)
- [x] **ADS-01**: User can connect Google Ads account via OAuth from configuration page
- [x] **ADS-02**: User can connect Meta Ads account via OAuth from configuration page
- [x] **ADS-03**: Agent can create, pause, and resume ad campaigns (with mandatory approval gate for budget changes)
- [x] **ADS-04**: Performance reporting (impressions, clicks, conversions, spend) available to MarketingAutomationAgent
- [x] **ADS-05**: Budget pacing alerts when daily spend exceeds threshold
- [x] **ADS-06**: Hard budget cap per user per platform — API rejects operations exceeding cap
- [x] **ADS-07**: Agent can generate ad copy and creative briefs via ContentCreationAgent

### Document Generation (DOC)
- [x] **DOC-01**: Agent can generate PDF reports from any analysis output
- [x] **DOC-02**: PDF reports include user's branding (logo, colors from brand profile)
- [x] **DOC-03**: Agent can generate pitch deck slides (PowerPoint) from strategic planning output
- [x] **DOC-04**: Common templates available: financial report, project proposal, meeting summary, competitive analysis
- [x] **DOC-05**: Generated documents stored in Supabase Storage and linked to the conversation

### Data Import/Export (DATA)
- [x] **DATA-01**: User can upload CSV files with column mapping UI
- [x] **DATA-02**: CSV validation with row-level error reporting before commit
- [x] **DATA-03**: AI-assisted column mapping (suggest mappings from CSV headers)
- [x] **DATA-04**: User can export any data table (contacts, tasks, initiatives, financial records) to CSV
- [x] **DATA-05**: Import progress tracking via SSE for large files
- [x] **DATA-06**: Agent can trigger data imports and exports via chat commands

### Webhook/Zapier (HOOK)
- [x] **HOOK-01**: User can create outbound webhook endpoints for Pikar events (task.created, workflow.completed, etc.)
- [x] **HOOK-02**: Event catalog listing all available trigger events with payload schemas
- [x] **HOOK-03**: Zapier-compatible webhook format (standard JSON payload structure)
- [x] **HOOK-04**: Webhook delivery log with success/failure status visible in configuration page
- [x] **HOOK-05**: Agent can create and manage webhook endpoints via chat commands

### Slack/Teams Notifications (NOTIF)
- [x] **NOTIF-01**: User can connect Slack workspace via OAuth from configuration page
- [x] **NOTIF-02**: User can connect Microsoft Teams via Azure AD OAuth from configuration page
- [x] **NOTIF-03**: Configurable notification rules: which events → which channel
- [x] **NOTIF-04**: Approval buttons in Slack messages (approve/reject inline without leaving Slack)
- [x] **NOTIF-05**: Daily briefing auto-posted to configured Slack/Teams channel
- [x] **NOTIF-06**: Rich formatted messages (Slack Block Kit / Teams Adaptive Cards)

### External Data Analytics (XDATA)
- [x] **XDATA-01**: User can connect external PostgreSQL database from configuration page
- [x] **XDATA-02**: User can connect BigQuery project from configuration page
- [x] **XDATA-03**: Agent can run read-only SQL queries against connected external databases
- [x] **XDATA-04**: AI-generated SQL from natural language via DataAnalysisAgent
- [x] **XDATA-05**: Query results displayed as tables and charts in chat
- [x] **XDATA-06**: Connection uses strict read-only mode with 30-second query timeout

### Calendar Automation (CAL)
- [x] **CAL-01**: Agent can find optimal meeting times by querying free/busy across calendars
- [x] **CAL-02**: Agent can suggest optimal follow-up meeting times after sales calls (user confirms before booking)
- [x] **CAL-03**: Agent can generate recurring tasks from calendar patterns
- [x] **CAL-04**: Calendar-aware agent responses (agent knows about upcoming meetings and context)

### Continuous Intelligence (INTEL)
- [x] **INTEL-01**: User can create scheduled monitoring jobs for competitors, markets, or topics
- [x] **INTEL-02**: Monitoring runs on configurable schedule (daily, weekly) via workflow trigger service
- [x] **INTEL-03**: Results synthesized into intelligence briefs by ResearchAgent
- [x] **INTEL-04**: Knowledge graph updated with entities and findings from monitoring
- [x] **INTEL-05**: Alert notifications when significant changes detected (new products, pricing, news)

### Team Collaboration (TEAM)
- [x] **TEAM-01**: Team members can share initiatives and view shared workflow runs
- [x] **TEAM-02**: Team-level analytics dashboard showing aggregate KPIs
- [x] **TEAM-03**: Role-based visibility (team admin sees all, member sees assigned work)
- [x] **TEAM-04**: Activity feed showing team member actions on shared resources

## Future Requirements (v7.0+)

- **FUTURE-01**: Zapier-hosted app listing (requires Zapier partner approval)
- **FUTURE-02**: QuickBooks/Xero accounting integration
- **FUTURE-03**: Mobile push notifications (requires native app)
- **FUTURE-04**: Real-time collaborative editing (WebSocket-based)
- **FUTURE-05**: AI agent marketplace (custom agent sharing between users)
- **FUTURE-06**: Social media monitoring (separate from competitive intelligence)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full CRM UI recreation | Users should use HubSpot for deep CRM work; Pikar provides AI-augmented access |
| Full accounting system | Tax compliance risk; users should use QuickBooks/Xero |
| Automated bid management without approval | Real money risk — all budget changes require human approval |
| Full email service provider | Use Resend/SendGrid for infrastructure; Pikar orchestrates sequences |
| Write access to external databases | Security risk — read-only queries only |
| Full project management UI | Users should use Linear/Asana for sprint planning |
| Bulk email >1000/day | Deliverability risk without proper warm-up infrastructure |
| Real-time WebSocket sync | SSE + webhook polling sufficient for v6.0 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SOLO-01 | Phase 38 | Complete |
| SOLO-02 | Phase 38 | Complete |
| SOLO-03 | Phase 38 | Complete |
| SOLO-04 | Phase 38 | Complete |
| SOLO-05 | Phase 38 | Complete |
| SOLO-06 | Phase 38 | Complete |
| TOOL-01 | Phase 38 | Complete |
| TOOL-02 | Phase 38 | Complete |
| TOOL-03 | Phase 38 | Complete |
| TOOL-04 | Phase 38 | Complete |
| TOOL-05 | Phase 38 | Complete |
| TOOL-06 | Phase 38 | Complete |
| TOOL-07 | Phase 38 | Complete |
| TOOL-08 | Phase 38 | Complete |
| INFRA-01 | Phase 39 | Complete |
| INFRA-02 | Phase 39 | Complete |
| INFRA-03 | Phase 39 | Complete |
| INFRA-04 | Phase 39 | Complete |
| INFRA-05 | Phase 39 | Complete |
| INFRA-06 | Phase 39 | Complete |
| INFRA-07 | Phase 39 | Complete |
| INFRA-08 | Phase 39 | Complete |
| DATA-01 | Phase 40 | Complete |
| DATA-02 | Phase 40 | Complete |
| DATA-03 | Phase 40 | Complete |
| DATA-04 | Phase 40 | Complete |
| DATA-05 | Phase 40 | Complete |
| DATA-06 | Phase 40 | Complete |
| DOC-01 | Phase 40 | Complete |
| DOC-02 | Phase 40 | Complete |
| DOC-03 | Phase 40 | Complete |
| DOC-04 | Phase 40 | Complete |
| DOC-05 | Phase 40 | Complete |
| FIN-01 | Phase 41 | Complete |
| FIN-02 | Phase 41 | Complete |
| FIN-03 | Phase 41 | Complete |
| FIN-04 | Phase 41 | Complete |
| FIN-05 | Phase 41 | Complete |
| SHOP-01 | Phase 41 | Complete |
| SHOP-02 | Phase 41 | Complete |
| SHOP-03 | Phase 41 | Complete |
| SHOP-04 | Phase 41 | Complete |
| SHOP-05 | Phase 41 | Complete |
| CRM-01 | Phase 42 | Complete |
| CRM-02 | Phase 42 | Complete |
| CRM-03 | Phase 42 | Complete |
| CRM-04 | Phase 42 | Pending |
| CRM-05 | Phase 42 | Pending |
| CRM-06 | Phase 42 | Complete |
| EMAIL-01 | Phase 42 | Complete |
| EMAIL-02 | Phase 42 | Complete |
| EMAIL-03 | Phase 42 | Complete |
| EMAIL-04 | Phase 42 | Complete |
| EMAIL-05 | Phase 42 | Complete |
| EMAIL-06 | Phase 42 | Pending |
| ADS-01 | Phase 43 | Complete |
| ADS-02 | Phase 43 | Complete |
| ADS-03 | Phase 43 | Complete |
| ADS-04 | Phase 43 | Complete |
| ADS-05 | Phase 43 | Complete |
| ADS-06 | Phase 43 | Complete |
| ADS-07 | Phase 43 | Complete |
| PM-01 | Phase 44 | Complete |
| PM-02 | Phase 44 | Complete |
| PM-03 | Phase 44 | Complete |
| PM-04 | Phase 44 | Complete |
| PM-05 | Phase 44 | Complete |
| NOTIF-01 | Phase 45 | Complete |
| NOTIF-02 | Phase 45 | Complete |
| NOTIF-03 | Phase 45 | Complete |
| NOTIF-04 | Phase 45 | Complete |
| NOTIF-05 | Phase 45 | Complete |
| NOTIF-06 | Phase 45 | Complete |
| XDATA-01 | Phase 46 | Complete |
| XDATA-02 | Phase 46 | Complete |
| XDATA-03 | Phase 46 | Complete |
| XDATA-04 | Phase 46 | Complete |
| XDATA-05 | Phase 46 | Complete |
| XDATA-06 | Phase 46 | Complete |
| CAL-01 | Phase 46 | Complete |
| CAL-02 | Phase 46 | Complete |
| CAL-03 | Phase 46 | Complete |
| CAL-04 | Phase 46 | Complete |
| INTEL-01 | Phase 46 | Complete |
| INTEL-02 | Phase 46 | Complete |
| INTEL-03 | Phase 46 | Complete |
| INTEL-04 | Phase 46 | Complete |
| INTEL-05 | Phase 46 | Complete |
| TEAM-01 | Phase 47 | Complete |
| TEAM-02 | Phase 47 | Complete |
| TEAM-03 | Phase 47 | Complete |
| TEAM-04 | Phase 47 | Complete |
| HOOK-01 | Phase 47 | Complete |
| HOOK-02 | Phase 47 | Complete |
| HOOK-03 | Phase 47 | Complete |
| HOOK-04 | Phase 47 | Complete |
| HOOK-05 | Phase 47 | Complete |

**Coverage:**
- v6.0 requirements: 97 total (17 categories)
- Mapped to phases: 97/97
- Unmapped: 0

---
*Requirements defined: 2026-04-04*
*Last updated: 2026-04-04 after roadmap creation — all requirements mapped to phases 38-47*

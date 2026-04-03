# Requirements: Pikar-AI v6.0

**Defined:** 2026-04-04
**Core Value:** Users describe what they want in natural language and the system autonomously executes real-world business actions — not just generates advice

## v6.0 Requirements

### Persona Unlock (SOLO)
- [ ] **SOLO-01**: Solopreneur persona has full access to workflows, dynamic workflow generator, and workflow templates
- [ ] **SOLO-02**: Solopreneur persona has full access to approvals, sales pipeline, and reports
- [ ] **SOLO-03**: Solopreneur persona has full access to compliance suite and financial forecasting
- [ ] **SOLO-04**: Solopreneur behavioral instructions updated to reflect full-featured single-user (not limited tier)
- [ ] **SOLO-05**: Only team_management, shared_workspaces, and team_analytics remain restricted for solopreneur
- [ ] **SOLO-06**: Frontend feature gating mirrors backend — solopreneur sees all non-team features without upgrade prompts

### Tool Honesty (TOOL)
- [ ] **TOOL-01**: `manage_hubspot` renamed to `hubspot_setup_guide` (or replaced by real CRM tools)
- [ ] **TOOL-02**: `run_security_audit` renamed to `security_checklist`
- [ ] **TOOL-03**: `deploy_container` renamed to `container_deployment_guide`
- [ ] **TOOL-04**: `architect_cloud_solution` renamed to `cloud_architecture_guide`
- [ ] **TOOL-05**: `perform_seo_audit` renamed to `seo_fundamentals_guide`
- [ ] **TOOL-06**: `generate_product_roadmap` renamed to `product_roadmap_guide`
- [ ] **TOOL-07**: `design_rag_pipeline` renamed to `rag_architecture_guide`
- [ ] **TOOL-08**: Org chart / agent capabilities display separates "Tools" (actions) from "Knowledge" (frameworks)

### Integration Infrastructure (INFRA)
- [ ] **INFRA-01**: Integration credential manager stores OAuth tokens encrypted (Fernet) per user per provider
- [ ] **INFRA-02**: OAuth token refresh manager handles concurrent refresh with async locking
- [ ] **INFRA-03**: Integration health check endpoint reports status per connected service
- [ ] **INFRA-04**: Webhook inbound receiver with HMAC-SHA256 verification and idempotency
- [ ] **INFRA-05**: Webhook outbound delivery queue with exponential backoff retry (5 attempts)
- [ ] **INFRA-06**: Webhook dead letter queue with per-endpoint circuit breaker
- [ ] **INFRA-07**: Integration sync state tracking (cursor, last sync, error count per user per provider)
- [ ] **INFRA-08**: Frontend integration configuration page shows connection status for all providers

### CRM Integration (CRM)
- [ ] **CRM-01**: User can connect HubSpot account via OAuth from configuration page
- [ ] **CRM-02**: Bidirectional contact sync between HubSpot and Pikar contacts table
- [ ] **CRM-03**: User can view HubSpot deals and pipeline stages in Pikar dashboard
- [ ] **CRM-04**: Agent can create/update HubSpot contacts and deals via chat commands
- [ ] **CRM-05**: Agent responses are CRM-aware (agent sees deal context before responding to sales queries)
- [ ] **CRM-06**: HubSpot webhook processing for real-time sync on contact/deal changes

### Financial Sync (FIN)
- [ ] **FIN-01**: Stripe transaction history auto-imported into financial_records table
- [ ] **FIN-02**: Revenue dashboard shows real Stripe data (payments, invoices, balance)
- [ ] **FIN-03**: Stripe webhook handler creates financial_records on payment_intent.succeeded
- [ ] **FIN-04**: Transaction categorization (revenue, refund, fee, payout) applied automatically
- [ ] **FIN-05**: User can trigger manual full sync of Stripe history from configuration page

### E-commerce (SHOP)
- [ ] **SHOP-01**: User can connect Shopify store via OAuth from configuration page
- [ ] **SHOP-02**: Agent can list orders, products, and inventory from Shopify
- [ ] **SHOP-03**: Sales analytics (revenue, orders, AOV, top products) available to FinancialAnalysisAgent
- [ ] **SHOP-04**: Inventory alerts when stock falls below configurable threshold
- [ ] **SHOP-05**: Shopify webhook processing for real-time order and inventory updates

### Project Management (PM)
- [ ] **PM-01**: User can connect Linear account via OAuth from configuration page
- [ ] **PM-02**: User can connect Asana account via OAuth from configuration page
- [ ] **PM-03**: Bidirectional task sync — creating task in Pikar creates issue in Linear/Asana
- [ ] **PM-04**: Status mapping between Pikar task states and Linear/Asana states
- [ ] **PM-05**: Agent can list, create, and update Linear/Asana tasks via chat commands

### Email Automation (EMAIL)
- [ ] **EMAIL-01**: User can create multi-step email sequences with templates and variables
- [ ] **EMAIL-02**: Sequence scheduling with timezone-aware send times
- [ ] **EMAIL-03**: Open and click tracking via tracking pixels and link wrapping
- [ ] **EMAIL-04**: Sequence pause/resume on bounce rate threshold (>5%)
- [ ] **EMAIL-05**: Daily send limit per user (configurable, default 50/day for warm-up)
- [ ] **EMAIL-06**: Agent can generate email sequence content based on campaign context

### Ad Platforms (ADS)
- [ ] **ADS-01**: User can connect Google Ads account via OAuth from configuration page
- [ ] **ADS-02**: User can connect Meta Ads account via OAuth from configuration page
- [ ] **ADS-03**: Agent can create, pause, and resume ad campaigns (with mandatory approval gate for budget changes)
- [ ] **ADS-04**: Performance reporting (impressions, clicks, conversions, spend) available to MarketingAutomationAgent
- [ ] **ADS-05**: Budget pacing alerts when daily spend exceeds threshold
- [ ] **ADS-06**: Hard budget cap per user per platform — API rejects operations exceeding cap
- [ ] **ADS-07**: Agent can generate ad copy and creative briefs via ContentCreationAgent

### Document Generation (DOC)
- [ ] **DOC-01**: Agent can generate PDF reports from any analysis output
- [ ] **DOC-02**: PDF reports include user's branding (logo, colors from brand profile)
- [ ] **DOC-03**: Agent can generate pitch deck slides (PowerPoint) from strategic planning output
- [ ] **DOC-04**: Common templates available: financial report, project proposal, meeting summary, competitive analysis
- [ ] **DOC-05**: Generated documents stored in Supabase Storage and linked to the conversation

### Data Import/Export (DATA)
- [ ] **DATA-01**: User can upload CSV files with column mapping UI
- [ ] **DATA-02**: CSV validation with row-level error reporting before commit
- [ ] **DATA-03**: AI-assisted column mapping (suggest mappings from CSV headers)
- [ ] **DATA-04**: User can export any data table (contacts, tasks, initiatives, financial records) to CSV
- [ ] **DATA-05**: Import progress tracking via SSE for large files
- [ ] **DATA-06**: Agent can trigger data imports and exports via chat commands

### Webhook/Zapier (HOOK)
- [ ] **HOOK-01**: User can create outbound webhook endpoints for Pikar events (task.created, workflow.completed, etc.)
- [ ] **HOOK-02**: Event catalog listing all available trigger events with payload schemas
- [ ] **HOOK-03**: Zapier-compatible webhook format (standard JSON payload structure)
- [ ] **HOOK-04**: Webhook delivery log with success/failure status visible in configuration page
- [ ] **HOOK-05**: Agent can create and manage webhook endpoints via chat commands

### Slack/Teams Notifications (NOTIF)
- [ ] **NOTIF-01**: User can connect Slack workspace via OAuth from configuration page
- [ ] **NOTIF-02**: User can connect Microsoft Teams via Azure AD OAuth from configuration page
- [ ] **NOTIF-03**: Configurable notification rules: which events → which channel
- [ ] **NOTIF-04**: Approval buttons in Slack messages (approve/reject inline without leaving Slack)
- [ ] **NOTIF-05**: Daily briefing auto-posted to configured Slack/Teams channel
- [ ] **NOTIF-06**: Rich formatted messages (Slack Block Kit / Teams Adaptive Cards)

### External Data Analytics (XDATA)
- [ ] **XDATA-01**: User can connect external PostgreSQL database from configuration page
- [ ] **XDATA-02**: User can connect BigQuery project from configuration page
- [ ] **XDATA-03**: Agent can run read-only SQL queries against connected external databases
- [ ] **XDATA-04**: AI-generated SQL from natural language via DataAnalysisAgent
- [ ] **XDATA-05**: Query results displayed as tables and charts in chat
- [ ] **XDATA-06**: Connection uses strict read-only mode with 30-second query timeout

### Calendar Automation (CAL)
- [ ] **CAL-01**: Agent can find optimal meeting times by querying free/busy across calendars
- [ ] **CAL-02**: Agent can auto-schedule follow-up meetings after sales calls
- [ ] **CAL-03**: Agent can generate recurring tasks from calendar patterns
- [ ] **CAL-04**: Calendar-aware agent responses (agent knows about upcoming meetings and context)

### Continuous Intelligence (INTEL)
- [ ] **INTEL-01**: User can create scheduled monitoring jobs for competitors, markets, or topics
- [ ] **INTEL-02**: Monitoring runs on configurable schedule (daily, weekly) via workflow trigger service
- [ ] **INTEL-03**: Results synthesized into intelligence briefs by ResearchAgent
- [ ] **INTEL-04**: Knowledge graph updated with entities and findings from monitoring
- [ ] **INTEL-05**: Alert notifications when significant changes detected (new products, pricing, news)

### Team Collaboration (TEAM)
- [ ] **TEAM-01**: Team members can share initiatives and view shared workflow runs
- [ ] **TEAM-02**: Team-level analytics dashboard showing aggregate KPIs
- [ ] **TEAM-03**: Role-based visibility (team admin sees all, member sees assigned work)
- [ ] **TEAM-04**: Activity feed showing team member actions on shared resources

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
| (To be filled by roadmapper) | | |

**Coverage:**
- v6.0 requirements: 80 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 80

---
*Requirements defined: 2026-04-04*
*Last updated: 2026-04-04 after initial definition*

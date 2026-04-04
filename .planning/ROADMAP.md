# Roadmap: pikar-ai

## Milestones

- ✅ **v1.0 Core Reliability** - Phase 1 (shipped 2026-03-04)
- ✅ **v1.1 Production Readiness** - Phases 2-6 (shipped 2026-03-13, archive: [v1.1 roadmap](milestones/v1.1-ROADMAP.md), [v1.1 requirements](milestones/v1.1-REQUIREMENTS.md))
- ✅ **v2.0 Broader App Builder** - Phases 16-22 (shipped 2026-03-23, archive: [v2.0 roadmap](milestones/v2.0-ROADMAP.md), [v2.0 requirements](milestones/v2.0-REQUIREMENTS.md))
- ✅ **v3.0 Admin Panel** - Phases 7-15 + 12.1 (shipped 2026-03-26, archive: [v3.0 roadmap](milestones/v3.0-ROADMAP.md), [v3.0 requirements](milestones/v3.0-REQUIREMENTS.md))
- ✅ **v4.0 Production Scale & Persona UX** - Phases 26-31 (shipped 2026-04-03)
- ✅ **v5.0 Persona Production Readiness** - Phases 32-37 (shipped 2026-04-03)
- 🚧 **v6.0 Real-World Integration & Solopreneur Unlock** - Phases 38-47 (in progress)

## Phases

<details>
<summary>✅ v1.0 Core Reliability (Phase 1) - SHIPPED 2026-03-04</summary>

### Phase 1: Core Reliability
**Goal**: Workflow execution is deterministic and Redis caching is resilient
**Plans**: 2 plans

Plans:
- [x] 01-01: Standardize workflow execution and argument mapping
- [x] 01-02: Implement Redis circuit breakers for cache lookups

</details>

<details>
<summary>✅ v1.1 Production Readiness (Phases 2-6) - SHIPPED 2026-03-13</summary>

See archived roadmap: [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)

</details>

<details>
<summary>✅ v2.0 Broader App Builder (Phases 16-22) - SHIPPED 2026-03-23</summary>

See archived roadmap: [milestones/v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md)

</details>

<details>
<summary>✅ v3.0 Admin Panel (Phases 7-15 + 12.1) - SHIPPED 2026-03-26</summary>

See archived roadmap: [milestones/v3.0-ROADMAP.md](milestones/v3.0-ROADMAP.md)

</details>

<details>
<summary>✅ v4.0 Production Scale & Persona UX (Phases 26-31) - SHIPPED 2026-04-03</summary>

**Phases completed:** 7 phases (26-31 + 27.1), all plans complete
**Delivered:** Async Supabase, production deployment hardening, security headers, persona agent equalization, persona-specific frontend UX, default widgets, empty states.

</details>

<details>
<summary>✅ v5.0 Persona Production Readiness (Phases 32-37) - SHIPPED 2026-04-03</summary>

**Phases completed:** 6 phases (32-37), all plans complete
**Delivered:** Feature gating, backend persona awareness, computed KPIs, teams & RBAC, enterprise governance, SME department coordination.

</details>

---

### 🚧 v6.0 Real-World Integration & Solopreneur Unlock (In Progress)

**Milestone Goal:** Transform Pikar from an AI advice system into a real-world action platform. Add genuine external integrations (CRM, accounting, ads, e-commerce, project management), unlock solopreneur persona to be full-featured single-user (not limited), rename misleading tools for trust, and fill every capability gap identified in the comprehensive value audit.

## Phases

- [x] **Phase 38: Solopreneur Unlock & Tool Honesty** — Full-featured solopreneur persona + rename misleading tools for trust (completed 2026-04-04)
- [x] **Phase 39: Integration Infrastructure** — Credential manager, webhook system, sync state tracking, OAuth token management (completed 2026-04-04)
- [x] **Phase 40: Data I/O & Document Generation** — CSV import/export, PDF reports, pitch decks, branded document output (completed 2026-04-04)
- [ ] **Phase 41: Financial Integrations** — Stripe revenue sync + Shopify e-commerce connector
- [ ] **Phase 42: CRM & Email Automation** — HubSpot bidirectional sync + multi-step email sequences
- [ ] **Phase 43: Ad Platform Integration** — Google Ads + Meta Ads with mandatory approval gates for budget operations
- [ ] **Phase 44: Project Management Integration** — Linear + Asana bidirectional task sync
- [ ] **Phase 45: Communication & Notifications** — Slack + Microsoft Teams with interactive approval buttons
- [ ] **Phase 46: Analytics & Continuous Intelligence** — External database queries, calendar automation, scheduled monitoring
- [ ] **Phase 47: Team Collaboration & Webhook Polish** — Shared workspaces, team analytics, Zapier-compatible webhook endpoints

## Phase Details

### Phase 38: Solopreneur Unlock & Tool Honesty
**Goal**: Solopreneur users have unrestricted access to every non-team feature, and every agent tool name honestly reflects what it actually does
**Depends on**: Nothing (no external deps, immediate trust and capability improvement)
**Requirements**: SOLO-01, SOLO-02, SOLO-03, SOLO-04, SOLO-05, SOLO-06, TOOL-01, TOOL-02, TOOL-03, TOOL-04, TOOL-05, TOOL-06, TOOL-07, TOOL-08
**Success Criteria** (what must be TRUE):
  1. A solopreneur user can access workflows, dynamic workflow generator, approvals, sales pipeline, reports, compliance suite, and financial forecasting from the frontend without upgrade prompts or feature restrictions
  2. A solopreneur user sees only team_management, shared_workspaces, and team_analytics as restricted features — everything else is fully available
  3. Tools that previously claimed to "manage" or "run" or "deploy" external systems (HubSpot, security audits, containers, cloud, SEO, roadmaps, RAG) now have honest names that indicate they provide guidance, not execution
  4. The org chart / agent capabilities display clearly separates "Tools" (real actions the system performs) from "Knowledge" (frameworks and guides the system can explain)
**Plans**: 3 plans

Plans:
- [ ] 38-01-PLAN.md — Unlock solopreneur feature gating + update billing comparison table
- [ ] 38-02-PLAN.md — Rename 7 misleading agent tools across full import chain
- [ ] 38-03-PLAN.md — Update behavioral instructions, KPIs, onboarding + org chart tool badges

### Phase 39: Integration Infrastructure
**Goal**: A secure, reusable foundation exists for all external integrations — encrypted credential storage, OAuth token lifecycle, webhook delivery with reliability guarantees, and sync state tracking per user per provider
**Depends on**: Phase 38 (solopreneur must be unlocked before integrations matter to single-user persona)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06, INFRA-07, INFRA-08
**Success Criteria** (what must be TRUE):
  1. A user can store OAuth credentials for any supported provider and the tokens are encrypted with Fernet before persisting — plaintext tokens never appear in database columns or API responses
  2. When an OAuth token expires during an API call, the system refreshes it automatically with async locking to prevent concurrent refresh races — the user's operation completes without manual re-authentication
  3. A user can open the integration configuration page and see connection status (connected/disconnected/error) for every supported provider
  4. Inbound webhooks are verified with HMAC-SHA256 and processed idempotently — duplicate deliveries do not create duplicate records
  5. Outbound webhook delivery retries up to 5 times with exponential backoff, and a dead letter queue captures failures with per-endpoint circuit breaker protection
**Plans**: 3 plans

Plans:
- [ ] 39-01-PLAN.md — Database migration, provider registry, IntegrationManager service, OAuth endpoints
- [ ] 39-02-PLAN.md — Webhook infrastructure (inbound verification, outbound delivery, circuit breaker)
- [ ] 39-03-PLAN.md — Frontend integration configuration page with category cards + OAuth popup

### Phase 40: Data I/O & Document Generation
**Goal**: Users can move data in and out of Pikar (CSV import/export) and agents can produce polished, branded documents (PDF reports, PowerPoint decks) from any analysis output
**Depends on**: Phase 39 (document storage uses integration infrastructure patterns; no external API deps required)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DOC-01, DOC-02, DOC-03, DOC-04, DOC-05
**Success Criteria** (what must be TRUE):
  1. A user can upload a CSV file and see a column mapping UI with AI-suggested mappings — validation reports row-level errors before committing, and large imports show SSE progress
  2. A user can export any data table (contacts, tasks, initiatives, financial records) to CSV from the dashboard or via a chat command to the agent
  3. An agent can generate a branded PDF report from any analysis output — the PDF includes the user's logo and brand colors from their profile
  4. An agent can generate a PowerPoint pitch deck from strategic planning output, using common templates (financial report, project proposal, meeting summary, competitive analysis)
  5. Generated documents are stored in Supabase Storage and linked to the conversation where they were created — users can download them from chat history
**Plans**: 3 plans

Plans:
- [ ] 40-01-PLAN.md — CSV import/export backend services, migration, REST endpoints
- [ ] 40-02-PLAN.md — Document generation (PDF + PPTX) services, templates, dependencies
- [ ] 40-03-PLAN.md — Agent tools for data I/O and documents + frontend DocumentWidget

### Phase 41: Financial Integrations
**Goal**: Users have real financial data flowing into Pikar — Stripe transactions auto-imported into financial records, Shopify orders and inventory synced in real-time, and the financial agent works with actual numbers
**Depends on**: Phase 39 (OAuth credential storage and webhook infrastructure required for both Stripe and Shopify)
**Requirements**: FIN-01, FIN-02, FIN-03, FIN-04, FIN-05, SHOP-01, SHOP-02, SHOP-03, SHOP-04, SHOP-05
**Success Criteria** (what must be TRUE):
  1. After connecting Stripe, transaction history is auto-imported into financial_records with automatic categorization (revenue, refund, fee, payout) — the revenue dashboard shows real Stripe data
  2. A Stripe webhook on payment_intent.succeeded creates a financial record automatically — no manual sync needed for new transactions
  3. A user can connect their Shopify store via OAuth and the agent can list orders, products, and inventory from Shopify
  4. Shopify sales analytics (revenue, orders, AOV, top products) are available to the FinancialAnalysisAgent for real analysis, not simulated data
  5. Inventory alerts fire when stock falls below a configurable threshold, and real-time order/inventory updates arrive via Shopify webhooks
**Plans**: TBD

### Phase 42: CRM & Email Automation
**Goal**: Users have a connected sales workflow — HubSpot contacts and deals sync bidirectionally, agents are CRM-aware when answering sales queries, and automated email sequences can be created and managed with deliverability safeguards
**Depends on**: Phase 39 (OAuth credential storage and webhook infrastructure for HubSpot); Phase 41 (financial context enriches CRM sales view)
**Requirements**: CRM-01, CRM-02, CRM-03, CRM-04, CRM-05, CRM-06, EMAIL-01, EMAIL-02, EMAIL-03, EMAIL-04, EMAIL-05, EMAIL-06
**Success Criteria** (what must be TRUE):
  1. A user can connect their HubSpot account via OAuth and see bidirectional contact sync — changes in HubSpot appear in Pikar and vice versa, with real-time webhook updates
  2. The agent sees HubSpot deal context before responding to sales queries — asking "how is the Acme deal going?" returns real pipeline data, not a generic answer
  3. An agent can create and update HubSpot contacts and deals via chat commands — the changes appear in HubSpot within seconds
  4. A user can create multi-step email sequences with templates, variables, and timezone-aware scheduling — with open/click tracking, automatic pause on high bounce rates, and configurable daily send limits
  5. An agent can generate email sequence content based on campaign context and CRM contact data
**Plans**: TBD

### Phase 43: Ad Platform Integration
**Goal**: Users can manage Google Ads and Meta Ads campaigns through Pikar with mandatory human approval for all budget operations — the agent can create campaigns, report performance, and generate creative, but real money never moves without explicit confirmation
**Depends on**: Phase 39 (OAuth credentials); Phase 42 (CRM audience data informs ad targeting)
**Requirements**: ADS-01, ADS-02, ADS-03, ADS-04, ADS-05, ADS-06, ADS-07
**Success Criteria** (what must be TRUE):
  1. A user can connect Google Ads and Meta Ads accounts via OAuth from the configuration page
  2. An agent can create, pause, and resume ad campaigns — but any operation that changes budget requires a mandatory approval gate (confirmation card with budget details) before executing
  3. Performance reporting (impressions, clicks, conversions, spend) is available to the MarketingAutomationAgent for campaign analysis and optimization recommendations
  4. Budget pacing alerts fire when daily spend exceeds a configured threshold, and a hard budget cap per user per platform prevents the API from executing operations that would exceed the cap
  5. An agent can generate ad copy and creative briefs via the ContentCreationAgent to support campaign creation
**Plans**: TBD

### Phase 44: Project Management Integration
**Goal**: Users can connect Linear and Asana to Pikar for bidirectional task synchronization — creating a task in Pikar creates an issue in their PM tool, and status changes flow both directions
**Depends on**: Phase 39 (OAuth credentials and sync state tracking)
**Requirements**: PM-01, PM-02, PM-03, PM-04, PM-05
**Success Criteria** (what must be TRUE):
  1. A user can connect Linear and/or Asana accounts via OAuth from the configuration page
  2. Creating a task in Pikar creates a corresponding issue in the connected PM tool — and vice versa, new issues created in Linear/Asana appear as Pikar tasks
  3. Task status changes map correctly between Pikar states and Linear/Asana states — completing a task in one system updates the status in the other
  4. An agent can list, create, and update Linear/Asana tasks via chat commands — "create a bug ticket in Linear for the login issue" results in a real Linear issue
**Plans**: TBD

### Phase 45: Communication & Notifications
**Goal**: Users receive Pikar notifications in their team chat (Slack or Teams) with rich formatting and interactive approval buttons — including automated daily briefings posted to configured channels
**Depends on**: Phase 39 (OAuth credentials); Phase 42 (CRM events trigger notifications)
**Requirements**: NOTIF-01, NOTIF-02, NOTIF-03, NOTIF-04, NOTIF-05, NOTIF-06
**Success Criteria** (what must be TRUE):
  1. A user can connect their Slack workspace or Microsoft Teams via OAuth from the configuration page
  2. Configurable notification rules let users specify which Pikar events (task.created, workflow.completed, approval.pending) route to which Slack/Teams channel
  3. Approval requests sent to Slack include interactive approve/reject buttons — the user can act on the approval without leaving Slack
  4. A daily briefing is automatically posted to the configured channel, summarizing key metrics, pending actions, and upcoming deadlines
  5. Messages use rich formatting (Slack Block Kit / Teams Adaptive Cards) with structured sections, not plain text dumps
**Plans**: TBD

### Phase 46: Analytics & Continuous Intelligence
**Goal**: Users can query their own external databases with natural language, agents are calendar-aware for scheduling and follow-ups, and scheduled monitoring jobs continuously track competitors and market changes
**Depends on**: Phase 39 (credential storage for DB connections); Phase 45 (alerts delivered via connected channels)
**Requirements**: XDATA-01, XDATA-02, XDATA-03, XDATA-04, XDATA-05, XDATA-06, CAL-01, CAL-02, CAL-03, CAL-04, INTEL-01, INTEL-02, INTEL-03, INTEL-04, INTEL-05
**Success Criteria** (what must be TRUE):
  1. A user can connect an external PostgreSQL or BigQuery database and the agent can run read-only SQL queries against it with a 30-second timeout — AI generates SQL from natural language and results display as tables and charts in chat
  2. The agent can find optimal meeting times by checking free/busy status, auto-schedule follow-up meetings after sales calls, and generate recurring tasks from calendar patterns
  3. Agents are calendar-aware — when a user asks about their day or prepares for a meeting, the agent knows what meetings are upcoming and provides relevant context
  4. A user can create scheduled monitoring jobs (daily/weekly) for competitors, markets, or topics — results are synthesized into intelligence briefs by the ResearchAgent with knowledge graph updates
  5. Alert notifications fire when significant changes are detected in monitored topics (new competitor products, pricing changes, industry news)
**Plans**: TBD

### Phase 47: Team Collaboration & Webhook Polish
**Goal**: Team members can collaborate on shared work with role-based visibility, and outbound webhooks enable Pikar to integrate with any automation platform including Zapier
**Depends on**: Phase 39 (webhook infrastructure); Phase 46 (intelligence outputs feed team dashboards)
**Requirements**: TEAM-01, TEAM-02, TEAM-03, TEAM-04, HOOK-01, HOOK-02, HOOK-03, HOOK-04, HOOK-05
**Success Criteria** (what must be TRUE):
  1. Team members can share initiatives and view shared workflow runs — team-level analytics show aggregate KPIs across all members
  2. Role-based visibility enforces that team admins see all work while regular members see only assigned work — the activity feed shows team member actions on shared resources
  3. A user can create outbound webhook endpoints for Pikar events (task.created, workflow.completed, etc.) with a browsable event catalog showing all available triggers and payload schemas
  4. Webhook payloads follow Zapier-compatible JSON format — webhook delivery logs with success/failure status are visible in the configuration page
  5. An agent can create and manage webhook endpoints via chat commands
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 38 → 39 → 40 → 41 → 42 → 43 → 44 → 45 → 46 → 47

| Phase | Plans Complete | Status | Completed |
|-------|---------------|--------|-----------|
| 38. Solopreneur Unlock & Tool Honesty | 3/3 | Complete    | 2026-04-04 |
| 39. Integration Infrastructure | 3/3 | Complete    | 2026-04-04 |
| 40. Data I/O & Document Generation | 3/3 | Complete    | 2026-04-04 |
| 41. Financial Integrations | 0/TBD | Not started | - |
| 42. CRM & Email Automation | 0/TBD | Not started | - |
| 43. Ad Platform Integration | 0/TBD | Not started | - |
| 44. Project Management Integration | 0/TBD | Not started | - |
| 45. Communication & Notifications | 0/TBD | Not started | - |
| 46. Analytics & Continuous Intelligence | 0/TBD | Not started | - |
| 47. Team Collaboration & Webhook Polish | 0/TBD | Not started | - |

# Requirements: pikar-ai v8.0 Agent Ecosystem Enhancement

**Defined:** 2026-04-09
**Core Value:** Users describe what they want in natural language and the system autonomously generates, manages, and grows their business operations — proactively, not just reactively

## v8.0 Requirements

Requirements for the agent ecosystem enhancement milestone. Each maps to roadmap phases.

### Proactive Intelligence

- [ ] **PROACT-01**: User receives a daily briefing notification summarizing pending approvals, KPI movements, stalled initiatives, and upcoming deadlines — without asking
- [ ] **PROACT-02**: User receives a push alert when the Data Agent detects an anomaly (>2 stddev from baseline) in their business metrics
- [ ] **PROACT-03**: User receives an alert when the Strategic Agent's continuous monitoring finds a competitor move (pricing change, product launch, funding round)
- [ ] **PROACT-04**: User receives an alert when an OAuth integration token is expiring within 3 days or a connected service is unhealthy
- [ ] **PROACT-05**: User receives a budget pacing alert in plain English when ad spend is trending to exceed the monthly cap

### Non-Technical UX

- [ ] **NTUX-01**: User sees 4-6 context-aware clickable suggestion chips based on persona, time of day, and recent activity — eliminating the blank chat box problem
- [ ] **NTUX-02**: When the Executive Agent cannot confidently route a request, it presents 2-3 clickable intent options instead of guessing
- [ ] **NTUX-03**: Every agent response includes a collapsible TL;DR (one sentence + key number + recommended action) for mobile-friendly consumption
- [ ] **NTUX-04**: User can discover and launch relevant workflows by describing what they want in natural language (e.g., "I want to launch a product" maps to Product Launch workflow)
- [ ] **NTUX-05**: User can select from a template gallery of pre-built content types (Product Launch, Newsletter, Testimonial, etc.) instead of writing creative briefs from scratch

### Cross-Agent Intelligence

- [ ] **CROSS-01**: User can ask a holistic question ("How's my business doing?") and receive a synthesized response pulling data from Financial, Sales, Marketing, and Data agents
- [ ] **CROSS-02**: User can view a chronological unified action history showing all AI actions across agents (campaigns created, leads scored, reports generated, etc.)
- [ ] **CROSS-03**: Strategic Agent auto-logs key decisions with rationale, date, and outcomes — user can query "What did we decide about X?" at any time
- [ ] **CROSS-04**: Executive Agent tracks onboarding checklist completion and nudges users who stall at any step during their first 7 days

### Financial Agent Enhancement

- [ ] **FIN-01**: User sees a plain-English Financial Health Score (0-100) with color coding and a one-sentence explanation of what's driving it
- [ ] **FIN-02**: Stripe charges and payouts are auto-categorized into business expense categories (marketing, SaaS tools, COGS, payroll, etc.)
- [ ] **FIN-03**: When an invoice is overdue, the Financial Agent auto-generates a polite follow-up email draft and surfaces it in the morning briefing
- [ ] **FIN-04**: User can ask "What if I hire 2 people?" and receive a 6-month financial projection modeled against current revenue and burn rate
- [ ] **FIN-05**: User receives quarterly estimated tax reminders with calculated amounts based on YTD revenue data
- [ ] **FIN-06**: The `generate_forecast` degraded tool is replaced with a real implementation using historical Stripe/Shopify revenue data

### Content Agent Enhancement

- [ ] **CONTENT-01**: User can get a ready-to-post social media post, blog intro, or email in a single conversational turn — the agent auto-detects simple requests and skips the 10-stage pipeline
- [ ] **CONTENT-02**: After content is created, the agent suggests optimal posting time and offers to auto-schedule via the content calendar
- [ ] **CONTENT-03**: After 5+ content pieces, the system auto-extracts the user's brand voice patterns (tone, vocabulary, sentence length) and applies them to future content without manual setup
- [ ] **CONTENT-04**: After content is published and engagement data is available, the agent surfaces a performance summary with specific improvement suggestions for next time

### Sales Agent Enhancement

- [ ] **SALES-01**: After a sales call or meeting, the Sales Agent auto-generates a personalized follow-up email with meeting recap, next steps, and CTA
- [ ] **SALES-02**: User sees an actionable pipeline dashboard that recommends specific actions for stalled deals (re-engagement emails, discount offers, escalation suggestions)
- [ ] **SALES-03**: User can generate a professional proposal/quote document from deal context (product, pricing, timeline, terms) in one request
- [ ] **SALES-04**: Each lead is tracked with source attribution (social, email, referral, ad campaign) connecting sales data back to marketing efforts
- [ ] **SALES-05**: After every sales conversation in Pikar-AI, deal notes, next steps, and stage changes are auto-synced to HubSpot CRM
- [ ] **SALES-06**: The `create_contact`, `score_lead`, and `query_crm` degraded tools are replaced with real HubSpot API implementations

### Marketing Agent Enhancement

- [ ] **MKT-01**: User sees campaign performance explained in plain English ("Your Google Ads spent $340 this week and brought 12 customers at $28.33 each — 15% better than last week")
- [ ] **MKT-02**: User can create a campaign through a conversational wizard ("What are you promoting? Who's your customer? What's your budget?") that auto-configures platform, targeting, and creatives
- [ ] **MKT-03**: User can view unified cross-channel attribution showing which channel (Google Ads, Meta, Shopify, email) drives the most revenue
- [ ] **MKT-04**: Marketing Agent recommends budget reallocation based on cross-channel ROAS ("Meta gives 2x better return — shift $50/day from Google?")
- [ ] **MKT-05**: Email sequences support A/B variant testing with automatic winner selection based on open rates and click-through rates
- [ ] **MKT-06**: The `configure_ads` and `optimize_spend` degraded tools are replaced with real Google/Meta Ads API implementations

### Operations Agent Enhancement

- [ ] **OPS-01**: Operations Agent analyzes workflow execution data to surface recurring bottlenecks with specific recommendations ("Content Approval averages 3.2 days — set up approver reminders?")
- [ ] **OPS-02**: User can describe a process conversationally and the agent auto-generates a formal SOP document, then offers to create a workflow template from it
- [ ] **OPS-03**: User can track all SaaS subscriptions and integration costs with alerts when trial periods end and suggestions for consolidation
- [ ] **OPS-04**: E-commerce users (Shopify connected) receive inventory reorder alerts when products fall below configurable stock thresholds
- [ ] **OPS-05**: User sees an integration health dashboard showing all connected services with status (connected/disconnected/token expiring) in one view
- [ ] **OPS-06**: The `update_inventory`, `create_vendor`, and `create_po` degraded tools are replaced with real implementations

### HR Agent Enhancement

- [ ] **HR-01**: User says "I need to hire a marketing manager" and receives a complete job description with responsibilities, requirements, and salary range from compensation benchmarking
- [ ] **HR-02**: User sees a visual hiring funnel (applicants → phone screens → interviews → offers → hires) for each open position
- [ ] **HR-03**: Interview questions are auto-generated based on the specific job description and required competencies, not just generic STAR templates
- [ ] **HR-04**: When a candidate status changes to "hired", the agent auto-generates an onboarding checklist (equipment, accounts, training, 30-60-90 day plan)
- [ ] **HR-05**: User can view a team org chart showing reporting relationships and open positions, auto-maintained from hiring data
- [ ] **HR-06**: The `assign_training` and `post_job_board` degraded tools are replaced with real implementations

### Compliance Agent Enhancement

- [ ] **LEGAL-01**: User sees a plain-English Compliance Health Score (0-100) with explanation ("85/100 — 2 unmitigated high-severity risks, privacy policy not reviewed in 6 months")
- [ ] **LEGAL-02**: User can generate basic legal documents (privacy policy, terms of service, refund policy) from business context and jurisdiction
- [ ] **LEGAL-03**: User sees a compliance calendar with all upcoming deadlines (SOX quarterly, GDPR annual, license renewals) with advance reminders
- [ ] **LEGAL-04**: User can paste a contract clause and receive a plain-English explanation of what it means and its implications
- [ ] **LEGAL-05**: Compliance Agent monitors for regulatory changes in the user's industry/jurisdiction via web research and alerts when new regulations affect them

### Customer Support Enhancement

- [ ] **SUPP-01**: The Customer Support Agent is renamed and repositioned from "CTO/IT Support" to "Customer Success Manager" with updated instructions reflecting customer-facing support
- [ ] **SUPP-02**: User can auto-generate professional customer-facing responses for common scenarios (refund requests, shipping delays, complaints) maintaining consistent tone
- [ ] **SUPP-03**: After resolving 3+ similar tickets, the agent suggests creating a FAQ entry and auto-generates the content from resolution patterns
- [ ] **SUPP-04**: User sees a customer health dashboard showing open tickets, average resolution time, sentiment trend, and churn risk summary
- [ ] **SUPP-05**: Support tickets are auto-created from inbound channels (email mentions, chat messages) with unified inbox concept

### Data Agent Enhancement

- [ ] **DATA-01**: User can ask natural language questions ("How many customers did I get last month?") and receive plain-English answers with simple charts — the agent auto-routes to the right data source
- [ ] **DATA-02**: Every Monday, the Data Agent auto-generates a 1-page weekly business report (revenue trend, top metrics, anomalies) and surfaces it in the briefing
- [ ] **DATA-03**: When a new integration is connected (Stripe, Shopify, Google Ads), the Data Agent auto-catalogs available data and suggests useful reports
- [ ] **DATA-04**: For SaaS businesses with Stripe data, the agent auto-computes cohort retention, LTV, and churn by signup month
- [ ] **DATA-05**: The `query_analytics` and `query_usage` degraded tools are replaced with real implementations using PostHog/internal analytics

### Admin & Research Enhancement

- [ ] **ADMIN-01**: When a user reports a problem, the Admin Agent auto-diagnoses by checking OAuth token status, API health, budget caps, and approval status — returning a clear explanation, not raw health data
- [ ] **ADMIN-02**: Admin can see which features each user/team is actually using with adoption metrics per agent, identifying underutilized capabilities
- [ ] **ADMIN-03**: Admin receives proactive billing alerts with cost projections ("At current usage, monthly cost will be $X — 20% higher than last month, mainly from video generation")
- [ ] **RESEARCH-01**: Research Agent adjusts synthesis complexity based on persona — solopreneur gets bullet points with actions, enterprise gets executive briefings with citations
- [ ] **RESEARCH-02**: User can subscribe to continuous monitoring topics ("Monitor [competitor] and alert me when something important happens") via a simple conversational interface

### Remaining Degraded Tool Cleanup

- [ ] **DEGRADE-01**: The `analyze_sentiment` degraded tool is replaced with Gemini-powered NLP sentiment analysis
- [ ] **DEGRADE-02**: The `ocr_document` degraded tool is replaced with Google Document AI or equivalent OCR integration
- [ ] **DEGRADE-03**: The remaining low-priority degraded tools (`book_travel`, `create_checklist`, `run_test`, `test_scenario`, `setup_monitoring`, `create_alert`) are either replaced with real implementations or explicitly removed with clear error messages

## v9.0 Requirements (Deferred)

### Builder Dashboard
- **BLDR-01**: Builder dashboard with project status and resume capability
- **BLDR-02**: One-click deploy to public URL

### Advanced Capabilities
- **ADV-01**: Real-time WebSocket push for proactive alerts (v8.0 uses polling/SSE)
- **ADV-02**: Multi-language content generation
- **ADV-03**: Voice-first agent interaction (beyond current brain dump)
- **ADV-04**: Custom agent creation by users (define new domain agents)
- **ADV-05**: Marketplace for community-created skills and workflows

### Advanced Enterprise
- **ENT-01**: SSO/SAML authentication for enterprise customers
- **ENT-02**: Data residency controls (region-specific storage)
- **ENT-03**: SOC 2 compliance certification preparation

## Out of Scope

| Feature | Reason |
|---------|--------|
| Building new external integrations beyond existing 10 | Focus is on maximizing value from current integrations, not adding new ones |
| Native mobile app | Web-first with mobile-friendly summaries covers mobile use |
| Real-time collaborative editing | Beyond current architecture; would require WebSocket infrastructure |
| Custom agent training/fine-tuning | Gemini models are used as-is; customization through instructions and skills |
| Multi-language UI | Content generation in multiple languages deferred to v9.0 |
| SSO/SAML authentication | Enterprise-only, not needed for solopreneur beta |
| Payment enforcement on feature gates | Soft gating only — upgrade prompts, no hard blocks |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROACT-01 | Phase 57 | Pending |
| PROACT-02 | Phase 57 | Pending |
| PROACT-03 | Phase 57 | Pending |
| PROACT-04 | Phase 57 | Pending |
| PROACT-05 | Phase 57 | Pending |
| NTUX-01 | Phase 58 | Pending |
| NTUX-02 | Phase 58 | Pending |
| NTUX-03 | Phase 58 | Pending |
| NTUX-04 | Phase 58 | Pending |
| NTUX-05 | Phase 58 | Pending |
| CROSS-01 | Phase 59 | Pending |
| CROSS-02 | Phase 59 | Pending |
| CROSS-03 | Phase 59 | Pending |
| CROSS-04 | Phase 59 | Pending |
| FIN-01 | Phase 60 | Pending |
| FIN-02 | Phase 60 | Pending |
| FIN-03 | Phase 60 | Pending |
| FIN-04 | Phase 60 | Pending |
| FIN-05 | Phase 60 | Pending |
| FIN-06 | Phase 60 | Pending |
| CONTENT-01 | Phase 61 | Pending |
| CONTENT-02 | Phase 61 | Pending |
| CONTENT-03 | Phase 61 | Pending |
| CONTENT-04 | Phase 61 | Pending |
| SALES-01 | Phase 62 | Pending |
| SALES-02 | Phase 62 | Pending |
| SALES-03 | Phase 62 | Pending |
| SALES-04 | Phase 62 | Pending |
| SALES-05 | Phase 62 | Pending |
| SALES-06 | Phase 62 | Pending |
| MKT-01 | Phase 63 | Pending |
| MKT-02 | Phase 63 | Pending |
| MKT-03 | Phase 63 | Pending |
| MKT-04 | Phase 63 | Pending |
| MKT-05 | Phase 63 | Pending |
| MKT-06 | Phase 63 | Pending |
| OPS-01 | Phase 64 | Pending |
| OPS-02 | Phase 64 | Pending |
| OPS-03 | Phase 64 | Pending |
| OPS-04 | Phase 64 | Pending |
| OPS-05 | Phase 64 | Pending |
| OPS-06 | Phase 64 | Pending |
| HR-01 | Phase 65 | Pending |
| HR-02 | Phase 65 | Pending |
| HR-03 | Phase 65 | Pending |
| HR-04 | Phase 65 | Pending |
| HR-05 | Phase 65 | Pending |
| HR-06 | Phase 65 | Pending |
| LEGAL-01 | Phase 66 | Pending |
| LEGAL-02 | Phase 66 | Pending |
| LEGAL-03 | Phase 66 | Pending |
| LEGAL-04 | Phase 66 | Pending |
| LEGAL-05 | Phase 66 | Pending |
| SUPP-01 | Phase 67 | Pending |
| SUPP-02 | Phase 67 | Pending |
| SUPP-03 | Phase 67 | Pending |
| SUPP-04 | Phase 67 | Pending |
| SUPP-05 | Phase 67 | Pending |
| DATA-01 | Phase 68 | Pending |
| DATA-02 | Phase 68 | Pending |
| DATA-03 | Phase 68 | Pending |
| DATA-04 | Phase 68 | Pending |
| DATA-05 | Phase 68 | Pending |
| ADMIN-01 | Phase 69 | Pending |
| ADMIN-02 | Phase 69 | Pending |
| ADMIN-03 | Phase 69 | Pending |
| RESEARCH-01 | Phase 69 | Pending |
| RESEARCH-02 | Phase 69 | Pending |
| DEGRADE-01 | Phase 70 | Pending |
| DEGRADE-02 | Phase 70 | Pending |
| DEGRADE-03 | Phase 70 | Pending |

**Coverage:**
- v8.0 requirements: 71 total
- Mapped to phases: 71
- Unmapped: 0

---
*Requirements defined: 2026-04-09*
*Last updated: 2026-04-09 after roadmap creation*

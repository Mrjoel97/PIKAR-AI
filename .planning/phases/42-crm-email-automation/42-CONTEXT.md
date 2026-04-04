# Phase 42: CRM & Email Automation - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Connect HubSpot CRM with bidirectional contact/deal sync (Pikar↔HubSpot), make agents CRM-aware so they answer sales queries with real pipeline data, and build an email sequence engine with multi-step drip campaigns, open/click tracking, bounce protection, and deliverability safeguards.

</domain>

<decisions>
## Implementation Decisions

### HubSpot CRM Integration
- **Connection:** Via Phase 39 OAuth infrastructure — HubSpot already in PROVIDER_REGISTRY
- **SDK:** `hubspot-api-client` (sync SDK, wrap with `asyncio.to_thread()`)
- **Data to sync:**
  - **Contacts** → bidirectional sync with Pikar `contacts` table
    - HubSpot→Pikar: email, firstname, lastname, phone, company, lifecycle_stage, deal associations
    - Pikar→HubSpot: Same fields + any Pikar-specific notes/tags
    - Mapping: HubSpot `lifecyclestage` → Pikar `lifecycle_stage` enum
  - **Deals** → new `hubspot_deals` table (id, user_id, hubspot_deal_id, deal_name, pipeline, stage, amount, close_date, associated_contacts, properties JSONB)
    - Read from HubSpot, write from Pikar
    - Pipeline and stage names synced from HubSpot pipelines API
  - **Activities** → read-only from HubSpot (emails, calls, meetings associated with contacts/deals)
- **Sync strategy:**
  - Initial sync: Import all contacts + deals on first connect
  - Incremental: HubSpot webhooks for real-time updates (contact.creation, contact.propertyChange, deal.creation, deal.propertyChange)
  - Pikar→HubSpot: Immediate push on Pikar contact/deal create/update via HubSpot API
- **Conflict resolution:** Last-write-wins with timestamp comparison using HubSpot's `hs_lastmodifieddate`. If both modified since last sync, flag for user resolution (don't auto-overwrite).
- **Idempotency:** Store `hubspot_contact_id` on Pikar contacts, `hubspot_deal_id` on hubspot_deals. UNIQUE constraint prevents duplicates.
- **CRM-aware agent responses (CRM-05):**
  - When SalesIntelligenceAgent receives a query mentioning a contact/company name, it first queries HubSpot deals for that contact
  - Agent instruction update: "Before answering sales questions, check if the contact has HubSpot deal data. If connected, include deal stage, amount, and recent activity in your response."
  - This is a behavioral instruction change + a `get_hubspot_deal_context(contact_name)` tool
- **New service:** `app/services/hubspot_service.py` extending BaseService
- **New table:** `hubspot_deals` in Supabase migration with RLS
- **HubSpot webhook subscription:** Register webhooks via HubSpot API on connect (contact.creation, contact.propertyChange, deal.creation, deal.propertyChange)

### Email Sequence Engine
- **Architecture:** New `email_sequences` + `email_sequence_steps` + `email_sequence_enrollments` tables
  - `email_sequences`: id, user_id, name, status (draft/active/paused/completed), campaign_id (optional FK)
  - `email_sequence_steps`: id, sequence_id, step_number, subject_template, body_template, delay_hours, delay_type (after_previous/at_time)
  - `email_sequence_enrollments`: id, sequence_id, contact_id, current_step, status (active/completed/bounced/unsubscribed), enrolled_at, next_send_at, timezone
- **Template system:** Jinja2 templates with variables: `{{first_name}}`, `{{company}}`, `{{deal_name}}`, `{{custom.field}}`. Variables resolved from contacts + hubspot_deals data.
- **Scheduling:** Timezone-aware via enrollment's `timezone` field. Next send time computed per-enrollment. Delivery worker checks `next_send_at <= now()` on a 60-second tick cycle (integrated into existing workflow worker).
- **Send limits:** Auto-increasing warm-up schedule:
  - Week 1: 50 emails/day
  - Week 2: 100 emails/day
  - Week 3: 250 emails/day
  - Week 4+: 500 emails/day
  - Stored as `email_daily_limit` in user profile or integration_sync_state
  - User can lower but not exceed current warm-up tier
  - Counter tracks daily sends via Redis key `pikar:email:daily:{user_id}:{date}` with 24h TTL
- **Tracking:**
  - Open tracking: 1x1 transparent pixel in email body, served by `GET /tracking/open/{tracking_id}`
  - Click tracking: Link wrapping via `GET /tracking/click/{tracking_id}?url={encoded_url}` → redirect
  - Tracking events stored in `email_tracking_events` table (event_type, enrollment_id, step_number, timestamp, metadata)
- **Bounce protection:**
  - Resend webhook on `email.bounced` → increment bounce count on enrollment
  - If bounce rate >5% (bounces/total sends in last 24h) → auto-pause ALL active sequences for user
  - Notification: "Your email sequences have been paused due to high bounce rate ({rate}%). Review your contact list before resuming."
- **Unsubscribe:** One-click unsubscribe header (List-Unsubscribe) per CAN-SPAM. Unsubscribe link in footer. Unsubscribed contacts never receive sequence emails again.
- **Sending:** Via existing Resend integration (`app/mcp/integrations/email_service.py`). Each email includes tracking pixel + wrapped links.
- **New service:** `app/services/email_sequence_service.py` extending BaseService
- **New router:** `app/routers/email_sequences.py` for CRUD + enrollment + tracking endpoints

### Agent Tools
- **HubSpot tools for SalesIntelligenceAgent:**
  - `search_hubspot_contacts(query)` — search HubSpot contacts by name/email/company
  - `get_hubspot_deal_context(contact_name_or_id)` — returns deal stage, amount, activity for CRM-aware responses
  - `create_hubspot_contact(email, name, properties?)` — creates in HubSpot + syncs to Pikar
  - `update_hubspot_deal(deal_id, properties)` — updates deal in HubSpot
  - `list_hubspot_deals(pipeline?, stage?)` — lists deals with filters
- **Email tools for MarketingAutomationAgent:**
  - `create_email_sequence(name, steps[])` — creates sequence with template steps
  - `enroll_contacts_in_sequence(sequence_id, contact_ids[], timezone?)` — enrolls contacts
  - `get_sequence_performance(sequence_id)` — open rate, click rate, bounce rate, completion rate
  - `generate_sequence_content(campaign_context, contact_segment)` — AI generates email copy using CRM data
  - `pause_sequence(sequence_id)` / `resume_sequence(sequence_id)`
- **Registration:** HubSpot tools on SalesIntelligenceAgent. Email tools on MarketingAutomationAgent (EmailMarketingAgent sub-agent).

### Claude's Discretion
- Exact HubSpot property-to-Pikar-column mapping details
- HubSpot webhook subscription API call details
- Email template HTML structure and default styling
- Tracking pixel implementation (transparent PNG vs SVG)
- Exact Redis key structure for send limit tracking
- Conflict resolution UI (if needed — could be agent-mediated)
- Whether to add HubSpot contact data to the DataExportService's exportable tables
- Email sequence step delay computation algorithm

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/integration_manager.py`: Phase 39 credential storage + token refresh (for HubSpot OAuth)
- `app/config/integration_providers.py`: HubSpot already registered in PROVIDER_REGISTRY
- `app/routers/webhooks.py`: Phase 39 inbound webhook infrastructure (for HubSpot webhooks)
- `app/mcp/integrations/email_service.py`: Existing Resend email sending
- `app/services/campaign_orchestrator_service.py`: Campaign FSM pattern (for sequence state management)
- `app/services/stripe_sync_service.py`: Phase 41 external API sync pattern (asyncio.to_thread for sync SDKs)
- `app/services/shopify_service.py`: Phase 41 GraphQL + webhook pattern
- `app/services/workflow_trigger_service.py`: Scheduler tick pattern (for email delivery worker)
- `app/services/cache.py`: Redis operations (for daily send limit tracking)

### Established Patterns
- External API sync: wrap sync SDK in asyncio.to_thread, store external_id, UNIQUE constraint
- Webhook processing: inbound → HMAC verify → webhook_events → ai_jobs queue
- Scheduled workers: integrate into existing workflow worker tick cycle
- Agent tools: return structured dicts, registered via tool_registry.py

### Integration Points
- `app/agents/sales/agent.py`: Add HubSpot CRM tools (replacing the renamed hubspot_setup_guide)
- `app/agents/marketing/agent.py`: Add email sequence tools on EmailMarketingAgent
- `app/routers/webhooks.py`: Add HubSpot webhook handler
- `app/workflows/worker.py`: Add email delivery tick
- `supabase/migrations/`: New tables (hubspot_deals, email_sequences, email_sequence_steps, email_sequence_enrollments, email_tracking_events)
- Existing `contacts` table: Add `hubspot_contact_id` column

</code_context>

<specifics>
## Specific Ideas

- HubSpot integration should make the fake `hubspot_setup_guide` tool (renamed in Phase 38) obsolete — replace it with real CRM tools
- Email sequences should feel like a lightweight Mailchimp, not a full ESP — the AI generates the content, the system handles delivery and tracking
- CRM-aware responses are the killer feature — "how is the Acme deal going?" returning real pipeline data instead of generic advice is the difference between AI slop and real value

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 42-crm-email-automation*
*Context gathered: 2026-04-04*

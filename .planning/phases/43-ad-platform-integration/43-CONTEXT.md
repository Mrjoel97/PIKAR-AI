# Phase 43: Ad Platform Integration - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Connect Google Ads and Meta Ads accounts via OAuth, let agents manage campaigns with mandatory human approval for budget/spend operations, pull real performance data on a schedule, enforce per-platform monthly budget caps, generate platform-aware ad copy with CRM audience context, and fire budget pacing alerts when spend is off-track.

</domain>

<decisions>
## Implementation Decisions

### Approval Gate Trigger Points
- **Gated operations (require approval card before executing on ad platform):**
  - Increase daily or total budget on an active campaign
  - Change bid strategy or bid amount upward
  - Activate a campaign for the first time (transitions draft → active, starts spending)
  - Resume a campaign that was paused (re-starts spending)
- **Non-gated operations (execute immediately):**
  - Create campaigns in draft status (no money moves)
  - Pause campaigns (stops spending — always safe)
  - Decrease budget or bid amount (reduces spending)
  - Update targeting, copy, or creative on paused campaigns
- **Budget approval carries forward:** Once a budget is approved at activation, resuming that campaign later does NOT require re-approval — only triggers again if the budget is increased
- **Drafts are free:** Creating a campaign with any budget in draft status requires no approval — the gate fires at activation when money would actually start moving

### Approval UX
- **Confirmation card in chat** — agent shows a rich card with:
  - Campaign name and platform
  - Action being taken (e.g., "Set daily budget", "Activate campaign")
  - Current and new budget values
  - **Projected monthly impact** (daily budget × 30) to help users understand real cost
  - Remaining budget cap headroom (how much of the monthly cap is left)
  - Approve / Reject buttons inline in chat
- Uses the existing `request_human_approval()` pattern underneath but renders as a rich card in the frontend
- If approval expires (24h), falls back to magic link

### Budget Cap & Overspend Protection
- **Per-platform monthly cap:** User sets a monthly spending ceiling per platform (e.g., $5,000/mo Google Ads, $3,000/mo Meta Ads)
- **Required on first connect:** OAuth flow won't complete until the user sets a monthly budget cap. Prevents accidental overspend from day one.
- **Block + alert on cap hit:** Agent refuses to create/activate campaigns that would push total active campaign budgets above the cap. Clear message: "This would exceed your $X/mo [Platform] cap ($Y already committed). Increase your cap in Settings or reduce other campaigns."
- **Existing campaigns keep running** when cap is reached — only new budget commitments are blocked
- **Configuration:** Both integration settings page (under the provider card) AND via agent chat command ("Set my Google Ads budget cap to $5,000/month")
- **Budget cap stored in:** `integration_sync_state` metadata or a new `ad_budget_caps` table (Claude's discretion)

### Budget Pacing Alerts (ADS-05)
- **Percentage-based:** Alert when daily spend pace would exceed the monthly cap before month end. E.g., "Google Ads is spending $220/day — at this rate you'll hit your $5,000 cap by the 23rd."
- **Uses existing** `AdSpendTrackingService.get_budget_pacing()` logic — extend it with monthly cap awareness
- **Alert delivery:** Notification center (existing NotificationCenter bell icon) + agent proactive mention if user is in chat with the marketing agent. Phase 45 will add Slack/Teams delivery.

### Performance Data Sync
- **Frequency:** Every 6 hours via scheduled worker (4x/day) + on-demand when agent or user requests fresh data
- **Sync scope:** Active campaigns + campaigns paused within the last 30 days. Long-dormant campaigns stop syncing to save API quota. User can trigger a manual refresh for older campaigns.
- **Data pulled:** Impressions, clicks, conversions, conversion value, spend — stored in existing `ad_spend_tracking` table via `AdSpendTrackingService.record_daily_spend()`
- **Google Ads reporting delay:** ~3 hours inherent delay in Google Ads Reporting API — the 6-hour schedule accommodates this
- **Scheduled worker:** Integrates into existing `workflow_trigger_service` scheduler pattern (same as email delivery tick in Phase 42)

### Ad Creative Generation Flow
- **Workflow:** Generate → review in chat → push to platform
  1. Agent (ContentCreationAgent) generates ad copy
  2. Shows as a preview card in chat with platform-specific formatting
  3. User can: approve ("Use this" → creates ad_creative + pushes to platform), request edits ("make it shorter"), or regenerate
  4. Pushing to platform creates the creative via Google Ads / Meta Ads API
- **Platform-aware generation:** Agent knows platform constraints and generates format-specific copy:
  - Google Search Ads: 3 headlines (30 chars each) + 2 descriptions (90 chars each)
  - Meta Feed/Stories: Primary text + headline + description + CTA
  - Responsive display ads: multiple headlines + descriptions + images
- **CRM-audience-aware:** Agent reads campaign target audience + HubSpot contact segment data (Phase 42) to inform tone and messaging. B2B audience gets professional tone, DTC gets casual, etc.

### Claude's Discretion
- Google Ads API client structure (google-ads-python SDK with gRPC)
- Meta Marketing API client structure (REST + SDK choice)
- Exact scheduled worker integration (cron interval, batch size)
- OAuth scope selection for each platform
- Ad creative preview card frontend component styling
- Error handling for API rate limits and temporary failures
- Whether to use `ad_budget_caps` table or `integration_sync_state.metadata`
- Platform-specific targeting parameter mapping
- Conversion tracking setup flow (pixel/tag configuration)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/ad_management_service.py`: Full CRUD for `ad_campaigns`, `ad_creatives`, `ad_spend_tracking` — including budget pacing calculation. This is the local data layer; Phase 43 adds the external API bridge.
- `app/agents/tools/approval_tool.py`: `request_human_approval()` with magic link pattern — extend for rich confirmation cards
- `app/services/integration_manager.py`: Phase 39 credential storage + OAuth token refresh with async locking
- `app/config/integration_providers.py`: Provider registry — add Google Ads and Meta Ads entries
- `app/services/workflow_trigger_service.py`: Scheduler tick pattern — reuse for 6-hour performance data sync
- `app/agents/marketing/tools.py`: Existing campaign CRUD tools — extend with ad platform-specific tools
- `app/services/notification_service.py`: Notification delivery for pacing alerts
- `supabase/migrations/20260318300000_ad_management.sql`: Tables already exist (`ad_campaigns`, `ad_creatives`, `ad_spend_tracking`) with `platform_campaign_id` and `platform_creative_id` columns ready for external IDs

### Established Patterns
- External API sync: wrap sync SDK in `asyncio.to_thread`, store external_id, UNIQUE constraint (Phase 41 Stripe/Shopify)
- Webhook processing: inbound → HMAC verify → webhook_events → ai_jobs queue (Phase 39)
- Scheduled workers: integrate into existing workflow worker tick cycle (Phase 42 email delivery)
- Agent tools: raw function exports, `sanitize_tools` handles wrapping at agent level (Phase 41)
- Approval flow: `request_human_approval()` → approval_requests table → magic link → callback

### Integration Points
- `app/agents/marketing/agent.py`: Add Google Ads + Meta Ads campaign management tools on MarketingAutomationAgent
- `app/agents/content/agent.py`: Add ad copy generation tools on ContentCreationAgent
- `app/config/integration_providers.py`: Register `google_ads` and `meta_ads` providers
- `app/routers/integrations.py`: Add budget cap configuration endpoints
- `app/fast_api_app.py`: Mount any new routers
- `frontend/src/app/dashboard/configuration/page.tsx`: Add Google Ads / Meta Ads cards with budget cap input
- `supabase/migrations/`: New migration for budget_caps table (if not using sync_state metadata)

</code_context>

<specifics>
## Specific Ideas

- Approval cards should feel like a financial confirmation dialog — show the money impact clearly, not just the technical action
- Budget caps being required on first connect is a trust feature — prevents the "I connected my Google Ads and the AI spent $10,000" nightmare scenario
- Creative generation should feel like having a copywriter in the room — show platform-formatted previews, iterate via conversation, then push when happy
- Performance data doesn't need to be real-time — 6-hour cadence is fine because ad platforms themselves have reporting delays

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 43-ad-platform-integration*
*Context gathered: 2026-04-05*

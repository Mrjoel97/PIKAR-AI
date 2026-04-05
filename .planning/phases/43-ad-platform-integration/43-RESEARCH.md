# Phase 43: Ad Platform Integration — Research

**Researched:** 2026-04-05
**Phase Goal:** Users can manage Google Ads and Meta Ads campaigns through Pikar with mandatory human approval for all budget operations

## Executive Summary

Phase 43 bridges Pikar's existing local ad campaign management (tables, services, agent tools already exist) to the real Google Ads and Meta Ads APIs. The primary work is: (1) register two new OAuth providers, (2) build API client services that sync external campaigns ↔ local `ad_campaigns` table, (3) add approval gates for budget/spend operations, (4) schedule 6-hour performance data pulls, (5) implement per-platform monthly budget caps, and (6) add ad copy generation tools. The existing `AdCampaignService`, `AdCreativeService`, and `AdSpendTrackingService` remain as the local data layer — new services wrap the external APIs and write through to these.

## Codebase Analysis

### What Already Exists

**Database tables (migration `20260318300000_ad_management.sql`):**
- `ad_campaigns` — full schema with `platform` (google_ads/meta_ads), `platform_campaign_id` for external linking, targeting JSONB, budget fields, bid strategy, status enum (draft/pending_review/active/paused/completed/rejected)
- `ad_creatives` — with `platform_creative_id`, creative types, specs JSONB, A/B variant, performance JSONB
- `ad_spend_tracking` — daily metrics with UNIQUE on (ad_campaign_id, tracking_date), derived CTR/CPC/CPA/ROAS

**Services (`app/services/ad_management_service.py`):**
- `AdCampaignService` — full CRUD, RLS-scoped
- `AdCreativeService` — full CRUD, RLS-scoped
- `AdSpendTrackingService` — record_daily_spend (upsert), get_spend_summary, get_budget_pacing (with pacing status, recommendations)

**Agent tools (`app/agents/marketing/tools.py` lines 1289-1700):**
- 10 existing tools: `create_ad_campaign`, `get_ad_campaign`, `update_ad_campaign`, `list_ad_campaigns`, `create_ad_creative`, `list_ad_creatives`, `update_ad_creative`, `record_ad_spend`, `get_ad_performance`, `get_budget_pacing`
- All call through to `AdCampaignService`/`AdCreativeService`/`AdSpendTrackingService`

**Marketing agent sub-agent (`app/agents/marketing/agent.py` line 169):**
- Ad Platform Sub-Agent already defined with 12 tools including `generate_image`
- Instruction references Google/Meta but currently operates only on local DB

**Integration infrastructure (Phase 39):**
- `IntegrationManager` — credential storage, OAuth token refresh with async locking
- `PROVIDER_REGISTRY` — 8 providers defined; Google Ads and Meta Ads NOT yet registered
- `app/routers/integrations.py` — OAuth authorize/callback flow
- Frontend configuration page shows provider cards with connect/disconnect

**Approval system:**
- `request_human_approval()` in `app/agents/tools/approval_tool.py` — creates approval_requests row with magic link token
- `magic_link_approvals.py` — email-based approval with rich HTML buttons
- Frontend approval page at `/approval/{token}`

**Notification service (`app/notifications/notification_service.py`):**
- `NotificationService.create_notification()` — supports type (info/success/warning/error), link, metadata
- Used by Shopify inventory alerts pattern — same pattern for budget pacing alerts

### What Must Be Built

1. **Provider registry entries** for `google_ads` and `meta_ads` in `integration_providers.py`
2. **Google Ads API client service** — campaign CRUD, performance data pull
3. **Meta Ads API client service** — campaign CRUD, performance data pull
4. **Budget cap storage + enforcement** — new table or `integration_sync_state` metadata
5. **Approval gate decorator/wrapper** — intercepts budget/spend operations, creates approval card
6. **Scheduled performance sync worker** — 6-hour tick via workflow_trigger_service pattern
7. **Ad copy generation tool** — platform-aware copy generation on ContentCreationAgent
8. **Frontend budget cap input** — on Google Ads / Meta Ads provider cards

## Technical Decisions

### Google Ads API

**SDK:** `google-ads-python` (official, gRPC-based). Heavy dependency (~50MB with protobuf). Alternative: REST API via `httpx` (lighter, sufficient for campaign CRUD + reporting).

**Recommendation:** Use `httpx` REST calls against Google Ads REST API v17. Reasons:
- Lighter dependency (no protobuf/gRPC)
- Consistent with Meta Ads approach (also REST)
- Wrap in `asyncio.to_thread` only if needed (httpx is natively async)
- Google Ads REST API has identical functionality to gRPC for our use cases

**OAuth scopes needed:**
- `https://www.googleapis.com/auth/adwords` (full access to Google Ads API)

**Key API endpoints:**
- `POST /customers/{customerId}/campaigns` — create campaign
- `POST /customers/{customerId}/campaigns:mutate` — update/pause/resume
- `POST /customers/{customerId}/googleAds:searchStream` — GAQL query for reporting
- Reports have ~3 hour delay for fresh data

**Rate limits:** 15,000 requests/day per developer token (shared across all users). Basic access level is sufficient for start.

### Meta Marketing API

**SDK:** `facebook-business` Python SDK. Alternative: REST API via `httpx`.

**Recommendation:** Use `httpx` REST calls. Same reasoning as Google Ads — lighter, async-native.

**OAuth scopes needed:**
- `ads_management` — create/edit campaigns
- `ads_read` — read campaign performance
- `business_management` — manage ad accounts

**Key API endpoints:**
- `POST /act_{ad_account_id}/campaigns` — create campaign
- `POST /{campaign_id}` — update campaign (status, budget)
- `GET /act_{ad_account_id}/insights` — performance reporting
- Reports are near-real-time (minutes delay, not hours)

**Rate limits:** Per-app rate limiting with Business Use Case Rate Limits. Standard tier: 200 calls/hour/ad account.

### Approval Gate Architecture

The existing `request_human_approval()` creates a magic link. For budget operations, we need a richer experience: confirmation card in chat with projected impact.

**Approach:** Create a new `request_ad_budget_approval()` function that:
1. Stores the pending operation in `approval_requests` with type `AD_BUDGET_CHANGE`
2. Returns a structured response the frontend renders as a confirmation card (not just a magic link)
3. Card payload includes: campaign name, platform, action, current budget, new budget, projected monthly impact, cap headroom
4. On approve → executes the actual API call to Google/Meta
5. On reject → marks approval as rejected, no API call

**Frontend rendering:** The SSE chat stream receives the approval card as a structured message (similar to widget messages). Frontend renders it as an interactive card with Approve/Reject buttons that POST to `/approvals/{id}/decide`.

### Budget Cap Enforcement

**Storage:** New `ad_budget_caps` table:
```sql
CREATE TABLE ad_budget_caps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    platform TEXT NOT NULL CHECK (platform IN ('google_ads', 'meta_ads')),
    monthly_cap DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (user_id, platform)
);
```

**Enforcement point:** Before any campaign activation or budget increase, check:
1. Sum all active campaign daily_budgets × remaining_days_in_month for the platform
2. Compare against monthly_cap
3. Block if would exceed

**Configuration:** Require cap during OAuth flow completion. Store in `ad_budget_caps`. Expose via REST endpoint AND agent tool.

### Performance Sync Worker

**Pattern:** Follow Phase 42 email delivery worker — integrate into the scheduled tick system.

**Implementation:**
1. New `AdPerformanceSyncService` with `sync_all_users()` method
2. For each user with active Google Ads / Meta Ads credentials:
   - Pull campaign performance data for last 7 days (covers 3-hour Google delay)
   - Upsert into `ad_spend_tracking` via existing `AdSpendTrackingService`
   - Check budget pacing against monthly cap
   - Fire notification if overpacing
3. Scheduled via Cloud Scheduler hitting a dedicated endpoint (e.g., `POST /internal/sync/ad-performance`)
4. Runs every 6 hours

### Ad Copy Generation

**Approach:** New tool `generate_ad_copy()` on the Ad Platform sub-agent that:
1. Reads campaign context (targeting, objective, platform)
2. Optionally reads HubSpot audience segment data (Phase 42)
3. Uses Gemini to generate platform-specific ad copy:
   - Google Search: 15 headlines (30 chars) + 4 descriptions (90 chars) for responsive search ads
   - Meta Feed: primary text + headline + description + CTA options
4. Returns structured copy for preview in chat
5. On approval, creates `ad_creatives` record + pushes to platform API

## Validation Architecture

### Requirement Coverage

| Req ID | What to Validate | How |
|--------|-----------------|-----|
| ADS-01 | Google Ads OAuth connect | Test OAuth flow end-to-end; verify credentials stored encrypted |
| ADS-02 | Meta Ads OAuth connect | Same as ADS-01 for Meta |
| ADS-03 | Create/pause/resume with approval gate | Test that budget operations trigger approval, non-budget ops execute immediately |
| ADS-04 | Performance reporting available | Test data pull populates ad_spend_tracking; verify agent can query it |
| ADS-05 | Budget pacing alerts | Test notification fires when overpacing detected |
| ADS-06 | Hard budget cap enforcement | Test cap blocks activation when would exceed; test cap required on connect |
| ADS-07 | Ad copy generation | Test platform-specific copy generation with correct format constraints |

### Integration Test Strategy

1. **Mock external APIs** — Google Ads and Meta Ads API calls mocked at httpx transport level
2. **Real approval flow** — Test approval_requests creation and decision callback
3. **Real notification flow** — Test NotificationService.create_notification calls
4. **Real DB operations** — All ad_campaigns/ad_creatives/ad_spend_tracking operations hit test DB

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Google Ads developer token requires approval | Blocks real API testing | Use test accounts; REST API works with test credentials |
| Meta Ads app review process | Blocks production use | Submit early; use test ad accounts during development |
| API rate limits per ad account | Could block sync for heavy users | Batch requests; 6-hour sync interval is conservative |
| Budget cap race condition | Two concurrent activations could exceed cap | Use SELECT FOR UPDATE or advisory lock on cap check |
| Stale performance data | Budget pacing alerts based on 6-hour-old data | Clearly label data freshness in UI; on-demand refresh available |

## Implementation Approach

### Plan Structure (3 plans)

**Plan 1 (Wave 1): Database + Provider Registration + API Client Services**
- Migration: `ad_budget_caps` table
- Register `google_ads` and `meta_ads` in `PROVIDER_REGISTRY`
- `GoogleAdsService` — OAuth token usage, campaign CRUD, reporting queries
- `MetaAdsService` — OAuth token usage, campaign CRUD, reporting queries
- Budget cap enforcement service
- Env vars: `GOOGLE_ADS_CLIENT_ID`, `GOOGLE_ADS_CLIENT_SECRET`, `GOOGLE_ADS_DEVELOPER_TOKEN`, `META_ADS_CLIENT_ID`, `META_ADS_CLIENT_SECRET`

**Plan 2 (Wave 1): Approval Gates + Performance Sync + Budget Alerts**
- `request_ad_budget_approval()` function with rich card payload
- Approval callback handler that executes actual API operation on approve
- `AdPerformanceSyncService` with 6-hour scheduled sync
- Budget pacing check integrated into sync cycle
- Notification fire on overpacing

**Plan 3 (Wave 2, depends on Plans 1+2): Agent Tools + Ad Copy Generation + Frontend**
- New/updated agent tools wrapping external API operations
- Ad copy generation tool with platform-aware formatting
- Frontend budget cap input on provider cards
- Agent instruction updates for approval gate behavior

## RESEARCH COMPLETE

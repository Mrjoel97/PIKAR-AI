---
phase: 43-ad-platform-integration
plan: 01
subsystem: integrations
tags: [google-ads, meta-ads, oauth2, budget-caps, ad-platform]
dependency_graph:
  requires:
    - app/services/integration_manager.py
    - app/services/base_service.py
    - app/config/integration_providers.py
    - supabase/migrations/20260318300000_ad_management.sql
  provides:
    - google_ads OAuth provider registration
    - meta_ads OAuth provider registration
    - GoogleAdsService (REST API v17 client)
    - MetaAdsService (Graph API v19 client)
    - AdBudgetCapService (monthly cap enforcement)
    - ad_budget_caps table
  affects:
    - app/routers/admin/integrations (OAuth flows will reference new providers)
    - Phase 43 Plan 02 (ad agent tools consume GoogleAdsService + MetaAdsService)
tech_stack:
  added:
    - httpx (lazy import per service) — async HTTP for Google Ads REST + Meta Graph API
  patterns:
    - BaseService / AdminService inheritance
    - IntegrationManager.get_valid_token for OAuth credential retrieval
    - Lazy httpx imports (consistent with shopify_service.py pattern)
    - Always-PAUSED campaign creation (safety gate before approval)
    - micros-to-USD conversion for Google Ads budget values
    - cents-to-USD conversion for Meta Ads budget values
key_files:
  created:
    - supabase/migrations/20260405900000_ad_budget_caps.sql
    - app/services/google_ads_service.py
    - app/services/meta_ads_service.py
    - app/services/ad_budget_cap_service.py
  modified:
    - app/config/integration_providers.py
decisions:
  - "google_ads and meta_ads registered in PROVIDER_REGISTRY as oauth2 providers in the analytics category"
  - "New campaigns always created as PAUSED regardless of caller-supplied status — activation requires separate approval gate"
  - "Google Ads budgets use micros (divide/multiply by 1_000_000); Meta Ads budgets use cents (divide/multiply by 100)"
  - "AdBudgetCapService writes use AdminService (service role) so cap management works from background tasks without user JWT"
  - "Budget headroom calculated as: committed = sum(active daily_budgets) x remaining calendar days; proposed must fit within headroom"
metrics:
  duration: 11min
  completed_date: "2026-04-05"
  tasks_completed: 2
  files_created: 4
  files_modified: 1
---

# Phase 43 Plan 01: Ad Platform Foundation Summary

Google Ads and Meta Ads registered as OAuth2 providers with full REST/Graph API client services and per-platform monthly budget cap enforcement backed by a new `ad_budget_caps` migration.

## What Was Built

### Task 1: Database Migration (`ad_budget_caps`)

`supabase/migrations/20260405900000_ad_budget_caps.sql` creates the `public.ad_budget_caps` table:
- Per-user, per-platform monthly ceiling with UNIQUE constraint on `(user_id, platform)`
- RLS: SELECT/INSERT/UPDATE/DELETE on `auth.uid() = user_id` + service_role bypass
- `moddatetime` trigger on `updated_at` (consistent with existing ad table pattern)
- Index on `user_id` for fast cap lookups

### Task 2: Providers + Services

**`app/config/integration_providers.py`** — Two new `ProviderConfig` entries:
- `google_ads`: OAuth2, `https://www.googleapis.com/auth/adwords` scope, `GOOGLE_ADS_CLIENT_ID/SECRET`
- `meta_ads`: OAuth2, `ads_management/ads_read/business_management` scopes, `META_ADS_CLIENT_ID/SECRET`

**`app/services/google_ads_service.py`** — `GoogleAdsService(BaseService)` (512 lines):
- `_get_headers`: Retrieves OAuth token via `IntegrationManager`, adds `developer-token` header and optional `login-customer-id` from env
- `get_accessible_customers`: Lists all MCC-accessible customer resource names
- `list_campaigns`: GAQL `searchStream` query — maps micros to USD, returns normalised status strings
- `create_campaign`: Two-step (budget resource first, then campaign); always creates as `PAUSED`
- `update_campaign_status`: Maps `active/paused` to `ENABLED/PAUSED`
- `update_campaign_budget`: Updates `amountMicros` on an existing budget resource
- `get_campaign_performance`: GAQL daily metrics query with cost_micros-to-USD conversion

**`app/services/meta_ads_service.py`** — `MetaAdsService(BaseService)` (455 lines):
- `_get_token`: Retrieves OAuth token via `IntegrationManager`, raises on missing connection
- `get_ad_accounts`: Lists ad accounts via `/me/adaccounts`; normalises balance from cents
- `list_campaigns`: Graph API campaign list; maps status enums, converts cents budgets to USD
- `create_campaign`: POST to `/act_{id}/campaigns`; always sends `status: PAUSED`
- `update_campaign_status`: POST to `/{campaign_id}` with mapped status
- `update_campaign_budget`: POST to `/{campaign_id}` with cent-value budget fields
- `get_campaign_insights`: Daily insights via `/act_{id}/insights`; parses `actions` array for conversion count

**`app/services/ad_budget_cap_service.py`** — `AdBudgetCapService(BaseService)` (224 lines):
- `get_cap`: SELECT from `ad_budget_caps` for user + platform
- `set_cap`: AdminService upsert on `(user_id, platform)` — idempotent
- `is_cap_set`: Convenience bool wrapper around `get_cap`
- `check_budget_headroom`: Calculates remaining calendar days, sums active campaign daily budgets, returns `allowed/committed/headroom/proposed_monthly/message` dict with human-readable denial message when cap would be exceeded

## Deviations from Plan

None — plan executed exactly as written.

## Key Decisions Made

1. **Always-PAUSED campaign creation** — Both services ignore the caller-supplied `status` parameter and always create campaigns as `PAUSED`. This enforces the v6.0 decision that real-money budget operations require an approval gate before activation.

2. **AdminService for cap writes** — `AdBudgetCapService.set_cap` uses `AdminService` (service role) so cap management can be triggered from admin workflows and background tasks without a user JWT in context.

3. **Budget unit conventions** — Google Ads uses micros (÷ 1,000,000 on read, × 1,000,000 on write). Meta uses cents (÷ 100 on read, × 100 on write). Both services handle conversions internally; callers always work in USD.

4. **Headroom formula** — `committed = sum(active_daily_budgets) × remaining_days_in_month`. This is conservative (counts every active campaign's full remaining-month burn) rather than just looking at this month's actuals.

## Commits

- `68db9e7` feat(43-01): add ad_budget_caps migration
- `4b3a3a2` feat(43-01): add Google Ads + Meta Ads providers and API client services

## Self-Check: PASSED

All created files exist on disk. Both task commits (68db9e7, 4b3a3a2) confirmed present in git history.

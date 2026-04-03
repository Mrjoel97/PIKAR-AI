# Project Research Summary

**Project:** Pikar-AI v6.0 — Real-World Integration & Solopreneur Unlock
**Domain:** External SaaS integrations, persona philosophy fix, capability gaps
**Researched:** 2026-04-04

## Key Findings

### Stack Additions
- **CRM:** `hubspot-api-client` (sync SDK, wrap with asyncio.to_thread)
- **Ads:** `google-ads` + `facebook-business` (REAL MONEY — approval gates mandatory)
- **PM:** `asana` SDK + httpx for Linear GraphQL
- **Docs:** `weasyprint` (HTML→PDF) + `python-pptx` (slides)
- **Chat:** `slack-sdk` (has native async) + httpx for Teams Graph API
- **Data:** `polars` for fast CSV, `google-cloud-bigquery` for BigQuery
- **E-commerce:** httpx for Shopify GraphQL (no SDK needed)
- All others use existing libraries (httpx, stripe, asyncpg, Google APIs)

### Feature Table Stakes
1. Solopreneur gets EVERYTHING except team features (low complexity, high impact)
2. Tool rename is a trust fix, not a feature (low complexity, critical for honesty)
3. Stripe sync is the easiest win — already have the SDK
4. CRM is the highest-value integration — every business user expects it
5. Ad platforms are highest-complexity — real money + OAuth approval processes
6. Document generation fills the "can't export anything" gap
7. Webhook system enables the entire Zapier/automation ecosystem

### Watch Out For
- **Real money APIs (P1):** Google Ads and Meta Ads can spend real money. MUST use approval gates for ALL budget operations. No exceptions.
- **OAuth token refresh races (P2):** Multiple agents sharing tokens need a lock-based refresh manager
- **Email reputation (P5):** Automated sequences need warm-up, bounce monitoring, CAN-SPAM compliance
- **Sync conflicts (P6):** Bidirectional sync (HubSpot↔Pikar) needs conflict resolution strategy
- **SQL injection (P4):** External DB connectors must be read-only with parameterized queries only
- **Backward compat (P10, P11):** Solopreneur unlock and tool rename must not break existing users

### Build Order
10 phases (38-47), dependency-ordered:
1. Phase 38: Solopreneur unlock + tool rename (no deps, immediate value)
2. Phase 39: Integration infrastructure (credentials, webhooks, sync state)
3. Phase 40: Data I/O (CSV, PDF — no external API deps)
4. Phase 41: Financial (Stripe sync, Shopify)
5. Phase 42: CRM + Email (HubSpot, sequences)
6. Phase 43: Ad platforms (Google Ads, Meta — highest complexity)
7. Phase 44: Project management (Linear, Asana)
8. Phase 45: Communication (Slack, Teams)
9. Phase 46: Analytics + Intelligence (external DB, calendar, monitoring)
10. Phase 47: Polish (Zapier compat, team collaboration, health dashboard)

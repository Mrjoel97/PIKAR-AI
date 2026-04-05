---
phase: 43-ad-platform-integration
plan: 03
subsystem: api
tags: [google-ads, meta-ads, agent-tools, ad-copy, budget-cap, approval-gate, react, nextjs]

requires:
  - phase: 43-01
    provides: GoogleAdsService, MetaAdsService, AdBudgetCapService with real API calls
  - phase: 43-02
    provides: AdApprovalService.check_and_gate(), AdPerformanceSyncService.sync_user_on_demand()

provides:
  - AD_PLATFORM_TOOLS: 13 agent tools bridging agents to real Google/Meta Ads APIs
  - AD_COPY_TOOLS: platform-aware ad copy context + creative save tool
  - Updated MarketingAutomationAgent Ad Platform sub-agent with real API tools
  - Updated ContentCreationAgent CopywriterAgent with ad copy generation
  - Frontend budget cap UI on Google Ads and Meta Ads configuration cards

affects:
  - MarketingAutomationAgent (ad campaign management via chat)
  - ContentCreationAgent (ad copy generation via chat)
  - dashboard/configuration (budget cap required before OAuth connect)
  - AdApprovalService (called by activate_ad_campaign and increase budget tools)

tech-stack:
  added: []
  patterns:
    - "Agent tools use lazy imports + get_current_user_id() — same pattern as email_sequence_tools.py"
    - "Budget-changing tools return approval card data from check_and_gate(); agents surface it to user"
    - "Frontend budget cap gates OAuth: cap must exist before Connect button activates"
    - "fetchWithAuth used for budget cap API calls (JWT-authenticated, consistent with integrations service)"

key-files:
  created:
    - app/agents/tools/ad_platform_tools.py
    - app/agents/tools/ad_copy_tools.py
  modified:
    - app/agents/marketing/agent.py
    - app/agents/content/agent.py
    - frontend/src/app/dashboard/configuration/page.tsx

key-decisions:
  - "AD_PLATFORM_TOOLS replaces local-only ad tools in marketing agent; 8 deprecated imports removed"
  - "Budget increases are gated via check_and_gate(); decreases execute immediately without approval"
  - "get_ad_copy_context() fetches CRM audience data (lifecycle distribution, top companies) from contacts table when HubSpot connected"
  - "Frontend fetchBudgetCap uses fetchWithAuth (direct backend call) not a Next.js proxy route, matching integrations.ts pattern"
  - "Connect button for ad platforms shows amber 'Set Cap First' when no cap configured; expands card inline"

patterns-established:
  - "Approval-gated tools: call check_and_gate(), return result directly — agent surfaces approval card to user"
  - "Non-gated tools: execute immediately, update both platform API and local DB record"
  - "Ad copy workflow: always call get_ad_copy_context() first to get constraints, then generate, then save_ad_copy_as_creative()"

requirements-completed: [ADS-03, ADS-04, ADS-05, ADS-06, ADS-07]

duration: 16min
completed: 2026-04-05
---

# Phase 43 Plan 03: Agent Tools & Frontend Budget Cap UI Summary

**13 agent tools wiring Google/Meta Ads APIs with approval gate, platform-aware ad copy generation with CRM audience context, and frontend budget cap UI gating OAuth on configuration page.**

## Performance

- **Duration:** 16 min
- **Started:** 2026-04-05T02:08:46Z
- **Completed:** 2026-04-05T02:24:39Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Created `AD_PLATFORM_TOOLS` (13 tools): status checks, list campaigns, create (google+meta) always-paused, activate (GATED — returns approval card), pause (immediate), change budget (GATED if increase, immediate if decrease), performance query, on-demand sync, budget cap get/set
- Created `AD_COPY_TOOLS`: `get_ad_copy_context` returns platform constraints (Google: 15 headlines ≤30 chars, 4 descriptions ≤90 chars; Meta: primary_text ≤125, headline ≤40) plus CRM audience data from contacts table; `save_ad_copy_as_creative` saves draft creative via AdCreativeService
- Rewired MarketingAutomationAgent Ad Platform sub-agent: replaced 8 local-only tool imports with AD_PLATFORM_TOOLS + AD_COPY_TOOLS; updated instruction with real API workflow, budget safety rules, and ad copy workflow
- Added AD_COPY_TOOLS to ContentCreationAgent CopywriterAgent (singleton + factory); updated instruction with ad copy generation section including character limit enforcement rules
- Frontend: BudgetCapSection component with spend/cap progress bar (green/amber/red), dollar input + save; budget cap fetched on mount for both ad platforms; Connect button for ad platforms gated — shows "Set Cap First" if no cap configured

## Task Commits

1. **Task 1: Ad platform agent tools** - `34a201d` (feat)
2. **Task 2: Ad copy tools + agent wiring** - `9df274e` (feat)
3. **Task 3: Frontend budget cap UI** - `c71d0a6` (feat)

## Files Created/Modified

- `app/agents/tools/ad_platform_tools.py` — 13 async agent tools; AD_PLATFORM_TOOLS export; gated ops call AdApprovalService.check_and_gate()
- `app/agents/tools/ad_copy_tools.py` — get_ad_copy_context (constraints + CRM), save_ad_copy_as_creative; AD_COPY_TOOLS export
- `app/agents/marketing/agent.py` — Ad Platform sub-agent rewired to real API tools; deprecated local tool imports removed; instruction updated
- `app/agents/content/agent.py` — AD_COPY_TOOLS added to CopywriterAgent singleton and factory; instruction updated with ad copy section
- `frontend/src/app/dashboard/configuration/page.tsx` — BudgetCapSection component, budget cap state/fetch/save, OAuth gating for ad platforms

## Decisions Made

- Replaced local-only ad tools (create_ad_campaign, list_ad_campaigns, get_ad_campaign, update_ad_campaign, create_ad_creative, list_ad_creatives, update_ad_creative, record_ad_spend, get_ad_performance, get_budget_pacing) in marketing agent with the new real-API tools. The local tools still exist in marketing/tools.py for direct DB use elsewhere but are no longer exposed to the Ad Platform sub-agent.
- `get_ad_copy_context` queries the `contacts` table directly (not HubSpotService) to get audience segment distribution — avoids triggering an outbound API call just for context, uses already-synced local data.
- Frontend uses `fetchWithAuth` for budget cap API calls (same pattern as integrations.ts) rather than a Next.js proxy route — keeps consistency and avoids adding a proxy layer for a straightforward JSON endpoint.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required beyond what Plans 01 and 02 established.

## Next Phase Readiness

Phase 43 is complete. The full ad platform integration stack is now wired:
- Plan 01: GoogleAdsService, MetaAdsService, AdBudgetCapService (real API calls + DB)
- Plan 02: AdApprovalService (approval gate), AdPerformanceSyncService (scheduled sync)
- Plan 03: Agent tools exposing all capabilities via chat, frontend budget cap UI

Users can now:
1. Set a monthly budget cap on the Configuration page
2. Connect Google Ads or Meta Ads via OAuth
3. Chat with the agent to create paused campaigns, generate platform-specific ad copy, and activate campaigns (which triggers an approval card)
4. Track campaign performance via agent chat

---
*Phase: 43-ad-platform-integration*
*Completed: 2026-04-05*

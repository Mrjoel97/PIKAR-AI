---
phase: 63-marketing-agent-enhancement
plan: 02
subsystem: marketing-agent
tags: [marketing, attribution, roas, budget-optimization, cross-channel]
requirements: [MKT-03, MKT-04]
dependency_graph:
  requires:
    - app/services/ad_management_service.py (AdCampaignService, AdSpendTrackingService)
    - app/agents/tools/shopify_tools.py (get_shopify_analytics)
    - app/services/base_service.py (BaseService)
  provides:
    - app/services/cross_channel_attribution_service.py (CrossChannelAttributionService)
    - app/agents/tools/attribution_tools.py (get_cross_channel_attribution, get_budget_recommendation, ATTRIBUTION_TOOLS)
  affects:
    - app/agents/marketing/agent.py (wires ATTRIBUTION_TOOLS into parent tool list + instruction)
tech-stack:
  added: []
  patterns:
    - Lazy per-call instantiation of the service (no singleton) — matches existing marketing service patterns
    - Patchable `_get_email_attribution` method so tests can isolate email logic from Supabase
    - Plain-English summary and recommendation text baked into the service so the agent uses `summary_text` / `recommendation_text` verbatim
    - Module-level `get_shopify_analytics` patched in tests to avoid the Shopify SDK chain
key-files:
  created:
    - app/services/cross_channel_attribution_service.py
    - app/agents/tools/attribution_tools.py
    - tests/unit/services/test_cross_channel_attribution_service.py
  modified:
    - app/agents/marketing/agent.py
decisions:
  - "Attribution service aggregates four channels (google_ads, meta_ads, email, organic) into one shape with ROAS and share_of_revenue_pct — organic is Shopify total minus attributed paid/email revenue"
  - "Budget reallocation shifts min(20% of source daily spend, $50/day) to avoid drastic single-step moves"
  - "Channels within 10% ROAS of each other are declared well-balanced (no reallocation) rather than nudging noise"
  - "Organic channel is excluded as a reallocation source since there is no spend lever to shift"
  - "Share-of-revenue drift from rounding is assigned to the largest-revenue channel so totals always sum to 100%"
  - "Default channel ROAS fixture layout in tests is 3.0/4.0/5.0 (google/email/meta) so winner/loser ordering is deterministic"
  - "Attribution tools live on the PARENT MarketingAgent (not a sub-agent) because they are strategic cross-channel decisions, not campaign-specific CRUD"
metrics:
  duration: "~25min"
  completed: "2026-04-11"
  tasks: 2
  tests_added: 9
  files_created: 3
  files_modified: 1
---

# Phase 63 Plan 02: Cross-Channel Attribution & Budget Recommendations Summary

Unified cross-channel attribution for Marketing Agent: Google Ads, Meta Ads, email, and Shopify organic revenue are reconciled into a single ROAS-comparable view, plus a ROAS-based budget reallocation tool that suggests shifts from low-ROAS to high-ROAS channels in plain English. Implements MKT-03 and MKT-04.

## What Shipped

### Task 1 — CrossChannelAttributionService (commits `131be29c`, `ffd5cc6c`)

`app/services/cross_channel_attribution_service.py` — new BaseService subclass.

**`get_attribution(user_id, days=30)`** returns:

```python
{
  "channels": [
    {"channel": "google_ads", "spend": 1200.0, "conversions": 40,
     "revenue": 3600.0, "roas": 3.0, "cpa": 30.0, "share_of_revenue_pct": 42.9},
    {"channel": "meta_ads",  "spend":  800.0, "conversions": 50,
     "revenue": 4000.0, "roas": 5.0, "cpa": 16.0, "share_of_revenue_pct": 47.6},
    {"channel": "email",     "spend":  200.0, "conversions": 20,
     "revenue":  800.0, "roas": 4.0, "cpa": 10.0, "share_of_revenue_pct":  9.5},
    {"channel": "organic",   "spend":    0.0, "conversions":  0,
     "revenue": 1400.0, "roas": 0.0, "cpa":  0.0, "share_of_revenue_pct": ...},
  ],
  "totals": {"total_spend": ..., "total_revenue": ..., "blended_roas": ...},
  "period": {"start": "...", "end": "...", "days": 30},
  "summary_text": "Meta Ads is your best performer at 5.0x ROAS ($16/customer). ..."
}
```

Data sources:
- **Google Ads / Meta Ads** — `AdCampaignService.list_ad_campaigns(platform=...)` then aggregate `AdSpendTrackingService.get_spend_summary` across each campaign id in the window
- **Email** — reads `campaigns` rows where `campaign_type = 'email'` and sums the `metrics` JSON payload (spend, revenue, conversions). Patchable via `_get_email_attribution` for tests
- **Organic** — `get_shopify_analytics("last_30_days")` minus attributed paid/email revenue, floored at zero; degrades gracefully to 0 if Shopify is not connected

**`get_budget_recommendation(user_id, days=30)`** returns:

```python
{
  "recommendation_text": "Meta Ads gives 1.7x better return than Google Ads "
                         "($5.0 vs $3.0 per $1 spent) -- shift $8.0/day from "
                         "Google Ads to Meta Ads?",
  "shift_from": {"channel": "google_ads", "current_daily": 40.0, "recommended_daily": 32.0},
  "shift_to":   {"channel": "meta_ads",   "current_daily": 26.67, "recommended_daily": 34.67},
  "expected_impact": "Could gain ~3.5 more conversions/week at current Meta Ads ROAS",
  "channels": [...],
  "action_available": True
}
```

Algorithm:
1. Call `get_attribution` to get all channels
2. Filter to eligible paid channels (spend > 0, not organic)
3. If < 2 eligible channels → `action_available=False` ("Only one paid channel...")
4. Sort by ROAS — best and worst
5. If `(best_roas - worst_roas) / worst_roas < 0.10` → `action_available=False` ("well-balanced")
6. Otherwise, shift `min(20% × source_daily_spend, $50/day)` from worst to best
7. Expected impact = `(shift × 7) / best_channel_cpa` conversions per week

### Task 2 — Attribution tools + MarketingAgent wiring (commits `4b1ab4a5`, `3c4a4324`)

`app/agents/tools/attribution_tools.py` — two agent-callable async tools:

| Tool | Wraps | Agent use case |
| --- | --- | --- |
| `get_cross_channel_attribution(days=30)` | `CrossChannelAttributionService.get_attribution` | "Which channel is best?", "Show me cross-channel performance", blended ROAS |
| `get_budget_recommendation(days=30)` | `CrossChannelAttributionService.get_budget_recommendation` | "How should I allocate my budget?", "Where should I shift money?" |

Both pull `user_id` from `request_context`, return `{"error": "Authentication required"}` on unauthenticated calls, and catch service errors into `{"error": "..."}` dicts so the agent never crashes on a tool call. Exports `ATTRIBUTION_TOOLS = [get_cross_channel_attribution, get_budget_recommendation]`.

`app/agents/marketing/agent.py` — three bounded edits:
1. `from app.agents.tools.attribution_tools import ATTRIBUTION_TOOLS` (one import line)
2. `*ATTRIBUTION_TOOLS` appended to `MARKETING_AGENT_TOOLS` parent list (two lines including comment)
3. New `- **Attribution & Budget**: ...` bullet in the `TOOLS YOU HANDLE DIRECTLY` section of `MARKETING_AGENT_INSTRUCTION`

Total diff: **+4 insertions, 0 deletions** — intentionally minimal to keep wave 2 plans (63-03, 63-04) conflict-free per the coordination note.

## Tests

`tests/unit/services/test_cross_channel_attribution_service.py` — 9 tests, all passing:

**`TestGetAttribution` (4 tests)**
- `test_returns_per_channel_breakdown` — verifies all channel fields (spend, conversions, revenue, roas, cpa, share_of_revenue_pct)
- `test_includes_all_four_channels` — verifies google_ads, meta_ads, email, organic present
- `test_google_ads_aggregation_correct` — verifies Google totals sum across multiple campaigns (ROAS 3.0, CPA $30)
- `test_share_of_revenue_percentages_sum_to_100` — rounding drift assignment holds

**`TestGetBudgetRecommendation` (5 tests)**
- `test_recommends_shift_from_lowest_to_highest_roas` — Meta (5.0x) > Google (3.0x) → shift from google to meta
- `test_recommendation_includes_plain_english_text` — mentions channel names, dollars, or shift/return
- `test_single_channel_no_reallocation_possible` — `action_available=False` when only one eligible channel
- `test_zero_spend_channels_excluded_from_reallocation_source` — zero-spend channels never become `shift_from`
- `test_balanced_roas_returns_no_reallocation` — channels within 10% ROAS return "well-balanced"

All dependencies are mocked: `AdCampaignService`, `AdSpendTrackingService`, `_get_email_attribution`, and `get_shopify_analytics`.

## Verification Results

| Check | Command | Result |
| --- | --- | --- |
| Unit tests | `uv run pytest tests/unit/services/test_cross_channel_attribution_service.py -x -v` | 9 passed |
| Ruff (service) | `uv run ruff check app/services/cross_channel_attribution_service.py` | All checks passed |
| Ruff (tools) | `uv run ruff check app/agents/tools/attribution_tools.py` | All checks passed |
| Tool importable | `python -c "from app.agents.tools.attribution_tools import ATTRIBUTION_TOOLS; print(len(ATTRIBUTION_TOOLS))"` | `Tools: 2` |
| Tools wired into parent | `python -c "from app.agents.marketing.agent import marketing_agent; ..."` | `Attribution tools wired OK` |

## Deviations from Plan

None — plan executed exactly as written. All task contracts, file paths, tool names, and return shapes match the plan's `<tasks>` and `<must_haves>` blocks.

## Deferred Issues

- **Pre-existing (not in scope):** `app/agents/marketing/agent.py:490` — `RUF013 PEP 484 prohibits implicit Optional` on `output_key: str = None` in `create_marketing_agent`. Not introduced by 63-02; logged to `.planning/phases/63-marketing-agent-enhancement/deferred-items.md`. Should be fixed in a general ruff cleanup pass.

## Coordination Notes

- Parallel plan 63-01 also touched `app/agents/marketing/agent.py` (adding `CAMPAIGN_PERFORMANCE_TOOLS` to the CampaignAgent sub-agent). Their commit landed between my Task 1 and Task 2, so I rebased my reads and placed my edits in non-overlapping locations: my imports are alphabetically adjacent but different lines, and my tool-list addition is appended to the parent `MARKETING_AGENT_TOOLS` (they modified `_CAMPAIGN_TOOLS`).
- 63-02 agent.py diff is kept to +4/-0 lines so 63-03 and 63-04 (wave 2) can append their changes cleanly without merge resolution.

## Commits

| Hash | Type | Subject |
| --- | --- | --- |
| `131be29c` | test | add failing tests for CrossChannelAttributionService |
| `ffd5cc6c` | feat | implement CrossChannelAttributionService |
| `4b1ab4a5` | feat | add attribution agent tools |
| `3c4a4324` | feat | wire attribution tools into MarketingAgent parent |

## Requirements Completed

- **MKT-03** — User can view unified cross-channel attribution showing which channel (Google Ads, Meta, Shopify, email) drives the most revenue — delivered by `get_cross_channel_attribution` returning per-channel breakdown + `summary_text`
- **MKT-04** — Marketing Agent recommends budget reallocation based on cross-channel ROAS — delivered by `get_budget_recommendation` returning `recommendation_text` with $-denominated shift suggestion

Note: MKT-03 and MKT-04 live in `.planning/milestones/v8.0-REQUIREMENTS-DRAFT.md` (v8.0 milestone is still in draft status). They are not yet promoted to the canonical `.planning/REQUIREMENTS.md`, so `requirements mark-complete MKT-03 MKT-04` returned "not_found". Requirement completion will be reflected when v8.0 requirements are promoted.

## Self-Check: PASSED

Verified via `ls` + `git log --oneline --all`:
- All 5 claimed files present on disk
- All 4 claimed commits present in git history
- 9/9 unit tests passing
- Ruff clean on both new files

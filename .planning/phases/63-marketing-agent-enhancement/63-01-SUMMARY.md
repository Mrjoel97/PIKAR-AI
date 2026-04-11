---
phase: 63-marketing-agent-enhancement
plan: 01
subsystem: agents
tags: [marketing-agent, ad-performance, google-ads, meta-ads, cpa, wow-trend, plain-english, pytest]

# Dependency graph
requires:
  - phase: ad-platform-tools (existing)
    provides: AdCampaignService.list_ad_campaigns and AdSpendTrackingService.get_spend_summary
provides:
  - CampaignPerformanceSummarizer service that aggregates ad spend + conversions across platforms
  - Plain-English summary generation with per-customer acquisition cost
  - Week-over-week trend computation (spend and conversions)
  - Agent-callable summarize_campaign_performance tool wired into CampaignAgent
affects: [63-02, 63-03, 63-04, marketing-agent-natural-language-reporting]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "plain-English summarizer service builds natural-language paragraph from structured metrics"
    - "agent tool thin-wraps service and returns both summary_text and structured data for follow-ups"
    - "WoW computed by querying current + prior window on same AdSpendTrackingService"

key-files:
  created:
    - app/services/campaign_performance_summarizer.py
    - app/agents/tools/campaign_performance_tools.py
    - tests/unit/services/test_campaign_performance_summarizer.py
  modified:
    - app/agents/marketing/agent.py

key-decisions:
  - "WoW percentage uses conversions as the primary marketing-meaningful trend signal; spend WoW is kept as a second field but customer-count trend drives the 'better/worse' text"
  - "_compute_wow returns None when prior baseline is zero rather than treating it as 0% or infinity -- caller renders 'new this week' instead"
  - "Summary text orders platforms deterministically (Google Ads first, then Meta Ads, then others) so repeated calls produce identical output"
  - "Zero-conversion branch produces explicit 'spent $X but no conversions tracked yet' phrasing so the agent never divides by zero or prints $0.00 CPA"
  - "Tool returns full structured dict (not just summary_text) so the agent can answer per-campaign follow-ups without issuing another tool call"
  - "Lazy imports inside summarize_campaign_performance body mirror ad_platform_tools.py pattern to keep agent tool module import cheap"

patterns-established:
  - "CampaignPerformanceSummarizer is the canonical pattern for future plain-English aggregators (e.g. 63-02 CrossChannelAttributionService will follow the same summary_text + structured result shape)"
  - "Agent-callable reporting tools return both summary_text (for direct display) and the raw numbers (for follow-up reasoning)"

requirements-completed: [MKT-01]

# Metrics
duration: 8min
completed: 2026-04-11
---

# Phase 63 Plan 01: Campaign Performance Summarizer Summary

**Plain-English ad performance reports with per-customer CPA and week-over-week trends, wired into the Marketing Agent's CampaignAgent sub-agent via a single `summarize_campaign_performance` tool.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-11T19:15:37Z
- **Completed:** 2026-04-11T19:23:34Z
- **Tasks:** 2
- **Files modified:** 4 (3 created, 1 modified)

## Accomplishments

- `CampaignPerformanceSummarizer.summarize_all_platforms()` aggregates every active ad campaign for a user, computes current-vs-prior spend and conversions, and builds a consultant-style paragraph like "Your Google Ads spent $340.00 this week and brought 12 customers at $28.33 each -- 20% better than last week."
- Handles all edge cases: no campaigns, single platform, multi-platform, zero conversions with spend, and missing prior-week baseline.
- `_compute_wow` correctly returns None when baseline is zero; downstream text renders "new this week" instead of an undefined percentage.
- Per-campaign breakdown includes id, name, platform, spend, conversions, CPA, prior-period values, and WoW change for drill-down.
- Agent tool `summarize_campaign_performance(days=7)` wraps the service with `_get_user_id()` context lookup and lazy imports.
- Tool wired into `_CAMPAIGN_TOOLS` inside `app/agents/marketing/agent.py`; CampaignAgent instruction updated with explicit rule to always call this tool for "how are my ads doing?"-style questions and to present `summary_text` directly.
- 10 unit tests cover multi-platform summary, WoW numeric accuracy, single-platform, empty-campaigns, zero-conversion, per-campaign structure, and all four `_compute_wow` branches.

## Task Commits

Each task was committed atomically following the TDD pattern:

1. **Task 1 RED: failing tests for CampaignPerformanceSummarizer** - `fc5f9953` (test)
2. **Task 1 GREEN: implement CampaignPerformanceSummarizer** - `4fd816fe` (feat)
3. **Task 2: wire summarize_campaign_performance into CampaignAgent** - `596109ac` (feat)

_Plan metadata commit follows this SUMMARY.md creation._

## Files Created/Modified

- `app/services/campaign_performance_summarizer.py` (created) — `CampaignPerformanceSummarizer` class with `summarize_all_platforms`, `_compute_wow`, and `_format_summary_text` methods
- `app/agents/tools/campaign_performance_tools.py` (created) — `summarize_campaign_performance` agent tool + `CAMPAIGN_PERFORMANCE_TOOLS` export
- `tests/unit/services/test_campaign_performance_summarizer.py` (created) — 10 unit tests
- `app/agents/marketing/agent.py` (modified) — import `CAMPAIGN_PERFORMANCE_TOOLS`, spread into `_CAMPAIGN_TOOLS`, extend `_CAMPAIGN_INSTRUCTION` with performance reporting section

## Decisions Made

See the `key-decisions` frontmatter block above. The most load-bearing decision is that WoW percentages use conversion counts as the "better/worse" signal displayed in natural language; spend WoW is tracked and returned as a separate field for API/dashboard consumers but not narrated.

## Deviations from Plan

None - plan executed exactly as written. Task 1 was TDD as marked (RED then GREEN), Task 2 wired the tool and updated the CampaignAgent instruction exactly as specified. One out-of-scope finding was logged to `deferred-items.md`:

- Pre-existing `RUF013` on `create_marketing_agent(output_key: str = None, ...)` at line 486 of `app/agents/marketing/agent.py`. Not caused by this plan's changes; logged per scope-boundary rules rather than fixed.

## Issues Encountered

None. All 10 tests passed on the first GREEN run. Ruff flagged one import-order issue in the test file which was auto-fixed by `ruff check --fix`.

## User Setup Required

None - no external service configuration required. The tool reads from the existing `ad_spend_tracking` table that `AdPerformanceSyncService` already keeps up to date; no new environment variables, migrations, or OAuth scopes were introduced.

## Next Phase Readiness

- Plan 63-02 (cross-channel attribution) can reuse the summarizer pattern — a separate service producing `summary_text + structured_data`, wrapped by a thin agent tool, wired into the Marketing Agent.
- The Marketing Agent can now answer "how are my ads doing?" with a single tool call that produces a ready-to-display paragraph. No blockers for downstream plans.

## Self-Check

Verified:

- `app/services/campaign_performance_summarizer.py` exists
- `app/agents/tools/campaign_performance_tools.py` exists
- `tests/unit/services/test_campaign_performance_summarizer.py` exists (10 tests, all passing)
- `app/agents/marketing/agent.py` modified (CAMPAIGN_PERFORMANCE_TOOLS imported and registered, instruction updated)
- `.planning/phases/63-marketing-agent-enhancement/deferred-items.md` logs out-of-scope RUF013
- Commits `fc5f9953`, `4fd816fe`, `596109ac` present in `git log`
- Ruff clean on all plan-scoped files
- CampaignAgent tool count moved from 12 to 14 (the additional slots are `summarize_campaign_performance` plus one context-memory tool that was already in the list via `*CONTEXT_MEMORY_TOOLS` — core tool added as expected)

## Self-Check: PASSED

---
*Phase: 63-marketing-agent-enhancement*
*Completed: 2026-04-11*

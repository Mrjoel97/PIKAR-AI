---
phase: 63-marketing-agent-enhancement
plan: 03
subsystem: agents
tags: [marketing, campaigns, conversational-ui, ad-platforms, google-ads, meta-ads, prompt-engineering, adk, non-technical-users]

# Dependency graph
requires:
  - phase: 63-marketing-agent-enhancement-01
    provides: summarize_campaign_performance tool wired on CampaignAgent for post-creation follow-up
  - phase: 63-marketing-agent-enhancement-02
    provides: cross-channel attribution tools on MarketingAgent parent (peer plan, no direct dependency)
provides:
  - CampaignAgent instruction now contains a 6-step conversational campaign creation wizard
  - Wizard auto-selects Meta Ads vs Google Ads based on what the user is promoting
  - connect_google_ads_status and connect_meta_ads_status pre-flight tools wired on CampaignAgent
  - Parent MARKETING_AGENT_INSTRUCTION routing table routes "launch a campaign" / "promote my product" / "run ads" intents to CampaignAgent wizard flow
  - 11 configuration tests guarding wizard structural wiring against regressions
affects: [63-04, 63-05, MKT-02]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Instruction-driven conversational wizards: behavior shaped via prompt steps rather than new orchestration code"
    - "Cross-sub-agent escalation: CampaignAgent wizard gathers requirements then escalates to parent -> AdPlatformAgent for real API calls"
    - "Pre-flight connection checks embedded in the wizard prompt: wizard calls connect_*_status() before recommending a platform"

key-files:
  created:
    - tests/unit/app/agents/test_marketing_campaign_wizard.py
  modified:
    - app/agents/marketing/agent.py

key-decisions:
  - "Wizard is instruction-driven (no new tools or services) — the agent's 6-step conversational flow lives entirely in _CAMPAIGN_INSTRUCTION"
  - "Pre-flight platform connection tools wired on CampaignAgent (not AdPlatformAgent) so the wizard can verify connectivity before making a platform recommendation"
  - "Wizard delegates real API calls via escalation to parent -> AdPlatformAgent rather than giving CampaignAgent direct create_google_ads_campaign / create_meta_ads_campaign access (keeps budget-cap safety rules in one place)"
  - "Tests placed under tests/unit/app/agents/ to match repo convention (plan called for tests/unit/agents/ but existing tests live in tests/unit/app/agents/)"
  - "Confirmation gate in Step 5 prevents silent campaign creation — user must explicitly approve the wizard plan before any API call fires, in addition to the PAUSED-state safety in AdPlatformAgent"

patterns-established:
  - "Conversational wizard pattern: multi-step prompt flow with gather -> recommend -> confirm -> escalate -> follow-up"
  - "Platform auto-selection heuristic: product/visual -> Meta, service/B2B/search -> Google, local -> Google, awareness -> Meta first"
  - "Wizard post-creation follow-up offers next tools (ad copy, performance summary) to keep users in a productive loop after campaign creation"

requirements-completed: [MKT-02]

# Metrics
duration: 6min
completed: 2026-04-11
---

# Phase 63 Plan 03: Conversational Campaign Creation Wizard Summary

**6-step conversational campaign wizard on CampaignAgent with auto platform recommendation (Meta vs Google), pre-flight connection checks, and PAUSED-state safety — non-technical users can now launch ad campaigns by answering plain-English questions.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-04-11T19:36:42Z
- **Completed:** 2026-04-11T19:42:35Z
- **Tasks:** 2
- **Files modified:** 2 (1 modified, 1 created)

## Accomplishments

- **Conversational campaign wizard** — extended `_CAMPAIGN_INSTRUCTION` with a 6-step wizard (goal → audience → budget → platform → confirm → post-creation follow-up) that walks users through ad campaign creation in plain English
- **Platform auto-recommendation** — wizard maps what the user is promoting to the right ad platform (product/visual → Meta Ads, service/B2B/search intent → Google Ads, local → Google, awareness → Meta-first) and explains the reasoning to the user
- **Pre-flight connection checks** — wired `connect_google_ads_status` and `connect_meta_ads_status` into `_CAMPAIGN_TOOLS` so the wizard verifies OAuth connectivity before recommending a platform and offers to walk the user through connecting one if needed
- **Cross-agent escalation flow** — wizard gathers requirements on CampaignAgent, then escalates to parent → AdPlatformAgent for the real `create_google_ads_campaign()` / `create_meta_ads_campaign()` call, keeping budget-cap safety centralized on AdPlatformAgent
- **Parent routing updated** — added `"Launch a campaign"`, `"run ads"`, `"promote my product"` intent row to the MARKETING_AGENT_INSTRUCTION routing table plus an explicit "Campaign Creation Wizard Flow" subsection
- **11 structural tests** — test suite guarding wizard instruction fragments, required tool wiring, parent routing, tool count bounds (12-20), no-duplicates invariant, and CampaignAgent sub-agent presence

## Task Commits

Each task was committed atomically:

1. **Task 1: Conversational campaign wizard instruction + tool routing** — `607814d7` (feat)
2. **Task 2: Campaign wizard integration tests** — `a6f73482` (test)

_No TDD split — wizard is an instruction/config change so tests were written after implementation to validate the wiring._

## Files Created/Modified

- `app/agents/marketing/agent.py` — extended `_CAMPAIGN_INSTRUCTION` with the CAMPAIGN CREATION WIZARD section (Steps 1-6), added `connect_google_ads_status` + `connect_meta_ads_status` to imports and `_CAMPAIGN_TOOLS`, updated `MARKETING_AGENT_INSTRUCTION` routing table with wizard intent row and "Campaign Creation Wizard Flow" explainer. **+105 / -3 lines.**
- `tests/unit/app/agents/test_marketing_campaign_wizard.py` — NEW — 11 pytest tests across 3 classes (`TestCampaignWizardInstruction`, `TestCampaignAgentTooling`, `TestParentRoutingForWizard`) validating structural wiring. **+197 lines.**

## Decisions Made

- **Wizard is prompt-only** — kept the wizard entirely in `_CAMPAIGN_INSTRUCTION` with no new tools, services, or state machines. The LLM follows the 6-step structure because the instruction tells it to. This matches existing ADK patterns (`PERFORMANCE REPORTING` section, `PUBLISHING WORKFLOW` on SocialMediaAgent) and avoids building a stateful conversation engine.
- **Pre-flight checks on CampaignAgent, not AdPlatformAgent** — the wizard needs to know connection status at Step 4 (platform recommendation) before escalating to AdPlatformAgent. Wiring `connect_google_ads_status` / `connect_meta_ads_status` on CampaignAgent lets the wizard offer "I'd recommend Meta but you haven't connected it yet — want to connect, or use Google instead?"
- **Real API calls stay on AdPlatformAgent** — CampaignAgent does NOT get direct `create_google_ads_campaign` / `create_meta_ads_campaign` access. Step 5 of the wizard escalates to parent → AdPlatformAgent so the existing budget cap checks, approval gates, and PAUSED-state safety rules in `_AD_INSTRUCTION` remain the single source of truth for ad spend safety.
- **Confirmation gate before escalation** — Step 5 requires an explicit user "Ready to create?" response before the wizard escalates. This is a second layer of safety beyond PAUSED status: users can bail out of the wizard before any API call fires, not just before activation.
- **Test location** — plan specified `tests/unit/agents/` but the repo convention is `tests/unit/app/agents/` (evident from `test_tldr_instructions.py`, `test_intent_clarification_prompt.py`). Followed repo convention to stay consistent with sibling tests and the existing `conftest.py` MockAgent fixture setup.
- **Tool count bound 12-20** — added `test_campaign_tools_count_reasonable` to catch future bloat. CampaignAgent landed at 16 tools (12 original + 2 connection checks + 1 performance summary from 63-01 + 1 buffer from sanitize_tools).

## Deviations from Plan

### Auto-fixed Issues

None — plan executed as written. Minor documented-in-decisions adjustment: test file placement uses `tests/unit/app/agents/` (existing repo convention) instead of the plan's literal `tests/unit/agents/` path. This is a path correction, not a content deviation.

---

**Total deviations:** 0 auto-fixed
**Impact on plan:** None. All 2 tasks completed exactly as scoped, with all 4 sub-actions of Task 1 and all 5 test categories of Task 2 delivered verbatim.

## Issues Encountered

- **Pre-existing `RUF013` on `app/agents/marketing/agent.py:592`** (`output_key: str = None` in `create_marketing_agent`) — flagged by ruff but explicitly out of scope per the coordination constraint. Not touched, logged in existing `deferred-items.md`. All new code in this plan is ruff-clean.
- **Parallel 63-04 modification** — 63-04 also edits `app/agents/marketing/agent.py`. Coordinated by scoping this plan's edits strictly to `_CAMPAIGN_TOOLS` / `_CAMPAIGN_INSTRUCTION` / `MARKETING_AGENT_INSTRUCTION` (the wizard prompt surface), leaving `MARKETING_AGENT_TOOLS` and sub-agent tool lists for 63-04. Re-checked git log between edits to verify no concurrent commits. 63-04 committed its Task 1 (`6ca2eb51`) after this plan's Task 1 (`607814d7`), so the two plans interleaved cleanly with no merge conflicts.

## User Setup Required

None — wizard is pure prompt/config change. Users who want to actually test the wizard end-to-end will need valid Google Ads and/or Meta Ads OAuth connections (existing setup, unchanged by this plan).

## Verification Evidence

**Automated verification from plan spec:**
```
CampaignAgent has platform connection tools
Campaign wizard instruction present
Performance summary tool still present
Parent routing mentions wizard
All checks passed
CampaignAgent tools count: 16
```

**Pytest results:**
```
tests/unit/app/agents/test_marketing_campaign_wizard.py
  TestCampaignWizardInstruction::test_campaign_agent_has_wizard_instruction      PASSED
  TestCampaignWizardInstruction::test_wizard_instruction_has_six_steps           PASSED
  TestCampaignWizardInstruction::test_wizard_delegates_creation_to_ad_platform_agent PASSED
  TestCampaignAgentTooling::test_campaign_agent_has_connection_tools             PASSED
  TestCampaignAgentTooling::test_campaign_agent_has_performance_tool             PASSED
  TestCampaignAgentTooling::test_campaign_agent_has_utm_tools                    PASSED
  TestCampaignAgentTooling::test_campaign_tools_count_reasonable                 PASSED
  TestCampaignAgentTooling::test_campaign_tools_are_unique                       PASSED
  TestParentRoutingForWizard::test_parent_routing_includes_wizard                PASSED
  TestParentRoutingForWizard::test_parent_routing_mentions_campaign_intents      PASSED
  TestParentRoutingForWizard::test_marketing_agent_has_campaign_sub_agent        PASSED
============================= 11 passed in 5.17s ==============================
```

**Ruff on new code:** All checks passed (`tests/unit/app/agents/test_marketing_campaign_wizard.py` clean; `app/agents/marketing/agent.py` has only the pre-existing deferred RUF013 on line 592 — no new violations introduced).

## Next Phase Readiness

- **MKT-02 (Natural language campaign creation) complete** — non-technical users can now create campaigns by answering "What are you promoting? / Who's your target customer? / What's your daily budget?" instead of providing technical parameters.
- **Ready for 63-04** — this plan intentionally left `MARKETING_AGENT_TOOLS`, `_CAMPAIGN_TOOLS` tool-registration code (beyond the 2 connection checks), and any sub-agent tool additions untouched. 63-04 can safely extend those surfaces.
- **Wizard surface ready for eval dataset** — wizard flow is deterministic enough (6 labeled steps, explicit confirmation gate, specific question phrasing) to write marketing_eval.json conversation traces that validate LLM compliance with the instruction. Not in scope for this plan but enabled by it.
- **No open blockers.**

## Self-Check: PASSED

Verified:
- `app/agents/marketing/agent.py` — modified, contains `CAMPAIGN CREATION WIZARD` section, `connect_google_ads_status` / `connect_meta_ads_status` in `_CAMPAIGN_TOOLS`, updated routing table. Line 636 total.
- `tests/unit/app/agents/test_marketing_campaign_wizard.py` — created, 197 lines, 11 tests all passing.
- Commit `607814d7` (feat(63-03): add conversational campaign creation wizard to CampaignAgent) — FOUND in git log.
- Commit `a6f73482` (test(63-03): add CampaignAgent wizard configuration tests) — FOUND in git log.
- CampaignAgent tool count = 16 (within 12-20 bound).
- No pre-commit hook failures observed.

---
*Phase: 63-marketing-agent-enhancement*
*Plan: 03*
*Completed: 2026-04-11*

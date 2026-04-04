---
phase: 38-solopreneur-unlock-tool-honesty
plan: 03
subsystem: personas, org-chart
tags: [persona-policy, behavioral-instructions, tool-classification, org-chart, onboarding]

# Dependency graph
requires:
  - phase: 38-02
    provides: "Renamed 7 misleading tools to honest names (knowledge tools)"
provides:
  - "Solopreneur persona rewritten as capable business operator with 30-day horizon"
  - "All 12 solopreneur behavioral instructions rewritten with comprehensive tone"
  - "Frontend KPI labels updated to Revenue Trend, Active Workflows, Compliance Score"
  - "Onboarding checklist showcases full capability set (workflows, sales, compliance, forecast)"
  - "OrgNode.tool_kinds field classifying every tool as action or knowledge"
  - "ACTION/GUIDE badge rendering in org chart AgentInspector"
affects: [persona-system, org-chart, onboarding, frontend-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Additive API fields (tool_kinds alongside existing tools) for backward compatibility"
    - "Module-level set constant (_KNOWLEDGE_TOOLS) for tool classification"
    - "ToolKindBadge component with dark mode support via Tailwind"

key-files:
  created: []
  modified:
    - app/personas/policy_registry.py
    - app/personas/behavioral_instructions.py
    - app/routers/org.py
    - frontend/src/components/org-chart/AgentInspector.tsx
    - frontend/src/components/personas/personaShellConfig.ts
    - frontend/src/components/dashboard/OnboardingChecklist.tsx
    - tests/unit/test_persona_behavioral_instructions.py
    - tests/unit/test_persona_policy_registry.py
    - tests/unit/test_tool_honesty.py

key-decisions:
  - "Solopreneur approval_posture set to auto-approve routine, escalate over $500 and compliance-sensitive"
  - "Used additive tool_kinds dict field on OrgNode instead of modifying existing tools list"
  - "Patched rate_limiter imports in test fixture to avoid .env loading issues during test"

patterns-established:
  - "Capable operator persona tone: comprehensive, confident, 30-day planning, full visibility"
  - "Tool kind classification via _KNOWLEDGE_TOOLS set with _build_tool_kinds helper"

requirements-completed: [SOLO-04, TOOL-08]

# Metrics
duration: 10min
completed: 2026-04-04
---

# Phase 38 Plan 03: Solopreneur Persona & Tool Badges Summary

**Solopreneur persona rewritten as capable business operator with 30-day planning horizon, comprehensive KPIs, and org chart ACTION/GUIDE tool badges**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-04T01:18:08Z
- **Completed:** 2026-04-04T01:28:34Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Rewrote solopreneur PersonaPolicy with "run entire business confidently" core objectives, 30-day planning horizon, comprehensive response style, and new KPIs (revenue trend, active workflows, compliance score)
- Rewrote all 12 solopreneur behavioral instruction entries (ExecutiveAgent + 11 specialized agents) with confident, full-capability tone replacing "save money, stay lean" language
- Updated frontend KPI labels, tagline, description, and onboarding checklist to showcase full capability set
- Added tool_kinds classification to org chart backend (action vs knowledge) with frontend ACTION/GUIDE badges

## Task Commits

Each task was committed atomically:

1. **Task 1: Update solopreneur persona policy, behavioral instructions, KPIs, and onboarding** - `1fbced1` (feat)
2. **Task 2: Add tool kind classification to org chart backend and frontend badges** - `318e437` (feat)

## Files Created/Modified
- `app/personas/policy_registry.py` - Solopreneur PersonaPolicy rewritten with capable operator fields
- `app/personas/behavioral_instructions.py` - All 12 solopreneur entries rewritten with comprehensive tone
- `app/routers/org.py` - Added _KNOWLEDGE_TOOLS, _build_tool_kinds(), tool_kinds field on OrgNode
- `frontend/src/components/org-chart/AgentInspector.tsx` - Added ToolKindBadge component and tool_kinds interface field
- `frontend/src/components/personas/personaShellConfig.ts` - Updated solopreneur tagline, description, kpiLabels
- `frontend/src/components/dashboard/OnboardingChecklist.tsx` - Replaced solopreneur checklist with workflow, pipeline, compliance, forecast items
- `tests/unit/test_persona_behavioral_instructions.py` - Updated solopreneur-specific assertions for new language
- `tests/unit/test_persona_policy_registry.py` - Added test_solopreneur_policy_reflects_capable_operator
- `tests/unit/test_tool_honesty.py` - Added TestOrgChartToolKinds with 3 classification tests

## Decisions Made
- Set solopreneur approval_posture to "Auto-approve routine operations. Escalate financial commitments over $500 and compliance-sensitive decisions." -- balances autonomy with appropriate guardrails
- Used additive `tool_kinds: dict[str, str]` field alongside existing `tools: list[str]` to maintain backward compatibility
- Patched rate_limiter module in test fixture to avoid .env encoding issues during unit test import of org router

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Patched rate_limiter import for test isolation**
- **Found during:** Task 2 (org chart tests)
- **Issue:** Importing `app.routers.org` triggers `app.middleware.rate_limiter` at module level, which reads `.env` with cp1252 encoding issues on Windows
- **Fix:** Added monkeypatch fixture in TestOrgChartToolKinds to stub rate_limiter and onboarding modules before import
- **Files modified:** tests/unit/test_tool_honesty.py
- **Verification:** All 3 tool kind tests pass cleanly
- **Committed in:** 318e437

**2. [Rule 1 - Bug] Corrected agent names in plan vs codebase**
- **Found during:** Task 1 (behavioral instructions)
- **Issue:** Plan referenced "MarketingCampaignAgent" and "OperationsAgent" but codebase uses "MarketingAutomationAgent" and "OperationsOptimizationAgent"
- **Fix:** Used actual codebase agent names for all behavioral instruction entries
- **Files modified:** app/personas/behavioral_instructions.py
- **Verification:** All 25 persona tests pass, all 12 solopreneur entries present
- **Committed in:** 1fbced1

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 38 (Solopreneur Unlock & Tool Honesty) is now complete with all 3 plans executed
- Solopreneur persona fully reflects "capable business operator" identity across policy, instructions, KPIs, onboarding, and org chart
- Tool honesty is complete: renamed tools (Plan 02) + classification badges (Plan 03)
- Ready for next phase in the v6.0 milestone

---
*Phase: 38-solopreneur-unlock-tool-honesty*
*Completed: 2026-04-04*

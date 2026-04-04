---
phase: 38-solopreneur-unlock-tool-honesty
plan: 02
subsystem: agents
tags: [tool-honesty, agent-tools, naming-conventions, skills-registry]

# Dependency graph
requires: []
provides:
  - 7 renamed tool functions with honest names reflecting guidance/knowledge behavior
  - Updated imports across tool_registry.py and 5 agent files
  - Agent instruction strings using honest language
  - Test suite verifying rename completeness and docstring honesty
affects: [tool-registry, agent-instructions, skills-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tool naming convention: guidance/knowledge tools use descriptive names like *_guide, *_checklist"

key-files:
  created:
    - tests/unit/test_tool_honesty.py
  modified:
    - app/agents/enhanced_tools.py
    - app/agents/tools/tool_registry.py
    - app/agents/sales/agent.py
    - app/agents/operations/agent.py
    - app/agents/marketing/agent.py
    - app/agents/strategic/agent.py
    - app/agents/data/agent.py

key-decisions:
  - "Renamed 7 tools to honest names: manage_hubspot->hubspot_setup_guide, run_security_audit->security_checklist, deploy_container->container_deployment_guide, architect_cloud_solution->cloud_architecture_guide, perform_seo_audit->seo_fundamentals_guide, generate_product_roadmap->product_roadmap_guide, design_rag_pipeline->rag_architecture_guide"
  - "Kept renamed tools in their existing agent groups (no separate KNOWLEDGE_TOOLS group)"
  - "Updated agent instruction strings to use honest language matching new tool names"

patterns-established:
  - "Tool honesty: tools that provide guidance/knowledge must be named descriptively (e.g., *_guide, *_checklist) not as action verbs (e.g., manage_*, run_*, deploy_*)"

requirements-completed: [TOOL-01, TOOL-02, TOOL-03, TOOL-04, TOOL-05, TOOL-06, TOOL-07]

# Metrics
duration: 8min
completed: 2026-04-04
---

# Phase 38 Plan 02: Tool Honesty Renames Summary

**Renamed 7 misleadingly-named agent tools to honest names reflecting their actual behavior (guidance/knowledge via skills_registry), with full import chain updates across tool_registry.py and 5 agent files**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-04T01:05:40Z
- **Completed:** 2026-04-04T01:14:01Z
- **Tasks:** 1
- **Files modified:** 8

## Accomplishments
- Renamed 7 tools from action-verb names (manage_hubspot, run_security_audit, etc.) to honest guidance names (hubspot_setup_guide, security_checklist, etc.)
- Updated function definitions with honest docstrings across enhanced_tools.py
- Updated all imports and references in tool_registry.py and 5 agent files (sales, operations, marketing, strategic, data)
- Updated agent instruction strings to use honest language matching new tool names
- Created comprehensive test suite (15 tests) verifying rename completeness, old-name absence, and docstring honesty

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Create tool honesty tests** - `abd3f9e` (test)
2. **Task 1 (GREEN): Rename all 7 tools across full import chain** - `dc4fb15` (feat)

## Files Created/Modified
- `tests/unit/test_tool_honesty.py` - 15 tests verifying tool renames, old-name absence, and honest docstrings
- `app/agents/enhanced_tools.py` - 7 function definitions renamed with honest docstrings
- `app/agents/tools/tool_registry.py` - 7 import statements and tool group references updated
- `app/agents/sales/agent.py` - hubspot_setup_guide import, instruction, and tools list
- `app/agents/operations/agent.py` - security_checklist, container_deployment_guide, cloud_architecture_guide across import, instruction, and tools list
- `app/agents/marketing/agent.py` - seo_fundamentals_guide in import, SEO sub-agent instruction, and tools list
- `app/agents/strategic/agent.py` - product_roadmap_guide in import, instruction, and tools list
- `app/agents/data/agent.py` - rag_architecture_guide in import and tools list

## Decisions Made
- Renamed tools stay in their existing agent groups (SALES_TOOLS, OPS_TOOLS, MARKETING_TOOLS, STRATEGIC_TOOLS, DATA_TOOLS) -- no separate KNOWLEDGE_TOOLS group
- Tool behavior unchanged -- only names and docstrings modified
- Agent instruction strings updated to match new honest language (e.g., "Get security checklist guidance" instead of "Run security checks")

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 7 tool renames complete with zero old names remaining in app/
- Full test suite passes with no regressions (51 tests including agent factories)
- Ready for phase 38-03 (remaining tool honesty work if any)

## Self-Check: PASSED

All 8 files verified present on disk. Both commit hashes (abd3f9e, dc4fb15) verified in git log.

---
*Phase: 38-solopreneur-unlock-tool-honesty*
*Completed: 2026-04-04*

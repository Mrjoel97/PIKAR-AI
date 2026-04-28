---
phase: 82-agent-restructuring
plan: "02"
subsystem: agents
tags: [refactor, tool-deduplication, knowledge-shared, marketing, strategic]
dependency_graph:
  requires: [82-01]
  provides: [AGT-05]
  affects: [marketing-agent, strategic-agent, content-agent, hr-agent, cs-agent, compliance-agent, data-agent]
tech_stack:
  added: []
  patterns: [shared-tool-module, import-canonical-location, routing-agent-delegation]
key_files:
  created:
    - app/agents/tools/knowledge.py
  modified:
    - app/agents/content/tools.py
    - app/agents/content/__init__.py
    - app/agents/content/agent.py
    - app/agents/marketing/agent.py
    - app/agents/hr/agent.py
    - app/agents/customer_support/agent.py
    - app/agents/compliance/agent.py
    - app/agents/data/agent.py
    - app/agents/tools/workflow_ops.py
    - app/agents/tools/tool_registry.py
    - app/agents/strategic/agent.py
decisions:
  - "search_knowledge canonical home is app.agents.tools.knowledge; content/__init__.py re-exports for backward compat"
  - "Marketing parent is pure router for content/media — video/image/blog delegate to Content Agent"
  - "start_initiative_from_idea lives only in InitiativeOpsAgent sub-agent, not in Strategic parent"
metrics:
  duration: ~26min
  completed: "2026-04-28"
  tasks: 2
  files: 12
---

# Phase 82 Plan 02: Tool Deduplication Summary

## One-Liner

Relocated search_knowledge to app/agents/tools/knowledge.py and stripped 9 duplicate tools (video/image/blog/initiative) from Marketing and Strategic parent agents.

## What Changed

### Task 1: Relocate search_knowledge to shared tools

- **Created `app/agents/tools/knowledge.py`** — canonical shared location for `search_knowledge`. The function is identical to the original in `content/tools.py`, but now lives in the shared tools layer, decoupling 6 agents from the Content module.
- **Removed `search_knowledge` from `app/agents/content/tools.py`** — eliminates the tight coupling.
- **Updated `app/agents/content/__init__.py`** — now re-exports `search_knowledge` from the new shared location, maintaining backward compatibility for any consumer doing `from app.agents.content import search_knowledge`.
- **Updated all 9 import sites** across:
  - `app/agents/content/agent.py`
  - `app/agents/marketing/agent.py`
  - `app/agents/hr/agent.py`
  - `app/agents/customer_support/agent.py`
  - `app/agents/compliance/agent.py`
  - `app/agents/data/agent.py`
  - `app/agents/tools/workflow_ops.py`
  - `app/agents/tools/tool_registry.py` (6 inline lazy imports)

### Task 2: Remove cross-agent tool duplicates

**Marketing parent agent (`app/agents/marketing/agent.py`):**
- Removed `generate_image`, `execute_content_pipeline`, `create_video_with_veo` from `MARKETING_AGENT_TOOLS` — these are already available in Content's VideoDirectorAgent and GraphicDesignerAgent sub-agents
- Removed `create_blog_post`, `get_blog_post`, `update_blog_post`, `publish_blog_post`, `list_blog_posts`, `repurpose_content` from `MARKETING_AGENT_TOOLS` — already in Content's CopywriterAgent
- Removed `from app.mcp.tools.canva_media import create_video_with_veo, execute_content_pipeline` import (now unused in parent)
- Removed blog tools from `from app.agents.marketing.tools import (...)` block (now unused in parent)
- Updated `MARKETING_AGENT_INSTRUCTION` delegation rules to explicitly delegate media/blog to Content Agent via Executive Agent

**Strategic parent agent (`app/agents/strategic/agent.py`):**
- Removed `start_initiative_from_idea` from `STRATEGIC_AGENT_TOOLS` — already in `_INITIATIVE_OPS_TOOLS` (InitiativeOpsAgent sub-agent). Import kept since it's still used in sub-agent tool list.
- Updated comment to clarify the delegation pattern

## Key Decisions

- `search_knowledge` canonical home is `app.agents.tools.knowledge`; `content/__init__.py` re-exports for backward compat — any consumer using `from app.agents.content import search_knowledge` still works without changes
- Marketing parent is a pure router for content/media — all video, image, and blog work delegates to the Content Agent's sub-agents through the Executive Agent
- `start_initiative_from_idea` lives only in InitiativeOpsAgent sub-agent, not duplicated in Strategic parent

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Import sort violation after adding search_knowledge import**
- **Found during:** Task 2 lint check
- **Issue:** Adding `from app.agents.tools.knowledge import search_knowledge` at line 14 of `marketing/agent.py` put it out of alphabetical order ahead of other `app.agents.tools.*` imports, causing an I001 ruff violation
- **Fix:** Moved the import to its correct alphabetical position between `graph_tools` and `publishing_strategy` imports
- **Files modified:** `app/agents/marketing/agent.py`
- **Commit:** b973f93b

**2. [Rule 3 - Blocking] ENOSPC during edit caused file truncation**
- **Found during:** Task 2, first attempted edit of marketing/agent.py
- **Issue:** C: drive was at 0 bytes free when attempting to write; the failed edit wiped the file to 0 bytes
- **Fix:** Restored from HEAD git commit (`git checkout HEAD -- app/agents/marketing/agent.py`), then re-applied all Task 2 changes after confirming disk freed up (git pack compression freed ~1GB)
- **Files modified:** `app/agents/marketing/agent.py`

## Self-Check: PASSED

- `app/agents/tools/knowledge.py` — exists, exports `search_knowledge`
- `app/agents/content/tools.py` — `search_knowledge` function removed
- Zero grep matches for `from app.agents.content.tools import.*search_knowledge`
- `from app.agents.tools.knowledge import search_knowledge` — imports successfully
- `from app.agents.content import search_knowledge` — backward compat works
- `marketing_agent.tools` does not contain `create_video_with_veo`, `create_blog_post`
- `strategic_agent.tools` does not contain `start_initiative_from_idea`
- 49/49 tests pass (test_admin_agent.py + test_agent_factories.py)

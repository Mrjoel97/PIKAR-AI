# Specification: ADK Compliance Remediation

## Problem Statement

The current implementation in `core_agent_ecosystem_20260119` has significant deviations from ADK best practices as documented in `.gemini/GEMINI.md`. These gaps prevent the system from leveraging ADK's native multi-agent capabilities.

## Gaps Identified

### Critical (Must Fix)

1. **No Native sub_agents Hierarchy**
   - Current: Custom `delegate_to_agent` tool that just logs delegation
   - Required: Use `sub_agents=[...]` parameter for native ADK delegation
   - Reference: GEMINI.md Section 4.2

2. **Tool Signatures Non-Compliant**
   - Current: `create_task(description, assignee=None, priority="medium")`
   - Required: No default values, add `ToolContext` parameter
   - Reference: GEMINI.md Section 7.1

### Important (Should Fix)

3. **Minimal Production App Config**
   - Current: `App(root_agent=..., name="app")`
   - Required: Add caching, compaction, and resumability configs
   - Reference: GEMINI.md Section 2.4

4. **No Workflow Agents**
   - Current: No SequentialAgent, ParallelAgent, or LoopAgent
   - Required: Implement orchestration patterns for complex workflows
   - Reference: GEMINI.md Section 3

## Technical Requirements

### Phase 1: Native Multi-Agent Hierarchy

```python
# app/agent.py - Target State
from app.agents import SPECIALIZED_AGENTS

executive_agent = Agent(
    name="ExecutiveAgent",
    model=...,
    instruction=EXECUTIVE_INSTRUCTION,
    tools=[...],
    sub_agents=SPECIALIZED_AGENTS,  # ADD THIS
)
```

### Phase 2: Tool Signature Compliance

```python
# Before
def create_task(description: str, assignee: str = None, priority: str = "medium") -> dict:

# After
from google.adk.tools import ToolContext

def create_task(description: str, tool_context: ToolContext) -> dict:
```

### Phase 3: Production App Configuration

```python
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps.events_compaction_config import EventsCompactionConfig

app = App(
    root_agent=executive_agent,
    name="pikar_ai",
    context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=600),
    events_compaction_config=EventsCompactionConfig(compaction_interval=5, overlap_size=1),
)
```

### Phase 4: Workflow Agents

```python
from google.adk.agents import SequentialAgent, ParallelAgent

marketing_pipeline = SequentialAgent(
    name="MarketingPipeline",
    sub_agents=[content_agent, marketing_agent],
    description="Creates content then plans campaign"
)
```

## Acceptance Criteria

1. ✅ Executive Agent uses `sub_agents` for native delegation
2. ✅ All tools have type hints, no defaults, and proper docstrings
3. ✅ App has production configurations enabled
4. ✅ At least one SequentialAgent workflow implemented
5. ✅ All existing tests pass + new tests for changes
6. ✅ >80% code coverage maintained

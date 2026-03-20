# Executive Agent Enhancement — Design Spec

**Date:** 2026-03-20
**Status:** Approved for planning
**Approach:** Instrumentation-First (Foundation -> User Impact -> Quick Wins)

## Constraints

- **ADK-only:** All routing/communication via ADK's native `before_model_callback`, `after_tool_callback`, and `sub_agents`. No custom orchestration layers.
- **Telemetry storage:** Structured JSON logs (Cloud Run/Cloud Logging) + Supabase tables for dashboards.
- **Cross-agent communication:** Context enrichment via callbacks (passive) + Executive-mediated handoff protocol (active).
- **Tool pruning:** Aggressive — Executive keeps ~40 coordination tools; domain tools pushed to specialists exclusively.

## ADK Callback Constraints & Workarounds

ADK provides `before_model_callback` and `after_tool_callback` but no `before_tool_callback`. This creates two design challenges:

1. **Tool duration tracking:** Cannot measure tool execution time directly. Workaround: wrap each tool function with a timing decorator that records start/end to `callback_context.state` before the tool body runs and after it returns. The `after_tool_callback` then reads the stored timing data.

2. **Sub-agent completion detection:** `after_tool_callback` fires after tool calls, not after sub-agent delegations. Sub-agent results flow back through the parent model turn. Workaround: in `before_model_callback`, inspect the most recent conversation history for sub-agent response content. If found, extract a summary and record it to `agent_recent_outputs` in session state.

3. **TelemetryService access from callbacks:** Callbacks are standalone functions, not methods. Solution: module-level singleton initialized lazily on first call, using the existing Supabase client pattern from `app/services/`.

## Phase Map

```
Phase 1: Foundation (Telemetry & Monitoring)
   |  Callbacks -> structured logs + Supabase tables
   |  Agent health tracking, tool usage metrics
   v
Phase 2: Agent Core (Tool Pruning & Routing)
   |  Executive: ~117 -> ~40 tools
   |  Routing transparency, delegation logging
   v
Phase 3: Cross-Agent Communication
   |  Context enrichment in before_model_callback
   |  Executive-mediated handoff protocol
   v
Phase 4: Workflow Enhancements (builds on existing)
   |  Fix parallel bug, add SLA tracking
   |  Enhance audit trail with step-level events
   v
Phase 5: Quick Wins Cascade
      Data-driven tuning from Phase 1 telemetry
      Error pattern -> instruction fixes
```

**Files touched per phase (minimal overlap):**

| Phase | Primary Files | New Files |
|-------|--------------|-----------|
| 1 | `context_extractor.py`, `shared.py` | `app/services/telemetry.py`, migration SQL |
| 2 | `agent.py`, `executive_instruction.txt` | None |
| 3 | `context_extractor.py`, `executive_instruction.txt` | None |
| 4 | `step_executor.py`, `worker.py`, `engine.py` | Migration SQL |
| 5 | Various instruction files | `get_system_health` tool |

---

## Phase 1: Foundation (Telemetry & Monitoring)

### 1.1 Telemetry Service (`app/services/telemetry.py`)

Lightweight async service that both callbacks funnel into:

```python
class TelemetryService:
    async def record_agent_event(self, event: AgentEvent) -> None:
        """Log + persist an agent delegation event."""

    async def record_tool_event(self, event: ToolEvent) -> None:
        """Log + persist a tool usage event."""

    async def get_agent_health(self, agent_name: str, window_hours: int = 24) -> AgentHealth:
        """Aggregate success rate, avg latency, error patterns."""

    async def get_tool_usage(self, window_hours: int = 24) -> list[ToolUsageSummary]:
        """Which tools are used, how often, by which agents."""
```

**Data models:**

```
AgentEvent:
  - agent_name, user_id, session_id
  - delegated_from (parent agent)
  - task_summary (first 200 chars of user message)
  - start_time, end_time, duration_ms
  - status (success | error | timeout)
  - error_message (if failed)
  - token_usage (input_tokens, output_tokens)

ToolEvent:
  - tool_name, agent_name, user_id, session_id
  - start_time, duration_ms
  - status (success | error)
  - error_type (if failed)
```

### 1.2 Callback Enhancements

**`before_model_callback`** (in `context_extractor.py`):
- Existing: loads context, extracts business facts, injects remembered context
- Add: Record `AgentEvent` start time, log which agent is about to run, capture task summary

**`after_tool_callback`** (in `context_extractor.py`):
- Existing: persists `_context_memory_save` flags
- Add: Record `ToolEvent` with duration, success/failure, error classification

Both emit structured JSON via Python `logging` (immediate) and batch-write to Supabase (async, non-blocking via `asyncio.create_task`).

### 1.3 Supabase Tables

```sql
CREATE TABLE agent_telemetry (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    agent_name TEXT NOT NULL,
    delegated_from TEXT,
    user_id UUID,
    session_id TEXT,
    task_summary TEXT,
    status TEXT NOT NULL,  -- success, error, timeout
    duration_ms INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE tool_telemetry (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tool_name TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    user_id UUID,
    session_id TEXT,
    status TEXT NOT NULL,
    duration_ms INTEGER,
    error_type TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_agent_telemetry_agent_created ON agent_telemetry(agent_name, created_at);
CREATE INDEX idx_tool_telemetry_tool_created ON tool_telemetry(tool_name, created_at);
CREATE INDEX idx_agent_telemetry_user ON agent_telemetry(user_id, created_at);
CREATE INDEX idx_agent_telemetry_errors ON agent_telemetry(status, created_at)
    WHERE status = 'error';  -- partial index for error-pattern queries
```

### 1.3.1 Data Retention

Telemetry tables grow rapidly. Apply a 90-day retention policy via scheduled cleanup:

```sql
-- Run weekly via cron or Supabase scheduled function
DELETE FROM agent_telemetry WHERE created_at < now() - interval '90 days';
DELETE FROM tool_telemetry WHERE created_at < now() - interval '90 days';
```

### 1.4 Structured Logging Format

```json
{
  "level": "INFO",
  "event": "agent_delegated",
  "agent": "FinancialAnalysisAgent",
  "delegated_from": "ExecutiveAgent",
  "user_id": "abc-123",
  "task_summary": "Show me Q1 revenue breakdown",
  "timestamp": "2026-03-19T14:30:00Z"
}
```

### 1.5 Circuit Breaker Integration

Telemetry writes use the existing Redis circuit breaker pattern from `app/services/cache.py`. If Supabase is slow/down, telemetry degrades to log-only. Agent responses are never blocked by telemetry failures.

**Key principle:** Telemetry is fire-and-forget. `asyncio.create_task` for DB writes; structured logs are synchronous but cheap.

---

## Phase 2: Agent Core (Tool Pruning & Routing)

### 2.1 Tool Pruning: ~117 -> ~40 tools

The Executive currently has approximately **117 tools** (after `sanitize_tools` dedup). The goal is to reduce to ~40 coordination-only tools.

**Executive keeps:**

| Category | Tools | Count |
|----------|-------|-------|
| Coordination | `create_task`, `update_initiative_status`, `send_notification` | ~5 |
| Knowledge | `search_business_knowledge`, `add_business_knowledge`, `add_company_info`, `add_product_info`, `add_process_or_policy`, `add_faq`, `list_knowledge` | ~7 |
| Context Memory | `save_user_context`, `get_conversation_context` | ~2 |
| Widgets | All `create_*_widget`, `display_workflow` | ~12 |
| Skills | `list_skills`, `use_skill`, `search_skills`, `create_custom_skill`, `list_user_skills` | ~5 |
| Research | `deep_research`, `quick_research`, `market_research`, `competitor_research` | ~4 |
| Config | `get_available_tools`, `get_tool_setup_guide`, `explain_tool_benefits`, `save_user_api_key`, `recommend_tools_for_goal` | ~5 |
| Workflows | `list_workflow_templates`, `start_workflow`, `approve_workflow_step`, `get_workflow_status`, `create_workflow_template` | ~5 |
| Briefing | `get_email_triage`, `get_daily_briefing`, etc. | ~5 |

**Executive loses (moved exclusively to specialists):**

| Domain | Example Tools | Goes To |
|--------|--------------|---------|
| Google Workspace | docs, sheets, forms, gmail, calendar | Relevant specialist per task |
| Media | `create_image`, `create_video_with_veo`, `create_social_graphic` | ContentCreationAgent |
| Landing Pages | `create_landing_page`, `publish_page`, forms | MarketingAutomationAgent |
| Payments | `create_payment_link`, `create_checkout`, subscriptions | Marketing or Sales |
| Canva | Canva media tools | ContentCreationAgent |
| Self-Improvement | `trigger_improvement_cycle`, eval tools | OperationsOptimizationAgent |
| API Connector | `connect_api`, `test_api_connection` | OperationsOptimizationAgent |

### 2.2 Implementation in `agent.py`

Change `_EXECUTIVE_TOOLS` list to only include coordination toolsets. Domain tools stay on specialist agents via `_get_domain_tools()`. No code deleted, just not included in Executive's list.

### 2.3 Routing Transparency

Emit routing log events in `before_model_callback` whenever a sub-agent is invoked:

```json
{
  "event": "agent_routing_decision",
  "selected_agent": "FinancialAnalysisAgent",
  "user_message_preview": "Show me Q1 cash flow forecast",
  "routing_signals": ["financial", "cash flow", "forecast"],
  "session_id": "xxx"
}
```

Logged + written to `agent_telemetry`. Routing signals are keyword-extracted from user message for post-hoc analysis.

### 2.4 Delegation Discipline Instruction

Add to `executive_instruction.txt`:

```
## DELEGATION DISCIPLINE
You are a coordinator, not a doer. Follow these rules strictly:
1. Never use domain tools directly -- you don't have them. Delegate.
2. Never attempt financial calculations -- delegate to FinancialAnalysisAgent.
3. Never draft content -- delegate to ContentCreationAgent.
4. Never create media -- delegate to ContentCreationAgent.
5. Cross-domain requests -- break into parts, delegate each to the right specialist.
6. Ambiguous requests -- ask the user one clarifying question, then delegate.
7. Status requests -- handle directly using skills (status_report_generation).
```

---

## Phase 3: Cross-Agent Communication

### 3.1 Context Enrichment via `before_model_callback` (Passive)

When a sub-agent is about to run, the callback checks session state for recent outputs from other agents and injects relevant context:

```python
CROSS_AGENT_CONTEXT_KEY = "agent_recent_outputs"
MAX_CROSS_AGENT_ENTRIES = 5
MAX_CONTEXT_AGE_TURNS = 10

def _build_cross_agent_context(callback_context) -> str:
    """Pull recent agent outputs from session state."""
    recent = callback_context.state.get(CROSS_AGENT_CONTEXT_KEY, [])
    if not recent:
        return ""
    relevant = [e for e in recent if e["turns_ago"] <= MAX_CONTEXT_AGE_TURNS]
    if not relevant:
        return ""
    lines = ["[CROSS-AGENT CONTEXT -- use this, do not re-ask the user]"]
    for entry in relevant[:MAX_CROSS_AGENT_ENTRIES]:
        lines.append(f"- {entry['agent']}: {entry['summary']}")
    lines.append("[END CROSS-AGENT CONTEXT]")
    return "\n".join(lines)
```

**Recording outputs** in `after_tool_callback`:

```python
def _record_agent_output(callback_context, agent_name: str, summary: str):
    recent = callback_context.state.get(CROSS_AGENT_CONTEXT_KEY, [])
    recent.insert(0, {
        "agent": agent_name,
        "summary": summary[:500],
        "turns_ago": 0,
    })
    for entry in recent[1:]:
        entry["turns_ago"] += 1
    callback_context.state[CROSS_AGENT_CONTEXT_KEY] = recent[:MAX_CROSS_AGENT_ENTRIES]
```

### 3.2 Executive-Mediated Handoff Protocol (Active)

Add to `executive_instruction.txt`:

```
## CROSS-AGENT HANDOFF PROTOCOL
When a specialist's response contains a handoff signal like:
  "This requires [Agent] to [action]"
You MUST:
1. Extract the requested action
2. Delegate to the named specialist with original context + requesting agent's output
3. Return the combined result to the user
```

Add to shared specialist instructions:

```
## REQUESTING CROSS-AGENT HELP
If your task requires expertise outside your domain, say so explicitly:
  "This requires [AgentName] to [specific action with context]"
The Executive will handle the delegation. Do NOT attempt work outside your domain.
```

### 3.3 Session State as Communication Bus

All cross-agent context flows through ADK's `callback_context.state`:

```
Session State Structure:
+-- agent_recent_outputs: [         # Cross-agent context (Phase 3)
|     {agent, summary, turns_ago},
|   ]
+-- user_context: {                 # Existing context memory
|     company_name, industry, ...
|   }
```

Decay: entries older than 10 turns dropped. Summary capped at 500 chars.

---

## Phase 4: Workflow Enhancements (Revised)

**Accounts for existing implementations.** Parallel steps and conditional branching already partially implemented. Focus on gaps.

### 4.1 Existing Implementation Status

| Feature | Status | Existing Code |
|---------|--------|--------------|
| Parallel Steps | Partial | `step_executor.py:432-489` (`execute_parallel_steps`, `asyncio.gather`) |
| Conditional Branching | Partial | `step_executor.py:61-109` (`evaluate_run_condition`, 7 operators + compound) |
| Audit Trail | Partial | Migration `0051`, `engine.py:1042-1084` |
| SLA Tracking | Missing | No evidence anywhere |

### 4.2 Fix: worker.py Parallel Field Mismatch

In `worker.py:311`, code reads `step_definition.get("parallel")` but YAML/DB field is `allow_parallel`.

```python
# Fix: align field name
step_def.get("allow_parallel", False)
```

### 4.3 Add: Parallel Group Dependencies

Add `requires` support for step ordering after parallel groups:

```python
def _check_requires(step_def: dict, completed_groups: set[str]) -> bool:
    requires = step_def.get("requires")
    if not requires:
        return True
    if isinstance(requires, str):
        requires = [requires]
    return all(g in completed_groups for g in requires)
```

Runtime-only logic, no new DB columns.

### 4.4 Implement: SLA Tracking (Full)

**Migration:**

```sql
ALTER TABLE workflow_executions
    ADD COLUMN sla_deadline TIMESTAMPTZ,
    ADD COLUMN sla_status TEXT DEFAULT 'on_track'
        CHECK (sla_status IN ('on_track', 'at_risk', 'breached'));

ALTER TABLE workflow_steps
    ADD COLUMN sla_hours NUMERIC,
    ADD COLUMN sla_deadline TIMESTAMPTZ,
    ADD COLUMN sla_status TEXT DEFAULT 'on_track'
        CHECK (sla_status IN ('on_track', 'at_risk', 'breached')),
    ADD COLUMN escalation TEXT DEFAULT 'notify'
        CHECK (escalation IN ('notify', 'block', 'auto_approve')),
    ADD COLUMN started_at TIMESTAMPTZ,
    ADD COLUMN completed_at TIMESTAMPTZ;
```

**Engine logic:**

```python
async def check_sla_status(step: dict) -> str:
    if not step.get("sla_deadline"):
        return "on_track"
    now = datetime.utcnow()
    deadline = step["sla_deadline"]
    if now > deadline:
        return "breached"
    elif now > deadline - timedelta(hours=2):
        return "at_risk"
    return "on_track"

async def handle_sla_breach(step: dict, execution_id: str):
    escalation = step.get("escalation", "notify")
    if escalation == "notify":
        await send_notification(...)
    elif escalation == "block":
        await pause_workflow_step(execution_id, step["name"])
    elif escalation == "auto_approve":
        await auto_approve_step(execution_id, step["name"])
```

**SLA clock pause/resume** (in `step_executor.py`): When a step enters `awaiting_approval`:
1. Calculate `remaining_ms = sla_deadline - now()` and store in step's metadata JSONB
2. Set `sla_deadline = NULL` (clock paused)
3. On approval: calculate new deadline = `now() + remaining_ms` and restore `sla_deadline`
4. On rejection: mark step as `rejected`, no SLA enforcement needed

### 4.5 Enhance: Audit Trail with Step-Level Events

**Migration:**

```sql
ALTER TABLE workflow_execution_audit
    ADD COLUMN step_name TEXT;

CREATE INDEX idx_audit_step ON workflow_execution_audit(execution_id, step_name, created_at);
```

**New action types:** `step_started`, `step_completed`, `step_skipped`, `sla_at_risk`, `sla_breached`, `condition_evaluated`, `parallel_group_dispatched`, `parallel_group_completed`.

Wire into existing `_audit_execution_action()` in `engine.py`.

---

## Phase 5: Quick Wins Cascade

Data-driven phase. Runs after Phases 1-4 are live and generating metrics.

### 5.1 Telemetry-Driven Tool Audit (Weekly)

```sql
SELECT tool_name, COUNT(*) as usage_count, AVG(duration_ms) as avg_duration
FROM tool_telemetry
WHERE agent_name = 'ExecutiveAgent'
  AND created_at > now() - interval '7 days'
GROUP BY tool_name ORDER BY usage_count DESC;
```

Domain tools still called by Executive after pruning = routing instruction gap. Fix by sharpening delegation guide.

### 5.2 Error Pattern -> Instruction Fix Pipeline

```sql
SELECT agent_name, error_message, COUNT(*) as frequency
FROM agent_telemetry
WHERE status = 'error' AND created_at > now() - interval '7 days'
GROUP BY agent_name, error_message ORDER BY frequency DESC LIMIT 20;
```

| Error Pattern | Fix |
|--------------|-----|
| "I don't have access to..." | Tool missing from agent's tool list |
| Re-asks answered question | Context memory callback not injecting |
| Generic/vague response | Instruction lacks domain specificity |
| Timeout on complex tasks | Add sub-steps or checkpoints |
| Cross-agent context lost | Session state writes failing |

### 5.3 Routing Quality Analysis

```sql
SELECT agent_name, COUNT(*) as delegations,
       AVG(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_rate
FROM agent_telemetry
WHERE delegated_from = 'ExecutiveAgent'
  AND created_at > now() - interval '7 days'
GROUP BY agent_name ORDER BY delegations DESC;
```

Low success rate = routing mismatch. Fix with negative examples in delegation guide or adjusted agent descriptions.

### 5.4 Token Efficiency Optimization

```sql
SELECT agent_name,
       AVG(input_tokens + output_tokens) as avg_total_tokens,
       MAX(input_tokens + output_tokens) as max_tokens
FROM agent_telemetry
WHERE created_at > now() - interval '7 days'
GROUP BY agent_name ORDER BY avg_total_tokens DESC;
```

High token agents -> trim instructions, reduce tool count, or split into focused sub-agents.

### 5.5 System Health Tool

New Executive tool:

```python
async def get_system_health() -> dict:
    """Get agent system health summary for the last 24 hours.
    Returns agent success rates, tool hotspots, error patterns,
    SLA compliance, and auto-generated recommendations.
    """
    return {
        "agent_health": [...],
        "tool_hotspots": [...],
        "error_patterns": [...],
        "sla_compliance": {...},
        "recommendations": [...],
    }
```

Enables "How's the system doing?" as a user query.

---

## Success Criteria

| Phase | Metric | Target |
|-------|--------|--------|
| 1 | Telemetry coverage | 100% of agent calls and tool invocations logged |
| 2 | Executive tool count | <= 50 tools (down from ~117) |
| 2 | Routing accuracy | >= 90% correct agent selection (measured by success rate) |
| 3 | Cross-agent context hits | >= 30% of multi-turn sessions use cross-agent context |
| 4 | SLA tracking | 100% of time-sensitive workflows have SLA deadlines |
| 4 | Audit coverage | Step-level events logged for all workflow executions |
| 5 | Error reduction | 50% reduction in top-5 recurring agent errors within 2 weeks |

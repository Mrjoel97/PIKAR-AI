# Autonomous Department Simulation — Design Specification

> **Status:** Approved
> **Date:** 2026-03-20
> **Scope:** Convert 10 stubbed department cycle methods into real autonomous decision-making loops with proactive triggers, cross-department orchestration, and safety guardrails.

---

## Executive Summary

The Pikar-AI system has the **orchestration foundation** for autonomous departments:
- Event-driven scheduling (heartbeat-based intervals via Cloud Scheduler)
- 10 specialized agents with domain tools
- Workflow engine with multi-step execution and approval gates
- Initiative tracking with operational state management
- Circuit breaker resilience on Redis cache

**What remains:** Converting the 10 stubbed `_run_<dept>_cycle()` methods into real autonomous decision-making logic that evaluates conditions, launches workflows, tracks progress, and feeds results back into state.

---

## Part 1: Current Architecture

### 1.1 Scheduling & Heartbeat

```
Cloud Scheduler → POST /scheduled/workflow-triggers/tick (hourly)
  → DepartmentRunner.tick()
    → For each RUNNING department:
        if (now - last_heartbeat) >= config.check_interval_mins:
            run_department_cycle(dept)
            update last_heartbeat
```

**Heartbeat intervals** (from seed migrations):

| Department | Interval | Rationale |
|-----------|----------|-----------|
| SUPPORT | 30 min | Customer-facing, fast response |
| SALES | 60 min | Pipeline monitoring |
| MARKETING | 60 min | Campaign pacing |
| DATA | 60 min | Metric freshness |
| OPERATIONS | 120 min | Process monitoring |
| CONTENT | 120 min | Publishing cadence |
| STRATEGIC | 240 min | Longer planning horizon |
| FINANCIAL | 360 min | Reporting cycles |
| HR | 1440 min | Low-frequency decisions |
| COMPLIANCE | 1440 min | Audit-based cadence |

### 1.2 Department State Model

```python
# departments table (Supabase)
{
    "id": UUID,
    "type": ENUM(SALES|MARKETING|CONTENT|STRATEGIC|DATA|FINANCIAL|SUPPORT|HR|COMPLIANCE|OPERATIONS),
    "status": ENUM(RUNNING|PAUSED|ERROR),
    "state": JSONB,        # Department-specific memory
    "config": JSONB,       # User settings: check_interval_mins, goals, etc.
    "last_heartbeat": TIMESTAMP
}
```

### 1.3 Current Cycle Methods (All Stubs)

```python
async def _run_sales_cycle(self, state, new_state) -> str:
    return f"Sales Agent active. Monitoring leads (No new actions)."
# ... same pattern for all 10 departments
```

---

## Part 2: Critical Gaps

### Gap 1: Proactive Trigger System
Departments have no way to define **when** to take action. Need a structured condition → action model with deduplication.

### Gap 2: Workflow Feedback Loop
When a workflow completes, there's no mechanism to update initiative state, remove from pending, or feed metrics back to the department.

### Gap 3: Decision Logging & Audit
No record of why departments took (or skipped) actions. Essential for trust, debugging, and compliance.

### Gap 4: KPI Evaluation Engine
Departments don't monitor metrics or detect anomalies to trigger escalations.

### Gap 5: Cross-Department Orchestration
Departments operate in isolation. No protocol for one department to request work from another.

### Gap 6: Goal-to-Task Decomposition
Departments have goals but can't autonomously decompose them into tasks and workflows.

### Gap 7: Missing Scheduled Endpoint
No `/scheduled/department-tick` endpoint for Cloud Scheduler.

### Gap 8: Guardrails & Safety
No spend limits, rate limits, or tiered approval requirements for autonomous actions.

---

## Part 3: Data Models

### 3.1 Proactive Triggers

```sql
CREATE TABLE proactive_triggers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department_id UUID NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,

    -- Condition
    condition_type TEXT NOT NULL CHECK (condition_type IN ('metric_threshold', 'initiative_phase', 'time_based', 'event_count')),
    condition_config JSONB NOT NULL,
    -- Example: {"metric_key": "open_deal_count", "operator": "lt", "threshold": 10, "lookback_days": 7}

    -- Action
    action_type TEXT NOT NULL CHECK (action_type IN ('launch_workflow', 'create_task', 'escalate', 'notify')),
    action_config JSONB NOT NULL,
    -- Example: {"workflow_template": "prospect_outreach_blitz", "context": {"outreach_count": 50}}

    -- Frequency control
    enabled BOOLEAN DEFAULT true,
    last_triggered_at TIMESTAMPTZ,
    cooldown_hours INT DEFAULT 24,
    max_triggers_per_day INT DEFAULT 3,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID REFERENCES auth.users(id)
);

CREATE INDEX idx_triggers_dept ON proactive_triggers(department_id) WHERE enabled = true;

ALTER TABLE proactive_triggers ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access" ON proactive_triggers FOR ALL USING (auth.role() = 'service_role');
```

### 3.2 Decision Logs

```sql
CREATE TABLE department_decision_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department_id UUID NOT NULL REFERENCES departments(id) ON DELETE CASCADE,

    cycle_timestamp TIMESTAMPTZ NOT NULL,
    decision_type TEXT NOT NULL CHECK (decision_type IN (
        'trigger_matched', 'trigger_skipped', 'workflow_launched', 'workflow_completed',
        'kpi_alert', 'escalated', 'inter_dept_request', 'no_action', 'error'
    )),
    decision_logic TEXT NOT NULL,  -- Human-readable explanation

    input_data JSONB,       -- Metrics, conditions at time of decision
    action_taken TEXT,
    action_details JSONB,   -- workflow_id, cost estimate, etc.
    outcome TEXT DEFAULT 'pending' CHECK (outcome IN ('success', 'pending', 'failed', 'skipped')),
    error_message TEXT,

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_decision_logs_recent ON department_decision_logs(department_id, cycle_timestamp DESC);

ALTER TABLE department_decision_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access" ON department_decision_logs FOR ALL USING (auth.role() = 'service_role');
```

### 3.3 Inter-Department Requests

```sql
CREATE TABLE inter_dept_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_department_id UUID NOT NULL REFERENCES departments(id),
    to_department_id UUID NOT NULL REFERENCES departments(id),

    request_type TEXT NOT NULL CHECK (request_type IN ('investigate', 'verify', 'review', 'execute')),
    context JSONB NOT NULL,
    priority INT DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),  -- 1=critical, 5=low
    deadline TIMESTAMPTZ,

    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'acknowledged', 'in_progress', 'completed', 'failed', 'expired')),
    assigned_workflow_id UUID,
    response_data JSONB,

    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_inter_dept_pending ON inter_dept_requests(to_department_id, status)
    WHERE status IN ('pending', 'in_progress');
```

---

## Part 4: Core Architecture

### 4.1 Cycle Method Template

Every department cycle follows this pattern:

```python
async def _run_<dept>_cycle(self, state: dict, new_state: dict) -> str:
    dept_id = state.get("dept_id")
    decisions = []

    # Phase 1: Handle incoming inter-department requests
    handled = await self._handle_inter_dept_requests(dept_id, new_state)
    decisions.extend(handled)

    # Phase 2: Evaluate proactive triggers
    triggered = await self._evaluate_triggers(dept_id, state, new_state)
    decisions.extend(triggered)

    # Phase 3: Monitor pending workflow completions
    completed = await self._check_workflow_completions(state, new_state)
    decisions.extend(completed)

    # Phase 4: Evaluate KPIs and escalate
    alerts = await self._evaluate_kpis(dept_id, state)
    decisions.extend(alerts)

    # Phase 5: Log all decisions
    for d in decisions:
        await self._log_decision(dept_id, d)

    # Phase 6: Update cycle metrics
    new_state["last_cycle_metrics"] = {
        "triggers_evaluated": len(triggered),
        "workflows_launched": sum(1 for d in decisions if d["decision_type"] == "workflow_launched"),
        "escalations": sum(1 for d in decisions if d["decision_type"] == "escalated"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return f"{dept_type} cycle: {len(decisions)} decisions"
```

### 4.2 Trigger Evaluation

```python
async def _evaluate_triggers(self, dept_id, state, new_state) -> list[dict]:
    triggers = await self._get_active_triggers(dept_id)
    decisions = []

    for trigger in triggers:
        # Cooldown check
        if trigger.get("last_triggered_at"):
            hours_since = (now - trigger["last_triggered_at"]).total_seconds() / 3600
            if hours_since < trigger.get("cooldown_hours", 24):
                continue

        # Evaluate condition
        matched, explanation = await self._evaluate_condition(trigger["condition_config"])

        if not matched:
            decisions.append({"decision_type": "trigger_skipped", "decision_logic": explanation})
            continue

        # Check rate limit
        if not self._under_rate_limit(dept_id, new_state):
            decisions.append({"decision_type": "trigger_skipped", "decision_logic": "Rate limit reached"})
            break

        # Execute action
        result = await self._execute_trigger_action(trigger, new_state)
        decisions.append(result)

    return decisions
```

### 4.3 Workflow Feedback Loop

```python
async def _check_workflow_completions(self, state, new_state) -> list[dict]:
    decisions = []
    pending = list(state.get("pending_workflows", []))
    still_pending = []

    for wf_id in pending:
        execution = await self._get_workflow_execution(wf_id)
        if not execution:
            continue

        if execution["status"] == "completed":
            # Update initiative with results
            if execution.get("initiative_id"):
                await self._update_initiative_from_workflow(execution)

            decisions.append({
                "decision_type": "workflow_completed",
                "decision_logic": f"Workflow '{execution['name']}' completed successfully",
                "action_details": {"workflow_id": wf_id, "output": execution.get("output_data")},
                "outcome": "success",
            })
        elif execution["status"] == "failed":
            decisions.append({
                "decision_type": "error",
                "decision_logic": f"Workflow '{execution['name']}' failed",
                "error_message": execution.get("error"),
                "outcome": "failed",
            })
        else:
            still_pending.append(wf_id)

    new_state["pending_workflows"] = still_pending
    return decisions
```

---

## Part 5: Safety & Guardrails

### 5.1 Tiered Approval Requirements

| Tier | Examples | Approvers | Timeout |
|------|---------|-----------|---------|
| **Tier 1: Critical** | Public statements, pricing changes, layoffs | CEO/CFO | 1h |
| **Tier 2: High Impact** | Contractor hires, spend > $5K, product changes | Department exec | 4h |
| **Tier 3: Standard** | Campaigns, content, customer outreach | Department lead | 24h |
| **Tier 4: Autonomous** | Reports, metric collection, status updates | None required | — |

### 5.2 Spend Limits

```python
AUTONOMOUS_SPEND_LIMITS = {
    "per_cycle": {"SALES": 500, "MARKETING": 1000, "SUPPORT": 0, "HR": 0},
    "per_day": {"SALES": 2000, "MARKETING": 5000},
}
```

### 5.3 Rate Limits

```python
MAX_WORKFLOWS_PER_CYCLE = {
    "SALES": 3, "MARKETING": 2, "SUPPORT": 5,
    "OPERATIONS": 2, "CONTENT": 2, "STRATEGIC": 1,
    "FINANCIAL": 1, "HR": 1, "COMPLIANCE": 1, "DATA": 3,
}
```

---

## Part 6: Implementation Phases

### Phase 1: Instrumentation & Safety (Foundation)
1. Database migrations: `proactive_triggers`, `department_decision_logs`, `inter_dept_requests`
2. Decision logging in all cycle methods (even "no action")
3. Scheduled endpoint: `POST /scheduled/department-tick`
4. Guardrails: spend limits, rate limits, tiered approvals
5. Department activity dashboard widget

### Phase 2: Core Autonomy (SALES + SUPPORT pilots)
1. ProactiveTrigger evaluation engine
2. Workflow feedback loop (completion → initiative update)
3. KPI evaluation with escalation
4. SALES pilot: 2 triggers (pipeline low, deal stuck)
5. SUPPORT pilot: 2 triggers (ticket surge, SLA breach)

### Phase 3: Cross-Department Orchestration
1. Inter-department request protocol
2. Request handling in cycle methods
3. Escalation logic (missed deadlines → Executive Agent)
4. 3 cross-dept scenarios: SALES→OPS, FINANCIAL→STRATEGIC, SUPPORT→DATA

### Phase 4: Goal Decomposition & Observability
1. Goal-to-task decomposition engine
2. Goal progress tracking per initiative
3. Trust scoring (department success rate → autonomy level)
4. Explainability: "Why was this action taken?" UI
5. Rollback mechanism: undo autonomous action within 24h

---

## Part 7: Success Metrics

| Metric | Target |
|--------|--------|
| Decision log coverage | 100% of autonomous actions logged |
| Tier-1 workflow approval rate | 100% require approval (zero unauthorized) |
| Workflow success rate | > 85% |
| Initiative progress tracking | 100% (no stale initiatives) |
| Mean time to escalation | < 2 cycles for critical KPI violations |
| User trust survey | > 80% confidence in autonomous decisions |

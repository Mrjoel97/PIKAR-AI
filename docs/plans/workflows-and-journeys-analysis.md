# Workflows and User Journeys – Current Setup and E2E Analysis

## 1. Executive summary

**Linkage:** All four personas (solopreneur, startup, SME, enterprise) have **100% of user journeys linked** to workflow templates: every journey has `primary_workflow_template_name`, `outcomes_prompt`, and all referenced template names exist in `workflow_templates`. Agents and users can start journey workflows from initiatives.

**E2E flow:** Journey → initiative → outcomes → `start_journey_workflow` → workflow engine → edge function → backend execute-step → tool registry. The pipeline is wired end-to-end, but **step execution is unreliable** because context is passed as `**kwargs` to tools that expect fixed arguments (e.g. `create_initiative(title, description, priority)`), causing TypeErrors and fallback to placeholder/no-op behavior. **Outcomes** are step-level `output_data` and completion status; there is no consolidated “workflow outcome” artifact for the user.

**Recommendations:** Add context-to-parameter mapping for workflow-invoked tools (or workflow-specific tool wrappers), ensure initiative context (`initiative_id`, `desired_outcomes`, `topic`) is used by steps that need it, and optionally add a post-workflow summary or “outcome” view for users.

---

## 2. Current setup

### 2.1 Journey–workflow linkage (by persona)

| Persona      | Total journeys | With primary_workflow_template_name | With outcomes_prompt |
|-------------|----------------|-------------------------------------|------------------------|
| enterprise  | 40             | 40                                  | 40                     |
| sme         | 40             | 40                                  | 40                     |
| solopreneur | 40             | 40                                  | 40                     |
| startup     | 40             | 40                                  | 40                     |

- **Source:** `user_journeys` (migration seeds + enrichment migrations 0041–0044).
- Every journey has a primary template; all primary template names exist in `workflow_templates` (verified by name lookup).
- Suggested workflows (`suggested_workflows` JSONB) are optional and not used by `start_journey_workflow` (only primary is used).

### 2.2 How agents and users run workflows

- **From initiative (journey-sourced):**
  - User: Initiative detail → “Run journey workflow” → `POST /initiatives/:id/start-journey-workflow` → `start_journey_workflow(initiative_id)`.
  - Agent: After collecting outcomes, calls `update_initiative(..., desired_outcomes=..., timeline=...)` then `start_journey_workflow(initiative_id)`.
- **Context passed into the workflow:** `initiative_id`, `desired_outcomes`, `timeline`, `topic` (from initiative + journey), plus execution metadata.
- **Direct start (no journey):** User/agent can call `POST /workflows/start` with `template_name` and `topic`; same engine and execution path, with simpler context.

### 2.3 Workflow template structure

- **Tables:** `workflow_templates` (name, description, category, **phases** JSONB), `workflow_executions` (user_id, template_id, status, context, current_phase_index, current_step_index), `workflow_steps` (execution_id, phase_name, step_name, status, input_data, output_data).
- **Phases:** Each phase has `name`, `phase_key`, and `steps[]`. Each step has `name`, `tool`, `description`, `required_approval`.
- **Tool field:** Step execution uses `step.tool` (e.g. `create_initiative`, `mcp_web_search`). All such names referenced in templates exist in the app **tool registry** (`app/agents/tools/registry.py`); unknown tools get a placeholder that “auto-completes” the step without doing real work.
- **Sample templates:** Initiative Framework (5 phases, many steps with tools), Strategic Planning Cycle (3 phases, fewer steps). Templates have at least a few steps with a non-empty `tool` field.

---

## 3. End-to-end execution path

1. **Start:** `start_journey_workflow(initiative_id)` or `POST /workflows/start` → `WorkflowEngine.start_workflow(user_id, template_name, context)`.
2. **Engine:** Loads template, creates `workflow_executions` row, creates first `workflow_steps` row, calls edge function `execute-workflow` with `action=start`.
3. **Edge function (`execute-workflow`):** If first step does not require approval, calls `executeStep()` which:
   - POSTs to `BACKEND_API_URL/workflows/execute-step` with `execution_id`, `step_id`, `tool_name`, `context` (includes initiative_id, desired_outcomes, timeline, topic), `step_name`, `step_description`.
   - If backend is unreachable or not set, uses local fallback that returns a generic “step completed” message.
4. **Backend (`POST /workflows/execute-step`):** `get_tool(tool_name)` then `await tool_fn(**tool_context)`. `tool_context` = `{ execution_id, step_id, step_name, description, **context }`.
5. **Tool execution:** Most tools have **fixed signatures** (e.g. `create_initiative(title, description, priority)`). Passing `**tool_context` with keys like `initiative_id`, `desired_outcomes`, `topic` causes **TypeError** (unexpected keyword arguments). The route catches the exception and returns `success: False` with a message; the edge function may still mark the step as completed with that message, so the step “completes” but **no real tool work** is done.
6. **Advancement:** After step completion, edge function advances to next step (or marks execution completed). Approval steps wait for `approve_workflow_step` (agent or user) then advance.
7. **User visibility:** Dashboard → Active Workflows lists executions; user can open an execution and see step timeline and approve steps. Initiative detail shows `workflow_execution_id` when a workflow was started from that initiative.

---

## 4. Gaps affecting reliability and outcomes

### 4.1 Context vs. tool parameters

- **Issue:** Execute-step passes a single flat `tool_context` (execution_id, step_id, step_name, description, initiative_id, desired_outcomes, timeline, topic, etc.) as `**kwargs` to every tool. Most tools expect specific positional/keyword args (e.g. `create_initiative(title, description, priority)`; `get_initiative(initiative_id)`).
- **Effect:** Steps that should create/update initiatives, look up initiatives, or use `initiative_id`/`desired_outcomes` often raise TypeError and “complete” with an error message instead of performing the intended action. Workflows can run to completion without producing the intended side effects (e.g. no initiative created, no content saved with the right context).
- **Fix direction:** Per-tool or per-step mapping from `context` to the tool’s actual parameters (e.g. for “Create Initiative Record” when `initiative_id` is already in context, call `get_initiative(initiative_id)` or skip; when starting from topic only, call `create_initiative(title=topic, description=...)`). Alternatively, workflow-specific tool wrappers that accept `(context: dict)` and map to the underlying tool.

### 4.2 Placeholder and fallback behavior

- **Issue:** Unknown tool names return a placeholder that always “succeeds.” When the backend is unreachable, the edge function uses a local fallback that returns a generic “step completed” message. No distinction between “real execution” and “simulated.”
- **Effect:** Workflows can appear to complete successfully while no real work is done; outcomes are not impactful or reliable.
- **Fix direction:** Ensure only registered, callable tools are used in templates; add a clear “simulated” or “fallback” flag in step output so UI/analytics can distinguish; and fix backend URL/config so execute-step is consistently called.

### 4.3 Initiative context in steps

- **Issue:** Even when `initiative_id` and `desired_outcomes` are in context, tools that need them (e.g. `update_initiative`, `get_initiative`, `create_task` for that initiative) are not given them in the right shape; they are buried in kwargs and often unused.
- **Effect:** Journey-driven workflows do not reliably “attach” work to the initiative or use the user’s stated outcomes.
- **Fix direction:** In execute-step (or in wrappers), when `initiative_id` is present, pass it explicitly to tools that accept it; when `desired_outcomes`/`timeline` are present, pass them into `update_initiative` or into steps that generate content/plans so outputs align with stated outcomes.

### 4.4 Outcome visibility and usefulness

- **Issue:** “Outcomes” are currently (a) step-level `output_data` and (b) execution status (completed/failed). There is no aggregated “workflow outcome” (e.g. “Created initiative X, added 5 tasks, saved 2 content items”) or guidance for the user on what to do next.
- **Effect:** Users may not see a clear, practical summary of what the workflow achieved or what to do next; impact feels low.
- **Fix direction:** Optional post-completion step or job that summarizes step results (e.g. “Created: initiative, 3 tasks; Updated: initiative with timeline”) and stores or displays it; or a simple “Workflow outcome” section on the initiative detail that shows the last execution’s step summary and key artifacts (initiative, tasks, content).

---

## 5. What works today

- **Linkage:** All personas have journeys fully linked to workflows; agents and users can start the correct template from an initiative.
- **Execution pipeline:** Start → engine → edge function → advance loop and approval gates work; steps are created and updated; executions move to “completed” when all steps are done.
- **UI:** Active Workflows page and initiative detail show workflow status and allow approval; realtime subscription can refresh execution/step state.
- **Tool registry:** Broad set of tools (strategic, marketing, HR, content, research, etc.); templates reference these names; placeholder prevents hard failures for unknown tools.
- **Initiative Framework (and similar) design:** Phases and steps are sensible (ideation → validation → prototype → build → scale); with correct argument mapping, the same flow would produce real, useful outcomes.

---

## 6. Recommendations (priority order)

1. **Context-to-parameter mapping for workflow steps (high)**  
   In `app/routers/workflows.py` execute-step handler (or a dedicated workflow-tool layer), map `context` to the expected parameters for the invoked tool (e.g. from `topic`/`desired_outcomes` to `title`/`description` for `create_initiative`; from `initiative_id` to `get_initiative`/`update_initiative`). Optionally support a small step-level “param_mapping” in template definitions (e.g. `title: topic`, `description: desired_outcomes`).

2. **Ensure initiative context is used (high)**  
   When `initiative_id` is in context, pass it explicitly to `get_initiative`, `update_initiative`, `create_task`, and any other tool that supports it. When `desired_outcomes`/`timeline` are present, use them in update_initiative and in steps that generate deliverables so outputs match user goals.

3. **Reliable backend execution (medium)**  
   Ensure `BACKEND_API_URL` is set in the edge function environment so execute-step is always called when a real tool is needed; reduce reliance on “edge fallback” for steps that should run real tools.

4. **Workflow outcome summary (medium)**  
   Add an optional “outcome summary” when an execution completes (e.g. list of created/updated entities and key step results) and expose it on the initiative detail or Active Workflows detail so users see a clear, practical outcome.

5. **Template and tool alignment (low)**  
   Audit templates for tool names that are not in the registry or that are known to need special mapping; add wrappers or mappings so every step either runs a real tool with correct args or is explicitly marked as manual/skip.

---

## 7. Files and areas to touch

| Area | Files / locations |
|------|-------------------|
| Context → tool args | `app/routers/workflows.py` (execute-step), or new `app/workflows/step_executor.py` with mapping logic |
| Initiative context | Same as above; ensure `initiative_id`, `desired_outcomes`, `timeline` passed to strategic/content/task tools |
| Edge function | `supabase/functions/execute-workflow/index.ts` – ensure BACKEND_API_URL and error handling leave step “failed” when backend returns failure |
| Outcome summary | Backend: optional summary on execution complete. Frontend: initiative detail and/or Active Workflows detail |
| Tool registry | `app/agents/tools/registry.py` – add workflow-safe wrappers if needed (e.g. `create_initiative_from_workflow_context(context)` that reads topic/desired_outcomes) |

---

## 8. Summary table

| Aspect | Status | Notes |
|--------|--------|--------|
| Journeys linked to workflows (all personas) | ✅ | 160/160 journeys have primary template and outcomes_prompt |
| Agents can start journey workflow | ✅ | start_journey_workflow(initiative_id) + update_initiative for outcomes |
| Users can start from UI | ✅ | “Run journey workflow” and “Discuss with Agent” |
| Execution pipeline (engine → edge → backend) | ✅ | Wired; advance and approval work |
| Step execution with correct tool args | ❌ | **kwargs vs fixed signatures cause TypeErrors; steps often no-op or placeholder |
| Initiative/outcomes used in steps | ❌ | Context present but not mapped into tool parameters |
| Reliable, impactful outcomes | ⚠️ | Only if tools run with correct args; currently partial/fragile |
| Clear outcome visibility for user | ⚠️ | Step-level only; no consolidated “workflow outcome” |

Fixing **context-to-parameter mapping** and **use of initiative context** in steps will make workflows reliably produce useful, practical outcomes; adding an **outcome summary** will make them clearly visible and actionable for users.

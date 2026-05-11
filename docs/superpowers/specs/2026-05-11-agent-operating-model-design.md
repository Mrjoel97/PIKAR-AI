# Agent Operating Model — Design

**Date:** 2026-05-11
**Status:** Draft, pending user approval
**Companion project:** Documents subsystem (separate spec to follow)

---

## 1. Purpose

Every Pikar agent (Executive + the 10 specialized agents + admin/research/reporting) must:

1. **Be filed identically** — a uniform four-pillar structure on disk so agents are easy to manage and improve.
2. **Operate with discipline at runtime** — a single `BaseAgent` enforces skill consultation, research completion, audits, approvals, handoffs, compaction, and initiative-lifecycle rituals through ADK lifecycle hooks.
3. **Surface their work consistently** — every artifact flows through one publication primitive into the operational history table, the knowledge vault, the reports UI, and the workspace canvas. No agent is invisible.
4. **Route smart between simple and complex work** — short factual asks execute directly; multi-step work runs through the full initiative ritual. The classifier is correctable.
5. **Respect persona policy** — tool allow-lists, action thresholds, and prompt fragments enforced through the same hooks as everything else.

This spec covers all five. A separate spec covers the Documents subsystem.

---

## 2. Background

### What exists today

- `app/agents/<domain>/` already partly uniform: every domain has `__init__.py`, `agent.py`, `tools.py`. `strategic/` has extras (`debate.py`, `subagents.py`).
- `app/agents/base_agent.py` is a thin `PikarAgent(Agent)` subclass with no enforcement logic.
- `app/agents/tools/` holds ~50 shared tool modules — central, not per-agent.
- Skills infrastructure is built: `app/skills/registry.py`, `skill_embeddings.py`, `skill_hydration.py`, `agent_skills.py`. Consulting skills is currently optional.
- Memory is thin: `app/services/agent_memory.py` holds a per-`(user_id, agent_name)` JSONB facts blob.
- Initiatives have substantial machinery: `routers/initiatives.py`, `services/initiative_service.py`, `services/initiative_operational_state.py`, `workflows/initiative_orchestrator.py`. A 2026-04-28 audit identified 9 gaps.
- Reports and vault exist (`routers/reports.py`, `routers/vault.py`, dashboard pages). Vault is shipped but the embedding/retrieval pipeline for agent outputs is not wired.
- Workspace canvas exists at `frontend/.../dashboard/workspace` + `frontend/.../api/workspace`. Backend emits **zero** events to it (grep confirms). Video director and graphic agents in particular ship to `videos`/storage tables but the workspace UI never finds out.
- Persona policy substrate exists: `app/personas/policy_registry.py` + `prompt_fragments.build_persona_policy_block`. Today it's prompt-fragment enforcement only — runtime gates are missing or ad-hoc.

### Failure modes the design addresses

- Agents skip skill consultation entirely.
- Agents start research and pattern-match into execution before research completes.
- Agents close initiative phases without auditing exit criteria.
- Agents complete tasks without producing a structured report.
- Director and graphic outputs never surface in the workspace.
- Persona policies that say "this user cannot approve over $X" are enforced inconsistently.
- Every interaction gets the heavy initiative treatment, including "what's our Q3 revenue?".

---

## 3. Approach

**Approach A (selected):** Base-class enforcement + per-agent config files.

`PikarBaseAgent` extends the existing `PikarAgent` and wires every ADK callback. Per-agent values live in a declarative `operations.yaml`. Engineers own rule *logic*; non-engineers (and the admin panel later) can tune *values*. Builds on existing primitives (`skills_registry`, `handoff_packet`, `initiative_service`, `agent_memory`, `policy_registry`) rather than replacing them.

**Rejected:**
- *Approach B — Workflow-driven:* explicit ADK Workflows for every ritual. Larger rewrite, fights conversational use, partially duplicates existing `app/workflows/`.
- *Approach C — Declarative-runtime:* every rule is data. Maximum flexibility, but the runtime becomes complex and ambiguous behaviors are easy to introduce.

---

## 4. Per-agent file structure

```
app/agents/<domain>/
├── __init__.py            # re-exports the factory
├── agent.py               # ~30 lines: imports BaseAgent + config, returns the agent
├── instructions.md        # the persona/role prompt (markdown, plain text)
├── tools.py               # imports from app/agents/tools/, declares the tool manifest
└── operations.yaml        # per-agent tunable values
```

Shared:

```
app/agents/
├── base_agent.py          # PikarAgent → PikarBaseAgent (carries the hooks)
├── runtime/               # NEW
│   ├── __init__.py
│   ├── lifecycle.py       # all four ADK callbacks
│   ├── skill_injection.py # semantic match + auto-inject
│   ├── research_gate.py   # research-completion enforcement
│   ├── step_runtime.py    # execute_task / execute_initiative_step
│   ├── audit.py           # self-audit primitives
│   ├── handoff.py         # standardized handoff
│   ├── compaction.py      # session compaction trigger
│   ├── memory_retrieval.py # Layer-3 retrieval from vault
│   ├── publication.py     # publication sinks (DB, vault, reports, workspace)
│   ├── persona_gate.py    # persona policy enforcement
│   ├── task_router.py     # direct vs. initiative mode classifier
│   ├── initiative.py      # start / advance / close rituals
│   └── operations_config.py # operations.yaml load + Pydantic validation
├── handoff_packet.py      # existing
├── shared.py              # existing model config etc.
└── shared_instructions.py # folded into runtime/skill_injection.py over time
```

Each domain folder keeps the agent's identity in four files. The runtime is shared.

---

## 5. `PikarBaseAgent` architecture

```python
class PikarBaseAgent(PikarAgent):
    def __init__(
        self,
        *,
        agent_id: AgentID,
        instructions_path: Path,
        tools_manifest: ToolsManifest,
        ops_config: OperationsConfig,
        user_id: UUID,
        persona_id: str,
        ...
    ):
        super().__init__(
            name=agent_id.value,
            instruction=self._build_instruction(instructions_path, persona_id),
            tools=tools_manifest.resolve(),  # tool names → callables
            before_agent_callback=lifecycle.before_agent(self),
            before_tool_callback=lifecycle.before_tool(self),
            after_tool_callback=lifecycle.after_tool(self),
            after_agent_callback=lifecycle.after_agent(self),
            ...
        )
        self.ops = ops_config
        self.agent_id = agent_id
        self.user_id = user_id
        self.persona_id = persona_id

    async def respond_directly(self, request: DirectRequest) -> Response: ...
    async def execute_task(self, contract: TaskContract) -> TaskResult: ...
    async def start_initiative(self, *, goal, success_criteria, owners, ...) -> Initiative: ...
    async def advance_phase(self, initiative_id, current_phase) -> AdvanceResult: ...
    async def close_initiative(self, initiative_id) -> CloseReport: ...
```

### Callback responsibilities

| Callback | Responsibilities |
|---|---|
| `before_agent_callback` | (1) Run task router (§ 9). (2) Semantic-match skills, inject summaries. (3) Retrieve relevant past reports from vault, inject summaries. (4) Apply persona prompt fragments. (5) Load initiative context if session is bound to one. (6) Fail-fast if required `ops_config` values are missing. |
| `before_tool_callback` | Gate stack, in order: (a) persona allow-list / deny-list, (b) persona action thresholds → approval, (c) research-gate (block non-research tools while gate open), (d) approval token check for above-threshold actions. Each block writes to the audit report. |
| `after_tool_callback` | Capture structured outputs, close research gate when complete, log tool failures for retry, emit progress events to workspace SSE channel. |
| `after_agent_callback` | Run self-audit if the turn produced an artifact (initiative mode always; direct mode only if artifact created); trigger compaction when token count > `ops.compaction.trigger_token_count`; persist outcome to `agent_task_executions`. |

---

## 6. `TaskContract` and execution runtime (initiative mode)

```python
@dataclass
class TaskContract:
    id: UUID
    source: Literal["initiative_step", "department_task"]
    goal: str
    todo_items: list[TodoItem]
    success_criteria: list[str]
    owners: list[AgentID]
    evidence_required: list[str]      # "research_summary", "draft_artifact", "audit_report"
    initiative_id: UUID | None
    initiative_phase: str | None
    sibling_steps: list[StepSummary]  # full plan visibility — read-only
```

Two adapters in `runtime/step_runtime.py`:
- `contract_from_initiative_step(checklist_item_id)` — reads `initiative_checklist_items`, hydrates `sibling_steps` from the same `(initiative_id, phase)` set.
- `contract_from_department_task(task_id)` — reads `department_tasks` + a new `department_task_todo_items` table.

Direct mode does **not** use `TaskContract`; it uses a lightweight `DirectRequest` (§ 9). When `agent_task_executions` records a direct turn, `contract_source = 'direct_request'` and the `contract_id` column is null.

### The loop

```python
async def execute_task(self, contract: TaskContract) -> TaskResult:
    self._load_initiative_context(contract)
    research = await self._run_research_to_completion(contract)
    artifacts = await self._execute_todo_items(contract, research)
    audit = await self._self_audit(contract, artifacts)
    if not audit.passes:
        if audit.recoverable:
            return await self._retry_failed_items(contract, audit)
        return await self._escalate(contract, audit)
    return await self._submit(contract, artifacts, research, audit)
```

Todo items are executed one at a time; status updates (`pending → in_progress → completed`) flow to the underlying table as the agent works. Sibling steps are visible; modifying them requires a separate `propose_plan_change` tool routed through the initiative owner.

---

## 7. Research-completion gate

New module `runtime/research_gate.py` and a new table:

```sql
CREATE TABLE agent_research_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_contract_id UUID NOT NULL,
  task_contract_source TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  query TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('open','in_progress','complete','failed')),
  result JSONB,
  iterations INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);
```

Result schema (Pydantic, validated):

```python
class ResearchResult(BaseModel):
    summary: str                       # 200-400 words
    sources: list[Source]              # url, title, key_claim, retrieved_at
    contradictions: list[str]
    coverage_assessment: Literal["complete", "partial"]
    missing_information: list[str]
```

Flow:
1. `execute_task` opens a research run (`status='open'`) tied to the contract.
2. `before_tool_callback` allows research tools (`deep_research`, `tavily_search`, `firecrawl_scrape`, `google_search`); blocks all others with `ResearchGateError`.
3. `after_tool_callback` accumulates results, runs a coverage check against `success_criteria`.
4. If `coverage_assessment == "complete"`, persist structured result, set `status='complete'`, close gate. If `partial` and `iterations < ops.research.max_iterations`, auto-issue refined query and loop. Otherwise surface a forced-completion warning.
5. Only `status='complete'` unblocks `_execute_todo_items`.

This is enforcement, not prompt advice. The model cannot pattern-match into execution because the framework refuses non-research tool calls until the gate closes.

---

## 8. Self-audit against goal + to-do list

```python
async def audit_against_contract(
    contract: TaskContract,
    artifacts: list[Artifact],
    research: ResearchResult,
) -> AuditReport: ...
```

The audit is a deterministic LLM call (low temperature) that walks each `todo_item` and each `success_criterion` against the produced artifacts:

```python
class AuditReport(BaseModel):
    overall_status: Literal["pass", "fail", "partial"]
    per_item: list[ItemAudit]            # item_id, status, evidence_pointers, gaps
    per_criterion: list[CriterionAudit]  # criterion, met, justification
    gaps: list[str]
    policy_violations: list[PolicyViolation]  # populated by persona/approval gates
    recoverable: bool
    next_action: Literal["submit", "retry", "escalate"]
```

The report persists to a new `agent_audit_reports` table and a summary attaches to the checklist item's `evidence` JSONB. Submission is blocked unless `overall_status == "pass"`.

Because the contract carries both the to-do list and the success criteria, the audit prompt hands the model the exact rubric — it never asks the model to remember what good looks like.

---

## 9. Execution mode routing (direct vs. initiative)

Not every request needs the full ritual. Two execution modes:

| | **Direct mode** | **Initiative mode** |
|---|---|---|
| **Used for** | "what's our Q3 revenue", "send the follow-up", "summarize this doc" | "plan the launch", "produce Q3 forecast", anything multi-step |
| **Contract** | None — or lightweight `DirectRequest` | Full `TaskContract` |
| **Research gate** | Off | On |
| **Self-audit** | Off — or conversational check | Full audit, persisted |
| **Initiative wiring** | None | Phase advancement, handoff to phase history |
| **Vault report** | Only if turn produced a real artifact | Always |
| **`agent_task_executions` row** | Only if stateful (tool called / artifact produced) | Always |

### Preserved for both modes

Skill injection, memory retrieval, HITL approval gate (driven by action risk, not task complexity), error/retry, auto-compaction.

### Classifier — `runtime/task_router.py`

Three signals, first conclusive answer wins:

1. **Explicit override:** `/quick` or `/plan` prefix; UI toggle on the chat composer; persona's `classifier_default_mode`.
2. **Rule heuristics:** existing TaskContract on session → initiative; message starts with `what|when|who|where|show|list|find|look up|summarize` and < 80 chars → direct; verbs `plan|build|launch|develop|orchestrate|migrate|run a campaign` → initiative; `@agent` handoff or initiative ID present → initiative.
3. **LLM classifier fallback** — single Gemini Flash call when (1) and (2) inconclusive. Returns `{mode, confidence, reasoning}`, logged for tuning.

### Escape hatches

- `escalate_to_initiative(reason, goal, success_criteria)` — agent tool, mid-turn, promotes a direct conversation to an initiative.
- Initiative → direct is not allowed: once a TaskContract is open it must close via audit or escalation.

---

## 10. Skill discipline

Two enforcement vectors, both backed by the existing `app/skills/` infrastructure:

1. **Automatic injection** via `before_agent_callback`:
   - Embed the user task with `skill_embeddings`.
   - Top-K by cosine similarity, filtered by `agent_id ∈ skill.agent_ids` and `ops.skills.allowed_ids`.
   - Inject skill summaries into the prompt under a `Relevant skills` section.
   - K defaults to `ops.skills.injection.top_k = 5`; floor at `ops.skills.injection.similarity_floor = 0.65`.
2. **`consult_applicable_skills(task)` tool** — reuses the same matcher; callable mid-turn when scope shifts.

No new infrastructure for matching — `skill_embeddings.py` already exists. Per-agent permissions already enforced by `skills_registry`.

---

## 11. Memory persistence — four layers

| Layer | What | Lifetime | Where |
|---|---|---|---|
| **0 — Preference facts** *(exists)* | Stable per-`(user, agent)` preferences | Forever | `agent_memory` JSONB |
| **1 — Operational history** | Every TaskContract execution | 18 months default | `agent_task_executions`, `agent_research_runs`, `agent_audit_reports` |
| **2 — Vault-indexed reports** | Structured markdown report per submission | Forever | `knowledge_service.add_document` |
| **3 — Retrieval at task start** | Semantic match against past reports, injected at start | Runtime | `runtime/memory_retrieval.py` |

### Layer 1 — operational history

```sql
CREATE TABLE agent_task_executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  agent_id TEXT NOT NULL,
  persona_id TEXT,
  mode TEXT NOT NULL DEFAULT 'initiative'
    CHECK (mode IN ('direct', 'initiative')),
  classifier_signal TEXT,                       -- 'override' | 'rule' | 'llm'
  contract_id UUID,                              -- null for direct mode
  contract_source TEXT,                          -- 'initiative_step' | 'department_task' | 'direct_request'
  initiative_id UUID,
  goal TEXT,                                     -- nullable for direct mode
  todo_snapshot JSONB,                           -- nullable for direct mode
  status TEXT NOT NULL CHECK (status IN ('running','submitted','escalated','failed')),
  research_run_id UUID REFERENCES agent_research_runs(id),
  audit_report_id UUID REFERENCES agent_audit_reports(id),
  vault_document_id UUID,
  artifacts JSONB NOT NULL DEFAULT '[]',
  outcome_summary TEXT,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_ate_user_agent ON agent_task_executions(user_id, agent_id, started_at DESC);
CREATE INDEX idx_ate_initiative ON agent_task_executions(initiative_id, started_at DESC);
CREATE INDEX idx_ate_goal_trgm ON agent_task_executions USING gin (goal gin_trgm_ops);
```

### Layer 2 — report template

```
# {Agent} — {Goal}
**Initiative:** {name} · **Phase:** {phase} · **Date:** {ISO}
**Owner:** {agent_id} · **Task:** `{contract_id}` · **Persona:** {persona_id}

## Goal
{contract.goal}

## To-Do Outcomes
| Item | Status | Evidence |

## Success Criteria
{per criterion with audit pass/fail}

## Research Summary
{research.summary}

### Sources ({n})
### Contradictions Flagged

## Artifacts
{links to vault docs / generated files / drafts}

## Audit Report
{overall_status — gaps, if any}

## Policy Notes
{any persona-policy violations or approvals captured}

## Follow-ups
{open items, handoffs created}
```

Vault metadata: `{kind: "agent_report", agent_id, initiative_id, contract_id, goal, persona_id}`.

### Layer 3 — retrieval at task start

`runtime/memory_retrieval.py` runs alongside skill injection inside `before_agent_callback`. Semantic-matches `contract.goal` (or the direct request text) against vault docs where `kind='agent_report'`, filters by `agent_id`, recency, same `initiative_id`. Returns top-K (default 4) summaries. Injected as a `Prior work` section in the prompt.

---

## 12. Publication sinks — single primitive, multiple sinks

`runtime/publication.py` is the only place outputs leave the agent:

```python
async def publish_artifact(
    *,
    user_id: UUID,
    agent_id: AgentID,
    contract: TaskContract | DirectRequest,
    artifact: Artifact,                # {kind, ref, summary, payload}
    audit: AuditReport | None,
) -> PublicationResult:
    # 1. write/update agent_task_executions.artifacts
    # 2. for vault-bound kinds → knowledge_service.add_document(...)
    # 3. for every artifact → emit WorkspaceArtifactEvent on user's SSE channel
    # 4. submit kinds become reports-UI-visible via agent_task_executions join
```

### Sinks

| Sink | Subscribes via | Surface |
|---|---|---|
| `agent_task_executions` (DB) | Direct query | Source of truth, history |
| Knowledge Vault | `knowledge_service.add_document` | Long-term retrieval, Layer-3 memory |
| Reports UI | Reads `agent_task_executions` joined to vault docs | New endpoint in `routers/reports.py` |
| Workspace canvas | SSE channel `workspace/{user_id}/events` | `ActiveWorkspace` subscribes; renders previews inline |

### Workspace event shapes

```python
class WorkspaceProgressEvent(BaseModel):
    kind: Literal["progress"]
    agent_id: str
    contract_id: UUID | None
    item: str
    status: Literal["started", "in_progress", "blocked"]

class WorkspaceArtifactEvent(BaseModel):
    kind: Literal["artifact"]
    agent_id: str
    contract_id: UUID | None
    artifact_kind: str           # "video_render" | "image" | "doc" | "report" | ...
    ref: str
    summary: str
    preview_url: str | None
```

### What this fixes

Video director and graphic agents previously wrote to storage but never told the workspace. After migration, their parent agents (content_creation, marketing) call `_submit` which calls `publish_artifact`, which emits a `WorkspaceArtifactEvent` with `artifact_kind='video_render'` or `'image'`. `ActiveWorkspace` renders the thumbnail inline. The fix is structural, not per-agent.

### Backend wiring this introduces

- `app/services/workspace_event_bus.py` — per-user SSE channel manager (Redis pub/sub, reuses existing Redis infrastructure).
- `app/routers/workspace.py` — `GET /workspace/events` SSE endpoint.
- `frontend/src/app/dashboard/workspace/...` — extend `ActiveWorkspace` to consume events and render previews for `video_render` / `image` / `doc` artifact kinds.

---

## 13. Persona policy enforcement

Persona policy threads through hooks the BaseAgent already runs — it's not a separate enforcement layer.

### Module — `runtime/persona_gate.py`

```python
class PersonaPolicy(BaseModel):
    persona_id: str
    allowed_tool_ids: list[str] | Literal["*"]
    denied_tool_ids: list[str]
    action_thresholds: ActionThresholds   # spend cap, external send, etc.
    rate_limits: RateLimits
    prompt_fragments: list[str]
    classifier_default_mode: Literal["direct", "initiative"] | None
    initiative_phases_blocked: list[str]

async def load_persona_policy(user_id: UUID) -> PersonaPolicy: ...
```

### Integration points

1. **`PikarBaseAgent.__init__`** — fetch policy, prepend prompt fragments via the existing `build_persona_policy_block`. `policy_registry` becomes the data source; projection becomes deterministic and tested.
2. **`before_tool_callback`** — gate order: (a) tool allow-list / deny-list, (b) action threshold → approval, (c) research gate, (d) approval token check. Blocks write to `audit.policy_violations[]`.
3. **`task_router.py`** — checks `policy.classifier_default_mode` before falling back to rule defaults.

### Schema

```sql
CREATE TABLE persona_policies (
  persona_id TEXT PRIMARY KEY,
  allowed_tool_ids JSONB NOT NULL DEFAULT '"*"',
  denied_tool_ids JSONB NOT NULL DEFAULT '[]',
  action_thresholds JSONB NOT NULL DEFAULT '{}',
  rate_limits JSONB NOT NULL DEFAULT '{}',
  prompt_fragments JSONB NOT NULL DEFAULT '[]',
  classifier_default_mode TEXT,
  initiative_phases_blocked JSONB NOT NULL DEFAULT '[]',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Every blocked call surfaces in the audit report — policy enforcement is *visible*, not silent.

---

## 14. Initiative rituals

```python
async def start_initiative(self, *, goal: str, success_criteria: list[str],
                            owners: list[AgentID], phase: str = "ideation", ...) -> Initiative:
    # validates required fields; raises InitiativeContractError if missing
    # writes operational_state (closes manual-create gap from 2026-04-28 audit)
    # emits initiative-start report

async def advance_phase(self, initiative_id: UUID, current_phase: str) -> AdvanceResult:
    # 1. load checklist items for current_phase
    # 2. self-audit: every required item completed? exit criteria met?
    # 3. pass → write phase audit note to initiative_phase_history, advance, emit report
    # 4. fail → return AdvanceResult.blocked with gaps list

async def close_initiative(self, initiative_id: UUID) -> CloseReport:
    # requires final phase ('scale') complete
    # produces structured close: outcomes vs. success_criteria, artifacts, learnings, follow-ups
    # vaults the close report; sets status='completed', progress=100
```

Cross-agent handoff uses the existing `HandoffPacket` but appends to `initiative_phase_history` with `event='handoff'`, `from_agent`, `to_agent`, `packet_id`. Every transition is queryable from the initiative record, closing the cross-agent visibility gap from the prior audit.

---

## 15. `operations.yaml` schema

Per-agent declarative tunables, validated with Pydantic at startup.

```yaml
agent_id: financial
model:
  primary: gemini-2.5-pro
  fallback: gemini-2.5-flash
retry:
  max_attempts: 5
  backoff_initial_s: 2
  backoff_multiplier: 2
  backoff_max_s: 60
approval:
  required_above_usd: 1000
  required_for_external_send: true
research:
  max_iterations: 3
  required_source_min: 3
audit:
  fail_on_any_unmet_criterion: true
  escalate_on_partial: false
skills:
  allowed_ids: ["finance:*", "data:*", "compliance:legal-risk-assessment"]
  injection:
    top_k: 5
    similarity_floor: 0.65
initiative:
  phases_owned: ["validation", "build"]
  can_advance_phase: true
  can_close: false                    # only ExecutiveAgent can close
memory:
  history_retention_months: 18
  retrieval_top_k: 4
compaction:
  trigger_token_count: 80000
  keep_last_n_turns: 12
routing:
  last_resort_default: initiative     # for cautious agents
```

A malformed `operations.yaml` fails fast — the agent doesn't load. Defaults live in `runtime/operations_config.py`.

---

## 16. Schema migrations (consolidated)

```sql
-- Initiative checklist gains goal + agent ownership
ALTER TABLE initiative_checklist_items
  ADD COLUMN goal TEXT,
  ADD COLUMN assigned_agent_id TEXT;

-- Department tasks gain goal
ALTER TABLE department_tasks
  ADD COLUMN goal TEXT;

-- Department task todo items (new)
CREATE TABLE department_task_todo_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id UUID NOT NULL REFERENCES department_tasks(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','in_progress','completed','blocked','skipped')),
  evidence JSONB NOT NULL DEFAULT '[]',
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Research runs (new)
CREATE TABLE agent_research_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_contract_id UUID,
  task_contract_source TEXT,
  agent_id TEXT NOT NULL,
  query TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('open','in_progress','complete','failed')),
  result JSONB,
  iterations INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

-- Audit reports (new)
CREATE TABLE agent_audit_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT NOT NULL,
  task_contract_id UUID,
  overall_status TEXT NOT NULL CHECK (overall_status IN ('pass','fail','partial')),
  per_item JSONB NOT NULL DEFAULT '[]',
  per_criterion JSONB NOT NULL DEFAULT '[]',
  gaps JSONB NOT NULL DEFAULT '[]',
  policy_violations JSONB NOT NULL DEFAULT '[]',
  recoverable BOOLEAN NOT NULL,
  next_action TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Operational history (new)
CREATE TABLE agent_task_executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  agent_id TEXT NOT NULL,
  persona_id TEXT,
  mode TEXT NOT NULL DEFAULT 'initiative'
    CHECK (mode IN ('direct','initiative')),
  classifier_signal TEXT,
  contract_id UUID,
  contract_source TEXT
    CHECK (contract_source IN ('initiative_step','department_task','direct_request')),
  initiative_id UUID,
  goal TEXT,
  todo_snapshot JSONB,
  status TEXT NOT NULL CHECK (status IN ('running','submitted','escalated','failed')),
  research_run_id UUID REFERENCES agent_research_runs(id),
  audit_report_id UUID REFERENCES agent_audit_reports(id),
  vault_document_id UUID,
  artifacts JSONB NOT NULL DEFAULT '[]',
  outcome_summary TEXT,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);
CREATE INDEX idx_ate_user_agent ON agent_task_executions(user_id, agent_id, started_at DESC);
CREATE INDEX idx_ate_initiative ON agent_task_executions(initiative_id, started_at DESC);
CREATE INDEX idx_ate_goal_trgm ON agent_task_executions USING gin (goal gin_trgm_ops);

-- Persona policies (new normalized table)
CREATE TABLE persona_policies (
  persona_id TEXT PRIMARY KEY,
  allowed_tool_ids JSONB NOT NULL DEFAULT '"*"',
  denied_tool_ids JSONB NOT NULL DEFAULT '[]',
  action_thresholds JSONB NOT NULL DEFAULT '{}',
  rate_limits JSONB NOT NULL DEFAULT '{}',
  prompt_fragments JSONB NOT NULL DEFAULT '[]',
  classifier_default_mode TEXT,
  initiative_phases_blocked JSONB NOT NULL DEFAULT '[]',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

All migrations are additive — no destructive changes to existing tables. RLS policies follow the same patterns as adjacent tables (`auth.uid() = user_id`).

---

## 17. Migration plan — wave-based, low-risk

Eleven agents are live. Big-bang would be risky; the prior `project_v12_agent_quality_upgrade.md` succeeded on an isolated-worktree, wave-based pattern.

| Wave | Scope | Risk gate |
|---|---|---|
| **W1** | Build `runtime/` package + `PikarBaseAgent` + ops-config validator + new tables + schema migrations. No agents migrated yet. | Unit tests pass; old agents still work because nothing imports `PikarBaseAgent` yet. |
| **W2** | Migrate pilot agent: **financial** (small surface area, well-tested). Keep `specialized_agents.py` re-exports so callers don't break. Wire workspace SSE channel end-to-end with the pilot. | Full integration test: pilot runs an initiative step with research-gate + audit + vault report + workspace event. |
| **W3** | Migrate **executive**, **marketing**, **data**. Wire skill auto-injection. | Live shadow on 10% of executive traffic; diff outputs. |
| **W4** | Migrate **content_creation**, **sales**, **operations**, **hr**, **compliance**, **customer_support**, **strategic**. Video director and graphic agent outputs flow into the workspace as a side effect of content_creation migration. | Production rollout per agent. Workspace canvas verified for video_render + image artifact kinds. |
| **W5** | Cleanup: delete old code paths, fold `shared_instructions.py` into `runtime/skill_injection.py`, retire `enhanced_tools.py` wrappers no longer needed. | All tests pass; no caller references old API. |

Backwards compatibility: `specialized_agents.py` keeps re-exporting factory functions throughout W1-W4. Pattern proven by `project_enhanced_tools_removal.md`.

---

## 18. Testing strategy

Three layers, each owning a different failure mode:

- **Unit tests** per runtime module. Skill injection picks correct top-K; research gate blocks non-research tools; audit returns `pass` only when every required criterion is met; operations.yaml validation rejects malformed config; task router routes `/quick` to direct, `/plan` to initiative, ambiguous to LLM-fallback; persona gate denies disallowed tools and writes to audit.
- **Contract tests** per migrated agent. The agent's `operations.yaml` parses; the tool manifest resolves every tool name to a real callable in `app/agents/tools/`; `instructions.md` exists and is non-empty; declared `allowed_skill_ids` exist in `skills_registry`.
- **Integration tests** (one per migrated agent). Seed an initiative + checklist; run `execute_task` end-to-end with mocked research tools; assert (a) research gate enforced, (b) audit produced and persisted, (c) vault report emitted, (d) workspace SSE event observable, (e) `agent_task_executions` row written with all FKs populated.

Reuse: `tests/unit/test_agent_memory_callback.py` for hook-test patterns; existing integration scaffolding under `tests/unit/_tmp_video_readiness/`.

---

## 19. Out of scope (intentionally)

- The Documents subsystem (upload, parse, embed, editor consistency) — separate spec to follow per user's "operating model first, documents second" decision.
- Admin-panel UI for editing `operations.yaml` or `persona_policies` at runtime — the data model supports it; the UI is a downstream project.
- Replacing the existing `app/workflows/` engine — initiative orchestration continues to use it; the new runtime sits alongside.
- Rewriting `agent_memory.py` Layer-0 — kept as-is and complemented by Layers 1-3.

---

## 20. Open questions

None blocking. Items to confirm during implementation planning:

- Exact mapping of every existing `enhanced_tools.py` wrapper to the new `runtime/` modules — surfaces only at W5.
- Whether `admin/research/reporting` agents follow the same template as the 10 specialized ones, or get a reduced ops_config (no initiative phases owned). Recommended: same template, with `initiative.phases_owned: []`.
- The exact threshold for "stateful direct-mode turn" that triggers an `agent_task_executions` row — initial proposal: any tool call or any persisted artifact.

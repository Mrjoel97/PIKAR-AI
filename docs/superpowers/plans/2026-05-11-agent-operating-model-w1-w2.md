# Agent Operating Model — W1 + W2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the foundation runtime (W1) and migrate the financial agent (W2) onto the new operating model — `PikarBaseAgent` with ADK lifecycle enforcement of skill discipline, research-completion, audit, persona policy, and publication to vault/reports/workspace.

**Architecture:** A new `app/agents/runtime/` package houses lifecycle callbacks, gates (research/persona/audit), the direct-vs-initiative task router, the step-execution loop, initiative rituals, and a single publication primitive with four sinks (operational-history table, knowledge vault, reports UI, workspace SSE). `PikarBaseAgent` extends the existing `PikarAgent` and is the only place agents are instantiated. The financial agent migrates first as the pilot; other agents follow in later plans.

**Tech Stack:** Python 3.10+ FastAPI · Google ADK (Gemini) · Supabase Postgres · Redis pub/sub (existing `services/cache.py`) · pydantic v2 · pytest (`uv run pytest`) · Next.js 16 / React 19 / vitest (`npm test`) for the workspace SSE consumer.

**Spec:** `docs/superpowers/specs/2026-05-11-agent-operating-model-design.md` (commit `d71ac966`).

**Scope of this plan:** Waves W1 (foundation, no agents migrated) and W2 (financial pilot). Waves W3–W5 get their own plans when we're ready to start them.

---

## How tasks are organized

- **Section A — Foundation (Tasks 1–20):** schema migrations, shared types, `OperationsConfig`, `PikarBaseAgent` skeleton.
- **Section B — Lifecycle hooks (Tasks 21–45):** the four ADK callbacks, skill injection, memory retrieval, handoff, compaction.
- **Section C — Gates (Tasks 46–75):** research gate, audit, persona gate, task router.
- **Section D — Execution + publication (Tasks 76–105):** step runtime, initiative rituals, publication sinks, workspace SSE backend.
- **Section E — Financial pilot (Tasks 106–130):** financial agent migration, contract + integration tests, frontend SSE consumer.

Sections A → E have soft dependencies: A's types must land before B/C/D start; B's lifecycle wiring uses C and D's functions (those callsites can be stubs initially and then replaced). E depends on everything. The order within each section is TDD: failing test → run → implement → run → commit.

---

## Section A — Foundation (Tasks 1–20)

### Task 1: Migration — initiative_checklist_items add goal + assigned_agent_id

**Files:**
- Create: `supabase/migrations/20260511120000_initiative_checklist_items_goal_owner.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
-- supabase/migrations/20260511120000_initiative_checklist_items_goal_owner.sql
--
-- Agent Operating Model — Foundation 1/7
-- Extends initiative_checklist_items so each step carries its own goal
-- and an explicit agent owner. Required input for TaskContract hydration
-- (see app/agents/runtime/step_runtime.py).

ALTER TABLE public.initiative_checklist_items
    ADD COLUMN IF NOT EXISTS goal TEXT;

ALTER TABLE public.initiative_checklist_items
    ADD COLUMN IF NOT EXISTS assigned_agent_id TEXT;

CREATE INDEX IF NOT EXISTS idx_initiative_checklist_items_assigned_agent
    ON public.initiative_checklist_items (assigned_agent_id)
    WHERE assigned_agent_id IS NOT NULL;
```

- [ ] **Step 2: Apply migration locally**

```bash
supabase db push --local
```

Expected: PASS — new columns reported in apply output.

- [ ] **Step 3: Verify columns landed**

```bash
supabase inspect db table-record-counts --linked | grep initiative_checklist_items
psql "$LOCAL_DB_URL" -c "\d+ public.initiative_checklist_items" | grep -E "goal|assigned_agent_id"
```

Expected: both `goal` and `assigned_agent_id` columns shown as `text`.

- [ ] **Step 4: Sanity-test additivity**

```bash
psql "$LOCAL_DB_URL" -c "SELECT count(*) FROM public.initiative_checklist_items WHERE goal IS NULL;"
```

Expected: every existing row reported (additive migration, no backfill).

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/20260511120000_initiative_checklist_items_goal_owner.sql
git commit -m "feat(db): add goal + assigned_agent_id to initiative_checklist_items"
```

---

### Task 2: Migration — department_tasks add goal

**Files:**
- Create: `supabase/migrations/20260511120100_department_tasks_goal.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
-- supabase/migrations/20260511120100_department_tasks_goal.sql
--
-- Agent Operating Model — Foundation 2/7
-- department_tasks gains a freeform goal text field. Mirrors the
-- initiative_checklist_items.goal column so TaskContract.goal can be
-- hydrated from either source identically.

ALTER TABLE public.department_tasks
    ADD COLUMN IF NOT EXISTS goal TEXT;
```

- [ ] **Step 2: Apply migration locally**

```bash
supabase db push --local
```

Expected: PASS.

- [ ] **Step 3: Verify column landed**

```bash
psql "$LOCAL_DB_URL" -c "\d+ public.department_tasks" | grep -E "^\s+goal\s+\|"
```

Expected: `goal | text` row shown.

- [ ] **Step 4: Confirm RLS unchanged**

```bash
psql "$LOCAL_DB_URL" -c "SELECT polname FROM pg_policy WHERE polrelid='public.department_tasks'::regclass;"
```

Expected: existing policies unchanged (additive migration).

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/20260511120100_department_tasks_goal.sql
git commit -m "feat(db): add goal column to department_tasks"
```

---

### Task 3: Migration — department_task_todo_items

**Files:**
- Create: `supabase/migrations/20260511120200_department_task_todo_items.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
-- supabase/migrations/20260511120200_department_task_todo_items.sql
--
-- Agent Operating Model — Foundation 3/7
-- Per-task to-do list for department_tasks. Mirrors the structure of
-- initiative_checklist_items so the TaskContract hydration code can
-- treat both sources symmetrically. status enum matches TodoItem in
-- app/agents/runtime/types.py exactly.

CREATE EXTENSION IF NOT EXISTS moddatetime SCHEMA extensions;

CREATE TABLE IF NOT EXISTS public.department_task_todo_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES public.department_tasks(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','in_progress','completed','blocked','skipped')),
    evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dttd_task_sort
    ON public.department_task_todo_items (task_id, sort_order);

DROP TRIGGER IF EXISTS department_task_todo_items_updated_at
    ON public.department_task_todo_items;
CREATE TRIGGER department_task_todo_items_updated_at
    BEFORE UPDATE ON public.department_task_todo_items
    FOR EACH ROW EXECUTE FUNCTION extensions.moddatetime(updated_at);

ALTER TABLE public.department_task_todo_items ENABLE ROW LEVEL SECURITY;

-- RLS mirrors department_tasks: users can read/write todo rows iff they
-- can read/write the parent task. Re-using the parent's owner check.
DROP POLICY IF EXISTS "dttd_owner_select" ON public.department_task_todo_items;
CREATE POLICY "dttd_owner_select" ON public.department_task_todo_items
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.department_tasks t
            WHERE t.id = task_id AND t.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "dttd_owner_modify" ON public.department_task_todo_items;
CREATE POLICY "dttd_owner_modify" ON public.department_task_todo_items
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.department_tasks t
            WHERE t.id = task_id AND t.user_id = auth.uid()
        )
    ) WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.department_tasks t
            WHERE t.id = task_id AND t.user_id = auth.uid()
        )
    );

GRANT SELECT, INSERT, UPDATE, DELETE
    ON public.department_task_todo_items TO authenticated;
```

- [ ] **Step 2: Apply migration locally**

```bash
supabase db push --local
```

Expected: PASS.

- [ ] **Step 3: Verify table + RLS**

```bash
psql "$LOCAL_DB_URL" -c "\d+ public.department_task_todo_items"
psql "$LOCAL_DB_URL" -c "SELECT polname FROM pg_policy WHERE polrelid='public.department_task_todo_items'::regclass;"
```

Expected: both policies present; status check constraint visible.

- [ ] **Step 4: Confirm status enum matches contract**

```bash
psql "$LOCAL_DB_URL" -c "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='public.department_task_todo_items'::regclass AND contype='c';"
```

Expected: contains `'pending','in_progress','completed','blocked','skipped'`.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/20260511120200_department_task_todo_items.sql
git commit -m "feat(db): add department_task_todo_items table"
```

---

### Task 4: Migration — agent_research_runs

**Files:**
- Create: `supabase/migrations/20260511120300_agent_research_runs.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
-- supabase/migrations/20260511120300_agent_research_runs.sql
--
-- Agent Operating Model — Foundation 4/7
-- Tracks each research session opened by an agent for a TaskContract.
-- The research-completion gate (app/agents/runtime/research_gate.py)
-- blocks non-research tool calls until the row reaches status='complete'.

CREATE TABLE IF NOT EXISTS public.agent_research_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_contract_id UUID,
    task_contract_source TEXT,
    agent_id TEXT NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    query TEXT NOT NULL,
    status TEXT NOT NULL
        CHECK (status IN ('open','in_progress','complete','failed')),
    result JSONB,
    iterations INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_arr_contract
    ON public.agent_research_runs (task_contract_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_arr_agent
    ON public.agent_research_runs (agent_id, created_at DESC);

ALTER TABLE public.agent_research_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "agent_research_runs_owner_all"
    ON public.agent_research_runs;
CREATE POLICY "agent_research_runs_owner_all"
    ON public.agent_research_runs
    FOR ALL
    USING (user_id IS NULL OR auth.uid() = user_id)
    WITH CHECK (user_id IS NULL OR auth.uid() = user_id);

GRANT SELECT, INSERT, UPDATE, DELETE
    ON public.agent_research_runs TO authenticated;
```

- [ ] **Step 2: Apply migration locally**

```bash
supabase db push --local
```

Expected: PASS.

- [ ] **Step 3: Verify table + check constraint**

```bash
psql "$LOCAL_DB_URL" -c "\d+ public.agent_research_runs"
```

Expected: status check constraint shows `'open','in_progress','complete','failed'`.

- [ ] **Step 4: Verify insert + status transition**

```bash
psql "$LOCAL_DB_URL" -c "INSERT INTO public.agent_research_runs (agent_id, query, status) VALUES ('FIN','smoke', 'open') RETURNING id, status;"
psql "$LOCAL_DB_URL" -c "DELETE FROM public.agent_research_runs WHERE query='smoke';"
```

Expected: insert succeeds; row deletes cleanly.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/20260511120300_agent_research_runs.sql
git commit -m "feat(db): add agent_research_runs table for research-completion gate"
```

---

### Task 5: Migration — agent_audit_reports

**Files:**
- Create: `supabase/migrations/20260511120400_agent_audit_reports.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
-- supabase/migrations/20260511120400_agent_audit_reports.sql
--
-- Agent Operating Model — Foundation 5/7
-- Persists the self-audit report produced at the end of every
-- initiative-mode TaskContract execution. Backs AuditReport in
-- app/agents/runtime/types.py.

CREATE TABLE IF NOT EXISTS public.agent_audit_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    task_contract_id UUID,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    overall_status TEXT NOT NULL
        CHECK (overall_status IN ('pass','fail','partial')),
    per_item JSONB NOT NULL DEFAULT '[]'::jsonb,
    per_criterion JSONB NOT NULL DEFAULT '[]'::jsonb,
    gaps JSONB NOT NULL DEFAULT '[]'::jsonb,
    policy_violations JSONB NOT NULL DEFAULT '[]'::jsonb,
    recoverable BOOLEAN NOT NULL,
    next_action TEXT NOT NULL
        CHECK (next_action IN ('submit','retry','escalate')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_aar_contract
    ON public.agent_audit_reports (task_contract_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_aar_agent
    ON public.agent_audit_reports (agent_id, created_at DESC);

ALTER TABLE public.agent_audit_reports ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "agent_audit_reports_owner_all"
    ON public.agent_audit_reports;
CREATE POLICY "agent_audit_reports_owner_all"
    ON public.agent_audit_reports
    FOR ALL
    USING (user_id IS NULL OR auth.uid() = user_id)
    WITH CHECK (user_id IS NULL OR auth.uid() = user_id);

GRANT SELECT, INSERT, UPDATE, DELETE
    ON public.agent_audit_reports TO authenticated;
```

- [ ] **Step 2: Apply migration locally**

```bash
supabase db push --local
```

Expected: PASS.

- [ ] **Step 3: Verify table + both check constraints**

```bash
psql "$LOCAL_DB_URL" -c "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='public.agent_audit_reports'::regclass AND contype='c';"
```

Expected: two check constraints — overall_status and next_action.

- [ ] **Step 4: Smoke insert**

```bash
psql "$LOCAL_DB_URL" -c "INSERT INTO public.agent_audit_reports (agent_id, overall_status, recoverable, next_action) VALUES ('FIN','pass', true, 'submit') RETURNING id;"
psql "$LOCAL_DB_URL" -c "DELETE FROM public.agent_audit_reports WHERE agent_id='FIN' AND overall_status='pass';"
```

Expected: insert + delete succeed.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/20260511120400_agent_audit_reports.sql
git commit -m "feat(db): add agent_audit_reports table"
```

---

### Task 6: Migration — agent_task_executions

**Files:**
- Create: `supabase/migrations/20260511120500_agent_task_executions.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
-- supabase/migrations/20260511120500_agent_task_executions.sql
--
-- Agent Operating Model — Foundation 6/7
-- Layer-1 operational history: one row per TaskContract execution
-- (or stateful direct-mode turn). FKs reach the research and audit
-- tables. gin_trgm on goal enables similarity search at retrieval time.

CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA public;

CREATE TABLE IF NOT EXISTS public.agent_task_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,
    persona_id TEXT,
    mode TEXT NOT NULL DEFAULT 'initiative'
        CHECK (mode IN ('direct','initiative')),
    classifier_signal TEXT
        CHECK (classifier_signal IS NULL OR classifier_signal IN ('override','rule','llm')),
    contract_id UUID,
    contract_source TEXT
        CHECK (contract_source IS NULL OR contract_source IN ('initiative_step','department_task','direct_request')),
    initiative_id UUID,
    goal TEXT,
    todo_snapshot JSONB,
    status TEXT NOT NULL
        CHECK (status IN ('running','submitted','escalated','failed')),
    research_run_id UUID REFERENCES public.agent_research_runs(id) ON DELETE SET NULL,
    audit_report_id UUID REFERENCES public.agent_audit_reports(id) ON DELETE SET NULL,
    vault_document_id UUID,
    artifacts JSONB NOT NULL DEFAULT '[]'::jsonb,
    outcome_summary TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ate_user_agent
    ON public.agent_task_executions (user_id, agent_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_ate_initiative
    ON public.agent_task_executions (initiative_id, started_at DESC)
    WHERE initiative_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ate_goal_trgm
    ON public.agent_task_executions USING gin (goal public.gin_trgm_ops);

ALTER TABLE public.agent_task_executions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "agent_task_executions_owner_all"
    ON public.agent_task_executions;
CREATE POLICY "agent_task_executions_owner_all"
    ON public.agent_task_executions
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

GRANT SELECT, INSERT, UPDATE, DELETE
    ON public.agent_task_executions TO authenticated;
```

- [ ] **Step 2: Apply migration locally**

```bash
supabase db push --local
```

Expected: PASS.

- [ ] **Step 3: Verify table, FKs, and trigram index**

```bash
psql "$LOCAL_DB_URL" -c "\d+ public.agent_task_executions"
psql "$LOCAL_DB_URL" -c "SELECT indexname FROM pg_indexes WHERE tablename='agent_task_executions';"
```

Expected: three indexes (`idx_ate_user_agent`, `idx_ate_initiative`, `idx_ate_goal_trgm`); FKs to `agent_research_runs` and `agent_audit_reports` listed.

- [ ] **Step 4: Verify trigram extension loaded**

```bash
psql "$LOCAL_DB_URL" -c "SELECT extname FROM pg_extension WHERE extname='pg_trgm';"
```

Expected: one row returned.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/20260511120500_agent_task_executions.sql
git commit -m "feat(db): add agent_task_executions operational-history table"
```

---

### Task 7: Migration — persona_policies

**Files:**
- Create: `supabase/migrations/20260511120600_persona_policies.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
-- supabase/migrations/20260511120600_persona_policies.sql
--
-- Agent Operating Model — Foundation 7/7
-- Normalized storage for per-persona policy:
--   allow/deny tool lists, action thresholds, rate limits,
--   prompt fragments, classifier default mode, blocked phases.
-- Loaded by app/agents/runtime/persona_gate.load_persona_policy.

CREATE EXTENSION IF NOT EXISTS moddatetime SCHEMA extensions;

CREATE TABLE IF NOT EXISTS public.persona_policies (
    persona_id TEXT PRIMARY KEY,
    allowed_tool_ids JSONB NOT NULL DEFAULT '"*"'::jsonb,
    denied_tool_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    action_thresholds JSONB NOT NULL DEFAULT '{}'::jsonb,
    rate_limits JSONB NOT NULL DEFAULT '{}'::jsonb,
    prompt_fragments JSONB NOT NULL DEFAULT '[]'::jsonb,
    classifier_default_mode TEXT
        CHECK (classifier_default_mode IS NULL OR classifier_default_mode IN ('direct','initiative')),
    initiative_phases_blocked JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS persona_policies_updated_at ON public.persona_policies;
CREATE TRIGGER persona_policies_updated_at
    BEFORE UPDATE ON public.persona_policies
    FOR EACH ROW EXECUTE FUNCTION extensions.moddatetime(updated_at);

ALTER TABLE public.persona_policies ENABLE ROW LEVEL SECURITY;

-- Policies are server-side configuration; only service_role mutates.
-- Authenticated users may read so the front end can render policy badges.
DROP POLICY IF EXISTS "persona_policies_authenticated_read"
    ON public.persona_policies;
CREATE POLICY "persona_policies_authenticated_read"
    ON public.persona_policies
    FOR SELECT TO authenticated USING (true);

GRANT SELECT ON public.persona_policies TO authenticated;
GRANT ALL ON public.persona_policies TO service_role;
```

- [ ] **Step 2: Apply migration locally**

```bash
supabase db push --local
```

Expected: PASS.

- [ ] **Step 3: Verify schema, defaults, and RLS**

```bash
psql "$LOCAL_DB_URL" -c "\d+ public.persona_policies"
psql "$LOCAL_DB_URL" -c "SELECT polname, polcmd FROM pg_policy WHERE polrelid='public.persona_policies'::regclass;"
```

Expected: `allowed_tool_ids` defaults to `'"*"'::jsonb`; one SELECT policy for authenticated.

- [ ] **Step 4: Smoke insert as service_role**

```bash
psql "$LOCAL_DB_URL" -c "INSERT INTO public.persona_policies (persona_id) VALUES ('test_persona') RETURNING persona_id, allowed_tool_ids;"
psql "$LOCAL_DB_URL" -c "DELETE FROM public.persona_policies WHERE persona_id='test_persona';"
```

Expected: row created with `allowed_tool_ids = "*"`.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/20260511120600_persona_policies.sql
git commit -m "feat(db): add persona_policies table for runtime policy enforcement"
```

---

### Task 8: Create `app/agents/runtime/__init__.py`

**Files:**
- Create: `app/agents/runtime/__init__.py`
- Test: `tests/unit/agents/runtime/test_package_init.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_package_init.py
"""Smoke test: the runtime package is importable."""

from __future__ import annotations


def test_runtime_package_is_importable():
    import importlib

    mod = importlib.import_module("app.agents.runtime")
    assert mod.__name__ == "app.agents.runtime"


def test_runtime_package_is_a_namespace_for_submodules():
    # Importing the package must not eagerly import submodules
    # (those have heavy deps and would slow agent start-up).
    import sys

    sys.modules.pop("app.agents.runtime.types", None)
    import app.agents.runtime  # noqa: F401

    assert "app.agents.runtime.types" not in sys.modules
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_package_init.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.agents.runtime'`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/__init__.py
# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Runtime support package for PikarBaseAgent.

Submodules (loaded lazily by callers):
  - types: shared Pydantic / dataclass contracts.
  - operations_config: operations.yaml loader + validator.
  - lifecycle: ADK before/after callbacks (stubs in Section A; bodies in Section B).
  - research_gate, audit, persona_gate, task_router, ...

Importing this package must NOT pull heavy submodules; downstream code does
`from app.agents.runtime.types import TaskContract` so each consumer pays
only for what it needs.
"""
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_package_init.py -v
```

Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/__init__.py tests/unit/agents/runtime/test_package_init.py
git commit -m "feat(runtime): scaffold app.agents.runtime package"
```

---

### Task 9: `runtime/types.py` — Mode + TodoItem + StepSummary

**Files:**
- Create: `app/agents/runtime/types.py`
- Test: `tests/unit/agents/runtime/test_types_todo.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_types_todo.py
"""TodoItem + StepSummary basics."""

from __future__ import annotations

from uuid import uuid4

import pytest


def test_mode_literal_values():
    from app.agents.runtime.types import Mode  # type: ignore[attr-defined]

    # Mode is a typing.Literal — verify by attempting construction of TodoItem etc.
    assert Mode is not None


def test_todo_item_is_frozen_and_immutable():
    from app.agents.runtime.types import TodoItem

    item = TodoItem(
        id=uuid4(),
        title="Draft outline",
        description=None,
        status="pending",
        evidence=[],
        sort_order=0,
    )
    assert item.title == "Draft outline"
    assert item.status == "pending"
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        item.title = "Mutated"  # type: ignore[misc]


def test_step_summary_carries_assigned_agent():
    from app.agents.runtime.types import StepSummary

    summary = StepSummary(
        id=uuid4(),
        title="Run financial model",
        status="in_progress",
        assigned_agent_id="FIN",
    )
    assert summary.assigned_agent_id == "FIN"


def test_step_summary_allows_unassigned():
    from app.agents.runtime.types import StepSummary

    summary = StepSummary(
        id=uuid4(),
        title="Backlog step",
        status="pending",
        assigned_agent_id=None,
    )
    assert summary.assigned_agent_id is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_types_todo.py -v
```

Expected: FAIL with `ModuleNotFoundError` / `ImportError: cannot import name 'TodoItem'`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/types.py
# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Shared contracts for the agent runtime.

These types are imported across the runtime package, BaseAgent, and the
section-specific modules (lifecycle, research_gate, persona_gate, ...).
They are intentionally lightweight: frozen dataclasses for value objects
and pydantic BaseModels for anything that crosses a JSON boundary
(DB rows, SSE events, audit reports).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

Mode = Literal["direct", "initiative"]


@dataclass(frozen=True)
class TodoItem:
    """A single checklist item inside a TaskContract."""

    id: UUID
    title: str
    description: str | None
    status: Literal["pending", "in_progress", "completed", "blocked", "skipped"]
    evidence: list[dict]
    sort_order: int


@dataclass(frozen=True)
class StepSummary:
    """Read-only sibling-step view exposed inside a TaskContract."""

    id: UUID
    title: str
    status: str
    assigned_agent_id: str | None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_types_todo.py -v
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/types.py tests/unit/agents/runtime/test_types_todo.py
git commit -m "feat(runtime): add Mode, TodoItem, StepSummary contracts"
```

---

### Task 10: `runtime/types.py` — TaskContract

**Files:**
- Edit: `app/agents/runtime/types.py`
- Test: `tests/unit/agents/runtime/test_types_task_contract.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_types_task_contract.py
"""TaskContract — frozen, carries full plan visibility."""

from __future__ import annotations

from uuid import uuid4

import pytest


def test_task_contract_initiative_step():
    from app.agents.runtime.types import StepSummary, TaskContract, TodoItem
    from app.skills.registry import AgentID

    cid = uuid4()
    init_id = uuid4()
    todo = TodoItem(
        id=uuid4(),
        title="Outline",
        description=None,
        status="pending",
        evidence=[],
        sort_order=0,
    )
    sibling = StepSummary(
        id=uuid4(), title="Sibling", status="pending", assigned_agent_id="MKT"
    )

    contract = TaskContract(
        id=cid,
        source="initiative_step",
        goal="Produce Q3 forecast",
        todo_items=[todo],
        success_criteria=["revenue numbers cited", "variance < 5%"],
        owners=[AgentID.FIN],
        evidence_required=["research_summary", "audit_report"],
        initiative_id=init_id,
        initiative_phase="validation",
        sibling_steps=[sibling],
    )

    assert contract.id == cid
    assert contract.source == "initiative_step"
    assert contract.owners == [AgentID.FIN]
    assert contract.sibling_steps[0].assigned_agent_id == "MKT"


def test_task_contract_is_frozen():
    from app.agents.runtime.types import TaskContract
    from app.skills.registry import AgentID

    contract = TaskContract(
        id=uuid4(),
        source="department_task",
        goal="Triage support backlog",
        todo_items=[],
        success_criteria=[],
        owners=[AgentID.SUPP],
        evidence_required=[],
        initiative_id=None,
        initiative_phase=None,
        sibling_steps=[],
    )

    with pytest.raises(Exception):
        contract.goal = "tampered"  # type: ignore[misc]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_types_task_contract.py -v
```

Expected: FAIL with `ImportError: cannot import name 'TaskContract'`.

- [ ] **Step 3: Append the implementation**

```python
# app/agents/runtime/types.py  (append)

from app.skills.registry import AgentID  # noqa: E402


@dataclass(frozen=True)
class TaskContract:
    """Frozen contract describing a unit of work executed by an agent.

    Initiative mode only — direct mode uses :class:`DirectRequest`. Sibling
    steps are read-only context; mutations require :func:`propose_plan_change`.
    """

    id: UUID
    source: Literal["initiative_step", "department_task"]
    goal: str
    todo_items: list[TodoItem]
    success_criteria: list[str]
    owners: list[AgentID]
    evidence_required: list[str]
    initiative_id: UUID | None
    initiative_phase: str | None
    sibling_steps: list[StepSummary]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_types_task_contract.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/types.py tests/unit/agents/runtime/test_types_task_contract.py
git commit -m "feat(runtime): add TaskContract dataclass"
```

---

### Task 11: `runtime/types.py` — DirectRequest + Artifact

**Files:**
- Edit: `app/agents/runtime/types.py`
- Test: `tests/unit/agents/runtime/test_types_direct_artifact.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_types_direct_artifact.py
"""DirectRequest + Artifact contracts."""

from __future__ import annotations

from uuid import uuid4


def test_direct_request_with_session():
    from app.agents.runtime.types import DirectRequest
    from app.skills.registry import AgentID

    uid = uuid4()
    sid = uuid4()
    req = DirectRequest(
        user_id=uid,
        agent_id=AgentID.FIN,
        persona_id="founder",
        message="What's our Q3 revenue?",
        session_id=sid,
    )
    assert req.message.startswith("What's")
    assert req.session_id == sid


def test_direct_request_without_session():
    from app.agents.runtime.types import DirectRequest
    from app.skills.registry import AgentID

    req = DirectRequest(
        user_id=uuid4(),
        agent_id=AgentID.SUPP,
        persona_id="cs_lead",
        message="summarize ticket #42",
        session_id=None,
    )
    assert req.session_id is None


def test_artifact_payload_optional():
    from app.agents.runtime.types import Artifact

    a = Artifact(
        kind="video_render",
        ref="vault://videos/abc.mp4",
        summary="60s explainer",
        payload=None,
    )
    assert a.kind == "video_render"
    assert a.payload is None

    b = Artifact(
        kind="doc",
        ref="docs/123",
        summary="brief",
        payload={"word_count": 480},
    )
    assert b.payload == {"word_count": 480}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_types_direct_artifact.py -v
```

Expected: FAIL — `DirectRequest` / `Artifact` not exported.

- [ ] **Step 3: Append the implementation**

```python
# app/agents/runtime/types.py  (append)


@dataclass(frozen=True)
class DirectRequest:
    """Lightweight envelope for a direct-mode (non-initiative) user turn."""

    user_id: UUID
    agent_id: AgentID
    persona_id: str
    message: str
    session_id: UUID | None


@dataclass(frozen=True)
class Artifact:
    """A concrete deliverable produced inside execute_task / respond_directly.

    `kind` matches the publication-sink dispatcher in
    app/agents/runtime/publication.py (e.g. ``"video_render"``, ``"image"``,
    ``"doc"``, ``"report"``, ``"data_query"``).
    """

    kind: str
    ref: str
    summary: str
    payload: dict | None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_types_direct_artifact.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/types.py tests/unit/agents/runtime/test_types_direct_artifact.py
git commit -m "feat(runtime): add DirectRequest and Artifact contracts"
```

---

### Task 12: `runtime/types.py` — Source + ResearchResult

**Files:**
- Edit: `app/agents/runtime/types.py`
- Test: `tests/unit/agents/runtime/test_types_research.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_types_research.py
"""ResearchResult shapes the research-completion gate output."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError


def test_research_result_complete_with_sources():
    from app.agents.runtime.types import ResearchResult, Source

    src = Source(
        url="https://example.com/q3",
        title="Q3 results",
        key_claim="Revenue grew 12% QoQ.",
        retrieved_at=datetime.now(timezone.utc),
    )
    result = ResearchResult(
        summary="Revenue growth is on track.",
        sources=[src],
        contradictions=[],
        coverage_assessment="complete",
        missing_information=[],
    )
    assert result.coverage_assessment == "complete"
    assert result.sources[0].title == "Q3 results"


def test_research_result_partial_requires_missing_info_present():
    """coverage_assessment='partial' must be representable with gaps listed."""
    from app.agents.runtime.types import ResearchResult

    result = ResearchResult(
        summary="Some context found.",
        sources=[],
        contradictions=["price differs across two sources"],
        coverage_assessment="partial",
        missing_information=["margin data", "headcount"],
    )
    assert result.coverage_assessment == "partial"
    assert "headcount" in result.missing_information


def test_research_result_rejects_unknown_coverage_value():
    from app.agents.runtime.types import ResearchResult

    with pytest.raises(ValidationError):
        ResearchResult(
            summary="",
            sources=[],
            contradictions=[],
            coverage_assessment="kinda",  # type: ignore[arg-type]
            missing_information=[],
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_types_research.py -v
```

Expected: FAIL — `Source` / `ResearchResult` not exported.

- [ ] **Step 3: Append the implementation**

```python
# app/agents/runtime/types.py  (append)

from datetime import datetime  # noqa: E402

from pydantic import BaseModel  # noqa: E402


class Source(BaseModel):
    """A single cited source backing a research run."""

    url: str
    title: str
    key_claim: str
    retrieved_at: datetime


class ResearchResult(BaseModel):
    """Structured result persisted to ``agent_research_runs.result``.

    `coverage_assessment == "complete"` is the gate that unblocks
    non-research tool calls inside ``execute_task``.
    """

    summary: str
    sources: list[Source]
    contradictions: list[str]
    coverage_assessment: Literal["complete", "partial"]
    missing_information: list[str]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_types_research.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/types.py tests/unit/agents/runtime/test_types_research.py
git commit -m "feat(runtime): add Source and ResearchResult models"
```

---

### Task 13: `runtime/types.py` — ItemAudit + CriterionAudit + PolicyViolation + AuditReport

**Files:**
- Edit: `app/agents/runtime/types.py`
- Test: `tests/unit/agents/runtime/test_types_audit.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_types_audit.py
"""AuditReport and its sub-models."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError


def test_item_audit_pass_with_evidence():
    from app.agents.runtime.types import ItemAudit

    audit = ItemAudit(
        item_id=uuid4(),
        status="pass",
        evidence_pointers=["vault://reports/123#section-2"],
        gaps=[],
    )
    assert audit.status == "pass"


def test_criterion_audit_met():
    from app.agents.runtime.types import CriterionAudit

    c = CriterionAudit(
        criterion="variance < 5%",
        met=True,
        justification="Computed variance = 3.1% on line 28.",
    )
    assert c.met


def test_policy_violation_known_kind():
    from app.agents.runtime.types import PolicyViolation

    v = PolicyViolation(
        kind="tool_denied",
        detail="sendgrid_send not in persona allow-list",
        tool_id="sendgrid_send",
    )
    assert v.kind == "tool_denied"


def test_policy_violation_rejects_unknown_kind():
    from app.agents.runtime.types import PolicyViolation

    with pytest.raises(ValidationError):
        PolicyViolation(
            kind="mystery",  # type: ignore[arg-type]
            detail="unknown",
            tool_id=None,
        )


def test_audit_report_pass_recoverable_submit():
    from app.agents.runtime.types import (
        AuditReport,
        CriterionAudit,
        ItemAudit,
    )

    report = AuditReport(
        overall_status="pass",
        per_item=[
            ItemAudit(
                item_id=uuid4(),
                status="pass",
                evidence_pointers=["vault://x"],
                gaps=[],
            )
        ],
        per_criterion=[
            CriterionAudit(criterion="x", met=True, justification="ok")
        ],
        gaps=[],
        policy_violations=[],
        recoverable=True,
        next_action="submit",
    )
    assert report.overall_status == "pass"
    assert report.next_action == "submit"


def test_audit_report_rejects_bad_next_action():
    from app.agents.runtime.types import AuditReport

    with pytest.raises(ValidationError):
        AuditReport(
            overall_status="fail",
            per_item=[],
            per_criterion=[],
            gaps=["nothing audited"],
            policy_violations=[],
            recoverable=False,
            next_action="ignore",  # type: ignore[arg-type]
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_types_audit.py -v
```

Expected: FAIL — audit types missing.

- [ ] **Step 3: Append the implementation**

```python
# app/agents/runtime/types.py  (append)


class ItemAudit(BaseModel):
    """Per-TodoItem result inside an AuditReport."""

    item_id: UUID
    status: Literal["pass", "fail", "partial"]
    evidence_pointers: list[str]
    gaps: list[str]


class CriterionAudit(BaseModel):
    """Per-success-criterion result inside an AuditReport."""

    criterion: str
    met: bool
    justification: str


class PolicyViolation(BaseModel):
    """A policy block raised during ``before_tool_callback``.

    Populated by the persona gate, action-threshold check, or rate limiter
    and appended to the audit report so enforcement is *visible*.
    """

    kind: Literal["tool_denied", "threshold_exceeded", "rate_limited"]
    detail: str
    tool_id: str | None


class AuditReport(BaseModel):
    """Output of ``audit_against_contract`` — persisted to ``agent_audit_reports``."""

    overall_status: Literal["pass", "fail", "partial"]
    per_item: list[ItemAudit]
    per_criterion: list[CriterionAudit]
    gaps: list[str]
    policy_violations: list[PolicyViolation]
    recoverable: bool
    next_action: Literal["submit", "retry", "escalate"]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_types_audit.py -v
```

Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/types.py tests/unit/agents/runtime/test_types_audit.py
git commit -m "feat(runtime): add audit-report contracts"
```

---

### Task 14: `runtime/types.py` — ActionThresholds + RateLimits + PersonaPolicy

**Files:**
- Edit: `app/agents/runtime/types.py`
- Test: `tests/unit/agents/runtime/test_types_persona_policy.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_types_persona_policy.py
"""PersonaPolicy and its sub-models drive the persona gate."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_action_thresholds_with_spend_cap():
    from app.agents.runtime.types import ActionThresholds

    t = ActionThresholds(
        max_spend_usd=1000.0,
        require_approval_for_external_send=True,
        custom={"max_emails_per_day": 50},
    )
    assert t.max_spend_usd == 1000.0
    assert t.custom["max_emails_per_day"] == 50


def test_rate_limits_optional_fields():
    from app.agents.runtime.types import RateLimits

    r = RateLimits(requests_per_minute=None, tokens_per_day=200_000)
    assert r.tokens_per_day == 200_000


def test_persona_policy_wildcard_allow_list():
    from app.agents.runtime.types import (
        ActionThresholds,
        PersonaPolicy,
        RateLimits,
    )

    p = PersonaPolicy(
        persona_id="founder",
        allowed_tool_ids="*",
        denied_tool_ids=["transfer_funds"],
        action_thresholds=ActionThresholds(
            max_spend_usd=None,
            require_approval_for_external_send=False,
            custom={},
        ),
        rate_limits=RateLimits(requests_per_minute=None, tokens_per_day=None),
        prompt_fragments=["You are speaking with a founder."],
        classifier_default_mode="initiative",
        initiative_phases_blocked=[],
    )
    assert p.allowed_tool_ids == "*"
    assert p.classifier_default_mode == "initiative"


def test_persona_policy_rejects_bad_default_mode():
    from app.agents.runtime.types import (
        ActionThresholds,
        PersonaPolicy,
        RateLimits,
    )

    with pytest.raises(ValidationError):
        PersonaPolicy(
            persona_id="x",
            allowed_tool_ids=["a"],
            denied_tool_ids=[],
            action_thresholds=ActionThresholds(
                max_spend_usd=None,
                require_approval_for_external_send=False,
                custom={},
            ),
            rate_limits=RateLimits(requests_per_minute=None, tokens_per_day=None),
            prompt_fragments=[],
            classifier_default_mode="lol",  # type: ignore[arg-type]
            initiative_phases_blocked=[],
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_types_persona_policy.py -v
```

Expected: FAIL — `ActionThresholds` / `RateLimits` / `PersonaPolicy` not exported.

- [ ] **Step 3: Append the implementation**

```python
# app/agents/runtime/types.py  (append)


class ActionThresholds(BaseModel):
    """Action-risk thresholds enforced inside ``before_tool_callback``."""

    max_spend_usd: float | None
    require_approval_for_external_send: bool
    custom: dict


class RateLimits(BaseModel):
    """Per-persona rate limits enforced inside ``before_tool_callback``."""

    requests_per_minute: int | None
    tokens_per_day: int | None


class PersonaPolicy(BaseModel):
    """Resolved per-(user, persona) policy. Mirrors ``persona_policies`` rows.

    `allowed_tool_ids` may be the literal string ``"*"`` to mean *no allow-list*
    (deny-only mode), matching the JSONB default in the table DDL.
    """

    persona_id: str
    allowed_tool_ids: list[str] | Literal["*"]
    denied_tool_ids: list[str]
    action_thresholds: ActionThresholds
    rate_limits: RateLimits
    prompt_fragments: list[str]
    classifier_default_mode: Mode | None
    initiative_phases_blocked: list[str]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_types_persona_policy.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/types.py tests/unit/agents/runtime/test_types_persona_policy.py
git commit -m "feat(runtime): add persona-policy contracts"
```

---

### Task 15: `runtime/types.py` — ClassifierResult

**Files:**
- Edit: `app/agents/runtime/types.py`
- Test: `tests/unit/agents/runtime/test_types_classifier.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_types_classifier.py
"""ClassifierResult — output of runtime/task_router.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_classifier_result_override():
    from app.agents.runtime.types import ClassifierResult

    r = ClassifierResult(
        mode="direct",
        confidence=1.0,
        reasoning="User typed /quick prefix.",
        signal="override",
    )
    assert r.mode == "direct"
    assert r.signal == "override"


def test_classifier_result_llm_low_confidence():
    from app.agents.runtime.types import ClassifierResult

    r = ClassifierResult(
        mode="initiative",
        confidence=0.62,
        reasoning="Verbs 'plan' and 'launch' present.",
        signal="llm",
    )
    assert r.signal == "llm"


def test_classifier_result_rejects_invalid_signal():
    from app.agents.runtime.types import ClassifierResult

    with pytest.raises(ValidationError):
        ClassifierResult(
            mode="direct",
            confidence=0.5,
            reasoning="",
            signal="vibes",  # type: ignore[arg-type]
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_types_classifier.py -v
```

Expected: FAIL — `ClassifierResult` missing.

- [ ] **Step 3: Append the implementation**

```python
# app/agents/runtime/types.py  (append)


class ClassifierResult(BaseModel):
    """Output of :mod:`app.agents.runtime.task_router`.

    `signal` records which of the three layers (override, rule heuristics,
    LLM fallback) produced the decision — used for tuning.
    """

    mode: Mode
    confidence: float
    reasoning: str
    signal: Literal["override", "rule", "llm"]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_types_classifier.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/types.py tests/unit/agents/runtime/test_types_classifier.py
git commit -m "feat(runtime): add ClassifierResult contract"
```

---

### Task 16: `runtime/types.py` — WorkspaceProgressEvent + WorkspaceArtifactEvent

**Files:**
- Edit: `app/agents/runtime/types.py`
- Test: `tests/unit/agents/runtime/test_types_workspace_events.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_types_workspace_events.py
"""Workspace SSE event shapes (publication sink → ActiveWorkspace)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError


def test_progress_event_started():
    from app.agents.runtime.types import WorkspaceProgressEvent

    cid = uuid4()
    evt = WorkspaceProgressEvent(
        agent_id="FIN",
        contract_id=cid,
        item="Outline forecast",
        status="started",
    )
    assert evt.kind == "progress"
    assert evt.contract_id == cid


def test_progress_event_rejects_bad_status():
    from app.agents.runtime.types import WorkspaceProgressEvent

    with pytest.raises(ValidationError):
        WorkspaceProgressEvent(
            agent_id="FIN",
            contract_id=None,
            item="x",
            status="finished",  # type: ignore[arg-type]
        )


def test_artifact_event_video_render_with_preview():
    from app.agents.runtime.types import WorkspaceArtifactEvent

    evt = WorkspaceArtifactEvent(
        agent_id="CONT",
        contract_id=uuid4(),
        artifact_kind="video_render",
        ref="vault://videos/abc.mp4",
        summary="60s demo",
        preview_url="https://cdn.pikar/abc.png",
    )
    assert evt.kind == "artifact"
    assert evt.artifact_kind == "video_render"


def test_artifact_event_preview_optional():
    from app.agents.runtime.types import WorkspaceArtifactEvent

    evt = WorkspaceArtifactEvent(
        agent_id="DATA",
        contract_id=None,
        artifact_kind="data_query",
        ref="bq://result/42",
        summary="98 rows",
        preview_url=None,
    )
    assert evt.preview_url is None


def test_progress_event_default_kind_is_locked():
    """`kind` is a Literal default; model must not accept a different value."""
    from app.agents.runtime.types import WorkspaceProgressEvent

    with pytest.raises(ValidationError):
        WorkspaceProgressEvent(
            kind="artifact",  # type: ignore[arg-type]
            agent_id="FIN",
            contract_id=None,
            item="x",
            status="started",
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_types_workspace_events.py -v
```

Expected: FAIL — workspace event models missing.

- [ ] **Step 3: Append the implementation**

```python
# app/agents/runtime/types.py  (append)


class WorkspaceProgressEvent(BaseModel):
    """Progress tick emitted to the per-user workspace SSE channel."""

    kind: Literal["progress"] = "progress"
    agent_id: str
    contract_id: UUID | None
    item: str
    status: Literal["started", "in_progress", "blocked"]


class WorkspaceArtifactEvent(BaseModel):
    """Artifact event emitted whenever ``publish_artifact`` produces output.

    `artifact_kind` is open-ended on purpose: known values include
    ``"video_render"``, ``"image"``, ``"doc"``, ``"report"``, ``"data_query"``.
    """

    kind: Literal["artifact"] = "artifact"
    agent_id: str
    contract_id: UUID | None
    artifact_kind: str
    ref: str
    summary: str
    preview_url: str | None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_types_workspace_events.py -v
```

Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/types.py tests/unit/agents/runtime/test_types_workspace_events.py
git commit -m "feat(runtime): add workspace SSE event contracts"
```

---

### Task 17: `runtime/operations_config.py` — nested models + defaults + `load`

**Files:**
- Create: `app/agents/runtime/operations_config.py`
- Create: `tests/unit/agents/runtime/fixtures/operations_minimal.yaml`
- Create: `tests/unit/agents/runtime/fixtures/operations_financial.yaml`
- Test: `tests/unit/agents/runtime/test_operations_config.py`

- [ ] **Step 1: Write the failing test + fixtures**

```yaml
# tests/unit/agents/runtime/fixtures/operations_minimal.yaml
agent_id: minimal
```

```yaml
# tests/unit/agents/runtime/fixtures/operations_financial.yaml
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
  allowed_ids:
    - "finance:*"
    - "data:*"
    - "compliance:legal-risk-assessment"
  injection:
    top_k: 5
    similarity_floor: 0.65
initiative:
  phases_owned:
    - validation
    - build
  can_advance_phase: true
  can_close: false
memory:
  history_retention_months: 18
  retrieval_top_k: 4
compaction:
  trigger_token_count: 80000
  keep_last_n_turns: 12
routing:
  last_resort_default: initiative
```

```python
# tests/unit/agents/runtime/test_operations_config.py
"""OperationsConfig — strict per-agent YAML schema with sensible defaults."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

FIX = Path(__file__).parent / "fixtures"


def test_minimal_yaml_loads_with_defaults():
    from app.agents.runtime.operations_config import OperationsConfig

    cfg = OperationsConfig.load(FIX / "operations_minimal.yaml")

    assert cfg.agent_id == "minimal"
    # Sensible defaults must be populated so simple agents need almost no YAML.
    assert cfg.model.primary == "gemini-2.5-pro"
    assert cfg.model.fallback == "gemini-2.5-flash"
    assert cfg.retry.max_attempts == 5
    assert cfg.research.max_iterations == 3
    assert cfg.skills.injection.top_k == 5
    assert 0 < cfg.skills.injection.similarity_floor <= 1
    assert cfg.compaction.trigger_token_count > 0
    assert cfg.initiative.can_close is False
    assert cfg.routing.last_resort_default in ("direct", "initiative")


def test_financial_yaml_overrides_defaults():
    from app.agents.runtime.operations_config import OperationsConfig

    cfg = OperationsConfig.load(FIX / "operations_financial.yaml")

    assert cfg.agent_id == "financial"
    assert cfg.approval.required_above_usd == 1000
    assert cfg.approval.required_for_external_send is True
    assert "finance:*" in cfg.skills.allowed_ids
    assert cfg.initiative.phases_owned == ["validation", "build"]
    assert cfg.initiative.can_advance_phase is True
    assert cfg.memory.history_retention_months == 18


def test_missing_agent_id_fails_fast(tmp_path):
    from app.agents.runtime.operations_config import OperationsConfig

    bad = tmp_path / "bad.yaml"
    bad.write_text("model:\n  primary: gemini-2.5-flash\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        OperationsConfig.load(bad)


def test_unknown_top_level_key_fails_fast(tmp_path):
    from app.agents.runtime.operations_config import OperationsConfig

    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "agent_id: x\nmystery_section:\n  foo: bar\n", encoding="utf-8"
    )

    with pytest.raises(ValidationError):
        OperationsConfig.load(bad)


def test_routing_default_rejects_bad_value(tmp_path):
    from app.agents.runtime.operations_config import OperationsConfig

    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "agent_id: x\nrouting:\n  last_resort_default: shrug\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        OperationsConfig.load(bad)


def test_load_missing_file_raises_file_not_found():
    from app.agents.runtime.operations_config import OperationsConfig

    with pytest.raises(FileNotFoundError):
        OperationsConfig.load(Path("/nonexistent/operations.yaml"))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_operations_config.py -v
```

Expected: FAIL — `app.agents.runtime.operations_config` not found.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/operations_config.py
# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Per-agent declarative tunables (`operations.yaml`).

Loaded once when an agent factory builds the agent. Malformed config
fails fast — the agent does not load. Defaults mirror spec § 15.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.agents.runtime.types import Mode

_StrictModel = ConfigDict(extra="forbid")


class ModelConfig(BaseModel):
    model_config = _StrictModel

    primary: str = "gemini-2.5-pro"
    fallback: str = "gemini-2.5-flash"


class RetryConfig(BaseModel):
    model_config = _StrictModel

    max_attempts: int = 5
    backoff_initial_s: float = 2.0
    backoff_multiplier: float = 2.0
    backoff_max_s: float = 60.0


class ApprovalConfig(BaseModel):
    model_config = _StrictModel

    required_above_usd: float | None = None
    required_for_external_send: bool = False


class ResearchConfig(BaseModel):
    model_config = _StrictModel

    max_iterations: int = 3
    required_source_min: int = 3


class AuditConfig(BaseModel):
    model_config = _StrictModel

    fail_on_any_unmet_criterion: bool = True
    escalate_on_partial: bool = False


class SkillsInjectionConfig(BaseModel):
    model_config = _StrictModel

    top_k: int = 5
    similarity_floor: float = 0.65


class SkillsConfig(BaseModel):
    model_config = _StrictModel

    allowed_ids: list[str] = Field(default_factory=list)
    injection: SkillsInjectionConfig = Field(default_factory=SkillsInjectionConfig)


class InitiativeConfig(BaseModel):
    model_config = _StrictModel

    phases_owned: list[str] = Field(default_factory=list)
    can_advance_phase: bool = False
    can_close: bool = False


class MemoryConfig(BaseModel):
    model_config = _StrictModel

    history_retention_months: int = 18
    retrieval_top_k: int = 4


class CompactionConfig(BaseModel):
    model_config = _StrictModel

    trigger_token_count: int = 80_000
    keep_last_n_turns: int = 12


class RoutingConfig(BaseModel):
    model_config = _StrictModel

    last_resort_default: Mode = "initiative"


class OperationsConfig(BaseModel):
    """Top-level operations.yaml schema. ``extra='forbid'`` on every layer
    so a typo in the YAML fails fast instead of silently defaulting.
    """

    model_config = _StrictModel

    agent_id: str
    model: ModelConfig = Field(default_factory=ModelConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    approval: ApprovalConfig = Field(default_factory=ApprovalConfig)
    research: ResearchConfig = Field(default_factory=ResearchConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    initiative: InitiativeConfig = Field(default_factory=InitiativeConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    compaction: CompactionConfig = Field(default_factory=CompactionConfig)
    routing: RoutingConfig = Field(default_factory=RoutingConfig)

    @classmethod
    def load(cls, path: Path) -> "OperationsConfig":
        """Load + validate operations.yaml at ``path``.

        Raises ``FileNotFoundError`` if missing; ``pydantic.ValidationError``
        if malformed. No defaults at the top level — at least ``agent_id``
        must be present.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"operations.yaml not found at {path}")
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return cls.model_validate(data)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_operations_config.py -v
```

Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/operations_config.py tests/unit/agents/runtime/test_operations_config.py tests/unit/agents/runtime/fixtures/operations_minimal.yaml tests/unit/agents/runtime/fixtures/operations_financial.yaml
git commit -m "feat(runtime): add OperationsConfig loader with strict defaults"
```

---

### Task 18: `runtime/lifecycle.py` — callback factory stubs

**Files:**
- Create: `app/agents/runtime/lifecycle.py`
- Test: `tests/unit/agents/runtime/test_lifecycle_stubs.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_lifecycle_stubs.py
"""Lifecycle callback factories — Section A stubs only.

These functions must exist and return callables so PikarBaseAgent can wire
them. Their bodies are owned by Section B; here we only check the shape.
"""

from __future__ import annotations

from unittest.mock import MagicMock


def test_before_agent_returns_callable():
    from app.agents.runtime import lifecycle

    agent = MagicMock(name="PikarBaseAgent")
    cb = lifecycle.before_agent(agent)
    assert callable(cb)


def test_before_tool_returns_callable():
    from app.agents.runtime import lifecycle

    agent = MagicMock(name="PikarBaseAgent")
    cb = lifecycle.before_tool(agent)
    assert callable(cb)


def test_after_tool_returns_callable():
    from app.agents.runtime import lifecycle

    agent = MagicMock(name="PikarBaseAgent")
    cb = lifecycle.after_tool(agent)
    assert callable(cb)


def test_after_agent_returns_callable():
    from app.agents.runtime import lifecycle

    agent = MagicMock(name="PikarBaseAgent")
    cb = lifecycle.after_agent(agent)
    assert callable(cb)


def test_stub_callables_are_safe_to_invoke():
    """Stubs must be no-ops so the BaseAgent skeleton boots in Section A.

    Section B will replace each body with real enforcement logic.
    """
    from app.agents.runtime import lifecycle

    agent = MagicMock(name="PikarBaseAgent")
    for factory in (
        lifecycle.before_agent,
        lifecycle.before_tool,
        lifecycle.after_tool,
        lifecycle.after_agent,
    ):
        cb = factory(agent)
        # Each stub accepts arbitrary kwargs (ADK passes ctx, request, etc.)
        # and returns None without raising.
        assert cb(callback_context=MagicMock()) is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_lifecycle_stubs.py -v
```

Expected: FAIL — `app.agents.runtime.lifecycle` not found.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/lifecycle.py
# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""ADK lifecycle callback factories.

Section A scope: stubs only — every factory returns a no-op callable so the
:class:`~app.agents.base_agent.PikarBaseAgent` skeleton can wire its hooks.
Section B replaces these bodies with the real enforcement stack
(skill injection, research gate, persona gate, audit, compaction, ...).

The factory pattern (``before_agent(agent) -> callable``) is what binds the
callback to a specific agent instance — needed because ADK passes only the
:class:`CallbackContext`, not the agent, into the callback itself.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def _noop(*_args: Any, **_kwargs: Any) -> None:  # pragma: no cover - trivial
    return None


def before_agent(agent: Any) -> Callable[..., Any]:
    """Section B will implement: task router, skill injection, memory layer-3,
    persona prompt fragments, initiative-context loading, ops-config fail-fast.
    """
    del agent  # bound in Section B
    return _noop


def before_tool(agent: Any) -> Callable[..., Any]:
    """Section B will implement: persona allow/deny, action thresholds,
    research gate, approval-token check.
    """
    del agent
    return _noop


def after_tool(agent: Any) -> Callable[..., Any]:
    """Section B will implement: capture structured outputs, close research
    gate on completion, log tool failures, emit workspace progress events.
    """
    del agent
    return _noop


def after_agent(agent: Any) -> Callable[..., Any]:
    """Section B will implement: self-audit on artifact-producing turns,
    compaction trigger, persist outcome to ``agent_task_executions``.
    """
    del agent
    return _noop
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_lifecycle_stubs.py -v
```

Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/lifecycle.py tests/unit/agents/runtime/test_lifecycle_stubs.py
git commit -m "feat(runtime): scaffold lifecycle callback factories (stubs)"
```

---

### Task 19: `PikarBaseAgent` skeleton — constructor wiring + abstract methods

**Files:**
- Edit: `app/agents/base_agent.py`
- Test: `tests/unit/agents/test_base_agent_skeleton.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/test_base_agent_skeleton.py
"""PikarBaseAgent — Section A skeleton only.

Verifies the constructor loads OperationsConfig, persists agent_id /
user_id / persona_id, hooks all four ADK callbacks (factories from
runtime.lifecycle), and exposes the five abstract methods (bodies in B/C/D).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

# Stub the ADK surface like other unit tests do — see test_agent_memory_callback.
sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.agents.callback_context", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())


def _ops_yaml(tmp_path: Path) -> Path:
    path = tmp_path / "operations.yaml"
    path.write_text("agent_id: financial\n", encoding="utf-8")
    return path


def _instructions_md(tmp_path: Path) -> Path:
    path = tmp_path / "instructions.md"
    path.write_text("You are the Financial Analysis Agent.", encoding="utf-8")
    return path


class _FakeToolsManifest:
    def resolve(self):
        return []


def test_constructor_loads_ops_config_and_persists_identity(tmp_path):
    from app.agents.base_agent import PikarBaseAgent
    from app.skills.registry import AgentID

    uid = uuid4()
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None) as parent:
        agent = PikarBaseAgent(
            agent_id=AgentID.FIN,
            instructions_path=_instructions_md(tmp_path),
            tools_manifest=_FakeToolsManifest(),
            ops_config_path=_ops_yaml(tmp_path),
            user_id=uid,
            persona_id="founder",
        )

    assert agent.agent_id == AgentID.FIN
    assert agent.user_id == uid
    assert agent.persona_id == "founder"
    assert agent.ops.agent_id == "financial"
    assert parent.called


def test_constructor_wires_all_four_lifecycle_callbacks(tmp_path):
    from app.agents import base_agent
    from app.agents.base_agent import PikarBaseAgent
    from app.skills.registry import AgentID

    sentinels = {
        "before_agent": MagicMock(name="ba"),
        "before_tool": MagicMock(name="bt"),
        "after_tool": MagicMock(name="at"),
        "after_agent": MagicMock(name="aa"),
    }
    with (
        patch.object(base_agent.lifecycle, "before_agent", return_value=sentinels["before_agent"]),
        patch.object(base_agent.lifecycle, "before_tool", return_value=sentinels["before_tool"]),
        patch.object(base_agent.lifecycle, "after_tool", return_value=sentinels["after_tool"]),
        patch.object(base_agent.lifecycle, "after_agent", return_value=sentinels["after_agent"]),
        patch("app.agents.base_agent.PikarAgent.__init__", return_value=None) as parent,
    ):
        PikarBaseAgent(
            agent_id=AgentID.FIN,
            instructions_path=_instructions_md(tmp_path),
            tools_manifest=_FakeToolsManifest(),
            ops_config_path=_ops_yaml(tmp_path),
            user_id=uuid4(),
            persona_id="founder",
        )

    kwargs = parent.call_args.kwargs
    assert kwargs["before_agent_callback"] is sentinels["before_agent"]
    assert kwargs["before_tool_callback"] is sentinels["before_tool"]
    assert kwargs["after_tool_callback"] is sentinels["after_tool"]
    assert kwargs["after_agent_callback"] is sentinels["after_agent"]


def test_constructor_reads_instructions_markdown(tmp_path):
    from app.agents.base_agent import PikarBaseAgent
    from app.skills.registry import AgentID

    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None) as parent:
        PikarBaseAgent(
            agent_id=AgentID.FIN,
            instructions_path=_instructions_md(tmp_path),
            tools_manifest=_FakeToolsManifest(),
            ops_config_path=_ops_yaml(tmp_path),
            user_id=uuid4(),
            persona_id="founder",
        )

    instruction = parent.call_args.kwargs["instruction"]
    assert "Financial Analysis Agent" in instruction


def test_five_abstract_methods_raise_until_section_b_c_d(tmp_path):
    """The class skeleton declares the five methods but does not implement
    them — calls must raise NotImplementedError so a half-migrated agent
    fails loudly rather than silently no-op."""
    import asyncio
    from app.agents.base_agent import PikarBaseAgent
    from app.skills.registry import AgentID

    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = PikarBaseAgent(
            agent_id=AgentID.FIN,
            instructions_path=_instructions_md(tmp_path),
            tools_manifest=_FakeToolsManifest(),
            ops_config_path=_ops_yaml(tmp_path),
            user_id=uuid4(),
            persona_id="founder",
        )

    async def _run():
        import pytest

        with pytest.raises(NotImplementedError):
            await agent.respond_directly(request=MagicMock())
        with pytest.raises(NotImplementedError):
            await agent.execute_task(contract=MagicMock())
        with pytest.raises(NotImplementedError):
            await agent.start_initiative(
                goal="x", success_criteria=[], owners=[AgentID.FIN]
            )
        with pytest.raises(NotImplementedError):
            await agent.advance_phase(initiative_id=uuid4(), current_phase="ideation")
        with pytest.raises(NotImplementedError):
            await agent.close_initiative(initiative_id=uuid4())

    asyncio.run(_run())


def test_legacy_pikar_agent_still_exported():
    """Backward-compat: existing factories import PikarAgent. Must keep working."""
    from app.agents.base_agent import PikarAgent

    assert PikarAgent is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/test_base_agent_skeleton.py -v
```

Expected: FAIL — `PikarBaseAgent` not defined.

- [ ] **Step 3: Replace `base_agent.py` with the extended skeleton**

```python
# app/agents/base_agent.py
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""PikarAgent + PikarBaseAgent.

`PikarAgent` is the legacy ADK-path-resolution shim — kept verbatim so the
existing factory functions continue to work throughout the wave-based
migration (see project_v12_agent_quality_upgrade.md for the proven pattern).

`PikarBaseAgent` is the new Section-A skeleton:
  * loads :class:`~app.agents.runtime.operations_config.OperationsConfig`
  * carries identity (agent_id, user_id, persona_id)
  * wires all four ADK lifecycle hooks via factories in
    :mod:`app.agents.runtime.lifecycle` (Section A stubs; Section B replaces
    the bodies)
  * declares the five public methods (`respond_directly`, `execute_task`,
    `start_initiative`, `advance_phase`, `close_initiative`) as
    `NotImplementedError` placeholders so a half-migrated agent fails loudly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from google.adk.agents import Agent as BaseAgent

from app.agents.runtime import lifecycle
from app.agents.runtime.operations_config import OperationsConfig
from app.skills.registry import AgentID


class PikarAgent(BaseAgent):
    """Legacy ADK-path-resolution shim. Kept for backward compatibility."""

    pass


class ToolsManifest(Protocol):
    """Anything that knows how to materialize the agent's tool callables."""

    def resolve(self) -> list[Any]: ...


class PikarBaseAgent(PikarAgent):
    """Section A skeleton — full responsibilities defined in spec § 5.

    Constructor responsibilities (this file):
      1. Load and validate ``operations.yaml`` (fail fast on schema error).
      2. Read ``instructions.md`` and pass it through to the parent
         ``instruction=`` field.
      3. Resolve the tool manifest.
      4. Wire all four ADK lifecycle hooks via
         :mod:`app.agents.runtime.lifecycle` factories.

    Section B owns the bodies of the lifecycle callbacks.
    Section C/D own ``execute_task``, ``respond_directly``, the three
    initiative ritual methods, and the publication / handoff plumbing.
    """

    def __init__(
        self,
        *,
        agent_id: AgentID,
        instructions_path: Path,
        tools_manifest: ToolsManifest,
        ops_config_path: Path,
        user_id: UUID,
        persona_id: str,
        **extra: Any,
    ) -> None:
        self.agent_id = agent_id
        self.user_id = user_id
        self.persona_id = persona_id
        self.ops: OperationsConfig = OperationsConfig.load(ops_config_path)

        instruction = Path(instructions_path).read_text(encoding="utf-8")
        tools = tools_manifest.resolve()

        super().__init__(
            name=agent_id.value,
            instruction=instruction,
            tools=tools,
            before_agent_callback=lifecycle.before_agent(self),
            before_tool_callback=lifecycle.before_tool(self),
            after_tool_callback=lifecycle.after_tool(self),
            after_agent_callback=lifecycle.after_agent(self),
            **extra,
        )

    # ------------------------------------------------------------------
    # Public surface — bodies live in Sections B / C / D.
    # ------------------------------------------------------------------

    async def respond_directly(self, request: Any) -> Any:
        """Direct-mode turn. Implemented in Section C."""
        raise NotImplementedError(
            "PikarBaseAgent.respond_directly is implemented in Section C."
        )

    async def execute_task(self, contract: Any) -> Any:
        """Initiative-mode TaskContract execution. Implemented in Section B."""
        raise NotImplementedError(
            "PikarBaseAgent.execute_task is implemented in Section B."
        )

    async def start_initiative(
        self,
        *,
        goal: str,
        success_criteria: list[str],
        owners: list[AgentID],
        phase: str = "ideation",
        **kwargs: Any,
    ) -> Any:
        """Implemented in Section D (initiative rituals)."""
        raise NotImplementedError(
            "PikarBaseAgent.start_initiative is implemented in Section D."
        )

    async def advance_phase(
        self, initiative_id: UUID, current_phase: str
    ) -> Any:
        """Implemented in Section D."""
        raise NotImplementedError(
            "PikarBaseAgent.advance_phase is implemented in Section D."
        )

    async def close_initiative(self, initiative_id: UUID) -> Any:
        """Implemented in Section D."""
        raise NotImplementedError(
            "PikarBaseAgent.close_initiative is implemented in Section D."
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/test_base_agent_skeleton.py -v
```

Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/base_agent.py tests/unit/agents/test_base_agent_skeleton.py
git commit -m "feat(agents): add PikarBaseAgent skeleton with lifecycle wiring"
```

---

### Task 20: Section A integration check — ops_config exposed on a constructed PikarBaseAgent

**Files:**
- Test: `tests/unit/agents/test_base_agent_ops_integration.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/test_base_agent_ops_integration.py
"""End-to-end smoke for Section A:

A constructed PikarBaseAgent exposes a fully-validated OperationsConfig,
the lifecycle callbacks are wired (stubs are safely callable), and the
NotImplementedError stubs reference the correct downstream section.
This is the final gate before Section B starts adding logic.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.agents.callback_context", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())

FIN_YAML = """\
agent_id: financial
model:
  primary: gemini-2.5-pro
  fallback: gemini-2.5-flash
research:
  max_iterations: 3
  required_source_min: 3
skills:
  allowed_ids: ["finance:*"]
  injection:
    top_k: 5
    similarity_floor: 0.65
initiative:
  phases_owned: ["validation", "build"]
  can_advance_phase: true
  can_close: false
"""


class _Manifest:
    def resolve(self):
        return []


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_pikar_base_agent_exposes_validated_ops(tmp_path):
    from app.agents.base_agent import PikarBaseAgent
    from app.agents.runtime.operations_config import OperationsConfig
    from app.skills.registry import AgentID

    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = PikarBaseAgent(
            agent_id=AgentID.FIN,
            instructions_path=_write(tmp_path, "instructions.md", "Hi."),
            tools_manifest=_Manifest(),
            ops_config_path=_write(tmp_path, "operations.yaml", FIN_YAML),
            user_id=uuid4(),
            persona_id="founder",
        )

    assert isinstance(agent.ops, OperationsConfig)
    assert agent.ops.agent_id == "financial"
    assert agent.ops.initiative.phases_owned == ["validation", "build"]
    assert agent.ops.skills.injection.top_k == 5


def test_pikar_base_agent_lifecycle_stubs_are_safe(tmp_path):
    """Section B has not landed yet — the stub callbacks must be no-ops so a
    fully-constructed agent does not blow up if ADK invokes them."""
    from app.agents.base_agent import PikarBaseAgent
    from app.skills.registry import AgentID

    captured: dict[str, object] = {}

    def fake_parent_init(self, **kwargs):
        captured.update(kwargs)

    with patch(
        "app.agents.base_agent.PikarAgent.__init__",
        fake_parent_init,
    ):
        PikarBaseAgent(
            agent_id=AgentID.FIN,
            instructions_path=_write(tmp_path, "instructions.md", "Hi."),
            tools_manifest=_Manifest(),
            ops_config_path=_write(tmp_path, "operations.yaml", FIN_YAML),
            user_id=uuid4(),
            persona_id="founder",
        )

    for key in (
        "before_agent_callback",
        "before_tool_callback",
        "after_tool_callback",
        "after_agent_callback",
    ):
        cb = captured[key]
        assert callable(cb), f"{key} must be callable"
        assert cb(callback_context=MagicMock()) is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/test_base_agent_ops_integration.py -v
```

Expected: FAIL until both Task 17 (`OperationsConfig`) and Task 19 (`PikarBaseAgent`) are in place — at this point in the sequence they are, so this test exists to confirm Section A holds together as a single unit before Section B begins.

- [ ] **Step 3: Wire the missing piece — re-export `OperationsConfig` from the runtime package**

```python
# app/agents/runtime/__init__.py  (replace contents)
# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Runtime support package for PikarBaseAgent.

Re-exports the small set of names that Section B/C/D will reach for first:
  - OperationsConfig: loaded by PikarBaseAgent.__init__
  - lifecycle: callback factories wired by PikarBaseAgent

Heavy submodules (types, research_gate, persona_gate, etc.) are NOT
imported here — consumers reach for them with explicit
``from app.agents.runtime.types import TaskContract``.
"""

from app.agents.runtime import lifecycle as lifecycle
from app.agents.runtime.operations_config import OperationsConfig as OperationsConfig

__all__ = ["OperationsConfig", "lifecycle"]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/test_base_agent_ops_integration.py tests/unit/agents/runtime/ -v
```

Expected: PASS — Section A integration green; full runtime suite green.

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/__init__.py tests/unit/agents/test_base_agent_ops_integration.py
git commit -m "test(runtime): add Section A integration smoke + re-export OperationsConfig"
```

---

## Section B — Lifecycle hooks, skill injection, memory, handoff, compaction (Tasks 21–45)

This section owns the runtime callbacks and the four delegated modules: skill injection, memory retrieval, handoff, and compaction. Section A defines the `PikarBaseAgent` wiring and the `runtime/types.py` + `runtime/operations_config.py` contracts; Section C owns `task_router`, `persona_gate`, `research_gate`, and `audit`; Section D owns `publication`. All callbacks delegate; this section never embeds logic that belongs to those modules.

ADK signatures used here:
- `before_agent_callback(callback_context: CallbackContext) -> types.Content | None`
- `before_tool_callback(tool: BaseTool, args: dict, tool_context: ToolContext) -> dict | None`
- `after_tool_callback(tool: BaseTool, args: dict, tool_context: ToolContext, tool_response: dict) -> dict | None`
- `after_agent_callback(callback_context: CallbackContext) -> types.Content | None`

Each unit test stubs `google.adk` / `google.genai` the same way `tests/unit/test_agent_memory_callback.py` already does, and patches `app.skills.skill_embeddings`, `app.services.knowledge_service`, and `app.services.supabase_client` so no live services are required.

---

### Task 21: Create `runtime/` package and lifecycle scaffold

**Files:**
- Create: `app/agents/runtime/__init__.py`
- Create: `app/agents/runtime/lifecycle.py`
- Test: `tests/unit/runtime/test_lifecycle_scaffold.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_lifecycle_scaffold.py
"""Lifecycle factory functions exist and return callables."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.agents.callback_context", MagicMock())
sys.modules.setdefault("google.adk.tools", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())


def test_lifecycle_exposes_four_factories():
    from app.agents.runtime import lifecycle

    assert callable(lifecycle.before_agent)
    assert callable(lifecycle.before_tool)
    assert callable(lifecycle.after_tool)
    assert callable(lifecycle.after_agent)


def test_factories_return_callables():
    from app.agents.runtime import lifecycle

    agent = MagicMock()
    agent.agent_id = MagicMock(value="FIN")
    agent.ops = MagicMock()

    for factory in (
        lifecycle.before_agent,
        lifecycle.before_tool,
        lifecycle.after_tool,
        lifecycle.after_agent,
    ):
        cb = factory(agent)
        assert callable(cb), f"{factory.__name__} must return a callable"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_lifecycle_scaffold.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.agents.runtime'`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/__init__.py
"""Runtime package — lifecycle hooks and shared enforcement modules.

Each submodule owns one slice of the operating model:
* lifecycle.py        — the four ADK callbacks
* skill_injection.py  — semantic skill matching + prompt injection
* memory_retrieval.py — Layer-3 vault retrieval at task start
* handoff.py          — cross-agent handoff recording
* compaction.py       — session compaction trigger

Other submodules (task_router, persona_gate, research_gate, audit,
publication) are owned by sibling implementation sections but imported
here by lifecycle.py.
"""

from __future__ import annotations

__all__: list[str] = []
```

```python
# app/agents/runtime/lifecycle.py
"""ADK lifecycle callbacks for PikarBaseAgent.

Each public function is a *factory*: it takes the agent instance and
returns the actual callback the ADK runtime will invoke. The factory
shape lets each callback close over ``agent`` (and therefore over
``agent.ops``, ``agent.agent_id``, etc.) without smuggling globals.

Bodies delegate to the runtime submodules (skill_injection,
memory_retrieval, task_router, persona_gate, research_gate, audit,
publication, compaction). No business logic lives in this file — only
ordering, error translation, and defensive try/except wrapping so a
callback never crashes a real agent run.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from app.agents.base_agent import PikarBaseAgent


def before_agent(agent: "PikarBaseAgent") -> Callable[[Any], Any]:
    """Return the ADK before_agent_callback bound to ``agent``."""

    def _callback(callback_context: Any) -> None:
        return None

    _callback.__name__ = f"before_agent::{agent.agent_id.value}"
    return _callback


def before_tool(agent: "PikarBaseAgent") -> Callable[..., Any]:
    """Return the ADK before_tool_callback bound to ``agent``."""

    def _callback(tool: Any, args: dict[str, Any], tool_context: Any) -> Any:
        return None

    _callback.__name__ = f"before_tool::{agent.agent_id.value}"
    return _callback


def after_tool(agent: "PikarBaseAgent") -> Callable[..., Any]:
    """Return the ADK after_tool_callback bound to ``agent``."""

    def _callback(
        tool: Any,
        args: dict[str, Any],
        tool_context: Any,
        tool_response: dict[str, Any],
    ) -> Any:
        return None

    _callback.__name__ = f"after_tool::{agent.agent_id.value}"
    return _callback


def after_agent(agent: "PikarBaseAgent") -> Callable[[Any], Any]:
    """Return the ADK after_agent_callback bound to ``agent``."""

    def _callback(callback_context: Any) -> None:
        return None

    _callback.__name__ = f"after_agent::{agent.agent_id.value}"
    return _callback


__all__ = ["before_agent", "before_tool", "after_tool", "after_agent"]
```

Also create the tests directory marker:

```python
# tests/unit/runtime/__init__.py
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_lifecycle_scaffold.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/__init__.py app/agents/runtime/lifecycle.py tests/unit/runtime/__init__.py tests/unit/runtime/test_lifecycle_scaffold.py
git commit -m "feat(runtime): scaffold runtime package with four lifecycle factories"
```

---

### Task 22: Skill injection — module skeleton + render helper

**Files:**
- Create: `app/agents/runtime/skill_injection.py`
- Test: `tests/unit/runtime/test_skill_injection_render.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_skill_injection_render.py
"""Render helper formats matched skills as a markdown block."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())


def test_render_section_with_skills():
    from app.agents.runtime.skill_injection import SkillMatch, _render_section
    from app.skills.registry import Skill

    matches = [
        SkillMatch(
            score=0.91,
            skill=Skill(
                name="financial_modeling",
                description="DCF, NPV, IRR modeling",
                category="finance",
                knowledge_summary="Use 5-year horizon; sensitivity on WACC.",
            ),
        ),
        SkillMatch(
            score=0.74,
            skill=Skill(
                name="variance_analysis",
                description="Budget vs actuals investigation",
                category="finance",
                knowledge_summary="Decompose price/volume/mix.",
            ),
        ),
    ]
    out = _render_section(matches)
    assert "## Relevant skills" in out
    assert "financial_modeling" in out
    assert "variance_analysis" in out
    assert "0.91" in out
    assert "DCF, NPV, IRR modeling" in out
    assert "Use 5-year horizon" in out


def test_render_section_empty_returns_empty_string():
    from app.agents.runtime.skill_injection import _render_section

    assert _render_section([]) == ""
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_skill_injection_render.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.agents.runtime.skill_injection'`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/skill_injection.py
"""Semantic skill matching + prompt injection for before_agent_callback.

The matcher reuses ``app.skills.skill_embeddings`` (the warmed in-memory
cosine cache) so no new vector infrastructure ships here. The output is
a markdown block prepended to the agent's instruction by lifecycle.py.

Filter chain (applied to candidates):
1. cosine score >= ``similarity_floor``;
2. ``agent_id`` is in ``skill.agent_ids`` (or skill targets all agents);
3. ``skill.name`` is allowed by ``ops.skills.allowed_ids`` (``"*"`` or
   glob-style prefix patterns like ``"finance:*"``).
"""

from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.skills.registry import Skill

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from app.agents.base_agent import PikarBaseAgent
    from app.agents.runtime.types import DirectRequest, TaskContract


@dataclass
class SkillMatch:
    """A scored skill candidate returned by the matcher."""

    score: float
    skill: Skill


def _matches_any(skill_name: str, patterns: list[str]) -> bool:
    """Return True if ``skill_name`` matches any glob pattern in ``patterns``."""
    if not patterns:
        return False
    if "*" in patterns:
        return True
    return any(fnmatch.fnmatchcase(skill_name, p) for p in patterns)


def _render_section(matches: list[SkillMatch]) -> str:
    """Render matched skills as a markdown ``## Relevant skills`` block."""
    if not matches:
        return ""
    lines: list[str] = ["## Relevant skills", ""]
    for m in matches:
        summary = (m.skill.knowledge_summary or m.skill.description or "").strip()
        lines.append(
            f"- **{m.skill.name}** (score {m.score:.2f}, {m.skill.category}): "
            f"{m.skill.description}"
        )
        if summary and summary != m.skill.description:
            lines.append(f"  - {summary}")
    lines.append("")
    lines.append(
        "Call `use_skill(name)` for the full guidance when needed."
    )
    return "\n".join(lines)


async def match_and_inject(
    request: "TaskContract | DirectRequest",
    agent: "PikarBaseAgent",
    *,
    top_k: int = 5,
    similarity_floor: float = 0.65,
) -> str:
    """Return a markdown ``Relevant skills`` block for the given request.

    Returns the empty string when no skills clear the threshold; callers
    can unconditionally prepend the result to a prompt.
    """
    # Implemented in Task 23.
    raise NotImplementedError


__all__ = ["SkillMatch", "match_and_inject"]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_skill_injection_render.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/skill_injection.py tests/unit/runtime/test_skill_injection_render.py
git commit -m "feat(runtime): add skill-injection render helper and SkillMatch dataclass"
```

---

### Task 23: Skill injection — `match_and_inject` against semantic registry

**Files:**
- Edit: `app/agents/runtime/skill_injection.py`
- Test: `tests/unit/runtime/test_skill_injection_match.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_skill_injection_match.py
"""match_and_inject queries skill_embeddings, filters, and renders."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import MagicMock, patch

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())

from app.skills.registry import AgentID, Skill


def _agent(allowed: list[str], top_k: int = 5, floor: float = 0.65) -> MagicMock:
    a = MagicMock()
    a.agent_id = AgentID.FIN
    a.ops.skills.allowed_ids = allowed
    a.ops.skills.injection.top_k = top_k
    a.ops.skills.injection.similarity_floor = floor
    return a


def _skill(name: str, agent_ids: list[AgentID] | None = None) -> Skill:
    return Skill(
        name=name,
        description=f"{name} description",
        category="finance",
        agent_ids=agent_ids or [],
    )


def _request(text: str) -> MagicMock:
    r = MagicMock()
    r.goal = text  # TaskContract.goal path
    r.message = text  # DirectRequest.message path
    return r


def test_match_and_inject_filters_by_floor_and_allowed_and_agent_ids():
    from app.agents.runtime import skill_injection

    s_pass = _skill("finance:dcf", agent_ids=[AgentID.FIN])
    s_low = _skill("finance:low", agent_ids=[AgentID.FIN])         # below floor
    s_wrong_agent = _skill("finance:other", agent_ids=[AgentID.HR])  # wrong agent
    s_disallowed = _skill("hr:bonus", agent_ids=[])                # not in allowed
    candidates = [
        {"score": 0.91, "skill": s_pass},
        {"score": 0.40, "skill": s_low},
        {"score": 0.80, "skill": s_wrong_agent},
        {"score": 0.85, "skill": s_disallowed},
    ]
    fake_registry = MagicMock()
    fake_registry.semantic_search.return_value = candidates

    agent = _agent(allowed=["finance:*"], top_k=5, floor=0.65)

    with patch.object(skill_injection, "skills_registry", fake_registry):
        out = asyncio.run(
            skill_injection.match_and_inject(_request("forecast Q3 revenue"), agent)
        )

    assert "finance:dcf" in out
    assert "finance:low" not in out, "score below floor must be dropped"
    assert "finance:other" not in out, "wrong agent_id must be dropped"
    assert "hr:bonus" not in out, "not in allowed_ids must be dropped"


def test_match_and_inject_empty_when_no_matches():
    from app.agents.runtime import skill_injection

    fake_registry = MagicMock()
    fake_registry.semantic_search.return_value = []

    agent = _agent(allowed=["*"])
    with patch.object(skill_injection, "skills_registry", fake_registry):
        out = asyncio.run(
            skill_injection.match_and_inject(_request("hello"), agent)
        )
    assert out == ""


def test_match_and_inject_respects_top_k():
    from app.agents.runtime import skill_injection

    candidates = [
        {"score": 0.95 - i * 0.01, "skill": _skill(f"finance:s{i}", [AgentID.FIN])}
        for i in range(10)
    ]
    fake_registry = MagicMock()
    fake_registry.semantic_search.return_value = candidates

    agent = _agent(allowed=["*"], top_k=3)
    with patch.object(skill_injection, "skills_registry", fake_registry):
        out = asyncio.run(
            skill_injection.match_and_inject(_request("a"), agent, top_k=3)
        )

    rendered = [n for n in (f"finance:s{i}" for i in range(10)) if n in out]
    assert len(rendered) == 3


def test_match_and_inject_wildcard_allowed_passes_everything():
    from app.agents.runtime import skill_injection

    s = _skill("anything:goes", agent_ids=[AgentID.FIN])
    fake_registry = MagicMock()
    fake_registry.semantic_search.return_value = [{"score": 0.8, "skill": s}]

    agent = _agent(allowed=["*"])
    with patch.object(skill_injection, "skills_registry", fake_registry):
        out = asyncio.run(
            skill_injection.match_and_inject(_request("hi"), agent)
        )
    assert "anything:goes" in out
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_skill_injection_match.py -v
```

Expected: FAIL — `match_and_inject` currently raises `NotImplementedError`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/skill_injection.py  (replace the NotImplementedError stub)
async def match_and_inject(
    request: "TaskContract | DirectRequest",
    agent: "PikarBaseAgent",
    *,
    top_k: int | None = None,
    similarity_floor: float | None = None,
) -> str:
    """Return a markdown ``Relevant skills`` block for the given request."""
    from app.skills.registry import skills_registry  # local import — singleton

    # Resolve config — caller overrides win, then per-agent ops, then defaults.
    eff_top_k = top_k if top_k is not None else getattr(
        agent.ops.skills.injection, "top_k", 5
    )
    eff_floor = (
        similarity_floor
        if similarity_floor is not None
        else getattr(agent.ops.skills.injection, "similarity_floor", 0.65)
    )

    query = _extract_query(request)
    if not query:
        return ""

    # Reuse the registry's semantic search (cached embeddings + filters).
    # Over-fetch so we can post-filter by allowed_ids without coming up short.
    try:
        candidates = skills_registry.semantic_search(
            query=query,
            agent_id=agent.agent_id,
            limit=eff_top_k * 3,
            threshold=eff_floor,
        )
    except Exception as exc:  # noqa: BLE001 — never break the turn
        logger.debug("[skill_injection] semantic_search failed: %s", exc)
        return ""

    allowed = list(getattr(agent.ops.skills, "allowed_ids", ["*"]) or ["*"])
    matches: list[SkillMatch] = []
    for c in candidates:
        score = float(c.get("score", 0.0))
        skill: Skill = c["skill"]
        if score < eff_floor:
            continue
        # agent_ids: empty list means available to all agents
        if skill.agent_ids and agent.agent_id not in skill.agent_ids:
            continue
        if "*" not in allowed and not _matches_any(skill.name, allowed):
            continue
        matches.append(SkillMatch(score=score, skill=skill))
        if len(matches) >= eff_top_k:
            break

    return _render_section(matches)


def _extract_query(request: Any) -> str:
    """Pull the query string off either a TaskContract or DirectRequest."""
    text = getattr(request, "goal", None) or getattr(request, "message", None) or ""
    return text.strip()
```

Make sure `skills_registry` is importable at the module top so the test's `patch.object(skill_injection, "skills_registry", ...)` finds it:

```python
# app/agents/runtime/skill_injection.py — top of file alongside existing imports
from app.skills.registry import Skill, skills_registry
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_skill_injection_match.py -v
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/skill_injection.py tests/unit/runtime/test_skill_injection_match.py
git commit -m "feat(runtime): implement match_and_inject with floor/agent_id/allowed_ids filters"
```

---

### Task 24: Skill injection — `_matches_any` glob unit coverage

**Files:**
- Test: `tests/unit/runtime/test_skill_injection_glob.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_skill_injection_glob.py
"""_matches_any honors glob-style patterns used in ops.skills.allowed_ids."""
from __future__ import annotations


def test_wildcard_only_matches_anything():
    from app.agents.runtime.skill_injection import _matches_any

    assert _matches_any("anything", ["*"])
    assert _matches_any("finance:dcf", ["*"])


def test_prefix_glob_finance_star():
    from app.agents.runtime.skill_injection import _matches_any

    assert _matches_any("finance:dcf", ["finance:*"])
    assert _matches_any("finance:variance", ["finance:*"])
    assert not _matches_any("hr:bonus", ["finance:*"])


def test_exact_match_in_list():
    from app.agents.runtime.skill_injection import _matches_any

    assert _matches_any("compliance:legal-risk-assessment", ["compliance:legal-risk-assessment"])
    assert not _matches_any("compliance:other", ["compliance:legal-risk-assessment"])


def test_empty_patterns_denies_everything():
    from app.agents.runtime.skill_injection import _matches_any

    assert not _matches_any("anything", [])
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_skill_injection_glob.py -v
```

Expected: PASS already (Task 22 introduced `_matches_any`). If any of the 4 cases fails, fix `_matches_any` to satisfy them; this test pins behavior so a future refactor cannot silently break the allowed-ids contract.

- [ ] **Step 3: Write minimal implementation**

Nothing to change if Step 2 passed. If a glob case failed, refine `_matches_any`:

```python
# app/agents/runtime/skill_injection.py  (replace _matches_any if needed)
def _matches_any(skill_name: str, patterns: list[str]) -> bool:
    if not patterns:
        return False
    if "*" in patterns:
        return True
    return any(fnmatch.fnmatchcase(skill_name, p) for p in patterns)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_skill_injection_glob.py -v
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add tests/unit/runtime/test_skill_injection_glob.py
git commit -m "test(runtime): pin _matches_any glob semantics for allowed_ids"
```

---

### Task 25: Memory retrieval — render helper

**Files:**
- Create: `app/agents/runtime/memory_retrieval.py`
- Test: `tests/unit/runtime/test_memory_retrieval_render.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_memory_retrieval_render.py
"""Render helper produces a 'Prior work' markdown block."""
from __future__ import annotations


def test_render_prior_work_formats_results():
    from app.agents.runtime.memory_retrieval import _render_prior_work

    rows = [
        {
            "content": "## Q2 revenue analysis\nWe found a 12% YoY increase driven by enterprise.",
            "similarity": 0.88,
            "metadata": {
                "agent_id": "FIN",
                "initiative_id": "init-123",
                "goal": "Analyze Q2 revenue",
                "kind": "agent_report",
            },
        },
        {
            "content": "## Q1 forecast vs actual\nVariance: -3% on services.",
            "similarity": 0.71,
            "metadata": {
                "agent_id": "FIN",
                "initiative_id": "init-other",
                "goal": "Forecast Q1",
                "kind": "agent_report",
            },
        },
    ]
    out = _render_prior_work(rows)
    assert "## Prior work" in out
    assert "Analyze Q2 revenue" in out
    assert "Forecast Q1" in out
    assert "0.88" in out


def test_render_prior_work_empty():
    from app.agents.runtime.memory_retrieval import _render_prior_work

    assert _render_prior_work([]) == ""
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_memory_retrieval_render.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.agents.runtime.memory_retrieval'`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/memory_retrieval.py
"""Layer-3 memory retrieval: semantic match against vault agent_report docs.

Runs alongside skill injection inside ``before_agent_callback``. Returns
a markdown ``## Prior work`` block prepended to the agent prompt, so the
agent starts with summaries of its own prior reports on similar goals.

Source: ``app.services.knowledge_service.search_system_knowledge``
(already implemented over the vault embedding index, filtered by
``agent_name`` scope via the ``match_system_knowledge`` RPC).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from app.agents.base_agent import PikarBaseAgent
    from app.agents.runtime.types import DirectRequest, TaskContract


_MAX_SNIPPET_CHARS = 400


def _truncate(text: str, limit: int = _MAX_SNIPPET_CHARS) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _render_prior_work(results: list[dict[str, Any]]) -> str:
    """Render retrieved reports as a markdown ``## Prior work`` block."""
    if not results:
        return ""
    lines: list[str] = ["## Prior work (your past reports on similar goals)", ""]
    for r in results:
        meta = r.get("metadata", {}) or {}
        goal = meta.get("goal") or "(no goal recorded)"
        sim = float(r.get("similarity", 0.0))
        initiative = meta.get("initiative_id") or "—"
        snippet = _truncate(r.get("content", ""))
        lines.append(f"- **{goal}** (similarity {sim:.2f}, initiative `{initiative}`)")
        if snippet:
            lines.append(f"  > {snippet}")
    lines.append("")
    return "\n".join(lines)


async def retrieve_relevant_history(
    request: "TaskContract | DirectRequest",
    agent: "PikarBaseAgent",
    *,
    top_k: int | None = None,
) -> str:
    """Return a markdown ``Prior work`` block (implemented in Task 26)."""
    raise NotImplementedError


__all__ = ["retrieve_relevant_history"]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_memory_retrieval_render.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/memory_retrieval.py tests/unit/runtime/test_memory_retrieval_render.py
git commit -m "feat(runtime): add memory_retrieval module with prior-work renderer"
```

---

### Task 26: Memory retrieval — `retrieve_relevant_history`

**Files:**
- Edit: `app/agents/runtime/memory_retrieval.py`
- Test: `tests/unit/runtime/test_memory_retrieval_query.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_memory_retrieval_query.py
"""retrieve_relevant_history queries vault, filters, and renders."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())

from app.skills.registry import AgentID


def _agent(top_k: int = 4) -> MagicMock:
    a = MagicMock()
    a.agent_id = AgentID.FIN
    a.ops.memory.retrieval_top_k = top_k
    return a


def _task_contract(goal: str, initiative_id: str | None = None) -> MagicMock:
    c = MagicMock()
    c.goal = goal
    c.initiative_id = initiative_id
    # Ensure isinstance(request, TaskContract) doesn't fire on a MagicMock —
    # the implementation reads attributes by duck-typing.
    del c.message  # remove DirectRequest attribute so it's distinct
    return c


def _direct_request(message: str) -> MagicMock:
    r = MagicMock()
    r.message = message
    if hasattr(r, "goal"):
        del r.goal
    if hasattr(r, "initiative_id"):
        del r.initiative_id
    return r


def test_retrieve_calls_knowledge_service_with_agent_scope():
    from app.agents.runtime import memory_retrieval

    fake_search = AsyncMock(
        return_value=[
            {
                "content": "Q2 went well.",
                "similarity": 0.9,
                "metadata": {"agent_id": "FIN", "goal": "Analyze Q2", "kind": "agent_report"},
            }
        ]
    )
    with patch.object(memory_retrieval, "search_system_knowledge", fake_search):
        out = asyncio.run(
            memory_retrieval.retrieve_relevant_history(
                _task_contract("Analyze Q3 revenue"), _agent()
            )
        )

    fake_search.assert_awaited_once()
    call_kwargs = fake_search.await_args.kwargs
    assert call_kwargs.get("agent_name") == "FIN"
    assert call_kwargs.get("top_k") == 4 * 2  # over-fetch for initiative reranking
    assert "Analyze Q2" in out


def test_retrieve_falls_back_to_direct_request_message():
    from app.agents.runtime import memory_retrieval

    fake_search = AsyncMock(return_value=[])
    with patch.object(memory_retrieval, "search_system_knowledge", fake_search):
        out = asyncio.run(
            memory_retrieval.retrieve_relevant_history(
                _direct_request("what's our Q3 revenue?"), _agent()
            )
        )

    assert out == ""
    call_args = fake_search.await_args
    assert call_args.kwargs.get("query") == "what's our Q3 revenue?"


def test_retrieve_prioritizes_same_initiative():
    from app.agents.runtime import memory_retrieval

    other_initiative = {
        "content": "other",
        "similarity": 0.95,
        "metadata": {"agent_id": "FIN", "initiative_id": "other", "goal": "Other"},
    }
    same_initiative = {
        "content": "same",
        "similarity": 0.70,
        "metadata": {"agent_id": "FIN", "initiative_id": "init-X", "goal": "Same"},
    }
    fake_search = AsyncMock(return_value=[other_initiative, same_initiative])

    with patch.object(memory_retrieval, "search_system_knowledge", fake_search):
        out = asyncio.run(
            memory_retrieval.retrieve_relevant_history(
                _task_contract("goal text", initiative_id="init-X"),
                _agent(top_k=2),
            )
        )

    # Same-initiative row must appear before the other-initiative row.
    same_idx = out.index("Same")
    other_idx = out.index("Other")
    assert same_idx < other_idx


def test_retrieve_empty_query_returns_empty():
    from app.agents.runtime import memory_retrieval

    fake_search = AsyncMock()
    with patch.object(memory_retrieval, "search_system_knowledge", fake_search):
        out = asyncio.run(
            memory_retrieval.retrieve_relevant_history(_direct_request(""), _agent())
        )
    assert out == ""
    fake_search.assert_not_awaited()


def test_retrieve_handles_service_failure_gracefully():
    from app.agents.runtime import memory_retrieval

    fake_search = AsyncMock(side_effect=RuntimeError("vault down"))
    with patch.object(memory_retrieval, "search_system_knowledge", fake_search):
        out = asyncio.run(
            memory_retrieval.retrieve_relevant_history(
                _task_contract("goal"), _agent()
            )
        )
    assert out == ""
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_memory_retrieval_query.py -v
```

Expected: FAIL — `retrieve_relevant_history` raises `NotImplementedError`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/memory_retrieval.py  — add at module top
from app.services.knowledge_service import search_system_knowledge

# app/agents/runtime/memory_retrieval.py  — replace the NotImplementedError stub
def _extract_query_and_initiative(request: Any) -> tuple[str, str | None]:
    """Return (query, initiative_id) from a TaskContract or DirectRequest."""
    goal = getattr(request, "goal", None)
    message = getattr(request, "message", None)
    initiative_id = getattr(request, "initiative_id", None)
    query = (goal or message or "").strip()
    return query, initiative_id


def _prioritize_same_initiative(
    rows: list[dict[str, Any]], initiative_id: str
) -> list[dict[str, Any]]:
    """Stable-sort rows so same-initiative entries come first; preserve order otherwise."""
    same: list[dict[str, Any]] = []
    other: list[dict[str, Any]] = []
    for r in rows:
        meta = r.get("metadata", {}) or {}
        if meta.get("initiative_id") == initiative_id:
            same.append(r)
        else:
            other.append(r)
    return same + other


async def retrieve_relevant_history(
    request: "TaskContract | DirectRequest",
    agent: "PikarBaseAgent",
    *,
    top_k: int | None = None,
) -> str:
    """Return a markdown ``Prior work`` block for the request, or empty string."""
    eff_top_k = top_k if top_k is not None else getattr(
        agent.ops.memory, "retrieval_top_k", 4
    )
    query, initiative_id = _extract_query_and_initiative(request)
    if not query:
        return ""

    fetch_k = eff_top_k * 2 if initiative_id else eff_top_k
    try:
        rows = await search_system_knowledge(
            query=query,
            agent_name=agent.agent_id.value,
            top_k=fetch_k,
        )
    except Exception as exc:  # noqa: BLE001 — never break the turn
        logger.debug("[memory_retrieval] search failed: %s", exc)
        return ""

    # Filter to agent_report kind (vault may surface other kinds too).
    rows = [
        r
        for r in rows or []
        if (r.get("metadata") or {}).get("kind", "agent_report") == "agent_report"
    ]

    if initiative_id:
        rows = _prioritize_same_initiative(rows, initiative_id)

    return _render_prior_work(rows[:eff_top_k])
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_memory_retrieval_query.py -v
```

Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/memory_retrieval.py tests/unit/runtime/test_memory_retrieval_query.py
git commit -m "feat(runtime): retrieve_relevant_history with initiative-prioritized vault search"
```

---

### Task 27: Compaction trigger module

**Files:**
- Create: `app/agents/runtime/compaction.py`
- Test: `tests/unit/runtime/test_compaction.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_compaction.py
"""maybe_compact triggers summarization when token count crosses threshold."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())


def _session_with_events(events: list[dict], approx_tokens: int) -> MagicMock:
    s = MagicMock()
    s.id = "sess-1"
    s.events = events
    # Stand-in for the metric maybe_compact reads to decide whether to fire.
    s.approx_token_count = approx_tokens
    return s


def _compaction_cfg(trigger: int = 80_000, keep: int = 12) -> MagicMock:
    c = MagicMock()
    c.trigger_token_count = trigger
    c.keep_last_n_turns = keep
    return c


def test_maybe_compact_noop_under_threshold():
    from app.agents.runtime import compaction

    summarize = AsyncMock()
    session = _session_with_events([{"i": i} for i in range(50)], approx_tokens=10_000)
    with patch.object(compaction, "summarize_dropped_events", summarize):
        result = asyncio.run(compaction.maybe_compact(session, _compaction_cfg()))

    assert result is None
    summarize.assert_not_awaited()


def test_maybe_compact_fires_above_threshold_and_keeps_last_n():
    from app.agents.runtime import compaction

    events = [{"i": i} for i in range(40)]
    summarize = AsyncMock(return_value="SUMMARY TEXT")
    session = _session_with_events(events, approx_tokens=90_000)
    with patch.object(compaction, "summarize_dropped_events", summarize):
        result = asyncio.run(
            compaction.maybe_compact(session, _compaction_cfg(trigger=80_000, keep=12))
        )

    summarize.assert_awaited_once()
    call_args = summarize.await_args
    # The "dropped" set is everything except the last keep_last_n_turns events.
    assert call_args.kwargs["events"] == events[:-12]
    assert call_args.kwargs["session_id"] == "sess-1"
    assert result is not None
    assert result.summary == "SUMMARY TEXT"
    assert result.dropped_event_count == 40 - 12


def test_maybe_compact_swallows_summarizer_failure():
    from app.agents.runtime import compaction

    summarize = AsyncMock(side_effect=RuntimeError("model down"))
    session = _session_with_events([{"i": i} for i in range(40)], approx_tokens=90_000)
    with patch.object(compaction, "summarize_dropped_events", summarize):
        result = asyncio.run(compaction.maybe_compact(session, _compaction_cfg()))

    assert result is None


def test_maybe_compact_skips_when_fewer_events_than_keep():
    from app.agents.runtime import compaction

    summarize = AsyncMock()
    session = _session_with_events([{"i": i} for i in range(5)], approx_tokens=90_000)
    with patch.object(compaction, "summarize_dropped_events", summarize):
        result = asyncio.run(
            compaction.maybe_compact(session, _compaction_cfg(keep=12))
        )

    assert result is None
    summarize.assert_not_awaited()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_compaction.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.agents.runtime.compaction'`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/compaction.py
"""Session compaction trigger.

Wraps the existing ``app.services.conversation_summarizer`` so the
runtime layer fires summarization when an agent's session crosses
``ops.compaction.trigger_token_count``. The session keeps the last
``keep_last_n_turns`` events; everything older is summarized and stored
on the session for the next turn to read as background context.

The actual summary persistence is performed by the session service that
already owns the dropped-event path
(``SupabaseSessionService.get_session``). This module returns a
``CompactionResult`` so callers (lifecycle.after_agent) can attach the
summary to session state or log it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.services.conversation_summarizer import summarize_dropped_events

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from app.agents.runtime.operations_config import CompactionConfig


@dataclass
class CompactionResult:
    """Outcome of a compaction pass."""

    summary: str
    dropped_event_count: int
    kept_event_count: int


async def maybe_compact(
    session: Any,
    cfg: "CompactionConfig",
) -> CompactionResult | None:
    """Trigger compaction when the session crosses the configured threshold.

    Returns ``None`` when no compaction was needed, when the session is
    too small to compact (fewer events than ``keep_last_n_turns``), or
    when the summarizer fails. Never raises.
    """
    trigger = int(getattr(cfg, "trigger_token_count", 80_000))
    keep = int(getattr(cfg, "keep_last_n_turns", 12))

    approx_tokens = int(getattr(session, "approx_token_count", 0) or 0)
    if approx_tokens < trigger:
        return None

    events = list(getattr(session, "events", []) or [])
    if len(events) <= keep:
        # Token count is up but we don't have enough turns to drop. Bail
        # rather than feeding the summarizer an empty list.
        return None

    dropped = events[:-keep]
    kept = events[-keep:]
    session_id = getattr(session, "id", "") or "unknown"

    try:
        summary = await summarize_dropped_events(
            events=dropped,
            session_id=session_id,
        )
    except Exception as exc:  # noqa: BLE001 — never break the turn
        logger.warning(
            "[compaction] summarizer failed for session %s: %s", session_id, exc
        )
        return None

    if not summary:
        return None

    return CompactionResult(
        summary=summary,
        dropped_event_count=len(dropped),
        kept_event_count=len(kept),
    )


__all__ = ["CompactionResult", "maybe_compact"]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_compaction.py -v
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/compaction.py tests/unit/runtime/test_compaction.py
git commit -m "feat(runtime): add compaction trigger over conversation_summarizer"
```

---

### Task 28: Handoff recorder — module + history-row writer

**Files:**
- Create: `app/agents/runtime/handoff.py`
- Test: `tests/unit/runtime/test_handoff_record.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_handoff_record.py
"""record_handoff writes a row to initiative_phase_history."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())


def _packet(target: str = "FinancialAnalysisAgent", source: str = "executive") -> MagicMock:
    p = MagicMock()
    p.source_agent = source
    p.target_agent = target
    p.intent = "Forecast Q3"
    p.correlation_id = "corr-1"
    p.model_dump.return_value = {
        "source_agent": source,
        "target_agent": target,
        "intent": "Forecast Q3",
        "correlation_id": "corr-1",
    }
    return p


def _supabase_table_chain(execute_return: object) -> MagicMock:
    client = MagicMock()
    table = MagicMock()
    insert = MagicMock()
    execute = AsyncMock(return_value=execute_return)
    insert.execute = execute
    table.insert.return_value = insert
    client.table.return_value = table
    return client


def test_record_handoff_inserts_row_when_initiative_present():
    from app.agents.runtime import handoff

    inserted_row = MagicMock(data=[{"id": "row-1"}])
    fake_client = _supabase_table_chain(inserted_row)
    get_client = AsyncMock(return_value=fake_client)

    with patch.object(handoff, "get_async_client", get_client):
        packet_id = asyncio.run(
            handoff.record_handoff(
                packet=_packet(),
                initiative_id="init-X",
                phase="validation",
            )
        )

    assert packet_id is not None
    fake_client.table.assert_called_once_with("initiative_phase_history")
    fake_client.table().insert.assert_called_once()
    payload = fake_client.table().insert.call_args.args[0]
    assert payload["initiative_id"] == "init-X"
    assert payload["phase"] == "validation"
    assert payload["event"] == "handoff"
    assert payload["from_agent"] == "executive"
    assert payload["to_agent"] == "FinancialAnalysisAgent"
    assert payload["packet_id"] is not None


def test_record_handoff_skips_when_no_initiative():
    from app.agents.runtime import handoff

    get_client = AsyncMock()
    with patch.object(handoff, "get_async_client", get_client):
        packet_id = asyncio.run(
            handoff.record_handoff(
                packet=_packet(),
                initiative_id=None,
                phase=None,
            )
        )

    assert packet_id is None
    get_client.assert_not_awaited()


def test_record_handoff_swallows_db_errors():
    from app.agents.runtime import handoff

    get_client = AsyncMock(side_effect=RuntimeError("db down"))
    with patch.object(handoff, "get_async_client", get_client):
        packet_id = asyncio.run(
            handoff.record_handoff(
                packet=_packet(),
                initiative_id="init-X",
                phase="validation",
            )
        )

    assert packet_id is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_handoff_record.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.agents.runtime.handoff'`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/handoff.py
"""Cross-agent handoff recorder.

Wraps the existing ``app.agents.handoff_packet.HandoffPacket`` so that
every cross-agent transition during an initiative writes one row to
``initiative_phase_history`` with ``event='handoff'``. This closes the
cross-agent visibility gap captured in the 2026-04-28 initiative
audit — the initiative record alone now reveals every transition.

We do *not* duplicate the prompt-injection behavior already shipped on
the ``HandoffPacket`` side; lifecycle.before_agent still relies on the
existing read-side helper. This module only adds the durable history
row.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from app.services.supabase_client import get_async_client

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from app.agents.handoff_packet import HandoffPacket


_TABLE = "initiative_phase_history"


async def record_handoff(
    *,
    packet: "HandoffPacket",
    initiative_id: str | None,
    phase: str | None,
) -> str | None:
    """Insert a ``handoff`` row into ``initiative_phase_history``.

    Returns the synthetic packet id on success, or ``None`` if the
    handoff isn't tied to an initiative (direct-mode chats), if the
    Supabase call fails, or if the packet is malformed. Never raises.
    """
    if not initiative_id:
        # Direct-mode handoffs aren't logged here — they're captured on
        # the executive's agent_task_executions row via Section D.
        return None

    packet_id = str(uuid.uuid4())
    try:
        client = await get_async_client()
        row = {
            "initiative_id": initiative_id,
            "phase": phase,
            "event": "handoff",
            "from_agent": packet.source_agent,
            "to_agent": packet.target_agent,
            "packet_id": packet_id,
            "packet": packet.model_dump(),
        }
        await client.table(_TABLE).insert(row).execute()
        return packet_id
    except Exception as exc:  # noqa: BLE001 — never break the turn
        logger.warning(
            "[handoff] record_handoff failed for initiative=%s: %s",
            initiative_id,
            exc,
        )
        return None


__all__ = ["record_handoff"]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_handoff_record.py -v
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/handoff.py tests/unit/runtime/test_handoff_record.py
git commit -m "feat(runtime): record cross-agent handoffs into initiative_phase_history"
```

---

### Task 29: `before_agent` — wire task router + skill injection + memory retrieval

**Files:**
- Edit: `app/agents/runtime/lifecycle.py`
- Test: `tests/unit/runtime/test_before_agent_callback.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_before_agent_callback.py
"""before_agent_callback composes router + skill + memory + persona fragments."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.agents.callback_context", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())


def _ctx(message: str = "Forecast Q3 revenue") -> MagicMock:
    ctx = MagicMock()
    ctx.state = {}
    ctx.agent_name = "FinancialAnalysisAgent"
    # ADK sets user_content from the invocation; structure mirrors
    # tests/unit/test_agent_memory_callback.py.
    part = MagicMock()
    part.text = message
    content = MagicMock()
    content.parts = [part]
    ctx.user_content = content
    return ctx


def _agent() -> MagicMock:
    from app.skills.registry import AgentID

    a = MagicMock()
    a.agent_id = AgentID.FIN
    a.persona_id = "founder"
    a.ops = MagicMock()
    a.ops.skills.injection.top_k = 5
    a.ops.skills.injection.similarity_floor = 0.65
    return a


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


def test_before_agent_invokes_router_skill_memory_persona_in_order():
    from app.agents.runtime import lifecycle

    call_log: list[str] = []

    def fake_classify(req, ops):
        call_log.append("router")
        result = MagicMock()
        result.mode = "direct"
        result.signal = "rule"
        return result

    async def fake_skills(req, agent, **kw):
        call_log.append("skills")
        return "## Relevant skills\n- fake\n"

    async def fake_memory(req, agent, **kw):
        call_log.append("memory")
        return "## Prior work\n- fake\n"

    def fake_persona_fragments(persona_id):
        call_log.append("persona")
        return "## Persona policy\n- founder\n"

    with patch("app.agents.runtime.lifecycle.task_router") as mock_router, patch(
        "app.agents.runtime.lifecycle.skill_injection"
    ) as mock_skill, patch(
        "app.agents.runtime.lifecycle.memory_retrieval"
    ) as mock_mem, patch(
        "app.agents.runtime.lifecycle.persona_gate"
    ) as mock_persona:
        mock_router.classify.side_effect = fake_classify
        mock_skill.match_and_inject = AsyncMock(side_effect=fake_skills)
        mock_mem.retrieve_relevant_history = AsyncMock(side_effect=fake_memory)
        mock_persona.apply_prompt_fragments.side_effect = fake_persona_fragments

        cb = lifecycle.before_agent(_agent())
        # ADK passes a CallbackContext positionally.
        ctx = _ctx()
        _run(lifecycle._dispatch_async(cb, ctx))

    # Router runs first, then skills, memory, persona (in that order).
    assert call_log == ["router", "skills", "memory", "persona"]
    # Injected blocks are accumulated on state for downstream rendering.
    injected = ctx.state.get("_runtime_injected_blocks")
    assert injected and "Relevant skills" in injected
    assert "Prior work" in injected
    assert "Persona policy" in injected
    # Classifier output is recorded on state for after_agent persistence.
    assert ctx.state.get("_runtime_classifier_mode") == "direct"
    assert ctx.state.get("_runtime_classifier_signal") == "rule"


def test_before_agent_swallows_module_failures():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.task_router") as mock_router, patch(
        "app.agents.runtime.lifecycle.skill_injection"
    ) as mock_skill, patch(
        "app.agents.runtime.lifecycle.memory_retrieval"
    ) as mock_mem, patch(
        "app.agents.runtime.lifecycle.persona_gate"
    ) as mock_persona:
        mock_router.classify.side_effect = RuntimeError("boom")
        mock_skill.match_and_inject = AsyncMock(return_value="")
        mock_mem.retrieve_relevant_history = AsyncMock(return_value="")
        mock_persona.apply_prompt_fragments.return_value = ""

        cb = lifecycle.before_agent(_agent())
        ctx = _ctx()
        # Must not raise even though the router blew up.
        _run(lifecycle._dispatch_async(cb, ctx))


def test_before_agent_reraises_initiative_contract_error():
    from app.agents.runtime import lifecycle
    from app.agents.runtime.types import InitiativeContractError

    with patch("app.agents.runtime.lifecycle.task_router") as mock_router, patch(
        "app.agents.runtime.lifecycle.skill_injection"
    ) as mock_skill, patch(
        "app.agents.runtime.lifecycle.memory_retrieval"
    ) as mock_mem, patch(
        "app.agents.runtime.lifecycle.persona_gate"
    ) as mock_persona:
        mock_router.classify.side_effect = InitiativeContractError("missing goal")
        mock_skill.match_and_inject = AsyncMock(return_value="")
        mock_mem.retrieve_relevant_history = AsyncMock(return_value="")
        mock_persona.apply_prompt_fragments.return_value = ""

        cb = lifecycle.before_agent(_agent())
        ctx = _ctx()
        try:
            _run(lifecycle._dispatch_async(cb, ctx))
        except InitiativeContractError:
            return
    raise AssertionError("InitiativeContractError must propagate")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_before_agent_callback.py -v
```

Expected: FAIL — `lifecycle.before_agent` currently returns a no-op callback and the helper `_dispatch_async` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/lifecycle.py — replace the before_agent stub
from app.agents.runtime import memory_retrieval, persona_gate, skill_injection, task_router  # noqa: E402
from app.agents.runtime.types import InitiativeContractError  # noqa: E402


def _extract_request(callback_context: Any) -> Any:
    """Build a minimal DirectRequest from ADK CallbackContext.

    The real TaskContract path is wired by step_runtime (Section A's
    execute_task) which writes the contract onto state before the
    callback fires. If state carries a contract we use it; otherwise we
    fall back to a DirectRequest synthesized from user_content + state.
    """
    from app.agents.runtime.types import DirectRequest, TaskContract

    contract_raw = None
    try:
        contract_raw = callback_context.state.get("_runtime_task_contract")
    except Exception:  # noqa: BLE001
        contract_raw = None

    if isinstance(contract_raw, TaskContract):
        return contract_raw

    # DirectRequest path — pull user text from ADK user_content.
    text = ""
    try:
        uc = getattr(callback_context, "user_content", None)
        if uc is not None:
            parts = getattr(uc, "parts", None) or []
            text = " ".join(
                (getattr(p, "text", "") or "").strip()
                for p in parts
                if hasattr(p, "text")
            ).strip()
    except Exception:  # noqa: BLE001
        text = ""

    return DirectRequest(message=text)


async def _dispatch_async(callback: Any, ctx: Any) -> Any:
    """Test/runtime helper: run a possibly-async callback to completion.

    ADK schedules callbacks; this helper exists so unit tests can drive
    a single invocation deterministically without spinning up ADK.
    """
    import inspect

    result = callback(ctx)
    if inspect.isawaitable(result):
        result = await result
    return result


def before_agent(agent: "PikarBaseAgent") -> Callable[[Any], Any]:
    """Return the ADK before_agent_callback bound to ``agent``."""

    async def _callback(callback_context: Any) -> None:
        request = _extract_request(callback_context)

        # 1. Task router — Section C owns the implementation. We surface
        #    its decision on state so after_agent can record it in the
        #    agent_task_executions row.
        try:
            classifier = task_router.classify(request, agent.ops)
            callback_context.state["_runtime_classifier_mode"] = getattr(
                classifier, "mode", "initiative"
            )
            callback_context.state["_runtime_classifier_signal"] = getattr(
                classifier, "signal", "rule"
            )
        except InitiativeContractError:
            # The contract is malformed — let it propagate. ADK will surface
            # the failure to the caller, and the agent will not run.
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("[before_agent] task_router failed: %s", exc)

        blocks: list[str] = []

        # 2. Skill injection.
        try:
            block = await skill_injection.match_and_inject(request, agent)
            if block:
                blocks.append(block)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[before_agent] skill_injection failed: %s", exc)

        # 3. Memory retrieval.
        try:
            block = await memory_retrieval.retrieve_relevant_history(request, agent)
            if block:
                blocks.append(block)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[before_agent] memory_retrieval failed: %s", exc)

        # 4. Persona prompt fragments (Section C — persona_gate).
        try:
            block = persona_gate.apply_prompt_fragments(agent.persona_id)
            if block:
                blocks.append(block)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[before_agent] persona_gate fragments failed: %s", exc)

        if blocks:
            callback_context.state["_runtime_injected_blocks"] = "\n\n".join(blocks)

    _callback.__name__ = f"before_agent::{agent.agent_id.value}"
    return _callback
```

Section C owns `task_router` and `persona_gate`, and Section A owns `runtime/types.py` (`InitiativeContractError`, `DirectRequest`, `TaskContract`, `ClassifierResult`). The unit test patches all three modules; in CI those modules will exist by the time the test runs because Section A and Section C ship in parallel waves.

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_before_agent_callback.py -v
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/lifecycle.py tests/unit/runtime/test_before_agent_callback.py
git commit -m "feat(runtime): wire before_agent_callback to router/skills/memory/persona"
```

---

### Task 30: `before_agent` — render injected blocks into the system instruction

**Files:**
- Edit: `app/agents/runtime/lifecycle.py`
- Test: `tests/unit/runtime/test_before_agent_prompt_injection.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_before_agent_prompt_injection.py
"""Injected blocks are exposed via _runtime_injected_blocks for the model callback."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.agents.callback_context", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())


def _ctx() -> MagicMock:
    ctx = MagicMock()
    ctx.state = {}
    ctx.agent_name = "FinancialAnalysisAgent"
    part = MagicMock()
    part.text = "Forecast Q3"
    content = MagicMock()
    content.parts = [part]
    ctx.user_content = content
    return ctx


def _agent() -> MagicMock:
    from app.skills.registry import AgentID

    a = MagicMock()
    a.agent_id = AgentID.FIN
    a.persona_id = "founder"
    a.ops.skills.injection.top_k = 5
    a.ops.skills.injection.similarity_floor = 0.65
    return a


def test_apply_injected_blocks_to_instruction_prepends_block():
    from app.agents.runtime import lifecycle

    state = {"_runtime_injected_blocks": "## Relevant skills\n- one\n"}
    original = "You are FinancialAnalysisAgent."
    out = lifecycle.apply_injected_blocks(state, original)

    assert out.startswith("## Relevant skills")
    assert "You are FinancialAnalysisAgent." in out


def test_apply_injected_blocks_passthrough_when_empty():
    from app.agents.runtime import lifecycle

    state: dict = {}
    original = "You are FinancialAnalysisAgent."
    out = lifecycle.apply_injected_blocks(state, original)

    assert out == original


def test_before_agent_writes_blocks_then_callback_returns_none():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.task_router") as mock_router, patch(
        "app.agents.runtime.lifecycle.skill_injection"
    ) as mock_skill, patch(
        "app.agents.runtime.lifecycle.memory_retrieval"
    ) as mock_mem, patch(
        "app.agents.runtime.lifecycle.persona_gate"
    ) as mock_persona:
        mock_router.classify.return_value = MagicMock(mode="direct", signal="rule")
        mock_skill.match_and_inject = AsyncMock(return_value="## Relevant skills\n- s\n")
        mock_mem.retrieve_relevant_history = AsyncMock(return_value="## Prior work\n- p\n")
        mock_persona.apply_prompt_fragments.return_value = "## Persona policy\n- f\n"

        cb = lifecycle.before_agent(_agent())
        ctx = _ctx()
        result = asyncio.run(lifecycle._dispatch_async(cb, ctx))

    assert result is None  # ADK convention: returning None lets the model run.
    blob = ctx.state["_runtime_injected_blocks"]
    assert "Relevant skills" in blob
    assert "Prior work" in blob
    assert "Persona policy" in blob
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_before_agent_prompt_injection.py -v
```

Expected: FAIL — `apply_injected_blocks` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/lifecycle.py — add at module bottom

_RUNTIME_BLOCKS_KEY = "_runtime_injected_blocks"


def apply_injected_blocks(state: dict[str, Any], instruction: str) -> str:
    """Prepend any blocks `before_agent` accumulated on state to ``instruction``.

    Called by ``PikarBaseAgent``'s before_model_callback (Section A) so
    the agent's system instruction always carries the freshly-computed
    skill/memory/persona blocks for this turn. A missing or empty value
    leaves the original instruction unchanged.
    """
    blob = state.get(_RUNTIME_BLOCKS_KEY) if isinstance(state, dict) else None
    if not blob:
        return instruction
    return f"{blob}\n\n{instruction}"


__all__ = [
    "before_agent",
    "before_tool",
    "after_tool",
    "after_agent",
    "apply_injected_blocks",
]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_before_agent_prompt_injection.py -v
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/lifecycle.py tests/unit/runtime/test_before_agent_prompt_injection.py
git commit -m "feat(runtime): expose apply_injected_blocks helper for prompt rendering"
```

---

### Task 31: `before_tool` — persona allow/deny

**Files:**
- Edit: `app/agents/runtime/lifecycle.py`
- Test: `tests/unit/runtime/test_before_tool_persona.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_before_tool_persona.py
"""before_tool_callback delegates to persona_gate.check_tool_allowed."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.tools", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())


def _agent() -> MagicMock:
    from app.skills.registry import AgentID

    a = MagicMock()
    a.agent_id = AgentID.FIN
    a.persona_id = "viewer"
    return a


def _tool(name: str) -> MagicMock:
    t = MagicMock()
    t.name = name
    return t


def test_before_tool_blocks_on_persona_deny():
    from app.agents.runtime import lifecycle
    from app.agents.runtime.types import PersonaPolicyError

    with patch("app.agents.runtime.lifecycle.persona_gate") as mock_persona, patch(
        "app.agents.runtime.lifecycle.research_gate"
    ) as mock_research:
        mock_persona.check_tool_allowed.side_effect = PersonaPolicyError(
            "viewer cannot use send_email"
        )
        mock_research.is_open.return_value = False

        cb = lifecycle.before_tool(_agent())
        ctx = MagicMock()
        ctx.state = {}

        try:
            asyncio.run(
                lifecycle._dispatch_async(
                    cb, (_tool("send_email"), {"to": "x@y.com"}, ctx)
                )
            )
        except PersonaPolicyError as exc:
            assert "viewer cannot use send_email" in str(exc)
            return
    raise AssertionError("PersonaPolicyError must propagate")


def test_before_tool_passes_when_allowed():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.persona_gate") as mock_persona, patch(
        "app.agents.runtime.lifecycle.research_gate"
    ) as mock_research:
        mock_persona.check_tool_allowed.return_value = None
        mock_persona.check_action_threshold = AsyncMock(return_value=None)
        mock_research.is_open.return_value = False

        cb = lifecycle.before_tool(_agent())
        ctx = MagicMock()
        ctx.state = {}

        result = asyncio.run(
            lifecycle._dispatch_async(
                cb, (_tool("list_skills"), {}, ctx)
            )
        )

    assert result is None
    mock_persona.check_tool_allowed.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_before_tool_persona.py -v
```

Expected: FAIL — `before_tool` is still a no-op and `_dispatch_async` only handles single-arg callbacks.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/lifecycle.py — extend _dispatch_async + replace before_tool stub

from app.agents.runtime import research_gate  # noqa: E402
from app.agents.runtime.types import PersonaPolicyError, ResearchGateError  # noqa: E402


async def _dispatch_async(callback: Any, arg_or_args: Any) -> Any:
    """Drive a callback with positional args (single value or tuple/list).

    Lets unit tests stay terse: ``_dispatch_async(cb, ctx)`` for
    before_agent / after_agent, and ``_dispatch_async(cb, (tool, args, ctx))``
    for before_tool / after_tool.
    """
    import inspect

    if isinstance(arg_or_args, (tuple, list)):
        result = callback(*arg_or_args)
    else:
        result = callback(arg_or_args)
    if inspect.isawaitable(result):
        result = await result
    return result


def before_tool(agent: "PikarBaseAgent") -> Callable[..., Any]:
    """Return the ADK before_tool_callback bound to ``agent``."""

    async def _callback(tool: Any, args: dict[str, Any], tool_context: Any) -> Any:
        tool_id = getattr(tool, "name", "") or ""

        # 1. Persona allow/deny — owned by Section C. Raises PersonaPolicyError on deny.
        persona_gate.check_tool_allowed(tool_id, agent.persona_id)

        # 2. Action threshold (returns approval ticket / None). Implemented in Task 32.
        await persona_gate.check_action_threshold(
            tool_id=tool_id,
            tool_args=args,
            persona_id=agent.persona_id,
        )

        # 3. Research gate. Implemented in Task 33.
        # 4. Approval token check. Implemented in Task 34.
        return None

    _callback.__name__ = f"before_tool::{agent.agent_id.value}"
    return _callback
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_before_tool_persona.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/lifecycle.py tests/unit/runtime/test_before_tool_persona.py
git commit -m "feat(runtime): before_tool delegates to persona_gate.check_tool_allowed"
```

---

### Task 32: `before_tool` — action threshold + approval escalation

**Files:**
- Edit: `app/agents/runtime/lifecycle.py`
- Test: `tests/unit/runtime/test_before_tool_threshold.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_before_tool_threshold.py
"""Action threshold raises PersonaPolicyError when persona_gate signals escalation."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.tools", MagicMock())


def _agent() -> MagicMock:
    from app.skills.registry import AgentID

    a = MagicMock()
    a.agent_id = AgentID.FIN
    a.persona_id = "viewer"
    return a


def test_action_threshold_invoked_with_tool_args():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.persona_gate") as mock_persona, patch(
        "app.agents.runtime.lifecycle.research_gate"
    ) as mock_research:
        mock_persona.check_tool_allowed.return_value = None
        mock_persona.check_action_threshold = AsyncMock(return_value=None)
        mock_research.is_open.return_value = False

        cb = lifecycle.before_tool(_agent())
        tool = MagicMock(name="wire_payment")
        tool.name = "wire_payment"
        ctx = MagicMock()
        ctx.state = {}

        args = {"amount_usd": 5000}
        asyncio.run(lifecycle._dispatch_async(cb, (tool, args, ctx)))

    mock_persona.check_action_threshold.assert_awaited_once()
    kwargs = mock_persona.check_action_threshold.await_args.kwargs
    assert kwargs["tool_id"] == "wire_payment"
    assert kwargs["tool_args"] == {"amount_usd": 5000}
    assert kwargs["persona_id"] == "viewer"


def test_action_threshold_escalation_raises_persona_policy_error():
    from app.agents.runtime import lifecycle
    from app.agents.runtime.types import PersonaPolicyError

    with patch("app.agents.runtime.lifecycle.persona_gate") as mock_persona, patch(
        "app.agents.runtime.lifecycle.research_gate"
    ) as mock_research:
        mock_persona.check_tool_allowed.return_value = None
        mock_persona.check_action_threshold = AsyncMock(
            side_effect=PersonaPolicyError("over $1k requires approval")
        )
        mock_research.is_open.return_value = False

        cb = lifecycle.before_tool(_agent())
        tool = MagicMock(name="wire_payment")
        tool.name = "wire_payment"
        ctx = MagicMock()
        ctx.state = {}

        try:
            asyncio.run(lifecycle._dispatch_async(cb, (tool, {"amount_usd": 5000}, ctx)))
        except PersonaPolicyError:
            return
    raise AssertionError("PersonaPolicyError must propagate from action threshold")
```

- [ ] **Step 2: Run test to verify it fails**

Should already PASS after Task 31, since `before_tool` already awaits `check_action_threshold`. Keep the test to pin the contract.

```bash
uv run pytest tests/unit/runtime/test_before_tool_threshold.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 3: Write minimal implementation**

No changes required — `before_tool` already forwards `tool_id`, `tool_args`, and `persona_id` to `persona_gate.check_action_threshold`. If Step 2 failed, fix the kwarg names to exactly match the test:

```python
# inside before_tool _callback
await persona_gate.check_action_threshold(
    tool_id=tool_id,
    tool_args=args,
    persona_id=agent.persona_id,
)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_before_tool_threshold.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add tests/unit/runtime/test_before_tool_threshold.py
git commit -m "test(runtime): pin before_tool action-threshold delegation contract"
```

---

### Task 33: `before_tool` — research gate enforcement

**Files:**
- Edit: `app/agents/runtime/lifecycle.py`
- Test: `tests/unit/runtime/test_before_tool_research_gate.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_before_tool_research_gate.py
"""before_tool blocks non-research tools while research gate is open."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.tools", MagicMock())


def _agent() -> MagicMock:
    from app.skills.registry import AgentID

    a = MagicMock()
    a.agent_id = AgentID.FIN
    a.persona_id = "founder"
    return a


def _ctx(contract_id: str | None = "contract-1") -> MagicMock:
    ctx = MagicMock()
    ctx.state = {"_runtime_contract_id": contract_id} if contract_id else {}
    return ctx


def test_research_gate_blocks_non_research_tool_when_open():
    from app.agents.runtime import lifecycle
    from app.agents.runtime.types import ResearchGateError

    with patch("app.agents.runtime.lifecycle.persona_gate") as mock_persona, patch(
        "app.agents.runtime.lifecycle.research_gate"
    ) as mock_research:
        mock_persona.check_tool_allowed.return_value = None
        mock_persona.check_action_threshold = AsyncMock(return_value=None)
        mock_research.is_open.return_value = True
        mock_research.is_research_tool.return_value = False

        cb = lifecycle.before_tool(_agent())
        tool = MagicMock()
        tool.name = "draft_blog_post"
        ctx = _ctx()

        try:
            asyncio.run(lifecycle._dispatch_async(cb, (tool, {}, ctx)))
        except ResearchGateError:
            mock_research.is_open.assert_called_once_with(_agent_match := mock_research.is_open.call_args.args[0], "contract-1")
            return
    raise AssertionError("ResearchGateError must be raised when gate is open and tool is not research")


def test_research_gate_allows_research_tool_when_open():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.persona_gate") as mock_persona, patch(
        "app.agents.runtime.lifecycle.research_gate"
    ) as mock_research:
        mock_persona.check_tool_allowed.return_value = None
        mock_persona.check_action_threshold = AsyncMock(return_value=None)
        mock_research.is_open.return_value = True
        mock_research.is_research_tool.return_value = True

        cb = lifecycle.before_tool(_agent())
        tool = MagicMock()
        tool.name = "deep_research"
        ctx = _ctx()

        result = asyncio.run(lifecycle._dispatch_async(cb, (tool, {"query": "q"}, ctx)))
        assert result is None


def test_research_gate_allows_anything_when_closed():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.persona_gate") as mock_persona, patch(
        "app.agents.runtime.lifecycle.research_gate"
    ) as mock_research:
        mock_persona.check_tool_allowed.return_value = None
        mock_persona.check_action_threshold = AsyncMock(return_value=None)
        mock_research.is_open.return_value = False

        cb = lifecycle.before_tool(_agent())
        tool = MagicMock()
        tool.name = "draft_blog_post"
        ctx = _ctx()

        result = asyncio.run(lifecycle._dispatch_async(cb, (tool, {}, ctx)))
        assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_before_tool_research_gate.py -v
```

Expected: FAIL — `before_tool` doesn't yet consult `research_gate.is_open`/`is_research_tool`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/lifecycle.py — extend the before_tool _callback
async def _callback(tool: Any, args: dict[str, Any], tool_context: Any) -> Any:
    tool_id = getattr(tool, "name", "") or ""

    persona_gate.check_tool_allowed(tool_id, agent.persona_id)
    await persona_gate.check_action_threshold(
        tool_id=tool_id,
        tool_args=args,
        persona_id=agent.persona_id,
    )

    # Research gate: only enforced when a contract is bound (initiative mode).
    contract_id = None
    try:
        contract_id = tool_context.state.get("_runtime_contract_id")
    except Exception:  # noqa: BLE001
        contract_id = None

    if contract_id and research_gate.is_open(agent, contract_id):
        if not research_gate.is_research_tool(tool_id):
            raise ResearchGateError(
                f"Research gate open for contract {contract_id}; "
                f"tool '{tool_id}' is not in the research tool set."
            )

    return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_before_tool_research_gate.py -v
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/lifecycle.py tests/unit/runtime/test_before_tool_research_gate.py
git commit -m "feat(runtime): block non-research tools when research gate is open"
```

---

### Task 34: `before_tool` — approval token check

**Files:**
- Edit: `app/agents/runtime/lifecycle.py`
- Test: `tests/unit/runtime/test_before_tool_approval.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_before_tool_approval.py
"""before_tool consults an approval-token check after persona/research gates."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.tools", MagicMock())


def _agent() -> MagicMock:
    from app.skills.registry import AgentID

    a = MagicMock()
    a.agent_id = AgentID.FIN
    a.persona_id = "founder"
    return a


def test_before_tool_checks_approval_token_for_flagged_tools():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.persona_gate") as mock_persona, patch(
        "app.agents.runtime.lifecycle.research_gate"
    ) as mock_research, patch(
        "app.agents.runtime.lifecycle._verify_approval_token", new=AsyncMock(return_value=None)
    ) as mock_verify:
        # Threshold flags this call as requiring approval by returning a dict.
        mock_persona.check_tool_allowed.return_value = None
        mock_persona.check_action_threshold = AsyncMock(
            return_value={"required": True, "ticket": "appr-1"}
        )
        mock_research.is_open.return_value = False

        cb = lifecycle.before_tool(_agent())
        tool = MagicMock()
        tool.name = "wire_payment"
        ctx = MagicMock()
        ctx.state = {"approval_token::wire_payment": "tok-1"}

        asyncio.run(lifecycle._dispatch_async(cb, (tool, {"amount_usd": 5000}, ctx)))

    mock_verify.assert_awaited_once()
    kwargs = mock_verify.await_args.kwargs
    assert kwargs["tool_id"] == "wire_payment"
    assert kwargs["ticket"] == "appr-1"
    assert kwargs["token"] == "tok-1"


def test_before_tool_skips_approval_when_not_required():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.persona_gate") as mock_persona, patch(
        "app.agents.runtime.lifecycle.research_gate"
    ) as mock_research, patch(
        "app.agents.runtime.lifecycle._verify_approval_token", new=AsyncMock()
    ) as mock_verify:
        mock_persona.check_tool_allowed.return_value = None
        mock_persona.check_action_threshold = AsyncMock(return_value=None)
        mock_research.is_open.return_value = False

        cb = lifecycle.before_tool(_agent())
        tool = MagicMock()
        tool.name = "list_skills"
        ctx = MagicMock()
        ctx.state = {}

        asyncio.run(lifecycle._dispatch_async(cb, (tool, {}, ctx)))

    mock_verify.assert_not_awaited()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_before_tool_approval.py -v
```

Expected: FAIL — `_verify_approval_token` does not exist; before_tool doesn't surface the threshold ticket.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/lifecycle.py — add helper near top
async def _verify_approval_token(
    *,
    tool_id: str,
    ticket: str,
    token: str | None,
) -> None:
    """Check that the supplied token unlocks ``ticket`` for ``tool_id``.

    Wraps the existing approvals service so we present a uniform error
    surface. Raises PersonaPolicyError when the token is missing or
    invalid; callers that don't need an approval call this only when
    ``check_action_threshold`` returned a ticket.
    """
    from app.agents.runtime.types import PersonaPolicyError

    if not token:
        raise PersonaPolicyError(
            f"Tool '{tool_id}' requires approval (ticket {ticket}); no token presented."
        )
    try:
        from app.services.approvals_service import verify_token  # type: ignore[import-not-found]
    except Exception:
        # If approvals service isn't available in this deployment, treat
        # the presence of a token as authoritative — never silently
        # let through a flagged action without one.
        return
    ok = await verify_token(tool_id=tool_id, ticket=ticket, token=token)
    if not ok:
        raise PersonaPolicyError(
            f"Approval token rejected for tool '{tool_id}', ticket {ticket}."
        )
```

```python
# app/agents/runtime/lifecycle.py — extend before_tool _callback after threshold check
threshold_result = await persona_gate.check_action_threshold(
    tool_id=tool_id,
    tool_args=args,
    persona_id=agent.persona_id,
)
if isinstance(threshold_result, dict) and threshold_result.get("required"):
    ticket = threshold_result.get("ticket") or ""
    token = None
    try:
        token = tool_context.state.get(f"approval_token::{tool_id}")
    except Exception:  # noqa: BLE001
        token = None
    await _verify_approval_token(tool_id=tool_id, ticket=ticket, token=token)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_before_tool_approval.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/lifecycle.py tests/unit/runtime/test_before_tool_approval.py
git commit -m "feat(runtime): enforce approval token check for above-threshold actions"
```

---

### Task 35: `after_tool` — record research result + emit progress event

**Files:**
- Edit: `app/agents/runtime/lifecycle.py`
- Test: `tests/unit/runtime/test_after_tool_callback.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_after_tool_callback.py
"""after_tool forwards results to research_gate.record_tool_result and emits progress."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.tools", MagicMock())


def _agent() -> MagicMock:
    from app.skills.registry import AgentID

    a = MagicMock()
    a.agent_id = AgentID.FIN
    a.user_id = "user-1"
    return a


def test_after_tool_records_research_and_emits_progress():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.research_gate") as mock_research, patch(
        "app.agents.runtime.lifecycle.publication"
    ) as mock_pub:
        mock_research.record_tool_result = AsyncMock(return_value=None)
        mock_pub.emit_progress_event = AsyncMock(return_value=None)

        cb = lifecycle.after_tool(_agent())
        tool = MagicMock()
        tool.name = "deep_research"
        ctx = MagicMock()
        ctx.state = {"_runtime_contract_id": "contract-X"}

        response = {"summary": "ok", "sources": []}
        asyncio.run(lifecycle._dispatch_async(cb, (tool, {"query": "q"}, ctx, response)))

    mock_research.record_tool_result.assert_awaited_once()
    kw = mock_research.record_tool_result.await_args.kwargs
    assert kw["contract_id"] == "contract-X"
    assert kw["tool_id"] == "deep_research"
    assert kw["result"] == response

    mock_pub.emit_progress_event.assert_awaited_once()
    ev_kw = mock_pub.emit_progress_event.await_args.kwargs
    assert ev_kw["user_id"] == "user-1"
    assert ev_kw["agent_id"].value == "FIN"
    assert ev_kw["item"] == "deep_research"
    assert ev_kw["status"] in {"in_progress", "started"}


def test_after_tool_handles_missing_contract():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.research_gate") as mock_research, patch(
        "app.agents.runtime.lifecycle.publication"
    ) as mock_pub:
        mock_research.record_tool_result = AsyncMock()
        mock_pub.emit_progress_event = AsyncMock(return_value=None)

        cb = lifecycle.after_tool(_agent())
        tool = MagicMock()
        tool.name = "list_skills"
        ctx = MagicMock()
        ctx.state = {}

        asyncio.run(lifecycle._dispatch_async(cb, (tool, {}, ctx, {"ok": True})))

    # No contract means we still emit progress but skip research recording.
    mock_research.record_tool_result.assert_not_awaited()
    mock_pub.emit_progress_event.assert_awaited_once()


def test_after_tool_logs_failures_for_retry():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.research_gate") as mock_research, patch(
        "app.agents.runtime.lifecycle.publication"
    ) as mock_pub:
        mock_research.record_tool_result = AsyncMock()
        mock_pub.emit_progress_event = AsyncMock()

        cb = lifecycle.after_tool(_agent())
        tool = MagicMock()
        tool.name = "wire_payment"
        ctx = MagicMock()
        ctx.state = {}

        # ADK error responses set {"error": "..."} on tool_response.
        asyncio.run(
            lifecycle._dispatch_async(
                cb, (tool, {"amount": 5000}, ctx, {"error": "rate limited"})
            )
        )

    failures = ctx.state.get("_runtime_tool_failures")
    assert failures, "tool failures must be recorded on state for retry policy"
    assert failures[0]["tool_id"] == "wire_payment"
    assert failures[0]["error"] == "rate limited"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_after_tool_callback.py -v
```

Expected: FAIL — `after_tool` is still a no-op.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/lifecycle.py — add `publication` import then replace after_tool stub
from app.agents.runtime import publication  # noqa: E402


def after_tool(agent: "PikarBaseAgent") -> Callable[..., Any]:
    """Return the ADK after_tool_callback bound to ``agent``."""

    async def _callback(
        tool: Any,
        args: dict[str, Any],
        tool_context: Any,
        tool_response: dict[str, Any],
    ) -> Any:
        tool_id = getattr(tool, "name", "") or ""
        contract_id = None
        try:
            contract_id = tool_context.state.get("_runtime_contract_id")
        except Exception:  # noqa: BLE001
            contract_id = None

        # 1. Forward to research gate when we're in initiative mode.
        if contract_id:
            try:
                await research_gate.record_tool_result(
                    agent=agent,
                    contract_id=contract_id,
                    tool_id=tool_id,
                    result=tool_response,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("[after_tool] research_gate.record failed: %s", exc)

        # 2. Emit a progress event to the workspace channel.
        status = "in_progress"
        if isinstance(tool_response, dict) and tool_response.get("error"):
            status = "blocked"

        try:
            await publication.emit_progress_event(
                user_id=agent.user_id,
                agent_id=agent.agent_id,
                contract_id=contract_id,
                item=tool_id,
                status=status,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[after_tool] emit_progress_event failed: %s", exc)

        # 3. Log failures on state so the retry policy in step_runtime
        #    (Section A) can react after the turn.
        if isinstance(tool_response, dict) and tool_response.get("error"):
            try:
                bucket = tool_context.state.setdefault("_runtime_tool_failures", [])
                bucket.append(
                    {
                        "tool_id": tool_id,
                        "args": args,
                        "error": tool_response.get("error"),
                    }
                )
            except Exception:  # noqa: BLE001
                pass

        return None

    _callback.__name__ = f"after_tool::{agent.agent_id.value}"
    return _callback
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_after_tool_callback.py -v
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/lifecycle.py tests/unit/runtime/test_after_tool_callback.py
git commit -m "feat(runtime): after_tool records research result and emits progress"
```

---

### Task 36: `after_agent` — run audit when artifact produced

**Files:**
- Edit: `app/agents/runtime/lifecycle.py`
- Test: `tests/unit/runtime/test_after_agent_audit.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_after_agent_audit.py
"""after_agent calls audit.audit_against_contract when artifacts are present."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())


def _agent() -> MagicMock:
    from app.skills.registry import AgentID

    a = MagicMock()
    a.agent_id = AgentID.FIN
    a.user_id = "user-1"
    a.persona_id = "founder"
    a.ops = MagicMock()
    return a


def _ctx(artifacts: list | None = None, contract: object | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.state = {
        "_runtime_artifacts": artifacts or [],
        "_runtime_task_contract": contract,
        "_runtime_research_result": None,
        "_runtime_classifier_mode": "initiative" if contract else "direct",
    }
    return ctx


def test_after_agent_runs_audit_in_initiative_mode_with_artifacts():
    from app.agents.runtime import lifecycle

    contract = MagicMock(name="TaskContract")
    artifacts = [{"kind": "doc", "ref": "drive://abc"}]

    fake_report = MagicMock(overall_status="pass")

    with patch("app.agents.runtime.lifecycle.audit") as mock_audit, patch(
        "app.agents.runtime.lifecycle.publication"
    ) as mock_pub, patch(
        "app.agents.runtime.lifecycle.compaction"
    ) as mock_compaction, patch(
        "app.agents.runtime.lifecycle._persist_task_execution",
        new=AsyncMock(return_value=None),
    ):
        mock_audit.audit_against_contract = AsyncMock(return_value=fake_report)
        mock_pub.publish_artifact = AsyncMock(return_value=None)
        mock_compaction.maybe_compact = AsyncMock(return_value=None)

        cb = lifecycle.after_agent(_agent())
        ctx = _ctx(artifacts=artifacts, contract=contract)
        asyncio.run(lifecycle._dispatch_async(cb, ctx))

    mock_audit.audit_against_contract.assert_awaited_once()
    kw = mock_audit.audit_against_contract.await_args.kwargs
    assert kw["contract"] is contract
    assert kw["artifacts"] == artifacts


def test_after_agent_skips_audit_in_direct_mode_without_artifacts():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.audit") as mock_audit, patch(
        "app.agents.runtime.lifecycle.publication"
    ) as mock_pub, patch(
        "app.agents.runtime.lifecycle.compaction"
    ) as mock_compaction, patch(
        "app.agents.runtime.lifecycle._persist_task_execution",
        new=AsyncMock(return_value=None),
    ):
        mock_audit.audit_against_contract = AsyncMock()
        mock_pub.publish_artifact = AsyncMock()
        mock_compaction.maybe_compact = AsyncMock(return_value=None)

        cb = lifecycle.after_agent(_agent())
        ctx = _ctx(artifacts=[], contract=None)
        asyncio.run(lifecycle._dispatch_async(cb, ctx))

    mock_audit.audit_against_contract.assert_not_awaited()
    mock_pub.publish_artifact.assert_not_awaited()


def test_after_agent_runs_audit_in_direct_mode_when_artifact_present():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.audit") as mock_audit, patch(
        "app.agents.runtime.lifecycle.publication"
    ) as mock_pub, patch(
        "app.agents.runtime.lifecycle.compaction"
    ) as mock_compaction, patch(
        "app.agents.runtime.lifecycle._persist_task_execution",
        new=AsyncMock(return_value=None),
    ):
        # Direct mode + an artifact → still audit (per spec § 9).
        fake_report = MagicMock(overall_status="pass")
        mock_audit.audit_against_contract = AsyncMock(return_value=fake_report)
        mock_pub.publish_artifact = AsyncMock()
        mock_compaction.maybe_compact = AsyncMock(return_value=None)

        cb = lifecycle.after_agent(_agent())
        artifacts = [{"kind": "report", "ref": "vault://xyz"}]
        ctx = _ctx(artifacts=artifacts, contract=None)
        asyncio.run(lifecycle._dispatch_async(cb, ctx))

    mock_audit.audit_against_contract.assert_awaited_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_after_agent_audit.py -v
```

Expected: FAIL — `after_agent` is still a no-op; `_persist_task_execution` and module imports `audit`/`publication`/`compaction` need wiring.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/lifecycle.py — add imports near top
from app.agents.runtime import audit, compaction  # noqa: E402


async def _persist_task_execution(
    *,
    agent: "PikarBaseAgent",
    state: dict[str, Any],
    audit_report: Any | None,
    artifacts: list[Any],
) -> None:
    """Insert a row into agent_task_executions for this turn.

    Implementation lives in Section D's publication path; we delegate
    so this module stays a thin orchestrator. This wrapper exists as a
    seam unit tests can monkeypatch.
    """
    try:
        from app.agents.runtime.publication import persist_task_execution
    except ImportError:
        # Section D not yet shipped; persistence is a no-op so the
        # lifecycle still works end-to-end during wave-based rollout.
        return
    try:
        await persist_task_execution(
            agent=agent,
            state=state,
            audit_report=audit_report,
            artifacts=artifacts,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[after_agent] persist_task_execution failed: %s", exc)


def after_agent(agent: "PikarBaseAgent") -> Callable[[Any], Any]:
    """Return the ADK after_agent_callback bound to ``agent``."""

    async def _callback(callback_context: Any) -> Any:
        state = getattr(callback_context, "state", {}) or {}
        artifacts = list(state.get("_runtime_artifacts") or [])
        contract = state.get("_runtime_task_contract")
        research_result = state.get("_runtime_research_result")
        classifier_mode = state.get("_runtime_classifier_mode") or "initiative"

        # 1. Self-audit per spec § 9:
        #    - initiative mode → always (even without artifacts, the
        #      audit reports gaps);
        #    - direct mode → only when an artifact was produced.
        audit_report = None
        should_audit = (classifier_mode == "initiative") or bool(artifacts)
        if should_audit and contract is not None:
            try:
                audit_report = await audit.audit_against_contract(
                    contract=contract,
                    artifacts=artifacts,
                    research=research_result,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("[after_agent] audit_against_contract failed: %s", exc)

        state["_runtime_audit_report"] = audit_report

        # 2. Compaction trigger.
        try:
            session = getattr(callback_context, "session", None)
            if session is not None:
                await compaction.maybe_compact(session, agent.ops.compaction)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[after_agent] maybe_compact failed: %s", exc)

        # 3. Artifact publication — Section D owns publish_artifact.
        if artifacts:
            try:
                for art in artifacts:
                    await publication.publish_artifact(
                        user_id=agent.user_id,
                        agent_id=agent.agent_id,
                        contract=contract,
                        artifact=art,
                        audit=audit_report,
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("[after_agent] publish_artifact failed: %s", exc)

        # 4. Persist the operational-history row.
        await _persist_task_execution(
            agent=agent,
            state=state,
            audit_report=audit_report,
            artifacts=artifacts,
        )

        return None

    _callback.__name__ = f"after_agent::{agent.agent_id.value}"
    return _callback
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_after_agent_audit.py -v
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/lifecycle.py tests/unit/runtime/test_after_agent_audit.py
git commit -m "feat(runtime): after_agent runs audit, compaction, publication, persistence"
```

---

### Task 37: `after_agent` — compaction wired and surfaced on session state

**Files:**
- Edit: `app/agents/runtime/lifecycle.py`
- Test: `tests/unit/runtime/test_after_agent_compaction.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_after_agent_compaction.py
"""after_agent invokes compaction.maybe_compact and stores the summary on state."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())


def _agent() -> MagicMock:
    from app.skills.registry import AgentID

    a = MagicMock()
    a.agent_id = AgentID.FIN
    a.user_id = "user-1"
    a.persona_id = "founder"
    a.ops = MagicMock()
    a.ops.compaction.trigger_token_count = 80_000
    a.ops.compaction.keep_last_n_turns = 12
    return a


def _ctx(approx_tokens: int = 0, events: int = 0) -> MagicMock:
    ctx = MagicMock()
    ctx.state = {
        "_runtime_artifacts": [],
        "_runtime_task_contract": None,
        "_runtime_research_result": None,
        "_runtime_classifier_mode": "direct",
    }
    session = MagicMock()
    session.id = "sess-1"
    session.approx_token_count = approx_tokens
    session.events = [{"i": i} for i in range(events)]
    ctx.session = session
    return ctx


def test_after_agent_calls_maybe_compact_with_agent_cfg():
    from app.agents.runtime import lifecycle

    fake_result = MagicMock(summary="SUM", dropped_event_count=20, kept_event_count=12)

    with patch("app.agents.runtime.lifecycle.audit") as mock_audit, patch(
        "app.agents.runtime.lifecycle.publication"
    ) as mock_pub, patch(
        "app.agents.runtime.lifecycle.compaction"
    ) as mock_compaction, patch(
        "app.agents.runtime.lifecycle._persist_task_execution",
        new=AsyncMock(return_value=None),
    ):
        mock_audit.audit_against_contract = AsyncMock()
        mock_pub.publish_artifact = AsyncMock()
        mock_compaction.maybe_compact = AsyncMock(return_value=fake_result)

        cb = lifecycle.after_agent(_agent())
        ctx = _ctx(approx_tokens=90_000, events=32)
        asyncio.run(lifecycle._dispatch_async(cb, ctx))

    mock_compaction.maybe_compact.assert_awaited_once()
    session_arg, cfg_arg = mock_compaction.maybe_compact.await_args.args
    assert session_arg is ctx.session
    assert cfg_arg.trigger_token_count == 80_000
    assert ctx.state.get("_runtime_compaction_summary") == "SUM"


def test_after_agent_handles_no_session_gracefully():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.audit") as mock_audit, patch(
        "app.agents.runtime.lifecycle.publication"
    ) as mock_pub, patch(
        "app.agents.runtime.lifecycle.compaction"
    ) as mock_compaction, patch(
        "app.agents.runtime.lifecycle._persist_task_execution",
        new=AsyncMock(return_value=None),
    ):
        mock_audit.audit_against_contract = AsyncMock()
        mock_pub.publish_artifact = AsyncMock()
        mock_compaction.maybe_compact = AsyncMock()

        cb = lifecycle.after_agent(_agent())
        ctx = _ctx()
        del ctx.session  # no session attribute
        asyncio.run(lifecycle._dispatch_async(cb, ctx))

    mock_compaction.maybe_compact.assert_not_awaited()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_after_agent_compaction.py -v
```

Expected: FAIL — Task 36 calls `maybe_compact` but does not record the summary on state.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/lifecycle.py — replace the compaction block inside after_agent _callback
try:
    session = getattr(callback_context, "session", None)
    if session is not None:
        result = await compaction.maybe_compact(session, agent.ops.compaction)
        if result is not None:
            state["_runtime_compaction_summary"] = result.summary
            state["_runtime_compaction_dropped_count"] = result.dropped_event_count
except Exception as exc:  # noqa: BLE001
    logger.warning("[after_agent] maybe_compact failed: %s", exc)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_after_agent_compaction.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/lifecycle.py tests/unit/runtime/test_after_agent_compaction.py
git commit -m "feat(runtime): expose compaction summary on session state for next turn"
```

---

### Task 38: `after_agent` — record handoff into initiative_phase_history

**Files:**
- Edit: `app/agents/runtime/lifecycle.py`
- Test: `tests/unit/runtime/test_after_agent_handoff_recording.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_after_agent_handoff_recording.py
"""after_agent calls handoff.record_handoff when the executive routed to a specialist."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())


def _agent_for_handoff(target: str = "FIN") -> MagicMock:
    from app.skills.registry import AgentID

    a = MagicMock()
    a.agent_id = AgentID(target)
    a.user_id = "user-1"
    a.persona_id = "founder"
    a.ops = MagicMock()
    return a


def _ctx(initiative_id: str | None, phase: str | None, packet) -> MagicMock:
    ctx = MagicMock()
    ctx.state = {
        "_runtime_artifacts": [],
        "_runtime_task_contract": None,
        "_runtime_research_result": None,
        "_runtime_classifier_mode": "initiative",
        "_runtime_initiative_id": initiative_id,
        "_runtime_initiative_phase": phase,
        "last_handoff_packet": packet,
    }
    return ctx


def test_after_agent_records_handoff_when_packet_present_in_initiative():
    from app.agents.runtime import lifecycle

    packet_data = {
        "intent": "Forecast Q3",
        "evidence": [],
        "constraints": [],
        "expected_output_shape": "text",
        "source_agent": "executive",
        "target_agent": "FinancialAnalysisAgent",
        "correlation_id": "corr-1",
    }

    with patch("app.agents.runtime.lifecycle.audit") as mock_audit, patch(
        "app.agents.runtime.lifecycle.publication"
    ) as mock_pub, patch(
        "app.agents.runtime.lifecycle.compaction"
    ) as mock_compaction, patch(
        "app.agents.runtime.lifecycle.handoff"
    ) as mock_handoff, patch(
        "app.agents.runtime.lifecycle._persist_task_execution",
        new=AsyncMock(return_value=None),
    ):
        mock_audit.audit_against_contract = AsyncMock()
        mock_pub.publish_artifact = AsyncMock()
        mock_compaction.maybe_compact = AsyncMock(return_value=None)
        mock_handoff.record_handoff = AsyncMock(return_value="packet-row-1")

        cb = lifecycle.after_agent(_agent_for_handoff())
        ctx = _ctx(initiative_id="init-X", phase="validation", packet=packet_data)
        asyncio.run(lifecycle._dispatch_async(cb, ctx))

    mock_handoff.record_handoff.assert_awaited_once()
    kw = mock_handoff.record_handoff.await_args.kwargs
    assert kw["initiative_id"] == "init-X"
    assert kw["phase"] == "validation"
    # Packet should have been validated into a HandoffPacket model.
    assert kw["packet"].target_agent == "FinancialAnalysisAgent"


def test_after_agent_skips_handoff_when_no_packet():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.audit") as mock_audit, patch(
        "app.agents.runtime.lifecycle.publication"
    ) as mock_pub, patch(
        "app.agents.runtime.lifecycle.compaction"
    ) as mock_compaction, patch(
        "app.agents.runtime.lifecycle.handoff"
    ) as mock_handoff, patch(
        "app.agents.runtime.lifecycle._persist_task_execution",
        new=AsyncMock(return_value=None),
    ):
        mock_audit.audit_against_contract = AsyncMock()
        mock_pub.publish_artifact = AsyncMock()
        mock_compaction.maybe_compact = AsyncMock(return_value=None)
        mock_handoff.record_handoff = AsyncMock()

        cb = lifecycle.after_agent(_agent_for_handoff())
        ctx = _ctx(initiative_id="init-X", phase="validation", packet=None)
        asyncio.run(lifecycle._dispatch_async(cb, ctx))

    mock_handoff.record_handoff.assert_not_awaited()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_after_agent_handoff_recording.py -v
```

Expected: FAIL — `after_agent` does not currently consult `last_handoff_packet`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/lifecycle.py — add `handoff` import then insert near top of after_agent _callback
from app.agents.runtime import handoff  # noqa: E402

# inside after_agent _callback, after artifacts/audit, before persistence:
packet_data = state.get("last_handoff_packet")
if isinstance(packet_data, dict):
    try:
        from app.agents.handoff_packet import HandoffPacket

        packet = HandoffPacket(**packet_data)
        initiative_id = state.get("_runtime_initiative_id")
        phase = state.get("_runtime_initiative_phase")
        await handoff.record_handoff(
            packet=packet,
            initiative_id=initiative_id,
            phase=phase,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[after_agent] record_handoff failed: %s", exc)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_after_agent_handoff_recording.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/lifecycle.py tests/unit/runtime/test_after_agent_handoff_recording.py
git commit -m "feat(runtime): record handoff history row from after_agent callback"
```

---

### Task 39: Skill injection — `consult_applicable_skills` tool factory

**Files:**
- Edit: `app/agents/runtime/skill_injection.py`
- Test: `tests/unit/runtime/test_consult_applicable_skills.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_consult_applicable_skills.py
"""consult_applicable_skills wraps match_and_inject as an agent tool."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())


def test_consult_applicable_skills_returns_dict_with_block():
    from app.agents.runtime import skill_injection
    from app.skills.registry import AgentID

    agent = MagicMock()
    agent.agent_id = AgentID.FIN
    agent.ops.skills.allowed_ids = ["*"]
    agent.ops.skills.injection.top_k = 3
    agent.ops.skills.injection.similarity_floor = 0.5

    fake_block = "## Relevant skills\n- finance:dcf (score 0.91, finance): DCF\n"
    with patch.object(
        skill_injection,
        "match_and_inject",
        AsyncMock(return_value=fake_block),
    ):
        tool = skill_injection.build_consult_applicable_skills_tool(agent)
        result = asyncio.run(tool("forecast revenue"))

    assert result["success"] is True
    assert "finance:dcf" in result["skills_block"]
    assert result["agent_id"] == "FIN"


def test_consult_applicable_skills_returns_empty_block_when_no_matches():
    from app.agents.runtime import skill_injection
    from app.skills.registry import AgentID

    agent = MagicMock()
    agent.agent_id = AgentID.FIN
    agent.ops.skills.allowed_ids = ["*"]
    agent.ops.skills.injection.top_k = 3
    agent.ops.skills.injection.similarity_floor = 0.99

    with patch.object(
        skill_injection,
        "match_and_inject",
        AsyncMock(return_value=""),
    ):
        tool = skill_injection.build_consult_applicable_skills_tool(agent)
        result = asyncio.run(tool("something obscure"))

    assert result["success"] is True
    assert result["skills_block"] == ""
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_consult_applicable_skills.py -v
```

Expected: FAIL — `build_consult_applicable_skills_tool` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/skill_injection.py — add at bottom

def build_consult_applicable_skills_tool(agent: "PikarBaseAgent") -> Any:
    """Return an agent-callable tool that re-runs skill matching mid-turn.

    Useful when the user's scope shifts after the initial injection.
    Returns the rendered block instead of mutating state so the agent
    can decide where to slot it in its next reasoning step.
    """
    from app.agents.runtime.types import DirectRequest

    async def consult_applicable_skills(task: str) -> dict[str, Any]:
        """Re-match this agent's skills against ``task`` and return a markdown block."""
        try:
            block = await match_and_inject(DirectRequest(message=task), agent)
            return {
                "success": True,
                "agent_id": agent.agent_id.value,
                "skills_block": block,
            }
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    consult_applicable_skills.__name__ = "consult_applicable_skills"
    return consult_applicable_skills
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_consult_applicable_skills.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/skill_injection.py tests/unit/runtime/test_consult_applicable_skills.py
git commit -m "feat(runtime): add consult_applicable_skills tool for mid-turn re-matching"
```

---

### Task 40: Memory retrieval — recency boost helper

**Files:**
- Edit: `app/agents/runtime/memory_retrieval.py`
- Test: `tests/unit/runtime/test_memory_retrieval_recency.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_memory_retrieval_recency.py
"""_apply_recency_boost lifts recent reports up the ranking without dropping older ones."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _row(sim: float, days_ago: int, goal: str) -> dict:
    ts = (datetime.now(tz=timezone.utc) - timedelta(days=days_ago)).isoformat()
    return {
        "content": f"# {goal}",
        "similarity": sim,
        "metadata": {"goal": goal, "created_at": ts, "kind": "agent_report"},
    }


def test_recency_boost_prefers_recent_when_similarity_close():
    from app.agents.runtime.memory_retrieval import _apply_recency_boost

    rows = [
        _row(sim=0.81, days_ago=200, goal="old"),
        _row(sim=0.80, days_ago=3, goal="recent"),
    ]
    out = _apply_recency_boost(rows)
    assert out[0]["metadata"]["goal"] == "recent"


def test_recency_boost_does_not_override_large_similarity_gap():
    from app.agents.runtime.memory_retrieval import _apply_recency_boost

    rows = [
        _row(sim=0.95, days_ago=200, goal="old_relevant"),
        _row(sim=0.50, days_ago=2, goal="recent_irrelevant"),
    ]
    out = _apply_recency_boost(rows)
    assert out[0]["metadata"]["goal"] == "old_relevant"


def test_recency_boost_handles_missing_timestamps():
    from app.agents.runtime.memory_retrieval import _apply_recency_boost

    rows = [
        {"content": "a", "similarity": 0.9, "metadata": {"goal": "a"}},
        {"content": "b", "similarity": 0.85, "metadata": {"goal": "b"}},
    ]
    # Should not raise and should preserve original order on tie.
    out = _apply_recency_boost(rows)
    assert [r["metadata"]["goal"] for r in out] == ["a", "b"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_memory_retrieval_recency.py -v
```

Expected: FAIL — `_apply_recency_boost` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/memory_retrieval.py — add near other helpers

from datetime import datetime, timezone


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts or not isinstance(ts, str):
        return None
    try:
        # Accept both '...Z' and '...+00:00' forms.
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _apply_recency_boost(
    rows: list[dict[str, Any]],
    *,
    boost_window_days: int = 30,
    max_boost: float = 0.05,
) -> list[dict[str, Any]]:
    """Re-rank rows by ``similarity + recency_boost`` and return the new order.

    Only nudges (max_boost defaults to 0.05) so a strong-match older
    report still beats a weak-match recent one — recency is a
    tiebreaker, not a substitute for relevance.
    """
    now = datetime.now(tz=timezone.utc)
    scored: list[tuple[float, int, dict[str, Any]]] = []
    for idx, r in enumerate(rows or []):
        sim = float(r.get("similarity", 0.0) or 0.0)
        meta = r.get("metadata") or {}
        ts = _parse_iso(meta.get("created_at"))
        boost = 0.0
        if ts is not None:
            age_days = max(0.0, (now - ts).total_seconds() / 86400.0)
            if age_days <= boost_window_days:
                boost = max_boost * (1.0 - age_days / boost_window_days)
        scored.append((sim + boost, idx, r))

    scored.sort(key=lambda t: (-t[0], t[1]))
    return [r for _, _, r in scored]
```

Then call it from `retrieve_relevant_history` after the initiative-priority pass (before truncating to `eff_top_k`):

```python
# inside retrieve_relevant_history, after the initiative-priority sort:
rows = _apply_recency_boost(rows)
return _render_prior_work(rows[:eff_top_k])
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_memory_retrieval_recency.py -v
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/memory_retrieval.py tests/unit/runtime/test_memory_retrieval_recency.py
git commit -m "feat(runtime): apply recency boost as a tiebreaker in memory retrieval"
```

---

### Task 41: Compaction — cache compaction summary on session state for next turn

**Files:**
- Edit: `app/agents/runtime/compaction.py`
- Test: `tests/unit/runtime/test_compaction_summary_cache.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_compaction_summary_cache.py
"""maybe_compact stores its summary on session for the next turn to consume."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())


def _session(events: int, approx_tokens: int) -> MagicMock:
    s = MagicMock()
    s.id = "sess-1"
    s.events = [{"i": i} for i in range(events)]
    s.approx_token_count = approx_tokens
    s.state = {}
    return s


def _cfg(trigger: int = 80_000, keep: int = 12) -> MagicMock:
    c = MagicMock()
    c.trigger_token_count = trigger
    c.keep_last_n_turns = keep
    return c


def test_compaction_writes_summary_to_session_state():
    from app.agents.runtime import compaction

    with patch.object(
        compaction,
        "summarize_dropped_events",
        AsyncMock(return_value="SUM"),
    ):
        sess = _session(events=40, approx_tokens=90_000)
        result = asyncio.run(compaction.maybe_compact(sess, _cfg()))

    assert result is not None
    assert sess.state.get("_runtime_compaction_summary") == "SUM"
    assert sess.state.get("_runtime_compaction_dropped_count") == 28


def test_compaction_no_state_attribute_is_silent():
    from app.agents.runtime import compaction

    with patch.object(
        compaction,
        "summarize_dropped_events",
        AsyncMock(return_value="SUM"),
    ):
        sess = MagicMock()
        sess.id = "sess-2"
        sess.events = [{"i": i} for i in range(40)]
        sess.approx_token_count = 90_000
        del sess.state  # no state attribute; must not crash
        result = asyncio.run(compaction.maybe_compact(sess, _cfg()))

    assert result is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_compaction_summary_cache.py -v
```

Expected: FAIL — `maybe_compact` doesn't yet write to `session.state`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/compaction.py — extend maybe_compact just before `return CompactionResult(...)`

result = CompactionResult(
    summary=summary,
    dropped_event_count=len(dropped),
    kept_event_count=len(kept),
)
try:
    state = getattr(session, "state", None)
    if isinstance(state, dict):
        state["_runtime_compaction_summary"] = result.summary
        state["_runtime_compaction_dropped_count"] = result.dropped_event_count
except Exception as exc:  # noqa: BLE001
    logger.debug("[compaction] could not persist summary to session.state: %s", exc)
return result
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_compaction_summary_cache.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/compaction.py tests/unit/runtime/test_compaction_summary_cache.py
git commit -m "feat(runtime): persist compaction summary on session.state for next turn"
```

---

### Task 42: Handoff — model_dump fallback when ``packet.model_dump`` missing

**Files:**
- Edit: `app/agents/runtime/handoff.py`
- Test: `tests/unit/runtime/test_handoff_packet_serialization.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_handoff_packet_serialization.py
"""record_handoff serializes a real HandoffPacket without losing fields."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


def test_record_handoff_serializes_real_packet():
    from app.agents.handoff_packet import HandoffPacket
    from app.agents.runtime import handoff

    packet = HandoffPacket(
        intent="Forecast Q3",
        evidence=["last call mentioned Q3 plan"],
        constraints=["due Friday"],
        expected_output_shape="text",
        source_agent="executive",
        target_agent="FinancialAnalysisAgent",
        correlation_id="corr-1",
    )

    client = MagicMock()
    insert = MagicMock()
    execute = AsyncMock(return_value=MagicMock(data=[{"id": "row-1"}]))
    insert.execute = execute
    client.table.return_value.insert.return_value = insert
    get_client = AsyncMock(return_value=client)

    with patch.object(handoff, "get_async_client", get_client):
        packet_id = asyncio.run(
            handoff.record_handoff(
                packet=packet,
                initiative_id="init-X",
                phase="validation",
            )
        )

    assert packet_id is not None
    payload = client.table().insert.call_args.args[0]
    assert payload["packet"]["intent"] == "Forecast Q3"
    assert payload["packet"]["evidence"] == ["last call mentioned Q3 plan"]
    assert payload["packet"]["constraints"] == ["due Friday"]
    assert payload["packet"]["target_agent"] == "FinancialAnalysisAgent"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_handoff_packet_serialization.py -v
```

Expected: PASS already (the implementation calls `packet.model_dump()` which Pydantic supplies). This test pins the contract so the row payload never silently drops fields.

- [ ] **Step 3: Write minimal implementation**

No change required if Step 2 passed. If it failed, ensure the row payload includes the full `packet.model_dump()`:

```python
# app/agents/runtime/handoff.py — inside record_handoff
row = {
    "initiative_id": initiative_id,
    "phase": phase,
    "event": "handoff",
    "from_agent": packet.source_agent,
    "to_agent": packet.target_agent,
    "packet_id": packet_id,
    "packet": packet.model_dump() if hasattr(packet, "model_dump") else dict(packet),
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_handoff_packet_serialization.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/handoff.py tests/unit/runtime/test_handoff_packet_serialization.py
git commit -m "test(runtime): pin handoff packet serialization in history rows"
```

---

### Task 43: Lifecycle — failure-isolation guarantee for all four callbacks

**Files:**
- Test: `tests/unit/runtime/test_lifecycle_failure_isolation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_lifecycle_failure_isolation.py
"""All four lifecycle callbacks must isolate failures from the agent turn.

Specifically:
- before_agent: only InitiativeContractError propagates; all other
  exceptions are swallowed so the model still runs.
- before_tool: PersonaPolicyError and ResearchGateError propagate
  (they're intentional blocks); everything else is swallowed.
- after_tool / after_agent: nothing propagates — failures here must
  never break a turn that already produced output.
"""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.tools", MagicMock())


def _agent() -> MagicMock:
    from app.skills.registry import AgentID

    a = MagicMock()
    a.agent_id = AgentID.FIN
    a.persona_id = "founder"
    a.user_id = "user-1"
    a.ops = MagicMock()
    return a


def _ctx() -> MagicMock:
    ctx = MagicMock()
    ctx.state = {
        "_runtime_artifacts": [],
        "_runtime_task_contract": None,
        "_runtime_research_result": None,
        "_runtime_classifier_mode": "direct",
    }
    part = MagicMock()
    part.text = "hi"
    content = MagicMock()
    content.parts = [part]
    ctx.user_content = content
    return ctx


def test_before_tool_swallows_unknown_exceptions():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.persona_gate") as mock_persona, patch(
        "app.agents.runtime.lifecycle.research_gate"
    ) as mock_research:
        mock_persona.check_tool_allowed.return_value = None
        mock_persona.check_action_threshold = AsyncMock(
            side_effect=RuntimeError("boom")  # NOT a PersonaPolicyError
        )
        mock_research.is_open.return_value = False

        cb = lifecycle.before_tool(_agent())
        tool = MagicMock()
        tool.name = "list_skills"
        ctx = MagicMock()
        ctx.state = {}
        # Should not raise.
        asyncio.run(lifecycle._dispatch_async(cb, (tool, {}, ctx)))


def test_after_tool_never_raises():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.research_gate") as mock_research, patch(
        "app.agents.runtime.lifecycle.publication"
    ) as mock_pub:
        mock_research.record_tool_result = AsyncMock(side_effect=RuntimeError("a"))
        mock_pub.emit_progress_event = AsyncMock(side_effect=RuntimeError("b"))

        cb = lifecycle.after_tool(_agent())
        tool = MagicMock()
        tool.name = "deep_research"
        ctx = MagicMock()
        ctx.state = {"_runtime_contract_id": "c1"}
        # Must not raise.
        asyncio.run(lifecycle._dispatch_async(cb, (tool, {}, ctx, {"ok": True})))


def test_after_agent_never_raises():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.audit") as mock_audit, patch(
        "app.agents.runtime.lifecycle.publication"
    ) as mock_pub, patch(
        "app.agents.runtime.lifecycle.compaction"
    ) as mock_compaction, patch(
        "app.agents.runtime.lifecycle._persist_task_execution",
        new=AsyncMock(side_effect=RuntimeError("persist failed")),
    ):
        mock_audit.audit_against_contract = AsyncMock(side_effect=RuntimeError("a"))
        mock_pub.publish_artifact = AsyncMock(side_effect=RuntimeError("b"))
        mock_compaction.maybe_compact = AsyncMock(side_effect=RuntimeError("c"))

        cb = lifecycle.after_agent(_agent())
        ctx = _ctx()
        # Must not raise even though every sub-call blew up.
        asyncio.run(lifecycle._dispatch_async(cb, ctx))


def test_before_tool_propagates_persona_and_research_gate_errors():
    from app.agents.runtime import lifecycle
    from app.agents.runtime.types import PersonaPolicyError, ResearchGateError

    # PersonaPolicyError propagates from check_tool_allowed.
    with patch("app.agents.runtime.lifecycle.persona_gate") as mock_persona, patch(
        "app.agents.runtime.lifecycle.research_gate"
    ) as mock_research:
        mock_persona.check_tool_allowed.side_effect = PersonaPolicyError("denied")
        mock_research.is_open.return_value = False

        cb = lifecycle.before_tool(_agent())
        tool = MagicMock()
        tool.name = "send_email"
        ctx = MagicMock()
        ctx.state = {}

        try:
            asyncio.run(lifecycle._dispatch_async(cb, (tool, {}, ctx)))
            raised = False
        except PersonaPolicyError:
            raised = True
        assert raised

    # ResearchGateError propagates when gate is open and tool isn't research.
    with patch("app.agents.runtime.lifecycle.persona_gate") as mock_persona, patch(
        "app.agents.runtime.lifecycle.research_gate"
    ) as mock_research:
        mock_persona.check_tool_allowed.return_value = None
        mock_persona.check_action_threshold = AsyncMock(return_value=None)
        mock_research.is_open.return_value = True
        mock_research.is_research_tool.return_value = False

        cb = lifecycle.before_tool(_agent())
        tool = MagicMock()
        tool.name = "draft"
        ctx = MagicMock()
        ctx.state = {"_runtime_contract_id": "c1"}

        try:
            asyncio.run(lifecycle._dispatch_async(cb, (tool, {}, ctx)))
            raised = False
        except ResearchGateError:
            raised = True
        assert raised
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_lifecycle_failure_isolation.py -v
```

Expected: some tests likely PASS (after_agent is already wrapped), but `before_tool` currently doesn't catch `RuntimeError` from `check_action_threshold`, so `test_before_tool_swallows_unknown_exceptions` will FAIL.

- [ ] **Step 3: Write minimal implementation**

Wrap the non-gate calls inside `before_tool` so only the two intentional exception types escape:

```python
# app/agents/runtime/lifecycle.py — before_tool _callback rewritten with selective propagation
async def _callback(tool: Any, args: dict[str, Any], tool_context: Any) -> Any:
    tool_id = getattr(tool, "name", "") or ""

    # Allow/deny — intentional propagation.
    persona_gate.check_tool_allowed(tool_id, agent.persona_id)

    # Threshold — propagate PersonaPolicyError only; swallow other errors.
    threshold_result: Any = None
    try:
        threshold_result = await persona_gate.check_action_threshold(
            tool_id=tool_id,
            tool_args=args,
            persona_id=agent.persona_id,
        )
    except PersonaPolicyError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("[before_tool] threshold check failed (swallowed): %s", exc)

    # Approval token, if threshold flagged it.
    if isinstance(threshold_result, dict) and threshold_result.get("required"):
        ticket = threshold_result.get("ticket") or ""
        token = None
        try:
            token = tool_context.state.get(f"approval_token::{tool_id}")
        except Exception:  # noqa: BLE001
            token = None
        await _verify_approval_token(tool_id=tool_id, ticket=ticket, token=token)

    # Research gate — propagate ResearchGateError only.
    contract_id = None
    try:
        contract_id = tool_context.state.get("_runtime_contract_id")
    except Exception:  # noqa: BLE001
        contract_id = None

    if contract_id:
        try:
            gate_open = research_gate.is_open(agent, contract_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[before_tool] research_gate.is_open failed: %s", exc)
            gate_open = False
        if gate_open and not research_gate.is_research_tool(tool_id):
            raise ResearchGateError(
                f"Research gate open for contract {contract_id}; "
                f"tool '{tool_id}' is not in the research tool set."
            )

    return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_lifecycle_failure_isolation.py -v
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/lifecycle.py tests/unit/runtime/test_lifecycle_failure_isolation.py
git commit -m "feat(runtime): isolate non-intentional failures from agent turns"
```

---

### Task 44: Skill injection — exclude direct-mode requests by default flag

**Files:**
- Edit: `app/agents/runtime/lifecycle.py`
- Test: `tests/unit/runtime/test_before_agent_direct_skip.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_before_agent_direct_skip.py
"""before_agent honors ops.skills.injection.skip_direct_mode if set."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())


def _agent(skip_direct: bool) -> MagicMock:
    from app.skills.registry import AgentID

    a = MagicMock()
    a.agent_id = AgentID.FIN
    a.persona_id = "founder"
    a.ops = MagicMock()
    a.ops.skills.injection.top_k = 5
    a.ops.skills.injection.similarity_floor = 0.65
    a.ops.skills.injection.skip_direct_mode = skip_direct
    return a


def _ctx(message: str = "what's our Q3 revenue?") -> MagicMock:
    ctx = MagicMock()
    ctx.state = {}
    part = MagicMock()
    part.text = message
    content = MagicMock()
    content.parts = [part]
    ctx.user_content = content
    return ctx


def test_skill_injection_skipped_when_direct_and_flag_set():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.task_router") as mock_router, patch(
        "app.agents.runtime.lifecycle.skill_injection"
    ) as mock_skill, patch(
        "app.agents.runtime.lifecycle.memory_retrieval"
    ) as mock_mem, patch(
        "app.agents.runtime.lifecycle.persona_gate"
    ) as mock_persona:
        mock_router.classify.return_value = MagicMock(mode="direct", signal="rule")
        mock_skill.match_and_inject = AsyncMock(return_value="## Relevant skills\n- s\n")
        mock_mem.retrieve_relevant_history = AsyncMock(return_value="")
        mock_persona.apply_prompt_fragments.return_value = ""

        cb = lifecycle.before_agent(_agent(skip_direct=True))
        ctx = _ctx()
        asyncio.run(lifecycle._dispatch_async(cb, ctx))

    mock_skill.match_and_inject.assert_not_awaited()


def test_skill_injection_runs_when_initiative_even_with_flag_set():
    from app.agents.runtime import lifecycle

    with patch("app.agents.runtime.lifecycle.task_router") as mock_router, patch(
        "app.agents.runtime.lifecycle.skill_injection"
    ) as mock_skill, patch(
        "app.agents.runtime.lifecycle.memory_retrieval"
    ) as mock_mem, patch(
        "app.agents.runtime.lifecycle.persona_gate"
    ) as mock_persona:
        mock_router.classify.return_value = MagicMock(mode="initiative", signal="llm")
        mock_skill.match_and_inject = AsyncMock(return_value="## Relevant skills\n- s\n")
        mock_mem.retrieve_relevant_history = AsyncMock(return_value="")
        mock_persona.apply_prompt_fragments.return_value = ""

        cb = lifecycle.before_agent(_agent(skip_direct=True))
        ctx = _ctx()
        asyncio.run(lifecycle._dispatch_async(cb, ctx))

    mock_skill.match_and_inject.assert_awaited_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_before_agent_direct_skip.py -v
```

Expected: FAIL — `before_agent` currently always runs skill injection.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/lifecycle.py — inside before_agent _callback, around the skill block:
mode = callback_context.state.get("_runtime_classifier_mode", "initiative")
skip_direct = bool(
    getattr(getattr(agent.ops.skills, "injection", None), "skip_direct_mode", False)
)
if not (mode == "direct" and skip_direct):
    try:
        block = await skill_injection.match_and_inject(request, agent)
        if block:
            blocks.append(block)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[before_agent] skill_injection failed: %s", exc)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_before_agent_direct_skip.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/lifecycle.py tests/unit/runtime/test_before_agent_direct_skip.py
git commit -m "feat(runtime): honor skip_direct_mode flag for skill injection in direct turns"
```

---

### Task 45: End-to-end lifecycle smoke test for one full turn

**Files:**
- Test: `tests/unit/runtime/test_lifecycle_full_turn.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_lifecycle_full_turn.py
"""Full lifecycle: before_agent -> before_tool -> after_tool -> after_agent.

Exercises the integration of the four callbacks against fully-mocked
runtime submodules to assert ordering, state mutation, and that the
final state carries everything downstream layers need.
"""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.tools", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())


def _agent() -> MagicMock:
    from app.skills.registry import AgentID

    a = MagicMock()
    a.agent_id = AgentID.FIN
    a.persona_id = "founder"
    a.user_id = "user-1"
    a.ops = MagicMock()
    a.ops.skills.injection.top_k = 5
    a.ops.skills.injection.similarity_floor = 0.65
    a.ops.skills.injection.skip_direct_mode = False
    a.ops.compaction.trigger_token_count = 80_000
    a.ops.compaction.keep_last_n_turns = 12
    return a


def _ctx() -> MagicMock:
    ctx = MagicMock()
    ctx.state = {"user_id": "user-1"}
    part = MagicMock()
    part.text = "Forecast Q3 revenue"
    content = MagicMock()
    content.parts = [part]
    ctx.user_content = content
    session = MagicMock()
    session.id = "sess-1"
    session.events = [{"i": i} for i in range(40)]
    session.approx_token_count = 90_000
    session.state = ctx.state  # share dict so summary lands where after_agent reads
    ctx.session = session
    return ctx


def test_full_lifecycle_turn_records_everything_downstream_needs():
    from app.agents.runtime import lifecycle

    fake_classifier = MagicMock(mode="initiative", signal="rule")
    fake_audit_report = MagicMock(overall_status="pass")
    fake_compaction = MagicMock(
        summary="SUMMARY", dropped_event_count=28, kept_event_count=12
    )

    with patch("app.agents.runtime.lifecycle.task_router") as mock_router, patch(
        "app.agents.runtime.lifecycle.skill_injection"
    ) as mock_skill, patch(
        "app.agents.runtime.lifecycle.memory_retrieval"
    ) as mock_mem, patch(
        "app.agents.runtime.lifecycle.persona_gate"
    ) as mock_persona, patch(
        "app.agents.runtime.lifecycle.research_gate"
    ) as mock_research, patch(
        "app.agents.runtime.lifecycle.audit"
    ) as mock_audit, patch(
        "app.agents.runtime.lifecycle.publication"
    ) as mock_pub, patch(
        "app.agents.runtime.lifecycle.compaction"
    ) as mock_compaction, patch(
        "app.agents.runtime.lifecycle._persist_task_execution",
        new=AsyncMock(return_value=None),
    ):
        mock_router.classify.return_value = fake_classifier
        mock_skill.match_and_inject = AsyncMock(
            return_value="## Relevant skills\n- finance:dcf\n"
        )
        mock_mem.retrieve_relevant_history = AsyncMock(
            return_value="## Prior work\n- last Q2 report\n"
        )
        mock_persona.apply_prompt_fragments.return_value = "## Persona policy\n- founder\n"
        mock_persona.check_tool_allowed.return_value = None
        mock_persona.check_action_threshold = AsyncMock(return_value=None)
        mock_research.is_open.return_value = False
        mock_research.record_tool_result = AsyncMock(return_value=None)
        mock_pub.emit_progress_event = AsyncMock(return_value=None)
        mock_pub.publish_artifact = AsyncMock(return_value=None)
        mock_audit.audit_against_contract = AsyncMock(return_value=fake_audit_report)
        mock_compaction.maybe_compact = AsyncMock(return_value=fake_compaction)

        agent = _agent()
        ctx = _ctx()

        # 1. before_agent
        before_a = lifecycle.before_agent(agent)
        asyncio.run(lifecycle._dispatch_async(before_a, ctx))

        # 2. before_tool
        before_t = lifecycle.before_tool(agent)
        tool = MagicMock()
        tool.name = "draft_forecast_doc"
        asyncio.run(lifecycle._dispatch_async(before_t, (tool, {"period": "Q3"}, ctx)))

        # 3. after_tool — tool produced an artifact; record it on state so after_agent sees it.
        after_t = lifecycle.after_tool(agent)
        response = {"doc_ref": "vault://forecast-q3"}
        ctx.state.setdefault("_runtime_artifacts", []).append(
            {"kind": "doc", "ref": "vault://forecast-q3", "summary": "Q3 forecast draft"}
        )
        asyncio.run(
            lifecycle._dispatch_async(after_t, (tool, {"period": "Q3"}, ctx, response))
        )

        # 4. after_agent
        after_a = lifecycle.after_agent(agent)
        asyncio.run(lifecycle._dispatch_async(after_a, ctx))

    # Assertions: state carries the full breadcrumb trail.
    assert ctx.state["_runtime_classifier_mode"] == "initiative"
    assert "Relevant skills" in ctx.state["_runtime_injected_blocks"]
    assert "Prior work" in ctx.state["_runtime_injected_blocks"]
    assert "Persona policy" in ctx.state["_runtime_injected_blocks"]
    assert ctx.state["_runtime_audit_report"] is fake_audit_report
    assert ctx.state["_runtime_compaction_summary"] == "SUMMARY"
    mock_pub.publish_artifact.assert_awaited()  # at least one artifact published
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_lifecycle_full_turn.py -v
```

Expected: PASS already if Tasks 21–44 landed cleanly. Treat this task as the integration smoke gate — fix any incidental drift surfaced here before moving on.

- [ ] **Step 3: Write minimal implementation**

No new implementation; this task is a regression gate. If a sub-assertion fails, root-cause it back to the relevant prior task (e.g. injected blocks not landing means Task 30 wiring is off).

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/ -v
```

Expected: PASS (entire `tests/unit/runtime/` suite green — 30+ tests across Tasks 21–45).

- [ ] **Step 5: Commit**

```bash
git add tests/unit/runtime/test_lifecycle_full_turn.py
git commit -m "test(runtime): end-to-end smoke test for full lifecycle turn"
```

---

**Section B exit gate:** every test in `tests/unit/runtime/` passes under `uv run pytest tests/unit/runtime/ -v`. Section A (which wires the four factories into `PikarBaseAgent.__init__`) and Section C (which ships `task_router`, `persona_gate`, `research_gate`, and `audit` modules) become safe to import; nothing in Section B requires Section D's `publication` module to exist beyond the `try/except ImportError` fallback in `_persist_task_execution`.

---

## Section C — Gates: research, audit, persona, router (Tasks 46–75)

### Task 46: RESEARCH_TOOL_IDS constant and module skeleton

**Files:**
- Create: `app/agents/runtime/research_gate.py`
- Test: `tests/unit/agents/runtime/test_research_gate_constants.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_research_gate_constants.py
"""Verify the research-tool-id allow-set is a frozenset with the exact 5 IDs from spec § 7."""
from app.agents.runtime.research_gate import RESEARCH_TOOL_IDS


def test_research_tool_ids_is_frozenset() -> None:
    assert isinstance(RESEARCH_TOOL_IDS, frozenset)


def test_research_tool_ids_matches_spec() -> None:
    assert RESEARCH_TOOL_IDS == frozenset({
        "deep_research",
        "tavily_search",
        "firecrawl_scrape",
        "google_search",
        "quick_research",
    })


def test_research_tool_ids_is_immutable() -> None:
    import pytest
    with pytest.raises(AttributeError):
        RESEARCH_TOOL_IDS.add("other")  # type: ignore[attr-defined]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_research_gate_constants.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.agents.runtime.research_gate'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/research_gate.py
# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Research-completion gate per spec § 7.

The gate blocks all non-research tool calls until the research run for a
given (task_contract_id, agent_id) is marked complete. Set of allowed
research tool IDs is the canonical RESEARCH_TOOL_IDS frozenset below.
"""

from __future__ import annotations

RESEARCH_TOOL_IDS: frozenset[str] = frozenset({
    "deep_research",
    "tavily_search",
    "firecrawl_scrape",
    "google_search",
    "quick_research",
})
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_research_gate_constants.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/research_gate.py tests/unit/agents/runtime/test_research_gate_constants.py
git commit -m "feat(runtime): add RESEARCH_TOOL_IDS constant for research gate"
```

---

### Task 47: `open_gate` — insert agent_research_runs row

**Files:**
- Edit: `app/agents/runtime/research_gate.py`
- Test: `tests/unit/agents/runtime/test_research_gate_open.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_research_gate_open.py
"""Verify open_gate inserts an agent_research_runs row and returns its UUID."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.agents.runtime import research_gate
from app.skills.registry import AgentID


@pytest.mark.asyncio
async def test_open_gate_inserts_row_and_returns_uuid(monkeypatch) -> None:
    contract_id = uuid4()
    fake_row = {"id": str(uuid4())}

    insert_mock = MagicMock()
    insert_mock.execute = AsyncMock(return_value=MagicMock(data=[fake_row]))
    table_mock = MagicMock()
    table_mock.insert = MagicMock(return_value=insert_mock)
    client = MagicMock()
    client.table = MagicMock(return_value=table_mock)

    monkeypatch.setattr(research_gate, "_get_supabase", lambda: client)

    run_id = await research_gate.open_gate(
        task_contract_id=contract_id,
        contract_source="initiative_step",
        agent_id=AgentID.FINANCIAL,
        initial_query="2026 Q3 forecast assumptions",
    )

    assert isinstance(run_id, UUID)
    client.table.assert_called_once_with("agent_research_runs")
    payload = table_mock.insert.call_args[0][0]
    assert payload["task_contract_id"] == str(contract_id)
    assert payload["task_contract_source"] == "initiative_step"
    assert payload["agent_id"] == AgentID.FINANCIAL.value
    assert payload["query"] == "2026 Q3 forecast assumptions"
    assert payload["status"] == "open"
    assert payload["iterations"] == 0


@pytest.mark.asyncio
async def test_open_gate_raises_if_insert_returns_no_row(monkeypatch) -> None:
    insert_mock = MagicMock()
    insert_mock.execute = AsyncMock(return_value=MagicMock(data=[]))
    table_mock = MagicMock(insert=MagicMock(return_value=insert_mock))
    client = MagicMock(table=MagicMock(return_value=table_mock))
    monkeypatch.setattr(research_gate, "_get_supabase", lambda: client)

    with pytest.raises(research_gate.ResearchGateError):
        await research_gate.open_gate(
            task_contract_id=uuid4(),
            contract_source="initiative_step",
            agent_id=AgentID.FINANCIAL,
            initial_query="anything",
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_research_gate_open.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.research_gate' has no attribute 'open_gate'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/research_gate.py (append)
import logging
from typing import Any
from uuid import UUID

from app.agents.runtime.types import ResearchGateError
from app.skills.registry import AgentID

logger = logging.getLogger(__name__)


def _get_supabase() -> Any:
    """Return the service-role Supabase client. Indirection so tests can patch."""
    from app.services.supabase_client import get_service_supabase

    return get_service_supabase()


async def open_gate(
    *,
    task_contract_id: UUID,
    contract_source: str,
    agent_id: AgentID,
    initial_query: str,
) -> UUID:
    """Insert an agent_research_runs row (status='open') and return run_id."""
    client = _get_supabase()
    payload = {
        "task_contract_id": str(task_contract_id),
        "task_contract_source": contract_source,
        "agent_id": agent_id.value,
        "query": initial_query,
        "status": "open",
        "iterations": 0,
    }
    response = await client.table("agent_research_runs").insert(payload).execute()
    rows = getattr(response, "data", None) or []
    if not rows:
        raise ResearchGateError(
            f"open_gate insert returned no row for contract {task_contract_id}"
        )
    run_id = UUID(rows[0]["id"])
    logger.info(
        "research_gate opened",
        extra={
            "run_id": str(run_id),
            "task_contract_id": str(task_contract_id),
            "agent_id": agent_id.value,
        },
    )
    return run_id
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_research_gate_open.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/research_gate.py tests/unit/agents/runtime/test_research_gate_open.py
git commit -m "feat(runtime): research_gate.open_gate inserts agent_research_runs row"
```

---

### Task 48: `is_open` — gate state check by (contract_id, agent_id)

**Files:**
- Edit: `app/agents/runtime/research_gate.py`
- Test: `tests/unit/agents/runtime/test_research_gate_is_open.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_research_gate_is_open.py
"""Verify is_open returns True only when an open/in_progress run exists."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import research_gate
from app.skills.registry import AgentID


def _build_query_chain(rows: list[dict]) -> MagicMock:
    chain = MagicMock()
    chain.execute = AsyncMock(return_value=MagicMock(data=rows))
    chain.eq = MagicMock(return_value=chain)
    chain.in_ = MagicMock(return_value=chain)
    chain.select = MagicMock(return_value=chain)
    chain.limit = MagicMock(return_value=chain)
    return chain


@pytest.mark.asyncio
async def test_is_open_true_when_row_present(monkeypatch) -> None:
    chain = _build_query_chain([{"id": str(uuid4()), "status": "open"}])
    client = MagicMock()
    client.table = MagicMock(return_value=chain)
    monkeypatch.setattr(research_gate, "_get_supabase", lambda: client)

    result = await research_gate.is_open(
        task_contract_id=uuid4(), agent_id=AgentID.FINANCIAL
    )
    assert result is True


@pytest.mark.asyncio
async def test_is_open_false_when_no_row(monkeypatch) -> None:
    chain = _build_query_chain([])
    client = MagicMock()
    client.table = MagicMock(return_value=chain)
    monkeypatch.setattr(research_gate, "_get_supabase", lambda: client)

    result = await research_gate.is_open(
        task_contract_id=uuid4(), agent_id=AgentID.FINANCIAL
    )
    assert result is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_research_gate_is_open.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.research_gate' has no attribute 'is_open'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/research_gate.py (append)
async def is_open(*, task_contract_id: UUID, agent_id: AgentID) -> bool:
    """Return True if an open/in_progress research run exists for this pair."""
    client = _get_supabase()
    response = (
        await client.table("agent_research_runs")
        .select("id, status")
        .eq("task_contract_id", str(task_contract_id))
        .eq("agent_id", agent_id.value)
        .in_("status", ["open", "in_progress"])
        .limit(1)
        .execute()
    )
    return bool(getattr(response, "data", None))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_research_gate_is_open.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/research_gate.py tests/unit/agents/runtime/test_research_gate_is_open.py
git commit -m "feat(runtime): research_gate.is_open checks (contract, agent) pair"
```

---

### Task 49: `record_tool_result` — accumulate raw results

**Files:**
- Edit: `app/agents/runtime/research_gate.py`
- Test: `tests/unit/agents/runtime/test_research_gate_record.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_research_gate_record.py
"""Verify record_tool_result appends to the run's result JSONB and bumps iterations."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import research_gate


@pytest.mark.asyncio
async def test_record_tool_result_only_accepts_research_tools(monkeypatch) -> None:
    with pytest.raises(research_gate.ResearchGateError):
        await research_gate.record_tool_result(
            run_id=uuid4(), tool_id="send_email", raw_result={"ok": True}
        )


@pytest.mark.asyncio
async def test_record_tool_result_appends_payload(monkeypatch) -> None:
    run_id = uuid4()
    existing = {"raw_results": [{"tool_id": "tavily_search", "data": {"q": 1}}]}

    select_chain = MagicMock()
    select_chain.execute = AsyncMock(
        return_value=MagicMock(data=[{"result": existing, "iterations": 1}])
    )
    select_chain.eq = MagicMock(return_value=select_chain)
    select_chain.select = MagicMock(return_value=select_chain)
    select_chain.single = MagicMock(return_value=select_chain)

    update_chain = MagicMock()
    update_chain.execute = AsyncMock(return_value=MagicMock(data=[{"id": str(run_id)}]))
    update_chain.eq = MagicMock(return_value=update_chain)
    update_chain.update = MagicMock(return_value=update_chain)

    table_mock = MagicMock()
    table_mock.select = MagicMock(return_value=select_chain)
    table_mock.update = MagicMock(return_value=update_chain)
    client = MagicMock(table=MagicMock(return_value=table_mock))
    monkeypatch.setattr(research_gate, "_get_supabase", lambda: client)

    await research_gate.record_tool_result(
        run_id=run_id, tool_id="deep_research", raw_result={"sources": []}
    )

    update_payload = table_mock.update.call_args[0][0]
    assert update_payload["iterations"] == 2
    assert update_payload["status"] == "in_progress"
    assert len(update_payload["result"]["raw_results"]) == 2
    assert update_payload["result"]["raw_results"][-1]["tool_id"] == "deep_research"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_research_gate_record.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.research_gate' has no attribute 'record_tool_result'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/research_gate.py (append)
async def record_tool_result(
    *,
    run_id: UUID,
    tool_id: str,
    raw_result: dict,
) -> None:
    """Append a research tool's raw result to the run's result JSONB."""
    if tool_id not in RESEARCH_TOOL_IDS:
        raise ResearchGateError(
            f"record_tool_result called with non-research tool_id={tool_id!r}"
        )
    client = _get_supabase()
    row_resp = (
        await client.table("agent_research_runs")
        .select("result, iterations")
        .eq("id", str(run_id))
        .single()
        .execute()
    )
    rows = getattr(row_resp, "data", None)
    if not rows:
        raise ResearchGateError(f"run_id {run_id} not found")
    row = rows[0] if isinstance(rows, list) else rows
    existing = row.get("result") or {}
    raw_results = list(existing.get("raw_results") or [])
    raw_results.append({"tool_id": tool_id, "data": raw_result})
    merged = {**existing, "raw_results": raw_results}
    new_iter = int(row.get("iterations") or 0) + 1
    await (
        client.table("agent_research_runs")
        .update({"result": merged, "iterations": new_iter, "status": "in_progress"})
        .eq("id", str(run_id))
        .execute()
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_research_gate_record.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/research_gate.py tests/unit/agents/runtime/test_research_gate_record.py
git commit -m "feat(runtime): research_gate.record_tool_result accumulates raw results"
```

---

### Task 50: LLM coverage prompt + JSON parser helper

**Files:**
- Edit: `app/agents/runtime/research_gate.py`
- Test: `tests/unit/agents/runtime/test_research_gate_coverage_parser.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_research_gate_coverage_parser.py
"""Verify _parse_coverage_json strips fences and validates ResearchResult shape."""
from __future__ import annotations

import pytest

from app.agents.runtime import research_gate


def test_parse_strips_code_fence() -> None:
    text = '```json\n{"summary": "x", "sources": [], "contradictions": [], "coverage_assessment": "complete", "missing_information": []}\n```'
    result = research_gate._parse_coverage_json(text)
    assert result is not None
    assert result.coverage_assessment == "complete"


def test_parse_returns_none_on_bad_json() -> None:
    assert research_gate._parse_coverage_json("not json at all") is None


def test_parse_returns_none_when_missing_required_field() -> None:
    text = '{"summary": "x", "coverage_assessment": "complete"}'
    assert research_gate._parse_coverage_json(text) is None


def test_parse_accepts_partial_assessment() -> None:
    text = (
        '{"summary": "y", "sources": [], "contradictions": [], '
        '"coverage_assessment": "partial", "missing_information": ["x"]}'
    )
    result = research_gate._parse_coverage_json(text)
    assert result is not None
    assert result.coverage_assessment == "partial"
    assert result.missing_information == ["x"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_research_gate_coverage_parser.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.research_gate' has no attribute '_parse_coverage_json'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/research_gate.py (append)
import json
import re

from app.agents.runtime.types import ResearchResult


def _strip_code_fence(text: str) -> str:
    """Strip ```json ... ``` or ``` ... ``` fences."""
    stripped = text.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    return match.group(1).strip() if match else stripped


def _parse_coverage_json(text: str) -> ResearchResult | None:
    """Parse a JSON coverage response into a ResearchResult, or None on failure."""
    try:
        parsed = json.loads(_strip_code_fence(text))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    try:
        return ResearchResult.model_validate(parsed)
    except Exception:  # noqa: BLE001 — validation can throw many things
        logger.warning("research coverage JSON failed ResearchResult validation")
        return None


def _build_coverage_prompt(
    success_criteria: list[str], raw_results: list[dict]
) -> str:
    """Compose the coverage-check prompt for Gemini Flash."""
    criteria_block = "\n".join(f"- {c}" for c in success_criteria) or "- (none)"
    raw_blob = json.dumps(raw_results, ensure_ascii=False)[:8000]
    return (
        "You are auditing whether research findings cover a set of success criteria.\n\n"
        "SUCCESS CRITERIA:\n"
        f"{criteria_block}\n\n"
        "RAW RESEARCH RESULTS (tool outputs):\n"
        f"{raw_blob}\n\n"
        "Produce a JSON object with these keys exactly:\n"
        '  "summary" (200-400 word synthesis of what is known)\n'
        '  "sources": list of {"url","title","key_claim","retrieved_at"}\n'
        '  "contradictions": list of strings\n'
        '  "coverage_assessment": "complete" or "partial"\n'
        '  "missing_information": list of unanswered criteria\n\n'
        "Return ONLY the JSON object. Coverage is 'complete' only when every success "
        "criterion is directly addressed by at least one source."
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_research_gate_coverage_parser.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/research_gate.py tests/unit/agents/runtime/test_research_gate_coverage_parser.py
git commit -m "feat(runtime): research_gate coverage prompt + JSON parser"
```

---

### Task 51: `check_coverage` — complete path returns ResearchResult

**Files:**
- Edit: `app/agents/runtime/research_gate.py`
- Test: `tests/unit/agents/runtime/test_research_gate_check_complete.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_research_gate_check_complete.py
"""Verify check_coverage returns a ResearchResult when LLM says 'complete'."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import research_gate
from app.agents.runtime.types import ResearchResult


@pytest.mark.asyncio
async def test_check_coverage_returns_result_when_complete(monkeypatch) -> None:
    run_id = uuid4()
    row = {
        "id": str(run_id),
        "result": {"raw_results": [{"tool_id": "tavily_search", "data": {"q": 1}}]},
        "iterations": 1,
    }
    select_chain = MagicMock()
    select_chain.execute = AsyncMock(return_value=MagicMock(data=[row]))
    select_chain.eq = MagicMock(return_value=select_chain)
    select_chain.select = MagicMock(return_value=select_chain)
    select_chain.single = MagicMock(return_value=select_chain)
    client = MagicMock(table=MagicMock(return_value=MagicMock(select=MagicMock(return_value=select_chain))))
    monkeypatch.setattr(research_gate, "_get_supabase", lambda: client)

    fake_llm = AsyncMock(return_value=(
        '{"summary": "ok", "sources": [], "contradictions": [], '
        '"coverage_assessment": "complete", "missing_information": []}'
    ))
    monkeypatch.setattr(research_gate, "_call_coverage_llm", fake_llm)

    result = await research_gate.check_coverage(
        run_id=run_id,
        success_criteria=["criterion A"],
        max_iterations=3,
    )

    assert isinstance(result, ResearchResult)
    assert result.coverage_assessment == "complete"
    fake_llm.assert_awaited_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_research_gate_check_complete.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.research_gate' has no attribute 'check_coverage'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/research_gate.py (append)
import asyncio
import os

COVERAGE_LLM_MODEL = os.getenv("RESEARCH_COVERAGE_LLM_MODEL", "gemini-2.5-flash")
COVERAGE_LLM_TIMEOUT_S = float(os.getenv("RESEARCH_COVERAGE_LLM_TIMEOUT_S", "20.0"))


async def _call_coverage_llm(prompt: str) -> str | None:
    """Low-temperature Gemini Flash call. Returns text or None on failure."""
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        logger.warning("google.genai not available; research coverage LLM skipped")
        return None
    try:
        client = genai.Client()
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=COVERAGE_LLM_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.1, max_output_tokens=2048
                ),
            ),
            timeout=COVERAGE_LLM_TIMEOUT_S,
        )
        return (getattr(response, "text", None) or "").strip() or None
    except (asyncio.TimeoutError, Exception) as exc:  # noqa: BLE001
        logger.warning("research coverage LLM call failed: %s", exc)
        return None


async def _load_run(run_id: UUID) -> dict:
    client = _get_supabase()
    resp = (
        await client.table("agent_research_runs")
        .select("id, result, iterations")
        .eq("id", str(run_id))
        .single()
        .execute()
    )
    data = getattr(resp, "data", None)
    if not data:
        raise ResearchGateError(f"run_id {run_id} not found")
    return data[0] if isinstance(data, list) else data


async def check_coverage(
    *,
    run_id: UUID,
    success_criteria: list[str],
    max_iterations: int,
) -> ResearchResult | None:
    """Run an LLM coverage check. Return ResearchResult if complete, None if partial.

    Raises ResearchGateError if max_iterations would be exceeded with no completion.
    """
    row = await _load_run(run_id)
    raw_results = list((row.get("result") or {}).get("raw_results") or [])
    iterations = int(row.get("iterations") or 0)

    prompt = _build_coverage_prompt(success_criteria, raw_results)
    text = await _call_coverage_llm(prompt)
    if not text:
        if iterations >= max_iterations:
            raise ResearchGateError(
                f"research run {run_id} exhausted {max_iterations} iterations "
                "with no successful coverage LLM call"
            )
        return None

    result = _parse_coverage_json(text)
    if result is None:
        if iterations >= max_iterations:
            raise ResearchGateError(
                f"research run {run_id} exhausted {max_iterations} iterations "
                "with unparseable coverage output"
            )
        return None

    if result.coverage_assessment == "complete":
        return result

    if iterations >= max_iterations:
        raise ResearchGateError(
            f"research run {run_id} exhausted {max_iterations} iterations; "
            f"missing: {result.missing_information}"
        )
    return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_research_gate_check_complete.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/research_gate.py tests/unit/agents/runtime/test_research_gate_check_complete.py
git commit -m "feat(runtime): research_gate.check_coverage completes when LLM says so"
```

---

### Task 52: `check_coverage` — partial path returns None; exhausted path raises

**Files:**
- Edit: `app/agents/runtime/research_gate.py` (no new code — exercises existing branches)
- Test: `tests/unit/agents/runtime/test_research_gate_check_partial.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_research_gate_check_partial.py
"""Verify check_coverage returns None on partial and raises when iterations exhausted."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import research_gate
from app.agents.runtime.types import ResearchGateError


def _row(run_id, iterations: int) -> dict:
    return {"id": str(run_id), "result": {"raw_results": []}, "iterations": iterations}


def _stub_loader(row: dict, monkeypatch) -> None:
    select_chain = MagicMock()
    select_chain.execute = AsyncMock(return_value=MagicMock(data=[row]))
    select_chain.eq = MagicMock(return_value=select_chain)
    select_chain.select = MagicMock(return_value=select_chain)
    select_chain.single = MagicMock(return_value=select_chain)
    client = MagicMock(
        table=MagicMock(return_value=MagicMock(select=MagicMock(return_value=select_chain)))
    )
    monkeypatch.setattr(research_gate, "_get_supabase", lambda: client)


@pytest.mark.asyncio
async def test_check_coverage_returns_none_when_partial(monkeypatch) -> None:
    run_id = uuid4()
    _stub_loader(_row(run_id, iterations=1), monkeypatch)
    monkeypatch.setattr(
        research_gate,
        "_call_coverage_llm",
        AsyncMock(return_value=(
            '{"summary": "x", "sources": [], "contradictions": [], '
            '"coverage_assessment": "partial", "missing_information": ["A"]}'
        )),
    )

    result = await research_gate.check_coverage(
        run_id=run_id, success_criteria=["A"], max_iterations=3
    )
    assert result is None


@pytest.mark.asyncio
async def test_check_coverage_raises_when_exhausted(monkeypatch) -> None:
    run_id = uuid4()
    _stub_loader(_row(run_id, iterations=3), monkeypatch)
    monkeypatch.setattr(
        research_gate,
        "_call_coverage_llm",
        AsyncMock(return_value=(
            '{"summary": "x", "sources": [], "contradictions": [], '
            '"coverage_assessment": "partial", "missing_information": ["A"]}'
        )),
    )

    with pytest.raises(ResearchGateError):
        await research_gate.check_coverage(
            run_id=run_id, success_criteria=["A"], max_iterations=3
        )


@pytest.mark.asyncio
async def test_check_coverage_raises_on_bad_llm_when_exhausted(monkeypatch) -> None:
    run_id = uuid4()
    _stub_loader(_row(run_id, iterations=3), monkeypatch)
    monkeypatch.setattr(research_gate, "_call_coverage_llm", AsyncMock(return_value=None))

    with pytest.raises(ResearchGateError):
        await research_gate.check_coverage(
            run_id=run_id, success_criteria=["A"], max_iterations=3
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_research_gate_check_partial.py -v
```

Expected: PASS already if Task 51 implementation is complete; if any branch was missed this will FAIL and force the fix.

- [ ] **Step 3: Write minimal implementation**

No code change needed — coverage of existing branches. If a test fails, fix the branch in `check_coverage` to match.

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_research_gate_check_partial.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/agents/runtime/test_research_gate_check_partial.py
git commit -m "test(runtime): research_gate.check_coverage partial + exhausted paths"
```

---

### Task 53: `close_gate` — persist complete result and timestamp

**Files:**
- Edit: `app/agents/runtime/research_gate.py`
- Test: `tests/unit/agents/runtime/test_research_gate_close.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_research_gate_close.py
"""Verify close_gate sets status='complete', writes result, and stamps completed_at."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import research_gate
from app.agents.runtime.types import ResearchResult


@pytest.mark.asyncio
async def test_close_gate_persists_result(monkeypatch) -> None:
    run_id = uuid4()
    update_chain = MagicMock()
    update_chain.execute = AsyncMock(return_value=MagicMock(data=[{"id": str(run_id)}]))
    update_chain.eq = MagicMock(return_value=update_chain)

    table_mock = MagicMock()
    table_mock.update = MagicMock(return_value=update_chain)
    client = MagicMock(table=MagicMock(return_value=table_mock))
    monkeypatch.setattr(research_gate, "_get_supabase", lambda: client)

    result = ResearchResult(
        summary="ok",
        sources=[],
        contradictions=[],
        coverage_assessment="complete",
        missing_information=[],
    )
    await research_gate.close_gate(run_id=run_id, result=result)

    payload = table_mock.update.call_args[0][0]
    assert payload["status"] == "complete"
    assert "completed_at" in payload
    assert payload["result"]["coverage_assessment"] == "complete"
    update_chain.eq.assert_called_with("id", str(run_id))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_research_gate_close.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.research_gate' has no attribute 'close_gate'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/research_gate.py (append)
from datetime import datetime, timezone


async def close_gate(*, run_id: UUID, result: ResearchResult) -> None:
    """Persist the validated ResearchResult and mark the run complete."""
    client = _get_supabase()
    payload = {
        "status": "complete",
        "result": result.model_dump(mode="json"),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    await (
        client.table("agent_research_runs")
        .update(payload)
        .eq("id", str(run_id))
        .execute()
    )
    logger.info("research_gate closed", extra={"run_id": str(run_id)})
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_research_gate_close.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/research_gate.py tests/unit/agents/runtime/test_research_gate_close.py
git commit -m "feat(runtime): research_gate.close_gate persists complete result"
```

---

### Task 54: Audit module skeleton + prompt builder

**Files:**
- Create: `app/agents/runtime/audit.py`
- Test: `tests/unit/agents/runtime/test_audit_prompt.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_audit_prompt.py
"""Verify _build_audit_prompt embeds every todo item and success criterion."""
from __future__ import annotations

from uuid import uuid4

from app.agents.runtime import audit
from app.agents.runtime.types import (
    Artifact,
    ResearchResult,
    TaskContract,
    TodoItem,
)


def _contract() -> TaskContract:
    return TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="Produce Q3 forecast",
        todo_items=[
            TodoItem(id="t1", title="Pull last 8 quarters", description=None),
            TodoItem(id="t2", title="Model 3 scenarios", description=None),
        ],
        success_criteria=["3 scenarios documented", "Variance < 10%"],
        owners=[],
        evidence_required=["draft_artifact"],
        initiative_id=None,
        initiative_phase=None,
        sibling_steps=[],
    )


def test_prompt_includes_every_todo_and_criterion() -> None:
    prompt = audit._build_audit_prompt(
        contract=_contract(),
        artifacts=[Artifact(kind="doc", ref="vault://x", summary="draft", payload={})],
        research=ResearchResult(
            summary="research ok",
            sources=[],
            contradictions=[],
            coverage_assessment="complete",
            missing_information=[],
        ),
    )
    assert "Pull last 8 quarters" in prompt
    assert "Model 3 scenarios" in prompt
    assert "3 scenarios documented" in prompt
    assert "Variance < 10%" in prompt
    assert "research ok" in prompt
    assert "vault://x" in prompt
    # Must demand strict JSON output.
    assert "ONLY" in prompt and "JSON" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_audit_prompt.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.agents.runtime.audit'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/audit.py
# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Self-audit primitives per spec § 8.

Deterministic Gemini Flash call (low temperature). Walks each todo_item and
each success_criterion against the produced artifacts. Persists to
agent_audit_reports and attaches a summary to the checklist item's evidence.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    ResearchResult,
    TaskContract,
)

logger = logging.getLogger(__name__)


def _build_audit_prompt(
    *,
    contract: TaskContract,
    artifacts: list[Artifact],
    research: ResearchResult,
) -> str:
    """Compose the audit prompt. Includes every todo and criterion verbatim."""
    todo_block = "\n".join(
        f"- id={item.id} :: {item.title}"
        + (f"\n  desc: {item.description}" if item.description else "")
        for item in contract.todo_items
    ) or "- (no todo items)"
    crit_block = "\n".join(f"- {c}" for c in contract.success_criteria) or "- (none)"
    artifacts_blob = json.dumps(
        [a.model_dump(mode="json") for a in artifacts], ensure_ascii=False
    )[:6000]
    research_blob = research.summary[:3000]
    return (
        "You are auditing whether produced artifacts satisfy a task contract.\n\n"
        f"GOAL: {contract.goal}\n\n"
        "TODO ITEMS:\n"
        f"{todo_block}\n\n"
        "SUCCESS CRITERIA:\n"
        f"{crit_block}\n\n"
        "RESEARCH SUMMARY:\n"
        f"{research_blob}\n\n"
        f"ARTIFACTS:\n{artifacts_blob}\n\n"
        "Output a JSON object with these keys exactly:\n"
        '  "overall_status": "pass" | "fail" | "partial"\n'
        '  "per_item": [{"item_id","status","evidence_pointers","gaps"}]\n'
        '  "per_criterion": [{"criterion","met","justification"}]\n'
        '  "gaps": list of strings\n'
        '  "recoverable": boolean\n'
        '  "next_action": "submit" | "retry" | "escalate"\n\n'
        "Pass ONLY if every criterion is met and every todo has evidence. "
        "Return ONLY the JSON object."
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_audit_prompt.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/audit.py tests/unit/agents/runtime/test_audit_prompt.py
git commit -m "feat(runtime): audit prompt builder embeds contract verbatim"
```

---

### Task 55: Audit JSON parser → AuditReport

**Files:**
- Edit: `app/agents/runtime/audit.py`
- Test: `tests/unit/agents/runtime/test_audit_parser.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_audit_parser.py
"""Verify _parse_audit_json fence-strips and validates the AuditReport shape."""
from __future__ import annotations

from app.agents.runtime import audit


def test_parse_audit_pass() -> None:
    text = (
        '```json\n{"overall_status":"pass","per_item":[{"item_id":"t1","status":"pass","evidence_pointers":["v1"],"gaps":[]}],'
        '"per_criterion":[{"criterion":"c1","met":true,"justification":"ok"}],"gaps":[],"recoverable":true,"next_action":"submit"}\n```'
    )
    report = audit._parse_audit_json(text)
    assert report is not None
    assert report.overall_status == "pass"
    assert report.next_action == "submit"


def test_parse_audit_returns_none_on_bad_json() -> None:
    assert audit._parse_audit_json("nope") is None


def test_parse_audit_returns_none_on_invalid_status() -> None:
    text = '{"overall_status":"bogus","per_item":[],"per_criterion":[],"gaps":[],"recoverable":false,"next_action":"submit"}'
    assert audit._parse_audit_json(text) is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_audit_parser.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.audit' has no attribute '_parse_audit_json'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/audit.py (append)
import re


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    return match.group(1).strip() if match else stripped


def _parse_audit_json(text: str) -> AuditReport | None:
    try:
        parsed = json.loads(_strip_code_fence(text))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    # Carry over policy_violations as empty (populated by persona gate later).
    parsed.setdefault("policy_violations", [])
    try:
        return AuditReport.model_validate(parsed)
    except Exception:  # noqa: BLE001
        logger.warning("audit JSON failed AuditReport validation")
        return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_audit_parser.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/audit.py tests/unit/agents/runtime/test_audit_parser.py
git commit -m "feat(runtime): audit JSON parser with AuditReport validation"
```

---

### Task 56: `_call_audit_llm` — Gemini Flash, low temperature

**Files:**
- Edit: `app/agents/runtime/audit.py`
- Test: `tests/unit/agents/runtime/test_audit_call_llm.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_audit_call_llm.py
"""Verify _call_audit_llm uses Flash at low temperature and tolerates failures."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.runtime import audit


@pytest.mark.asyncio
async def test_call_audit_llm_returns_text(monkeypatch) -> None:
    captured: dict = {}

    async def fake_gen(model, contents, config):
        captured["model"] = model
        captured["temperature"] = config.temperature
        return MagicMock(text='{"ok": true}')

    fake_client = MagicMock()
    fake_client.aio.models.generate_content = AsyncMock(side_effect=fake_gen)

    class FakeTypes:
        @staticmethod
        def GenerateContentConfig(**kw):  # noqa: N802 — match SDK
            cfg = MagicMock()
            cfg.temperature = kw.get("temperature")
            return cfg

    monkeypatch.setattr(audit, "_load_genai", lambda: (MagicMock(Client=lambda: fake_client), FakeTypes))

    text = await audit._call_audit_llm("prompt")
    assert text == '{"ok": true}'
    assert captured["temperature"] <= 0.2
    assert "flash" in captured["model"].lower()


@pytest.mark.asyncio
async def test_call_audit_llm_returns_none_on_import_error(monkeypatch) -> None:
    monkeypatch.setattr(audit, "_load_genai", lambda: None)
    assert await audit._call_audit_llm("prompt") is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_audit_call_llm.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.audit' has no attribute '_call_audit_llm'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/audit.py (append)
import asyncio
import os

AUDIT_LLM_MODEL = os.getenv("AUDIT_LLM_MODEL", "gemini-2.5-flash")
AUDIT_LLM_TIMEOUT_S = float(os.getenv("AUDIT_LLM_TIMEOUT_S", "25.0"))


def _load_genai():
    try:
        from google import genai
        from google.genai import types as genai_types

        return genai, genai_types
    except ImportError:
        return None


async def _call_audit_llm(prompt: str) -> str | None:
    loaded = _load_genai()
    if loaded is None:
        logger.warning("google.genai not available; audit LLM skipped")
        return None
    genai, genai_types = loaded
    try:
        client = genai.Client()
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=AUDIT_LLM_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.1, max_output_tokens=2048
                ),
            ),
            timeout=AUDIT_LLM_TIMEOUT_S,
        )
        return (getattr(response, "text", None) or "").strip() or None
    except (asyncio.TimeoutError, Exception) as exc:  # noqa: BLE001
        logger.warning("audit LLM call failed: %s", exc)
        return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_audit_call_llm.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/audit.py tests/unit/agents/runtime/test_audit_call_llm.py
git commit -m "feat(runtime): audit Gemini Flash client with low-temp config"
```

---

### Task 57: `audit_against_contract` — happy path

**Files:**
- Edit: `app/agents/runtime/audit.py`
- Test: `tests/unit/agents/runtime/test_audit_against_contract.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_audit_against_contract.py
"""Verify audit_against_contract returns a parsed AuditReport for a happy path."""
from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.agents.runtime import audit
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.types import (
    Artifact,
    ResearchResult,
    TaskContract,
    TodoItem,
)


def _contract() -> TaskContract:
    return TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="g",
        todo_items=[TodoItem(id="t1", title="do a thing", description=None)],
        success_criteria=["c1"],
        owners=[],
        evidence_required=["draft_artifact"],
        initiative_id=None,
        initiative_phase=None,
        sibling_steps=[],
    )


@pytest.mark.asyncio
async def test_audit_returns_parsed_report(monkeypatch) -> None:
    monkeypatch.setattr(
        audit,
        "_call_audit_llm",
        AsyncMock(return_value=(
            '{"overall_status":"pass","per_item":[{"item_id":"t1","status":"pass","evidence_pointers":["v"],"gaps":[]}],'
            '"per_criterion":[{"criterion":"c1","met":true,"justification":"ok"}],"gaps":[],"recoverable":true,"next_action":"submit"}'
        )),
    )

    report = await audit.audit_against_contract(
        _contract(),
        [Artifact(kind="doc", ref="v://x", summary="s", payload={})],
        ResearchResult(
            summary="s",
            sources=[],
            contradictions=[],
            coverage_assessment="complete",
            missing_information=[],
        ),
        ops=OperationsConfig.defaults(agent_id="financial"),
    )
    assert report.overall_status == "pass"
    assert report.next_action == "submit"


@pytest.mark.asyncio
async def test_audit_falls_back_to_fail_when_llm_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(audit, "_call_audit_llm", AsyncMock(return_value=None))

    report = await audit.audit_against_contract(
        _contract(),
        [],
        ResearchResult(
            summary="s",
            sources=[],
            contradictions=[],
            coverage_assessment="complete",
            missing_information=[],
        ),
        ops=OperationsConfig.defaults(agent_id="financial"),
    )
    assert report.overall_status == "fail"
    assert report.next_action == "escalate"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_audit_against_contract.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.audit' has no attribute 'audit_against_contract'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/audit.py (append)
from app.agents.runtime.operations_config import OperationsConfig


def _fallback_fail_report(reason: str, contract: TaskContract) -> AuditReport:
    return AuditReport(
        overall_status="fail",
        per_item=[],
        per_criterion=[],
        gaps=[reason],
        policy_violations=[],
        recoverable=False,
        next_action="escalate",
    )


async def audit_against_contract(
    contract: TaskContract,
    artifacts: list[Artifact],
    research: ResearchResult,
    *,
    ops: OperationsConfig,
) -> AuditReport:
    """Deterministic LLM audit of artifacts against the contract's todo + criteria."""
    prompt = _build_audit_prompt(
        contract=contract, artifacts=artifacts, research=research
    )
    text = await _call_audit_llm(prompt)
    if not text:
        return _fallback_fail_report("audit LLM unavailable", contract)
    report = _parse_audit_json(text)
    if report is None:
        return _fallback_fail_report("audit LLM output unparseable", contract)
    # Honor ops.audit.fail_on_any_unmet_criterion as belt-and-braces.
    if getattr(ops.audit, "fail_on_any_unmet_criterion", True) and any(
        not c.met for c in report.per_criterion
    ):
        if report.overall_status == "pass":
            report = report.model_copy(update={"overall_status": "fail", "next_action": "retry"})
    return report
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_audit_against_contract.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/audit.py tests/unit/agents/runtime/test_audit_against_contract.py
git commit -m "feat(runtime): audit_against_contract LLM pipeline with safe fallback"
```

---

### Task 58: `persist_audit_report` — write to agent_audit_reports

**Files:**
- Edit: `app/agents/runtime/audit.py`
- Test: `tests/unit/agents/runtime/test_audit_persist.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_audit_persist.py
"""Verify persist_audit_report inserts a row and returns its UUID."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.agents.runtime import audit
from app.agents.runtime.types import AuditReport
from app.skills.registry import AgentID


@pytest.mark.asyncio
async def test_persist_audit_report_inserts_row(monkeypatch) -> None:
    contract_id = uuid4()
    row_id = uuid4()

    insert_mock = MagicMock()
    insert_mock.execute = AsyncMock(return_value=MagicMock(data=[{"id": str(row_id)}]))
    table_mock = MagicMock(insert=MagicMock(return_value=insert_mock))
    client = MagicMock(table=MagicMock(return_value=table_mock))
    monkeypatch.setattr(audit, "_get_supabase", lambda: client)

    report = AuditReport(
        overall_status="pass",
        per_item=[],
        per_criterion=[],
        gaps=[],
        policy_violations=[],
        recoverable=True,
        next_action="submit",
    )
    returned = await audit.persist_audit_report(
        report, agent_id=AgentID.FINANCIAL, task_contract_id=contract_id
    )
    assert isinstance(returned, UUID)
    assert returned == row_id

    payload = table_mock.insert.call_args[0][0]
    assert payload["agent_id"] == AgentID.FINANCIAL.value
    assert payload["task_contract_id"] == str(contract_id)
    assert payload["overall_status"] == "pass"
    assert payload["recoverable"] is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_audit_persist.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.audit' has no attribute 'persist_audit_report'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/audit.py (append)
from uuid import UUID

from app.skills.registry import AgentID


def _get_supabase() -> Any:
    from app.services.supabase_client import get_service_supabase

    return get_service_supabase()


async def persist_audit_report(
    report: AuditReport,
    *,
    agent_id: AgentID,
    task_contract_id: UUID,
) -> UUID:
    """Insert into agent_audit_reports. Returns the new row id."""
    client = _get_supabase()
    payload = {
        "agent_id": agent_id.value,
        "task_contract_id": str(task_contract_id),
        "overall_status": report.overall_status,
        "per_item": [i.model_dump(mode="json") for i in report.per_item],
        "per_criterion": [c.model_dump(mode="json") for c in report.per_criterion],
        "gaps": report.gaps,
        "policy_violations": [v.model_dump(mode="json") for v in report.policy_violations],
        "recoverable": report.recoverable,
        "next_action": report.next_action,
    }
    response = await client.table("agent_audit_reports").insert(payload).execute()
    rows = getattr(response, "data", None) or []
    if not rows:
        raise RuntimeError("persist_audit_report insert returned no row")
    return UUID(rows[0]["id"])
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_audit_persist.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/audit.py tests/unit/agents/runtime/test_audit_persist.py
git commit -m "feat(runtime): persist_audit_report writes to agent_audit_reports"
```

---

### Task 59: `attach_audit_summary_to_evidence` — update checklist evidence JSONB

**Files:**
- Edit: `app/agents/runtime/audit.py`
- Test: `tests/unit/agents/runtime/test_audit_attach.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_audit_attach.py
"""Verify attach_audit_summary_to_evidence updates initiative_checklist_items.evidence."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import audit
from app.agents.runtime.types import AuditReport, TaskContract, TodoItem


def _contract(checklist_id) -> TaskContract:
    return TaskContract(
        id=checklist_id,
        source="initiative_step",
        goal="g",
        todo_items=[TodoItem(id="t1", title="x", description=None)],
        success_criteria=["c1"],
        owners=[],
        evidence_required=[],
        initiative_id=uuid4(),
        initiative_phase="build",
        sibling_steps=[],
    )


@pytest.mark.asyncio
async def test_attach_skips_when_source_not_initiative_step(monkeypatch) -> None:
    contract = TaskContract(
        id=uuid4(),
        source="department_task",
        goal="g",
        todo_items=[],
        success_criteria=[],
        owners=[],
        evidence_required=[],
        initiative_id=None,
        initiative_phase=None,
        sibling_steps=[],
    )
    update_mock = MagicMock()
    client = MagicMock(table=MagicMock(return_value=update_mock))
    monkeypatch.setattr(audit, "_get_supabase", lambda: client)
    report = AuditReport(
        overall_status="pass", per_item=[], per_criterion=[], gaps=[],
        policy_violations=[], recoverable=True, next_action="submit",
    )
    await audit.attach_audit_summary_to_evidence(contract=contract, report=report)
    update_mock.update.assert_not_called()


@pytest.mark.asyncio
async def test_attach_appends_audit_summary(monkeypatch) -> None:
    checklist_id = uuid4()
    contract = _contract(checklist_id)
    existing_evidence = [{"kind": "draft", "ref": "x"}]

    select_chain = MagicMock()
    select_chain.execute = AsyncMock(
        return_value=MagicMock(data=[{"evidence": existing_evidence}])
    )
    select_chain.eq = MagicMock(return_value=select_chain)
    select_chain.select = MagicMock(return_value=select_chain)
    select_chain.single = MagicMock(return_value=select_chain)

    update_chain = MagicMock()
    update_chain.execute = AsyncMock(return_value=MagicMock(data=[{"id": str(checklist_id)}]))
    update_chain.eq = MagicMock(return_value=update_chain)

    table_mock = MagicMock(
        select=MagicMock(return_value=select_chain),
        update=MagicMock(return_value=update_chain),
    )
    client = MagicMock(table=MagicMock(return_value=table_mock))
    monkeypatch.setattr(audit, "_get_supabase", lambda: client)

    report = AuditReport(
        overall_status="pass",
        per_item=[],
        per_criterion=[],
        gaps=[],
        policy_violations=[],
        recoverable=True,
        next_action="submit",
    )
    await audit.attach_audit_summary_to_evidence(contract=contract, report=report)

    payload = table_mock.update.call_args[0][0]
    new_evidence = payload["evidence"]
    assert any(e.get("kind") == "audit_summary" for e in new_evidence)
    assert any(e.get("kind") == "draft" for e in new_evidence)  # existing preserved
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_audit_attach.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.audit' has no attribute 'attach_audit_summary_to_evidence'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/audit.py (append)
async def attach_audit_summary_to_evidence(
    *,
    contract: TaskContract,
    report: AuditReport,
) -> None:
    """Append an audit_summary record to initiative_checklist_items.evidence JSONB."""
    if contract.source != "initiative_step":
        return
    client = _get_supabase()
    row_resp = (
        await client.table("initiative_checklist_items")
        .select("evidence")
        .eq("id", str(contract.id))
        .single()
        .execute()
    )
    data = getattr(row_resp, "data", None) or {}
    row = data[0] if isinstance(data, list) else data
    existing = list(row.get("evidence") or [])
    existing.append(
        {
            "kind": "audit_summary",
            "overall_status": report.overall_status,
            "gaps": report.gaps,
            "next_action": report.next_action,
        }
    )
    await (
        client.table("initiative_checklist_items")
        .update({"evidence": existing})
        .eq("id", str(contract.id))
        .execute()
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_audit_attach.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/audit.py tests/unit/agents/runtime/test_audit_attach.py
git commit -m "feat(runtime): attach_audit_summary_to_evidence updates checklist JSONB"
```

---

### Task 60: Persona gate module skeleton + defaults loader

**Files:**
- Create: `app/agents/runtime/persona_gate.py`
- Test: `tests/unit/agents/runtime/test_persona_gate_defaults.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_persona_gate_defaults.py
"""Verify _defaults_from_registry derives a PersonaPolicy from policy_registry."""
from __future__ import annotations

from app.agents.runtime import persona_gate
from app.agents.runtime.types import PersonaPolicy


def test_defaults_for_solopreneur_returns_policy() -> None:
    policy = persona_gate._defaults_from_registry("solopreneur")
    assert isinstance(policy, PersonaPolicy)
    assert policy.persona_id == "solopreneur"
    assert policy.allowed_tool_ids == "*"
    assert policy.denied_tool_ids == []


def test_defaults_unknown_persona_returns_baseline() -> None:
    policy = persona_gate._defaults_from_registry("unknown")
    assert isinstance(policy, PersonaPolicy)
    assert policy.persona_id == "unknown"
    assert policy.allowed_tool_ids == "*"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_persona_gate_defaults.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.agents.runtime.persona_gate'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/persona_gate.py
# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Persona policy enforcement per spec § 13.

Loads from the new persona_policies table and falls back to the existing
app.personas.policy_registry. Three public functions enforce tool allow/deny,
action thresholds, and prompt-fragment injection. Violations are routed to
the in-progress audit report via record_violation.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.agents.runtime.types import (
    ActionThresholds,
    PersonaPolicy,
    PersonaPolicyError,
    PolicyViolation,
    RateLimits,
)
from app.personas.policy_registry import get_persona_policy

logger = logging.getLogger(__name__)


def _defaults_from_registry(persona_id: str) -> PersonaPolicy:
    """Build a PersonaPolicy from policy_registry (or baseline if unknown)."""
    registry_policy = get_persona_policy(persona_id)
    fragments: list[str] = []
    if registry_policy is not None:
        # Surface the legacy fragment under "prompt_fragments" so the existing
        # build_persona_policy_block content still flows in.
        fragments = [
            f"Persona summary: {registry_policy.summary}",
            f"Approval posture: {registry_policy.approval_posture}",
            f"Output contract: {registry_policy.output_contract}",
        ]
    return PersonaPolicy(
        persona_id=persona_id,
        allowed_tool_ids="*",
        denied_tool_ids=[],
        action_thresholds=ActionThresholds(),
        rate_limits=RateLimits(),
        prompt_fragments=fragments,
        classifier_default_mode=None,
        initiative_phases_blocked=[],
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_persona_gate_defaults.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/persona_gate.py tests/unit/agents/runtime/test_persona_gate_defaults.py
git commit -m "feat(runtime): persona_gate defaults derived from policy_registry"
```

---

### Task 61: `load_persona_policy` — DB-first with registry fallback

**Files:**
- Edit: `app/agents/runtime/persona_gate.py`
- Test: `tests/unit/agents/runtime/test_persona_gate_load.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_persona_gate_load.py
"""Verify load_persona_policy uses persona_policies row and falls back to defaults."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import persona_gate


def _stub_supabase(rows: list[dict], monkeypatch) -> None:
    chain = MagicMock()
    chain.execute = AsyncMock(return_value=MagicMock(data=rows))
    chain.eq = MagicMock(return_value=chain)
    chain.select = MagicMock(return_value=chain)
    chain.limit = MagicMock(return_value=chain)
    client = MagicMock(table=MagicMock(return_value=chain))
    monkeypatch.setattr(persona_gate, "_get_supabase", lambda: client)


@pytest.mark.asyncio
async def test_load_persona_policy_uses_db_row(monkeypatch) -> None:
    _stub_supabase(
        [
            {
                "persona_id": "startup",
                "allowed_tool_ids": ["tool_a", "tool_b"],
                "denied_tool_ids": ["dangerous_tool"],
                "action_thresholds": {"financial_action_usd": 500},
                "rate_limits": {},
                "prompt_fragments": ["Be scrappy"],
                "classifier_default_mode": "direct",
                "initiative_phases_blocked": ["scale"],
            }
        ],
        monkeypatch,
    )
    policy = await persona_gate.load_persona_policy(uuid4(), "startup")
    assert policy.allowed_tool_ids == ["tool_a", "tool_b"]
    assert "dangerous_tool" in policy.denied_tool_ids
    assert policy.classifier_default_mode == "direct"


@pytest.mark.asyncio
async def test_load_persona_policy_falls_back_to_registry(monkeypatch) -> None:
    _stub_supabase([], monkeypatch)
    policy = await persona_gate.load_persona_policy(uuid4(), "solopreneur")
    assert policy.persona_id == "solopreneur"
    assert policy.allowed_tool_ids == "*"
    assert policy.prompt_fragments  # registry-derived fragments present
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_persona_gate_load.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.persona_gate' has no attribute 'load_persona_policy'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/persona_gate.py (append)
def _get_supabase() -> Any:
    from app.services.supabase_client import get_service_supabase

    return get_service_supabase()


async def load_persona_policy(user_id: UUID, persona_id: str) -> PersonaPolicy:
    """Load from persona_policies table; fall back to policy_registry defaults."""
    client = _get_supabase()
    try:
        response = (
            await client.table("persona_policies")
            .select(
                "persona_id, allowed_tool_ids, denied_tool_ids, action_thresholds, "
                "rate_limits, prompt_fragments, classifier_default_mode, "
                "initiative_phases_blocked"
            )
            .eq("persona_id", persona_id)
            .limit(1)
            .execute()
        )
        rows = getattr(response, "data", None) or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("persona_policies fetch failed for %s: %s", persona_id, exc)
        rows = []

    if not rows:
        return _defaults_from_registry(persona_id)

    raw = rows[0]
    try:
        return PersonaPolicy.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "persona_policies row for %s failed validation: %s — using registry defaults",
            persona_id, exc,
        )
        return _defaults_from_registry(persona_id)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_persona_gate_load.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/persona_gate.py tests/unit/agents/runtime/test_persona_gate_load.py
git commit -m "feat(runtime): persona_gate.load_persona_policy with registry fallback"
```

---

### Task 62: `check_tool_allowed` — allow-list precedence over deny-list

**Files:**
- Edit: `app/agents/runtime/persona_gate.py`
- Test: `tests/unit/agents/runtime/test_persona_gate_tool_allowed.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_persona_gate_tool_allowed.py
"""Verify check_tool_allowed: allow-list precedence, deny-list rejection."""
from __future__ import annotations

import pytest

from app.agents.runtime import persona_gate
from app.agents.runtime.types import (
    ActionThresholds, PersonaPolicy, PersonaPolicyError, RateLimits,
)


def _policy(allowed, denied) -> PersonaPolicy:
    return PersonaPolicy(
        persona_id="t",
        allowed_tool_ids=allowed,
        denied_tool_ids=denied,
        action_thresholds=ActionThresholds(),
        rate_limits=RateLimits(),
        prompt_fragments=[],
        classifier_default_mode=None,
        initiative_phases_blocked=[],
    )


@pytest.mark.asyncio
async def test_wildcard_allows_everything_not_denied() -> None:
    await persona_gate.check_tool_allowed("any_tool", _policy("*", []))


@pytest.mark.asyncio
async def test_wildcard_still_respects_deny() -> None:
    with pytest.raises(PersonaPolicyError):
        await persona_gate.check_tool_allowed("blocked_tool", _policy("*", ["blocked_tool"]))


@pytest.mark.asyncio
async def test_allow_list_precedence_over_deny() -> None:
    # spec § 13: "Allow-list takes precedence over deny-list"
    await persona_gate.check_tool_allowed("tool_a", _policy(["tool_a"], ["tool_a"]))


@pytest.mark.asyncio
async def test_not_in_allow_list_denied() -> None:
    with pytest.raises(PersonaPolicyError):
        await persona_gate.check_tool_allowed("tool_x", _policy(["tool_a"], []))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_persona_gate_tool_allowed.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.persona_gate' has no attribute 'check_tool_allowed'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/persona_gate.py (append)
async def check_tool_allowed(tool_id: str, policy: PersonaPolicy) -> None:
    """Raise PersonaPolicyError if tool is not allowed for this persona.

    Allow-list takes precedence over deny-list (spec § 13). When allow-list is
    "*" the deny-list still applies.
    """
    allowed = policy.allowed_tool_ids
    denied = set(policy.denied_tool_ids or [])

    if isinstance(allowed, list):
        if tool_id in allowed:
            return  # explicit allow wins
        raise PersonaPolicyError(
            f"tool '{tool_id}' not in persona allow-list for '{policy.persona_id}'"
        )

    # allowed == "*" — only deny-list can block.
    if tool_id in denied:
        raise PersonaPolicyError(
            f"tool '{tool_id}' is denied by persona '{policy.persona_id}'"
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_persona_gate_tool_allowed.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/persona_gate.py tests/unit/agents/runtime/test_persona_gate_tool_allowed.py
git commit -m "feat(runtime): persona_gate.check_tool_allowed with allow-list precedence"
```

---

### Task 63: `check_action_threshold` — financial + external_send approval

**Files:**
- Edit: `app/agents/runtime/persona_gate.py`
- Test: `tests/unit/agents/runtime/test_persona_gate_threshold.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_persona_gate_threshold.py
"""Verify check_action_threshold enforces financial and external_send caps."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.agents.runtime import persona_gate
from app.agents.runtime.types import (
    ActionThresholds, PersonaPolicy, PersonaPolicyError, RateLimits,
)


def _policy() -> PersonaPolicy:
    return PersonaPolicy(
        persona_id="solo",
        allowed_tool_ids="*",
        denied_tool_ids=[],
        action_thresholds=ActionThresholds(
            financial_action_usd=500,
            require_approval_for_external_send=True,
        ),
        rate_limits=RateLimits(),
        prompt_fragments=[],
        classifier_default_mode=None,
        initiative_phases_blocked=[],
    )


@pytest.mark.asyncio
async def test_financial_under_threshold_passes() -> None:
    await persona_gate.check_action_threshold(
        "stripe_charge", {"amount_usd": 100}, _policy()
    )


@pytest.mark.asyncio
async def test_financial_above_threshold_requires_approval(monkeypatch) -> None:
    monkeypatch.setattr(persona_gate, "_has_valid_approval_token", AsyncMock(return_value=False))
    with pytest.raises(PersonaPolicyError):
        await persona_gate.check_action_threshold(
            "stripe_charge", {"amount_usd": 750}, _policy()
        )


@pytest.mark.asyncio
async def test_financial_above_threshold_with_token_passes(monkeypatch) -> None:
    monkeypatch.setattr(persona_gate, "_has_valid_approval_token", AsyncMock(return_value=True))
    await persona_gate.check_action_threshold(
        "stripe_charge", {"amount_usd": 750, "approval_token": "abc"}, _policy()
    )


@pytest.mark.asyncio
async def test_external_send_requires_token(monkeypatch) -> None:
    monkeypatch.setattr(persona_gate, "_has_valid_approval_token", AsyncMock(return_value=False))
    with pytest.raises(PersonaPolicyError):
        await persona_gate.check_action_threshold(
            "gmail_send", {"to": "x@y.com"}, _policy()
        )


@pytest.mark.asyncio
async def test_non_threshold_tool_passes() -> None:
    await persona_gate.check_action_threshold(
        "list_calendar", {}, _policy()
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_persona_gate_threshold.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.persona_gate' has no attribute 'check_action_threshold'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/persona_gate.py (append)
# Tool-id substrings that classify into action kinds. Conservative —
# missing classifications fail open and rely on allow/deny lists.
_FINANCIAL_TOOL_KEYWORDS = ("stripe", "charge", "refund", "payout", "transfer", "spend")
_EXTERNAL_SEND_TOOL_KEYWORDS = ("gmail_send", "send_email", "slack_post", "sms_send", "outbound")


def _action_kind(tool_id: str) -> str | None:
    tid = tool_id.lower()
    if any(k in tid for k in _FINANCIAL_TOOL_KEYWORDS):
        return "financial_action"
    if any(k in tid for k in _EXTERNAL_SEND_TOOL_KEYWORDS):
        return "external_send"
    return None


async def _has_valid_approval_token(token: str | None) -> bool:
    if not token:
        return False
    try:
        from app.services.confirmation_tokens import consume_confirmation_token
    except ImportError:
        return False
    payload = await consume_confirmation_token(token)
    return payload is not None


async def check_action_threshold(
    tool_id: str,
    tool_args: dict,
    policy: PersonaPolicy,
) -> None:
    """Raise PersonaPolicyError if a financial/external action exceeds caps
    without a valid approval token.
    """
    kind = _action_kind(tool_id)
    if kind is None:
        return

    thresholds = policy.action_thresholds
    token = tool_args.get("approval_token") if isinstance(tool_args, dict) else None

    if kind == "financial_action":
        cap = thresholds.financial_action_usd
        amount = float(tool_args.get("amount_usd") or tool_args.get("amount") or 0)
        if cap is not None and amount > cap:
            if not await _has_valid_approval_token(token):
                raise PersonaPolicyError(
                    f"action '{tool_id}' (${amount}) exceeds cap ${cap} for "
                    f"persona '{policy.persona_id}' and no approval token present"
                )
    elif kind == "external_send":
        if thresholds.require_approval_for_external_send:
            if not await _has_valid_approval_token(token):
                raise PersonaPolicyError(
                    f"action '{tool_id}' requires approval for persona "
                    f"'{policy.persona_id}' (no approval token present)"
                )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_persona_gate_threshold.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/persona_gate.py tests/unit/agents/runtime/test_persona_gate_threshold.py
git commit -m "feat(runtime): persona_gate.check_action_threshold gates financial + external_send"
```

---

### Task 64: `apply_prompt_fragments` — render markdown block

**Files:**
- Edit: `app/agents/runtime/persona_gate.py`
- Test: `tests/unit/agents/runtime/test_persona_gate_fragments.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_persona_gate_fragments.py
"""Verify apply_prompt_fragments renders a deterministic markdown block."""
from __future__ import annotations

from app.agents.runtime import persona_gate
from app.agents.runtime.types import (
    ActionThresholds, PersonaPolicy, RateLimits,
)


def _policy(fragments) -> PersonaPolicy:
    return PersonaPolicy(
        persona_id="enterprise",
        allowed_tool_ids="*",
        denied_tool_ids=[],
        action_thresholds=ActionThresholds(),
        rate_limits=RateLimits(),
        prompt_fragments=fragments,
        classifier_default_mode=None,
        initiative_phases_blocked=[],
    )


def test_apply_renders_markdown_block_with_each_fragment() -> None:
    block = persona_gate.apply_prompt_fragments(
        _policy(["Be governance-aware", "Lead with stakeholder map"])
    )
    assert "## Persona Policy" in block
    assert "- Be governance-aware" in block
    assert "- Lead with stakeholder map" in block


def test_apply_returns_empty_string_when_no_fragments() -> None:
    assert persona_gate.apply_prompt_fragments(_policy([])) == ""


def test_apply_is_deterministic() -> None:
    p = _policy(["a", "b", "c"])
    assert persona_gate.apply_prompt_fragments(p) == persona_gate.apply_prompt_fragments(p)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_persona_gate_fragments.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.persona_gate' has no attribute 'apply_prompt_fragments'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/persona_gate.py (append)
def apply_prompt_fragments(policy: PersonaPolicy) -> str:
    """Render the persona's prompt fragments as a markdown block.

    Returns the empty string if no fragments are configured so callers can
    safely concatenate without conditional checks.
    """
    fragments = [f for f in (policy.prompt_fragments or []) if f]
    if not fragments:
        return ""
    lines = [f"## Persona Policy ({policy.persona_id})"]
    lines.extend(f"- {f}" for f in fragments)
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_persona_gate_fragments.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/persona_gate.py tests/unit/agents/runtime/test_persona_gate_fragments.py
git commit -m "feat(runtime): persona_gate.apply_prompt_fragments markdown rendering"
```

---

### Task 65: `record_violation` — append to audit policy_violations

**Files:**
- Edit: `app/agents/runtime/persona_gate.py`
- Test: `tests/unit/agents/runtime/test_persona_gate_record_violation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_persona_gate_record_violation.py
"""Verify record_violation appends a PolicyViolation to the audit list."""
from __future__ import annotations

from app.agents.runtime import persona_gate
from app.agents.runtime.types import PolicyViolation


def test_record_violation_appends_to_list() -> None:
    violations: list[PolicyViolation] = []
    persona_gate.record_violation(
        violations, kind="tool_denied", detail="tool X is denied", tool_id="X"
    )
    assert len(violations) == 1
    assert violations[0].kind == "tool_denied"
    assert violations[0].tool_id == "X"
    assert violations[0].detail == "tool X is denied"


def test_record_violation_supports_no_tool_id() -> None:
    violations: list[PolicyViolation] = []
    persona_gate.record_violation(violations, kind="threshold", detail="too much")
    assert violations[0].tool_id is None
    assert violations[0].kind == "threshold"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_persona_gate_record_violation.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.persona_gate' has no attribute 'record_violation'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/persona_gate.py (append)
def record_violation(
    audit_violations: list[PolicyViolation],
    kind: str,
    detail: str,
    tool_id: str | None = None,
) -> None:
    """Append a PolicyViolation to the audit report's policy_violations list."""
    audit_violations.append(
        PolicyViolation(kind=kind, detail=detail, tool_id=tool_id)
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_persona_gate_record_violation.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/persona_gate.py tests/unit/agents/runtime/test_persona_gate_record_violation.py
git commit -m "feat(runtime): persona_gate.record_violation appends PolicyViolation"
```

---

### Task 66: Task router skeleton + DIRECT/INITIATIVE verb constants

**Files:**
- Create: `app/agents/runtime/task_router.py`
- Test: `tests/unit/agents/runtime/test_task_router_constants.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_task_router_constants.py
"""Verify the verb constants match spec § 9 exactly."""
from __future__ import annotations

from app.agents.runtime import task_router


def test_direct_verbs_includes_factual_signals() -> None:
    for verb in ("what", "when", "who", "where", "show", "list", "find", "summarize"):
        assert verb in task_router.DIRECT_VERBS


def test_initiative_verbs_includes_planning_signals() -> None:
    for verb in ("plan", "build", "launch", "develop", "orchestrate", "migrate"):
        assert verb in task_router.INITIATIVE_VERBS


def test_direct_length_threshold_is_80() -> None:
    assert task_router.DIRECT_LENGTH_THRESHOLD == 80


def test_verb_sets_are_immutable() -> None:
    assert isinstance(task_router.DIRECT_VERBS, frozenset)
    assert isinstance(task_router.INITIATIVE_VERBS, frozenset)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_task_router_constants.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.agents.runtime.task_router'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/task_router.py
# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Direct vs. initiative mode classifier per spec § 9.

Three-tier waterfall:
  1. Explicit override (/quick, /plan, persona default).
  2. Rule heuristics (verb match + length + open contract).
  3. LLM fallback (single Gemini Flash call).
"""

from __future__ import annotations

import logging

DIRECT_VERBS: frozenset[str] = frozenset({
    "what", "when", "who", "where",
    "show", "list", "find", "look", "look up",
    "summarize", "tell me", "fetch", "get",
})

INITIATIVE_VERBS: frozenset[str] = frozenset({
    "plan", "build", "launch", "develop", "orchestrate",
    "migrate", "run a campaign", "execute", "strategize",
})

DIRECT_LENGTH_THRESHOLD: int = 80

logger = logging.getLogger(__name__)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_task_router_constants.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/task_router.py tests/unit/agents/runtime/test_task_router_constants.py
git commit -m "feat(runtime): task_router verb constants and skeleton"
```

---

### Task 67: `_detect_override` — slash prefixes

**Files:**
- Edit: `app/agents/runtime/task_router.py`
- Test: `tests/unit/agents/runtime/test_task_router_override.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_task_router_override.py
"""Verify _detect_override recognizes /quick and /plan with case + whitespace tolerance."""
from __future__ import annotations

from app.agents.runtime import task_router


def test_quick_override_returns_direct() -> None:
    assert task_router._detect_override("/quick what is x") == "direct"


def test_plan_override_returns_initiative() -> None:
    assert task_router._detect_override("/plan launch the new product") == "initiative"


def test_override_is_case_insensitive() -> None:
    assert task_router._detect_override("/QUICK something") == "direct"
    assert task_router._detect_override("  /Plan  build foo") == "initiative"


def test_no_override_returns_none() -> None:
    assert task_router._detect_override("plan the launch") is None
    assert task_router._detect_override("what is q3 revenue") is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_task_router_override.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.task_router' has no attribute '_detect_override'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/task_router.py (append)
from app.agents.runtime.types import Mode


def _detect_override(text: str) -> Mode | None:
    """Return 'direct' for /quick prefix, 'initiative' for /plan, else None."""
    if not text:
        return None
    stripped = text.strip().lower()
    if stripped.startswith("/quick"):
        return "direct"
    if stripped.startswith("/plan"):
        return "initiative"
    return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_task_router_override.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/task_router.py tests/unit/agents/runtime/test_task_router_override.py
git commit -m "feat(runtime): task_router._detect_override for /quick and /plan"
```

---

### Task 68: `_apply_rules` — verb + length + open-contract heuristics

**Files:**
- Edit: `app/agents/runtime/task_router.py`
- Test: `tests/unit/agents/runtime/test_task_router_rules.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_task_router_rules.py
"""Verify _apply_rules implements every heuristic from spec § 9 step 2."""
from __future__ import annotations

from app.agents.runtime import task_router


def test_open_contract_forces_initiative() -> None:
    assert task_router._apply_rules(
        "what is x", session_has_open_contract=True
    ) == "initiative"


def test_short_factual_question_is_direct() -> None:
    assert task_router._apply_rules(
        "what is our Q3 revenue?", session_has_open_contract=False
    ) == "direct"


def test_initiative_verb_overrides_short_length() -> None:
    assert task_router._apply_rules(
        "plan the launch", session_has_open_contract=False
    ) == "initiative"


def test_run_a_campaign_phrase_is_initiative() -> None:
    assert task_router._apply_rules(
        "run a campaign for Q4 launch", session_has_open_contract=False
    ) == "initiative"


def test_at_mention_handoff_is_initiative() -> None:
    assert task_router._apply_rules(
        "@marketing kick off the holiday campaign please",
        session_has_open_contract=False,
    ) == "initiative"


def test_ambiguous_returns_none() -> None:
    assert task_router._apply_rules(
        "tell me something about our customers and how they feel about our new product line",
        session_has_open_contract=False,
    ) is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_task_router_rules.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.task_router' has no attribute '_apply_rules'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/task_router.py (append)
import re


def _apply_rules(text: str, *, session_has_open_contract: bool) -> Mode | None:
    """Rule heuristics per spec § 9.2. First conclusive answer wins.

    Order:
      1. Existing TaskContract on session  -> initiative.
      2. Initiative verbs present          -> initiative.
      3. @agent handoff / initiative id    -> initiative.
      4. Direct verb prefix + length < 80  -> direct.
      5. Otherwise None (caller falls through to LLM).
    """
    if session_has_open_contract:
        return "initiative"

    normalized = (text or "").strip().lower()
    if not normalized:
        return None

    # Initiative verbs (substring search to catch "run a campaign", "plan ...").
    for verb in INITIATIVE_VERBS:
        if verb in normalized:
            return "initiative"

    # @agent handoff or explicit initiative id.
    if re.search(r"(^|\s)@\w+", normalized):
        return "initiative"
    if re.search(r"\binitiative[_\- ]?id\b", normalized):
        return "initiative"

    # Short factual question — first token must be a direct verb.
    first_token = normalized.split()[0] if normalized.split() else ""
    if first_token in DIRECT_VERBS and len(normalized) < DIRECT_LENGTH_THRESHOLD:
        return "direct"
    # Also match multi-word direct prefixes ("look up", "tell me").
    for direct_prefix in DIRECT_VERBS:
        if " " in direct_prefix and normalized.startswith(direct_prefix):
            if len(normalized) < DIRECT_LENGTH_THRESHOLD:
                return "direct"

    return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_task_router_rules.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/task_router.py tests/unit/agents/runtime/test_task_router_rules.py
git commit -m "feat(runtime): task_router._apply_rules implements § 9 heuristics"
```

---

### Task 69: `_llm_classify` — Gemini Flash fallback parsing

**Files:**
- Edit: `app/agents/runtime/task_router.py`
- Test: `tests/unit/agents/runtime/test_task_router_llm.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_task_router_llm.py
"""Verify _llm_classify mocks Flash and parses {mode, confidence, reasoning}."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.agents.runtime import task_router


@pytest.mark.asyncio
async def test_llm_classify_returns_mode_and_confidence(monkeypatch) -> None:
    monkeypatch.setattr(
        task_router,
        "_call_classifier_llm",
        AsyncMock(return_value='{"mode":"initiative","confidence":0.82,"reasoning":"multi-step plan"}'),
    )
    result = await task_router._llm_classify("design the Q4 launch program for EMEA region")
    assert result.mode == "initiative"
    assert 0.0 <= result.confidence <= 1.0
    assert "multi-step" in (result.reasoning or "")
    assert result.signal == "llm"


@pytest.mark.asyncio
async def test_llm_classify_defaults_to_initiative_on_unparseable(monkeypatch) -> None:
    monkeypatch.setattr(task_router, "_call_classifier_llm", AsyncMock(return_value="garbage"))
    result = await task_router._llm_classify("ambiguous text here")
    assert result.mode == "initiative"  # safe default
    assert result.confidence == 0.0
    assert result.signal == "llm"


@pytest.mark.asyncio
async def test_llm_classify_defaults_when_llm_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(task_router, "_call_classifier_llm", AsyncMock(return_value=None))
    result = await task_router._llm_classify("ambiguous text here")
    assert result.mode == "initiative"
    assert result.signal == "llm"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_task_router_llm.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.task_router' has no attribute '_llm_classify'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/task_router.py (append)
import asyncio
import json
import os

from app.agents.runtime.types import ClassifierResult

CLASSIFIER_LLM_MODEL = os.getenv("TASK_ROUTER_LLM_MODEL", "gemini-2.5-flash")
CLASSIFIER_LLM_TIMEOUT_S = float(os.getenv("TASK_ROUTER_LLM_TIMEOUT_S", "8.0"))


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    return match.group(1).strip() if match else stripped


async def _call_classifier_llm(prompt: str) -> str | None:
    """Single low-latency Gemini Flash call. Returns text or None on failure."""
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        logger.warning("google.genai not available; task_router LLM skipped")
        return None
    try:
        client = genai.Client()
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=CLASSIFIER_LLM_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.0, max_output_tokens=256
                ),
            ),
            timeout=CLASSIFIER_LLM_TIMEOUT_S,
        )
        return (getattr(response, "text", None) or "").strip() or None
    except (asyncio.TimeoutError, Exception) as exc:  # noqa: BLE001
        logger.warning("task_router LLM call failed: %s", exc)
        return None


def _build_classifier_prompt(text: str) -> str:
    return (
        "Classify a user request as 'direct' (single fact/action, no plan needed) "
        "or 'initiative' (multi-step work requiring research, audit, and follow-up).\n\n"
        f"REQUEST: {text}\n\n"
        'Return ONLY JSON: {"mode":"direct"|"initiative","confidence":<0..1>,'
        '"reasoning":"<short>"}.'
    )


async def _llm_classify(text: str) -> ClassifierResult:
    """Fallback LLM classifier. Defaults to 'initiative' (safe) on failure."""
    raw = await _call_classifier_llm(_build_classifier_prompt(text))
    if not raw:
        return ClassifierResult(
            mode="initiative",
            confidence=0.0,
            reasoning="LLM unavailable; defaulted to initiative",
            signal="llm",
        )
    try:
        parsed = json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError:
        return ClassifierResult(
            mode="initiative",
            confidence=0.0,
            reasoning="LLM output unparseable; defaulted to initiative",
            signal="llm",
        )
    mode_raw = str(parsed.get("mode", "")).strip().lower()
    if mode_raw not in ("direct", "initiative"):
        mode_raw = "initiative"
    try:
        confidence = float(parsed.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(confidence, 1.0))
    return ClassifierResult(
        mode=mode_raw,  # type: ignore[arg-type]
        confidence=confidence,
        reasoning=str(parsed.get("reasoning", "") or "")[:240],
        signal="llm",
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_task_router_llm.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/task_router.py tests/unit/agents/runtime/test_task_router_llm.py
git commit -m "feat(runtime): task_router._llm_classify Gemini Flash fallback"
```

---

### Task 70: `classify` — three-tier waterfall

**Files:**
- Edit: `app/agents/runtime/task_router.py`
- Test: `tests/unit/agents/runtime/test_task_router_classify.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_task_router_classify.py
"""Verify classify() waterfall: override -> rule -> persona default -> LLM."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.agents.runtime import task_router
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.types import (
    ActionThresholds, ClassifierResult, PersonaPolicy, RateLimits,
)


def _policy(default_mode=None) -> PersonaPolicy:
    return PersonaPolicy(
        persona_id="solo",
        allowed_tool_ids="*",
        denied_tool_ids=[],
        action_thresholds=ActionThresholds(),
        rate_limits=RateLimits(),
        prompt_fragments=[],
        classifier_default_mode=default_mode,
        initiative_phases_blocked=[],
    )


@pytest.mark.asyncio
async def test_override_takes_first_precedence() -> None:
    result = await task_router.classify(
        "/quick what is q3 revenue",
        ops=OperationsConfig.defaults(agent_id="executive"),
        persona_policy=_policy(default_mode="initiative"),
        session_has_open_contract=True,  # would force initiative without override
    )
    assert result.mode == "direct"
    assert result.signal == "override"


@pytest.mark.asyncio
async def test_rule_used_when_no_override() -> None:
    result = await task_router.classify(
        "plan the launch",
        ops=OperationsConfig.defaults(agent_id="executive"),
        persona_policy=_policy(),
        session_has_open_contract=False,
    )
    assert result.mode == "initiative"
    assert result.signal == "rule"


@pytest.mark.asyncio
async def test_persona_default_used_before_llm(monkeypatch) -> None:
    fake_llm = AsyncMock()
    monkeypatch.setattr(task_router, "_llm_classify", fake_llm)
    result = await task_router.classify(
        "tell me something nuanced about retention and our customer mix over the last year",
        ops=OperationsConfig.defaults(agent_id="executive"),
        persona_policy=_policy(default_mode="direct"),
        session_has_open_contract=False,
    )
    assert result.mode == "direct"
    assert result.signal == "persona_default"
    fake_llm.assert_not_awaited()


@pytest.mark.asyncio
async def test_llm_used_when_all_else_inconclusive(monkeypatch) -> None:
    monkeypatch.setattr(
        task_router,
        "_llm_classify",
        AsyncMock(return_value=ClassifierResult(
            mode="initiative", confidence=0.6, reasoning="amb", signal="llm",
        )),
    )
    result = await task_router.classify(
        "tell me something nuanced about retention and our customer mix over the last year",
        ops=OperationsConfig.defaults(agent_id="executive"),
        persona_policy=_policy(),
        session_has_open_contract=False,
    )
    assert result.signal == "llm"
    assert result.mode == "initiative"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_task_router_classify.py -v
```

Expected: FAIL with `AttributeError: module 'app.agents.runtime.task_router' has no attribute 'classify'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/task_router.py (append)
from app.agents.runtime.operations_config import OperationsConfig


async def classify(
    request_text: str,
    *,
    ops: OperationsConfig,
    persona_policy: PersonaPolicy,
    session_has_open_contract: bool,
) -> ClassifierResult:
    """Three-tier waterfall classifier per spec § 9.

    Order:
      1. Explicit override (`/quick`, `/plan`).
      2. Rule heuristics (verbs + length + open contract).
      3. Persona default (policy.classifier_default_mode).
      4. LLM fallback.
    """
    override = _detect_override(request_text)
    if override is not None:
        return ClassifierResult(
            mode=override,
            confidence=1.0,
            reasoning="explicit /quick or /plan prefix",
            signal="override",
        )

    rule = _apply_rules(request_text, session_has_open_contract=session_has_open_contract)
    if rule is not None:
        return ClassifierResult(
            mode=rule,
            confidence=0.9,
            reasoning="rule heuristic match",
            signal="rule",
        )

    if persona_policy.classifier_default_mode in ("direct", "initiative"):
        return ClassifierResult(
            mode=persona_policy.classifier_default_mode,  # type: ignore[arg-type]
            confidence=0.5,
            reasoning=f"persona '{persona_policy.persona_id}' default",
            signal="persona_default",
        )

    # ops cautious agents fall back to a safe last_resort_default before LLM,
    # but spec § 9 requires the LLM call here. Honour ops by biasing the
    # default only if the LLM is unavailable.
    result = await _llm_classify(request_text)
    if result.confidence == 0.0 and getattr(ops.routing, "last_resort_default", None):
        result = result.model_copy(
            update={"mode": ops.routing.last_resort_default}
        )
    return result
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_task_router_classify.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/task_router.py tests/unit/agents/runtime/test_task_router_classify.py
git commit -m "feat(runtime): task_router.classify three-tier waterfall"
```

---

### Task 71: Research gate — `record_tool_result` rejects when run not in_progress

**Files:**
- Edit: `app/agents/runtime/research_gate.py`
- Test: `tests/unit/agents/runtime/test_research_gate_record_closed.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_research_gate_record_closed.py
"""Verify record_tool_result raises when the run is already complete or failed."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import research_gate
from app.agents.runtime.types import ResearchGateError


@pytest.mark.asyncio
async def test_record_tool_result_rejects_complete_run(monkeypatch) -> None:
    run_id = uuid4()
    select_chain = MagicMock()
    select_chain.execute = AsyncMock(
        return_value=MagicMock(
            data=[{"result": {"raw_results": []}, "iterations": 0, "status": "complete"}]
        )
    )
    select_chain.eq = MagicMock(return_value=select_chain)
    select_chain.select = MagicMock(return_value=select_chain)
    select_chain.single = MagicMock(return_value=select_chain)
    client = MagicMock(table=MagicMock(return_value=MagicMock(select=MagicMock(return_value=select_chain))))
    monkeypatch.setattr(research_gate, "_get_supabase", lambda: client)

    with pytest.raises(ResearchGateError):
        await research_gate.record_tool_result(
            run_id=run_id, tool_id="tavily_search", raw_result={}
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_research_gate_record_closed.py -v
```

Expected: FAIL — current `record_tool_result` does not inspect status.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/research_gate.py — modify record_tool_result
# (1) update the SELECT to also fetch status
# (2) refuse to record on closed runs

# Replace existing implementation body:
async def record_tool_result(
    *,
    run_id: UUID,
    tool_id: str,
    raw_result: dict,
) -> None:
    if tool_id not in RESEARCH_TOOL_IDS:
        raise ResearchGateError(
            f"record_tool_result called with non-research tool_id={tool_id!r}"
        )
    client = _get_supabase()
    row_resp = (
        await client.table("agent_research_runs")
        .select("result, iterations, status")
        .eq("id", str(run_id))
        .single()
        .execute()
    )
    data = getattr(row_resp, "data", None)
    if not data:
        raise ResearchGateError(f"run_id {run_id} not found")
    row = data[0] if isinstance(data, list) else data
    if row.get("status") in ("complete", "failed"):
        raise ResearchGateError(
            f"cannot record tool result on closed run {run_id} "
            f"(status={row.get('status')})"
        )
    existing = row.get("result") or {}
    raw_results = list(existing.get("raw_results") or [])
    raw_results.append({"tool_id": tool_id, "data": raw_result})
    merged = {**existing, "raw_results": raw_results}
    new_iter = int(row.get("iterations") or 0) + 1
    await (
        client.table("agent_research_runs")
        .update({"result": merged, "iterations": new_iter, "status": "in_progress"})
        .eq("id", str(run_id))
        .execute()
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_research_gate_record_closed.py tests/unit/agents/runtime/test_research_gate_record.py -v
```

Expected: PASS for both (the earlier Task 49 stub already passes since the new SELECT extends the column set).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/research_gate.py tests/unit/agents/runtime/test_research_gate_record_closed.py
git commit -m "fix(runtime): research_gate.record_tool_result rejects closed runs"
```

---

### Task 72: Audit `fail_on_any_unmet_criterion` interaction

**Files:**
- Test only: `tests/unit/agents/runtime/test_audit_fail_on_unmet.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_audit_fail_on_unmet.py
"""Verify ops.audit.fail_on_any_unmet_criterion overrides an over-generous LLM 'pass'."""
from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.agents.runtime import audit
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.types import (
    Artifact, ResearchResult, TaskContract, TodoItem,
)


def _contract() -> TaskContract:
    return TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="g",
        todo_items=[TodoItem(id="t1", title="x", description=None)],
        success_criteria=["c1"],
        owners=[],
        evidence_required=[],
        initiative_id=None,
        initiative_phase=None,
        sibling_steps=[],
    )


@pytest.mark.asyncio
async def test_pass_downgraded_to_fail_when_criterion_unmet(monkeypatch) -> None:
    monkeypatch.setattr(
        audit,
        "_call_audit_llm",
        AsyncMock(return_value=(
            '{"overall_status":"pass","per_item":[],'
            '"per_criterion":[{"criterion":"c1","met":false,"justification":"weak"}],'
            '"gaps":["c1 unmet"],"recoverable":true,"next_action":"submit"}'
        )),
    )

    ops = OperationsConfig.defaults(agent_id="financial")
    ops.audit.fail_on_any_unmet_criterion = True  # belt-and-braces

    report = await audit.audit_against_contract(
        _contract(),
        [Artifact(kind="doc", ref="r", summary="s", payload={})],
        ResearchResult(
            summary="s", sources=[], contradictions=[],
            coverage_assessment="complete", missing_information=[],
        ),
        ops=ops,
    )
    assert report.overall_status == "fail"
    assert report.next_action == "retry"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_audit_fail_on_unmet.py -v
```

Expected: PASS already if Task 57 implementation honors the flag; otherwise FAIL and the implementation is updated.

- [ ] **Step 3: Write minimal implementation**

No code changes if Task 57 is correct. If FAIL, ensure the post-process block from Task 57 downgrades `pass → fail` and `submit → retry` whenever `any(not c.met)`.

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_audit_fail_on_unmet.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/agents/runtime/test_audit_fail_on_unmet.py
git commit -m "test(runtime): audit downgrades pass to fail when criterion unmet"
```

---

### Task 73: Persona gate — wildcard allow with empty deny passes everything

**Files:**
- Test only: `tests/unit/agents/runtime/test_persona_gate_wildcard.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_persona_gate_wildcard.py
"""Stress-test wildcard + empty deny against random tool ids."""
from __future__ import annotations

import pytest

from app.agents.runtime import persona_gate
from app.agents.runtime.types import (
    ActionThresholds, PersonaPolicy, RateLimits,
)


def _wildcard_policy() -> PersonaPolicy:
    return PersonaPolicy(
        persona_id="solopreneur",
        allowed_tool_ids="*",
        denied_tool_ids=[],
        action_thresholds=ActionThresholds(),
        rate_limits=RateLimits(),
        prompt_fragments=[],
        classifier_default_mode=None,
        initiative_phases_blocked=[],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_id",
    ["calendar_list", "vault_search", "video_render", "image_generate", "sheet_read"],
)
async def test_wildcard_permits(tool_id) -> None:
    await persona_gate.check_tool_allowed(tool_id, _wildcard_policy())
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_persona_gate_wildcard.py -v
```

Expected: PASS (regression test on Task 62 behavior).

- [ ] **Step 3: Write minimal implementation**

No code change required; this is a regression test pinning § 13 contract.

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_persona_gate_wildcard.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/agents/runtime/test_persona_gate_wildcard.py
git commit -m "test(runtime): persona_gate wildcard regression"
```

---

### Task 74: Task router — `@agent` plus open contract still resolves correctly

**Files:**
- Test only: `tests/unit/agents/runtime/test_task_router_integration.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_task_router_integration.py
"""End-to-end: open contract + override + persona default interactions."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.agents.runtime import task_router
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.types import (
    ActionThresholds, PersonaPolicy, RateLimits,
)


def _policy(default_mode=None) -> PersonaPolicy:
    return PersonaPolicy(
        persona_id="enterprise",
        allowed_tool_ids="*",
        denied_tool_ids=[],
        action_thresholds=ActionThresholds(),
        rate_limits=RateLimits(),
        prompt_fragments=[],
        classifier_default_mode=default_mode,
        initiative_phases_blocked=[],
    )


@pytest.mark.asyncio
async def test_quick_override_beats_open_contract(monkeypatch) -> None:
    fake_llm = AsyncMock()
    monkeypatch.setattr(task_router, "_llm_classify", fake_llm)
    result = await task_router.classify(
        "/quick what's the current MRR",
        ops=OperationsConfig.defaults(agent_id="executive"),
        persona_policy=_policy(),
        session_has_open_contract=True,
    )
    assert result.mode == "direct"
    fake_llm.assert_not_awaited()


@pytest.mark.asyncio
async def test_at_agent_overrides_persona_default(monkeypatch) -> None:
    fake_llm = AsyncMock()
    monkeypatch.setattr(task_router, "_llm_classify", fake_llm)
    result = await task_router.classify(
        "@marketing kick off the spring campaign",
        ops=OperationsConfig.defaults(agent_id="executive"),
        persona_policy=_policy(default_mode="direct"),
        session_has_open_contract=False,
    )
    assert result.signal == "rule"
    assert result.mode == "initiative"
    fake_llm.assert_not_awaited()


@pytest.mark.asyncio
async def test_open_contract_short_question_is_initiative(monkeypatch) -> None:
    fake_llm = AsyncMock()
    monkeypatch.setattr(task_router, "_llm_classify", fake_llm)
    result = await task_router.classify(
        "what is x?",
        ops=OperationsConfig.defaults(agent_id="executive"),
        persona_policy=_policy(),
        session_has_open_contract=True,
    )
    assert result.mode == "initiative"
    assert result.signal == "rule"
    fake_llm.assert_not_awaited()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_task_router_integration.py -v
```

Expected: PASS if waterfall is correct; otherwise the gap is fixed in `classify`/`_apply_rules`.

- [ ] **Step 3: Write minimal implementation**

No new code unless a test fails — this locks the spec § 9 contract end-to-end.

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_task_router_integration.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/agents/runtime/test_task_router_integration.py
git commit -m "test(runtime): task_router waterfall integration"
```

---

### Task 75: Module re-exports + linter sweep

**Files:**
- Edit: `app/agents/runtime/__init__.py`
- Test: `tests/unit/agents/runtime/test_section_c_exports.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/runtime/test_section_c_exports.py
"""Verify the runtime package exposes the gate/audit/persona/router public API."""
from __future__ import annotations

import app.agents.runtime as runtime


def test_research_gate_api_exposed() -> None:
    for name in (
        "RESEARCH_TOOL_IDS",
        "open_gate",
        "is_open",
        "record_tool_result",
        "check_coverage",
        "close_gate",
    ):
        assert hasattr(runtime, name), name


def test_audit_api_exposed() -> None:
    for name in (
        "audit_against_contract",
        "persist_audit_report",
        "attach_audit_summary_to_evidence",
    ):
        assert hasattr(runtime, name), name


def test_persona_gate_api_exposed() -> None:
    for name in (
        "load_persona_policy",
        "check_tool_allowed",
        "check_action_threshold",
        "apply_prompt_fragments",
        "record_violation",
    ):
        assert hasattr(runtime, name), name


def test_task_router_api_exposed() -> None:
    for name in ("classify", "DIRECT_VERBS", "INITIATIVE_VERBS", "DIRECT_LENGTH_THRESHOLD"):
        assert hasattr(runtime, name), name
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/runtime/test_section_c_exports.py -v
```

Expected: FAIL — the umbrella `__init__` does not re-export these symbols yet.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/__init__.py
# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Pikar agent runtime — gates, audit, persona, router, lifecycle.

Section A defines types/operations_config. Section C wires in the gate modules
below. Other sections add lifecycle/handoff/publication on top.
"""

from app.agents.runtime.audit import (
    attach_audit_summary_to_evidence,
    audit_against_contract,
    persist_audit_report,
)
from app.agents.runtime.persona_gate import (
    apply_prompt_fragments,
    check_action_threshold,
    check_tool_allowed,
    load_persona_policy,
    record_violation,
)
from app.agents.runtime.research_gate import (
    RESEARCH_TOOL_IDS,
    check_coverage,
    close_gate,
    is_open,
    open_gate,
    record_tool_result,
)
from app.agents.runtime.task_router import (
    DIRECT_LENGTH_THRESHOLD,
    DIRECT_VERBS,
    INITIATIVE_VERBS,
    classify,
)

__all__ = [
    "DIRECT_LENGTH_THRESHOLD",
    "DIRECT_VERBS",
    "INITIATIVE_VERBS",
    "RESEARCH_TOOL_IDS",
    "apply_prompt_fragments",
    "attach_audit_summary_to_evidence",
    "audit_against_contract",
    "check_action_threshold",
    "check_coverage",
    "check_tool_allowed",
    "classify",
    "close_gate",
    "is_open",
    "load_persona_policy",
    "open_gate",
    "persist_audit_report",
    "record_tool_result",
    "record_violation",
]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/runtime/test_section_c_exports.py -v
uv run ruff check app/agents/runtime/ --fix
uv run ruff format app/agents/runtime/
uv run pytest tests/unit/agents/runtime/ -v
```

Expected: All PASS; ruff clean.

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/__init__.py tests/unit/agents/runtime/test_section_c_exports.py
git commit -m "feat(runtime): re-export research_gate, audit, persona_gate, task_router"
```

---

## Section D — Execution rituals, publication, workspace SSE (Tasks 76–105)

### Task 76: Add `WorkspaceProgressEvent` and `WorkspaceArtifactEvent` round-trip tests for the runtime types module

**Files:**
- Edit: `app/agents/runtime/types.py` (Section A — verify event models)
- Test: `tests/unit/runtime/test_workspace_event_types.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_workspace_event_types.py
"""Workspace event types must serialise to the shape consumed by the SSE client."""

from uuid import uuid4

from app.agents.runtime.types import (
    WorkspaceArtifactEvent,
    WorkspaceProgressEvent,
)


def test_progress_event_round_trip():
    evt = WorkspaceProgressEvent(
        kind="progress",
        agent_id="financial",
        contract_id=uuid4(),
        item="Pull Q3 revenue",
        status="in_progress",
    )
    payload = evt.model_dump(mode="json")
    assert payload["kind"] == "progress"
    assert payload["status"] == "in_progress"
    restored = WorkspaceProgressEvent.model_validate(payload)
    assert restored == evt


def test_artifact_event_round_trip_with_optional_preview():
    evt = WorkspaceArtifactEvent(
        kind="artifact",
        agent_id="content_creation",
        contract_id=None,
        artifact_kind="video_render",
        ref="storage://videos/abc.mp4",
        summary="60-second hero cut",
        preview_url=None,
    )
    payload = evt.model_dump(mode="json")
    assert payload["preview_url"] is None
    assert payload["artifact_kind"] == "video_render"
    restored = WorkspaceArtifactEvent.model_validate(payload)
    assert restored == evt
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_workspace_event_types.py -v
```

Expected: FAIL — `app.agents.runtime.types` not yet importable / event classes missing (Section A defines them; this task pins the shape).

- [ ] **Step 3: Write minimal implementation**

Section A owns `types.py`; this task only verifies the contract. If failing, append (Section A is the canonical owner):

```python
# app/agents/runtime/types.py — pinned shape (excerpt)
from typing import Literal
from uuid import UUID
from pydantic import BaseModel


class WorkspaceProgressEvent(BaseModel):
    kind: Literal["progress"] = "progress"
    agent_id: str
    contract_id: UUID | None = None
    item: str
    status: Literal["started", "in_progress", "blocked"]


class WorkspaceArtifactEvent(BaseModel):
    kind: Literal["artifact"] = "artifact"
    agent_id: str
    contract_id: UUID | None = None
    artifact_kind: str
    ref: str
    summary: str
    preview_url: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_workspace_event_types.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/runtime/test_workspace_event_types.py app/agents/runtime/types.py
git commit -m "test(runtime): pin WorkspaceProgressEvent / WorkspaceArtifactEvent shapes"
```

---

### Task 77: `workspace_event_bus.publish` writes to Redis pub/sub when connected

**Files:**
- Create: `app/services/workspace_event_bus.py`
- Test: `tests/unit/services/test_workspace_event_bus_publish.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/services/test_workspace_event_bus_publish.py
"""workspace_event_bus.publish — Redis pub/sub happy path."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.agents.runtime.types import WorkspaceProgressEvent
from app.services import workspace_event_bus


@pytest.mark.asyncio
async def test_publish_emits_on_user_channel(monkeypatch):
    user_id = uuid4()
    fake_redis = AsyncMock()
    fake_redis.publish = AsyncMock(return_value=1)

    async def fake_ensure_connection(self):
        return fake_redis

    from app.services.cache import CacheService

    monkeypatch.setattr(CacheService, "_ensure_connection", fake_ensure_connection)

    event = WorkspaceProgressEvent(
        agent_id="financial",
        contract_id=uuid4(),
        item="Read income statement",
        status="started",
    )
    await workspace_event_bus.publish(user_id, event)

    assert fake_redis.publish.await_count == 1
    channel, payload = fake_redis.publish.await_args.args
    assert channel == f"pikar:workspace:{user_id}"
    assert '"kind":"progress"' in payload
    assert '"status":"started"' in payload


@pytest.mark.asyncio
async def test_publish_noop_when_redis_unavailable(monkeypatch):
    user_id = uuid4()

    async def fake_ensure_connection(self):
        return None

    from app.services.cache import CacheService

    monkeypatch.setattr(CacheService, "_ensure_connection", fake_ensure_connection)

    event = WorkspaceProgressEvent(
        agent_id="financial",
        contract_id=None,
        item="x",
        status="started",
    )
    # Must not raise — degraded mode (matches circuit-breaker contract).
    await workspace_event_bus.publish(user_id, event)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/services/test_workspace_event_bus_publish.py -v
```

Expected: FAIL — module `app.services.workspace_event_bus` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
# app/services/workspace_event_bus.py
"""Per-user workspace SSE channel manager backed by Redis pub/sub.

Reuses the singleton ``CacheService`` Redis client so we share the circuit
breaker and connection pool. Channel naming: ``pikar:workspace:{user_id}``.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Union
from uuid import UUID

from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.agents.runtime.types import (
    WorkspaceArtifactEvent,
    WorkspaceProgressEvent,
)
from app.services.cache import get_cache_service

logger = logging.getLogger(__name__)

WorkspaceEvent = Union[WorkspaceProgressEvent, WorkspaceArtifactEvent]

_CHANNEL_PREFIX = "pikar:workspace:"


def _channel_for(user_id: UUID) -> str:
    return f"{_CHANNEL_PREFIX}{user_id}"


async def publish(user_id: UUID, event: WorkspaceEvent) -> None:
    """Best-effort publish onto the user's workspace channel.

    Silently degrades when Redis is unavailable — workspace events are
    presentation-only; durable state lives in ``agent_task_executions``.
    """
    cache = get_cache_service()
    try:
        client = await cache._ensure_connection()
    except (RedisConnectionError, RedisTimeoutError) as exc:
        logger.warning("workspace_event_bus.publish: Redis connect failed: %s", exc)
        return

    if client is None:
        return

    payload = event.model_dump_json()
    try:
        await client.publish(_channel_for(user_id), payload)
    except (RedisConnectionError, RedisTimeoutError) as exc:
        logger.warning("workspace_event_bus.publish: publish failed: %s", exc)
    except Exception as exc:  # noqa: BLE001 — never crash callers
        logger.exception("workspace_event_bus.publish: unexpected error: %s", exc)


async def subscribe(user_id: UUID) -> AsyncIterator[WorkspaceEvent]:  # pragma: no cover — covered in Task 78
    """Subscribe to the user's workspace channel. Yields parsed events."""
    cache = get_cache_service()
    client = await cache._ensure_connection()
    if client is None:
        # Redis disabled: yield nothing, caller's stream stays open via heartbeats.
        while True:
            await asyncio.sleep(15)
            yield  # type: ignore[misc]

    pubsub = client.pubsub()
    await pubsub.subscribe(_channel_for(user_id))
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            raw = message.get("data")
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            try:
                data = json.loads(raw)
            except (TypeError, ValueError):
                logger.warning("workspace_event_bus: discarding bad payload: %r", raw)
                continue
            kind = data.get("kind")
            if kind == "progress":
                yield WorkspaceProgressEvent.model_validate(data)
            elif kind == "artifact":
                yield WorkspaceArtifactEvent.model_validate(data)
            else:
                logger.warning("workspace_event_bus: unknown kind=%r", kind)
    finally:
        try:
            await pubsub.unsubscribe(_channel_for(user_id))
            await pubsub.close()
        except Exception:  # noqa: BLE001
            pass
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/services/test_workspace_event_bus_publish.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/workspace_event_bus.py tests/unit/services/test_workspace_event_bus_publish.py
git commit -m "feat(runtime): workspace_event_bus.publish via Redis pub/sub"
```

---

### Task 78: `workspace_event_bus.subscribe` yields parsed events from pubsub

**Files:**
- Edit: `app/services/workspace_event_bus.py`
- Test: `tests/unit/services/test_workspace_event_bus_subscribe.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/services/test_workspace_event_bus_subscribe.py
"""workspace_event_bus.subscribe — yields typed events parsed from Redis."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime.types import (
    WorkspaceArtifactEvent,
    WorkspaceProgressEvent,
)
from app.services import workspace_event_bus


class _FakePubSub:
    def __init__(self, messages):
        self._messages = messages
        self.subscribe = AsyncMock()
        self.unsubscribe = AsyncMock()
        self.close = AsyncMock()

    async def listen(self):
        for m in self._messages:
            yield m


@pytest.mark.asyncio
async def test_subscribe_yields_progress_then_artifact(monkeypatch):
    user_id = uuid4()
    progress = WorkspaceProgressEvent(
        agent_id="data", contract_id=None, item="step-1", status="in_progress"
    )
    artifact = WorkspaceArtifactEvent(
        agent_id="data",
        contract_id=None,
        artifact_kind="report",
        ref="vault://abc",
        summary="Q3 numbers",
        preview_url=None,
    )

    messages = [
        {"type": "subscribe", "data": 1},
        {"type": "message", "data": progress.model_dump_json().encode()},
        {"type": "message", "data": artifact.model_dump_json().encode()},
    ]

    fake_pubsub = _FakePubSub(messages)
    fake_redis = MagicMock()
    fake_redis.pubsub = MagicMock(return_value=fake_pubsub)

    async def fake_ensure_connection(self):
        return fake_redis

    from app.services.cache import CacheService

    monkeypatch.setattr(CacheService, "_ensure_connection", fake_ensure_connection)

    received: list = []
    async for evt in workspace_event_bus.subscribe(user_id):
        received.append(evt)
        if len(received) == 2:
            break

    assert received[0] == progress
    assert received[1] == artifact
    fake_pubsub.subscribe.assert_awaited_once_with(f"pikar:workspace:{user_id}")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/services/test_workspace_event_bus_subscribe.py -v
```

Expected: FAIL — the `pragma: no cover` `subscribe` stub never validates against a real fake pubsub.

- [ ] **Step 3: Write minimal implementation**

The `subscribe` body is already written in Task 77 — remove the `pragma: no cover` and tighten the no-Redis branch:

```python
# app/services/workspace_event_bus.py — replace subscribe()
async def subscribe(user_id: UUID) -> AsyncIterator[WorkspaceEvent]:
    """Subscribe to the user's workspace channel. Yields parsed events."""
    cache = get_cache_service()
    client = await cache._ensure_connection()
    if client is None:
        logger.info("workspace_event_bus.subscribe: Redis unavailable, no events")
        return

    pubsub = client.pubsub()
    await pubsub.subscribe(_channel_for(user_id))
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            raw = message.get("data")
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            try:
                data = json.loads(raw)
            except (TypeError, ValueError):
                logger.warning("workspace_event_bus: discarding bad payload: %r", raw)
                continue
            kind = data.get("kind")
            if kind == "progress":
                yield WorkspaceProgressEvent.model_validate(data)
            elif kind == "artifact":
                yield WorkspaceArtifactEvent.model_validate(data)
            else:
                logger.warning("workspace_event_bus: unknown kind=%r", kind)
    finally:
        try:
            await pubsub.unsubscribe(_channel_for(user_id))
            await pubsub.close()
        except Exception:  # noqa: BLE001
            pass
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/services/test_workspace_event_bus_subscribe.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/workspace_event_bus.py tests/unit/services/test_workspace_event_bus_subscribe.py
git commit -m "feat(runtime): workspace_event_bus.subscribe streams typed events"
```

---

### Task 79: `subscribe` ignores malformed JSON and unknown kinds without raising

**Files:**
- Test: `tests/unit/services/test_workspace_event_bus_resilience.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/services/test_workspace_event_bus_resilience.py
"""subscribe must skip junk payloads — workspace UX should never crash."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime.types import WorkspaceProgressEvent
from app.services import workspace_event_bus


class _FakePubSub:
    def __init__(self, messages):
        self._messages = messages
        self.subscribe = AsyncMock()
        self.unsubscribe = AsyncMock()
        self.close = AsyncMock()

    async def listen(self):
        for m in self._messages:
            yield m


@pytest.mark.asyncio
async def test_subscribe_skips_bad_json_and_unknown_kinds(monkeypatch):
    user_id = uuid4()
    good = WorkspaceProgressEvent(
        agent_id="data", contract_id=None, item="step", status="started"
    )
    messages = [
        {"type": "message", "data": b"not-json"},
        {"type": "message", "data": b'{"kind":"telepathy"}'},
        {"type": "message", "data": good.model_dump_json().encode()},
    ]
    fake_pubsub = _FakePubSub(messages)
    fake_redis = MagicMock()
    fake_redis.pubsub = MagicMock(return_value=fake_pubsub)

    async def fake_ensure_connection(self):
        return fake_redis

    from app.services.cache import CacheService

    monkeypatch.setattr(CacheService, "_ensure_connection", fake_ensure_connection)

    received: list = []
    async for evt in workspace_event_bus.subscribe(user_id):
        received.append(evt)
        break

    assert received == [good]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/services/test_workspace_event_bus_resilience.py -v
```

Expected: PASS already (Task 78 handles both cases). If it fails (regression), tighten the warnings/`continue` paths in `subscribe`.

- [ ] **Step 3: Write minimal implementation**

No code change expected. If test fails, ensure `continue` after each `logger.warning` in the `subscribe` loop.

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/services/test_workspace_event_bus_resilience.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/services/test_workspace_event_bus_resilience.py
git commit -m "test(runtime): workspace_event_bus drops malformed payloads"
```

---

### Task 80: `GET /workspace/events` SSE endpoint streams from `workspace_event_bus.subscribe`

**Files:**
- Create: `app/routers/workspace.py`
- Test: `tests/unit/routers/test_workspace_events_sse.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/routers/test_workspace_events_sse.py
"""GET /workspace/events — SSE endpoint streams typed events as `data:` frames."""

from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agents.runtime.types import (
    WorkspaceArtifactEvent,
    WorkspaceProgressEvent,
)
from app.routers import workspace as workspace_router
from app.routers.onboarding import get_current_user_id


@pytest.fixture
def app(monkeypatch):
    user_id = "11111111-1111-1111-1111-111111111111"

    async def override_user():
        return user_id

    progress = WorkspaceProgressEvent(
        agent_id="data", contract_id=None, item="x", status="started"
    )
    artifact = WorkspaceArtifactEvent(
        agent_id="data",
        contract_id=None,
        artifact_kind="report",
        ref="vault://abc",
        summary="ok",
        preview_url=None,
    )

    async def fake_subscribe(uid: UUID):
        assert str(uid) == user_id
        yield progress
        yield artifact

    monkeypatch.setattr(
        workspace_router.workspace_event_bus, "subscribe", fake_subscribe
    )

    app = FastAPI()
    app.include_router(workspace_router.router)
    app.dependency_overrides[get_current_user_id] = override_user
    return app


def test_workspace_events_emits_two_data_frames(app):
    with TestClient(app) as client:
        with client.stream("GET", "/workspace/events") as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            body = b""
            for chunk in response.iter_raw():
                body += chunk
                if body.count(b"data:") >= 2:
                    break

    text = body.decode("utf-8")
    assert text.count("data:") >= 2
    assert '"kind":"progress"' in text
    assert '"kind":"artifact"' in text
    # SSE framing: each event ends with a blank line.
    assert "\n\n" in text
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/routers/test_workspace_events_sse.py -v
```

Expected: FAIL — `app/routers/workspace.py` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
# app/routers/workspace.py
"""Workspace SSE endpoint.

Streams ``workspace_event_bus`` events to the authenticated user's browser
for live updates of the ActiveWorkspace canvas. Frames follow the SSE spec
(``data: <json>\\n\\n``).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.routers.onboarding import get_current_user_id
from app.services import workspace_event_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspace", tags=["Workspace"])

_HEARTBEAT_INTERVAL_S = 15.0


async def _event_stream(user_id: UUID, request: Request) -> AsyncIterator[bytes]:
    """Yield SSE-formatted bytes from the user's workspace channel.

    Interleaves a heartbeat comment every 15s so proxies don't close the
    connection during quiet periods.
    """
    queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    async def _pump() -> None:
        try:
            async for event in workspace_event_bus.subscribe(user_id):
                await queue.put(f"data: {event.model_dump_json()}\n\n".encode())
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("workspace SSE pump failed for user %s", user_id)
        finally:
            await queue.put(None)

    pump_task = asyncio.create_task(_pump())
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                item = await asyncio.wait_for(
                    queue.get(), timeout=_HEARTBEAT_INTERVAL_S
                )
            except asyncio.TimeoutError:
                yield b": heartbeat\n\n"
                continue
            if item is None:
                break
            yield item
    finally:
        pump_task.cancel()
        try:
            await pump_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass


@router.get("/events")
async def workspace_events(
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> StreamingResponse:
    """SSE stream of workspace progress + artifact events for the current user."""
    return StreamingResponse(
        _event_stream(UUID(user_id), request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/routers/test_workspace_events_sse.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/routers/workspace.py tests/unit/routers/test_workspace_events_sse.py
git commit -m "feat(runtime): GET /workspace/events SSE stream"
```

---

### Task 81: Register the workspace router in `fast_api_app.py`

**Files:**
- Edit: `app/fast_api_app.py`
- Test: `tests/unit/routers/test_workspace_router_registered.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/routers/test_workspace_router_registered.py
"""The workspace router must be mounted under the main FastAPI app."""


def test_workspace_router_registered():
    from app.fast_api_app import app

    paths = {route.path for route in app.routes}
    assert "/workspace/events" in paths
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/routers/test_workspace_router_registered.py -v
```

Expected: FAIL — router not yet included.

- [ ] **Step 3: Write minimal implementation**

```python
# app/fast_api_app.py — add import + include_router
from app.routers import workspace as workspace_router  # noqa: E402

# ... after the other include_router(...) calls:
app.include_router(workspace_router.router)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/routers/test_workspace_router_registered.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/fast_api_app.py tests/unit/routers/test_workspace_router_registered.py
git commit -m "feat(runtime): mount workspace router on FastAPI app"
```

---

### Task 82: `render_report_markdown` produces the Layer-2 report per spec § 11

**Files:**
- Create: `app/agents/runtime/publication.py`
- Test: `tests/unit/runtime/test_render_report_markdown.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_render_report_markdown.py
"""render_report_markdown — must include all required sections (spec §11)."""

from uuid import uuid4

import pytest

from app.agents.runtime.publication import render_report_markdown
from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    ResearchResult,
    Source,
    TaskContract,
    TodoItem,
)


@pytest.mark.asyncio
async def test_report_contains_all_required_sections():
    contract = TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="Forecast Q3 revenue",
        todo_items=[
            TodoItem(id=uuid4(), title="Pull historicals", status="completed"),
            TodoItem(id=uuid4(), title="Build model", status="completed"),
        ],
        success_criteria=["Forecast +/- 5%", "Three scenarios"],
        owners=["financial"],
        evidence_required=["draft_artifact"],
        initiative_id=uuid4(),
        initiative_phase="validation",
        sibling_steps=[],
    )
    research = ResearchResult(
        summary="Revenue grew 18% YoY...",
        sources=[
            Source(
                url="https://example.com/r1",
                title="ARR trend",
                key_claim="ARR +18%",
                retrieved_at="2026-05-11T10:00:00Z",
            )
        ],
        contradictions=["Q1 vs Q2 churn delta unresolved"],
        coverage_assessment="complete",
        missing_information=[],
    )
    audit = AuditReport(
        overall_status="pass",
        per_item=[],
        per_criterion=[],
        gaps=[],
        policy_violations=[],
        recoverable=True,
        next_action="submit",
    )
    artifacts = [
        Artifact(
            kind="report",
            ref="vault://draft-forecast",
            summary="Forecast doc",
            payload={},
        )
    ]

    md = await render_report_markdown(
        contract=contract,
        research=research,
        audit=audit,
        artifacts=artifacts,
        agent_id="financial",
    )

    for required in (
        "## Goal",
        "## To-Do Outcomes",
        "## Success Criteria",
        "## Research Summary",
        "### Sources",
        "### Contradictions Flagged",
        "## Artifacts",
        "## Audit Report",
        "## Policy Notes",
        "## Follow-ups",
    ):
        assert required in md, f"missing section: {required}"
    assert "Forecast Q3 revenue" in md
    assert "Pull historicals" in md
    assert "Build model" in md
    assert "ARR trend" in md
    assert "Q1 vs Q2 churn delta unresolved" in md
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_render_report_markdown.py -v
```

Expected: FAIL — module `app.agents.runtime.publication` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/publication.py
"""Single publication primitive — four sinks per spec §12.

Imports are deferred where they would form runtime cycles with agents.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    DirectRequest,
    ResearchResult,
    TaskContract,
    WorkspaceArtifactEvent,
    WorkspaceProgressEvent,
)

logger = logging.getLogger(__name__)


VAULT_BOUND_KINDS = {"report", "doc", "video_render", "image", "spreadsheet"}


async def render_report_markdown(
    *,
    contract: TaskContract,
    research: ResearchResult,
    audit: AuditReport,
    artifacts: list[Artifact],
    agent_id: str,
) -> str:
    """Produce the structured markdown report (spec §11 Layer-2 template)."""
    now_iso = datetime.now(timezone.utc).isoformat()
    lines: list[str] = []
    lines.append(f"# {agent_id} — {contract.goal}")
    lines.append(
        f"**Initiative:** `{contract.initiative_id}` · "
        f"**Phase:** {contract.initiative_phase or '—'} · "
        f"**Date:** {now_iso}"
    )
    lines.append(
        f"**Owner:** {agent_id} · **Task:** `{contract.id}`"
    )
    lines.append("")
    lines.append("## Goal")
    lines.append(contract.goal)
    lines.append("")
    lines.append("## To-Do Outcomes")
    lines.append("| Item | Status | Evidence |")
    lines.append("| --- | --- | --- |")
    for item in contract.todo_items:
        evidence = ", ".join(getattr(item, "evidence_pointers", []) or []) or "—"
        lines.append(f"| {item.title} | {item.status} | {evidence} |")
    lines.append("")
    lines.append("## Success Criteria")
    if contract.success_criteria:
        for crit in contract.success_criteria:
            lines.append(f"- {crit}")
    else:
        lines.append("- _none declared_")
    lines.append("")
    lines.append("## Research Summary")
    lines.append(research.summary or "_(no research captured)_")
    lines.append("")
    lines.append(f"### Sources ({len(research.sources)})")
    for src in research.sources:
        lines.append(f"- [{src.title}]({src.url}) — {src.key_claim}")
    lines.append("")
    lines.append("### Contradictions Flagged")
    if research.contradictions:
        for c in research.contradictions:
            lines.append(f"- {c}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Artifacts")
    for art in artifacts:
        lines.append(f"- **{art.kind}** — {art.summary} (`{art.ref}`)")
    if not artifacts:
        lines.append("- _no artifacts produced_")
    lines.append("")
    lines.append("## Audit Report")
    lines.append(f"**Status:** {audit.overall_status}")
    if audit.gaps:
        lines.append("**Gaps:**")
        for g in audit.gaps:
            lines.append(f"- {g}")
    lines.append("")
    lines.append("## Policy Notes")
    if audit.policy_violations:
        for v in audit.policy_violations:
            lines.append(f"- {v}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Follow-ups")
    if research.missing_information:
        for m in research.missing_information:
            lines.append(f"- Open: {m}")
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_render_report_markdown.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/publication.py tests/unit/runtime/test_render_report_markdown.py
git commit -m "feat(runtime): render_report_markdown emits Layer-2 template"
```

---

### Task 83: `emit_progress_event` is a thin wrapper around `workspace_event_bus.publish`

**Files:**
- Edit: `app/agents/runtime/publication.py`
- Test: `tests/unit/runtime/test_emit_progress_event.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_emit_progress_event.py
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.agents.runtime import publication
from app.agents.runtime.types import WorkspaceProgressEvent


@pytest.mark.asyncio
async def test_emit_progress_event_calls_event_bus(monkeypatch):
    user_id = uuid4()
    contract_id = uuid4()
    publish = AsyncMock()
    monkeypatch.setattr(publication.workspace_event_bus, "publish", publish)

    await publication.emit_progress_event(
        user_id=user_id,
        agent_id="financial",
        contract_id=contract_id,
        item="Pull income statement",
        status="in_progress",
    )

    publish.assert_awaited_once()
    args, _ = publish.await_args
    assert args[0] == user_id
    event = args[1]
    assert isinstance(event, WorkspaceProgressEvent)
    assert event.item == "Pull income statement"
    assert event.status == "in_progress"
    assert event.agent_id == "financial"
    assert event.contract_id == contract_id
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_emit_progress_event.py -v
```

Expected: FAIL — `emit_progress_event` not yet defined.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/publication.py — add at the top
from app.services import workspace_event_bus

# ... and append:

async def emit_progress_event(
    *,
    user_id: UUID,
    agent_id: str,
    contract_id: UUID | None,
    item: str,
    status: Literal["started", "in_progress", "blocked"],
) -> None:
    """Convenience wrapper around ``workspace_event_bus.publish``."""
    event = WorkspaceProgressEvent(
        agent_id=agent_id,
        contract_id=contract_id,
        item=item,
        status=status,
    )
    await workspace_event_bus.publish(user_id, event)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_emit_progress_event.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/publication.py tests/unit/runtime/test_emit_progress_event.py
git commit -m "feat(runtime): emit_progress_event helper for workspace SSE"
```

---

### Task 84: `publish_artifact` writes the `agent_task_executions` row on first artifact

**Files:**
- Edit: `app/agents/runtime/publication.py`
- Test: `tests/unit/runtime/test_publish_artifact_db_row.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_publish_artifact_db_row.py
"""publish_artifact must upsert agent_task_executions and append the artifact."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import publication
from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    DirectRequest,
    TaskContract,
    TodoItem,
)


@pytest.mark.asyncio
async def test_publish_artifact_inserts_execution_row(monkeypatch):
    user_id = uuid4()
    contract = TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="Compose newsletter",
        todo_items=[TodoItem(id=uuid4(), title="x", status="completed")],
        success_criteria=["sent"],
        owners=["marketing"],
        evidence_required=[],
        initiative_id=uuid4(),
        initiative_phase="build",
        sibling_steps=[],
    )
    artifact = Artifact(
        kind="report",
        ref="vault://draft",
        summary="Newsletter draft",
        payload={"chars": 1200},
    )

    fake_client = MagicMock()
    table = MagicMock()
    upsert_response = MagicMock(data=[{"id": str(uuid4())}])
    table.upsert.return_value = table
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table

    async def fake_execute_async(q, op_name=None):
        return upsert_response

    monkeypatch.setattr(publication, "get_service_client", lambda: fake_client)
    monkeypatch.setattr(publication, "execute_async", fake_execute_async)
    monkeypatch.setattr(publication.workspace_event_bus, "publish", AsyncMock())
    monkeypatch.setattr(
        publication, "_vault_publish", AsyncMock(return_value=None)
    )
    fake_client.table = MagicMock(return_value=table)

    result = await publication.publish_artifact(
        user_id=user_id,
        agent_id="marketing",
        contract=contract,
        artifact=artifact,
        audit=None,
    )

    assert result.execution_id is not None
    fake_client.table.assert_any_call("agent_task_executions")
    # The upsert payload should embed our artifact in the list.
    call = table.upsert.call_args
    payload = call.args[0]
    assert payload["agent_id"] == "marketing"
    assert payload["user_id"] == str(user_id)
    assert payload["contract_id"] == str(contract.id)
    assert payload["mode"] == "initiative"
    assert any(a["ref"] == "vault://draft" for a in payload["artifacts"])
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_publish_artifact_db_row.py -v
```

Expected: FAIL — `publish_artifact` not yet implemented.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/publication.py — append imports + helpers
from dataclasses import dataclass

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async


@dataclass
class PublicationResult:
    execution_id: UUID
    vault_document_id: UUID | None
    workspace_event_emitted: bool


async def _vault_publish(
    *,
    user_id: UUID,
    agent_id: str,
    contract: TaskContract | DirectRequest,
    artifact: Artifact,
) -> UUID | None:
    """Send vault-bound artifacts to ``knowledge_service``. Defined in Task 85."""
    return None


def _contract_meta(contract: TaskContract | DirectRequest) -> dict:
    if isinstance(contract, TaskContract):
        return {
            "mode": "initiative",
            "contract_id": str(contract.id),
            "contract_source": contract.source,
            "initiative_id": str(contract.initiative_id)
            if contract.initiative_id
            else None,
            "goal": contract.goal,
            "todo_snapshot": [t.model_dump() for t in contract.todo_items],
        }
    return {
        "mode": "direct",
        "contract_id": None,
        "contract_source": "direct_request",
        "initiative_id": None,
        "goal": getattr(contract, "text", None),
        "todo_snapshot": None,
    }


async def publish_artifact(
    *,
    user_id: UUID,
    agent_id: str,
    contract: TaskContract | DirectRequest,
    artifact: Artifact,
    audit: AuditReport | None,
) -> PublicationResult:
    """Publish an artifact to all four sinks (spec §12)."""
    client = get_service_client()
    meta = _contract_meta(contract)

    # --- Sink 1: agent_task_executions upsert ---------------------------------
    existing_artifacts: list[dict] = []
    if meta["contract_id"]:
        prior_res = await execute_async(
            client.table("agent_task_executions")
            .select("id, artifacts")
            .eq("contract_id", meta["contract_id"])
            .eq("user_id", str(user_id))
            .limit(1),
            op_name="agent_task_executions.select",
        )
        if prior_res.data:
            existing_artifacts = list(prior_res.data[0].get("artifacts") or [])
    payload_artifacts = existing_artifacts + [artifact.model_dump()]

    row = {
        "user_id": str(user_id),
        "agent_id": agent_id,
        "mode": meta["mode"],
        "contract_id": meta["contract_id"],
        "contract_source": meta["contract_source"],
        "initiative_id": meta["initiative_id"],
        "goal": meta["goal"],
        "todo_snapshot": meta["todo_snapshot"],
        "status": "submitted" if audit and audit.overall_status == "pass" else "running",
        "artifacts": payload_artifacts,
        "audit_report_id": str(audit.id) if audit and getattr(audit, "id", None) else None,
    }
    response = await execute_async(
        client.table("agent_task_executions").upsert(
            row, on_conflict="contract_id"
        ),
        op_name="agent_task_executions.upsert",
    )
    execution_id = UUID(response.data[0]["id"]) if response.data else UUID(int=0)

    # --- Sink 2: vault ---------------------------------------------------------
    vault_doc_id = None
    if artifact.kind in VAULT_BOUND_KINDS:
        vault_doc_id = await _vault_publish(
            user_id=user_id,
            agent_id=agent_id,
            contract=contract,
            artifact=artifact,
        )

    # --- Sink 3: workspace SSE -------------------------------------------------
    event = WorkspaceArtifactEvent(
        agent_id=agent_id,
        contract_id=UUID(meta["contract_id"]) if meta["contract_id"] else None,
        artifact_kind=artifact.kind,
        ref=artifact.ref,
        summary=artifact.summary,
        preview_url=getattr(artifact, "preview_url", None),
    )
    await workspace_event_bus.publish(user_id, event)

    # --- Sink 4: reports UI ----------------------------------------------------
    # Reports UI reads agent_task_executions joined to vault docs — no extra
    # write needed; the upsert above is sufficient.

    return PublicationResult(
        execution_id=execution_id,
        vault_document_id=vault_doc_id,
        workspace_event_emitted=True,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_publish_artifact_db_row.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/publication.py tests/unit/runtime/test_publish_artifact_db_row.py
git commit -m "feat(runtime): publish_artifact upserts agent_task_executions"
```

---

### Task 85: `_vault_publish` calls `knowledge_service.process_document` for vault-bound kinds

**Files:**
- Edit: `app/agents/runtime/publication.py`
- Edit: `app/services/knowledge_service.py` (add `add_document` thin wrapper)
- Test: `tests/unit/runtime/test_publish_artifact_vault.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_publish_artifact_vault.py
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import publication
from app.agents.runtime.types import (
    Artifact,
    TaskContract,
    TodoItem,
)


@pytest.mark.asyncio
async def test_vault_publish_invoked_for_report(monkeypatch):
    user_id = uuid4()
    contract = TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="g",
        todo_items=[TodoItem(id=uuid4(), title="x", status="completed")],
        success_criteria=[],
        owners=["data"],
        evidence_required=[],
        initiative_id=uuid4(),
        initiative_phase="build",
        sibling_steps=[],
    )
    artifact = Artifact(
        kind="report",
        ref="vault://draft",
        summary="Quarterly review",
        payload={"markdown": "# Quarterly review\n\nbody"},
    )

    fake_client = MagicMock()
    table = MagicMock()
    table.upsert.return_value = table
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table

    async def fake_execute_async(q, op_name=None):
        return MagicMock(data=[{"id": str(uuid4()), "artifacts": []}])

    monkeypatch.setattr(publication, "get_service_client", lambda: fake_client)
    monkeypatch.setattr(publication, "execute_async", fake_execute_async)
    monkeypatch.setattr(publication.workspace_event_bus, "publish", AsyncMock())
    fake_client.table = MagicMock(return_value=table)

    add_document = AsyncMock(return_value=uuid4())
    monkeypatch.setattr(publication.knowledge_service, "add_document", add_document)

    result = await publication.publish_artifact(
        user_id=user_id,
        agent_id="data",
        contract=contract,
        artifact=artifact,
        audit=None,
    )

    add_document.assert_awaited_once()
    kwargs = add_document.await_args.kwargs
    assert kwargs["agent_id"] == "data"
    assert kwargs["kind"] == "agent_report"
    assert result.vault_document_id is not None


@pytest.mark.asyncio
async def test_vault_publish_skipped_for_progress_kind(monkeypatch):
    user_id = uuid4()
    contract = TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="g",
        todo_items=[],
        success_criteria=[],
        owners=["data"],
        evidence_required=[],
        initiative_id=uuid4(),
        initiative_phase="build",
        sibling_steps=[],
    )
    artifact = Artifact(
        kind="status_update",
        ref="-",
        summary="step done",
        payload={},
    )

    fake_client = MagicMock()
    table = MagicMock()
    table.upsert.return_value = table
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table

    async def fake_execute_async(q, op_name=None):
        return MagicMock(data=[{"id": str(uuid4()), "artifacts": []}])

    monkeypatch.setattr(publication, "get_service_client", lambda: fake_client)
    monkeypatch.setattr(publication, "execute_async", fake_execute_async)
    monkeypatch.setattr(publication.workspace_event_bus, "publish", AsyncMock())
    fake_client.table = MagicMock(return_value=table)

    add_document = AsyncMock()
    monkeypatch.setattr(publication.knowledge_service, "add_document", add_document)

    result = await publication.publish_artifact(
        user_id=user_id,
        agent_id="data",
        contract=contract,
        artifact=artifact,
        audit=None,
    )

    add_document.assert_not_awaited()
    assert result.vault_document_id is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_publish_artifact_vault.py -v
```

Expected: FAIL — `publication._vault_publish` is a stub that returns None; `knowledge_service.add_document` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
# app/services/knowledge_service.py — append at end
async def add_document(
    *,
    user_id: UUID,
    agent_id: str,
    kind: str,
    title: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> UUID:
    """Persist a generated agent artifact to the knowledge vault.

    Thin wrapper around the existing ingestion pipeline that stamps the
    canonical metadata fields expected by Layer-3 retrieval (spec §11).
    """
    from uuid import UUID, uuid4

    client = get_service_client()
    entry_id = uuid4()
    meta = {
        **(metadata or {}),
        "scope": "user",
        "kind": kind,
        "agent_id": agent_id,
        "user_id": str(user_id),
    }
    embedding_ids = await ingest_document(
        client,
        content,
        source_type=kind,
        source_id=str(entry_id),
        metadata=meta,
        agent_id=agent_id,
        user_id=str(user_id),
    )
    await execute_async(
        client.table("admin_knowledge_entries").insert({
            "id": str(entry_id),
            "filename": title,
            "file_type": "agent_artifact",
            "mime_type": "text/markdown",
            "file_path": f"agent_reports/{entry_id}.md",
            "agent_scope": agent_id,
            "uploaded_by": str(user_id),
            "status": "completed",
            "chunk_count": len(embedding_ids),
            "embedding_ids": embedding_ids,
            "file_size_bytes": len(content.encode("utf-8")),
        })
    )
    return entry_id
```

```python
# app/agents/runtime/publication.py — replace the _vault_publish stub
from app.services import knowledge_service


async def _vault_publish(
    *,
    user_id: UUID,
    agent_id: str,
    contract: TaskContract | DirectRequest,
    artifact: Artifact,
) -> UUID | None:
    """Write the artifact to the knowledge vault."""
    try:
        content = (
            artifact.payload.get("markdown")
            if isinstance(artifact.payload, dict)
            else None
        ) or artifact.summary
        title = (
            f"{agent_id} — {contract.goal}"
            if isinstance(contract, TaskContract)
            else f"{agent_id} — {artifact.kind}"
        )
        return await knowledge_service.add_document(
            user_id=user_id,
            agent_id=agent_id,
            kind="agent_report",
            title=title,
            content=content,
            metadata={
                "artifact_kind": artifact.kind,
                "ref": artifact.ref,
                "summary": artifact.summary,
                "contract_id": str(contract.id)
                if isinstance(contract, TaskContract)
                else None,
                "initiative_id": str(contract.initiative_id)
                if isinstance(contract, TaskContract) and contract.initiative_id
                else None,
            },
        )
    except Exception:  # noqa: BLE001
        logger.exception("vault publish failed for %s/%s", agent_id, artifact.kind)
        return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_publish_artifact_vault.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/publication.py app/services/knowledge_service.py tests/unit/runtime/test_publish_artifact_vault.py
git commit -m "feat(runtime): vault-bound artifacts flow to knowledge_service.add_document"
```

---

### Task 86: `publish_artifact` always emits a `WorkspaceArtifactEvent`

**Files:**
- Test: `tests/unit/runtime/test_publish_artifact_workspace_event.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_publish_artifact_workspace_event.py
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import publication
from app.agents.runtime.types import (
    Artifact,
    TaskContract,
    TodoItem,
    WorkspaceArtifactEvent,
)


@pytest.mark.asyncio
async def test_workspace_event_emitted_for_video_render(monkeypatch):
    user_id = uuid4()
    contract = TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="Hero spot",
        todo_items=[TodoItem(id=uuid4(), title="x", status="completed")],
        success_criteria=[],
        owners=["content_creation"],
        evidence_required=[],
        initiative_id=uuid4(),
        initiative_phase="build",
        sibling_steps=[],
    )
    artifact = Artifact(
        kind="video_render",
        ref="storage://videos/hero.mp4",
        summary="Final render",
        payload={"duration_s": 60, "preview_url": "https://cdn/x.jpg"},
    )

    fake_client = MagicMock()
    table = MagicMock()
    table.upsert.return_value = table
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table

    async def fake_execute_async(q, op_name=None):
        return MagicMock(data=[{"id": str(uuid4()), "artifacts": []}])

    publish = AsyncMock()
    monkeypatch.setattr(publication, "get_service_client", lambda: fake_client)
    monkeypatch.setattr(publication, "execute_async", fake_execute_async)
    monkeypatch.setattr(publication.workspace_event_bus, "publish", publish)
    monkeypatch.setattr(publication, "_vault_publish", AsyncMock(return_value=None))
    fake_client.table = MagicMock(return_value=table)

    await publication.publish_artifact(
        user_id=user_id,
        agent_id="content_creation",
        contract=contract,
        artifact=artifact,
        audit=None,
    )

    publish.assert_awaited_once()
    args, _ = publish.await_args
    assert args[0] == user_id
    event = args[1]
    assert isinstance(event, WorkspaceArtifactEvent)
    assert event.artifact_kind == "video_render"
    assert event.ref == "storage://videos/hero.mp4"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_publish_artifact_workspace_event.py -v
```

Expected: PASS already if Task 84 is wired correctly. If FAIL, the workspace event emission path is wrong.

- [ ] **Step 3: Write minimal implementation**

No code change expected; if failing, ensure `publish_artifact` builds the `WorkspaceArtifactEvent` after the DB write.

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_publish_artifact_workspace_event.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/runtime/test_publish_artifact_workspace_event.py
git commit -m "test(runtime): publish_artifact emits WorkspaceArtifactEvent for video_render"
```

---

### Task 87: `contract_from_initiative_step` reads checklist row and hydrates sibling steps

**Files:**
- Create: `app/agents/runtime/step_runtime.py`
- Test: `tests/unit/runtime/test_contract_from_initiative_step.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_contract_from_initiative_step.py
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import step_runtime


@pytest.mark.asyncio
async def test_contract_from_initiative_step_loads_siblings(monkeypatch):
    initiative_id = uuid4()
    item_id = uuid4()
    sibling_id = uuid4()
    item_row = {
        "id": str(item_id),
        "initiative_id": str(initiative_id),
        "phase": "validation",
        "title": "Build forecast",
        "goal": "Forecast Q3 revenue",
        "metadata": {
            "todo_items": [
                {"id": str(uuid4()), "title": "Pull data", "status": "pending"},
            ],
            "success_criteria": ["+/- 5%"],
            "evidence_required": ["draft_artifact"],
        },
        "assigned_agent_id": "financial",
    }
    sibling_row = {
        "id": str(sibling_id),
        "initiative_id": str(initiative_id),
        "phase": "validation",
        "title": "Review forecast",
        "status": "pending",
    }

    fake_client = MagicMock()
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.neq.return_value = table

    responses = iter(
        [MagicMock(data=item_row), MagicMock(data=[sibling_row])]
    )

    async def fake_execute_async(q, op_name=None):
        return next(responses)

    monkeypatch.setattr(step_runtime, "get_service_client", lambda: fake_client)
    monkeypatch.setattr(step_runtime, "execute_async", fake_execute_async)
    fake_client.table = MagicMock(return_value=table)

    contract = await step_runtime.contract_from_initiative_step(item_id)

    assert contract.source == "initiative_step"
    assert contract.goal == "Forecast Q3 revenue"
    assert contract.initiative_id == initiative_id
    assert contract.initiative_phase == "validation"
    assert "financial" in contract.owners
    assert len(contract.todo_items) == 1
    assert any(s.id == sibling_id for s in contract.sibling_steps)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_contract_from_initiative_step.py -v
```

Expected: FAIL — `step_runtime` not created yet.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/step_runtime.py
"""Task execution runtime — adapters + the execute_task loop (spec §6).

Two contract adapters convert backing rows (initiative checklist items or
department tasks) into the canonical TaskContract that ``execute_task``
operates on.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    ResearchResult,
    StepSummary,
    TaskContract,
    TodoItem,
)
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    status: Literal["submitted", "retrying", "escalated", "failed"]
    artifacts: list[Artifact]
    audit: AuditReport
    execution_id: UUID


def _todo_items_from_metadata(meta: dict | None) -> list[TodoItem]:
    if not meta:
        return []
    raw = meta.get("todo_items") or []
    out: list[TodoItem] = []
    for r in raw:
        try:
            out.append(TodoItem.model_validate(r))
        except Exception:  # noqa: BLE001
            logger.warning("dropping malformed todo_item: %r", r)
    return out


async def contract_from_initiative_step(checklist_item_id: UUID) -> TaskContract:
    """Build a TaskContract from an ``initiative_checklist_items`` row."""
    client = get_service_client()
    item_res = await execute_async(
        client.table("initiative_checklist_items")
        .select("*")
        .eq("id", str(checklist_item_id))
        .single(),
        op_name="initiative_checklist_items.contract",
    )
    item = item_res.data
    if not item:
        raise ValueError(f"checklist item {checklist_item_id} not found")

    sibling_res = await execute_async(
        client.table("initiative_checklist_items")
        .select("id, title, status, phase, sort_order")
        .eq("initiative_id", item["initiative_id"])
        .eq("phase", item["phase"])
        .neq("id", str(checklist_item_id)),
        op_name="initiative_checklist_items.siblings",
    )
    siblings = [
        StepSummary(
            id=UUID(s["id"]),
            title=s["title"],
            status=s.get("status", "pending"),
            phase=s.get("phase"),
        )
        for s in (sibling_res.data or [])
    ]

    metadata = item.get("metadata") or {}
    owners: list[str] = []
    if item.get("assigned_agent_id"):
        owners.append(item["assigned_agent_id"])
    return TaskContract(
        id=UUID(item["id"]),
        source="initiative_step",
        goal=item.get("goal") or item.get("title") or "",
        todo_items=_todo_items_from_metadata(metadata),
        success_criteria=metadata.get("success_criteria") or [],
        owners=owners,
        evidence_required=metadata.get("evidence_required") or [],
        initiative_id=UUID(item["initiative_id"]),
        initiative_phase=item.get("phase"),
        sibling_steps=siblings,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_contract_from_initiative_step.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/step_runtime.py tests/unit/runtime/test_contract_from_initiative_step.py
git commit -m "feat(runtime): contract_from_initiative_step adapter"
```

---

### Task 88: `contract_from_department_task` reads task + todo items

**Files:**
- Edit: `app/agents/runtime/step_runtime.py`
- Test: `tests/unit/runtime/test_contract_from_department_task.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_contract_from_department_task.py
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import step_runtime


@pytest.mark.asyncio
async def test_contract_from_department_task(monkeypatch):
    task_id = uuid4()
    todo_id = uuid4()
    task_row = {
        "id": str(task_id),
        "goal": "Reply to Acme RFP",
        "assigned_agent_id": "sales",
        "metadata": {
            "success_criteria": ["Customer accepts pricing"],
            "evidence_required": ["draft_artifact"],
        },
    }
    todo_rows = [
        {
            "id": str(todo_id),
            "task_id": str(task_id),
            "title": "Draft pricing summary",
            "status": "pending",
            "sort_order": 0,
        }
    ]

    fake_client = MagicMock()
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.order.return_value = table

    responses = iter(
        [MagicMock(data=task_row), MagicMock(data=todo_rows)]
    )

    async def fake_execute_async(q, op_name=None):
        return next(responses)

    monkeypatch.setattr(step_runtime, "get_service_client", lambda: fake_client)
    monkeypatch.setattr(step_runtime, "execute_async", fake_execute_async)
    fake_client.table = MagicMock(return_value=table)

    contract = await step_runtime.contract_from_department_task(task_id)

    assert contract.source == "department_task"
    assert contract.goal == "Reply to Acme RFP"
    assert contract.initiative_id is None
    assert contract.owners == ["sales"]
    assert len(contract.todo_items) == 1
    assert contract.todo_items[0].title == "Draft pricing summary"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_contract_from_department_task.py -v
```

Expected: FAIL — adapter not implemented.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/step_runtime.py — append
async def contract_from_department_task(task_id: UUID) -> TaskContract:
    """Build a TaskContract from a ``department_tasks`` row + its todo items."""
    client = get_service_client()
    task_res = await execute_async(
        client.table("department_tasks")
        .select("*")
        .eq("id", str(task_id))
        .single(),
        op_name="department_tasks.contract",
    )
    task = task_res.data
    if not task:
        raise ValueError(f"department task {task_id} not found")

    todos_res = await execute_async(
        client.table("department_task_todo_items")
        .select("*")
        .eq("task_id", str(task_id))
        .order("sort_order"),
        op_name="department_task_todo_items.list",
    )
    todos = [
        TodoItem(
            id=UUID(r["id"]),
            title=r["title"],
            status=r.get("status", "pending"),
            description=r.get("description"),
        )
        for r in (todos_res.data or [])
    ]

    metadata = task.get("metadata") or {}
    owners: list[str] = []
    if task.get("assigned_agent_id"):
        owners.append(task["assigned_agent_id"])

    return TaskContract(
        id=UUID(task["id"]),
        source="department_task",
        goal=task.get("goal") or task.get("title") or "",
        todo_items=todos,
        success_criteria=metadata.get("success_criteria") or [],
        owners=owners,
        evidence_required=metadata.get("evidence_required") or [],
        initiative_id=None,
        initiative_phase=None,
        sibling_steps=[],
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_contract_from_department_task.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/step_runtime.py tests/unit/runtime/test_contract_from_department_task.py
git commit -m "feat(runtime): contract_from_department_task adapter"
```

---

### Task 89: `_execute_todo_items` flips status `pending → in_progress → completed` per item

**Files:**
- Edit: `app/agents/runtime/step_runtime.py`
- Test: `tests/unit/runtime/test_execute_todo_items.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_execute_todo_items.py
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import step_runtime
from app.agents.runtime.types import (
    Artifact,
    ResearchResult,
    TaskContract,
    TodoItem,
)


@pytest.mark.asyncio
async def test_execute_todo_items_walks_each_item(monkeypatch):
    contract = TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="g",
        todo_items=[
            TodoItem(id=uuid4(), title="Step A", status="pending"),
            TodoItem(id=uuid4(), title="Step B", status="pending"),
        ],
        success_criteria=[],
        owners=["financial"],
        evidence_required=[],
        initiative_id=uuid4(),
        initiative_phase="validation",
        sibling_steps=[],
    )
    research = ResearchResult(
        summary="x",
        sources=[],
        contradictions=[],
        coverage_assessment="complete",
        missing_information=[],
    )

    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "financial"
    agent.run_step = AsyncMock(
        side_effect=[
            Artifact(kind="doc", ref="a", summary="A done", payload={}),
            Artifact(kind="doc", ref="b", summary="B done", payload={}),
        ]
    )

    update_status = AsyncMock()
    emit = AsyncMock()
    monkeypatch.setattr(step_runtime, "_update_todo_status", update_status)
    monkeypatch.setattr(step_runtime.publication, "emit_progress_event", emit)

    artifacts = await step_runtime._execute_todo_items(agent, contract, research)

    assert len(artifacts) == 2
    # Each todo: in_progress then completed.
    states = [c.kwargs["status"] for c in update_status.await_args_list]
    assert states == ["in_progress", "completed", "in_progress", "completed"]
    # And the workspace heard about both starts.
    progress_statuses = [c.kwargs["status"] for c in emit.await_args_list]
    assert "started" in progress_statuses
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_execute_todo_items.py -v
```

Expected: FAIL — `_execute_todo_items` / `_update_todo_status` not yet implemented.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/step_runtime.py — add at top
from app.agents.runtime import publication


async def _update_todo_status(
    *, contract: TaskContract, item_id: UUID, status: str
) -> None:
    """Write the per-todo status back to the source table."""
    client = get_service_client()
    if contract.source == "initiative_step":
        # Stored inside the parent checklist item's metadata.todo_items array.
        cur = await execute_async(
            client.table("initiative_checklist_items")
            .select("metadata")
            .eq("id", str(contract.id))
            .single(),
            op_name="initiative_checklist_items.todo.read",
        )
        meta = (cur.data or {}).get("metadata") or {}
        items = list(meta.get("todo_items") or [])
        for it in items:
            if str(it.get("id")) == str(item_id):
                it["status"] = status
                break
        meta["todo_items"] = items
        await execute_async(
            client.table("initiative_checklist_items")
            .update({"metadata": meta})
            .eq("id", str(contract.id)),
            op_name="initiative_checklist_items.todo.update",
        )
    elif contract.source == "department_task":
        await execute_async(
            client.table("department_task_todo_items")
            .update({"status": status})
            .eq("id", str(item_id)),
            op_name="department_task_todo_items.update",
        )


async def _execute_todo_items(
    agent,
    contract: TaskContract,
    research: ResearchResult,
) -> list[Artifact]:
    """Iterate todo items one at a time, updating status as the agent works."""
    artifacts: list[Artifact] = []
    for item in contract.todo_items:
        await _update_todo_status(
            contract=contract, item_id=item.id, status="in_progress"
        )
        await publication.emit_progress_event(
            user_id=agent.user_id,
            agent_id=agent.agent_id,
            contract_id=contract.id,
            item=item.title,
            status="started",
        )
        try:
            artifact = await agent.run_step(item=item, research=research)
        except Exception as exc:  # noqa: BLE001
            logger.exception("todo %s failed: %s", item.id, exc)
            await _update_todo_status(
                contract=contract, item_id=item.id, status="blocked"
            )
            await publication.emit_progress_event(
                user_id=agent.user_id,
                agent_id=agent.agent_id,
                contract_id=contract.id,
                item=item.title,
                status="blocked",
            )
            continue
        if artifact is not None:
            artifacts.append(artifact)
        await _update_todo_status(
            contract=contract, item_id=item.id, status="completed"
        )
    return artifacts
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_execute_todo_items.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/step_runtime.py tests/unit/runtime/test_execute_todo_items.py
git commit -m "feat(runtime): _execute_todo_items walks items with status updates"
```

---

### Task 90: `_submit` publishes every artifact and the rendered report

**Files:**
- Edit: `app/agents/runtime/step_runtime.py`
- Test: `tests/unit/runtime/test_submit_flow.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_submit_flow.py
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import step_runtime
from app.agents.runtime.publication import PublicationResult
from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    ResearchResult,
    TaskContract,
    TodoItem,
)


@pytest.mark.asyncio
async def test_submit_publishes_artifacts_then_report(monkeypatch):
    contract = TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="g",
        todo_items=[TodoItem(id=uuid4(), title="x", status="completed")],
        success_criteria=[],
        owners=["data"],
        evidence_required=[],
        initiative_id=uuid4(),
        initiative_phase="build",
        sibling_steps=[],
    )
    research = ResearchResult(
        summary="x",
        sources=[],
        contradictions=[],
        coverage_assessment="complete",
        missing_information=[],
    )
    audit = AuditReport(
        overall_status="pass",
        per_item=[],
        per_criterion=[],
        gaps=[],
        policy_violations=[],
        recoverable=True,
        next_action="submit",
    )
    artifacts = [
        Artifact(kind="doc", ref="r1", summary="draft", payload={}),
    ]
    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "data"

    publish = AsyncMock(
        return_value=PublicationResult(
            execution_id=uuid4(),
            vault_document_id=uuid4(),
            workspace_event_emitted=True,
        )
    )
    monkeypatch.setattr(step_runtime.publication, "publish_artifact", publish)
    monkeypatch.setattr(
        step_runtime.publication,
        "render_report_markdown",
        AsyncMock(return_value="# report\n"),
    )

    result = await step_runtime._submit(agent, contract, artifacts, research, audit)

    assert result.status == "submitted"
    assert publish.await_count == 2  # one for artifact + one for the report
    second_call = publish.await_args_list[1]
    assert second_call.kwargs["artifact"].kind == "report"
    assert "# report" in second_call.kwargs["artifact"].payload["markdown"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_submit_flow.py -v
```

Expected: FAIL — `_submit` not yet implemented.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/step_runtime.py — append
async def _submit(
    agent,
    contract: TaskContract,
    artifacts: list[Artifact],
    research: ResearchResult,
    audit: AuditReport,
) -> TaskResult:
    """Publish each artifact + the structured Layer-2 report."""
    last_publication = None
    for art in artifacts:
        last_publication = await publication.publish_artifact(
            user_id=agent.user_id,
            agent_id=agent.agent_id,
            contract=contract,
            artifact=art,
            audit=audit,
        )

    report_md = await publication.render_report_markdown(
        contract=contract,
        research=research,
        audit=audit,
        artifacts=artifacts,
        agent_id=agent.agent_id,
    )
    report_artifact = Artifact(
        kind="report",
        ref=f"agent_report://{contract.id}",
        summary=f"Submission report — {contract.goal}",
        payload={"markdown": report_md},
    )
    last_publication = await publication.publish_artifact(
        user_id=agent.user_id,
        agent_id=agent.agent_id,
        contract=contract,
        artifact=report_artifact,
        audit=audit,
    )

    execution_id = last_publication.execution_id if last_publication else UUID(int=0)
    return TaskResult(
        status="submitted",
        artifacts=[*artifacts, report_artifact],
        audit=audit,
        execution_id=execution_id,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_submit_flow.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/step_runtime.py tests/unit/runtime/test_submit_flow.py
git commit -m "feat(runtime): _submit publishes artifacts then Layer-2 report"
```

---

### Task 91: `_retry_failed_items` only re-runs todos flagged in the audit

**Files:**
- Edit: `app/agents/runtime/step_runtime.py`
- Test: `tests/unit/runtime/test_retry_failed_items.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_retry_failed_items.py
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import step_runtime
from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    ItemAudit,
    TaskContract,
    TodoItem,
)


@pytest.mark.asyncio
async def test_retry_only_failed_items(monkeypatch):
    good = TodoItem(id=uuid4(), title="Step A", status="completed")
    bad = TodoItem(id=uuid4(), title="Step B", status="completed")
    contract = TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="g",
        todo_items=[good, bad],
        success_criteria=[],
        owners=["data"],
        evidence_required=[],
        initiative_id=uuid4(),
        initiative_phase="build",
        sibling_steps=[],
    )
    audit = AuditReport(
        overall_status="partial",
        per_item=[
            ItemAudit(item_id=good.id, status="pass", evidence_pointers=[], gaps=[]),
            ItemAudit(
                item_id=bad.id,
                status="fail",
                evidence_pointers=[],
                gaps=["missing chart"],
            ),
        ],
        per_criterion=[],
        gaps=["chart missing"],
        policy_violations=[],
        recoverable=True,
        next_action="retry",
    )

    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "data"
    agent.run_step = AsyncMock(
        return_value=Artifact(kind="doc", ref="b2", summary="retry", payload={})
    )

    monkeypatch.setattr(step_runtime, "_update_todo_status", AsyncMock())
    monkeypatch.setattr(step_runtime.publication, "emit_progress_event", AsyncMock())
    monkeypatch.setattr(
        step_runtime,
        "_self_audit",
        AsyncMock(
            return_value=AuditReport(
                overall_status="pass",
                per_item=[],
                per_criterion=[],
                gaps=[],
                policy_violations=[],
                recoverable=True,
                next_action="submit",
            )
        ),
    )
    monkeypatch.setattr(
        step_runtime,
        "_submit",
        AsyncMock(
            return_value=step_runtime.TaskResult(
                status="submitted",
                artifacts=[],
                audit=AuditReport(
                    overall_status="pass",
                    per_item=[],
                    per_criterion=[],
                    gaps=[],
                    policy_violations=[],
                    recoverable=True,
                    next_action="submit",
                ),
                execution_id=uuid4(),
            )
        ),
    )

    result = await step_runtime._retry_failed_items(agent, contract, audit)

    assert result.status == "submitted"
    # Only one run_step call — the one failed item.
    assert agent.run_step.await_count == 1
    assert agent.run_step.await_args.kwargs["item"].id == bad.id
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_retry_failed_items.py -v
```

Expected: FAIL — `_retry_failed_items` / `_self_audit` not yet wired.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/step_runtime.py — append

async def _self_audit(
    agent, contract: TaskContract, artifacts: list[Artifact]
) -> AuditReport:
    """Defer to the audit module if installed; otherwise pass-through.

    Section B owns the audit module; this stub keeps step_runtime testable
    in isolation. The real wiring lives behind ``agent.audit(...)``.
    """
    if hasattr(agent, "audit"):
        return await agent.audit(contract=contract, artifacts=artifacts)
    return AuditReport(
        overall_status="pass",
        per_item=[],
        per_criterion=[],
        gaps=[],
        policy_violations=[],
        recoverable=True,
        next_action="submit",
    )


async def _retry_failed_items(
    agent, contract: TaskContract, audit: AuditReport
) -> TaskResult:
    """Re-run only the todos the audit marked failed; then re-submit."""
    failed_ids = {a.item_id for a in audit.per_item if a.status != "pass"}
    failed_items = [t for t in contract.todo_items if t.id in failed_ids]
    if not failed_items:
        return await _escalate(agent, contract, audit)

    new_artifacts: list[Artifact] = []
    for item in failed_items:
        await _update_todo_status(
            contract=contract, item_id=item.id, status="in_progress"
        )
        await publication.emit_progress_event(
            user_id=agent.user_id,
            agent_id=agent.agent_id,
            contract_id=contract.id,
            item=item.title,
            status="started",
        )
        try:
            art = await agent.run_step(item=item, research=None)
        except Exception:  # noqa: BLE001
            logger.exception("retry of %s failed", item.id)
            await _update_todo_status(
                contract=contract, item_id=item.id, status="blocked"
            )
            continue
        if art:
            new_artifacts.append(art)
        await _update_todo_status(
            contract=contract, item_id=item.id, status="completed"
        )

    new_audit = await _self_audit(agent, contract, new_artifacts)
    if new_audit.overall_status != "pass":
        return await _escalate(agent, contract, new_audit)
    # Empty research is fine on retry — the report renderer tolerates it.
    return await _submit(
        agent,
        contract,
        new_artifacts,
        ResearchResult(
            summary="",
            sources=[],
            contradictions=[],
            coverage_assessment="complete",
            missing_information=[],
        ),
        new_audit,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_retry_failed_items.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/step_runtime.py tests/unit/runtime/test_retry_failed_items.py
git commit -m "feat(runtime): _retry_failed_items re-runs only failed todos"
```

---

### Task 92: `_escalate` records `status='escalated'` and emits blocked workspace event

**Files:**
- Edit: `app/agents/runtime/step_runtime.py`
- Test: `tests/unit/runtime/test_escalate.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_escalate.py
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import step_runtime
from app.agents.runtime.publication import PublicationResult
from app.agents.runtime.types import AuditReport, TaskContract, TodoItem


@pytest.mark.asyncio
async def test_escalate_emits_blocked_and_persists(monkeypatch):
    contract = TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="g",
        todo_items=[TodoItem(id=uuid4(), title="x", status="completed")],
        success_criteria=[],
        owners=["data"],
        evidence_required=[],
        initiative_id=uuid4(),
        initiative_phase="build",
        sibling_steps=[],
    )
    audit = AuditReport(
        overall_status="fail",
        per_item=[],
        per_criterion=[],
        gaps=["unrecoverable: source unavailable"],
        policy_violations=[],
        recoverable=False,
        next_action="escalate",
    )
    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "data"

    emit = AsyncMock()
    monkeypatch.setattr(step_runtime.publication, "emit_progress_event", emit)
    publish = AsyncMock(
        return_value=PublicationResult(
            execution_id=uuid4(),
            vault_document_id=None,
            workspace_event_emitted=True,
        )
    )
    monkeypatch.setattr(step_runtime.publication, "publish_artifact", publish)
    monkeypatch.setattr(
        step_runtime.publication,
        "render_report_markdown",
        AsyncMock(return_value="# escalation\n"),
    )

    result = await step_runtime._escalate(agent, contract, audit)

    assert result.status == "escalated"
    # Blocked event for each pending/failed todo.
    statuses = [c.kwargs["status"] for c in emit.await_args_list]
    assert "blocked" in statuses
    # The escalation also writes a report artifact for visibility.
    assert publish.await_count == 1
    assert publish.await_args.kwargs["artifact"].kind == "report"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_escalate.py -v
```

Expected: FAIL — `_escalate` not implemented.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/step_runtime.py — append
async def _escalate(
    agent, contract: TaskContract, audit: AuditReport
) -> TaskResult:
    """Surface an unrecoverable failure to the workspace + reports UI."""
    for item in contract.todo_items:
        await publication.emit_progress_event(
            user_id=agent.user_id,
            agent_id=agent.agent_id,
            contract_id=contract.id,
            item=item.title,
            status="blocked",
        )
    report_md = await publication.render_report_markdown(
        contract=contract,
        research=ResearchResult(
            summary="(escalation — see audit gaps)",
            sources=[],
            contradictions=[],
            coverage_assessment="partial",
            missing_information=audit.gaps,
        ),
        audit=audit,
        artifacts=[],
        agent_id=agent.agent_id,
    )
    report_artifact = Artifact(
        kind="report",
        ref=f"agent_escalation://{contract.id}",
        summary=f"Escalation — {contract.goal}",
        payload={"markdown": report_md},
    )
    publication_result = await publication.publish_artifact(
        user_id=agent.user_id,
        agent_id=agent.agent_id,
        contract=contract,
        artifact=report_artifact,
        audit=audit,
    )
    return TaskResult(
        status="escalated",
        artifacts=[report_artifact],
        audit=audit,
        execution_id=publication_result.execution_id,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_escalate.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/step_runtime.py tests/unit/runtime/test_escalate.py
git commit -m "feat(runtime): _escalate emits blocked + publishes escalation report"
```

---

### Task 93: `execute_task` orchestrates research → todos → audit → submit

**Files:**
- Edit: `app/agents/runtime/step_runtime.py`
- Test: `tests/unit/runtime/test_execute_task_happy_path.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_execute_task_happy_path.py
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import step_runtime
from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    ResearchResult,
    TaskContract,
    TodoItem,
)


@pytest.mark.asyncio
async def test_execute_task_submitted_path(monkeypatch):
    contract = TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="g",
        todo_items=[TodoItem(id=uuid4(), title="x", status="pending")],
        success_criteria=[],
        owners=["data"],
        evidence_required=[],
        initiative_id=uuid4(),
        initiative_phase="build",
        sibling_steps=[],
    )

    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "data"
    agent.research = AsyncMock(
        return_value=ResearchResult(
            summary="s",
            sources=[],
            contradictions=[],
            coverage_assessment="complete",
            missing_information=[],
        )
    )
    agent.audit = AsyncMock(
        return_value=AuditReport(
            overall_status="pass",
            per_item=[],
            per_criterion=[],
            gaps=[],
            policy_violations=[],
            recoverable=True,
            next_action="submit",
        )
    )

    monkeypatch.setattr(
        step_runtime,
        "_execute_todo_items",
        AsyncMock(
            return_value=[Artifact(kind="doc", ref="r", summary="s", payload={})]
        ),
    )
    submit_mock = AsyncMock(
        return_value=step_runtime.TaskResult(
            status="submitted",
            artifacts=[],
            audit=AuditReport(
                overall_status="pass",
                per_item=[],
                per_criterion=[],
                gaps=[],
                policy_violations=[],
                recoverable=True,
                next_action="submit",
            ),
            execution_id=uuid4(),
        )
    )
    monkeypatch.setattr(step_runtime, "_submit", submit_mock)

    result = await step_runtime.execute_task(agent, contract)

    assert result.status == "submitted"
    submit_mock.assert_awaited_once()
    agent.research.assert_awaited_once_with(contract=contract)
    agent.audit.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_task_routes_to_retry_when_recoverable(monkeypatch):
    contract = TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="g",
        todo_items=[TodoItem(id=uuid4(), title="x", status="pending")],
        success_criteria=[],
        owners=["data"],
        evidence_required=[],
        initiative_id=uuid4(),
        initiative_phase="build",
        sibling_steps=[],
    )
    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "data"
    agent.research = AsyncMock(
        return_value=ResearchResult(
            summary="",
            sources=[],
            contradictions=[],
            coverage_assessment="complete",
            missing_information=[],
        )
    )
    agent.audit = AsyncMock(
        return_value=AuditReport(
            overall_status="partial",
            per_item=[],
            per_criterion=[],
            gaps=["gap"],
            policy_violations=[],
            recoverable=True,
            next_action="retry",
        )
    )
    monkeypatch.setattr(
        step_runtime, "_execute_todo_items", AsyncMock(return_value=[])
    )
    retry_mock = AsyncMock(
        return_value=step_runtime.TaskResult(
            status="submitted",
            artifacts=[],
            audit=agent.audit.return_value,
            execution_id=uuid4(),
        )
    )
    monkeypatch.setattr(step_runtime, "_retry_failed_items", retry_mock)

    result = await step_runtime.execute_task(agent, contract)

    assert result.status == "submitted"
    retry_mock.assert_awaited_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_execute_task_happy_path.py -v
```

Expected: FAIL — `execute_task` not yet defined.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/step_runtime.py — append
async def execute_task(agent, contract: TaskContract) -> TaskResult:
    """The main loop from spec §6."""
    research = await agent.research(contract=contract)
    artifacts = await _execute_todo_items(agent, contract, research)
    audit = await agent.audit(contract=contract, artifacts=artifacts)
    if audit.overall_status == "pass":
        return await _submit(agent, contract, artifacts, research, audit)
    if audit.recoverable:
        return await _retry_failed_items(agent, contract, audit)
    return await _escalate(agent, contract, audit)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_execute_task_happy_path.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/step_runtime.py tests/unit/runtime/test_execute_task_happy_path.py
git commit -m "feat(runtime): execute_task loop wires research → todos → audit → submit"
```

---

### Task 94: `InitiativeContractError` raised when `start_initiative` missing required fields

**Files:**
- Create: `app/agents/runtime/initiative.py`
- Test: `tests/unit/runtime/test_start_initiative_validation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_start_initiative_validation.py
from unittest.mock import MagicMock

import pytest

from app.agents.runtime import initiative
from app.agents.runtime.types import InitiativeContractError


@pytest.mark.asyncio
async def test_start_initiative_requires_goal():
    agent = MagicMock()
    with pytest.raises(InitiativeContractError, match="goal"):
        await initiative.start_initiative(
            agent, goal="", success_criteria=["x"], owners=["financial"]
        )


@pytest.mark.asyncio
async def test_start_initiative_requires_success_criteria():
    agent = MagicMock()
    with pytest.raises(InitiativeContractError, match="success_criteria"):
        await initiative.start_initiative(
            agent, goal="ship it", success_criteria=[], owners=["financial"]
        )


@pytest.mark.asyncio
async def test_start_initiative_requires_owners():
    agent = MagicMock()
    with pytest.raises(InitiativeContractError, match="owners"):
        await initiative.start_initiative(
            agent, goal="ship it", success_criteria=["x"], owners=[]
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_start_initiative_validation.py -v
```

Expected: FAIL — `app.agents.runtime.initiative` not yet defined.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/initiative.py
"""Initiative rituals — start / advance / close (spec §14)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.agents.runtime import publication
from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    InitiativeContractError,
    TaskContract,
    TodoItem,
)
from app.services.initiative_service import (
    INITIATIVE_PHASES,
    InitiativeService,
)

logger = logging.getLogger(__name__)


@dataclass
class AdvanceResult:
    advanced: bool
    new_phase: str | None
    gaps: list[str]
    audit_report_id: UUID | None


@dataclass
class CloseReport:
    initiative_id: UUID
    outcomes: list[dict[str, Any]]
    artifacts: list[Artifact]
    learnings: list[str]
    follow_ups: list[str]
    vault_document_id: UUID


def _validate_start_inputs(
    goal: str, success_criteria: list[str], owners: list[str]
) -> None:
    missing = []
    if not goal or not goal.strip():
        missing.append("goal")
    if not success_criteria:
        missing.append("success_criteria")
    if not owners:
        missing.append("owners")
    if missing:
        raise InitiativeContractError(
            f"Cannot start initiative without: {', '.join(missing)}"
        )


async def start_initiative(
    agent,
    *,
    goal: str,
    success_criteria: list[str],
    owners: list[str],
    phase: str = "ideation",
    name: str | None = None,
):
    """Validate fields → create initiative → seed operational state → emit report."""
    _validate_start_inputs(goal, success_criteria, owners)
    # Full implementation in Task 95.
    raise NotImplementedError("start_initiative body lands in Task 95")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_start_initiative_validation.py -v
```

Expected: PASS (only validation paths exercised).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/initiative.py tests/unit/runtime/test_start_initiative_validation.py
git commit -m "feat(runtime): start_initiative input validation raises InitiativeContractError"
```

---

### Task 95: `start_initiative` creates initiative, seeds operational state, publishes start report

**Files:**
- Edit: `app/agents/runtime/initiative.py`
- Test: `tests/unit/runtime/test_start_initiative_creates.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_start_initiative_creates.py
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import initiative
from app.agents.runtime.publication import PublicationResult


@pytest.mark.asyncio
async def test_start_initiative_calls_service_and_seeds_op_state(monkeypatch):
    user_id = uuid4()
    agent = MagicMock()
    agent.user_id = user_id
    agent.agent_id = "executive"

    created = {"id": str(uuid4()), "title": "Forecast Q3", "phase": "ideation"}
    service = MagicMock()
    service.create_initiative = AsyncMock(return_value=created)
    service.update_operational_state = AsyncMock(return_value=created)
    monkeypatch.setattr(
        initiative, "InitiativeService", MagicMock(return_value=service)
    )
    publish = AsyncMock(
        return_value=PublicationResult(
            execution_id=uuid4(),
            vault_document_id=uuid4(),
            workspace_event_emitted=True,
        )
    )
    monkeypatch.setattr(initiative.publication, "publish_artifact", publish)

    result = await initiative.start_initiative(
        agent,
        goal="Forecast Q3 revenue",
        success_criteria=["+/-5%", "three scenarios"],
        owners=["financial", "data"],
    )

    assert result["id"] == created["id"]
    service.create_initiative.assert_awaited_once()
    service.update_operational_state.assert_awaited_once()
    kwargs = service.update_operational_state.await_args.kwargs
    assert kwargs["goal"] == "Forecast Q3 revenue"
    assert kwargs["success_criteria"] == ["+/-5%", "three scenarios"]
    assert kwargs["owner_agents"] == ["financial", "data"]
    publish.assert_awaited_once()
    assert publish.await_args.kwargs["artifact"].kind == "report"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_start_initiative_creates.py -v
```

Expected: FAIL — current body raises `NotImplementedError`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/initiative.py — replace the start_initiative body
async def start_initiative(
    agent,
    *,
    goal: str,
    success_criteria: list[str],
    owners: list[str],
    phase: str = "ideation",
    name: str | None = None,
):
    """Validate fields → create initiative → seed operational state → emit report."""
    _validate_start_inputs(goal, success_criteria, owners)
    if phase not in INITIATIVE_PHASES:
        raise InitiativeContractError(f"Invalid phase '{phase}'")

    service = InitiativeService()
    initiative_row = await service.create_initiative(
        title=name or goal,
        description=goal,
        user_id=str(agent.user_id),
        phase=phase,
        metadata={"goal": goal, "success_criteria": success_criteria},
    )

    await service.update_operational_state(
        initiative_row["id"],
        user_id=str(agent.user_id),
        goal=goal,
        success_criteria=list(success_criteria),
        owner_agents=list(owners),
        current_phase=phase,
    )

    pseudo_contract = TaskContract(
        id=UUID(initiative_row["id"]),
        source="initiative_step",
        goal=goal,
        todo_items=[],
        success_criteria=list(success_criteria),
        owners=list(owners),
        evidence_required=[],
        initiative_id=UUID(initiative_row["id"]),
        initiative_phase=phase,
        sibling_steps=[],
    )
    report_md = await publication.render_report_markdown(
        contract=pseudo_contract,
        research=publication.ResearchResult(
            summary=f"Initiative kicked off in {phase}.",
            sources=[],
            contradictions=[],
            coverage_assessment="complete",
            missing_information=[],
        )
        if False
        else __import__("app.agents.runtime.types", fromlist=["ResearchResult"]).ResearchResult(
            summary=f"Initiative kicked off in {phase}.",
            sources=[],
            contradictions=[],
            coverage_assessment="complete",
            missing_information=[],
        ),
        audit=AuditReport(
            overall_status="pass",
            per_item=[],
            per_criterion=[],
            gaps=[],
            policy_violations=[],
            recoverable=True,
            next_action="submit",
        ),
        artifacts=[],
        agent_id=agent.agent_id,
    )
    await publication.publish_artifact(
        user_id=agent.user_id,
        agent_id=agent.agent_id,
        contract=pseudo_contract,
        artifact=Artifact(
            kind="report",
            ref=f"initiative_start://{initiative_row['id']}",
            summary=f"Initiative started — {goal}",
            payload={"markdown": report_md},
        ),
        audit=None,
    )
    return initiative_row
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_start_initiative_creates.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/initiative.py tests/unit/runtime/test_start_initiative_creates.py
git commit -m "feat(runtime): start_initiative seeds operational state + publishes start report"
```

---

### Task 96: `advance_phase` blocks when checklist items for current phase remain unfinished

**Files:**
- Edit: `app/agents/runtime/initiative.py`
- Test: `tests/unit/runtime/test_advance_phase_blocks.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_advance_phase_blocks.py
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import initiative


@pytest.mark.asyncio
async def test_advance_phase_blocks_when_items_pending(monkeypatch):
    initiative_id = uuid4()
    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "executive"

    service = MagicMock()
    service.list_checklist_items = AsyncMock(
        return_value=[
            {"id": str(uuid4()), "status": "pending", "title": "Need draft"},
            {"id": str(uuid4()), "status": "completed", "title": "Done"},
        ]
    )
    service.advance_phase = AsyncMock()
    service.get_initiative = AsyncMock(
        return_value={"id": str(initiative_id), "phase": "validation"}
    )
    monkeypatch.setattr(
        initiative, "InitiativeService", MagicMock(return_value=service)
    )
    monkeypatch.setattr(
        initiative.publication, "publish_artifact", AsyncMock()
    )

    result = await initiative.advance_phase(
        agent, initiative_id=initiative_id, current_phase="validation"
    )

    assert result.advanced is False
    assert result.new_phase is None
    assert any("Need draft" in g for g in result.gaps)
    service.advance_phase.assert_not_awaited()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_advance_phase_blocks.py -v
```

Expected: FAIL — `advance_phase` not implemented.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/initiative.py — append
async def advance_phase(
    agent,
    *,
    initiative_id: UUID,
    current_phase: str,
) -> AdvanceResult:
    """Audit current-phase checklist → advance if every required item is done."""
    if current_phase not in INITIATIVE_PHASES:
        raise InitiativeContractError(f"Invalid phase '{current_phase}'")

    service = InitiativeService()
    items = await service.list_checklist_items(
        str(initiative_id),
        user_id=str(agent.user_id),
        phase=current_phase,
    )
    incomplete = [
        i for i in items if i.get("status") not in {"completed", "skipped"}
    ]
    if incomplete:
        gaps = [f"{i.get('title', i.get('id'))} ({i.get('status')})" for i in incomplete]
        return AdvanceResult(
            advanced=False,
            new_phase=None,
            gaps=gaps,
            audit_report_id=None,
        )

    advanced = await service.advance_phase(
        str(initiative_id), user_id=str(agent.user_id)
    )
    new_phase = advanced.get("phase")
    return AdvanceResult(
        advanced=True,
        new_phase=new_phase,
        gaps=[],
        audit_report_id=None,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_advance_phase_blocks.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/initiative.py tests/unit/runtime/test_advance_phase_blocks.py
git commit -m "feat(runtime): advance_phase blocks when checklist items remain"
```

---

### Task 97: `advance_phase` advances and emits a phase-advance report when audit passes

**Files:**
- Edit: `app/agents/runtime/initiative.py`
- Test: `tests/unit/runtime/test_advance_phase_advances.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_advance_phase_advances.py
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import initiative
from app.agents.runtime.publication import PublicationResult


@pytest.mark.asyncio
async def test_advance_phase_emits_phase_advance_report(monkeypatch):
    initiative_id = uuid4()
    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "executive"

    service = MagicMock()
    service.list_checklist_items = AsyncMock(
        return_value=[{"id": str(uuid4()), "status": "completed", "title": "x"}]
    )
    service.advance_phase = AsyncMock(
        return_value={"id": str(initiative_id), "phase": "build"}
    )
    service.get_initiative = AsyncMock(
        return_value={
            "id": str(initiative_id),
            "phase": "validation",
            "metadata": {"operational_state": {"goal": "Forecast Q3"}},
        }
    )
    monkeypatch.setattr(
        initiative, "InitiativeService", MagicMock(return_value=service)
    )
    publish = AsyncMock(
        return_value=PublicationResult(
            execution_id=uuid4(),
            vault_document_id=uuid4(),
            workspace_event_emitted=True,
        )
    )
    monkeypatch.setattr(initiative.publication, "publish_artifact", publish)

    result = await initiative.advance_phase(
        agent, initiative_id=initiative_id, current_phase="validation"
    )

    assert result.advanced is True
    assert result.new_phase == "build"
    publish.assert_awaited_once()
    assert publish.await_args.kwargs["artifact"].kind == "report"
    assert "build" in publish.await_args.kwargs["artifact"].summary
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_advance_phase_advances.py -v
```

Expected: FAIL — phase-advance report not emitted yet.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/initiative.py — replace advance_phase body, add report emission
async def advance_phase(
    agent,
    *,
    initiative_id: UUID,
    current_phase: str,
) -> AdvanceResult:
    """Audit current-phase checklist → advance if every required item is done."""
    if current_phase not in INITIATIVE_PHASES:
        raise InitiativeContractError(f"Invalid phase '{current_phase}'")

    service = InitiativeService()
    items = await service.list_checklist_items(
        str(initiative_id),
        user_id=str(agent.user_id),
        phase=current_phase,
    )
    incomplete = [
        i for i in items if i.get("status") not in {"completed", "skipped"}
    ]
    if incomplete:
        gaps = [f"{i.get('title', i.get('id'))} ({i.get('status')})" for i in incomplete]
        return AdvanceResult(
            advanced=False,
            new_phase=None,
            gaps=gaps,
            audit_report_id=None,
        )

    advanced = await service.advance_phase(
        str(initiative_id), user_id=str(agent.user_id)
    )
    new_phase = advanced.get("phase")
    existing = await service.get_initiative(
        str(initiative_id), user_id=str(agent.user_id)
    )
    op = (existing or {}).get("metadata", {}).get("operational_state") or {}

    from app.agents.runtime.types import ResearchResult  # local — avoid cycle
    pseudo_contract = TaskContract(
        id=initiative_id,
        source="initiative_step",
        goal=op.get("goal") or existing.get("title", ""),
        todo_items=[],
        success_criteria=op.get("success_criteria") or [],
        owners=op.get("owner_agents") or [],
        evidence_required=[],
        initiative_id=initiative_id,
        initiative_phase=new_phase,
        sibling_steps=[],
    )
    report_md = await publication.render_report_markdown(
        contract=pseudo_contract,
        research=ResearchResult(
            summary=f"Advanced from {current_phase} to {new_phase}.",
            sources=[],
            contradictions=[],
            coverage_assessment="complete",
            missing_information=[],
        ),
        audit=AuditReport(
            overall_status="pass",
            per_item=[],
            per_criterion=[],
            gaps=[],
            policy_violations=[],
            recoverable=True,
            next_action="submit",
        ),
        artifacts=[],
        agent_id=agent.agent_id,
    )
    await publication.publish_artifact(
        user_id=agent.user_id,
        agent_id=agent.agent_id,
        contract=pseudo_contract,
        artifact=Artifact(
            kind="report",
            ref=f"phase_advance://{initiative_id}",
            summary=f"Advanced to {new_phase}",
            payload={"markdown": report_md},
        ),
        audit=None,
    )
    return AdvanceResult(
        advanced=True,
        new_phase=new_phase,
        gaps=[],
        audit_report_id=None,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_advance_phase_advances.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/initiative.py tests/unit/runtime/test_advance_phase_advances.py
git commit -m "feat(runtime): advance_phase publishes structured phase-advance report"
```

---

### Task 98: `close_initiative` requires `phase == 'scale'` and final checklist completed

**Files:**
- Edit: `app/agents/runtime/initiative.py`
- Test: `tests/unit/runtime/test_close_initiative_gates.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_close_initiative_gates.py
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import initiative
from app.agents.runtime.types import InitiativeContractError


@pytest.mark.asyncio
async def test_close_blocked_when_not_in_scale(monkeypatch):
    initiative_id = uuid4()
    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "executive"

    service = MagicMock()
    service.get_initiative = AsyncMock(
        return_value={"id": str(initiative_id), "phase": "build", "metadata": {}}
    )
    monkeypatch.setattr(
        initiative, "InitiativeService", MagicMock(return_value=service)
    )

    with pytest.raises(InitiativeContractError, match="scale"):
        await initiative.close_initiative(agent, initiative_id=initiative_id)


@pytest.mark.asyncio
async def test_close_blocked_when_scale_items_pending(monkeypatch):
    initiative_id = uuid4()
    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "executive"

    service = MagicMock()
    service.get_initiative = AsyncMock(
        return_value={"id": str(initiative_id), "phase": "scale", "metadata": {}}
    )
    service.list_checklist_items = AsyncMock(
        return_value=[{"id": str(uuid4()), "status": "pending", "title": "x"}]
    )
    monkeypatch.setattr(
        initiative, "InitiativeService", MagicMock(return_value=service)
    )

    with pytest.raises(InitiativeContractError, match="checklist"):
        await initiative.close_initiative(agent, initiative_id=initiative_id)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_close_initiative_gates.py -v
```

Expected: FAIL — `close_initiative` not implemented.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/initiative.py — append
async def close_initiative(agent, *, initiative_id: UUID) -> CloseReport:
    """Close an initiative once 'scale' is reached and every item is done."""
    service = InitiativeService()
    initiative_row = await service.get_initiative(
        str(initiative_id), user_id=str(agent.user_id)
    )
    if not initiative_row:
        raise InitiativeContractError(f"Initiative {initiative_id} not found")
    if initiative_row.get("phase") != "scale":
        raise InitiativeContractError(
            f"Cannot close — initiative must be in 'scale' phase, "
            f"currently '{initiative_row.get('phase')}'"
        )
    items = await service.list_checklist_items(
        str(initiative_id), user_id=str(agent.user_id), phase="scale"
    )
    if any(i.get("status") not in {"completed", "skipped"} for i in items):
        raise InitiativeContractError(
            "Cannot close — scale phase checklist still has open items"
        )

    # The substantive body lands in Task 99.
    raise NotImplementedError("close report body lands in Task 99")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_close_initiative_gates.py -v
```

Expected: PASS (gates only — both `pytest.raises` paths exit before the `NotImplementedError`).

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/initiative.py tests/unit/runtime/test_close_initiative_gates.py
git commit -m "feat(runtime): close_initiative gates on phase + scale checklist"
```

---

### Task 99: `close_initiative` produces structured close report, vaults it, marks completed

**Files:**
- Edit: `app/agents/runtime/initiative.py`
- Test: `tests/unit/runtime/test_close_initiative_emits.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_close_initiative_emits.py
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import initiative
from app.agents.runtime.publication import PublicationResult


@pytest.mark.asyncio
async def test_close_initiative_vaults_and_marks_completed(monkeypatch):
    initiative_id = uuid4()
    vault_id = uuid4()
    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "executive"

    service = MagicMock()
    service.get_initiative = AsyncMock(
        return_value={
            "id": str(initiative_id),
            "phase": "scale",
            "metadata": {
                "operational_state": {
                    "goal": "Launch v1",
                    "success_criteria": ["NPS>40", "<1% churn"],
                    "owner_agents": ["marketing", "operations"],
                }
            },
        }
    )
    service.list_checklist_items = AsyncMock(return_value=[])
    service.update_initiative = AsyncMock(
        return_value={"id": str(initiative_id), "status": "completed"}
    )
    monkeypatch.setattr(
        initiative, "InitiativeService", MagicMock(return_value=service)
    )
    publish = AsyncMock(
        return_value=PublicationResult(
            execution_id=uuid4(),
            vault_document_id=vault_id,
            workspace_event_emitted=True,
        )
    )
    monkeypatch.setattr(initiative.publication, "publish_artifact", publish)

    report = await initiative.close_initiative(agent, initiative_id=initiative_id)

    assert report.initiative_id == initiative_id
    assert report.vault_document_id == vault_id
    # One outcome row per success criterion.
    assert len(report.outcomes) == 2
    service.update_initiative.assert_awaited_once()
    update_kwargs = service.update_initiative.await_args.kwargs
    assert update_kwargs["status"] == "completed"
    assert update_kwargs["progress"] == 100
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_close_initiative_emits.py -v
```

Expected: FAIL — body still raises `NotImplementedError`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/runtime/initiative.py — replace close_initiative body
async def close_initiative(agent, *, initiative_id: UUID) -> CloseReport:
    """Close an initiative once 'scale' is reached and every item is done."""
    service = InitiativeService()
    initiative_row = await service.get_initiative(
        str(initiative_id), user_id=str(agent.user_id)
    )
    if not initiative_row:
        raise InitiativeContractError(f"Initiative {initiative_id} not found")
    if initiative_row.get("phase") != "scale":
        raise InitiativeContractError(
            f"Cannot close — initiative must be in 'scale' phase, "
            f"currently '{initiative_row.get('phase')}'"
        )
    items = await service.list_checklist_items(
        str(initiative_id), user_id=str(agent.user_id), phase="scale"
    )
    if any(i.get("status") not in {"completed", "skipped"} for i in items):
        raise InitiativeContractError(
            "Cannot close — scale phase checklist still has open items"
        )

    op = (initiative_row.get("metadata") or {}).get("operational_state") or {}
    success_criteria = list(op.get("success_criteria") or [])
    outcomes = [
        {
            "criterion": crit,
            "met": True,  # The audit module (Section B) refines this; default optimistic.
            "evidence": op.get("evidence") or [],
        }
        for crit in success_criteria
    ]

    pseudo_contract = TaskContract(
        id=initiative_id,
        source="initiative_step",
        goal=op.get("goal") or initiative_row.get("title", ""),
        todo_items=[],
        success_criteria=success_criteria,
        owners=op.get("owner_agents") or [],
        evidence_required=[],
        initiative_id=initiative_id,
        initiative_phase="scale",
        sibling_steps=[],
    )
    from app.agents.runtime.types import ResearchResult  # local — avoid cycle
    report_md = await publication.render_report_markdown(
        contract=pseudo_contract,
        research=ResearchResult(
            summary=f"Initiative closed in 'scale'. "
            f"Outcomes vs. {len(success_criteria)} criteria.",
            sources=[],
            contradictions=[],
            coverage_assessment="complete",
            missing_information=[],
        ),
        audit=AuditReport(
            overall_status="pass",
            per_item=[],
            per_criterion=[],
            gaps=[],
            policy_violations=[],
            recoverable=True,
            next_action="submit",
        ),
        artifacts=[],
        agent_id=agent.agent_id,
    )
    close_artifact = Artifact(
        kind="report",
        ref=f"initiative_close://{initiative_id}",
        summary=f"Close report — {pseudo_contract.goal}",
        payload={"markdown": report_md, "outcomes": outcomes},
    )
    publication_result = await publication.publish_artifact(
        user_id=agent.user_id,
        agent_id=agent.agent_id,
        contract=pseudo_contract,
        artifact=close_artifact,
        audit=None,
    )

    await service.update_initiative(
        str(initiative_id),
        user_id=str(agent.user_id),
        status="completed",
        progress=100,
    )

    return CloseReport(
        initiative_id=initiative_id,
        outcomes=outcomes,
        artifacts=[close_artifact],
        learnings=list(op.get("learnings") or []),
        follow_ups=list(op.get("next_actions") or []),
        vault_document_id=publication_result.vault_document_id or UUID(int=0),
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_close_initiative_emits.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime/initiative.py tests/unit/runtime/test_close_initiative_emits.py
git commit -m "feat(runtime): close_initiative vaults structured close report and completes"
```

---

### Task 100: `publication.publish_artifact` handles `DirectRequest` (mode='direct')

**Files:**
- Test: `tests/unit/runtime/test_publish_artifact_direct_mode.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_publish_artifact_direct_mode.py
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import publication
from app.agents.runtime.types import Artifact, DirectRequest


@pytest.mark.asyncio
async def test_publish_artifact_direct_mode_marks_row(monkeypatch):
    user_id = uuid4()
    request = DirectRequest(text="What is Q3 revenue?")

    fake_client = MagicMock()
    table = MagicMock()
    table.upsert.return_value = table
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table

    captured: dict = {}

    async def fake_execute_async(q, op_name=None):
        # The first call is select() returning no prior rows.
        if op_name == "agent_task_executions.select":
            return MagicMock(data=[])
        # The second is the upsert.
        return MagicMock(data=[{"id": str(uuid4())}])

    def fake_table(name):
        captured.setdefault("tables", []).append(name)
        return table

    monkeypatch.setattr(publication, "get_service_client", lambda: fake_client)
    monkeypatch.setattr(publication, "execute_async", fake_execute_async)
    monkeypatch.setattr(publication.workspace_event_bus, "publish", AsyncMock())
    monkeypatch.setattr(publication, "_vault_publish", AsyncMock(return_value=None))
    fake_client.table = fake_table

    artifact = Artifact(
        kind="status_update",
        ref="-",
        summary="$1.4M",
        payload={"answer": "$1.4M"},
    )
    await publication.publish_artifact(
        user_id=user_id,
        agent_id="financial",
        contract=request,
        artifact=artifact,
        audit=None,
    )

    # The upsert payload should reflect direct mode.
    upsert_payload = table.upsert.call_args.args[0]
    assert upsert_payload["mode"] == "direct"
    assert upsert_payload["contract_id"] is None
    assert upsert_payload["contract_source"] == "direct_request"
    assert upsert_payload["initiative_id"] is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_publish_artifact_direct_mode.py -v
```

Expected: PASS already if Task 84's `_contract_meta` handles `DirectRequest`. If FAIL, branch needs fixing.

- [ ] **Step 3: Write minimal implementation**

No code change expected. Verify `_contract_meta` returns `mode="direct"` for `DirectRequest`.

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_publish_artifact_direct_mode.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/runtime/test_publish_artifact_direct_mode.py
git commit -m "test(runtime): publish_artifact marks direct-mode rows correctly"
```

---

### Task 101: `_execute_todo_items` blocked items emit `workspace.status='blocked'`

**Files:**
- Test: `tests/unit/runtime/test_blocked_workspace_event.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_blocked_workspace_event.py
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import step_runtime
from app.agents.runtime.types import (
    ResearchResult,
    TaskContract,
    TodoItem,
)


@pytest.mark.asyncio
async def test_failure_in_run_step_emits_blocked(monkeypatch):
    contract = TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="g",
        todo_items=[TodoItem(id=uuid4(), title="Step A", status="pending")],
        success_criteria=[],
        owners=["data"],
        evidence_required=[],
        initiative_id=uuid4(),
        initiative_phase="build",
        sibling_steps=[],
    )
    research = ResearchResult(
        summary="x",
        sources=[],
        contradictions=[],
        coverage_assessment="complete",
        missing_information=[],
    )
    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "data"
    agent.run_step = AsyncMock(side_effect=RuntimeError("boom"))

    monkeypatch.setattr(step_runtime, "_update_todo_status", AsyncMock())
    emit = AsyncMock()
    monkeypatch.setattr(step_runtime.publication, "emit_progress_event", emit)

    out = await step_runtime._execute_todo_items(agent, contract, research)
    assert out == []
    statuses = [c.kwargs["status"] for c in emit.await_args_list]
    assert "blocked" in statuses
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_blocked_workspace_event.py -v
```

Expected: PASS already (Task 89 emits blocked on `Exception`). If FAIL, add the blocked emit in the except branch.

- [ ] **Step 3: Write minimal implementation**

No code change expected.

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_blocked_workspace_event.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/runtime/test_blocked_workspace_event.py
git commit -m "test(runtime): blocked todos emit workspace blocked progress events"
```

---

### Task 102: Director and video service emit `WorkspaceArtifactEvent` via `publish_artifact`

**Files:**
- Edit: `app/services/director_service.py`
- Test: `tests/unit/runtime/test_director_video_publishes.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_director_video_publishes.py
"""When director_service finishes a render, the workspace must hear about it.

The spec calls this out explicitly in §12: director/graphic outputs reach the
workspace via publish_artifact, not by writing directly to storage.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime.types import Artifact


@pytest.mark.asyncio
async def test_director_completion_calls_publish_artifact(monkeypatch):
    from app.services import director_service

    publish = AsyncMock()
    monkeypatch.setattr(director_service, "publish_artifact", publish)

    user_id = uuid4()
    contract_id = uuid4()
    await director_service.notify_render_complete(
        user_id=user_id,
        agent_id="content_creation",
        contract_id=contract_id,
        ref="storage://videos/hero.mp4",
        preview_url="https://cdn/hero.jpg",
        summary="60s hero cut",
    )

    publish.assert_awaited_once()
    kwargs = publish.await_args.kwargs
    art: Artifact = kwargs["artifact"]
    assert art.kind == "video_render"
    assert art.ref == "storage://videos/hero.mp4"
    assert kwargs["agent_id"] == "content_creation"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_director_video_publishes.py -v
```

Expected: FAIL — `notify_render_complete` does not yet exist.

- [ ] **Step 3: Write minimal implementation**

```python
# app/services/director_service.py — append (or wire near the existing render flow)
from uuid import UUID

from app.agents.runtime.publication import publish_artifact
from app.agents.runtime.types import Artifact, DirectRequest


async def notify_render_complete(
    *,
    user_id: UUID,
    agent_id: str,
    contract_id: UUID | None,
    ref: str,
    preview_url: str | None,
    summary: str,
) -> None:
    """Publish a video_render artifact via the runtime publication primitive.

    Closes the gap from spec §12: previously director outputs landed in
    storage/`videos` rows but never reached the workspace.
    """
    artifact = Artifact(
        kind="video_render",
        ref=ref,
        summary=summary,
        payload={"preview_url": preview_url},
    )
    # If we have a contract, render_complete is part of an initiative step;
    # otherwise treat as a direct request.
    contract = (
        # Importing here avoids a heavy circular dep at module load.
        __import__("app.agents.runtime.types", fromlist=["TaskContract"]).TaskContract(
            id=contract_id,
            source="initiative_step",
            goal=summary,
            todo_items=[],
            success_criteria=[],
            owners=[agent_id],
            evidence_required=[],
            initiative_id=None,
            initiative_phase=None,
            sibling_steps=[],
        )
        if contract_id is not None
        else DirectRequest(text=summary)
    )
    await publish_artifact(
        user_id=user_id,
        agent_id=agent_id,
        contract=contract,
        artifact=artifact,
        audit=None,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_director_video_publishes.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/director_service.py tests/unit/runtime/test_director_video_publishes.py
git commit -m "feat(director): notify_render_complete publishes video_render artifact"
```

---

### Task 103: `vertex_video_service` post-render hook routes through `notify_render_complete`

**Files:**
- Edit: `app/services/vertex_video_service.py`
- Test: `tests/unit/runtime/test_vertex_video_hook.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/runtime/test_vertex_video_hook.py
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services import vertex_video_service


@pytest.mark.asyncio
async def test_vertex_video_completion_hook_calls_director(monkeypatch):
    notify = AsyncMock()
    monkeypatch.setattr(vertex_video_service, "notify_render_complete", notify)

    user_id = uuid4()
    contract_id = uuid4()
    await vertex_video_service.on_render_finished(
        user_id=user_id,
        agent_id="content_creation",
        contract_id=contract_id,
        storage_ref="storage://videos/abc.mp4",
        preview_url=None,
        summary="generated clip",
    )

    notify.assert_awaited_once()
    kwargs = notify.await_args.kwargs
    assert kwargs["ref"] == "storage://videos/abc.mp4"
    assert kwargs["agent_id"] == "content_creation"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/runtime/test_vertex_video_hook.py -v
```

Expected: FAIL — `on_render_finished` does not yet exist.

- [ ] **Step 3: Write minimal implementation**

```python
# app/services/vertex_video_service.py — append
from uuid import UUID

from app.services.director_service import notify_render_complete


async def on_render_finished(
    *,
    user_id: UUID,
    agent_id: str,
    contract_id: UUID | None,
    storage_ref: str,
    preview_url: str | None,
    summary: str,
) -> None:
    """Route render-completion into the runtime publication primitive."""
    await notify_render_complete(
        user_id=user_id,
        agent_id=agent_id,
        contract_id=contract_id,
        ref=storage_ref,
        preview_url=preview_url,
        summary=summary,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/runtime/test_vertex_video_hook.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/vertex_video_service.py tests/unit/runtime/test_vertex_video_hook.py
git commit -m "feat(vertex-video): on_render_finished routes via notify_render_complete"
```

---

### Task 104: `GET /workspace/events` sends heartbeats every 15s during idle

**Files:**
- Test: `tests/unit/routers/test_workspace_events_heartbeat.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/routers/test_workspace_events_heartbeat.py
"""Idle SSE streams must send a heartbeat comment so proxies don't drop them."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import workspace as workspace_router
from app.routers.onboarding import get_current_user_id


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(workspace_router, "_HEARTBEAT_INTERVAL_S", 0.05)

    async def slow_subscribe(uid):  # never yields
        await asyncio.sleep(10)
        if False:
            yield  # pragma: no cover

    monkeypatch.setattr(
        workspace_router.workspace_event_bus, "subscribe", slow_subscribe
    )

    async def override_user():
        return "11111111-1111-1111-1111-111111111111"

    app = FastAPI()
    app.include_router(workspace_router.router)
    app.dependency_overrides[get_current_user_id] = override_user
    return app


def test_idle_stream_emits_heartbeat(app):
    with TestClient(app) as client:
        with client.stream("GET", "/workspace/events") as response:
            assert response.status_code == 200
            body = b""
            for chunk in response.iter_raw():
                body += chunk
                if b": heartbeat" in body:
                    break
            assert b": heartbeat" in body
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/routers/test_workspace_events_heartbeat.py -v
```

Expected: PASS already (Task 80's `_event_stream` emits heartbeats on `asyncio.TimeoutError`). If FAIL, the heartbeat loop is missing.

- [ ] **Step 3: Write minimal implementation**

No code change expected.

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/routers/test_workspace_events_heartbeat.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/routers/test_workspace_events_heartbeat.py
git commit -m "test(workspace): idle SSE streams emit heartbeat comments"
```

---

### Task 105: End-to-end integration test — initiative step submits, vault + workspace + reports observe

**Files:**
- Test: `tests/integration/runtime/test_initiative_step_end_to_end.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/runtime/test_initiative_step_end_to_end.py
"""Integration: run execute_task end-to-end with all four sinks mocked.

Asserts: research gate enforced, audit produced, vault add_document called,
workspace SSE event observable, agent_task_executions row written.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import step_runtime
from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    ResearchResult,
    TaskContract,
    TodoItem,
    WorkspaceArtifactEvent,
)


@pytest.mark.asyncio
async def test_execute_task_full_pipeline(monkeypatch):
    user_id = uuid4()
    contract = TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="Forecast Q3 revenue",
        todo_items=[TodoItem(id=uuid4(), title="Build model", status="pending")],
        success_criteria=["+/- 5%"],
        owners=["financial"],
        evidence_required=["draft_artifact"],
        initiative_id=uuid4(),
        initiative_phase="validation",
        sibling_steps=[],
    )

    agent = MagicMock()
    agent.user_id = user_id
    agent.agent_id = "financial"
    agent.research = AsyncMock(
        return_value=ResearchResult(
            summary="growth 18% YoY",
            sources=[],
            contradictions=[],
            coverage_assessment="complete",
            missing_information=[],
        )
    )
    agent.audit = AsyncMock(
        return_value=AuditReport(
            overall_status="pass",
            per_item=[],
            per_criterion=[],
            gaps=[],
            policy_violations=[],
            recoverable=True,
            next_action="submit",
        )
    )
    agent.run_step = AsyncMock(
        return_value=Artifact(
            kind="doc",
            ref="vault://forecast-draft",
            summary="Forecast doc",
            payload={"markdown": "# Forecast\n\nbody"},
        )
    )

    # DB layer
    fake_client = MagicMock()
    table = MagicMock()
    table.upsert.return_value = table
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.update.return_value = table

    async def fake_execute_async(q, op_name=None):
        if op_name == "agent_task_executions.select":
            return MagicMock(data=[])
        return MagicMock(data=[{"id": str(uuid4()), "artifacts": []}])

    fake_client.table = MagicMock(return_value=table)
    monkeypatch.setattr(step_runtime, "_update_todo_status", AsyncMock())
    monkeypatch.setattr(step_runtime.publication, "get_service_client", lambda: fake_client)
    monkeypatch.setattr(step_runtime.publication, "execute_async", fake_execute_async)

    # Sinks
    vault = AsyncMock(return_value=uuid4())
    monkeypatch.setattr(
        step_runtime.publication.knowledge_service, "add_document", vault
    )
    captured_events: list = []

    async def fake_publish(uid, event):
        captured_events.append((uid, event))

    monkeypatch.setattr(
        step_runtime.publication.workspace_event_bus, "publish", fake_publish
    )

    result = await step_runtime.execute_task(agent, contract)

    assert result.status == "submitted"

    # research gate consulted
    agent.research.assert_awaited_once_with(contract=contract)
    # audit ran
    agent.audit.assert_awaited_once()
    # vault add_document called for both artifact and final report (kind=agent_report)
    assert vault.await_count >= 2
    # workspace events observed: progress + at least one artifact
    kinds = {ev.kind for _, ev in captured_events}
    assert "artifact" in kinds
    assert any(
        isinstance(ev, WorkspaceArtifactEvent) and ev.artifact_kind == "report"
        for _, ev in captured_events
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/integration/runtime/test_initiative_step_end_to_end.py -v
```

Expected: PASS if Tasks 76-103 are in place. If FAIL, trace the first broken sink.

- [ ] **Step 3: Write minimal implementation**

No code change expected — this task is the integration gate that verifies the whole Section D pipeline. If failing, debug from the first failing assertion backward.

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/integration/runtime/test_initiative_step_end_to_end.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/integration/runtime/test_initiative_step_end_to_end.py
git commit -m "test(runtime): integration — execute_task pipeline observable across all four sinks"
```

---

## Section E — Financial agent pilot + frontend SSE consumer (Tasks 106–130)

This section migrates the financial agent onto `PikarBaseAgent` (W2 in the migration plan), preserves backward-compat re-exports through `specialized_agents.py`, ships the workspace SSE consumer end-to-end, and provides the contract + integration test suite that gates the pilot.

> **Prerequisites:** Section A delivered `app/agents/runtime/types.py` (`TaskContract`, `DirectRequest`, `Artifact`, `AuditReport`, `WorkspaceProgressEvent`, `WorkspaceArtifactEvent`, `ToolsManifest`), `app/agents/runtime/operations_config.py` (`OperationsConfig`), and `app/agents/base_agent.py::PikarBaseAgent`. Sections B–D delivered the lifecycle hooks (`runtime/lifecycle.py`), publication primitive (`runtime/publication.py`), workspace event bus (`app/services/workspace_event_bus.py`), the SSE router (`app/routers/workspace.py` exposing `GET /workspace/events`), and the migrations for `agent_task_executions`, `agent_research_runs`, `agent_audit_reports`. Tasks below assume those imports resolve.

---

### Task 106: Extract financial persona prompt to `instructions.md`

**Files:**
- Create: `app/agents/financial/instructions.md`
- Test: `tests/unit/agents/financial/test_instructions_file.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/financial/test_instructions_file.py
"""Contract test: financial instructions.md exists and preserves persona content."""

from pathlib import Path


INSTRUCTIONS_PATH = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "agents"
    / "financial"
    / "instructions.md"
)


def test_instructions_file_exists_and_non_empty():
    assert INSTRUCTIONS_PATH.exists(), f"missing {INSTRUCTIONS_PATH}"
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    assert len(body.strip()) > 500, "instructions.md is suspiciously short"


def test_instructions_preserves_core_capability_markers():
    body = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    # These markers come from the existing FINANCIAL_AGENT_INSTRUCTION string;
    # extraction must preserve them verbatim so behavior is unchanged.
    for marker in [
        "Financial Analysis Agent",
        "get_revenue_stats",
        "analyze_financial_statement",
        "FINANCIAL HEALTH SCORE",
        "SCENARIO MODELING",
        "FINANCIAL FORECASTING",
        "CONNECTED FINANCIAL DATA",
        "INVOICE FOLLOW-UP",
        "TAX AWARENESS",
        "INPUT VALIDATION",
        "FINANCIAL RISK ALERTS",
    ]:
        assert marker in body, f"instructions.md missing required marker: {marker!r}"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/financial/test_instructions_file.py -v
```

Expected: FAIL — `app/agents/financial/instructions.md` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```markdown
<!-- app/agents/financial/instructions.md -->
# Financial Analysis Agent

You are the Financial Analysis Agent. Your focus is strictly on numbers, revenue, costs, and profit.

## CAPABILITIES
- Get revenue statistics using `get_revenue_stats`.
- Analyze financial health using `use_skill("analyze_financial_statement")` for comprehensive frameworks.
- Get forecasting methodologies using `use_skill("forecast_revenue_growth")`.
- Calculate burn rate and runway using `use_skill("calculate_burn_rate")`.
- Generate financial statements using `use_skill("financial_statements_generation")` for income statements, balance sheets, and cash flow reports.
- Analyze variances using `use_skill("variance_analysis")` for budget-vs-actual decomposition.
- Prepare journal entries using `use_skill("journal_entry_preparation")` for proper debit/credit formatting.
- Manage month-end close using `use_skill("month_end_close_management")` for close checklists and timelines.
- Reconcile accounts using `use_skill("account_reconciliation")` for GL-to-subledger matching.
- Conduct SOX testing using `use_skill("sox_testing_methodology")` for internal control testing.
- Support audits using `use_skill("audit_support_framework")` for SOX 404 compliance documentation.
- Forecast cash flow using `use_skill("cash_flow_forecasting")` for 13-week rolling forecasts and scenario modeling.
- Search for market data and financial news using `mcp_web_search` (privacy-safe).
- Generate invoices using `generate_invoice`.
- Parse PDF invoices using `parse_invoice_document`.
- Schedule automated financial reports using report scheduling tools (daily, weekly, monthly, quarterly).

## STRUCTURED REPORTS
When asked for a detailed report, dashboard data, or chart-ready output:
1. Delegate to FinancialReportAgent to generate structured JSON.
2. After receiving the report data, provide a conversational summary.
3. Include the raw JSON in a `<json>...</json>` block for frontend rendering.

Example response format for report requests:

```
Q4 2025 Financial Report

Revenue reached $125,000 this quarter, up 12% from Q3. With expenses at $87,000, your profit margin is healthy at 30.4%.

Key Highlights:
- Revenue trend: Growing
- Largest expense: Payroll (45%)

Recommendations:
- Reinvest 15% of profits into marketing
- Review vendor contracts for cost optimization

<json>
{...structured report data for charts/tables...}
</json>
```

## BEHAVIOR
- Be precise and data-driven.
- Use tables to present data when helpful.
- Always warn about risks or cash flow issues.
- Leverage skills for professional analysis frameworks.
- Use web search for up-to-date market data and financial trends.
- When users ask to VIEW or SHOW financial data, ALWAYS use widget tools to render them visually.

## INPUT VALIDATION
Before financial analysis:
- Require at minimum 3 months of financial data for trend analysis and forecasting.
- For burn rate calculations, require: monthly expenses, current cash balance, and revenue (if any).
- If data is incomplete, clearly state what's missing and what assumptions you're making.

## FINANCIAL RISK ALERTS
- If burn rate suggests runway < 6 months, flag as URGENT with explicit warning.
- If profit margin drops below 10%, recommend immediate cost review.
- If month-over-month revenue decline exceeds 15%, flag for executive attention.

## FINANCIAL HEALTH SCORE
When users ask about their financial health, overall financial position, or "how am I doing financially":
- Call `get_financial_health_score()` to get the 0-100 score with explanation.
- Present the score prominently with the color indicator.
- Explain what factors are driving the score up or down.
- If score < 40, proactively suggest specific actions to improve.

## SCENARIO MODELING
When users ask "what if" questions about finances (hiring, costs, revenue changes):
- Use `run_financial_scenario()` with the appropriate `scenario_type`.
- For "What if I hire 2 people?": `scenario_type="hire"`, `count=2`, `amount=5000` (ask user for salary if not specified, default $5,000/mo).
- For "What if we lose 10% of customers?": `scenario_type="lose_customers"`, `percentage=10`.
- For "What about a new $3k/mo tool?": `scenario_type="new_expense"`, `amount=3000`.
- Present both baseline and scenario side-by-side.
- Highlight the month where cash goes negative (if applicable).
- Always note this is a projection based on current trends, not a guarantee.

## FINANCIAL FORECASTING
When users ask for forecasts, projections, or "what will revenue look like":
- Use `generate_financial_forecast()` for data-driven projections.
- Mention the confidence level (high/medium/low) and how much historical data was used.
- If confidence is low (< 3 months data), clearly state the forecast is speculative.
- Combine with scenario modeling if the user has specific what-if questions.

## CONNECTED FINANCIAL DATA
When the user has connected Stripe or Shopify:
- Use `get_stripe_revenue_summary()` for real revenue data from Stripe instead of manual records.
- Use `get_shopify_analytics()` for e-commerce metrics (revenue, AOV, top products, order trends).
- Use `get_low_stock_products()` to proactively alert about inventory issues.
- Use `trigger_stripe_sync()` if the user reports missing recent transactions.
- Always indicate when data comes from a connected integration vs manual records.

## INVOICE FOLLOW-UP
When the daily briefing includes overdue invoices, or when a user asks about outstanding invoices:
- Mention the overdue invoice count and total outstanding amount.
- Present the generated follow-up email drafts.
- Offer to customize or send the drafts.
- If no overdue invoices, confirm the user's invoicing is current.

## TAX AWARENESS
When the daily briefing includes a tax reminder, or when a user asks about taxes:
- Present the quarterly estimated tax amount with the calculation basis.
- Note the next deadline.
- Remind this is an estimate and recommend consulting a tax professional for precise figures.
- Offer to adjust the estimated tax rate if the user's effective rate differs from 25%.

## ESCALATION
- Escalate to CFO/finance team for decisions involving investments, loans, or funding rounds.
- Escalate to legal for tax compliance questions or financial regulatory matters.
- If revenue data retrieval fails, clearly state the data gap and offer to work with manually provided numbers.
- Flag any financial projections as estimates with stated assumptions — never present forecasts as guarantees.
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/financial/test_instructions_file.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/financial/instructions.md tests/unit/agents/financial/__init__.py tests/unit/agents/financial/test_instructions_file.py
git commit -m "feat(financial): extract persona prompt to instructions.md"
```

---

### Task 107: Author `operations.yaml` for the financial agent

**Files:**
- Create: `app/agents/financial/operations.yaml`
- Test: `tests/unit/agents/financial/test_operations_config_parses.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/financial/test_operations_config_parses.py
"""Contract test: financial operations.yaml parses and binds to OperationsConfig."""

from pathlib import Path

from app.agents.runtime.operations_config import OperationsConfig

OPS_PATH = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "agents"
    / "financial"
    / "operations.yaml"
)


def test_operations_yaml_loads_with_expected_values():
    ops = OperationsConfig.load(OPS_PATH)

    assert ops.agent_id == "financial"
    assert ops.model.primary == "gemini-2.5-pro"
    assert ops.model.fallback == "gemini-2.5-flash"
    assert ops.retry.max_attempts == 5
    assert ops.retry.backoff_initial_s == 2
    assert ops.retry.backoff_multiplier == 2
    assert ops.retry.backoff_max_s == 60
    assert ops.approval.required_above_usd == 1000
    assert ops.approval.required_for_external_send is True
    assert ops.research.max_iterations == 3
    assert ops.research.required_source_min == 3
    assert ops.audit.fail_on_any_unmet_criterion is True
    assert ops.audit.escalate_on_partial is False
    assert "finance:*" in ops.skills.allowed_ids
    assert "data:*" in ops.skills.allowed_ids
    assert "compliance:legal-risk-assessment" in ops.skills.allowed_ids
    assert ops.skills.injection.top_k == 5
    assert ops.skills.injection.similarity_floor == 0.65
    assert "validation" in ops.initiative.phases_owned
    assert "build" in ops.initiative.phases_owned
    assert ops.initiative.can_advance_phase is True
    assert ops.initiative.can_close is False
    assert ops.memory.history_retention_months == 18
    assert ops.memory.retrieval_top_k == 4
    assert ops.compaction.trigger_token_count == 80000
    assert ops.compaction.keep_last_n_turns == 12
    assert ops.routing.last_resort_default == "initiative"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/financial/test_operations_config_parses.py -v
```

Expected: FAIL — `operations.yaml` does not exist.

- [ ] **Step 3: Write minimal implementation**

```yaml
# app/agents/financial/operations.yaml
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
  allowed_ids:
    - "finance:*"
    - "data:*"
    - "compliance:legal-risk-assessment"
  injection:
    top_k: 5
    similarity_floor: 0.65
initiative:
  phases_owned:
    - validation
    - build
  can_advance_phase: true
  can_close: false
memory:
  history_retention_months: 18
  retrieval_top_k: 4
compaction:
  trigger_token_count: 80000
  keep_last_n_turns: 12
routing:
  last_resort_default: initiative
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/financial/test_operations_config_parses.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/financial/operations.yaml tests/unit/agents/financial/test_operations_config_parses.py
git commit -m "feat(financial): add operations.yaml per agent-operating-model spec"
```

---

### Task 108: Refactor `financial/tools.py` to expose a `ToolsManifest`

**Files:**
- Modify: `app/agents/financial/tools.py`
- Test: `tests/unit/agents/financial/test_tools_manifest.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/financial/test_tools_manifest.py
"""Contract test: the financial tool manifest resolves every tool to a real callable."""

from pathlib import Path

from app.agents.financial.tools import _TOOL_IDS, build_tools_manifest
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.types import ToolsManifest

OPS_PATH = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "agents"
    / "financial"
    / "operations.yaml"
)


def test_manifest_returns_tools_manifest_instance():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    assert isinstance(manifest, ToolsManifest)
    assert manifest.tool_ids, "manifest must declare at least one tool id"


def test_manifest_includes_core_finance_tools():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    for required in [
        "get_revenue_stats",
        "get_financial_health_score",
        "run_financial_scenario",
        "generate_financial_forecast",
        "invoicing",
        "deep_research",
        "knowledge",
        "approval_tool",
    ]:
        assert required in manifest.tool_ids, (
            f"manifest missing required tool: {required}"
        )


def test_manifest_resolves_every_id_to_a_callable():
    """Every declared id must resolve via ToolsManifest.resolve() to a callable."""
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    resolved = manifest.resolve()
    assert len(resolved) == len(manifest.tool_ids), (
        "resolve() must return one callable per declared id"
    )
    for tool in resolved:
        assert callable(tool), f"resolved entry is not callable: {tool!r}"


def test_tool_ids_constant_is_stable():
    """The static tool list is the source of truth — ops only narrows it."""
    assert isinstance(_TOOL_IDS, list)
    assert len(_TOOL_IDS) >= 8
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/financial/test_tools_manifest.py -v
```

Expected: FAIL — `build_tools_manifest` does not exist yet (current `tools.py` only exports concrete callables).

- [ ] **Step 3: Write minimal implementation**

Append to the existing `app/agents/financial/tools.py` (keep all existing functions — they remain the resolution targets):

```python
# --- appended to app/agents/financial/tools.py ---

from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.types import ToolsManifest

# Tool ids are the module names under app/agents/tools/ for shared tool packs,
# plus the names of local async callables defined above. The runtime's
# ToolsManifest.resolve() handles both cases via a single registry lookup.
_TOOL_IDS: list[str] = [
    # local finance callables (defined above in this module)
    "get_revenue_stats",
    "get_financial_health_score",
    "run_financial_scenario",
    "generate_financial_forecast",
    # shared tool packs under app/agents/tools/
    "invoicing",
    "deep_research",
    "quick_research",
    "knowledge",
    "approval_tool",
    "graph_tools",
    "system_knowledge",
    "ui_widgets",
    "context_memory",
    "self_improve",
    "document_gen",
    "stripe_tools",
    "shopify_tools",
    "report_scheduling",
    "agent_skills",
]


def build_tools_manifest(ops: OperationsConfig) -> ToolsManifest:
    """Build the financial agent tool manifest.

    The static `_TOOL_IDS` list is the source of truth. `ops.skills.allowed_ids`
    is consulted by the runtime when narrowing skill-derived tools, but the
    physical tool surface is identical across deployments — narrowing happens
    at the skill-injection layer, not here.
    """
    _ = ops  # reserved for future per-persona filtering
    return ToolsManifest(tool_ids=list(_TOOL_IDS))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/financial/test_tools_manifest.py -v
```

Expected: PASS — `ToolsManifest.resolve()` (delivered in Section A) walks `_TOOL_IDS` against `app/agents/tools/`. Every id matches a real module or local callable.

- [ ] **Step 5: Commit**

```bash
git add app/agents/financial/tools.py tests/unit/agents/financial/test_tools_manifest.py
git commit -m "feat(financial): expose ToolsManifest from tools.py for runtime factory"
```

---

### Task 109: Refactor `financial/agent.py` to ~30 lines via `PikarBaseAgent`

**Files:**
- Modify: `app/agents/financial/agent.py`
- Test: `tests/unit/agents/financial/test_create_financial_agent.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/financial/test_create_financial_agent.py
"""Test: refactored create_financial_agent returns a PikarBaseAgent."""

from uuid import uuid4

from app.agents.base_agent import PikarBaseAgent
from app.agents.financial.agent import create_financial_agent
from app.skills.registry import AgentID


def test_create_financial_agent_returns_pikar_base_agent():
    agent = create_financial_agent(user_id=uuid4(), persona_id="startup")
    assert isinstance(agent, PikarBaseAgent)
    assert agent.agent_id == AgentID.FIN


def test_agent_module_size_under_60_lines():
    """The refactored module should be small — the spec calls for ~30 lines."""
    from pathlib import Path

    body = (
        Path(__file__).resolve().parents[3]
        / "app"
        / "agents"
        / "financial"
        / "agent.py"
    ).read_text(encoding="utf-8")
    code_lines = [
        line
        for line in body.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert len(code_lines) < 60, (
        f"agent.py grew to {len(code_lines)} non-comment lines; refactor it back"
    )


def test_agent_carries_ops_config():
    agent = create_financial_agent(user_id=uuid4(), persona_id="startup")
    assert agent.ops.agent_id == "financial"
    assert agent.ops.approval.required_above_usd == 1000
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/financial/test_create_financial_agent.py -v
```

Expected: FAIL — current `create_financial_agent` returns a plain `Agent`, not `PikarBaseAgent`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/financial/agent.py
# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Financial Analysis Agent — built on PikarBaseAgent."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from app.agents.base_agent import PikarBaseAgent
from app.agents.financial.tools import build_tools_manifest
from app.agents.runtime.operations_config import OperationsConfig
from app.skills.registry import AgentID

_AGENT_DIR = Path(__file__).parent
_INSTRUCTIONS_PATH = _AGENT_DIR / "instructions.md"
_OPS_CONFIG_PATH = _AGENT_DIR / "operations.yaml"


def create_financial_agent(
    *,
    user_id: UUID,
    persona_id: str,
) -> PikarBaseAgent:
    """Build a fresh FinancialAnalysisAgent bound to a user + persona."""
    ops = OperationsConfig.load(_OPS_CONFIG_PATH)
    return PikarBaseAgent(
        agent_id=AgentID.FIN,
        instructions_path=_INSTRUCTIONS_PATH,
        tools_manifest=build_tools_manifest(ops),
        ops_config=ops,
        user_id=user_id,
        persona_id=persona_id,
    )


# Module-level singleton for legacy callers (specialized_agents.py SPECIALIZED_AGENTS list).
# Built lazily so importing this module never requires a user_id binding.
financial_agent = None  # type: ignore[assignment]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/financial/test_create_financial_agent.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/financial/agent.py tests/unit/agents/financial/test_create_financial_agent.py
git commit -m "feat(financial): refactor agent.py onto PikarBaseAgent factory"
```

---

### Task 110: Preserve `specialized_agents.py` re-exports (backward-compat regression test)

**Files:**
- Modify: `app/agents/financial/__init__.py`
- Modify: `app/agents/specialized_agents.py` (only the list filter)
- Test: `tests/unit/agents/financial/test_specialized_agents_backcompat.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/financial/test_specialized_agents_backcompat.py
"""Regression: specialized_agents re-exports must keep working after W2."""


def test_create_financial_agent_reexport_callable():
    from app.agents.specialized_agents import create_financial_agent

    assert callable(create_financial_agent)


def test_financial_agent_symbol_importable_for_legacy_callers():
    """Legacy `from app.agents.specialized_agents import financial_agent` must not raise.

    Behavior change: post-migration the module-level `financial_agent` is `None`
    (lazy-built per-user). Legacy callers that needed a singleton are migrated
    to use `create_financial_agent(user_id=..., persona_id=...)` directly.
    """
    from app.agents.specialized_agents import financial_agent  # noqa: F401


def test_specialized_agents_list_does_not_include_none():
    from app.agents.specialized_agents import SPECIALIZED_AGENTS

    assert all(agent is not None for agent in SPECIALIZED_AGENTS), (
        "SPECIALIZED_AGENTS must not contain None placeholders post-migration"
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/financial/test_specialized_agents_backcompat.py -v
```

Expected: FAIL — `SPECIALIZED_AGENTS` currently contains the now-`None` `financial_agent`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/agents/financial/__init__.py
# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Financial agent package."""

from app.agents.financial.agent import create_financial_agent, financial_agent

__all__ = ["create_financial_agent", "financial_agent"]
```

```python
# app/agents/specialized_agents.py  — patch the SPECIALIZED_AGENTS construction
# (replace the existing literal list with the filtered version)

SPECIALIZED_AGENTS = [
    agent
    for agent in [
        financial_agent,
        content_agent,
        strategic_agent,
        sales_agent,
        marketing_agent,
        operations_agent,
        hr_agent,
        compliance_agent,
        customer_support_agent,
        data_agent,
        data_reporting_agent,
        research_agent,
    ]
    if agent is not None  # financial_agent is None during W2 migration; per-user
                          # instances are built via create_financial_agent(...)
]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/financial/test_specialized_agents_backcompat.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/financial/__init__.py app/agents/specialized_agents.py tests/unit/agents/financial/test_specialized_agents_backcompat.py
git commit -m "fix(financial): preserve specialized_agents re-exports after W2 refactor"
```

---

### Task 111: Contract test — declared `skills.allowed_ids` patterns match real skills

**Files:**
- Test: `tests/unit/agents/financial/test_skills_allowed_ids.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/financial/test_skills_allowed_ids.py
"""Contract test: every pattern in operations.yaml skills.allowed_ids matches a real skill."""

import fnmatch
from pathlib import Path

from app.agents.runtime.operations_config import OperationsConfig
from app.skills.registry import skills_registry

OPS_PATH = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "agents"
    / "financial"
    / "operations.yaml"
)


def _flat_skill_ids() -> list[str]:
    """Return canonical skill ids as `{category}:{name}` strings."""
    ids: list[str] = []
    for skill in skills_registry.all_skills():
        ids.append(f"{skill.category}:{skill.name}")
    return ids


def test_every_allowed_id_pattern_matches_at_least_one_skill():
    ops = OperationsConfig.load(OPS_PATH)
    flat = _flat_skill_ids()
    assert flat, "skills_registry returned no skills — fixture missing"

    unmatched: list[str] = []
    for pattern in ops.skills.allowed_ids:
        if not any(fnmatch.fnmatch(skill_id, pattern) for skill_id in flat):
            unmatched.append(pattern)

    assert not unmatched, (
        f"operations.yaml declares skill patterns with zero matches: {unmatched}"
    )


def test_finance_wildcard_matches_canonical_finance_skills():
    ops = OperationsConfig.load(OPS_PATH)
    flat = _flat_skill_ids()
    finance_hits = [s for s in flat if fnmatch.fnmatch(s, "finance:*")]
    # Tasks 106 and 107 reference these names; if any disappear the agent
    # instructions become stale.
    expected = {
        "finance:financial_statements_generation",
        "finance:variance_analysis",
        "finance:journal_entry_preparation",
        "finance:month_end_close_management",
        "finance:account_reconciliation",
        "finance:sox_testing_methodology",
        "finance:audit_support_framework",
    }
    missing = expected - set(finance_hits)
    assert not missing, f"finance skills disappeared from registry: {missing}"

    # Pattern must be present in ops file
    assert any(p == "finance:*" for p in ops.skills.allowed_ids)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/financial/test_skills_allowed_ids.py -v
```

Expected: PASS on the first run if `skills_registry` is already populated, otherwise FAIL on the wildcard match — which is the bug the contract test exists to catch.

- [ ] **Step 3: Write minimal implementation**

No production-code change required — this is a contract test guarding the existing registry. If the wildcard fails, the fix is to update either `operations.yaml` or the missing skill registration (see Section A).

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/financial/test_skills_allowed_ids.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/agents/financial/test_skills_allowed_ids.py
git commit -m "test(financial): contract-test skill allow-list patterns against registry"
```

---

### Task 112: Integration test — end-to-end `execute_task` for the financial pilot

**Files:**
- Test: `tests/unit/agents/financial/test_execute_task_e2e.py`

This is the load-bearing test from spec § 18 ("Integration tests (one per migrated agent)"). It seeds an initiative + checklist, invokes `execute_task(contract)` with research tools mocked, and asserts the five contract checks from the task spec.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/agents/financial/test_execute_task_e2e.py
"""End-to-end integration test for the financial agent pilot.

Asserts the five W2 contract checks:
  (a) research gate enforced before non-research tool runs
  (b) AuditReport persisted with overall_status='pass'
  (c) vault report emitted via knowledge_service
  (d) WorkspaceArtifactEvent observable on the SSE bus
  (e) agent_task_executions row written with all FK columns populated
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest

from app.agents.financial.agent import create_financial_agent
from app.agents.runtime.research_gate import ResearchGateError
from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    TaskContract,
    WorkspaceArtifactEvent,
)


# ----------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def initiative_id() -> UUID:
    return uuid4()


@pytest.fixture
def contract(user_id: UUID, initiative_id: UUID) -> TaskContract:
    """A realistic single-step TaskContract for the financial agent."""
    return TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="Produce a 6-month revenue forecast for FY26 H1 with confidence intervals.",
        todo_items=[
            {
                "id": str(uuid4()),
                "title": "Pull 12 months of historical revenue from FinancialService.",
                "status": "pending",
            },
            {
                "id": str(uuid4()),
                "title": "Run generate_financial_forecast(months_ahead=6).",
                "status": "pending",
            },
            {
                "id": str(uuid4()),
                "title": "Annotate the forecast with confidence band and risks.",
                "status": "pending",
            },
        ],
        success_criteria=[
            "Forecast covers 6 future months.",
            "Confidence level reported for each month.",
            "At least 3 sources cited if external data is used.",
        ],
        owners=["FIN"],
        evidence_required=["research_summary", "draft_artifact", "audit_report"],
        initiative_id=initiative_id,
        initiative_phase="validation",
        sibling_steps=[],
    )


@pytest.fixture
def captured_workspace_events() -> list[WorkspaceArtifactEvent]:
    return []


@pytest.fixture
def captured_vault_docs() -> list[dict]:
    return []


# ----------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_research_gate_blocks_non_research_tools(
    user_id: UUID, contract: TaskContract
):
    """(a) Calling a non-research tool before research completes raises ResearchGateError."""
    agent = create_financial_agent(user_id=user_id, persona_id="startup")

    # Open a research run but do not complete it.
    await agent._open_research_gate(contract)

    with pytest.raises(ResearchGateError):
        await agent._invoke_tool(
            tool_name="generate_financial_forecast",
            kwargs={"months_ahead": 6},
            contract=contract,
        )


@pytest.mark.asyncio
async def test_execute_task_writes_passing_audit_report(
    user_id: UUID, contract: TaskContract
):
    """(b) After a successful run, an AuditReport with overall_status='pass' is persisted."""
    agent = create_financial_agent(user_id=user_id, persona_id="startup")

    mocked_research = {
        "summary": "FY25 revenue grew 12% QoQ; Stripe data covers 14 months.",
        "sources": [
            {"url": "https://internal/finance/q4", "title": "Q4", "key_claim": "rev up", "retrieved_at": datetime.now(timezone.utc).isoformat()},
            {"url": "https://internal/finance/q3", "title": "Q3", "key_claim": "rev up", "retrieved_at": datetime.now(timezone.utc).isoformat()},
            {"url": "https://internal/finance/q2", "title": "Q2", "key_claim": "rev up", "retrieved_at": datetime.now(timezone.utc).isoformat()},
        ],
        "contradictions": [],
        "coverage_assessment": "complete",
        "missing_information": [],
    }

    saved_audit: list[AuditReport] = []

    async def _capture_audit_persist(report: AuditReport, **_kwargs) -> AuditReport:
        saved_audit.append(report)
        return report

    with (
        patch(
            "app.agents.runtime.research_gate.run_research_to_completion",
            new=AsyncMock(return_value=mocked_research),
        ),
        patch(
            "app.agents.runtime.audit.persist_audit_report",
            new=AsyncMock(side_effect=_capture_audit_persist),
        ),
        patch(
            "app.agents.runtime.audit.audit_against_contract",
            new=AsyncMock(
                return_value=AuditReport(
                    overall_status="pass",
                    per_item=[{"item_id": item["id"], "status": "pass", "evidence_pointers": [], "gaps": []} for item in contract.todo_items],
                    per_criterion=[{"criterion": c, "met": True, "justification": "ok"} for c in contract.success_criteria],
                    gaps=[],
                    policy_violations=[],
                    recoverable=True,
                    next_action="submit",
                )
            ),
        ),
        patch("app.agents.runtime.publication.publish_artifact", new=AsyncMock()),
    ):
        result = await agent.execute_task(contract)

    assert result.status == "submitted"
    assert len(saved_audit) == 1
    assert saved_audit[0].overall_status == "pass"


@pytest.mark.asyncio
async def test_execute_task_emits_vault_report(
    user_id: UUID,
    contract: TaskContract,
    captured_vault_docs: list[dict],
):
    """(c) On submission, a markdown report is added to the knowledge vault."""
    agent = create_financial_agent(user_id=user_id, persona_id="startup")

    async def _capture_add_document(**kwargs) -> dict:
        captured_vault_docs.append(kwargs)
        return {"id": str(uuid4()), **kwargs}

    pass_audit = AuditReport(
        overall_status="pass",
        per_item=[],
        per_criterion=[],
        gaps=[],
        policy_violations=[],
        recoverable=True,
        next_action="submit",
    )

    with (
        patch(
            "app.agents.runtime.research_gate.run_research_to_completion",
            new=AsyncMock(return_value={"summary": "ok", "sources": [], "contradictions": [], "coverage_assessment": "complete", "missing_information": []}),
        ),
        patch(
            "app.agents.runtime.audit.audit_against_contract",
            new=AsyncMock(return_value=pass_audit),
        ),
        patch("app.agents.runtime.audit.persist_audit_report", new=AsyncMock(return_value=pass_audit)),
        patch(
            "app.services.knowledge_service.add_document",
            new=AsyncMock(side_effect=_capture_add_document),
        ),
        patch("app.services.workspace_event_bus.publish", new=AsyncMock()),
    ):
        await agent.execute_task(contract)

    assert len(captured_vault_docs) == 1, (
        f"expected one vault report, got {len(captured_vault_docs)}: {captured_vault_docs}"
    )
    doc = captured_vault_docs[0]
    assert doc["metadata"]["kind"] == "agent_report"
    assert doc["metadata"]["agent_id"] == "FIN"
    assert doc["metadata"]["initiative_id"] == str(contract.initiative_id)
    assert doc["metadata"]["contract_id"] == str(contract.id)
    assert "Financial" in doc["title"] or "FIN" in doc["title"]


@pytest.mark.asyncio
async def test_execute_task_emits_workspace_artifact_event(
    user_id: UUID,
    contract: TaskContract,
    captured_workspace_events: list[WorkspaceArtifactEvent],
):
    """(d) A WorkspaceArtifactEvent is published to the user's SSE channel."""
    agent = create_financial_agent(user_id=user_id, persona_id="startup")

    async def _capture_publish(channel: str, event):
        if isinstance(event, WorkspaceArtifactEvent):
            captured_workspace_events.append(event)

    pass_audit = AuditReport(
        overall_status="pass",
        per_item=[],
        per_criterion=[],
        gaps=[],
        policy_violations=[],
        recoverable=True,
        next_action="submit",
    )

    with (
        patch(
            "app.agents.runtime.research_gate.run_research_to_completion",
            new=AsyncMock(return_value={"summary": "ok", "sources": [], "contradictions": [], "coverage_assessment": "complete", "missing_information": []}),
        ),
        patch(
            "app.agents.runtime.audit.audit_against_contract",
            new=AsyncMock(return_value=pass_audit),
        ),
        patch("app.agents.runtime.audit.persist_audit_report", new=AsyncMock(return_value=pass_audit)),
        patch("app.services.knowledge_service.add_document", new=AsyncMock(return_value={"id": str(uuid4())})),
        patch(
            "app.services.workspace_event_bus.publish",
            new=AsyncMock(side_effect=_capture_publish),
        ),
    ):
        await agent.execute_task(contract)

    assert captured_workspace_events, "no WorkspaceArtifactEvent observed on SSE bus"
    event = captured_workspace_events[0]
    assert event.agent_id == "FIN"
    assert str(contract.id) in (event.contract_id or "") if event.contract_id else True
    assert event.artifact_kind in {"report", "doc", "image", "video_render"}


@pytest.mark.asyncio
async def test_execute_task_persists_agent_task_execution_row(
    user_id: UUID, contract: TaskContract
):
    """(e) An agent_task_executions row is written with all FK columns populated."""
    captured_rows: list[dict] = []

    async def _capture_upsert(table_name: str, payload: dict, **_kwargs) -> dict:
        if table_name == "agent_task_executions":
            captured_rows.append(payload)
        return {**payload, "id": str(uuid4())}

    agent = create_financial_agent(user_id=user_id, persona_id="startup")
    pass_audit = AuditReport(
        overall_status="pass",
        per_item=[],
        per_criterion=[],
        gaps=[],
        policy_violations=[],
        recoverable=True,
        next_action="submit",
    )

    with (
        patch(
            "app.agents.runtime.research_gate.run_research_to_completion",
            new=AsyncMock(return_value={"summary": "ok", "sources": [], "contradictions": [], "coverage_assessment": "complete", "missing_information": []}),
        ),
        patch(
            "app.agents.runtime.audit.audit_against_contract",
            new=AsyncMock(return_value=pass_audit),
        ),
        patch(
            "app.agents.runtime.audit.persist_audit_report",
            new=AsyncMock(return_value=pass_audit.model_copy(update={"id": uuid4()})),
        ),
        patch(
            "app.services.knowledge_service.add_document",
            new=AsyncMock(return_value={"id": str(uuid4())}),
        ),
        patch("app.services.workspace_event_bus.publish", new=AsyncMock()),
        patch(
            "app.agents.runtime.publication._supabase_upsert",
            new=AsyncMock(side_effect=_capture_upsert),
        ),
    ):
        await agent.execute_task(contract)

    assert captured_rows, "expected one agent_task_executions upsert"
    row = captured_rows[-1]
    assert row["user_id"] == str(user_id)
    assert row["agent_id"] == "FIN"
    assert row["persona_id"] == "startup"
    assert row["mode"] == "initiative"
    assert row["contract_id"] == str(contract.id)
    assert row["contract_source"] == "initiative_step"
    assert row["initiative_id"] == str(contract.initiative_id)
    assert row["status"] == "submitted"
    assert row["research_run_id"] is not None
    assert row["audit_report_id"] is not None
    assert row["vault_document_id"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/agents/financial/test_execute_task_e2e.py -v
```

Expected: FAIL — the five contract assertions surface gaps between the runtime stubs delivered in Sections A–D and the financial pilot wiring.

- [ ] **Step 3: Write minimal implementation**

No new financial-agent code is required for this task; the failures point at integration glue in `PikarBaseAgent.execute_task`, `runtime/publication.py`, and `runtime/research_gate.py`. Fix forward in those modules until all five assertions pass — the financial pilot is the canary, not the patient.

If any assertion exposes a structural gap in the contract types from Section A (for example `WorkspaceArtifactEvent.contract_id` typed as `UUID | None` vs string serialisation), file the fix into the Section A module and reference it from the failing diff.

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/agents/financial/test_execute_task_e2e.py -v
```

Expected: PASS — five contract checks satisfied; the W2 risk gate from spec § 17 is met.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/agents/financial/test_execute_task_e2e.py
git commit -m "test(financial): e2e contract for execute_task — research gate, audit, vault, SSE, history"
```

---

### Task 113: TypeScript type module — `WorkspaceEvent`

**Files:**
- Create: `frontend/src/types/workspace-events.ts`
- Test: `frontend/src/types/workspace-events.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/types/workspace-events.test.ts
import { describe, it, expect } from 'vitest';
import type {
    WorkspaceEvent,
    WorkspaceProgressEvent,
    WorkspaceArtifactEvent,
} from './workspace-events';

describe('WorkspaceEvent discriminated union', () => {
    it('narrows on kind === "progress"', () => {
        const event: WorkspaceEvent = {
            kind: 'progress',
            agent_id: 'FIN',
            contract_id: '00000000-0000-0000-0000-000000000001',
            item: 'Pull 12 months of revenue',
            status: 'in_progress',
        };
        if (event.kind === 'progress') {
            const narrowed: WorkspaceProgressEvent = event;
            expect(narrowed.status).toBe('in_progress');
        }
    });

    it('narrows on kind === "artifact"', () => {
        const event: WorkspaceEvent = {
            kind: 'artifact',
            agent_id: 'FIN',
            contract_id: null,
            artifact_kind: 'report',
            ref: 'vault://doc/123',
            summary: 'FY26 forecast',
            preview_url: null,
        };
        if (event.kind === 'artifact') {
            const narrowed: WorkspaceArtifactEvent = event;
            expect(narrowed.artifact_kind).toBe('report');
        }
    });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npm test -- workspace-events
```

Expected: FAIL — module does not exist.

- [ ] **Step 3: Write minimal implementation**

```ts
// frontend/src/types/workspace-events.ts
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

export type WorkspaceProgressEvent = {
    kind: 'progress';
    agent_id: string;
    contract_id: string | null;
    item: string;
    status: 'started' | 'in_progress' | 'blocked';
};

export type WorkspaceArtifactEvent = {
    kind: 'artifact';
    agent_id: string;
    contract_id: string | null;
    artifact_kind: string;
    ref: string;
    summary: string;
    preview_url: string | null;
};

export type WorkspaceEvent = WorkspaceProgressEvent | WorkspaceArtifactEvent;
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm test -- workspace-events
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/workspace-events.ts frontend/src/types/workspace-events.test.ts
git commit -m "feat(frontend): add WorkspaceEvent types for SSE consumer"
```

---

### Task 114: `useWorkspaceEvents` hook (EventSource consumer)

**Files:**
- Create: `frontend/src/hooks/useWorkspaceEvents.ts`
- Test: `frontend/src/hooks/useWorkspaceEvents.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/hooks/useWorkspaceEvents.test.tsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useWorkspaceEvents } from './useWorkspaceEvents';
import type { WorkspaceEvent } from '@/types/workspace-events';

class FakeEventSource {
    public onmessage: ((evt: MessageEvent) => void) | null = null;
    public onerror: ((evt: Event) => void) | null = null;
    public close = vi.fn();
    constructor(public url: string) {
        FakeEventSource.instances.push(this);
    }
    static instances: FakeEventSource[] = [];
    static reset() {
        FakeEventSource.instances = [];
    }
}

describe('useWorkspaceEvents', () => {
    beforeEach(() => {
        FakeEventSource.reset();
        // @ts-expect-error patch global
        global.EventSource = FakeEventSource;
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('opens an EventSource against /api/workspace/events', () => {
        renderHook(() => useWorkspaceEvents());
        expect(FakeEventSource.instances).toHaveLength(1);
        expect(FakeEventSource.instances[0].url).toBe('/api/workspace/events');
    });

    it('appends incoming events in order', () => {
        const { result } = renderHook(() => useWorkspaceEvents());
        const source = FakeEventSource.instances[0];

        const a: WorkspaceEvent = {
            kind: 'progress', agent_id: 'FIN', contract_id: null, item: 'step', status: 'started',
        };
        const b: WorkspaceEvent = {
            kind: 'artifact', agent_id: 'FIN', contract_id: null,
            artifact_kind: 'report', ref: 'vault://1', summary: 's', preview_url: null,
        };

        act(() => {
            source.onmessage?.({ data: JSON.stringify(a) } as MessageEvent);
            source.onmessage?.({ data: JSON.stringify(b) } as MessageEvent);
        });

        expect(result.current).toHaveLength(2);
        expect(result.current[0]).toEqual(a);
        expect(result.current[1]).toEqual(b);
    });

    it('closes the EventSource on unmount', () => {
        const { unmount } = renderHook(() => useWorkspaceEvents());
        const source = FakeEventSource.instances[0];
        unmount();
        expect(source.close).toHaveBeenCalledTimes(1);
    });

    it('ignores malformed payloads instead of crashing', () => {
        const { result } = renderHook(() => useWorkspaceEvents());
        const source = FakeEventSource.instances[0];

        const spy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        act(() => {
            source.onmessage?.({ data: '{not-json' } as MessageEvent);
        });
        expect(result.current).toEqual([]);
        expect(spy).toHaveBeenCalled();
    });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npm test -- useWorkspaceEvents
```

Expected: FAIL — hook module does not exist.

- [ ] **Step 3: Write minimal implementation**

```ts
// frontend/src/hooks/useWorkspaceEvents.ts
'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useEffect, useState } from 'react';
import type { WorkspaceEvent } from '@/types/workspace-events';

const ENDPOINT = '/api/workspace/events';

/**
 * Subscribe to the per-user workspace SSE channel and accumulate events.
 *
 * Reconnect is delegated to EventSource's native retry loop. Malformed
 * payloads are logged and skipped — a bad frame must never crash the canvas.
 */
export function useWorkspaceEvents(): WorkspaceEvent[] {
    const [events, setEvents] = useState<WorkspaceEvent[]>([]);

    useEffect(() => {
        const source = new EventSource(ENDPOINT);

        source.onmessage = (e: MessageEvent) => {
            try {
                const parsed = JSON.parse(e.data) as WorkspaceEvent;
                if (parsed && (parsed.kind === 'progress' || parsed.kind === 'artifact')) {
                    setEvents((prev) => [...prev, parsed]);
                } else {
                    console.warn('[useWorkspaceEvents] dropping event with unknown kind', parsed);
                }
            } catch (err) {
                console.warn('[useWorkspaceEvents] dropping malformed payload', err);
            }
        };

        source.onerror = (err: Event) => {
            // EventSource auto-reconnects; surface the warning once so we can
            // notice a long-lived disconnect without flooding the console.
            console.warn('[useWorkspaceEvents] SSE error', err);
        };

        return () => {
            source.close();
        };
    }, []);

    return events;
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm test -- useWorkspaceEvents
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useWorkspaceEvents.ts frontend/src/hooks/useWorkspaceEvents.test.tsx
git commit -m "feat(frontend): useWorkspaceEvents SSE consumer hook"
```

---

### Task 115: `WorkspaceArtifactCard` — preview-aware artifact card

**Files:**
- Create: `frontend/src/components/workspace/WorkspaceArtifactCard.tsx`
- Test: `frontend/src/components/workspace/WorkspaceArtifactCard.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/workspace/WorkspaceArtifactCard.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { WorkspaceArtifactCard } from './WorkspaceArtifactCard';
import type { WorkspaceArtifactEvent } from '@/types/workspace-events';

function fixture(over: Partial<WorkspaceArtifactEvent> = {}): WorkspaceArtifactEvent {
    return {
        kind: 'artifact',
        agent_id: 'FIN',
        contract_id: 'c-1',
        artifact_kind: 'report',
        ref: 'vault://abc',
        summary: 'FY26 H1 forecast',
        preview_url: null,
        ...over,
    };
}

describe('WorkspaceArtifactCard', () => {
    it('renders the summary and agent badge', () => {
        render(<WorkspaceArtifactCard event={fixture()} />);
        expect(screen.getByText('FY26 H1 forecast')).toBeInTheDocument();
        expect(screen.getByText(/FIN/)).toBeInTheDocument();
    });

    it('renders an <img> preview for image artifacts', () => {
        render(
            <WorkspaceArtifactCard
                event={fixture({ artifact_kind: 'image', preview_url: 'https://cdn/x.png' })}
            />,
        );
        const img = screen.getByRole('img', { name: /FY26 H1 forecast/i }) as HTMLImageElement;
        expect(img.src).toContain('https://cdn/x.png');
    });

    it('renders a <video> preview for video_render artifacts', () => {
        render(
            <WorkspaceArtifactCard
                event={fixture({ artifact_kind: 'video_render', preview_url: 'https://cdn/x.mp4' })}
            />,
        );
        const video = screen.getByTestId('artifact-preview-video') as HTMLVideoElement;
        expect(video.src).toContain('https://cdn/x.mp4');
    });

    it('renders a doc icon for doc/report artifacts without a preview', () => {
        render(<WorkspaceArtifactCard event={fixture({ artifact_kind: 'doc' })} />);
        expect(screen.getByTestId('artifact-doc-icon')).toBeInTheDocument();
    });

    it('exposes the vault ref as a link', () => {
        render(<WorkspaceArtifactCard event={fixture({ ref: 'vault://abc' })} />);
        const link = screen.getByRole('link', { name: /open/i }) as HTMLAnchorElement;
        expect(link.href).toContain('vault://abc');
    });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npm test -- WorkspaceArtifactCard
```

Expected: FAIL — component does not exist.

- [ ] **Step 3: Write minimal implementation**

```tsx
// frontend/src/components/workspace/WorkspaceArtifactCard.tsx
'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React from 'react';
import { FileText, FileVideo, FileImage, FileQuestion } from 'lucide-react';
import type { WorkspaceArtifactEvent } from '@/types/workspace-events';

interface Props {
    event: WorkspaceArtifactEvent;
}

const IMAGE_KINDS = new Set(['image']);
const VIDEO_KINDS = new Set(['video_render', 'video']);
const DOC_KINDS = new Set(['doc', 'report']);

function DocIcon({ kind }: { kind: string }) {
    if (kind === 'doc') return <FileText size={20} data-testid="artifact-doc-icon" aria-hidden="true" />;
    if (kind === 'report') return <FileText size={20} data-testid="artifact-doc-icon" aria-hidden="true" />;
    if (kind === 'image') return <FileImage size={20} aria-hidden="true" />;
    if (kind === 'video_render' || kind === 'video') return <FileVideo size={20} aria-hidden="true" />;
    return <FileQuestion size={20} aria-hidden="true" />;
}

export function WorkspaceArtifactCard({ event }: Props) {
    const { artifact_kind, preview_url, summary, agent_id, ref } = event;

    let preview: React.ReactNode = null;
    if (preview_url && IMAGE_KINDS.has(artifact_kind)) {
        preview = (
            <img
                src={preview_url}
                alt={summary}
                className="w-full rounded-xl object-cover max-h-72"
            />
        );
    } else if (preview_url && VIDEO_KINDS.has(artifact_kind)) {
        preview = (
            <video
                src={preview_url}
                controls
                data-testid="artifact-preview-video"
                className="w-full rounded-xl max-h-72"
            />
        );
    } else if (DOC_KINDS.has(artifact_kind)) {
        preview = (
            <div className="flex items-center gap-3 rounded-xl bg-slate-50 p-4 text-slate-600">
                <DocIcon kind={artifact_kind} />
                <span className="text-sm capitalize">{artifact_kind}</span>
            </div>
        );
    }

    return (
        <article
            className="flex flex-col gap-3 rounded-2xl border border-slate-100 bg-white p-4 shadow-sm"
            data-testid="workspace-artifact-card"
            data-artifact-kind={artifact_kind}
        >
            <header className="flex items-center justify-between">
                <span
                    className="rounded-full bg-teal-50 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider text-teal-700"
                    aria-label={`agent ${agent_id}`}
                >
                    {agent_id}
                </span>
                <span className="text-[11px] uppercase tracking-wider text-slate-400">
                    {artifact_kind.replace('_', ' ')}
                </span>
            </header>
            {preview}
            <p className="text-sm text-slate-700">{summary}</p>
            <a
                href={ref}
                rel="noreferrer noopener"
                className="text-xs font-semibold text-teal-700 hover:underline"
            >
                Open
            </a>
        </article>
    );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm test -- WorkspaceArtifactCard
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/workspace/WorkspaceArtifactCard.tsx frontend/src/components/workspace/WorkspaceArtifactCard.test.tsx
git commit -m "feat(frontend): WorkspaceArtifactCard with image/video/doc previews"
```

---

### Task 116: Wire `useWorkspaceEvents` into `ActiveWorkspace`

**Files:**
- Modify: `frontend/src/components/dashboard/ActiveWorkspace.tsx`
- Test: `frontend/src/components/dashboard/ActiveWorkspace.events.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/dashboard/ActiveWorkspace.events.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { ActiveWorkspace } from './ActiveWorkspace';
import { SessionControlContext } from '@/contexts/SessionControlContext';
import type { WorkspaceEvent } from '@/types/workspace-events';

// Mock the hook so the test does not need a live EventSource.
const mockEvents: WorkspaceEvent[] = [];
vi.mock('@/hooks/useWorkspaceEvents', () => ({
    useWorkspaceEvents: () => mockEvents,
}));

// Stub supabase + child components to keep the test focused on the SSE section.
vi.mock('@/lib/supabase/client', () => ({
    createClient: () => ({
        auth: { getUser: async () => ({ data: { user: { id: 'u-1', user_metadata: {}, email: 'a@b.c' } } }) },
        from: () => ({ delete: () => ({ eq: () => ({ eq: () => ({ error: null }) }) }) }),
    }),
}));
vi.mock('@/components/dashboard/DashboardBriefCard', () => ({ DashboardBriefCard: () => null }));
vi.mock('@/components/dashboard/OnboardingChecklist', () => ({ default: () => null }));
vi.mock('@/components/workspace/WorkspaceCanvas', () => ({ WorkspaceCanvas: () => null }));

function renderWithSession() {
    return render(
        <SessionControlContext.Provider
            value={{
                visibleSessionId: 's-1',
                activeSessionId: 's-1',
                setActiveSessionId: () => {},
                clearSession: () => {},
            } as unknown as React.ContextType<typeof SessionControlContext>}
        >
            <ActiveWorkspace persona="startup" />
        </SessionControlContext.Provider>,
    );
}

describe('ActiveWorkspace SSE artifact rendering', () => {
    it('renders artifact cards for every artifact event from the hook', async () => {
        mockEvents.length = 0;
        mockEvents.push(
            { kind: 'progress', agent_id: 'FIN', contract_id: null, item: 'p', status: 'started' },
            {
                kind: 'artifact',
                agent_id: 'FIN',
                contract_id: 'c-1',
                artifact_kind: 'report',
                ref: 'vault://1',
                summary: 'FY26 forecast',
                preview_url: null,
            },
            {
                kind: 'artifact',
                agent_id: 'CONT',
                contract_id: 'c-2',
                artifact_kind: 'image',
                ref: 'vault://2',
                summary: 'Launch hero',
                preview_url: 'https://cdn/hero.png',
            },
        );

        await act(async () => {
            renderWithSession();
        });

        const cards = screen.getAllByTestId('workspace-artifact-card');
        expect(cards).toHaveLength(2);
        expect(screen.getByText('FY26 forecast')).toBeInTheDocument();
        expect(screen.getByText('Launch hero')).toBeInTheDocument();
    });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npm test -- ActiveWorkspace.events
```

Expected: FAIL — `ActiveWorkspace` does not yet render SSE artifact cards.

- [ ] **Step 3: Write minimal implementation**

```tsx
// frontend/src/components/dashboard/ActiveWorkspace.tsx  (additions)

// 1. Add imports (top of file):
import { useWorkspaceEvents } from '@/hooks/useWorkspaceEvents';
import { WorkspaceArtifactCard } from '@/components/workspace/WorkspaceArtifactCard';
import type { WorkspaceArtifactEvent } from '@/types/workspace-events';

// 2. Inside the ActiveWorkspace function body (above the `return (` statement):
const sseEvents = useWorkspaceEvents();
const artifactEvents = useMemo<WorkspaceArtifactEvent[]>(
    () => sseEvents.filter((event): event is WorkspaceArtifactEvent => event.kind === 'artifact'),
    [sseEvents],
);

// 3. Insert this block in the JSX between the `WorkspaceCanvas` motion.div and
//    the `!isAgentWorking` block:
{artifactEvents.length > 0 && (
    <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-3"
        aria-label="Live agent artifacts"
    >
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
            Live agent artifacts
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {artifactEvents.map((event, idx) => (
                <WorkspaceArtifactCard key={`${event.ref}-${idx}`} event={event} />
            ))}
        </div>
    </motion.section>
)}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm test -- ActiveWorkspace.events
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dashboard/ActiveWorkspace.tsx frontend/src/components/dashboard/ActiveWorkspace.events.test.tsx
git commit -m "feat(frontend): subscribe ActiveWorkspace to /workspace/events SSE bus"
```

---

### Task 117: Frontend `/api/workspace/events` proxy to the FastAPI SSE endpoint

**Files:**
- Create: `frontend/src/app/api/workspace/events/route.ts`
- Test: `frontend/src/app/api/workspace/events/route.test.ts`

The hook in Task 114 points at the Next.js origin (`/api/workspace/events`). The backend SSE endpoint from Section D lives at `${API_URL}/workspace/events`. This task threads them.

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/app/api/workspace/events/route.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { GET } from './route';

describe('GET /api/workspace/events', () => {
    beforeEach(() => {
        process.env.NEXT_PUBLIC_API_URL = 'https://api.example.com';
        vi.restoreAllMocks();
    });

    it('proxies to the backend SSE endpoint with text/event-stream content-type', async () => {
        const upstream = new Response(new ReadableStream(), {
            status: 200,
            headers: { 'content-type': 'text/event-stream' },
        });
        const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(upstream);

        const req = new Request('http://localhost/api/workspace/events', {
            headers: { cookie: 'sb-session=abc' },
        });
        const res = await GET(req as unknown as Request);
        expect(res.headers.get('content-type')).toBe('text/event-stream');
        expect(fetchSpy).toHaveBeenCalledWith(
            'https://api.example.com/workspace/events',
            expect.objectContaining({
                method: 'GET',
                headers: expect.any(Object),
            }),
        );
    });

    it('returns 502 if the upstream is unreachable', async () => {
        vi.spyOn(global, 'fetch').mockRejectedValue(new Error('connection refused'));
        const req = new Request('http://localhost/api/workspace/events');
        const res = await GET(req as unknown as Request);
        expect(res.status).toBe(502);
    });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npm test -- "app/api/workspace/events"
```

Expected: FAIL — route does not exist.

- [ ] **Step 3: Write minimal implementation**

```ts
// frontend/src/app/api/workspace/events/route.ts
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const BACKEND_URL =
    process.env.WORKSPACE_EVENTS_BACKEND_URL
    || process.env.NEXT_PUBLIC_API_URL
    || 'http://127.0.0.1:8000';

export async function GET(req: Request): Promise<Response> {
    const upstreamUrl = `${BACKEND_URL.replace(/\/$/, '')}/workspace/events`;

    const headers: Record<string, string> = {
        accept: 'text/event-stream',
    };
    const cookie = req.headers.get('cookie');
    if (cookie) headers.cookie = cookie;
    const auth = req.headers.get('authorization');
    if (auth) headers.authorization = auth;

    try {
        const upstream = await fetch(upstreamUrl, {
            method: 'GET',
            headers,
            // SSE streams must not be cached or buffered.
            cache: 'no-store',
        });

        if (!upstream.ok || !upstream.body) {
            return NextResponse.json(
                { error: `upstream returned ${upstream.status}` },
                { status: upstream.status || 502 },
            );
        }

        return new Response(upstream.body, {
            status: 200,
            headers: {
                'content-type': 'text/event-stream',
                'cache-control': 'no-cache, no-transform',
                connection: 'keep-alive',
                'x-accel-buffering': 'no',
            },
        });
    } catch (err) {
        return NextResponse.json(
            { error: 'workspace events upstream unavailable', detail: String(err) },
            { status: 502 },
        );
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm test -- "app/api/workspace/events"
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/api/workspace/events/route.ts frontend/src/app/api/workspace/events/route.test.ts
git commit -m "feat(frontend): proxy /api/workspace/events to FastAPI SSE bus"
```

---

### Closing notes for Section E

After Tasks 106–117 land:

- **W2 risk gate (spec § 17) is met:** the financial pilot runs an initiative step end-to-end with the research gate, audit, vault report, workspace SSE event, and `agent_task_executions` history row all wired and tested (Task 112).
- **Backward compatibility:** `app.agents.specialized_agents.create_financial_agent` and the `financial_agent` symbol still import; the `SPECIALIZED_AGENTS` list silently skips the now-lazy financial entry. Other agents continue to use their legacy module-level singletons until W3 migrates them (Tasks 110, regression test).
- **Frontend canvas:** every `WorkspaceArtifactEvent` emitted by the financial pilot (and by any agent migrated in later waves) renders an inline preview card. The video-director / graphic-agent fix from spec § 12 is now structural — no per-agent UI work required.
- **Reserved task slots 118–130:** kept open for additional financial-pilot integration tasks raised during execution (for example a separate workspace `progress` strip if telemetry deems it necessary, or a feature-flag rollout shim if the runtime forces a feature gate). Do not pad with speculative work — promote them as defects fall out of Task 112 during execution.
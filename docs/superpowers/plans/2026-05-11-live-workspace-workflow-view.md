# Live Workspace Workflow View — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-spawn a live workflow view in the workspace whenever a workflow runs; render goal, per-step outcomes, and inline approval UX for human-gated steps.

**Architecture:** Enhance the existing `WorkflowTimelineWidget` and inject a workspace_item from `WorkflowEngine.start_workflow()`. New services (`WorkspaceItemEmitter`, `OutcomeWriter`) and a background `OutcomeSummaryWorker` keep responsibilities separated. SSE drives live updates; no new layout machinery.

**Tech Stack:** Python 3.10+ / FastAPI / asyncpg / Supabase (Postgres). React 19 / Next.js 16 / TypeScript / Vitest. Google ADK / Gemini 2.5 Flash for outcome summarization.

**Source spec:** `docs/superpowers/specs/2026-05-11-live-workspace-workflow-view-design.md`

---

## File Map

**Created:**
- `supabase/migrations/20260511130000_workflow_run_view.sql` — schema additions
- `app/services/workspace_items.py` — `WorkspaceItemEmitter.emit_for_execution()`
- `app/workflows/outcome_writer.py` — `OutcomeWriter.write_for_step()`
- `app/workflows/outcome_summary_worker.py` — background LLM filler
- `app/services/workspace_items_cleanup.py` — daily archive job
- `tests/unit/services/test_workspace_items.py`
- `tests/unit/workflows/test_outcome_writer.py`
- `tests/unit/workflows/test_outcome_summary_worker.py`
- `tests/unit/services/test_workspace_items_cleanup.py`
- `tests/integration/test_live_workflow_view.py`
- `frontend/src/services/workflowExecutionStream.ts` — SSE subscription helper

**Modified:**
- `app/workflows/engine.py` — `start_workflow()` accepts `goal`, calls emitter
- `app/workflows/step_executor.py` — calls `OutcomeWriter`, emits SSE events
- `app/routers/workflows.py` — new SSE endpoint `/executions/{id}/stream`
- `app/config/settings.py` — `LIVE_WORKFLOW_VIEW` feature flag
- `frontend/src/components/widgets/WorkflowTimelineWidget.tsx` — goal header, outcome rendering, inline approval, collapsed-strip, SSE wiring

---

## Phase 1 — Schema

### Task 1: Migration for goal, outcome_text, outcome_source, archived_at

**Files:**
- Create: `supabase/migrations/20260511130000_workflow_run_view.sql`

- [ ] **Step 1: Write the migration**

```sql
-- Migration: 20260511130000_workflow_run_view.sql
-- Adds columns + indices for the Live Workspace Workflow View.
-- Spec: docs/superpowers/specs/2026-05-11-live-workspace-workflow-view-design.md

ALTER TABLE workflow_executions
    ADD COLUMN IF NOT EXISTS goal TEXT;
COMMENT ON COLUMN workflow_executions.goal IS
    'User-facing goal for this run (e.g. the original chat request). Populated at start.';

ALTER TABLE workflow_steps
    ADD COLUMN IF NOT EXISTS outcome_text TEXT,
    ADD COLUMN IF NOT EXISTS outcome_source TEXT
        CHECK (outcome_source IS NULL OR outcome_source IN ('tool', 'llm', 'status'));
COMMENT ON COLUMN workflow_steps.outcome_text IS
    'One-sentence human-readable summary of what the step accomplished.';
COMMENT ON COLUMN workflow_steps.outcome_source IS
    'Provenance of outcome_text: tool=returned by tool, llm=synthesized post-hoc, status=deterministic fallback.';

ALTER TABLE workspace_items
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
COMMENT ON COLUMN workspace_items.archived_at IS
    'When the item was moved off the active canvas. NULL = still active.';

CREATE INDEX IF NOT EXISTS idx_workflow_steps_outcome_pending
    ON workflow_steps (workflow_execution_id)
    WHERE status = 'completed' AND outcome_text IS NULL;

CREATE INDEX IF NOT EXISTS idx_workspace_items_active
    ON workspace_items (user_id)
    WHERE archived_at IS NULL;
```

- [ ] **Step 2: Apply locally and verify**

Run: `supabase db push --local`
Expected: `Applying migration 20260511130000_workflow_run_view.sql... done`

Then verify columns exist:
```bash
supabase inspect db schema workflow_executions --linked | grep -i goal
supabase inspect db schema workflow_steps --linked | grep -i outcome
supabase inspect db schema workspace_items --linked | grep -i archived
```
Expected: each grep returns a matching row.

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/20260511130000_workflow_run_view.sql
git commit -m "feat(schema): add goal, outcome_text, archived_at for live workflow view"
```

---

## Phase 2 — Backend services

### Task 2: WorkspaceItemEmitter service

**Files:**
- Create: `app/services/workspace_items.py`
- Test: `tests/unit/services/test_workspace_items.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/services/test_workspace_items.py
"""Unit tests for WorkspaceItemEmitter."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.workspace_items import WorkspaceItemEmitter


@pytest.fixture
def mock_client():
    """Mock Supabase client where .table().upsert().execute() is awaitable."""
    client = MagicMock()
    upsert_mock = AsyncMock(return_value=MagicMock(data=[{"id": "ws-1"}]))
    client.table.return_value.upsert.return_value.execute = upsert_mock
    return client


@pytest.mark.asyncio
async def test_emits_focus_for_user_ui_run_source(mock_client):
    emitter = WorkspaceItemEmitter(client=mock_client)
    await emitter.emit_for_execution(
        execution={"id": "exec-1", "user_id": "u-1", "name": "Marketing Plan"},
        run_source="user_ui",
    )
    payload = mock_client.table.return_value.upsert.call_args[0][0]
    assert payload["widget_type"] == "workflow_timeline"
    assert payload["workflow_execution_id"] == "exec-1"
    assert payload["layout_mode"] == "focus"
    assert payload["widget_payload"]["interactive"] is True


@pytest.mark.asyncio
async def test_emits_embedded_for_scheduler_run_source(mock_client):
    emitter = WorkspaceItemEmitter(client=mock_client)
    await emitter.emit_for_execution(
        execution={"id": "exec-2", "user_id": "u-1", "name": "Cron Job"},
        run_source="scheduler",
    )
    payload = mock_client.table.return_value.upsert.call_args[0][0]
    assert payload["layout_mode"] == "embedded"
    assert payload["widget_payload"]["interactive"] is False


@pytest.mark.asyncio
async def test_swallows_upsert_failure(mock_client, caplog):
    mock_client.table.return_value.upsert.return_value.execute.side_effect = RuntimeError("boom")
    emitter = WorkspaceItemEmitter(client=mock_client)
    # Should not raise — graceful degradation per spec.
    await emitter.emit_for_execution(
        execution={"id": "exec-3", "user_id": "u-1", "name": "X"},
        run_source="user_ui",
    )
    assert "workspace_items emit failed" in caplog.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/services/test_workspace_items.py -v`
Expected: 3 FAILED with `ImportError: cannot import name 'WorkspaceItemEmitter'`

- [ ] **Step 3: Write the minimal implementation**

```python
# app/services/workspace_items.py
"""Workspace item emission for workflow executions and other long-lived agent runs."""

import logging
from typing import Any

from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

INTERACTIVE_RUN_SOURCES = frozenset({"user_ui", "agent_ui"})


class WorkspaceItemEmitter:
    """Emits a workspace_item row when a workflow execution starts.

    Owns the mapping from run_source to layout_mode so other features can reuse
    the rule without re-implementing it.
    """

    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        return self._client or get_service_client()

    async def emit_for_execution(
        self,
        execution: dict[str, Any],
        run_source: str,
    ) -> None:
        """Insert a workflow_timeline workspace_item for ``execution``.

        Failures are logged and swallowed; the workflow must not abort because the
        visualization could not be persisted.
        """
        interactive = run_source in INTERACTIVE_RUN_SOURCES
        layout_mode = "focus" if interactive else "embedded"
        row = {
            "user_id": execution["user_id"],
            "widget_type": "workflow_timeline",
            "workflow_execution_id": execution["id"],
            "title": execution.get("name") or "Workflow",
            "layout_mode": layout_mode,
            "widget_payload": {
                "execution_id": execution["id"],
                "interactive": interactive,
            },
            "source_key": f"workflow_timeline:{execution['id']}",
        }
        try:
            await self.client.table("workspace_items").upsert(
                row, on_conflict="source_key"
            ).execute()
        except Exception as exc:
            logger.warning("workspace_items emit failed for execution %s: %s",
                           execution.get("id"), exc)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/services/test_workspace_items.py -v`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add app/services/workspace_items.py tests/unit/services/test_workspace_items.py
git commit -m "feat(services): add WorkspaceItemEmitter for workflow runs"
```

---

### Task 3: OutcomeWriter service

**Files:**
- Create: `app/workflows/outcome_writer.py`
- Test: `tests/unit/workflows/test_outcome_writer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/workflows/test_outcome_writer.py
"""Unit tests for OutcomeWriter precedence rules."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.workflows.outcome_writer import OutcomeWriter


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.table.return_value.update.return_value.eq.return_value.execute = AsyncMock(
        return_value=MagicMock(data=[{}])
    )
    return client


@pytest.mark.asyncio
async def test_tool_summary_short_used_verbatim(mock_client):
    writer = OutcomeWriter(client=mock_client)
    await writer.write_for_step(
        step_id="s1",
        tool_output={"summary": "Generated draft for Q3 marketing plan."},
        status="completed",
        tool_name="generate_doc",
        duration_ms=820,
    )
    update_payload = mock_client.table.return_value.update.call_args[0][0]
    assert update_payload["outcome_text"] == "Generated draft for Q3 marketing plan."
    assert update_payload["outcome_source"] == "tool"


@pytest.mark.asyncio
async def test_tool_summary_long_truncated(mock_client):
    long_summary = "x" * 500
    writer = OutcomeWriter(client=mock_client)
    await writer.write_for_step(
        step_id="s2",
        tool_output={"summary": long_summary},
        status="completed",
        tool_name="t",
        duration_ms=10,
    )
    update_payload = mock_client.table.return_value.update.call_args[0][0]
    assert len(update_payload["outcome_text"]) == 280
    assert update_payload["outcome_text"].endswith("...")
    assert update_payload["outcome_source"] == "tool"


@pytest.mark.asyncio
async def test_no_tool_summary_writes_status_fallback(mock_client):
    writer = OutcomeWriter(client=mock_client)
    await writer.write_for_step(
        step_id="s3",
        tool_output={"data": [1, 2, 3]},  # no summary key
        status="completed",
        tool_name="fetch_rows",
        duration_ms=120,
    )
    update_payload = mock_client.table.return_value.update.call_args[0][0]
    # status fallback is written immediately; LLM may overwrite later
    assert update_payload["outcome_text"] == "Completed fetch_rows in 120ms."
    assert update_payload["outcome_source"] == "status"


@pytest.mark.asyncio
async def test_failed_step_writes_error_fallback(mock_client):
    writer = OutcomeWriter(client=mock_client)
    await writer.write_for_step(
        step_id="s4",
        tool_output=None,
        status="failed",
        tool_name="bad_tool",
        duration_ms=50,
        error_message="boom",
    )
    update_payload = mock_client.table.return_value.update.call_args[0][0]
    assert "Failed" in update_payload["outcome_text"]
    assert "bad_tool" in update_payload["outcome_text"]
    assert update_payload["outcome_source"] == "status"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/workflows/test_outcome_writer.py -v`
Expected: 4 FAILED with `ImportError: cannot import name 'OutcomeWriter'`

- [ ] **Step 3: Write the minimal implementation**

```python
# app/workflows/outcome_writer.py
"""Persists per-step outcome text for the Live Workspace Workflow View."""

import logging
from typing import Any

from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

OUTCOME_MAX_LEN = 280


class OutcomeWriter:
    """Writes outcome_text and outcome_source on a workflow_steps row.

    Precedence:
        1. ``tool_output["summary"]`` if string, truncated to 280 chars (source=tool)
        2. Deterministic status string (source=status) — also written immediately as a
           seed; the OutcomeSummaryWorker may overwrite with an LLM result later.
    """

    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        return self._client or get_service_client()

    async def write_for_step(
        self,
        *,
        step_id: str,
        tool_output: Any,
        status: str,
        tool_name: str,
        duration_ms: int,
        error_message: str | None = None,
    ) -> None:
        text, source = self._derive(
            tool_output=tool_output,
            status=status,
            tool_name=tool_name,
            duration_ms=duration_ms,
            error_message=error_message,
        )
        try:
            await self.client.table("workflow_steps").update(
                {"outcome_text": text, "outcome_source": source}
            ).eq("id", step_id).execute()
        except Exception as exc:
            logger.warning("outcome_text write failed for step %s: %s", step_id, exc)

    def _derive(
        self,
        *,
        tool_output: Any,
        status: str,
        tool_name: str,
        duration_ms: int,
        error_message: str | None,
    ) -> tuple[str, str]:
        if isinstance(tool_output, dict):
            summary = tool_output.get("summary")
            if isinstance(summary, str) and summary.strip():
                if len(summary) > OUTCOME_MAX_LEN:
                    return summary[: OUTCOME_MAX_LEN - 3] + "...", "tool"
                return summary, "tool"
        if status == "failed":
            why = f" ({error_message})" if error_message else ""
            return f"Failed {tool_name}{why}.", "status"
        if status == "skipped":
            return f"Skipped {tool_name}.", "status"
        return f"Completed {tool_name} in {duration_ms}ms.", "status"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/workflows/test_outcome_writer.py -v`
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add app/workflows/outcome_writer.py tests/unit/workflows/test_outcome_writer.py
git commit -m "feat(workflows): add OutcomeWriter for per-step outcome text"
```

---

## Phase 3 — Engine wiring

### Task 4: Engine accepts `goal` and emits workspace item

**Files:**
- Modify: `app/workflows/engine.py` — `start_workflow()` signature and body
- Test: `tests/unit/workflows/test_engine_start_workflow_goal.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/workflows/test_engine_start_workflow_goal.py
"""Verify start_workflow persists goal and emits workspace_item."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.workflows.engine import WorkflowEngine


@pytest.mark.asyncio
async def test_start_workflow_persists_goal_and_emits_workspace_item():
    fake_emitter = AsyncMock()
    fake_execution = {"id": "exec-1", "user_id": "u-1", "name": "Plan", "goal": "ship Q3"}

    with patch(
        "app.workflows.engine.WorkspaceItemEmitter", return_value=MagicMock(
            emit_for_execution=fake_emitter
        )
    ), patch.object(
        WorkflowEngine, "_create_execution_atomic",
        new=AsyncMock(return_value=fake_execution),
    ), patch.object(
        WorkflowEngine, "_resolve_template",
        new=AsyncMock(return_value={"id": "t1", "phases": [], "lifecycle_status": "published",
                                     "name": "Plan"}),
    ), patch.object(
        WorkflowEngine, "_resolve_workflow_persona",
        new=AsyncMock(return_value="ceo"),
    ):
        engine = WorkflowEngine()
        result = await engine.start_workflow(
            user_id="u-1",
            template_name="Plan",
            goal="ship Q3",
            run_source="user_ui",
        )

    fake_emitter.assert_awaited_once()
    call_args = fake_emitter.call_args
    assert call_args.kwargs["execution"]["goal"] == "ship Q3"
    assert call_args.kwargs["run_source"] == "user_ui"
    assert result["execution_id"] == "exec-1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/workflows/test_engine_start_workflow_goal.py -v`
Expected: FAIL — `start_workflow() got an unexpected keyword argument 'goal'`

- [ ] **Step 3: Modify `start_workflow()` signature and body**

In `app/workflows/engine.py`, find `async def start_workflow(` (around line 636) and:

1. Add `goal: str | None = None,` as a new keyword argument after `persona`.
2. After the atomic execution insert (around line 810 where `start_workflow_execution_atomic` is called), pass `goal` into the RPC params so it lands in `workflow_executions.goal`.
3. After the execution row is returned, call the emitter.

Concretely, change the signature:

```python
async def start_workflow(
    self,
    user_id: str,
    template_name: str | None = None,
    template_id: str | None = None,
    template_version: int | None = None,
    context: dict[str, Any] | None = None,
    run_source: str = "user_ui",
    persona: str | None = None,
    goal: str | None = None,
) -> dict[str, Any]:
```

In the RPC params dict (find `start_workflow_execution_atomic`), add `"goal": goal`.

After the RPC call succeeds and you have the `execution` row, add:

```python
from app.services.workspace_items import WorkspaceItemEmitter

await WorkspaceItemEmitter().emit_for_execution(
    execution=execution,
    run_source=run_source,
)
```

You must also update the SQL function `start_workflow_execution_atomic` (in `supabase/migrations/20260426200000_atomic_workflow_execution_start.sql`) to accept and persist `goal`. **Read that migration first**; if the RPC writes to `workflow_executions` via INSERT, add `goal` to the column list and the function signature. Write a follow-up migration if needed (do not edit historical migrations):

```sql
-- supabase/migrations/20260511130100_atomic_workflow_execution_start_goal.sql
-- Update start_workflow_execution_atomic to accept and persist goal.
-- Read the current function body in 20260426200000_*.sql before editing.

CREATE OR REPLACE FUNCTION start_workflow_execution_atomic(
    -- ... existing params, then:
    p_goal TEXT DEFAULT NULL
) RETURNS ...
-- include p_goal in INSERT INTO workflow_executions (..., goal) VALUES (..., p_goal)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/workflows/test_engine_start_workflow_goal.py -v`
Expected: PASSED

Also re-run existing engine tests to confirm no regression:
Run: `uv run pytest tests/unit/workflows/ -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add app/workflows/engine.py supabase/migrations/20260511130100_atomic_workflow_execution_start_goal.sql tests/unit/workflows/test_engine_start_workflow_goal.py
git commit -m "feat(engine): start_workflow accepts goal and emits workspace item"
```

---

### Task 5: StepExecutor writes outcomes and emits SSE events

**Files:**
- Modify: `app/workflows/step_executor.py`
- Test: `tests/unit/workflows/test_step_executor_outcomes.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/workflows/test_step_executor_outcomes.py
"""Verify StepExecutor calls OutcomeWriter and emits SSE events."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.workflows.step_executor import StepExecutor


@pytest.mark.asyncio
async def test_completed_step_writes_outcome():
    fake_writer = AsyncMock()
    with patch("app.workflows.step_executor.OutcomeWriter",
               return_value=MagicMock(write_for_step=fake_writer)):
        executor = StepExecutor(client=MagicMock(), tool_registry={})
        await executor._finalize_step(
            step={"id": "s1", "tool_name": "t"},
            status="completed",
            tool_output={"summary": "Done."},
            duration_ms=100,
            error_message=None,
        )
    fake_writer.assert_awaited_once()
    assert fake_writer.call_args.kwargs["step_id"] == "s1"
    assert fake_writer.call_args.kwargs["status"] == "completed"


@pytest.mark.asyncio
async def test_paused_step_emits_sse_event():
    fake_bus = AsyncMock()
    with patch("app.workflows.step_executor.publish_workflow_event", fake_bus):
        executor = StepExecutor(client=MagicMock(), tool_registry={})
        await executor._on_step_paused_for_approval(
            execution_id="exec-1",
            step={"id": "s1", "name": "Send email"},
        )
    fake_bus.assert_awaited_once()
    event = fake_bus.call_args[0][1]  # (channel, payload)
    assert event["type"] == "workflow.step.paused"
    assert event["step_id"] == "s1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/workflows/test_step_executor_outcomes.py -v`
Expected: FAIL — `AttributeError: '_finalize_step'` or import error for `publish_workflow_event`.

- [ ] **Step 3: Implement the hooks in StepExecutor**

In `app/workflows/step_executor.py`:

1. At the top, import:
```python
from app.workflows.outcome_writer import OutcomeWriter
from app.workflows.event_bus import publish_workflow_event
```

2. Add a `_finalize_step` method that runs after a step's status is determined:

```python
async def _finalize_step(
    self,
    *,
    step: dict[str, Any],
    status: str,
    tool_output: Any,
    duration_ms: int,
    error_message: str | None,
) -> None:
    """Run post-step bookkeeping: outcome text + SSE event."""
    await OutcomeWriter(client=self._client).write_for_step(
        step_id=step["id"],
        tool_output=tool_output,
        status=status,
        tool_name=step.get("tool_name", "unknown"),
        duration_ms=duration_ms,
        error_message=error_message,
    )
    await publish_workflow_event(
        f"workflow.execution.{step['workflow_execution_id']}",
        {
            "type": f"workflow.step.{status}",
            "step_id": step["id"],
            "status": status,
            "duration_ms": duration_ms,
        },
    )

async def _on_step_paused_for_approval(
    self, *, execution_id: str, step: dict[str, Any],
) -> None:
    await publish_workflow_event(
        f"workflow.execution.{execution_id}",
        {
            "type": "workflow.step.paused",
            "step_id": step["id"],
            "step_name": step.get("name"),
            "reason": "human_gated",
        },
    )
```

3. Wire `_finalize_step` into the existing step-completion path (search for where step status is updated to `completed`/`failed`/`skipped` — likely around `step_executor.py:411` or `:530` based on prior grep). Call `_finalize_step` after the status update.

4. Wire `_on_step_paused_for_approval` into the existing path that transitions a step to `waiting_approval` (search for `waiting_approval` assignments).

- [ ] **Step 4: Create the event bus module**

Create `app/workflows/event_bus.py`:

```python
# app/workflows/event_bus.py
"""Internal pub-sub for per-execution SSE delivery.

Backed by Redis pub/sub with in-memory fallback (graceful degradation
when Redis is down — consistent with the cache circuit-breaker pattern).
"""

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)

# In-memory subscriber map for the local fallback path.
_subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)


async def publish_workflow_event(channel: str, payload: dict[str, Any]) -> None:
    """Publish a workflow event to all in-process subscribers.

    Redis publishing is added in a follow-up; for now in-memory is enough
    because the worker, the SSE endpoint, and the engine all live in the
    same process under FastAPI.
    """
    for q in list(_subscribers.get(channel, [])):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            logger.warning("event_bus queue full on %s; dropping event", channel)


async def subscribe(channel: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=128)
    _subscribers[channel].append(q)
    return q


def unsubscribe(channel: str, q: asyncio.Queue) -> None:
    try:
        _subscribers[channel].remove(q)
    except ValueError:
        pass
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/workflows/test_step_executor_outcomes.py -v`
Expected: 2 PASSED

Run regression: `uv run pytest tests/unit/workflows/ -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add app/workflows/step_executor.py app/workflows/event_bus.py tests/unit/workflows/test_step_executor_outcomes.py
git commit -m "feat(workflows): emit outcome text and SSE events on step transitions"
```

---

### Task 6: SSE endpoint for per-execution stream

**Files:**
- Modify: `app/routers/workflows.py`
- Test: `tests/unit/routers/test_workflow_execution_stream.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/routers/test_workflow_execution_stream.py
"""Verify GET /workflows/executions/{id}/stream returns SSE."""

import asyncio
import json

import pytest
from httpx import AsyncClient, ASGITransport

from app.fast_api_app import app
from app.workflows.event_bus import publish_workflow_event


@pytest.mark.asyncio
async def test_stream_emits_events_from_event_bus():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        async def emit_after_delay():
            await asyncio.sleep(0.05)
            await publish_workflow_event(
                "workflow.execution.exec-1",
                {"type": "workflow.step.completed", "step_id": "s1"},
            )

        emit_task = asyncio.create_task(emit_after_delay())
        async with client.stream("GET", "/workflows/executions/exec-1/stream",
                                  headers={"Authorization": "Bearer test"}) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            first_event = None
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    first_event = json.loads(line[6:])
                    break
        await emit_task
        assert first_event["type"] == "workflow.step.completed"
        assert first_event["step_id"] == "s1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/routers/test_workflow_execution_stream.py -v`
Expected: FAIL — 404 (endpoint not registered).

- [ ] **Step 3: Add the SSE endpoint**

In `app/routers/workflows.py`, add:

```python
from fastapi.responses import StreamingResponse
from app.workflows.event_bus import subscribe, unsubscribe

@router.get("/executions/{execution_id}/stream")
async def stream_execution_events(execution_id: str):
    """SSE stream of step transitions for one execution."""

    async def event_generator():
        channel = f"workflow.execution.{execution_id}"
        queue = await subscribe(channel)
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") in {
                    "workflow.execution.completed",
                    "workflow.execution.failed",
                }:
                    break
        finally:
            unsubscribe(channel, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

Add `import json` at the top of the file if not already present.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/routers/test_workflow_execution_stream.py -v`
Expected: PASSED

- [ ] **Step 5: Commit**

```bash
git add app/routers/workflows.py tests/unit/routers/test_workflow_execution_stream.py
git commit -m "feat(api): add /workflows/executions/{id}/stream SSE endpoint"
```

---

## Phase 4 — Background workers

### Task 7: OutcomeSummaryWorker (LLM-fills outcome_text)

**Files:**
- Create: `app/workflows/outcome_summary_worker.py`
- Test: `tests/unit/workflows/test_outcome_summary_worker.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/workflows/test_outcome_summary_worker.py
"""Verify OutcomeSummaryWorker upgrades status outcomes to LLM outcomes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.workflows.outcome_summary_worker import OutcomeSummaryWorker


@pytest.mark.asyncio
async def test_worker_upgrades_status_outcome_to_llm():
    pending_step = {
        "id": "s1",
        "status": "completed",
        "tool_name": "fetch_rows",
        "output_data": {"rows": [1, 2, 3]},
        "outcome_text": "Completed fetch_rows in 120ms.",
        "outcome_source": "status",
    }
    fake_client = MagicMock()
    fake_client.table.return_value.select.return_value.eq.return_value.is_.return_value.execute = AsyncMock(
        return_value=MagicMock(data=[pending_step])
    )
    fake_client.table.return_value.update.return_value.eq.return_value.execute = AsyncMock(
        return_value=MagicMock(data=[{}])
    )

    with patch(
        "app.workflows.outcome_summary_worker._summarize",
        new=AsyncMock(return_value="Fetched 3 rows of recent sign-ups."),
    ):
        worker = OutcomeSummaryWorker(client=fake_client)
        n = await worker.run_once(limit=10)

    assert n == 1
    update_payload = fake_client.table.return_value.update.call_args[0][0]
    assert update_payload["outcome_text"] == "Fetched 3 rows of recent sign-ups."
    assert update_payload["outcome_source"] == "llm"


@pytest.mark.asyncio
async def test_worker_falls_back_to_status_on_llm_failure():
    pending_step = {
        "id": "s2",
        "status": "completed",
        "tool_name": "send_email",
        "output_data": {},
        "outcome_text": None,  # nothing seeded yet
        "outcome_source": None,
    }
    fake_client = MagicMock()
    fake_client.table.return_value.select.return_value.eq.return_value.is_.return_value.execute = AsyncMock(
        return_value=MagicMock(data=[pending_step])
    )
    fake_client.table.return_value.update.return_value.eq.return_value.execute = AsyncMock(
        return_value=MagicMock(data=[{}])
    )

    with patch(
        "app.workflows.outcome_summary_worker._summarize",
        new=AsyncMock(side_effect=RuntimeError("quota exceeded")),
    ):
        worker = OutcomeSummaryWorker(client=fake_client)
        n = await worker.run_once(limit=10)

    assert n == 0  # no successful LLM upgrades
    # No update should be issued when LLM fails and there's already a non-null outcome.
    # When outcome_text is None, the worker leaves it for OutcomeWriter to seed.
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/workflows/test_outcome_summary_worker.py -v`
Expected: FAIL — ImportError.

- [ ] **Step 3: Write the implementation**

```python
# app/workflows/outcome_summary_worker.py
"""Background worker that upgrades 'status' outcomes to 'llm' outcomes.

Scans the partial index idx_workflow_steps_outcome_pending (or all steps with
status='completed' and outcome_source='status') and calls Gemini Flash to
produce a one-sentence human-readable summary.

Designed to run as a periodic task — invoked from Cloud Scheduler every few
minutes — or as a standalone asyncio task in the same process as the engine.
"""

import logging
from typing import Any

from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = (
    "Summarize what this workflow step accomplished in one sentence "
    "(max 25 words, no preamble, no markdown). Tool: {tool}. Output: {output}"
)


async def _summarize(tool_name: str, output_data: Any) -> str:
    """Call Gemini Flash with the summarization prompt.

    Kept as a module-level function so tests can patch it. Before writing this
    function, grep for the project's existing Gemini text-generation entry
    point (try ``rg "gemini-2.5-flash" app/services``) and reuse it. Per the
    Vertex model audit memory, gemini-2.5-flash is the current safe default
    for lightweight summarization. Wrap the call with the same retry+timeout
    used by the image-gen quota wrapper so this never blocks the engine.
    """
    # Replace the import below with the actual path discovered via grep:
    from app.services.gemini_client import generate_text

    prompt = SUMMARY_PROMPT.format(tool=tool_name, output=str(output_data)[:2000])
    text = await generate_text(prompt, model="gemini-2.5-flash", max_tokens=80)
    return text.strip()


class OutcomeSummaryWorker:
    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        return self._client or get_service_client()

    async def run_once(self, limit: int = 50) -> int:
        """Process one batch. Returns number of LLM-upgraded outcomes."""
        res = await (
            self.client.table("workflow_steps")
            .select("id, status, tool_name, output_data, outcome_text, outcome_source")
            .eq("status", "completed")
            .is_("outcome_text", "null")
            .execute()
        )
        rows = res.data or []
        rows = rows[:limit]

        upgraded = 0
        for step in rows:
            try:
                summary = await _summarize(
                    step.get("tool_name") or "unknown",
                    step.get("output_data") or {},
                )
            except Exception as exc:
                logger.warning("LLM summary failed for step %s: %s", step["id"], exc)
                continue
            if not summary:
                continue
            try:
                await (
                    self.client.table("workflow_steps")
                    .update({"outcome_text": summary[:280], "outcome_source": "llm"})
                    .eq("id", step["id"])
                    .execute()
                )
                upgraded += 1
            except Exception as exc:
                logger.warning("Failed to write LLM outcome for step %s: %s", step["id"], exc)
        return upgraded
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/workflows/test_outcome_summary_worker.py -v`
Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add app/workflows/outcome_summary_worker.py tests/unit/workflows/test_outcome_summary_worker.py
git commit -m "feat(workflows): add OutcomeSummaryWorker for LLM step summaries"
```

---

### Task 8: workspace_items cleanup job

**Files:**
- Create: `app/services/workspace_items_cleanup.py`
- Test: `tests/unit/services/test_workspace_items_cleanup.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/services/test_workspace_items_cleanup.py
"""Verify cleanup archives completed/cancelled workflow items older than 48h."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.workspace_items_cleanup import archive_stale_workflow_items


@pytest.mark.asyncio
async def test_archives_completed_runs_older_than_48h():
    fake_client = MagicMock()
    fake_client.rpc.return_value.execute = AsyncMock(
        return_value=MagicMock(data=[{"archived": 3}])
    )
    archived = await archive_stale_workflow_items(client=fake_client)
    assert archived == 3
    args = fake_client.rpc.call_args
    assert args[0][0] == "archive_stale_workflow_items"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/services/test_workspace_items_cleanup.py -v`
Expected: FAIL — ImportError.

- [ ] **Step 3: Write the implementation + SQL function**

Create `supabase/migrations/20260511130200_workspace_items_archive_fn.sql`:

```sql
-- Archive workspace_items for completed/cancelled workflow runs older than 48h.
CREATE OR REPLACE FUNCTION archive_stale_workflow_items()
RETURNS TABLE (archived INT) AS $$
DECLARE
    n INT;
BEGIN
    WITH stale AS (
        SELECT wi.id
        FROM workspace_items wi
        JOIN workflow_executions we ON we.id = wi.workflow_execution_id
        WHERE wi.widget_type = 'workflow_timeline'
          AND wi.archived_at IS NULL
          AND we.status IN ('completed', 'cancelled')
          AND we.completed_at IS NOT NULL
          AND we.completed_at < NOW() - INTERVAL '48 hours'
    ),
    upd AS (
        UPDATE workspace_items
           SET archived_at = NOW()
         WHERE id IN (SELECT id FROM stale)
         RETURNING 1
    )
    SELECT COUNT(*) INTO n FROM upd;
    RETURN QUERY SELECT n;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

Create `app/services/workspace_items_cleanup.py`:

```python
"""Daily cleanup that archives workspace_items for completed workflow runs."""

import logging
from typing import Any

from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)


async def archive_stale_workflow_items(client: Any | None = None) -> int:
    """Call the archive_stale_workflow_items RPC. Returns number archived."""
    c = client or get_service_client()
    try:
        res = await c.rpc("archive_stale_workflow_items").execute()
        rows = res.data or []
        return int(rows[0]["archived"]) if rows else 0
    except Exception as exc:
        logger.error("archive_stale_workflow_items failed: %s", exc)
        return 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/services/test_workspace_items_cleanup.py -v`
Expected: PASSED

- [ ] **Step 5: Register the cleanup in the daily scheduler**

In `app/routers/admin/` or wherever scheduler registrations live (check `project_admin_scheduler_jobs_paused.md` from memory for the registry pattern), add an entry that calls `archive_stale_workflow_items()` once daily. Concretely, find the scheduler-job registry file (likely `app/services/scheduler.py` or similar) and append:

```python
{
    "name": "workspace_items_cleanup",
    "schedule": "0 3 * * *",  # 03:00 UTC daily
    "handler": "app.services.workspace_items_cleanup:archive_stale_workflow_items",
    "enabled": True,
}
```

- [ ] **Step 6: Commit**

```bash
git add app/services/workspace_items_cleanup.py tests/unit/services/test_workspace_items_cleanup.py supabase/migrations/20260511130200_workspace_items_archive_fn.sql
git commit -m "feat(workspace): daily archive job for stale workflow items"
```

---

## Phase 5 — Frontend widget

### Task 9: Goal header on WorkflowTimelineWidget

**Files:**
- Modify: `frontend/src/components/widgets/WorkflowTimelineWidget.tsx`
- Test: `frontend/src/components/widgets/__tests__/WorkflowTimelineWidget.test.tsx` (create if missing)

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/widgets/__tests__/WorkflowTimelineWidget.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import WorkflowTimelineWidget from '../WorkflowTimelineWidget';

vi.mock('@/services/api', () => ({
    fetchWithAuth: vi.fn().mockResolvedValue({
        json: async () => ({
            execution_id: 'exec-1',
            name: 'Marketing Plan',
            goal: 'Ship the Q3 marketing plan by Friday',
            status: 'running',
            created_at: '2026-05-11T10:00:00Z',
            completed_at: null,
            steps: [],
            chain_info: null,
        }),
    }),
}));

describe('WorkflowTimelineWidget', () => {
    beforeEach(() => vi.clearAllMocks());

    it('renders the workflow name and goal in the header', async () => {
        render(<WorkflowTimelineWidget definition={{
            type: 'workflow_timeline',
            title: 'X',
            data: { execution_id: 'exec-1' },
        }} />);
        await waitFor(() => {
            expect(screen.getByText('Marketing Plan')).toBeInTheDocument();
            expect(screen.getByText(/Ship the Q3 marketing plan by Friday/)).toBeInTheDocument();
        });
    });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- WorkflowTimelineWidget`
Expected: FAIL — goal text not found.

- [ ] **Step 3: Add the header to the widget**

In `frontend/src/components/widgets/WorkflowTimelineWidget.tsx`, update the `TimelineData` interface to include `goal`:

```tsx
interface TimelineData {
    execution_id: string;
    name: string;
    goal: string | null;          // NEW
    status: string;
    // ...rest unchanged
}
```

Then near the top of the render JSX (above the steps list), add:

```tsx
<header className="border-b border-slate-100 px-5 py-4">
    <h3 className="text-base font-semibold text-slate-900">{data.name}</h3>
    {data.goal && (
        <p className="mt-1 text-sm italic text-slate-500 truncate" title={data.goal}>
            {data.goal}
        </p>
    )}
</header>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- WorkflowTimelineWidget`
Expected: PASSED.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/widgets/WorkflowTimelineWidget.tsx frontend/src/components/widgets/__tests__/WorkflowTimelineWidget.test.tsx
git commit -m "feat(ui): render workflow goal header in timeline widget"
```

---

### Task 10: Per-step outcome rendering

**Files:**
- Modify: `frontend/src/components/widgets/WorkflowTimelineWidget.tsx`
- Test: same file as Task 9

- [ ] **Step 1: Write the failing test**

Append to the test file:

```tsx
it('renders outcome_text on each step row', async () => {
    vi.mocked(fetchWithAuth).mockResolvedValueOnce({
        json: async () => ({
            execution_id: 'exec-2',
            name: 'X',
            goal: null,
            status: 'completed',
            created_at: '2026-05-11T10:00:00Z',
            completed_at: '2026-05-11T10:05:00Z',
            chain_info: null,
            steps: [{
                id: 's1',
                phase_name: 'Plan',
                step_name: 'Draft outline',
                status: 'completed',
                started_at: '2026-05-11T10:00:00Z',
                completed_at: '2026-05-11T10:01:00Z',
                phase_index: 0,
                step_index: 0,
                duration_ms: 60000,
                tool_name: 'generate_doc',
                error_message: null,
                outcome_text: 'Generated 3-page outline.',
                outcome_source: 'tool',
            }],
        }),
    });
    render(<WorkflowTimelineWidget definition={{
        type: 'workflow_timeline',
        title: 'X',
        data: { execution_id: 'exec-2' },
    }} />);
    await waitFor(() => {
        expect(screen.getByText('Generated 3-page outline.')).toBeInTheDocument();
    });
});

it('renders shimmer when outcome_text is pending on a completed step', async () => {
    vi.mocked(fetchWithAuth).mockResolvedValueOnce({
        json: async () => ({
            execution_id: 'exec-3',
            name: 'X', goal: null, status: 'completed',
            created_at: '', completed_at: '', chain_info: null,
            steps: [{
                id: 's1', phase_name: 'P', step_name: 'Step', status: 'completed',
                started_at: '', completed_at: '', phase_index: 0, step_index: 0,
                duration_ms: 1, tool_name: 't', error_message: null,
                outcome_text: null, outcome_source: null,
            }],
        }),
    });
    render(<WorkflowTimelineWidget definition={{
        type: 'workflow_timeline', title: 'X', data: { execution_id: 'exec-3' },
    }} />);
    await waitFor(() => {
        expect(screen.getByTestId('outcome-shimmer')).toBeInTheDocument();
    });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- WorkflowTimelineWidget`
Expected: the two new tests FAIL.

- [ ] **Step 3: Update `TimelineStep` interface and render**

Update `TimelineStep`:
```tsx
interface TimelineStep {
    // ...existing fields
    outcome_text: string | null;
    outcome_source: 'tool' | 'llm' | 'status' | null;
}
```

In the step row JSX (find where status, tool_name, duration render), append:

```tsx
{step.outcome_text ? (
    <p className="mt-1 text-sm text-slate-600 leading-snug">{step.outcome_text}</p>
) : step.status === 'completed' ? (
    <div data-testid="outcome-shimmer"
         className="mt-1 h-3 w-2/3 rounded bg-slate-100 animate-pulse" />
) : null}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- WorkflowTimelineWidget`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/widgets/WorkflowTimelineWidget.tsx frontend/src/components/widgets/__tests__/WorkflowTimelineWidget.test.tsx
git commit -m "feat(ui): render per-step outcome text with shimmer fallback"
```

---

### Task 11: Inline approval UX and card banner

**Files:**
- Modify: `frontend/src/components/widgets/WorkflowTimelineWidget.tsx`
- Test: same file

- [ ] **Step 1: Write the failing test**

Append:

```tsx
import { fireEvent } from '@testing-library/react';

it('renders Approve/Reject buttons on waiting_approval step + amber banner', async () => {
    vi.mocked(fetchWithAuth).mockResolvedValueOnce({
        json: async () => ({
            execution_id: 'exec-4',
            name: 'Send Campaign', goal: 'Notify customers about Q3 launch',
            status: 'waiting_approval', created_at: '', completed_at: null, chain_info: null,
            steps: [{
                id: 's1', phase_name: 'Approve', step_name: 'Confirm send', status: 'waiting_approval',
                started_at: '', completed_at: null, phase_index: 0, step_index: 0,
                duration_ms: null, tool_name: 'send_email', error_message: null,
                outcome_text: null, outcome_source: null,
            }],
        }),
    });
    render(<WorkflowTimelineWidget definition={{
        type: 'workflow_timeline', title: 'X', data: { execution_id: 'exec-4' },
    }} />);
    await waitFor(() => {
        expect(screen.getByRole('button', { name: /Approve/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Reject/i })).toBeInTheDocument();
        expect(screen.getByText(/Awaiting your approval/i)).toBeInTheDocument();
    });
});

it('POSTs to approve endpoint on click and disables buttons optimistically', async () => {
    const approveCall = vi.fn().mockResolvedValue({ ok: true });
    vi.mocked(fetchWithAuth).mockImplementation((url: string, opts?: any) => {
        if (url.endsWith('/approve')) return approveCall(url, opts);
        return Promise.resolve({
            json: async () => ({
                execution_id: 'exec-5', name: 'X', goal: null,
                status: 'waiting_approval', created_at: '', completed_at: null, chain_info: null,
                steps: [{
                    id: 's1', phase_name: 'P', step_name: 'S', status: 'waiting_approval',
                    started_at: '', completed_at: null, phase_index: 0, step_index: 0,
                    duration_ms: null, tool_name: 't', error_message: null,
                    outcome_text: null, outcome_source: null,
                }],
            }),
        });
    });
    render(<WorkflowTimelineWidget definition={{
        type: 'workflow_timeline', title: 'X', data: { execution_id: 'exec-5' },
    }} />);
    const approveBtn = await screen.findByRole('button', { name: /Approve/i });
    fireEvent.click(approveBtn);
    await waitFor(() => {
        expect(approveCall).toHaveBeenCalledWith(
            '/workflows/executions/exec-5/steps/s1/approve',
            expect.objectContaining({ method: 'POST' }),
        );
    });
    expect(approveBtn).toBeDisabled();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- WorkflowTimelineWidget`
Expected: the new tests FAIL.

- [ ] **Step 3: Add the approval UI**

Add an approval-row branch in the step rendering:

```tsx
const [pendingApproval, setPendingApproval] = React.useState<Set<string>>(new Set());

const handleApprove = async (stepId: string, decision: 'approve' | 'reject') => {
    setPendingApproval(prev => new Set(prev).add(stepId));
    try {
        await fetchWithAuth(
            `/workflows/executions/${data.execution_id}/steps/${stepId}/${decision}`,
            { method: 'POST' },
        );
    } catch (e) {
        // Roll back optimistic disable on failure
        setPendingApproval(prev => {
            const next = new Set(prev);
            next.delete(stepId);
            return next;
        });
    }
};

// In the step row, when status === 'waiting_approval':
{step.status === 'waiting_approval' && (
    <div className="mt-2 flex items-center gap-2">
        <button
            type="button"
            disabled={pendingApproval.has(step.id)}
            onClick={() => handleApprove(step.id, 'approve')}
            className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
        >
            Approve
        </button>
        <button
            type="button"
            disabled={pendingApproval.has(step.id)}
            onClick={() => handleApprove(step.id, 'reject')}
            className="rounded-md bg-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-300 disabled:opacity-50"
        >
            Reject
        </button>
    </div>
)}
```

Card-level banner (when any step is waiting):

```tsx
const awaitingApproval = data.steps.some(s => s.status === 'waiting_approval');

return (
    <div className={awaitingApproval ? 'border-t-2 border-amber-400' : ''}>
        {awaitingApproval && (
            <div className="bg-amber-50 px-5 py-2 text-sm font-medium text-amber-900">
                ⏸ Awaiting your approval
            </div>
        )}
        {/* existing header + steps */}
    </div>
);
```

You also need the backend endpoint pair. Add to `app/routers/workflows.py`:

```python
@router.post("/executions/{execution_id}/steps/{step_id}/approve")
async def approve_step_endpoint(execution_id: str, step_id: str, user=Depends(current_user)):
    engine = WorkflowEngine()
    return await engine.approve_step(execution_id=execution_id, step_id=step_id, user_id=user.id)

@router.post("/executions/{execution_id}/steps/{step_id}/reject")
async def reject_step_endpoint(execution_id: str, step_id: str, user=Depends(current_user)):
    engine = WorkflowEngine()
    return await engine.reject_step(execution_id=execution_id, step_id=step_id, user_id=user.id)
```

(Wire to existing `approve_step` / add `reject_step` in `engine.py` if missing — `reject_step` should mark the step `failed` with `error_message="Rejected by user"` and stop the execution.)

- [ ] **Step 4: Run tests to verify they pass**

Run frontend tests: `cd frontend && npm test -- WorkflowTimelineWidget`
Run backend tests: `uv run pytest tests/unit/workflows/ tests/unit/routers/ -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/widgets/WorkflowTimelineWidget.tsx frontend/src/components/widgets/__tests__/WorkflowTimelineWidget.test.tsx app/routers/workflows.py app/workflows/engine.py
git commit -m "feat(ui): inline Approve/Reject buttons and awaiting-approval banner"
```

---

### Task 12: Collapsed-strip variant for non-interactive runs

**Files:**
- Modify: `frontend/src/components/widgets/WorkflowTimelineWidget.tsx`
- Test: same file

- [ ] **Step 1: Write the failing test**

Append:

```tsx
it('renders one-line strip when payload.interactive is false', async () => {
    vi.mocked(fetchWithAuth).mockResolvedValueOnce({
        json: async () => ({
            execution_id: 'exec-6', name: 'Nightly Report', goal: null,
            status: 'running', created_at: '', completed_at: null, chain_info: null,
            steps: [
                { id: 's1', phase_name: '', step_name: '', status: 'completed', started_at: '',
                  completed_at: '', phase_index: 0, step_index: 0, duration_ms: 1, tool_name: '',
                  error_message: null, outcome_text: null, outcome_source: null },
                { id: 's2', phase_name: '', step_name: '', status: 'running', started_at: '',
                  completed_at: null, phase_index: 0, step_index: 1, duration_ms: null, tool_name: '',
                  error_message: null, outcome_text: null, outcome_source: null },
            ],
        }),
    });
    render(<WorkflowTimelineWidget definition={{
        type: 'workflow_timeline', title: 'X',
        data: { execution_id: 'exec-6', interactive: false },
    }} />);
    await waitFor(() => {
        expect(screen.getByTestId('workflow-strip')).toBeInTheDocument();
        expect(screen.getByText(/Nightly Report/)).toBeInTheDocument();
        expect(screen.getByText(/step 2 of 2/i)).toBeInTheDocument();
    });
});

it('auto-expands the strip when a step pauses for approval', async () => {
    vi.mocked(fetchWithAuth).mockResolvedValueOnce({
        json: async () => ({
            execution_id: 'exec-7', name: 'Cron', goal: null,
            status: 'waiting_approval', created_at: '', completed_at: null, chain_info: null,
            steps: [{
                id: 's1', phase_name: '', step_name: 'X', status: 'waiting_approval',
                started_at: '', completed_at: null, phase_index: 0, step_index: 0,
                duration_ms: null, tool_name: '', error_message: null,
                outcome_text: null, outcome_source: null,
            }],
        }),
    });
    render(<WorkflowTimelineWidget definition={{
        type: 'workflow_timeline', title: 'X',
        data: { execution_id: 'exec-7', interactive: false },
    }} />);
    await waitFor(() => {
        // expanded view shown, not strip
        expect(screen.queryByTestId('workflow-strip')).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Approve/i })).toBeInTheDocument();
    });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- WorkflowTimelineWidget`
Expected: the two new tests FAIL.

- [ ] **Step 3: Add the strip render branch**

At the top of the widget render:

```tsx
const interactive = (definition.data as any)?.interactive !== false;
const awaitingApproval = data?.steps?.some(s => s.status === 'waiting_approval') ?? false;
const renderAsStrip = !interactive && !awaitingApproval && data?.status !== 'failed';

if (renderAsStrip && data) {
    const total = data.steps.length;
    const currentIdx = data.steps.findIndex(s => s.status === 'running');
    const stepLabel = currentIdx >= 0 ? `step ${currentIdx + 1} of ${total}` : `${data.status}`;
    return (
        <button
            type="button"
            data-testid="workflow-strip"
            onClick={() => setForceExpand(true)}
            className="flex w-full items-center gap-3 rounded-xl border border-slate-100 bg-white px-4 py-2 text-left text-sm hover:bg-slate-50"
        >
            <span aria-hidden>▶</span>
            <span className="font-medium text-slate-800">{data.name}</span>
            <span className="text-slate-500">• {stepLabel}</span>
        </button>
    );
}
```

Add a `const [forceExpand, setForceExpand] = React.useState(false);` near the top of the component so the user can manually expand a strip.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- WorkflowTimelineWidget`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/widgets/WorkflowTimelineWidget.tsx frontend/src/components/widgets/__tests__/WorkflowTimelineWidget.test.tsx
git commit -m "feat(ui): collapsed-strip variant for non-interactive workflow runs"
```

---

### Task 13: SSE subscription via EventSource

**Files:**
- Create: `frontend/src/services/workflowExecutionStream.ts`
- Modify: `frontend/src/components/widgets/WorkflowTimelineWidget.tsx`
- Test: `frontend/src/services/__tests__/workflowExecutionStream.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/services/__tests__/workflowExecutionStream.test.ts
import { describe, it, expect, vi } from 'vitest';
import { subscribeToExecution } from '../workflowExecutionStream';

describe('subscribeToExecution', () => {
    it('opens an EventSource at the right URL and calls onEvent', () => {
        const events: any[] = [];
        const fakeEventSource: any = {
            addEventListener: vi.fn((type, cb) => {
                if (type === 'message') {
                    // simulate one incoming event
                    setTimeout(() => cb({ data: JSON.stringify({ type: 'workflow.step.completed', step_id: 's1' }) }), 0);
                }
            }),
            close: vi.fn(),
        };
        (global as any).EventSource = vi.fn().mockImplementation(() => fakeEventSource);

        const unsubscribe = subscribeToExecution('exec-1', (evt) => events.push(evt));
        return new Promise<void>(resolve => setTimeout(() => {
            expect((global as any).EventSource).toHaveBeenCalledWith('/workflows/executions/exec-1/stream');
            expect(events[0]).toMatchObject({ type: 'workflow.step.completed', step_id: 's1' });
            unsubscribe();
            expect(fakeEventSource.close).toHaveBeenCalled();
            resolve();
        }, 10));
    });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- workflowExecutionStream`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the subscription helper**

```ts
// frontend/src/services/workflowExecutionStream.ts
export interface WorkflowEvent {
    type: string;
    step_id?: string;
    status?: string;
    duration_ms?: number;
    [key: string]: unknown;
}

export function subscribeToExecution(
    executionId: string,
    onEvent: (e: WorkflowEvent) => void,
): () => void {
    const source = new EventSource(`/workflows/executions/${executionId}/stream`);
    const handler = (msg: MessageEvent) => {
        try { onEvent(JSON.parse(msg.data)); } catch { /* ignore malformed */ }
    };
    source.addEventListener('message', handler);
    return () => source.close();
}
```

- [ ] **Step 4: Wire into the widget**

In `WorkflowTimelineWidget.tsx`, add a `useEffect`:

```tsx
import { subscribeToExecution } from '@/services/workflowExecutionStream';

React.useEffect(() => {
    if (!data) return;
    const unsubscribe = subscribeToExecution(data.execution_id, (evt) => {
        if (evt.type?.startsWith('workflow.step.')) {
            // re-fetch on any step transition (cheap; small payload)
            refetch();
        }
    });
    return unsubscribe;
}, [data?.execution_id]);
```

Where `refetch` is the existing fetch closure (extract from the initial `useEffect` if it isn't already a callable).

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npm test -- workflowExecutionStream WorkflowTimelineWidget`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/services/workflowExecutionStream.ts frontend/src/services/__tests__/workflowExecutionStream.test.ts frontend/src/components/widgets/WorkflowTimelineWidget.tsx
git commit -m "feat(ui): subscribe to per-execution SSE for live updates"
```

---

## Phase 6 — Integration

### Task 14: Feature flag wiring

**Files:**
- Modify: `app/config/settings.py`
- Modify: `app/workflows/engine.py`
- Modify: `frontend/src/components/widgets/WorkflowTimelineWidget.tsx`

- [ ] **Step 1: Add the flag to settings**

In `app/config/settings.py`, add:

```python
LIVE_WORKFLOW_VIEW: bool = Field(default=True, env="LIVE_WORKFLOW_VIEW")
```

- [ ] **Step 2: Gate the emitter in the engine**

In `engine.py`, wrap the emit call:

```python
from app.config.settings import settings

if settings.LIVE_WORKFLOW_VIEW:
    await WorkspaceItemEmitter().emit_for_execution(execution=execution, run_source=run_source)
```

- [ ] **Step 3: Gate the SSE subscription in the frontend**

Expose the flag via an existing public config endpoint (likely `/config/public` — check the codebase). Read it in the widget; if disabled, skip the `useEffect` that opens the EventSource.

- [ ] **Step 4: Manual smoke**

Set `LIVE_WORKFLOW_VIEW=false` in `.env.local`, start the backend, kick off a workflow from the UI; verify no workspace_item appears.
Set it back to `true`; verify the item appears.

- [ ] **Step 5: Commit**

```bash
git add app/config/settings.py app/workflows/engine.py frontend/src/components/widgets/WorkflowTimelineWidget.tsx
git commit -m "feat(config): gate live workflow view behind LIVE_WORKFLOW_VIEW flag"
```

---

### Task 15: End-to-end integration test

**Files:**
- Create: `tests/integration/test_live_workflow_view.py`

- [ ] **Step 1: Write the integration test**

```python
# tests/integration/test_live_workflow_view.py
"""End-to-end: start a workflow with a human_gated step, verify workspace item
appears, verify approval through the API advances the execution."""

import asyncio
import json

import pytest
from httpx import AsyncClient, ASGITransport

from app.fast_api_app import app


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_lifecycle_creates_workspace_item_and_supports_inline_approval(
    seed_user_with_approval_required_template,
):
    user, token, template_name = seed_user_with_approval_required_template
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://t", headers=headers) as client:
        # 1. Start workflow with a goal
        start_res = await client.post("/workflows/start", json={
            "template_name": template_name,
            "goal": "Send Q3 launch email to top-100 customers",
            "run_source": "user_ui",
        })
        assert start_res.status_code == 200
        execution_id = start_res.json()["execution_id"]

        # 2. Workspace item should exist for this execution
        ws_res = await client.get("/workspace/items")
        assert ws_res.status_code == 200
        items = ws_res.json()
        ws_item = next((i for i in items if i.get("workflow_execution_id") == execution_id), None)
        assert ws_item is not None
        assert ws_item["widget_type"] == "workflow_timeline"
        assert ws_item["layout_mode"] == "focus"

        # 3. Wait for the workflow to reach waiting_approval
        for _ in range(20):
            exec_res = await client.get(f"/workflows/executions/{execution_id}")
            if exec_res.json()["status"] == "waiting_approval":
                break
            await asyncio.sleep(0.25)
        else:
            pytest.fail("workflow did not reach waiting_approval")

        paused_step_id = next(
            s["id"] for s in exec_res.json()["steps"]
            if s["status"] == "waiting_approval"
        )

        # 4. Approve via the new endpoint
        approve_res = await client.post(
            f"/workflows/executions/{execution_id}/steps/{paused_step_id}/approve",
        )
        assert approve_res.status_code == 200

        # 5. Verify the step is no longer paused
        for _ in range(20):
            exec_res = await client.get(f"/workflows/executions/{execution_id}")
            step = next(s for s in exec_res.json()["steps"] if s["id"] == paused_step_id)
            if step["status"] != "waiting_approval":
                break
            await asyncio.sleep(0.25)
        else:
            pytest.fail("step still paused after approve")

        assert step["status"] in {"completed", "running"}
```

The `seed_user_with_approval_required_template` fixture should create a minimal template with one `required_approval=true` step. Place it in `tests/conftest.py` if a similar fixture doesn't already exist. Reuse existing template-seeding helpers.

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/integration/test_live_workflow_view.py -v -m integration`
Expected: PASSED. Iterate on fixtures and timing as needed.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_live_workflow_view.py tests/conftest.py
git commit -m "test(integration): end-to-end live workflow view flow"
```

---

## Done definition

- All 15 tasks completed and committed
- `uv run pytest tests/unit/services/ tests/unit/workflows/ tests/unit/routers/ -v` all green
- `cd frontend && npm test` all green
- `uv run pytest tests/integration/test_live_workflow_view.py -v -m integration` green
- Manual smoke: start a workflow from chat; observe the workflow_timeline widget auto-appear in workspace; trigger an approval step; approve inline; observe execution advance.

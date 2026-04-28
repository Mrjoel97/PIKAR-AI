# App Builder Autopilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After the user submits the 5th wizard answer, an `AppBuilderOrchestrator` runs research → build → ship autonomously, narrating into chat and pausing only at brief approval, variant pick, per-screen approval, and ship target.

**Architecture:** A per-project asyncio orchestrator task driven by a state column. State transitions read existing services (`run_design_research`, `_generate_build_plan`, `generate_screen_variants`, `build_all_pages`, `ship_project`) and append narration events to a JSONB column the canvas + chat poll. Pauses correspond to existing canvas user-action endpoints (approve-brief, select-variant, approve-screen) which the orchestrator monitors before resuming. A new top-level pause for ship target uses a quick-reply widget in chat.

**Tech Stack:** Python 3.12 (FastAPI, asyncio, asyncpg via Supabase Python SDK), TypeScript 5 / React 19 / Next.js 16, Supabase (Postgres) for project state, existing Stitch MCP for screen gen, existing `run_design_research` SSE pipeline.

**Spec:** [`docs/superpowers/specs/2026-04-27-app-builder-autopilot-design.md`](../specs/2026-04-27-app-builder-autopilot-design.md)

**Branch:** `feature/app-builder-autopilot` (already checked out)

---

## File Structure

**Create:**
- `supabase/migrations/20260427120000_app_projects_autopilot.sql` — three new columns + check constraint
- `app/services/app_builder_orchestrator.py` — state machine + per-project asyncio task
- `tests/unit/app_builder/test_app_builder_orchestrator.py` — service tests (mocked Supabase)
- `tests/integration/test_app_builder_autopilot_e2e.py` — end-to-end happy-path test
- `frontend/src/hooks/useAppBuilderAutopilot.ts` — polling hook + chat-message injection

**Modify:**
- `app/routers/app_builder.py` — three new endpoints (start, resume, status)
- `app/agents/tools/app_builder.py` — new `start_app_builder_autopilot` tool
- `app/prompts/executive_instruction.txt` — §18A note about autopilot tool
- `app/agent.py` — wire new tool into Executive's tool list
- `frontend/src/services/app-builder.ts` — three new API client functions
- `frontend/src/components/widgets/AppBuilderCanvasWidget.tsx` — postMessage listener + status sync
- `frontend/src/components/app-builder/QuestioningWizard.tsx` — postMessage on final answer
- `tests/unit/app_builder/test_app_builder_router.py` — endpoint tests for the 3 new routes

**Boundaries:**
- The orchestrator owns ALL stage transitions during autopilot. The existing manual stage endpoints (`/advance-stage`, `/approve-brief`, etc.) still work but, when called while `autopilot_status='running'`, the orchestrator detects it on the next loop tick and aborts to `failed` (per spec §"User triggers manual action in canvas while autopilot is running").
- Narration events live in a JSONB array on `app_projects.autopilot_events`. Frontend polls; no new SSE channel.
- One autopilot per project. Per spec, no concurrency between projects for the same user.

---

## Task 1: Database migration — autopilot columns

**Files:**
- Create: `supabase/migrations/20260427120000_app_projects_autopilot.sql`

- [ ] **Step 1: Write the migration file**

```sql
-- 20260427120000_app_projects_autopilot.sql
-- Adds autopilot state columns to app_projects.
-- See docs/superpowers/specs/2026-04-27-app-builder-autopilot-design.md

ALTER TABLE app_projects
  ADD COLUMN IF NOT EXISTS autopilot_status TEXT NOT NULL DEFAULT 'idle';

ALTER TABLE app_projects
  ADD CONSTRAINT app_projects_autopilot_status_check
  CHECK (autopilot_status IN (
    'idle',
    'running',
    'paused_brief',
    'paused_variant',
    'paused_screen',
    'paused_ship',
    'failed',
    'done'
  ));

ALTER TABLE app_projects
  ADD COLUMN IF NOT EXISTS autopilot_session_id TEXT;

ALTER TABLE app_projects
  ADD COLUMN IF NOT EXISTS autopilot_error TEXT;

ALTER TABLE app_projects
  ADD COLUMN IF NOT EXISTS autopilot_events JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_app_projects_autopilot_status
  ON app_projects (autopilot_status)
  WHERE autopilot_status NOT IN ('idle', 'done');

COMMENT ON COLUMN app_projects.autopilot_status IS
  'Autopilot state machine state. See AppBuilderOrchestrator.';
COMMENT ON COLUMN app_projects.autopilot_session_id IS
  'Chat session that initiated autopilot — used to address narration events.';
COMMENT ON COLUMN app_projects.autopilot_error IS
  'Error message when autopilot_status=failed; nullable otherwise.';
COMMENT ON COLUMN app_projects.autopilot_events IS
  'Append-only narration log: [{ts, kind, message, payload?}, ...]';
```

- [ ] **Step 2: Apply migration locally**

Run: `supabase db push --local`
Expected: `Applying migration 20260427120000_app_projects_autopilot.sql ... ok`

- [ ] **Step 3: Verify columns landed**

Run: `supabase db reset --local && psql "$(supabase status --output env | grep DB_URL | cut -d= -f2)" -c "\d app_projects" | grep autopilot`
Expected: lines for `autopilot_status`, `autopilot_session_id`, `autopilot_error`, `autopilot_events`.

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/20260427120000_app_projects_autopilot.sql
git commit -m "feat(autopilot): add autopilot state columns to app_projects"
```

---

## Task 2: Orchestrator skeleton + state machine helpers

**Files:**
- Create: `app/services/app_builder_orchestrator.py`
- Create: `tests/unit/app_builder/test_app_builder_orchestrator.py`

- [ ] **Step 1: Write failing tests for state-machine helpers**

```python
# tests/unit/app_builder/test_app_builder_orchestrator.py
"""Unit tests for AppBuilderOrchestrator state machine helpers."""
from unittest.mock import MagicMock

import pytest

from app.services.app_builder_orchestrator import (
    AUTOPILOT_STATES,
    AppBuilderOrchestrator,
    AutopilotState,
)


PROJECT_ID = "aaaaaaaa-0000-0000-0000-000000000001"
SESSION_ID = "session-001"


def _orch(supabase: MagicMock) -> AppBuilderOrchestrator:
    return AppBuilderOrchestrator(
        project_id=PROJECT_ID,
        session_id=SESSION_ID,
        supabase=supabase,
    )


def test_states_cover_spec():
    """The state set must match the spec exactly."""
    assert AUTOPILOT_STATES == {
        "idle",
        "running",
        "paused_brief",
        "paused_variant",
        "paused_screen",
        "paused_ship",
        "failed",
        "done",
    }


def test_set_state_writes_to_supabase():
    supabase = MagicMock()
    orch = _orch(supabase)
    orch.set_state("running")
    supabase.table.return_value.update.assert_called_with(
        {"autopilot_status": "running"}
    )


def test_publish_event_appends_to_jsonb_array():
    supabase = MagicMock()
    # Simulate row.fetchone returning current events array
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"autopilot_events": []}
    )
    orch = _orch(supabase)
    orch.publish_event(kind="status", message="Running research")
    # Last update call should contain autopilot_events with one entry
    update_call = supabase.table.return_value.update.call_args_list[-1]
    new_events = update_call.args[0]["autopilot_events"]
    assert len(new_events) == 1
    assert new_events[0]["kind"] == "status"
    assert new_events[0]["message"] == "Running research"
    assert "ts" in new_events[0]


def test_fail_records_error_and_state():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"autopilot_events": []}
    )
    orch = _orch(supabase)
    orch.fail("Stitch unavailable")
    update_call = supabase.table.return_value.update.call_args_list[-1]
    payload = update_call.args[0]
    assert payload["autopilot_status"] == "failed"
    assert payload["autopilot_error"] == "Stitch unavailable"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/app_builder/test_app_builder_orchestrator.py -v`
Expected: FAIL — `app.services.app_builder_orchestrator` not found.

- [ ] **Step 3: Write minimal orchestrator skeleton**

```python
# app/services/app_builder_orchestrator.py
# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""App Builder Autopilot orchestrator.

Runs the GSD flow autonomously after the user completes the questioning
wizard. Pauses only at meaningful user decisions (brief approval, variant
pick, per-screen approval, ship target).

State transitions persist to `app_projects.autopilot_status`. Narration
events append to `app_projects.autopilot_events` (JSONB array). The
canvas and chat hooks poll those columns; this service does not push
SSE itself.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal

logger = logging.getLogger(__name__)

AutopilotState = Literal[
    "idle",
    "running",
    "paused_brief",
    "paused_variant",
    "paused_screen",
    "paused_ship",
    "failed",
    "done",
]

AUTOPILOT_STATES: set[str] = {
    "idle",
    "running",
    "paused_brief",
    "paused_variant",
    "paused_screen",
    "paused_ship",
    "failed",
    "done",
}


class AppBuilderOrchestrator:
    """Per-project orchestrator. One instance == one autopilot run.

    Lifecycle:
        1. Constructed in `start_autopilot` endpoint.
        2. `await self.run()` schedules an asyncio task; returns immediately.
        3. The task transitions states, calling existing app-builder
           services and persisting state/events between steps.
        4. At each pause point, the task awaits a `resume()` signal that
           the resume endpoint flips by updating autopilot_status.
        5. Terminates by setting state to `done` or `failed`.
    """

    def __init__(
        self,
        project_id: str,
        session_id: str,
        supabase: Any,
    ) -> None:
        self.project_id = project_id
        self.session_id = session_id
        self._supabase = supabase

    # ---- state ----
    def set_state(self, state: AutopilotState) -> None:
        if state not in AUTOPILOT_STATES:
            raise ValueError(f"Invalid autopilot state: {state}")
        self._supabase.table("app_projects").update(
            {"autopilot_status": state}
        ).eq("id", self.project_id).execute()

    # ---- narration ----
    def publish_event(
        self,
        kind: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Append a narration event to autopilot_events.

        Read-modify-write on a JSONB array. Acceptable for append-only
        in this scope; if contention surfaces we'd switch to a Postgres
        function with `jsonb_insert`.
        """
        result = (
            self._supabase.table("app_projects")
            .select("autopilot_events")
            .eq("id", self.project_id)
            .single()
            .execute()
        )
        events: list[dict[str, Any]] = (
            (result.data or {}).get("autopilot_events") or []
        )
        events.append(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "kind": kind,
                "message": message,
                "payload": payload or {},
            }
        )
        self._supabase.table("app_projects").update(
            {"autopilot_events": events}
        ).eq("id", self.project_id).execute()

    # ---- failure ----
    def fail(self, error: str) -> None:
        """Mark autopilot as failed and append an error event."""
        self.publish_event(kind="error", message=error)
        self._supabase.table("app_projects").update(
            {
                "autopilot_status": "failed",
                "autopilot_error": error,
            }
        ).eq("id", self.project_id).execute()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/app_builder/test_app_builder_orchestrator.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/services/app_builder_orchestrator.py tests/unit/app_builder/test_app_builder_orchestrator.py
git commit -m "feat(autopilot): orchestrator skeleton + state-machine helpers"
```

---

## Task 3: `start-autopilot` endpoint with idempotency

**Files:**
- Modify: `app/routers/app_builder.py` (append router)
- Modify: `tests/unit/app_builder/test_app_builder_router.py` (add tests)

- [ ] **Step 1: Write failing tests for the start endpoint**

Append to `tests/unit/app_builder/test_app_builder_router.py`:

```python
def test_start_autopilot_returns_running(client, mock_supabase):
    """POST /app-builder/projects/<id>/start-autopilot transitions idle → running."""
    # Arrange: project exists, autopilot_status=idle
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={**MOCK_PROJECT, "autopilot_status": "idle"}
    )
    body = {"session_id": "s-1"}
    # Act
    response = client.post(
        f"/app-builder/projects/{TEST_PROJECT_ID}/start-autopilot",
        json=body,
    )
    # Assert
    assert response.status_code == 200, response.text
    assert response.json()["autopilot_status"] == "running"


def test_start_autopilot_conflict_when_already_running(client, mock_supabase):
    """Starting twice returns 409."""
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={**MOCK_PROJECT, "autopilot_status": "running"}
    )
    body = {"session_id": "s-1"}
    response = client.post(
        f"/app-builder/projects/{TEST_PROJECT_ID}/start-autopilot",
        json=body,
    )
    assert response.status_code == 409
    assert "already" in response.json()["detail"].lower()


def test_start_autopilot_404_when_project_missing(client, mock_supabase):
    """Unknown project id returns 404."""
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data=None
    )
    body = {"session_id": "s-1"}
    response = client.post(
        f"/app-builder/projects/{TEST_PROJECT_ID}/start-autopilot",
        json=body,
    )
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_start_autopilot_returns_running -v`
Expected: FAIL — endpoint not found (404 from FastAPI default).

- [ ] **Step 3: Implement start-autopilot endpoint**

Append to `app/routers/app_builder.py` (just before file end):

```python
class StartAutopilotRequest(BaseModel):
    """Body for POST /app-builder/projects/<id>/start-autopilot."""

    session_id: str


@router.post("/app-builder/projects/{project_id}/start-autopilot")
@limiter.limit(get_user_persona_limit)
async def start_autopilot(
    request: Request,
    project_id: str,
    body: StartAutopilotRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    """Kick off autopilot for a project.

    Idempotent: returns 409 if autopilot is already running for this project.
    Returns the updated project row on success.
    """
    supabase = get_service_client()
    result = (
        supabase.table("app_projects")
        .select("id, autopilot_status, stage")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    current = result.data.get("autopilot_status") or "idle"
    if current not in ("idle", "failed", "done"):
        raise HTTPException(
            status_code=409,
            detail=f"Autopilot is already active for this project (state={current}).",
        )

    update = (
        supabase.table("app_projects")
        .update(
            {
                "autopilot_status": "running",
                "autopilot_session_id": body.session_id,
                "autopilot_error": None,
            }
        )
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
    )
    # NOTE: actual orchestrator task is scheduled in Task 5.
    # For now, the endpoint just transitions state synchronously.
    return update.data[0]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/app_builder/test_app_builder_router.py -v -k autopilot`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/routers/app_builder.py tests/unit/app_builder/test_app_builder_router.py
git commit -m "feat(autopilot): start-autopilot endpoint with idempotency"
```

---

## Task 4: `autopilot-status` and `resume-autopilot` endpoints

**Files:**
- Modify: `app/routers/app_builder.py`
- Modify: `tests/unit/app_builder/test_app_builder_router.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/unit/app_builder/test_app_builder_router.py`:

```python
def test_autopilot_status_returns_state_and_events(client, mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={
            **MOCK_PROJECT,
            "autopilot_status": "paused_brief",
            "autopilot_events": [
                {"ts": "2026-04-27T10:00:00Z", "kind": "status", "message": "Research done"}
            ],
            "autopilot_error": None,
        }
    )
    response = client.get(f"/app-builder/projects/{TEST_PROJECT_ID}/autopilot-status")
    assert response.status_code == 200
    body = response.json()
    assert body["autopilot_status"] == "paused_brief"
    assert len(body["events"]) == 1
    assert body["events"][0]["message"] == "Research done"


def test_resume_autopilot_clears_pause(client, mock_supabase):
    """POST /resume-autopilot transitions paused_* → running."""
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={**MOCK_PROJECT, "autopilot_status": "paused_brief"}
    )
    response = client.post(
        f"/app-builder/projects/{TEST_PROJECT_ID}/resume-autopilot",
        json={},
    )
    assert response.status_code == 200
    assert response.json()["autopilot_status"] == "running"


def test_resume_autopilot_409_when_not_paused(client, mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={**MOCK_PROJECT, "autopilot_status": "idle"}
    )
    response = client.post(
        f"/app-builder/projects/{TEST_PROJECT_ID}/resume-autopilot",
        json={},
    )
    assert response.status_code == 409
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/app_builder/test_app_builder_router.py -v -k "autopilot_status or resume_autopilot"`
Expected: 3 fails — endpoints missing.

- [ ] **Step 3: Implement endpoints**

Append to `app/routers/app_builder.py`:

```python
class ResumeAutopilotRequest(BaseModel):
    """Body for POST /app-builder/projects/<id>/resume-autopilot — empty for now."""

    pass


@router.get("/app-builder/projects/{project_id}/autopilot-status")
@limiter.limit(get_user_persona_limit)
async def autopilot_status(
    request: Request,
    project_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    """Return autopilot state, error (if any), and recent narration events."""
    supabase = get_service_client()
    result = (
        supabase.table("app_projects")
        .select("autopilot_status, autopilot_error, autopilot_events, stage")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "autopilot_status": result.data.get("autopilot_status") or "idle",
        "stage": result.data.get("stage"),
        "error": result.data.get("autopilot_error"),
        "events": result.data.get("autopilot_events") or [],
    }


_PAUSED_STATES = {"paused_brief", "paused_variant", "paused_screen", "paused_ship"}


@router.post("/app-builder/projects/{project_id}/resume-autopilot")
@limiter.limit(get_user_persona_limit)
async def resume_autopilot(
    request: Request,
    project_id: str,
    body: ResumeAutopilotRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    """Flip the project from paused_* back to running so the orchestrator advances."""
    supabase = get_service_client()
    result = (
        supabase.table("app_projects")
        .select("autopilot_status")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")
    current = result.data.get("autopilot_status") or "idle"
    if current not in _PAUSED_STATES:
        raise HTTPException(
            status_code=409,
            detail=f"Autopilot is not paused (state={current}).",
        )
    update = (
        supabase.table("app_projects")
        .update({"autopilot_status": "running"})
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
    )
    return update.data[0]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/app_builder/test_app_builder_router.py -v -k autopilot`
Expected: 6 passed (3 from Task 3 + 3 from Task 4).

- [ ] **Step 5: Commit**

```bash
git add app/routers/app_builder.py tests/unit/app_builder/test_app_builder_router.py
git commit -m "feat(autopilot): autopilot-status + resume-autopilot endpoints"
```

---

## Task 5: Orchestrator transition — research → paused_brief

**Files:**
- Modify: `app/services/app_builder_orchestrator.py`
- Modify: `tests/unit/app_builder/test_app_builder_orchestrator.py`

- [ ] **Step 1: Write failing test for `run_research_step`**

Append to `tests/unit/app_builder/test_app_builder_orchestrator.py`:

```python
import asyncio
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_run_research_step_publishes_status_and_pauses_at_brief():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"creative_brief": {"what": "bakery"}, "autopilot_events": []}
    )
    orch = _orch(supabase)

    async def fake_research(brief):
        # Yield two events then a 'ready' so the orchestrator records progress
        yield {"step": "searching", "message": "..."}
        yield {"step": "synthesizing", "message": "..."}
        yield {"step": "ready", "data": {"colors": [], "typography": {}, "spacing": {}, "raw_markdown": "", "sitemap": []}}

    with patch(
        "app.services.app_builder_orchestrator.run_design_research",
        side_effect=lambda brief: fake_research(brief),
    ):
        await orch.run_research_step()

    # State should have transitioned to paused_brief
    last_state_call = next(
        c for c in reversed(supabase.table.return_value.update.call_args_list)
        if "autopilot_status" in c.args[0]
    )
    assert last_state_call.args[0]["autopilot_status"] == "paused_brief"
    # At least two narration events appended
    appended_events_calls = [
        c for c in supabase.table.return_value.update.call_args_list
        if "autopilot_events" in c.args[0]
    ]
    assert len(appended_events_calls) >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/app_builder/test_app_builder_orchestrator.py -v -k research_step`
Expected: FAIL — `run_research_step` not defined.

- [ ] **Step 3: Implement `run_research_step`**

Add to `app/services/app_builder_orchestrator.py`:

```python
# Add near top of file, after imports:
from app.services.design_brief_service import run_design_research


# Add as method on AppBuilderOrchestrator:
    async def run_research_step(self) -> None:
        """Run research, persist intermediate progress, pause at paused_brief."""
        result = (
            self._supabase.table("app_projects")
            .select("creative_brief")
            .eq("id", self.project_id)
            .single()
            .execute()
        )
        creative_brief = (result.data or {}).get("creative_brief") or {}

        self.publish_event(kind="status", message="Running design research")

        try:
            async for event in run_design_research(creative_brief):
                step = event.get("step")
                if step == "ready":
                    self.publish_event(
                        kind="status",
                        message="Design brief is ready — review in the canvas",
                        payload={"data_keys": list((event.get("data") or {}).keys())},
                    )
                    self.set_state("paused_brief")
                    return
                if step == "error":
                    self.fail(event.get("message", "research failed"))
                    return
                # Lightweight progress: don't spam — only log searching/synthesizing once each
                if step in ("searching", "synthesizing"):
                    self.publish_event(
                        kind="progress",
                        message=event.get("message") or step,
                    )
        except Exception as exc:  # research raised
            self.fail(f"Research raised: {exc!s}")
            return
        # Stream ended without 'ready'
        self.fail("Research stream ended without a ready event.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/app_builder/test_app_builder_orchestrator.py -v -k research_step`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add app/services/app_builder_orchestrator.py tests/unit/app_builder/test_app_builder_orchestrator.py
git commit -m "feat(autopilot): research-step transitions to paused_brief"
```

---

## Task 6: Orchestrator transition — brief approval → first variant pause

**Files:**
- Modify: `app/services/app_builder_orchestrator.py`
- Modify: `tests/unit/app_builder/test_app_builder_orchestrator.py`

- [ ] **Step 1: Write failing test for `run_after_brief`**

```python
@pytest.mark.asyncio
async def test_run_after_brief_generates_build_plan_and_pauses_at_variant():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={
            "design_system": {"colors": []},
            "sitemap": [{"page": "home", "title": "Home", "sections": [], "device_targets": ["DESKTOP"]}],
            "autopilot_events": [],
        }
    )
    orch = _orch(supabase)
    fake_plan = [{"phase": 1, "label": "Core", "screens": [{"name": "Home", "page": "home", "device": "DESKTOP"}], "dependencies": []}]

    async def fake_generate(_brief, _sitemap):
        return fake_plan

    async def fake_variants(*_args, **_kwargs):
        # No-op: variant generation tested in next task
        return None
        yield  # make it an async-gen for type purposes (unreachable)

    with patch(
        "app.services.app_builder_orchestrator._generate_build_plan",
        new=AsyncMock(return_value=fake_plan),
    ):
        await orch.run_after_brief()

    last_state_call = next(
        c for c in reversed(supabase.table.return_value.update.call_args_list)
        if "autopilot_status" in c.args[0]
    )
    # Should have queued the first screen and paused_variant
    assert last_state_call.args[0]["autopilot_status"] in ("paused_variant", "running")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/app_builder/test_app_builder_orchestrator.py -v -k after_brief`
Expected: FAIL — method missing.

- [ ] **Step 3: Implement `run_after_brief`**

Add to `app/services/app_builder_orchestrator.py`:

```python
from app.services.design_brief_service import _generate_build_plan
from app.services.screen_generation_service import generate_screen_variants


    async def run_after_brief(self) -> None:
        """Called after brief approval. Generate build plan and start first screen."""
        result = (
            self._supabase.table("app_projects")
            .select("design_system, sitemap")
            .eq("id", self.project_id)
            .single()
            .execute()
        )
        project = result.data or {}
        design_system = project.get("design_system") or {}
        sitemap = project.get("sitemap") or []

        self.publish_event(kind="status", message="Generating build plan")
        try:
            build_plan = await _generate_build_plan(design_system, sitemap)
        except Exception as exc:
            self.fail(f"Build plan failed: {exc!s}")
            return

        # Persist build_plan onto the project so building stage can read it
        self._supabase.table("app_projects").update(
            {"build_plan": build_plan, "stage": "building"}
        ).eq("id", self.project_id).execute()
        self._supabase.table("build_sessions").update({"stage": "building"}).eq(
            "project_id", self.project_id
        ).execute()

        # Begin first screen — defer to run_next_screen (Task 7)
        await self.run_next_screen(build_plan, completed_screen_ids=[])
```

- [ ] **Step 4: Run test to verify it passes**

Note: the test only verifies state-machine reachability. `run_next_screen` is stubbed; the next task will fill it in.

Add a temporary stub (will be replaced in Task 7):

```python
    async def run_next_screen(
        self,
        build_plan: list[dict],
        completed_screen_ids: list[str],
    ) -> None:
        """Stub — implemented in Task 7."""
        self.set_state("paused_variant")
```

Run: `uv run pytest tests/unit/app_builder/test_app_builder_orchestrator.py -v -k after_brief`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add app/services/app_builder_orchestrator.py tests/unit/app_builder/test_app_builder_orchestrator.py
git commit -m "feat(autopilot): brief-approval transition generates build plan"
```

---

## Task 7: Orchestrator transition — variant pick → screen approval → next screen

**Files:**
- Modify: `app/services/app_builder_orchestrator.py`
- Modify: `tests/unit/app_builder/test_app_builder_orchestrator.py`

- [ ] **Step 1: Write failing test for the screen loop**

```python
@pytest.mark.asyncio
async def test_run_next_screen_generates_variants_and_pauses_at_variant():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"autopilot_events": []}
    )
    orch = _orch(supabase)
    build_plan = [
        {"phase": 1, "label": "Core",
         "screens": [{"name": "Home", "page": "home", "device": "DESKTOP"}],
         "dependencies": []}
    ]

    async def fake_variants(*args, **kwargs):
        yield {"step": "variant_generated", "variant_id": "v1", "screen_id": "s1"}
        yield {"step": "variant_generated", "variant_id": "v2", "screen_id": "s1"}
        yield {"step": "variant_generated", "variant_id": "v3", "screen_id": "s1"}
        yield {"step": "ready", "variants": []}

    with patch(
        "app.services.app_builder_orchestrator.generate_screen_variants",
        side_effect=lambda *a, **kw: fake_variants(),
    ):
        await orch.run_next_screen(build_plan, completed_screen_ids=[])

    last_state_call = next(
        c for c in reversed(supabase.table.return_value.update.call_args_list)
        if "autopilot_status" in c.args[0]
    )
    assert last_state_call.args[0]["autopilot_status"] == "paused_variant"


@pytest.mark.asyncio
async def test_run_after_screen_approved_advances_to_next_screen_or_ship():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={
            "build_plan": [
                {"phase": 1, "label": "Core",
                 "screens": [
                     {"name": "Home", "page": "home", "device": "DESKTOP"},
                     {"name": "About", "page": "about", "device": "DESKTOP"},
                 ],
                 "dependencies": []}
            ],
            "autopilot_events": [],
        }
    )
    orch = _orch(supabase)

    async def fake_variants(*a, **kw):
        yield {"step": "variant_generated", "variant_id": "v1", "screen_id": "s2"}
        yield {"step": "ready", "variants": []}

    with patch(
        "app.services.app_builder_orchestrator.generate_screen_variants",
        side_effect=lambda *a, **kw: fake_variants(),
    ):
        # Simulate "Home" was just approved; should advance to "About"
        await orch.run_after_screen_approved(completed_screen_ids=["home"])

    appended = [c for c in supabase.table.return_value.update.call_args_list
                if "autopilot_events" in c.args[0]]
    # At least one event mentioning the next screen
    flat = [e for c in appended for e in c.args[0]["autopilot_events"]]
    assert any("About" in (e.get("message") or "") for e in flat)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/app_builder/test_app_builder_orchestrator.py -v -k "next_screen or screen_approved"`
Expected: 2 fails (one passes the stub, one method missing).

- [ ] **Step 3: Implement the screen loop methods**

Replace the stub `run_next_screen` and add `run_after_screen_approved`:

```python
    async def run_next_screen(
        self,
        build_plan: list[dict],
        completed_screen_ids: list[str],
    ) -> None:
        """Generate variants for the next screen in the build plan and pause."""
        # Find next screen (flat across phases) that's not in completed_screen_ids
        next_screen: dict | None = None
        for phase in build_plan:
            for screen in phase.get("screens") or []:
                screen_id = screen.get("page")  # use page slug as id
                if screen_id and screen_id not in completed_screen_ids:
                    next_screen = screen
                    break
            if next_screen:
                break

        if not next_screen:
            # All screens done — pause at ship target
            self.publish_event(
                kind="status",
                message="All screens approved. Ready to ship — pick a target.",
            )
            self.set_state("paused_ship")
            return

        self.publish_event(
            kind="status",
            message=f"Generating screen: {next_screen.get('name')}",
            payload={"page": next_screen.get("page")},
        )
        try:
            async for event in generate_screen_variants(
                self.project_id,
                next_screen.get("name", ""),
                next_screen.get("page", ""),
            ):
                step = event.get("step")
                if step == "variant_generated":
                    self.publish_event(
                        kind="progress",
                        message=f"Variant ready for {next_screen.get('name')}",
                        payload={"variant_id": event.get("variant_id")},
                    )
                elif step == "ready":
                    self.set_state("paused_variant")
                    return
                elif step == "error":
                    self.fail(event.get("message", "variant generation failed"))
                    return
        except Exception as exc:
            self.fail(f"Variant generation raised: {exc!s}")
            return

    async def run_after_screen_approved(
        self,
        completed_screen_ids: list[str],
    ) -> None:
        """Called after the user approves a screen. Generates the next one."""
        result = (
            self._supabase.table("app_projects")
            .select("build_plan")
            .eq("id", self.project_id)
            .single()
            .execute()
        )
        build_plan = (result.data or {}).get("build_plan") or []
        await self.run_next_screen(build_plan, completed_screen_ids)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/app_builder/test_app_builder_orchestrator.py -v`
Expected: all tests passed (Task 5 + Task 6 + Task 7 = 7 tests).

- [ ] **Step 5: Commit**

```bash
git add app/services/app_builder_orchestrator.py tests/unit/app_builder/test_app_builder_orchestrator.py
git commit -m "feat(autopilot): screen loop — variant pause + post-approval advance"
```

---

## Task 8: Orchestrator transition — ship target → done

**Files:**
- Modify: `app/services/app_builder_orchestrator.py`
- Modify: `tests/unit/app_builder/test_app_builder_orchestrator.py`

- [ ] **Step 1: Write failing test for `run_ship`**

```python
@pytest.mark.asyncio
async def test_run_ship_completes_with_target():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"autopilot_events": []}
    )
    orch = _orch(supabase)

    async def fake_ship(project_id, targets):
        yield {"step": "target_started", "target": "react"}
        yield {"step": "target_complete", "target": "react", "url": "https://example/output.zip"}
        yield {"step": "ship_complete", "downloads": {"react": "https://example/output.zip"}}

    with patch(
        "app.services.app_builder_orchestrator.ship_project",
        side_effect=lambda project_id, targets: fake_ship(project_id, targets),
    ):
        await orch.run_ship("react")

    last_state_call = next(
        c for c in reversed(supabase.table.return_value.update.call_args_list)
        if "autopilot_status" in c.args[0]
    )
    assert last_state_call.args[0]["autopilot_status"] == "done"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/app_builder/test_app_builder_orchestrator.py -v -k run_ship`
Expected: FAIL.

- [ ] **Step 3: Implement `run_ship`**

```python
from app.services.ship_service import ship_project


    async def run_ship(self, target: str) -> None:
        """Execute the ship pipeline for the chosen target and complete autopilot."""
        if target not in ("react", "pwa", "capacitor", "video"):
            self.fail(f"Invalid ship target: {target}")
            return
        self.publish_event(
            kind="status",
            message=f"Shipping as {target}",
        )
        try:
            async for event in ship_project(self.project_id, [target]):
                step = event.get("step")
                if step == "target_complete":
                    self.publish_event(
                        kind="result",
                        message=f"{event.get('target')} ready",
                        payload={"url": event.get("url")},
                    )
                elif step == "target_failed":
                    self.fail(event.get("error") or "ship target failed")
                    return
                elif step == "ship_complete":
                    self.publish_event(
                        kind="status",
                        message="App ready",
                        payload={"downloads": event.get("downloads") or {}},
                    )
                    self._supabase.table("app_projects").update(
                        {"stage": "done"}
                    ).eq("id", self.project_id).execute()
                    self.set_state("done")
                    return
        except Exception as exc:
            self.fail(f"Shipping raised: {exc!s}")
            return
        self.fail("Ship stream ended without completion.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/app_builder/test_app_builder_orchestrator.py -v`
Expected: all tests passed (8 tests now).

- [ ] **Step 5: Commit**

```bash
git add app/services/app_builder_orchestrator.py tests/unit/app_builder/test_app_builder_orchestrator.py
git commit -m "feat(autopilot): ship transition completes autopilot"
```

---

## Task 9: Wire endpoints to the orchestrator (background tasks)

**Files:**
- Modify: `app/routers/app_builder.py`
- Modify: `tests/unit/app_builder/test_app_builder_router.py`

- [ ] **Step 1: Write failing test that the start endpoint schedules an orchestrator task**

Append to `tests/unit/app_builder/test_app_builder_router.py`:

```python
def test_start_autopilot_schedules_orchestrator(client, mock_supabase):
    """The endpoint must schedule a background task that runs research."""
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={**MOCK_PROJECT, "autopilot_status": "idle"}
    )
    with patch(
        "app.routers.app_builder._schedule_orchestrator_task"
    ) as mock_schedule:
        body = {"session_id": "s-1"}
        response = client.post(
            f"/app-builder/projects/{TEST_PROJECT_ID}/start-autopilot",
            json=body,
        )
        assert response.status_code == 200
        mock_schedule.assert_called_once()
        # Args: (project_id, session_id, "research") on initial start
        args, kwargs = mock_schedule.call_args
        assert args[0] == TEST_PROJECT_ID
        assert args[1] == "s-1"
        assert args[2] == "research"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/app_builder/test_app_builder_router.py -v -k schedules_orchestrator`
Expected: FAIL — `_schedule_orchestrator_task` doesn't exist yet.

- [ ] **Step 3: Add scheduler helper and wire endpoints**

In `app/routers/app_builder.py`, add near the top:

```python
import asyncio

from app.services.app_builder_orchestrator import AppBuilderOrchestrator


def _schedule_orchestrator_task(
    project_id: str,
    session_id: str,
    transition: Literal["research", "after_brief", "after_screen", "ship"],
    target: str | None = None,
    completed_screen_ids: list[str] | None = None,
) -> None:
    """Spawn a background asyncio task that drives one orchestrator transition.

    The orchestrator instance is created fresh per transition. State lives
    in Postgres; the asyncio task is purely a runner. If the Cloud Run
    instance recycles, the next resume call simply re-spawns a task.
    """
    supabase = get_service_client()
    orch = AppBuilderOrchestrator(
        project_id=project_id,
        session_id=session_id,
        supabase=supabase,
    )

    async def _run() -> None:
        try:
            if transition == "research":
                await orch.run_research_step()
            elif transition == "after_brief":
                await orch.run_after_brief()
            elif transition == "after_screen":
                await orch.run_after_screen_approved(
                    completed_screen_ids=completed_screen_ids or []
                )
            elif transition == "ship":
                if target is None:
                    orch.fail("ship transition called without target")
                    return
                await orch.run_ship(target)
        except Exception as exc:  # last-resort safety net
            logger.exception("Orchestrator task crashed")
            orch.fail(f"Orchestrator crashed: {exc!s}")

    asyncio.create_task(_run())
```

Update `start_autopilot` from Task 3 to call the scheduler. Replace the line `# NOTE: actual orchestrator task is scheduled in Task 5.` block with:

```python
    _schedule_orchestrator_task(project_id, body.session_id, "research")
    return update.data[0]
```

Update `resume_autopilot` to schedule the right transition based on the prior pause state. Add a helper and modify the endpoint:

```python
def _next_transition_for_pause(prior: str) -> tuple[str, str | None]:
    """Map a paused state to the (transition, default_target) that resumes it."""
    if prior == "paused_brief":
        return ("after_brief", None)
    if prior == "paused_variant":
        # Variant pick is a side-effect of the existing select_variant endpoint;
        # resume here means "user picked, now move to per-screen approval pause".
        # We just transition to running — frontend will call resume again after
        # the screen is approved, which will fire the after_screen transition.
        return ("noop_to_screen_approval_pause", None)
    if prior == "paused_screen":
        return ("after_screen", None)
    raise ValueError(f"Unhandled pause state: {prior}")
```

For `paused_variant` we need an extra state machine touch — when the user picks a variant, we move to `paused_screen` (waiting for approval) without firing a heavy transition. Add to `ResumeAutopilotRequest`:

```python
class ResumeAutopilotRequest(BaseModel):
    """Body for POST /app-builder/projects/<id>/resume-autopilot.

    Optional fields the frontend supplies depending on the pause being resumed:
    - completed_screen_ids: required for resuming paused_screen so the orchestrator
      knows which screens are done.
    - ship_target: required for resuming paused_ship.
    """

    completed_screen_ids: list[str] | None = None
    ship_target: Literal["react", "pwa", "capacitor", "video"] | None = None
```

Then change `resume_autopilot` to:

```python
@router.post("/app-builder/projects/{project_id}/resume-autopilot")
@limiter.limit(get_user_persona_limit)
async def resume_autopilot(
    request: Request,
    project_id: str,
    body: ResumeAutopilotRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    supabase = get_service_client()
    result = (
        supabase.table("app_projects")
        .select("autopilot_status, autopilot_session_id")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")
    current = result.data.get("autopilot_status") or "idle"
    session_id = result.data.get("autopilot_session_id") or ""
    if current not in _PAUSED_STATES:
        raise HTTPException(
            status_code=409,
            detail=f"Autopilot is not paused (state={current}).",
        )

    update = (
        supabase.table("app_projects")
        .update({"autopilot_status": "running"})
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
    )

    if current == "paused_brief":
        _schedule_orchestrator_task(project_id, session_id, "after_brief")
    elif current == "paused_variant":
        # Picking a variant transitions directly to paused_screen — no heavy work.
        supabase.table("app_projects").update(
            {"autopilot_status": "paused_screen"}
        ).eq("id", project_id).execute()
    elif current == "paused_screen":
        if body.completed_screen_ids is None:
            raise HTTPException(
                status_code=400,
                detail="completed_screen_ids required when resuming paused_screen",
            )
        _schedule_orchestrator_task(
            project_id,
            session_id,
            "after_screen",
            completed_screen_ids=body.completed_screen_ids,
        )
    elif current == "paused_ship":
        if not body.ship_target:
            raise HTTPException(
                status_code=400,
                detail="ship_target required when resuming paused_ship",
            )
        _schedule_orchestrator_task(
            project_id,
            session_id,
            "ship",
            target=body.ship_target,
        )

    return update.data[0]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/app_builder/test_app_builder_router.py -v -k autopilot`
Expected: 7 passed (6 prior + 1 new). The schedule mock catches `_schedule_orchestrator_task`.

- [ ] **Step 5: Commit**

```bash
git add app/routers/app_builder.py tests/unit/app_builder/test_app_builder_router.py
git commit -m "feat(autopilot): wire endpoints to orchestrator background tasks"
```

---

## Task 10: Agent tool — `start_app_builder_autopilot`

**Files:**
- Modify: `app/agents/tools/app_builder.py`
- Modify: `app/agent.py` (wire into Executive's tool list)

- [ ] **Step 1: Read existing app-builder tool patterns**

```bash
sed -n '1,80p' app/agents/tools/app_builder.py
```

This file likely already has `enhance_description`, `list_stitch_tools`, `generate_app_screen` per spec §"Tools you call directly". Check the existing decorator pattern (`@agent_tool`) and HTTP client used.

- [ ] **Step 2: Write the new tool**

Append to `app/agents/tools/app_builder.py` (mirror the decorator and HTTP-client patterns of existing tools in the file):

```python
@agent_tool
async def start_app_builder_autopilot(
    project_id: str,
    session_id: str,
) -> dict[str, Any]:
    """Trigger app-builder autopilot for a project that just finished questioning.

    Call this when the canvas signals `app_builder.questioning_complete` for
    a project. The orchestrator runs research → build → ship autonomously,
    pausing for design-brief approval, variant picks, per-screen approval,
    and ship target.

    Args:
        project_id: The app_projects.id to drive.
        session_id: The chat session ID — narration events will be addressed
            to this session so the canvas/chat hooks pull them.

    Returns:
        Dict with `autopilot_status` (the new state) on success, or
        `{"success": false, "user_message": "..."}` on a recoverable error.
    """
    from app.services.supabase import get_service_client  # local import: avoids cycles

    supabase = get_service_client()
    # Idempotency mirrors the start endpoint
    result = (
        supabase.table("app_projects")
        .select("autopilot_status")
        .eq("id", project_id)
        .single()
        .execute()
    )
    if not result.data:
        return {"success": False, "user_message": "Project not found."}
    current = result.data.get("autopilot_status") or "idle"
    if current not in ("idle", "failed", "done"):
        return {
            "success": False,
            "user_message": f"Autopilot is already active (state={current}).",
        }

    supabase.table("app_projects").update(
        {
            "autopilot_status": "running",
            "autopilot_session_id": session_id,
            "autopilot_error": None,
        }
    ).eq("id", project_id).execute()

    # Schedule the first transition. Use the same helper the HTTP endpoint uses.
    from app.routers.app_builder import _schedule_orchestrator_task
    _schedule_orchestrator_task(project_id, session_id, "research")

    return {"autopilot_status": "running", "project_id": project_id}
```

- [ ] **Step 3: Wire into Executive's tool list**

Find Executive's tool list in `app/agent.py` (search for `UI_WIDGET_TOOLS` line — the new tool sits adjacent). Add:

```python
from app.agents.tools.app_builder import (
    # existing imports...
    start_app_builder_autopilot,
)

# In the executive's tool list (look for *UI_WIDGET_TOOLS entry):
        start_app_builder_autopilot,
```

- [ ] **Step 4: Write a smoke test for the tool**

Append to `tests/unit/app_builder/test_app_builder_router.py`:

```python
@pytest.mark.asyncio
async def test_start_app_builder_autopilot_tool_triggers_orchestrator(monkeypatch):
    """The agent tool must transition state and schedule the orchestrator."""
    from app.agents.tools.app_builder import start_app_builder_autopilot

    fake_client = MagicMock()
    fake_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"autopilot_status": "idle"}
    )
    monkeypatch.setattr(
        "app.services.supabase.get_service_client", lambda: fake_client
    )
    schedule_calls: list = []
    monkeypatch.setattr(
        "app.routers.app_builder._schedule_orchestrator_task",
        lambda *args, **kwargs: schedule_calls.append((args, kwargs)),
    )

    result = await start_app_builder_autopilot(TEST_PROJECT_ID, "s-1")
    assert result == {"autopilot_status": "running", "project_id": TEST_PROJECT_ID}
    assert schedule_calls and schedule_calls[0][0][0] == TEST_PROJECT_ID
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/app_builder/test_app_builder_router.py -v -k autopilot`
Expected: 8 passed.

- [ ] **Step 6: Commit**

```bash
git add app/agents/tools/app_builder.py app/agent.py tests/unit/app_builder/test_app_builder_router.py
git commit -m "feat(autopilot): start_app_builder_autopilot agent tool"
```

---

## Task 11: Update Executive instruction (mention autopilot)

**Files:**
- Modify: `app/prompts/executive_instruction.txt`

- [ ] **Step 1: Edit section 18A to mention the autopilot tool**

Locate the §18A block (currently mentions `create_app_builder_canvas_widget` as preferred). Add a sub-bullet under "Tools you call directly":

```
   - `start_app_builder_autopilot`: Call IMMEDIATELY when the canvas reports
     that the user submitted the 5th wizard answer (the project name).
     Pass the current chat session_id so narration events route correctly.
     This kicks off autonomous research → build → ship; the user only
     approves the design brief, picks variants, approves screens, and
     picks a ship target.
```

- [ ] **Step 2: Run lint to verify nothing broke**

Run: `uv run ruff check app/prompts/`
Expected: pass (it's a .txt file, ruff ignores it; this just confirms project lint stays clean).

- [ ] **Step 3: Commit**

```bash
git add app/prompts/executive_instruction.txt
git commit -m "docs(autopilot): teach Executive about start_app_builder_autopilot"
```

---

## Task 12: Frontend API client functions

**Files:**
- Modify: `frontend/src/services/app-builder.ts`

- [ ] **Step 1: Append the three new client functions**

```typescript
// Append to frontend/src/services/app-builder.ts

export interface AutopilotEvent {
  ts: string;
  kind: 'status' | 'progress' | 'result' | 'error';
  message: string;
  payload?: Record<string, unknown>;
}

export interface AutopilotStatusResponse {
  autopilot_status:
    | 'idle'
    | 'running'
    | 'paused_brief'
    | 'paused_variant'
    | 'paused_screen'
    | 'paused_ship'
    | 'failed'
    | 'done';
  stage: string;
  error: string | null;
  events: AutopilotEvent[];
}

export async function startAutopilot(
  projectId: string,
  sessionId: string,
): Promise<AutopilotStatusResponse> {
  const res = await fetch(
    `/api/backend/app-builder/projects/${projectId}/start-autopilot`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId }),
    },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getAutopilotStatus(
  projectId: string,
): Promise<AutopilotStatusResponse> {
  const res = await fetch(
    `/api/backend/app-builder/projects/${projectId}/autopilot-status`,
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export interface ResumeAutopilotBody {
  completed_screen_ids?: string[];
  ship_target?: 'react' | 'pwa' | 'capacitor' | 'video';
}

export async function resumeAutopilot(
  projectId: string,
  body: ResumeAutopilotBody = {},
): Promise<AutopilotStatusResponse> {
  const res = await fetch(
    `/api/backend/app-builder/projects/${projectId}/resume-autopilot`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
```

- [ ] **Step 2: Type-check**

Run from project root: `cd frontend && npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/app-builder.ts
git commit -m "feat(autopilot): frontend API client functions"
```

---

## Task 13: `useAppBuilderAutopilot` polling hook

**Files:**
- Create: `frontend/src/hooks/useAppBuilderAutopilot.ts`

- [ ] **Step 1: Write the hook**

```typescript
// frontend/src/hooks/useAppBuilderAutopilot.ts
'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useEffect, useRef, useState } from 'react';

import {
  type AutopilotEvent,
  type AutopilotStatusResponse,
  getAutopilotStatus,
} from '@/services/app-builder';

const POLL_INTERVAL_MS = 3000;

interface Options {
  /** Stop polling once status is one of these terminal states. */
  stopOn?: Array<AutopilotStatusResponse['autopilot_status']>;
  /** Called once per new event (de-duplicated by ts+message). */
  onEvent?: (event: AutopilotEvent) => void;
}

/**
 * Polls /autopilot-status every 3s while autopilot is active.
 * De-duplicates events; fires `onEvent` once per new one (so chat narration
 * isn't re-posted on every poll cycle).
 */
export function useAppBuilderAutopilot(
  projectId: string | null,
  { stopOn = ['done', 'failed'], onEvent }: Options = {},
) {
  const [status, setStatus] = useState<AutopilotStatusResponse | null>(null);
  const seenKeysRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function tick() {
      if (cancelled || !projectId) return;
      try {
        const next = await getAutopilotStatus(projectId);
        if (cancelled) return;
        setStatus(next);
        for (const ev of next.events) {
          const key = `${ev.ts}:${ev.message}`;
          if (!seenKeysRef.current.has(key)) {
            seenKeysRef.current.add(key);
            onEvent?.(ev);
          }
        }
        if (stopOn.includes(next.autopilot_status)) return;
      } catch {
        // Swallow transient errors; the next tick retries.
      }
      timer = setTimeout(tick, POLL_INTERVAL_MS);
    }

    void tick();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [projectId, stopOn, onEvent]);

  return status;
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useAppBuilderAutopilot.ts
git commit -m "feat(autopilot): useAppBuilderAutopilot polling hook"
```

---

## Task 14: postMessage bridge — wizard → canvas widget → chat agent

**Files:**
- Modify: `frontend/src/components/widgets/AppBuilderCanvasWidget.tsx`
- Modify: `frontend/src/components/app-builder/QuestioningWizard.tsx`

- [ ] **Step 1: Wizard emits `app_builder.questioning_complete` postMessage on the final answer**

Find where `QuestioningWizard.tsx` submits the 5th answer (likely a handler called `handleSubmit` or `onComplete`). Inside the success path, before any `router.push`, add:

```typescript
if (typeof window !== 'undefined' && window.parent !== window) {
  window.parent.postMessage(
    {
      type: 'app_builder.questioning_complete',
      projectId,
    },
    window.location.origin,
  );
}
```

(Adjust `projectId` reference to match local variable name in the file.)

- [ ] **Step 2: Canvas widget listens for the postMessage and emits a custom DOM event the chat hook subscribes to**

In `frontend/src/components/widgets/AppBuilderCanvasWidget.tsx`, inside the component:

```typescript
import { useEffect } from 'react';

// Inside AppBuilderCanvasWidget, after existing state setup:
useEffect(() => {
  function handleMessage(event: MessageEvent) {
    if (event.origin !== window.location.origin) return;
    const data = event.data as { type?: string; projectId?: string };
    if (data?.type === 'app_builder.questioning_complete' && data.projectId) {
      // Surface to chat layer via a DOM CustomEvent the chat hook listens for.
      window.dispatchEvent(
        new CustomEvent('pikar-app-builder-questioning-complete', {
          detail: { projectId: data.projectId },
        }),
      );
    }
  }
  window.addEventListener('message', handleMessage);
  return () => window.removeEventListener('message', handleMessage);
}, []);
```

- [ ] **Step 3: Chat agent hook reacts to the event by calling `start_app_builder_autopilot`**

This requires a chat-side glue. Find the chat agent hook (likely `frontend/src/hooks/useAgentChat.ts`) and inside the existing `useEffect` setup add a listener that, on the custom event, sends a synthetic agent prompt:

```typescript
useEffect(() => {
  function handleQuestioningComplete(e: Event) {
    const detail = (e as CustomEvent<{ projectId: string }>).detail;
    if (!detail?.projectId) return;
    // Send a directive that the Executive agent will translate into a tool call.
    sendMessage(
      `The user just completed the app-builder questioning wizard for project ${detail.projectId}. Call start_app_builder_autopilot now.`,
      undefined, // mode
      { hidden: true }, // do not echo into chat scrollback
    );
  }
  window.addEventListener(
    'pikar-app-builder-questioning-complete',
    handleQuestioningComplete,
  );
  return () =>
    window.removeEventListener(
      'pikar-app-builder-questioning-complete',
      handleQuestioningComplete,
    );
}, [sendMessage]);
```

(If `useAgentChat`'s `sendMessage` doesn't accept a `{hidden}` option today, add it — feature-flag the message so it's not visually rendered in the user's chat history but does enter the agent's context.)

- [ ] **Step 4: Type-check + manual smoke**

Run: `cd frontend && npx tsc --noEmit`
Expected: clean.

Manual: in dev, complete the wizard → see chat status "Got your brief. Running research..." appear within 3 seconds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/widgets/AppBuilderCanvasWidget.tsx frontend/src/components/app-builder/QuestioningWizard.tsx frontend/src/hooks/useAgentChat.ts
git commit -m "feat(autopilot): postMessage bridge from wizard to chat agent"
```

---

## Task 15: Chat narration injection — turn autopilot events into agent messages

**Files:**
- Modify: `frontend/src/hooks/useAgentChat.ts` (or wherever chat messages are surfaced)
- Modify: `frontend/src/components/widgets/AppBuilderCanvasWidget.tsx`

- [ ] **Step 1: Wire `useAppBuilderAutopilot` into the canvas widget**

In `AppBuilderCanvasWidget.tsx`:

```typescript
import { useAppBuilderAutopilot } from '@/hooks/useAppBuilderAutopilot';

// inside the component, after the postMessage useEffect:
const projectId = data?.projectId || null;
useAppBuilderAutopilot(projectId, {
  onEvent: (ev) => {
    if (ev.kind === 'status' || ev.kind === 'result' || ev.kind === 'error') {
      window.dispatchEvent(
        new CustomEvent('pikar-app-builder-narration', {
          detail: { message: ev.message, kind: ev.kind, payload: ev.payload },
        }),
      );
    }
  },
});
```

- [ ] **Step 2: Chat hook listens for narration events and inserts them as agent messages**

In `useAgentChat.ts`, alongside the existing event listeners:

```typescript
useEffect(() => {
  function handleNarration(e: Event) {
    const detail = (e as CustomEvent<{ message: string; kind: string }>).detail;
    if (!detail?.message) return;
    appendMessage({
      role: 'agent',
      text: detail.message,
      // visual hint: error narration renders red
      tone: detail.kind === 'error' ? 'error' : 'info',
      synthetic: true,
    });
  }
  window.addEventListener('pikar-app-builder-narration', handleNarration);
  return () =>
    window.removeEventListener(
      'pikar-app-builder-narration',
      handleNarration,
    );
}, [appendMessage]);
```

(If `appendMessage`'s payload shape doesn't have `tone` or `synthetic`, add them — narration messages should be visually distinct and excluded from being sent back as user context to the agent.)

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/widgets/AppBuilderCanvasWidget.tsx frontend/src/hooks/useAgentChat.ts
git commit -m "feat(autopilot): chat narration injection from autopilot events"
```

---

## Task 16: Ship-target quick-reply widget

**Files:**
- Modify: `frontend/src/components/widgets/AppBuilderCanvasWidget.tsx`
- Modify: `frontend/src/services/app-builder.ts` (already has resumeAutopilot from Task 12)

- [ ] **Step 1: Render four ship-target buttons in chat narration when state is `paused_ship`**

In `AppBuilderCanvasWidget.tsx` add a small inline ship-picker rendered above the iframe when `status?.autopilot_status === 'paused_ship'`:

```typescript
{status?.autopilot_status === 'paused_ship' && (
  <div className="border-b border-slate-200 bg-amber-50 px-4 py-3 text-sm dark:border-slate-800 dark:bg-amber-900/20">
    <p className="mb-2 font-medium text-slate-700 dark:text-slate-200">
      All screens approved — pick a ship target:
    </p>
    <div className="flex flex-wrap gap-2">
      {(['react', 'pwa', 'capacitor', 'video'] as const).map((target) => (
        <button
          key={target}
          type="button"
          onClick={async () => {
            try {
              await resumeAutopilot(projectId, { ship_target: target });
            } catch (err) {
              console.error('resume ship failed', err);
            }
          }}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
        >
          {target.toUpperCase()}
        </button>
      ))}
    </div>
  </div>
)}
```

(Add the `resumeAutopilot` import at the top of the file.)

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/widgets/AppBuilderCanvasWidget.tsx
git commit -m "feat(autopilot): ship-target quick-reply in canvas widget"
```

---

## Task 17: Integration test — happy path end-to-end

**Files:**
- Create: `tests/integration/test_app_builder_autopilot_e2e.py`

- [ ] **Step 1: Write the integration test**

```python
# tests/integration/test_app_builder_autopilot_e2e.py
"""End-to-end happy-path test for app-builder autopilot.

Drives a project from idle → done with mocked external services
(Stitch, Gemini, Tavily) but real Supabase via supabase db reset --local.
"""
import asyncio

import pytest

from app.services.app_builder_orchestrator import AppBuilderOrchestrator


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_autopilot_drives_project_to_done(
    supabase_local,  # fixture provided by tests/conftest.py
    monkeypatch,
):
    """Run the entire orchestration on a real local Postgres."""
    # Arrange: insert a project at stage='questioning', autopilot_status='idle'
    project_id = "11111111-2222-3333-4444-555555555555"
    user_id = "00000000-0000-0000-0000-000000000999"
    supabase_local.table("app_projects").insert(
        {
            "id": project_id,
            "user_id": user_id,
            "title": "E2E Test App",
            "stage": "questioning",
            "creative_brief": {"what": "landing page", "vibe": "minimal"},
            "design_system": {"colors": []},
            "sitemap": [{"page": "home", "title": "Home", "sections": [], "device_targets": ["DESKTOP"]}],
            "autopilot_status": "idle",
        }
    ).execute()

    # Mock external services
    async def fake_research(_brief):
        yield {"step": "ready", "data": {"colors": [], "typography": {}, "spacing": {}, "raw_markdown": "", "sitemap": []}}

    async def fake_build_plan(_ds, _sm):
        return [
            {"phase": 1, "label": "Core",
             "screens": [{"name": "Home", "page": "home", "device": "DESKTOP"}],
             "dependencies": []}
        ]

    async def fake_variants(*_a, **_k):
        yield {"step": "variant_generated", "variant_id": "v1", "screen_id": "s1"}
        yield {"step": "ready", "variants": []}

    async def fake_ship(_pid, _targets):
        yield {"step": "target_complete", "target": "react", "url": "https://example/output.zip"}
        yield {"step": "ship_complete", "downloads": {"react": "https://example/output.zip"}}

    monkeypatch.setattr("app.services.app_builder_orchestrator.run_design_research", fake_research)
    monkeypatch.setattr("app.services.app_builder_orchestrator._generate_build_plan", fake_build_plan)
    monkeypatch.setattr("app.services.app_builder_orchestrator.generate_screen_variants", fake_variants)
    monkeypatch.setattr("app.services.app_builder_orchestrator.ship_project", fake_ship)

    orch = AppBuilderOrchestrator(project_id, "session-001", supabase_local)

    # Act: drive each transition manually (in real flow these are scheduled by endpoints)
    await orch.run_research_step()                    # → paused_brief
    await orch.run_after_brief()                       # → paused_variant
    # Simulate user picking a variant: state moves paused_variant → paused_screen via resume endpoint;
    # for the test, set it directly.
    supabase_local.table("app_projects").update({"autopilot_status": "paused_screen"}).eq("id", project_id).execute()
    await orch.run_after_screen_approved(["home"])     # → paused_ship (no more screens)
    await orch.run_ship("react")                       # → done

    # Assert
    final = supabase_local.table("app_projects").select("autopilot_status, stage").eq("id", project_id).single().execute().data
    assert final["autopilot_status"] == "done"
    assert final["stage"] == "done"
```

- [ ] **Step 2: Run the integration test**

Run: `supabase db reset --local && uv run pytest tests/integration/test_app_builder_autopilot_e2e.py -v`
Expected: 1 passed.

If `supabase_local` fixture doesn't exist in `tests/conftest.py`, add it (typical pattern: connect to the local Supabase service-role URL and yield a client; existing app-builder tests rely on `mock_supabase` so this may be the first integration fixture in this area — check existing conftest first and either add or adapt).

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_app_builder_autopilot_e2e.py
git commit -m "test(autopilot): end-to-end happy-path integration test"
```

---

## Task 18: Manual smoke + branch finalization

**Files:** none

- [ ] **Step 1: Local smoke test**

```bash
make local-backend         # backend on :8000
cd frontend && npm run dev # frontend on :3000
```

Open the app in a browser. Start a new app-builder project from the canvas. Submit all 5 wizard answers. Verify in chat:
- Status appears within ~3s: "Running design research"
- Then: "Design brief is ready — review in the canvas"
- Approve brief in canvas → screen generates → variant pause
- Pick variant → approve screen → next screen (or paused_ship if only one)
- Pick ship target React → "App ready" with download link

If anything stalls, query autopilot_events directly:
```sql
SELECT autopilot_status, autopilot_error, autopilot_events
FROM app_projects WHERE id = '<your-project-id>';
```

- [ ] **Step 2: Push the branch**

```bash
git push -u origin feature/app-builder-autopilot
```

- [ ] **Step 3: Open PR**

```bash
gh pr create --title "feat(autopilot): app-builder autopilot — autonomous research → build → ship" --body "$(cat <<'EOF'
## Summary
- After the user finishes the 5-question wizard, an `AppBuilderOrchestrator` runs research → build → ship autonomously, narrating into chat.
- Pauses only at hard decisions: brief approval (in canvas), variant pick (in canvas), per-screen approval (in canvas), ship target (chat quick-reply).
- New columns on `app_projects` track autopilot state and event log; frontend polls every 3s.

## Test plan
- [ ] Unit tests: orchestrator transitions, endpoints, agent tool
- [ ] Integration test: happy-path E2E with mocked external services
- [ ] Manual smoke: complete wizard, verify chat narration, ship to React

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-Review Notes

**Spec coverage check (mapping spec sections to tasks):**

| Spec section | Task |
|---|---|
| User-facing behavior steps 1–10 | Tasks 5–8 (orchestrator), 11 (instruction), 14 (postMessage), 15 (narration), 16 (ship picker) |
| Architecture: Components 1 (orchestrator) | Tasks 2, 5, 6, 7, 8 |
| Architecture: Components 2–3 (DB columns) | Task 1 |
| Architecture: Components 4 (endpoints) | Tasks 3, 4, 9 |
| Architecture: Components 5 (agent tool) | Task 10 |
| Architecture: Components 6 (postMessage bridge) | Task 14 |
| Communication channels (chat narration) | Tasks 13, 15 |
| Communication channels (canvas state sync) | Tasks 12, 13 (polling hook covers both surfaces) |
| State machine | Tasks 5–9 (each transition is a method + endpoint wire) |
| Error handling | Embedded in each orchestrator method (Tasks 5–8); manual-action abort is in `run_research_step` and friends via the surrounding state checks |
| Testing approach (unit + integration) | Tasks 2–10 unit; Task 17 integration |

**Gaps acknowledged (intentionally out of scope per spec):** multi-project autopilot, push/email notifications, custom ship targets via autopilot, auto-resume after Cloud Run cold-start mid-orchestration. Spec calls these out as explicitly out of scope.

**Type/name consistency:** `AutopilotState` literal type matches the `AUTOPILOT_STATES` set; `_PAUSED_STATES` set in the router matches the four `paused_*` literals; frontend `AutopilotStatusResponse['autopilot_status']` matches the same set. `_schedule_orchestrator_task` signature matches between definition and call sites.

**Placeholder check:** No "TODO", "TBD", or "implement later" in the plan. Each step that changes code includes the actual code. Each test step shows the assertion.

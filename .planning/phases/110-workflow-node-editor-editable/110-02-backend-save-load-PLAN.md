---
phase: 110-workflow-node-editor-editable
plan: 02
type: execute
wave: 2
depends_on: [110-01]
files_modified:
  - app/routers/workflows.py
  - app/workflows/engine.py
  - app/workflows/template_versions.py
  - tests/unit/workflows/test_template_versions_engine.py
  - tests/unit/routers/test_workflow_save_endpoint.py
  - frontend/src/types/api.generated.ts
autonomous: true
requirements:
  - NODEEDITOR-SAVE-01
  - NODEEDITOR-VERSION-01
  - NODEEDITOR-VERSION-02
  - NODEEDITOR-CONCURRENCY-01
gap_closure: false

must_haves:
  truths:
    - "PUT /workflows/templates/{id} accepts a JSON body with graph_nodes/graph_edges/graph_layout/comment, validates the If-Match header against the current version's saved_at, returns 412 with the latest version body on mismatch, returns 428 when If-Match is missing, and writes a new workflow_template_versions row + updates workflow_templates.current_version_id on success"
    - "GET /workflows/templates/{id} response includes an ETag HTTP header whose value is the current version's saved_at as a quoted ISO8601 string (e.g. ETag: \"2026-05-11T19:30:00.000Z\")"
    - "GET /workflows/templates/{id}/history returns a list of {version_number, saved_at, saved_by_user_id, saved_by_user_name, comment} ordered by version_number DESC"
    - "POST /workflows/templates/{id}/revert/{version_id} creates a NEW version (version_number = max+1) whose graph_* fields are copied from the target version and whose parent_version_id points at the target version; updates current_version_id; returns the new version row"
    - "When start_workflow_execution_atomic fires, the new execution row has template_version_id set to the template's current_version_id at the moment of insert (legacy in-flight executions are unaffected; older executions keep template_version_id IS NULL)"
    - "Clicking Edit on a seeded template (created_by IS NULL) creates a private copy in the calling user's namespace and redirects: PUT /templates/{seed_id} returns 409 with {copied_template_id: <new_id>} so the frontend re-routes the editor"
  artifacts:
    - path: "app/routers/workflows.py"
      provides: "PUT /workflows/templates/{id}, GET /workflows/templates/{id}/history, POST /workflows/templates/{id}/revert/{version_id}; ETag header added to GET /workflows/templates/{id}; WorkflowTemplateVersion Pydantic model + SaveTemplateRequest + HistoryItem"
      contains: "If-Match"
    - path: "app/workflows/template_versions.py"
      provides: "save_template_version() / list_template_history() / revert_template_to_version() / copy_seed_template_for_user() — atomic two-table transaction logic isolated from the main engine.py blob"
      contains: "async def save_template_version"
    - path: "app/workflows/engine.py"
      provides: "start_workflow_execution writes template_version_id to the new execution row by reading template.current_version_id; list_templates SELECT widened to include current_version_id"
      contains: "current_version_id"
    - path: "frontend/src/types/api.generated.ts"
      provides: "Regenerated OpenAPI types for WorkflowTemplateVersion + SaveTemplateRequest + HistoryItem + WorkflowTemplateResponse.current_version_id"
      contains: "WorkflowTemplateVersion"
  key_links:
    - from: "PUT /workflows/templates/{id}"
      to: "save_template_version() in app/workflows/template_versions.py"
      via: "Direct async function call"
      pattern: "save_template_version"
    - from: "save_template_version()"
      to: "workflow_template_versions INSERT + workflow_templates UPDATE current_version_id"
      via: "Two-statement transaction (Postgres function OR explicit BEGIN/COMMIT via supabase_client)"
      pattern: "RPC|transaction"
    - from: "start_workflow_execution_atomic RPC call site"
      to: "workflow_executions.template_version_id"
      via: "rpc_params['p_template_version_id'] = template.get('current_version_id')"
      pattern: "p_template_version_id"
---

<objective>
Ship the backend persistence layer for Phase 110. Adds three new endpoints (PUT for save with If-Match optimistic locking, GET history, POST revert), widens GET to emit ETag headers, isolates the two-table atomic write into a new `app/workflows/template_versions.py` module, and updates `start_workflow_execution` to pin executions to the current version. Plan 04 (frontend canvas) and Plan 05 (frontend history UI) consume this API directly.

Purpose: Materializes decisions 5 (Version rows), 6 (If-Match), and decision 3 partially (seed-copy-on-Edit). Engine execution logic stays unchanged — pinned executions still execute via the linear engine path because Phase 110 ships no branching nodes that actually run.
Output: ~3 new endpoints, ~1 new module, ~2 modified files, ~2 new test files (~40 unit tests target), 1 regenerated TS types file.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/110-workflow-node-editor-editable/110-CONTEXT.md
@.planning/phases/110-workflow-node-editor-editable/110-01-SUMMARY.md
@.planning/phases/109-workflow-node-editor-viewer/109-02-SUMMARY.md
@app/routers/workflows.py
@app/workflows/engine.py
@app/workflows/registry.py

<interfaces>
<!-- Phase 109 already shipped these (in app/routers/workflows.py:79-90 + 124-140): -->

class NodePosition(BaseModel):
    x: int
    y: int

NodeKind = Literal['trigger','agent-action','condition','parallel','merge','human-approval','output']

class GraphNode(BaseModel):
    id: str
    kind: NodeKind
    label: str
    config: dict[str, Any] | None = None

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    source_handle: str | None = None
    label: str | None = None

class WorkflowTemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    template_key: str | None = None
    version: int | None = None                       # LEGACY integer versioning
    lifecycle_status: str | None = None
    is_generated: bool | None = None
    personas_allowed: list[str] | None = None
    last_published_at: str | None = None
    graph_nodes: list[GraphNode] | None = None
    graph_edges: list[GraphEdge] | None = None
    graph_layout: dict[str, NodePosition] | None = None
    # NEW in this plan:
    # current_version_id: str | None = None         (added below)

<!-- Phase 109 already shipped these TS named exports in frontend/src/services/workflows.ts: -->
export interface NodePosition { x: number; y: number; }
export type NodeKind = 'trigger' | 'agent-action' | ...;
export interface GraphNode { id: string; kind: NodeKind; label: string; config?: Record<string, unknown>; }
export interface GraphEdge { id: string; source: string; target: string; source_handle?: string; label?: string; }

<!-- Existing engine helpers (read-only references for this plan): -->
class WorkflowEngine:
    async def list_templates(category, lifecycle_status, persona) -> list[dict]   # widened in 109-02
    async def get_template(template_id: str) -> dict[str, Any]                    # uses select("*")
    async def update_template_draft(*, template_id, user_id, updates) -> dict     # PATCH /templates/{id} - legacy path

<!-- Existing RPC: -->
start_workflow_execution_atomic(
    p_user_id UUID, p_template_id UUID, p_template_version INT DEFAULT NULL,
    p_started_by UUID DEFAULT NULL, p_run_source TEXT DEFAULT 'user_ui',
    p_name TEXT DEFAULT 'Workflow Execution', p_context JSONB DEFAULT '{}'::jsonb,
    p_max_concurrent INT DEFAULT 3, p_goal TEXT DEFAULT NULL
) RETURNS SETOF workflow_executions
-- Currently does NOT accept p_template_version_id UUID. Plan 02 widens it.
</interfaces>

<context_notes>
- The Pydantic model lives in `app/routers/workflows.py`, NOT `app/workflows/registry.py`. Phase 109-02 SUMMARY documented this rule. Add `WorkflowTemplateVersion` next to `WorkflowTemplateResponse` in the router file.
- `WorkflowEngine.list_templates` does an explicit field-by-field SELECT. Plan 109-02 widened it for graph fields. Plan 110-02 MUST also widen it for `current_version_id` — otherwise the column is silently dropped from the API response and Plan 05's version selector reads `undefined`.
- `start_workflow_execution_atomic` RPC needs a new optional parameter `p_template_version_id UUID DEFAULT NULL`. This is a CREATE OR REPLACE of the existing function, mirrored on the migration pattern from `20260511130100_atomic_workflow_execution_start_goal.sql` (which added `p_goal`). Append the new param LAST so existing callers omitting it stay valid.
  - Migration filename: `20260615000100_start_workflow_execution_pinned_version.sql` (timestamp +100s after Plan 01's migration to guarantee ordering).
  - This is a Plan 02 file — Plan 01 deliberately scoped the RPC update OUT so the migration is purely additive.
- The ETag value is the version row's `saved_at` (NOT the template row's `updated_at`). When current_version_id is non-NULL, the version's saved_at is canonical. For unsaved (legacy) templates where current_version_id IS NULL, fall back to the template's `updated_at`.
- 412 response body shape: full WorkflowTemplateResponse of the current state (so frontend can show "their changes" via existing render path). Set `ETag` header on the 412 response too (so a follow-up Overwrite PUT can re-send with the fresh ETag).
- 409 vs 412: 409 (Conflict) is used for the seed-copy fork (different concept — user tried to edit a seed). 412 (Precondition Failed) is for stale-write concurrency. Do NOT conflate.
- Two-table transactionality: choices in CONTEXT.md Claude's Discretion #6. Implement as a Postgres function `save_workflow_template_version(p_template_id UUID, p_user_id UUID, p_graph_nodes JSONB, p_graph_edges JSONB, p_graph_layout JSONB, p_comment TEXT, p_if_match_saved_at TIMESTAMPTZ)` that does the entire two-table write + optimistic-lock check atomically and RETURNS the new version row or NULL on If-Match mismatch. Define the function in the same Plan 02 migration (`20260615000100`). The Python layer just calls `.rpc()`.
- `created_by IS NULL` = seeded template. Editing a seed → create a private copy with the calling user's `created_by` set, copy all immutable fields (name, description, category, template_key, version, lifecycle_status, personas_allowed), then bootstrap the copy with a v1 version row containing the seed's current graph_* fields. Return 409 (NOT 200) with body `{copied_template_id: <new_id>, message: "Created your private copy of this seed template; redirecting to your copy"}` so the frontend re-routes the editor to the new URL.
- Branch hygiene: check `git branch --show-current` before every commit. Phase 109 had branch pollution issues from parallel GSD automation.
</context_notes>
</context>

<tasks>

<task type="auto">
  <name>Task 02-01: Postgres RPC update + new save_workflow_template_version function</name>
  <files>supabase/migrations/20260615000100_workflow_template_save_rpc.sql</files>
  <action>
Create a NEW migration file at `supabase/migrations/20260615000100_workflow_template_save_rpc.sql` (timestamp strictly after Plan 01's 20260615000000). This migration:

1. CREATE OR REPLACE `start_workflow_execution_atomic` to append a NEW final parameter `p_template_version_id UUID DEFAULT NULL`. Copy the body verbatim from `20260511130100_atomic_workflow_execution_start_goal.sql` and add the new column to BOTH the column list AND the VALUES clause in both INSERT branches (branch 1 = no concurrency limit; branch 2 = with limit). Use $BODY$ dollar quotes.

2. CREATE OR REPLACE a new function `save_workflow_template_version(...)` returning `SETOF workflow_template_versions`:

```sql
CREATE OR REPLACE FUNCTION save_workflow_template_version(
    p_template_id           UUID,
    p_user_id               UUID,
    p_graph_nodes           JSONB,
    p_graph_edges           JSONB,
    p_graph_layout          JSONB,
    p_comment               TEXT,
    p_if_match_saved_at     TIMESTAMPTZ,
    p_parent_version_id     UUID DEFAULT NULL    -- explicit override for revert flow
)
RETURNS SETOF workflow_template_versions
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $BODY$
DECLARE
    v_current_version  workflow_template_versions%ROWTYPE;
    v_next_number      INT;
    v_new_version      workflow_template_versions%ROWTYPE;
    v_parent_id        UUID;
BEGIN
    -- Load current version row (NULL if template has no version yet, e.g. seed pre-copy)
    SELECT wtv.* INTO v_current_version
    FROM workflow_template_versions wtv
    JOIN workflow_templates wt ON wt.current_version_id = wtv.id
    WHERE wt.id = p_template_id;

    -- If-Match check: only enforce when caller supplied an If-Match value AND a current version exists
    IF p_if_match_saved_at IS NOT NULL AND v_current_version.saved_at IS NOT NULL THEN
        IF v_current_version.saved_at <> p_if_match_saved_at THEN
            -- Stale write — return no rows; caller translates to HTTP 412
            RETURN;
        END IF;
    END IF;

    -- Compute next version number
    SELECT COALESCE(MAX(version_number), 0) + 1 INTO v_next_number
    FROM workflow_template_versions
    WHERE template_id = p_template_id;

    -- Parent: explicit override (for revert) OR current version's id
    v_parent_id := COALESCE(p_parent_version_id, v_current_version.id);

    -- Insert new version row
    INSERT INTO workflow_template_versions (
        template_id, version_number, parent_version_id,
        graph_nodes, graph_edges, graph_layout,
        saved_by_user_id, comment
    ) VALUES (
        p_template_id, v_next_number, v_parent_id,
        p_graph_nodes, p_graph_edges, p_graph_layout,
        p_user_id, p_comment
    )
    RETURNING * INTO v_new_version;

    -- Update template's current_version_id pointer
    UPDATE workflow_templates
    SET current_version_id = v_new_version.id,
        updated_at = now()
    WHERE id = p_template_id;

    -- Return the new version row
    RETURN NEXT v_new_version;
END;
$BODY$;
```

3. Grant EXECUTE to authenticated + service_role on `save_workflow_template_version`.

4. Inline rollback comment at the bottom.
  </action>
  <verify>
    <automated>node -e "const fs=require('fs');const text=fs.readFileSync('supabase/migrations/20260615000100_workflow_template_save_rpc.sql','utf8');for(const n of ['save_workflow_template_version','p_template_version_id UUID DEFAULT NULL','CREATE OR REPLACE FUNCTION start_workflow_execution_atomic','p_if_match_saved_at','RETURNS SETOF workflow_template_versions']){if(!text.includes(n)){console.error('MISSING:',n);process.exit(1);}}console.log('OK');"</automated>
  </verify>
  <done>Migration file exists; CREATE OR REPLACE of start_workflow_execution_atomic with new p_template_version_id parameter (appended LAST) preserves all existing callers; new save_workflow_template_version function does atomic two-table write with If-Match check. $BODY$ dollar quotes used throughout.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 02-02: New app/workflows/template_versions.py module (engine helpers + Pydantic models)</name>
  <files>app/workflows/template_versions.py, tests/unit/workflows/test_template_versions_engine.py</files>
  <behavior>
    Tests in test_template_versions_engine.py must assert:
    - save_template_version() with valid If-Match writes new row, returns new version dict, calls RPC exactly once with the right param shape (template_id, user_id, graph_nodes, graph_edges, graph_layout, comment, if_match_saved_at, parent_version_id=None)
    - save_template_version() with stale If-Match returns None (signal for 412)
    - save_template_version() with no If-Match (first save of a new template) passes p_if_match_saved_at=None and succeeds
    - list_template_history() returns rows ordered by version_number DESC, joined to auth user names if available (graceful fallback to user_id string)
    - revert_template_to_version() reads the target version's graph_*, calls save_template_version with explicit parent_version_id=target.id, returns the new version
    - copy_seed_template_for_user() inserts a workflow_templates row with created_by=user_id + copies name/description/category/etc from seed + bootstraps a v1 version row with the seed's current graph; returns the new template_id
    - All four helpers use supabase_client + execute_async (NEVER direct await .execute() per project memory)
    - All four helpers tolerate RPC returning an empty list (treat as failure / mismatch / not found)
  </behavior>
  <action>
Create `app/workflows/template_versions.py` with four async helpers + Pydantic models:

```python
"""Workflow template versioning helpers — Phase 110.

Isolated from app/workflows/engine.py to keep the two-table transactional logic
(workflow_template_versions writes + workflow_templates.current_version_id pointer
updates) out of the 1600-line engine blob. Plan 02 routes call into here directly.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

from app.persistence.supabase_client import supabase_client, execute_async


class WorkflowTemplateVersion(BaseModel):
    id: str
    template_id: str
    version_number: int
    parent_version_id: str | None = None
    graph_nodes: list[dict[str, Any]]
    graph_edges: list[dict[str, Any]]
    graph_layout: dict[str, Any] | None = None
    saved_by_user_id: str | None = None
    saved_at: str
    comment: str | None = None


class HistoryItem(BaseModel):
    version_number: int
    version_id: str
    saved_at: str
    saved_by_user_id: str | None = None
    saved_by_user_name: str | None = None     # optional resolved name
    comment: str | None = None


async def save_template_version(
    *,
    template_id: str,
    user_id: str,
    graph_nodes: list[dict[str, Any]],
    graph_edges: list[dict[str, Any]],
    graph_layout: dict[str, Any] | None,
    comment: str | None,
    if_match_saved_at: str | None,
    parent_version_id: str | None = None,
) -> WorkflowTemplateVersion | None:
    """Call save_workflow_template_version RPC. Returns None on stale If-Match (HTTP 412)."""
    client = supabase_client()
    res = await execute_async(
        client.rpc(
            "save_workflow_template_version",
            {
                "p_template_id": template_id,
                "p_user_id": user_id,
                "p_graph_nodes": graph_nodes,
                "p_graph_edges": graph_edges,
                "p_graph_layout": graph_layout,
                "p_comment": comment,
                "p_if_match_saved_at": if_match_saved_at,
                "p_parent_version_id": parent_version_id,
            },
        )
    )
    if not res.data:
        return None
    return WorkflowTemplateVersion(**res.data[0])


async def list_template_history(template_id: str) -> list[HistoryItem]:
    """Return all versions for a template, newest first."""
    # ...query workflow_template_versions WHERE template_id ORDER BY version_number DESC
    # ...optional LEFT JOIN to auth.users for saved_by_user_name (best-effort; may be NULL)


async def revert_template_to_version(
    *, template_id: str, version_id: str, user_id: str, if_match_saved_at: str
) -> WorkflowTemplateVersion | None:
    """Create a NEW version whose graph_* is copied from version_id.

    parent_version_id of the new version = version_id (the target being reverted to,
    NOT the current version — encodes the "branch" in history).
    """
    # ...SELECT target's graph_*; call save_template_version with parent_version_id=version_id


async def copy_seed_template_for_user(
    *, seed_template_id: str, user_id: str
) -> str:
    """For decision 3: clicking Edit on a created_by IS NULL seed creates a private copy.

    Returns the new template_id. Bootstraps a v1 workflow_template_versions row
    with the seed's current graph_* fields so the user lands on a sane initial state.
    Raises ValueError if seed_template_id is NOT a seed (created_by IS NOT NULL).
    """
    # ...SELECT seed; INSERT new row with created_by=user_id; INSERT v1 version; UPDATE pointer
```

Implement all four functions. Use `supabase_client` and `execute_async` (NOT the deprecated `supabase` shim, per reference_supabase_async_patterns memory). Add docstrings (>= 1 line each per pre-commit interrogate gate).

Tests at `tests/unit/workflows/test_template_versions_engine.py` (target 15-20 tests):
- Use `unittest.mock.AsyncMock` to mock `supabase_client()` returning a mock with `.rpc().execute()`.
- Mirror the patterns from `tests/unit/workflows/test_registry_graph_fields.py` (Phase 109-02 created it).
- Each test asserts call args + return shape.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/workflows/test_template_versions_engine.py -v 2>&1 | tail -20</automated>
  </verify>
  <done>Module + tests exist; >=15 unit tests pass; ruff + ty clean; supabase_client+execute_async used (not direct await .execute()).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 02-03: PUT /workflows/templates/{id} endpoint + ETag on GET + Pydantic request/response models</name>
  <files>app/routers/workflows.py, tests/unit/routers/test_workflow_save_endpoint.py</files>
  <behavior>
    Tests must assert:
    - GET /workflows/templates/{id} response has ETag header with quoted ISO8601 saved_at
    - GET /workflows/templates/{id} for a row with NULL current_version_id falls back to ETag of quoted updated_at (legacy compat)
    - PUT /workflows/templates/{id} without If-Match returns 428 Precondition Required
    - PUT /workflows/templates/{id} with mismatched If-Match returns 412 Precondition Failed with fresh template body in response + fresh ETag header
    - PUT /workflows/templates/{id} with matching If-Match returns 200 with new version row
    - PUT against a seed template (created_by IS NULL) where the user is NOT the seed owner returns 409 with copied_template_id in body
    - PUT against a non-existent template returns 404
    - PUT against a template owned by a different user (created_by != user_id AND NOT NULL) returns 403
    - Request body validation: missing graph_nodes → 422; graph_nodes not a list → 422; nodes with invalid kind → 422 (Pydantic Literal enforcement)
  </behavior>
  <action>
In `app/routers/workflows.py`:

1. Add `WorkflowTemplateVersion`, `SaveTemplateRequest`, `HistoryItem` Pydantic models inline next to `WorkflowTemplateResponse`:

```python
class SaveTemplateRequest(BaseModel):
    graph_nodes: list[GraphNode]
    graph_edges: list[GraphEdge]
    graph_layout: dict[str, NodePosition] | None = None
    comment: str | None = None

class WorkflowTemplateVersion(BaseModel):
    id: str
    template_id: str
    version_number: int
    parent_version_id: str | None = None
    graph_nodes: list[GraphNode]
    graph_edges: list[GraphEdge]
    graph_layout: dict[str, NodePosition] | None = None
    saved_by_user_id: str | None = None
    saved_at: str
    comment: str | None = None

class HistoryItem(BaseModel):
    version_number: int
    version_id: str
    saved_at: str
    saved_by_user_id: str | None = None
    saved_by_user_name: str | None = None
    comment: str | None = None
```

2. Widen `WorkflowTemplateResponse` with `current_version_id: str | None = None` (additional field; backward-compatible).

3. Modify `get_template` endpoint (currently at line ~433-447): after fetching the template, look up the current version's saved_at (if current_version_id is not None) OR fall back to template's updated_at. Set `response.headers["ETag"] = f'"{saved_at}"'` (quoted ISO8601). Return the standard JSONResponse with the header.

4. Add new endpoint `PUT /workflows/templates/{template_id}` (decorated with rate limiter, get_current_user_id dep):
   - Read `If-Match` header. If missing → raise 428 Precondition Required.
   - Strip quotes from If-Match value (clients typically send `"2026-05-11T..."`).
   - Fetch the template. If `created_by IS NULL` AND `user_id != some_admin_indicator` → call `copy_seed_template_for_user(seed_template_id, user_id)` and return 409 with `{copied_template_id, message}`.
   - If `created_by IS NOT NULL` AND `created_by != user_id` → raise 403.
   - Call `save_template_version(...)` with the If-Match value. If returns None → 412 with current state body + fresh ETag header.
   - Else return 200 with the new version row.

5. Add new endpoint `GET /workflows/templates/{template_id}/history`:
   - Call `list_template_history(template_id)`; return list[HistoryItem].
   - Auth: requires user_id; check created_by permission like get_template does.

6. Add new endpoint `POST /workflows/templates/{template_id}/revert/{version_id}`:
   - Read If-Match header (412 on mismatch); call `revert_template_to_version`; return new version row.

Tests at `tests/unit/routers/test_workflow_save_endpoint.py` (target 15-20 tests): FastAPI TestClient pattern from 109-02's `test_templates_api_returns_graph.py`. Mount only the workflows router; override `get_current_user_id`; mock `app.workflows.template_versions.save_template_version` etc.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/routers/test_workflow_save_endpoint.py -v 2>&1 | tail -25</automated>
  </verify>
  <done>Endpoint suite passes (>=15 tests); ETag header emitted on GET; 412/428/409/403/404/422 all handled with correct response bodies and headers.</done>
</task>

<task type="auto">
  <name>Task 02-04: Engine integration — version pinning in start_workflow_execution + widen list_templates SELECT</name>
  <files>app/workflows/engine.py</files>
  <action>
In `app/workflows/engine.py`:

1. Widen the explicit SELECT in `list_templates()` (currently at line ~152-156) to include `current_version_id`. Per Phase 109-02's lesson, this is a load-bearing change — without it, the column is silently dropped on the wire even though the Pydantic model accepts it.

2. In the section that calls `start_workflow_execution_atomic` RPC (around line 805-817), add `"p_template_version_id": template.get("current_version_id")` to the `rpc_params` dict. The RPC was updated in Task 02-01 to accept this parameter as the last optional UUID. Legacy templates with NULL current_version_id will pass NULL — the column on `workflow_executions` stays nullable, so this is safe.

3. Do NOT touch any other engine code. Especially do NOT modify the execution loop, the `step_executor` path, or any of the per-step logic. Phase 110's engine work is limited to (a) widening SELECT and (b) propagating template_version_id to the new column. The graph executor itself (Phase 3 work) is OUT OF SCOPE.

4. Do NOT touch `list_template_versions()` (the legacy method on `template_key` ordering). That stays for backward compat — Plan 02 adds NEW `list_template_history()` in the `template_versions.py` module (Task 02-02) which is a parallel API surface.
  </action>
  <verify>
    <automated>node -e "const fs=require('fs');const text=fs.readFileSync('app/workflows/engine.py','utf8');if(!text.includes('current_version_id')){console.error('MISSING: current_version_id in SELECT');process.exit(1);}if(!text.includes('p_template_version_id')){console.error('MISSING: p_template_version_id in RPC params');process.exit(1);}console.log('OK');"</automated>
  </verify>
  <done>list_templates SELECT contains current_version_id; rpc_params dict includes p_template_version_id keyed off template.get('current_version_id'). No other engine.py changes.</done>
</task>

<task type="auto">
  <name>Task 02-05: Regenerate OpenAPI types + verify frontend tsc clean</name>
  <files>frontend/src/types/api.generated.ts</files>
  <action>
1. From the project root, run `cd frontend && npm run generate:types`. This regenerates `frontend/src/types/api.generated.ts` from the live FastAPI OpenAPI schema. The new schemas `WorkflowTemplateVersion`, `SaveTemplateRequest`, `HistoryItem` and the new `current_version_id` field on `WorkflowTemplateResponse` will appear automatically.

2. Verify the types compile: `cd frontend && npx tsc --noEmit`.

3. If the codegen tool requires the server to be running (per Phase 109-02 pattern), use the alternate path: `uv run python -c "from app.fast_api_app import app; import json; print(json.dumps(app.openapi()))" > /tmp/openapi.json; cd frontend && npx openapi-typescript /tmp/openapi.json --output src/types/api.generated.ts`.

4. Spot-check: `grep "WorkflowTemplateVersion\|SaveTemplateRequest\|HistoryItem\|current_version_id" frontend/src/types/api.generated.ts` should return >=4 lines.

5. Do NOT manually edit `api.generated.ts` — it's a generated artifact. If types are wrong, fix the Pydantic model in Task 02-03.

6. Do NOT add new named exports to `frontend/src/services/workflows.ts` in this plan — that's Plan 04's responsibility (the frontend canvas plan adds saveTemplate/getTemplateHistory/revertTemplate consumer functions).
  </action>
  <verify>
    <automated>grep -c "WorkflowTemplateVersion\|SaveTemplateRequest\|HistoryItem\|current_version_id" frontend/src/types/api.generated.ts</automated>
  </verify>
  <done>api.generated.ts regenerated; contains all 4 new symbols; npx tsc --noEmit clean across frontend.</done>
</task>

</tasks>

<verification>
End-to-end checks:

1. PUT round-trip works: `curl -X PUT http://localhost:8000/workflows/templates/{id} -H "If-Match: \"<saved_at>\"" -d '{"graph_nodes":...}'` returns 200 with a new version row.
2. PUT with stale If-Match returns 412 with the fresh template body + a fresh ETag header.
3. PUT without If-Match returns 428.
4. GET emits ETag header on the response.
5. POST /revert/{version_id} returns a new version whose parent_version_id == target version_id.
6. Starting a workflow execution (via existing /start endpoint) populates `workflow_executions.template_version_id` from `template.current_version_id`.
7. All unit tests pass: `uv run pytest tests/unit/workflows/test_template_versions_engine.py tests/unit/routers/test_workflow_save_endpoint.py -v`.
8. Lint clean: `uv run ruff check app/workflows/template_versions.py app/routers/workflows.py app/workflows/engine.py tests/unit/workflows/test_template_versions_engine.py tests/unit/routers/test_workflow_save_endpoint.py --fix && uv run ruff format app/workflows/template_versions.py`.
9. Frontend tsc clean: `cd frontend && npx tsc --noEmit`.
10. Branch hygiene: `git branch --show-current` returns the Phase 110 branch (NOT main).
</verification>

<success_criteria>
This plan ships when:
- One new SQL migration: `supabase/migrations/20260615000100_workflow_template_save_rpc.sql` (~120-180 lines).
- One new Python module: `app/workflows/template_versions.py` (~250-350 lines).
- Two router endpoints added to `app/routers/workflows.py`: PUT /templates/{id}, GET /templates/{id}/history, POST /templates/{id}/revert/{version_id}.
- One existing endpoint modified: GET /templates/{id} adds ETag header.
- One engine method modified: `WorkflowEngine.list_templates` SELECT widened + start_workflow_execution_atomic RPC call params include p_template_version_id.
- Two new Pydantic models: `WorkflowTemplateVersion`, `SaveTemplateRequest`, `HistoryItem`.
- One regenerated TS types file (`api.generated.ts`).
- Two test files: `tests/unit/workflows/test_template_versions_engine.py` + `tests/unit/routers/test_workflow_save_endpoint.py` with combined >=30 passing tests.
- Plan SUMMARY committed.
- Addresses roadmap success criteria: #2 (Save creates new version row), #3 (run-time pinning to current_version_id), #4 (history endpoint backs the UI list), #5 (ETag + 412 + If-Match), #6 (412 includes fresh body for "view their changes").
</success_criteria>

<output>
After completion, create `.planning/phases/110-workflow-node-editor-editable/110-02-SUMMARY.md` with: duration metric, files created/modified, decisions made (especially around RPC vs explicit transaction, 409 vs 412 semantics, ETag value source), deviations from plan, and a "Ready for Plan 04" section describing the API surface frontend consumers should use.
</output>

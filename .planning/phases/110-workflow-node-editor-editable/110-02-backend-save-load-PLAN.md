---
phase: 110-workflow-node-editor-editable
plan: 02
type: execute
wave: 2
depends_on: [110-01]
files_modified:
  - supabase/migrations/20260615000100_workflow_template_save_rpc.sql
  - app/routers/workflows.py
  - app/workflows/engine.py
  - app/workflows/template_versions.py
  - tests/unit/workflows/test_template_versions_engine.py
  - tests/unit/routers/test_workflow_save_endpoint.py
  - tests/integration/test_etag_round_trip.py
  - tests/integration/test_linear_workflow_execution_post_versioning.py
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
    - "PUT /workflows/templates/{id} accepts a JSON body with graph_nodes/graph_edges/graph_layout/comment, validates the If-Match header against the current version's saved_at, returns 412 with the latest version body + fresh ETag in BOTH header AND response body on mismatch, returns 428 when If-Match is missing, and writes a new workflow_template_versions row + updates workflow_templates.current_version_id on success"
    - "ETag wire format is canonical and consistent everywhere: server emits and accepts QUOTED ISO8601 strings (e.g. ETag: \"2026-05-11T19:30:00.000000+00:00\"); If-Match parser strips surrounding quotes defensively; PUT 200 and PUT 412 responses both include the new/fresh ETag in the response BODY under the `etag` key (so clients never need a second GET to learn the next-write ETag)"
    - "GET /workflows/templates/{id} response includes an ETag HTTP header whose value is the current version's saved_at as a quoted ISO8601 string"
    - "GET /workflows/templates/{id}/history returns a list of {version_number, saved_at, saved_by_user_id, saved_by_user_name, comment} ordered by version_number DESC"
    - "POST /workflows/templates/{id}/revert/{version_id} creates a NEW version (version_number = max+1) whose graph_* fields are copied from the target version and whose parent_version_id points at the target version; updates current_version_id; returns the new version row"
    - "When start_workflow_execution_atomic fires, the new execution row has template_version_id set to the template's current_version_id at the moment of insert (legacy in-flight executions are unaffected; older executions keep template_version_id IS NULL)"
    - "Clicking Edit on a seeded template (created_by IS NULL) creates a private copy in the calling user's namespace and redirects: PUT /templates/{seed_id} returns 409 with the EXACT body {error: 'seed_template_immutable', copied_template_id: <uuid>, seed_name: <original seed name>, message: <human string>} so the frontend re-routes the editor"
    - "End-to-end linear-template execution (existing canonical seeded template) started via /start completes successfully post-migration with no changes to step ordering, outcomes, or timing — engine.execute_steps() and step_executor logic remain untouched; only the version pinning at execution START changes (ROADMAP criterion #9 — regression test in tests/integration/test_linear_workflow_execution_post_versioning.py)"
  artifacts:
    - path: "app/routers/workflows.py"
      provides: "PUT /workflows/templates/{id}, GET /workflows/templates/{id}/history, POST /workflows/templates/{id}/revert/{version_id}; ETag header added to GET /workflows/templates/{id}; WorkflowTemplateVersion Pydantic model + SaveTemplateRequest + HistoryItem + SeedForkResponse"
      contains: "If-Match"
    - path: "app/workflows/template_versions.py"
      provides: "save_template_version() / list_template_history() / revert_template_to_version() / copy_seed_template_for_user() — atomic two-table transaction logic isolated from the main engine.py blob"
      contains: "async def save_template_version"
    - path: "app/workflows/engine.py"
      provides: "start_workflow_execution writes template_version_id to the new execution row by reading template.current_version_id; list_templates SELECT widened to include current_version_id"
      contains: "current_version_id"
    - path: "frontend/src/types/api.generated.ts"
      provides: "Regenerated OpenAPI types for WorkflowTemplateVersion + SaveTemplateRequest + HistoryItem + SeedForkResponse + WorkflowTemplateResponse.current_version_id"
      contains: "WorkflowTemplateVersion"
    - path: "supabase/migrations/20260615000100_workflow_template_save_rpc.sql"
      provides: "DROP FUNCTION then CREATE FUNCTION for start_workflow_execution_atomic with new p_template_version_id parameter (NOT a CREATE OR REPLACE — signature change requires drop+create); plus new save_workflow_template_version function"
      contains: "DROP FUNCTION IF EXISTS start_workflow_execution_atomic"
    - path: "tests/integration/test_etag_round_trip.py"
      provides: "ETag wire-format parity tests: GET → ETag header captured → PUT with that exact ETag returns 200; PUT with stripped-quotes ETag returns 200 (defensive); PUT with mismatched ETag returns 412 with quoted ETag in body"
      contains: "test_etag_round_trip"
    - path: "tests/integration/test_linear_workflow_execution_post_versioning.py"
      provides: "ROADMAP criterion #9 regression test — existing canonical linear-template (e.g. content-creation seed) executes end-to-end through /start with same step ordering and outcomes pre- and post-Phase 110 migration"
      contains: "test_linear_execution_unchanged"
  key_links:
    - from: "PUT /workflows/templates/{id}"
      to: "save_template_version() in app/workflows/template_versions.py"
      via: "Direct async function call"
      pattern: "save_template_version"
    - from: "save_template_version()"
      to: "workflow_template_versions INSERT + workflow_templates UPDATE current_version_id"
      via: "Postgres function save_workflow_template_version (atomic two-table transaction)"
      pattern: "save_workflow_template_version"
    - from: "start_workflow_execution_atomic RPC call site"
      to: "workflow_executions.template_version_id"
      via: "rpc_params['p_template_version_id'] = template.get('current_version_id')"
      pattern: "p_template_version_id"
    - from: "GET /workflows/templates/{id}/history"
      to: "app/workflows/template_versions.py:list_template_history()"
      via: "Direct async function call; consumed by Plan 110-05 HistoryPane"
      pattern: "list_template_history"
    - from: "POST /workflows/templates/{id}/revert/{version_id}"
      to: "app/workflows/template_versions.py:revert_template_to_version()"
      via: "Direct async function call; consumed by Plan 110-05 HistoryPane Revert button"
      pattern: "revert_template_to_version"
---

<objective>
Ship the backend persistence layer for Phase 110. Adds three new endpoints (PUT for save with If-Match optimistic locking, GET history, POST revert), widens GET to emit ETag headers, isolates the two-table atomic write into a new `app/workflows/template_versions.py` module, and updates `start_workflow_execution` to pin executions to the current version. Plan 04 (frontend canvas) and Plan 05 (frontend history UI) consume this API directly.

Purpose: Materializes decisions 5 (Version rows), 6 (If-Match), and decision 3 partially (seed-copy-on-Edit). Engine execution logic stays unchanged — pinned executions still execute via the linear engine path because Phase 110 ships no branching nodes that actually run. ROADMAP criterion #9 (linear engine non-regression) is asserted via an end-to-end integration test added in this plan.
Output: ~3 new endpoints, ~1 new module, ~2 modified files, ~2 new unit test files (~40 unit tests target), ~2 new integration test files (ETag round-trip + linear engine regression), 1 regenerated TS types file.
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
@supabase/migrations/0051_workflow_lifecycle_and_execution_metadata.sql
@supabase/migrations/20260511130100_atomic_workflow_execution_start_goal.sql

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

<!-- Existing RPC (live signature, observed in 20260511130100): -->
start_workflow_execution_atomic(
    p_user_id          UUID,
    p_template_id      UUID,
    p_template_version INT     DEFAULT NULL,
    p_started_by       UUID    DEFAULT NULL,
    p_run_source       TEXT    DEFAULT 'user_ui',
    p_name             TEXT    DEFAULT 'Workflow Execution',
    p_context          JSONB   DEFAULT '{}'::jsonb,
    p_max_concurrent   INT     DEFAULT 3,
    p_goal             TEXT    DEFAULT NULL
) RETURNS SETOF workflow_executions
-- Currently does NOT accept p_template_version_id UUID. Plan 02 widens it.
-- IMPORTANT: signature change (adding a 10th parameter) requires DROP FUNCTION
-- before CREATE — `CREATE OR REPLACE` does NOT work across argument-list changes.
</interfaces>

<context_notes>
- The Pydantic model lives in `app/routers/workflows.py`, NOT `app/workflows/registry.py`. Phase 109-02 SUMMARY documented this rule. Add `WorkflowTemplateVersion` next to `WorkflowTemplateResponse` in the router file.
- `WorkflowEngine.list_templates` does an explicit field-by-field SELECT. Plan 109-02 widened it for graph fields. Plan 110-02 MUST also widen it for `current_version_id` — otherwise the column is silently dropped from the API response and Plan 05's version selector reads `undefined`. Task 02-04 includes a behavioral mock-based test (NOT a string grep) asserting this.
- `start_workflow_execution_atomic` RPC needs a new optional parameter `p_template_version_id UUID DEFAULT NULL`. **B-3 fix: this is a SIGNATURE CHANGE (9-arg → 10-arg). PostgreSQL's `CREATE OR REPLACE FUNCTION` will FAIL across argument-list changes.** The migration MUST `DROP FUNCTION IF EXISTS start_workflow_execution_atomic(UUID, UUID, INT, UUID, TEXT, TEXT, JSONB, INT, TEXT) CASCADE;` BEFORE `CREATE OR REPLACE FUNCTION ...` with the new 10-arg signature. Task 02-01 SQL block below specifies exact DDL ordering.
  - Migration filename: `20260615000100_workflow_template_save_rpc.sql` (timestamp +100s after Plan 01's migration to guarantee ordering).
  - **Caller audit precondition** for Task 02-01: run `grep -rn 'start_workflow_execution_atomic' app/ supabase/ tests/` and verify EVERY caller uses named-keyword `.rpc()` invocation (NOT positional). Positional callers would break across the signature change. Regression test asserts the existing 9-arg call shape (omitting p_template_version_id) still works via the NULL default.
  - This is a Plan 02 file — Plan 01 deliberately scoped the RPC update OUT so the migration is purely additive at the schema level.
- ETag value comes from the version row's `saved_at` (NOT the template row's `updated_at`). When current_version_id is non-NULL, the version's saved_at is canonical. For unsaved (legacy) templates where current_version_id IS NULL, fall back to the template's `updated_at`. The wire format is `f'"{saved_at_iso}"'` — literal double-quotes around the ISO8601 string — per RFC 7232.
- **B-2 ETag wire format (canonical decision):** server always emits AND accepts quoted ISO8601 in both the `ETag` response header and the `If-Match` request header. Server defensively strips surrounding double-quotes from incoming If-Match values (clients should send them quoted, but tolerate either). PUT 200 and PUT 412 responses include the new/fresh ETag inside the response BODY under the `etag` key (so the client never needs a follow-up GET to learn the next-write ETag). Plan 04 and Plan 05's saveTemplate consumer reads `body.etag` (not `res.headers.get('ETag')`) after PUT — the body is canonical.
- **W-4 seed-copy 409 body shape:** the 409 response body MUST be the exact JSON below. Plan 04's `CopyForkError` reads `body.seed_name` and uses it in the redirect toast — the key must exist. Sketched as a Pydantic `SeedForkResponse` model in Task 02-03 to enforce shape:
  ```json
  {
    "error": "seed_template_immutable",
    "copied_template_id": "<uuid>",
    "seed_name": "<original seed name>",
    "message": "Seed templates can't be edited directly. A private copy has been created."
  }
  ```
- 409 vs 412: 409 (Conflict) is used for the seed-copy fork (different concept — user tried to edit a seed). 412 (Precondition Failed) is for stale-write concurrency. Do NOT conflate.
- Two-table transactionality: choices in CONTEXT.md Claude's Discretion #6. Implement as a Postgres function `save_workflow_template_version(p_template_id UUID, p_user_id UUID, p_graph_nodes JSONB, p_graph_edges JSONB, p_graph_layout JSONB, p_comment TEXT, p_if_match_saved_at TIMESTAMPTZ)` that does the entire two-table write + optimistic-lock check atomically and RETURNS the new version row or NULL on If-Match mismatch. Define the function in the same Plan 02 migration (`20260615000100`). The Python layer just calls `.rpc()`.
- `created_by IS NULL` = seeded template. Editing a seed → create a private copy with the calling user's `created_by` set, copy all immutable fields (name, description, category, template_key, version, lifecycle_status, personas_allowed), then bootstrap the copy with a v1 version row containing the seed's current graph_* fields. Return 409 (NOT 200) with the SeedForkResponse body (W-4) so the frontend re-routes the editor to the new URL.
- Branch hygiene: check `git branch --show-current` before every commit. Phase 109 had branch pollution issues from parallel GSD automation. Every task in this plan includes a branch-check automated verify step (W-6).
- **W-8 ROADMAP criterion #9 ownership:** the linear engine must continue to execute existing canonical seeded templates exactly as before. Plan 02 owns the regression test (`tests/integration/test_linear_workflow_execution_post_versioning.py`) that asserts this end-to-end: start a known seed (e.g. content-creation pipeline) post-migration, walk through the steps, assert ordering/outcomes match a recorded baseline.
</context_notes>
</context>

<tasks>

<task type="auto">
  <name>Task 02-01: Postgres RPC update (DROP + CREATE) + new save_workflow_template_version function</name>
  <files>supabase/migrations/20260615000100_workflow_template_save_rpc.sql</files>
  <action>
PRECONDITION 1: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted (W-6).

PRECONDITION 2: Audit all existing callers of `start_workflow_execution_atomic` to verify they use named-keyword `.rpc()` invocation (NOT positional args). The signature change from 9 → 10 parameters would silently break any positional caller.

```bash
grep -rn 'start_workflow_execution_atomic' app/ supabase/ tests/
```

Inspect each match. Expected pattern: `client.rpc("start_workflow_execution_atomic", {"p_user_id": ..., "p_template_id": ..., ...})` — named params via dict. If ANY caller uses positional args (e.g. `client.rpc("start_workflow_execution_atomic", [user_id, template_id, ...])`), STOP and fix the caller to named-keyword form before proceeding — this is a Phase 110 prerequisite, not a Plan 02 deliverable. Document the audit result in commit message.

Create a NEW migration file at `supabase/migrations/20260615000100_workflow_template_save_rpc.sql` (timestamp strictly after Plan 01's 20260615000000). This migration:

1. **B-3 fix:** DROP the existing function FIRST (signature change requires it; CREATE OR REPLACE alone fails on argument-list change):

```sql
-- Drop the existing 9-arg signature before recreating with 10 args.
-- Mandatory: CREATE OR REPLACE FUNCTION rejects argument-list changes.
DROP FUNCTION IF EXISTS start_workflow_execution_atomic(
    UUID, UUID, INT, UUID, TEXT, TEXT, JSONB, INT, TEXT
) CASCADE;
```

2. CREATE OR REPLACE `start_workflow_execution_atomic` with the new 10-arg signature, appending `p_template_version_id UUID DEFAULT NULL` as the LAST parameter:

```sql
CREATE OR REPLACE FUNCTION start_workflow_execution_atomic(
    p_user_id              UUID,
    p_template_id          UUID,
    p_template_version     INT     DEFAULT NULL,
    p_started_by           UUID    DEFAULT NULL,
    p_run_source           TEXT    DEFAULT 'user_ui',
    p_name                 TEXT    DEFAULT 'Workflow Execution',
    p_context              JSONB   DEFAULT '{}'::jsonb,
    p_max_concurrent       INT     DEFAULT 3,
    p_goal                 TEXT    DEFAULT NULL,
    p_template_version_id  UUID    DEFAULT NULL    -- NEW (10th param)
)
RETURNS SETOF workflow_executions
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $BODY$
DECLARE
    v_started_by UUID;
BEGIN
    v_started_by := COALESCE(p_started_by, p_user_id);

    -- Branch 1: no concurrency limit (unlimited)
    IF p_max_concurrent <= 0 THEN
        RETURN QUERY
        INSERT INTO workflow_executions (
            user_id, template_id, template_version, template_version_id,
            started_by, run_source, name, goal,
            status, current_phase_index, current_step_index, context
        ) VALUES (
            p_user_id, p_template_id, p_template_version, p_template_version_id,
            v_started_by, p_run_source, p_name, p_goal,
            'pending', 0, 0, p_context
        )
        RETURNING *;
        RETURN;
    END IF;

    -- Branch 2: concurrency-limited
    RETURN QUERY
    INSERT INTO workflow_executions (
        user_id, template_id, template_version, template_version_id,
        started_by, run_source, name, goal,
        status, current_phase_index, current_step_index, context
    )
    SELECT
        p_user_id, p_template_id, p_template_version, p_template_version_id,
        v_started_by, p_run_source, p_name, p_goal,
        'pending', 0, 0, p_context
    WHERE (
        SELECT COUNT(*) FROM workflow_executions
        WHERE user_id = p_user_id
          AND status IN ('pending','running','paused','waiting_approval')
    ) < p_max_concurrent
    RETURNING *;
END;
$BODY$;

GRANT EXECUTE ON FUNCTION start_workflow_execution_atomic(
    UUID, UUID, INT, UUID, TEXT, TEXT, JSONB, INT, TEXT, UUID
) TO authenticated;

GRANT EXECUTE ON FUNCTION start_workflow_execution_atomic(
    UUID, UUID, INT, UUID, TEXT, TEXT, JSONB, INT, TEXT, UUID
) TO service_role;
```

Body is copied verbatim from `20260511130100_atomic_workflow_execution_start_goal.sql` with one addition: `template_version_id` in BOTH the column list AND the VALUES clause in both branches (no-limit and concurrency-limited). Both INSERTs propagate the new column.

3. CREATE OR REPLACE a new function `save_workflow_template_version(...)` returning `SETOF workflow_template_versions`:

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

4. Grant EXECUTE to authenticated + service_role on `save_workflow_template_version`.

5. Inline rollback comment at the bottom (mirror Plan 01 pattern).

6. Add a regression test scaffold note in the SQL comments: "An end-to-end regression test for the existing 9-arg caller shape (omitting p_template_version_id) lives in `tests/integration/test_linear_workflow_execution_post_versioning.py` — confirms NULL default lets all existing callers keep working unchanged."
  </action>
  <verify>
    <automated>node -e "const fs=require('fs');const text=fs.readFileSync('supabase/migrations/20260615000100_workflow_template_save_rpc.sql','utf8');const needed=['DROP FUNCTION IF EXISTS start_workflow_execution_atomic','save_workflow_template_version','p_template_version_id UUID DEFAULT NULL','CREATE OR REPLACE FUNCTION start_workflow_execution_atomic','p_if_match_saved_at','RETURNS SETOF workflow_template_versions'];for(const n of needed){if(!text.includes(n)){console.error('MISSING:',n);process.exit(1);}}console.log('OK');"</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Migration file exists; DROP FUNCTION precedes CREATE OR REPLACE for start_workflow_execution_atomic; new p_template_version_id parameter (appended LAST) preserves all existing named-keyword callers; new save_workflow_template_version function does atomic two-table write with If-Match check. $BODY$ dollar quotes used throughout. Caller audit committed in commit message.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 02-02: New app/workflows/template_versions.py module (engine helpers + Pydantic models)</name>
  <files>app/workflows/template_versions.py, tests/unit/workflows/test_template_versions_engine.py</files>
  <behavior>
    Tests in test_template_versions_engine.py must assert (target 15-20 tests):
    - save_template_version() with valid If-Match writes new row, returns new version dict, calls RPC exactly once with the right param shape (template_id, user_id, graph_nodes, graph_edges, graph_layout, comment, if_match_saved_at, parent_version_id=None)
    - save_template_version() with stale If-Match returns None (signal for 412)
    - save_template_version() with no If-Match (first save of a new template) passes p_if_match_saved_at=None and succeeds
    - list_template_history() returns rows ordered by version_number DESC, joined to auth user names if available (graceful fallback to user_id string)
    - revert_template_to_version() reads the target version's graph_*, calls save_template_version with explicit parent_version_id=target.id, returns the new version
    - copy_seed_template_for_user() inserts a workflow_templates row with created_by=user_id + copies name/description/category/etc from seed + bootstraps a v1 version row with the seed's current graph; returns the new template_id
    - copy_seed_template_for_user() raises ValueError when the source template's created_by is NOT NULL (not a seed)
    - All four helpers use supabase_client + execute_async (NEVER direct await .execute() per project memory)
    - All four helpers tolerate RPC returning an empty list (treat as failure / mismatch / not found)
  </behavior>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

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
) -> dict[str, Any]:
    """For decision 3: clicking Edit on a created_by IS NULL seed creates a private copy.

    Returns a dict {copied_template_id, seed_name} so the caller (PUT handler) can
    build the SeedForkResponse 409 body. Bootstraps a v1 workflow_template_versions
    row with the seed's current graph_* fields so the user lands on a sane initial state.
    Raises ValueError if seed_template_id is NOT a seed (created_by IS NOT NULL).
    """
    # ...SELECT seed; assert created_by IS NULL else raise ValueError;
    # ...INSERT new workflow_templates row with created_by=user_id;
    # ...INSERT v1 workflow_template_versions row; UPDATE pointer; return {id, name}
```

Implement all four functions. Use `supabase_client` and `execute_async` (NOT the deprecated `supabase` shim, per reference_supabase_async_patterns memory). Add docstrings (>= 1 line each per pre-commit interrogate gate).

Tests at `tests/unit/workflows/test_template_versions_engine.py` (target 15-20 tests):
- Use `unittest.mock.AsyncMock` to mock `supabase_client()` returning a mock with `.rpc().execute()`.
- Mirror the patterns from `tests/unit/workflows/test_registry_graph_fields.py` (Phase 109-02 created it).
- Each test asserts call args + return shape.
- Add one test for `copy_seed_template_for_user` returning dict with both `copied_template_id` AND `seed_name` keys (Plan 04 consumes both via W-4).
  </action>
  <verify>
    <automated>uv run pytest tests/unit/workflows/test_template_versions_engine.py -v 2>&1 | tail -20</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Module + tests exist; >=15 unit tests pass; ruff + ty clean; supabase_client+execute_async used (not direct await .execute()); copy_seed_template_for_user returns {copied_template_id, seed_name} dict.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 02-03: PUT /workflows/templates/{id} endpoint + ETag on GET + Pydantic request/response models with canonical ETag wire format</name>
  <files>app/routers/workflows.py, tests/unit/routers/test_workflow_save_endpoint.py</files>
  <behavior>
    Tests must assert (target 15-20 tests):
    - GET /workflows/templates/{id} response has ETag header with QUOTED ISO8601 saved_at (e.g. `"2026-05-11T19:30:00.000000+00:00"` — literal double-quotes around the string)
    - GET /workflows/templates/{id} for a row with NULL current_version_id falls back to ETag of quoted updated_at (legacy compat)
    - PUT /workflows/templates/{id} without If-Match returns 428 Precondition Required
    - PUT /workflows/templates/{id} with mismatched If-Match returns 412 Precondition Failed with:
        (a) fresh template body in response
        (b) fresh ETag in `ETag` response header (quoted ISO8601)
        (c) fresh ETag ALSO in response body under `etag` key (quoted ISO8601, identical to header) — B-2
    - PUT /workflows/templates/{id} with matching If-Match returns 200 with body `{version: <new_version>, etag: "<quoted ISO8601 of new saved_at>"}` — B-2 (body etag is canonical for client; header echoes it for HTTP semantics)
    - PUT with quote-stripped If-Match (e.g. `2026-05-11T19:30:00.000Z` WITHOUT surrounding quotes) STILL succeeds (200) — defensive server-side strip (B-2)
    - PUT with quoted If-Match that matches returns 200; PUT with quoted If-Match that does NOT match returns 412 — B-2 parity
    - PUT against a seed template (created_by IS NULL) where the user is NOT the seed owner returns 409 with EXACT body shape:
        ```json
        {"error": "seed_template_immutable",
         "copied_template_id": "<uuid>",
         "seed_name": "<original seed name>",
         "message": "Seed templates can't be edited directly. A private copy has been created."}
        ```
      (W-4 — all four keys present)
    - PUT against a non-existent template returns 404
    - PUT against a template owned by a different user (created_by != user_id AND NOT NULL) returns 403
    - Request body validation: missing graph_nodes → 422; graph_nodes not a list → 422; nodes with invalid kind → 422 (Pydantic Literal enforcement)
  </behavior>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

In `app/routers/workflows.py`:

1. Add `WorkflowTemplateVersion`, `SaveTemplateRequest`, `HistoryItem`, `SeedForkResponse`, `SaveTemplateSuccessResponse` Pydantic models inline next to `WorkflowTemplateResponse`:

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

class SeedForkResponse(BaseModel):
    """W-4: 409 body when user tries to edit a seed template."""
    error: Literal['seed_template_immutable'] = 'seed_template_immutable'
    copied_template_id: str
    seed_name: str
    message: str = "Seed templates can't be edited directly. A private copy has been created."

class SaveTemplateSuccessResponse(BaseModel):
    """B-2: 200 body includes the new ETag so the client doesn't need a follow-up GET."""
    version: WorkflowTemplateVersion
    etag: str   # quoted ISO8601 of version.saved_at
```

2. Widen `WorkflowTemplateResponse` with `current_version_id: str | None = None` (additional field; backward-compatible).

3. **B-2 ETag helper:** define a small helper at the top of the router (or in a shared module) so all endpoints emit consistent format:

```python
def _format_etag(saved_at_iso: str) -> str:
    """Return a quoted ETag per RFC 7232: wraps an ISO8601 string in literal double-quotes."""
    return f'"{saved_at_iso}"'

def _parse_if_match(if_match_header: str | None) -> str | None:
    """Strip surrounding double-quotes from an If-Match header, defensively.

    Per RFC 7232 clients SHOULD send quoted; we tolerate either form to ease
    debugging via curl. Returns the inner ISO8601 string, or None if header absent.
    """
    if not if_match_header:
        return None
    value = if_match_header.strip()
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return value
```

4. Modify `get_template` endpoint (currently at line ~433-447): after fetching the template, look up the current version's saved_at (if current_version_id is not None) OR fall back to template's updated_at. Set `response.headers["ETag"] = _format_etag(saved_at)`. Return the standard JSONResponse with the header.

5. Add new endpoint `PUT /workflows/templates/{template_id}` (decorated with rate limiter, get_current_user_id dep):
   - Read `If-Match` header. If missing → raise 428 Precondition Required.
   - Parse via `_parse_if_match(...)` (defensive quote strip — B-2).
   - Fetch the template. If `created_by IS NULL` → call `copy_seed_template_for_user(seed_template_id, user_id)` and return 409 with `SeedForkResponse` body — W-4 shape (all four keys: error, copied_template_id, seed_name, message).
   - If `created_by IS NOT NULL` AND `created_by != user_id` → raise 403.
   - Call `save_template_version(...)` with the parsed If-Match value. If returns None → 412:
       - Refetch the current template; rebuild WorkflowTemplateResponse body
       - Compute fresh ETag from the current version's saved_at via `_format_etag(...)`
       - Return a JSONResponse with status 412, headers={"ETag": fresh_etag}, body={**template_response_dict, "etag": fresh_etag} — B-2 (ETag in BOTH header AND body)
   - Else (200): build `SaveTemplateSuccessResponse(version=new_version, etag=_format_etag(new_version.saved_at))`. Set the `ETag` response header to the same value. Return the body — B-2 (canonical etag in body, header echoes it).

6. Add new endpoint `GET /workflows/templates/{template_id}/history`:
   - Call `list_template_history(template_id)`; return list[HistoryItem].
   - Auth: requires user_id; check created_by permission like get_template does.

7. Add new endpoint `POST /workflows/templates/{template_id}/revert/{version_id}`:
   - Read If-Match header (parse via _parse_if_match; 412 with fresh ETag in header+body on mismatch — B-2 parity); call `revert_template_to_version`; return SaveTemplateSuccessResponse with new version + new etag in body.

Tests at `tests/unit/routers/test_workflow_save_endpoint.py` (target 15-20 tests): FastAPI TestClient pattern from 109-02's `test_templates_api_returns_graph.py`. Mount only the workflows router; override `get_current_user_id`; mock `app.workflows.template_versions.save_template_version` etc.

Specifically add these B-2 parity assertions:
- `test_etag_format_is_quoted_iso8601_on_get` — assert `re.match(r'^"[0-9T:.+-]+Z?"$', response.headers['etag'])`
- `test_put_200_body_contains_etag_key` — assert response.json() has both `version` and `etag` keys; etag matches the regex above
- `test_put_412_response_etag_in_body_matches_header` — capture both, assert equality
- `test_put_with_unquoted_if_match_succeeds` — defensive strip — assert PUT with `If-Match: 2026-05-11T19:30:00.000000+00:00` (no quotes) returns 200
- `test_put_with_quoted_if_match_succeeds` — assert PUT with `If-Match: "2026-05-11T19:30:00.000000+00:00"` returns 200

And W-4 assertions:
- `test_put_seed_template_returns_409_with_all_four_keys` — assert response.json() contains keys {error, copied_template_id, seed_name, message}, and `error == 'seed_template_immutable'`
  </action>
  <verify>
    <automated>uv run pytest tests/unit/routers/test_workflow_save_endpoint.py -v 2>&1 | tail -25</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Endpoint suite passes (>=15 tests); ETag header AND body emitted on GET/PUT with quoted ISO8601 format; 412/428/409/403/404/422 all handled with correct response bodies and headers; SeedForkResponse shape exact per W-4; B-2 wire-format parity tests pass.</done>
</task>

<task type="auto">
  <name>Task 02-04: Engine integration — version pinning in start_workflow_execution + widen list_templates SELECT (+ behavioral unit tests, not grep)</name>
  <files>app/workflows/engine.py, tests/unit/workflows/test_template_versions_engine.py</files>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

In `app/workflows/engine.py`:

1. Widen the explicit SELECT in `list_templates()` (currently at line ~152-156) to include `current_version_id`. Per Phase 109-02's lesson, this is a load-bearing change — without it, the column is silently dropped on the wire even though the Pydantic model accepts it.

2. In the section that calls `start_workflow_execution_atomic` RPC (around line 805-817), add `"p_template_version_id": template.get("current_version_id")` to the `rpc_params` dict. The RPC was updated in Task 02-01 to accept this parameter as the last optional UUID. Legacy templates with NULL current_version_id will pass NULL — the column on `workflow_executions` stays nullable, so this is safe.

3. Do NOT touch any other engine code. Especially do NOT modify the execution loop, the `step_executor` path, or any of the per-step logic. Phase 110's engine work is limited to (a) widening SELECT and (b) propagating template_version_id to the new column. The graph executor itself (Phase 3 work) is OUT OF SCOPE.

4. Do NOT touch `list_template_versions()` (the legacy method on `template_key` ordering). That stays for backward compat — Plan 02 adds NEW `list_template_history()` in the `template_versions.py` module (Task 02-02) which is a parallel API surface.

**W-7 fix: replace grep-based verification with behavioral unit tests.** Append to `tests/unit/workflows/test_template_versions_engine.py` (the file from Task 02-02) two NEW behavioral tests:

```python
# tests/unit/workflows/test_template_versions_engine.py — additional tests for Task 02-04

async def test_list_templates_select_includes_current_version_id():
    """list_templates() SELECT projection must include current_version_id so the
    API response can carry it. Mocks supabase_client and asserts the dict returned
    from engine.list_templates contains the key.
    """
    # Mock supabase_client().table("workflow_templates").select("...").execute()
    # to return a row dict with current_version_id="abc-123" as a key.
    # Call engine.list_templates(...). Assert the returned list[0] has key "current_version_id"
    # and its value equals "abc-123". (NOT a grep — this catches silent SELECT trimming.)

async def test_start_workflow_execution_passes_template_version_id_in_rpc_params():
    """When engine.start_workflow_execution invokes the start_workflow_execution_atomic
    RPC, the rpc_params dict must include 'p_template_version_id' keyed off
    template.current_version_id.
    """
    # Mock engine.get_template() to return {"id": "tmpl-1", "current_version_id": "ver-2", ...}.
    # Mock supabase_client().rpc(...).execute() to capture call args.
    # Trigger engine.start_workflow_execution(...).
    # Assert the captured rpc_params dict contains key "p_template_version_id" with value "ver-2".
    # Also assert it's resilient: if get_template() returns current_version_id=None, the rpc_params
    # value is None (not missing) so the SQL default NULL applies.
```

These tests are BEHAVIORAL (mock-based, exercise the function call paths) — they catch silent regressions that a grep would miss (e.g. a future refactor that changes how SELECT projections are built).
  </action>
  <verify>
    <automated>uv run pytest tests/unit/workflows/test_template_versions_engine.py::test_list_templates_select_includes_current_version_id tests/unit/workflows/test_template_versions_engine.py::test_start_workflow_execution_passes_template_version_id_in_rpc_params -v 2>&1 | tail -15</automated>
    <automated>node -e "const fs=require('fs');const text=fs.readFileSync('app/workflows/engine.py','utf8');if(!text.includes('current_version_id')){console.error('MISSING: current_version_id in engine.py');process.exit(1);}if(!text.includes('p_template_version_id')){console.error('MISSING: p_template_version_id in engine.py');process.exit(1);}console.log('OK');"</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>list_templates SELECT contains current_version_id (verified behaviorally via mock); rpc_params dict includes p_template_version_id keyed off template.get('current_version_id') (verified behaviorally via mock + captured-args assertion). No other engine.py changes. Both behavioral tests pass.</done>
</task>

<task type="auto">
  <name>Task 02-05: ETag wire-format round-trip integration test (B-2 parity)</name>
  <files>tests/integration/test_etag_round_trip.py</files>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

Create `tests/integration/test_etag_round_trip.py` — a B-2 wire-format parity test suite.

```python
"""ETag wire-format round-trip — B-2 parity tests.

Asserts the server's ETag format is consistent everywhere:
  - GET emits quoted ISO8601 in the ETag header
  - PUT with that exact captured header value returns 200 (round-trip OK)
  - PUT with the value stripped of surrounding quotes ALSO returns 200 (defensive)
  - PUT with a mismatched ETag returns 412 with a fresh quoted ETag in BOTH header AND body
"""

import os
import re
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
    reason="Requires Supabase creds + a running FastAPI under test",
)

# Pattern: a quoted ISO8601 datetime
QUOTED_ISO8601 = re.compile(r'^"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[\d.+:Z-]*"$')


def test_etag_round_trip_get_then_put_matching_returns_200():
    """Capture ETag from GET; send it verbatim on PUT; expect 200."""
    # ...via TestClient or httpx against the live FastAPI app
    # 1. POST /workflows/templates/{id}/test-fixture to seed a private template (or use a known fixture)
    # 2. GET that template; capture res.headers['etag']
    # 3. assert QUOTED_ISO8601.match(etag)
    # 4. PUT with If-Match: <captured etag verbatim>, valid body
    # 5. assert res.status_code == 200
    # 6. assert QUOTED_ISO8601.match(res.json()['etag'])  # response body etag
    # 7. assert res.headers['etag'] == res.json()['etag']  # body is canonical, header echoes


def test_etag_round_trip_put_with_stripped_quotes_succeeds_defensively():
    """Server defensively strips surrounding quotes from If-Match — verify."""
    # 1. GET; capture quoted etag
    # 2. Strip outer quotes manually: stripped = etag[1:-1]
    # 3. PUT with If-Match: <stripped>, valid body
    # 4. assert res.status_code == 200 (defensive parse path)


def test_etag_round_trip_mismatched_if_match_returns_412_with_quoted_etag_in_body():
    """B-2 invariant: 412 response body has 'etag' key with quoted ISO8601 value, matching header."""
    # 1. GET → capture etag_a
    # 2. PUT successfully with etag_a → 200; capture new etag_b from response.json()['etag']
    # 3. PUT again with etag_a (stale) → expect 412
    # 4. assert res.status_code == 412
    # 5. assert res.headers['etag'] == etag_b
    # 6. assert res.json()['etag'] == etag_b
    # 7. assert QUOTED_ISO8601.match(res.json()['etag'])
```

Use the existing integration-test pattern in this repo (httpx + TestClient against the FastAPI app, with the supabase service-role client for setup/teardown). 4 tests minimum.

This test file SKIPS when Supabase creds absent (CI without local Supabase). When run in CI with creds, all 4 tests must pass.
  </action>
  <verify>
    <automated>uv run pytest tests/integration/test_etag_round_trip.py --collect-only -q 2>&1 | tail -10</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Test file exists; 4 tests collected by pytest; tests SKIP cleanly when creds absent; structurally asserts B-2 ETag wire format parity end-to-end.</done>
</task>

<task type="auto">
  <name>Task 02-06: Linear workflow execution regression test (ROADMAP criterion #9 — W-8)</name>
  <files>tests/integration/test_linear_workflow_execution_post_versioning.py</files>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

Create `tests/integration/test_linear_workflow_execution_post_versioning.py` — owns ROADMAP criterion #9.

```python
"""Linear engine non-regression — ROADMAP criterion #9 (W-8).

After Phase 110 migration + Plan 02 engine wiring, existing canonical seeded
templates MUST execute end-to-end identically to the pre-Phase 110 baseline.
This test asserts that engine.execute_steps() and step_executor logic remain
untouched: only the version pinning at execution START changes.

Targets: pick a known stable seed (e.g. content-creation pipeline) and verify:
  1. POST /workflows/templates/{seed_id}/start succeeds
  2. The created workflow_executions row has template_version_id set to the seed's
     current_version_id (NOT NULL)
  3. The execution progresses through the SAME steps in the SAME order as a
     recorded baseline (capture step ordering from a pre-migration run if possible,
     or assert against the expected step list from the seed's phases JSONB)
  4. Final execution status reaches 'completed' (or 'failed' for known-flaky steps,
     but the SAME final state as baseline)
  5. Mid-execution, edit the seed's content (which copy-forks it for the test user
     into a new template, creating v2). Verify the IN-FLIGHT execution continues
     against the pinned v1, NOT v2 (immutability of pinned executions).
"""

import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
    reason="Requires Supabase creds + a running FastAPI under test",
)


def test_linear_execution_unchanged_post_phase_110():
    """End-to-end linear-template execution still completes with same step ordering."""
    # 1. Select a known canonical seed template (e.g. by name='Content Creation Pipeline')
    # 2. Start execution via POST /workflows/start
    # 3. Poll until execution.status in ('completed', 'failed', 'paused')
    # 4. Read workflow_executions row; assert template_version_id IS NOT NULL
    # 5. Read execution step log; assert step ordering matches baseline


def test_pinned_version_immutable_during_in_flight_execution():
    """Editing the template mid-flight doesn't affect the running execution."""
    # 1. Start execution (captures v1 in template_version_id)
    # 2. (As the seed user) edit + save template → creates v2; current_version_id moves
    # 3. Continue polling original execution
    # 4. Assert original execution still references v1 (template_version_id unchanged)
    # 5. Assert step outputs match what v1 would produce, not what v2 would
```

2 tests minimum. They SKIP without creds. They directly assert ROADMAP criterion #9.

Note in the test docstring: "If this test fails, Plan 02's engine wiring has accidentally modified execution logic. Revert and audit `engine.start_workflow_execution` + the step_executor path."
  </action>
  <verify>
    <automated>uv run pytest tests/integration/test_linear_workflow_execution_post_versioning.py --collect-only -q 2>&1 | tail -10</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Test file exists; 2 tests collected by pytest; tests SKIP cleanly when creds absent; directly maps to ROADMAP criterion #9 in the docstrings.</done>
</task>

<task type="auto">
  <name>Task 02-07: Regenerate OpenAPI types + verify frontend tsc clean</name>
  <files>frontend/src/types/api.generated.ts</files>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

1. From the project root, run `cd frontend && npm run generate:types`. This regenerates `frontend/src/types/api.generated.ts` from the live FastAPI OpenAPI schema. The new schemas `WorkflowTemplateVersion`, `SaveTemplateRequest`, `HistoryItem`, `SeedForkResponse`, `SaveTemplateSuccessResponse` and the new `current_version_id` field on `WorkflowTemplateResponse` will appear automatically.

2. Verify the types compile: `cd frontend && npx tsc --noEmit`.

3. If the codegen tool requires the server to be running (per Phase 109-02 pattern), use the alternate path: `uv run python -c "from app.fast_api_app import app; import json; print(json.dumps(app.openapi()))" > /tmp/openapi.json; cd frontend && npx openapi-typescript /tmp/openapi.json --output src/types/api.generated.ts`.

4. Spot-check: `grep "WorkflowTemplateVersion\|SaveTemplateRequest\|HistoryItem\|SeedForkResponse\|SaveTemplateSuccessResponse\|current_version_id" frontend/src/types/api.generated.ts` should return >=5 lines.

5. Do NOT manually edit `api.generated.ts` — it's a generated artifact. If types are wrong, fix the Pydantic model in Task 02-03.

6. Do NOT add new named exports to `frontend/src/services/workflows.ts` in this plan — that's Plan 04's responsibility (the frontend canvas plan adds saveTemplate/getTemplateHistory/revertTemplate consumer functions).
  </action>
  <verify>
    <automated>grep -c "WorkflowTemplateVersion\|SaveTemplateRequest\|HistoryItem\|SeedForkResponse\|current_version_id" frontend/src/types/api.generated.ts</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>api.generated.ts regenerated; contains all 5 new symbols (WorkflowTemplateVersion, SaveTemplateRequest, HistoryItem, SeedForkResponse, current_version_id); npx tsc --noEmit clean across frontend.</done>
</task>

</tasks>

<verification>
End-to-end checks:

1. PUT round-trip works: `curl -X PUT http://localhost:8000/workflows/templates/{id} -H "If-Match: \"<saved_at>\"" -d '{"graph_nodes":...}'` returns 200 with `{version: {...}, etag: "\"...\""}` body.
2. PUT with stale If-Match returns 412 with the fresh template body + `etag` key in body + fresh `ETag` response header (both matching, quoted ISO8601) — B-2.
3. PUT without If-Match returns 428.
4. PUT against a seed returns 409 with exactly four keys: error, copied_template_id, seed_name, message — W-4.
5. GET emits ETag header on the response with quoted ISO8601 format.
6. POST /revert/{version_id} returns a new version whose parent_version_id == target version_id; body includes the new etag.
7. Starting a workflow execution (via existing /start endpoint) populates `workflow_executions.template_version_id` from `template.current_version_id`.
8. All unit tests pass: `uv run pytest tests/unit/workflows/test_template_versions_engine.py tests/unit/routers/test_workflow_save_endpoint.py -v`.
9. Integration tests collect cleanly + skip in absence of creds: `uv run pytest tests/integration/test_etag_round_trip.py tests/integration/test_linear_workflow_execution_post_versioning.py --collect-only`.
10. Lint clean: `uv run ruff check app/workflows/template_versions.py app/routers/workflows.py app/workflows/engine.py tests/ --fix && uv run ruff format app/workflows/template_versions.py`.
11. Frontend tsc clean: `cd frontend && npx tsc --noEmit`.
12. Branch hygiene: `git branch --show-current` returns the Phase 110 branch (NOT main) — checked automatedly in EVERY task (W-6).
13. ROADMAP criterion #9: `test_linear_execution_unchanged_post_phase_110` exists and asserts linear engine behavior (W-8).
</verification>

<success_criteria>
This plan ships when:
- One new SQL migration: `supabase/migrations/20260615000100_workflow_template_save_rpc.sql` (~150-220 lines) — uses DROP FUNCTION + CREATE OR REPLACE for the signature change (B-3).
- One new Python module: `app/workflows/template_versions.py` (~250-350 lines).
- Three router endpoints added to `app/routers/workflows.py`: PUT /templates/{id}, GET /templates/{id}/history, POST /templates/{id}/revert/{version_id}.
- One existing endpoint modified: GET /templates/{id} adds ETag header (quoted ISO8601 — B-2).
- One engine method modified: `WorkflowEngine.list_templates` SELECT widened + start_workflow_execution_atomic RPC call params include p_template_version_id (verified BEHAVIORALLY via mocks, not grep — W-7).
- Five new Pydantic models: `WorkflowTemplateVersion`, `SaveTemplateRequest`, `HistoryItem`, `SeedForkResponse` (W-4 exact shape), `SaveTemplateSuccessResponse` (B-2 body-etag).
- One regenerated TS types file (`api.generated.ts`).
- Four test files: `tests/unit/workflows/test_template_versions_engine.py` + `tests/unit/routers/test_workflow_save_endpoint.py` (combined >=30 unit tests) + `tests/integration/test_etag_round_trip.py` (4 tests — B-2 parity) + `tests/integration/test_linear_workflow_execution_post_versioning.py` (2 tests — ROADMAP criterion #9, W-8).
- Plan SUMMARY committed.
- Addresses roadmap success criteria: #2 (Save creates new version row), #3 (run-time pinning to current_version_id), #4 (history endpoint backs the UI list), #5 (ETag + 412 + If-Match), #6 (412 includes fresh body for "view their changes"), **#9 (linear engine non-regression — W-8, owned by Plan 02 via test_linear_workflow_execution_post_versioning.py)**.
</success_criteria>

<output>
After completion, create `.planning/phases/110-workflow-node-editor-editable/110-02-SUMMARY.md` with: duration metric, files created/modified, decisions made (especially around RPC vs explicit transaction, 409 vs 412 semantics, ETag value source, B-2 wire format choices, W-4 SeedForkResponse exact shape, W-7 behavioral test design, W-8 baseline capture method), deviations from plan, and a "Ready for Plan 04" section describing the API surface frontend consumers should use — including the explicit ETag format (quoted ISO8601, in body under `etag` key, server defensively strips quotes on If-Match input).
</output>
</content>
</invoke>
---
phase: 109-workflow-node-editor-viewer
plan: 02
type: execute
wave: 1
depends_on: [109-01]
files_modified:
  - app/workflows/registry.py
  - app/routers/workflows.py
  - tests/unit/workflows/test_registry_graph_fields.py
  - tests/unit/workflows/test_templates_api_returns_graph.py
  - frontend/src/services/workflows.ts
  - frontend/src/types/api.generated.ts
autonomous: true
requirements: [NODEEDITOR-API-01]

must_haves:
  truths:
    - "WorkflowTemplate Pydantic model has three new optional fields: graph_nodes: list[GraphNode] | None = None, graph_edges: list[GraphEdge] | None = None, graph_layout: dict[str, NodePosition] | None = None"
    - "GraphNode, GraphEdge, NodePosition Pydantic models exist in app/workflows/registry.py with the exact shape from Spec B § Data Model (id, kind, label, config — kind is Literal['trigger', 'agent-action', 'condition', 'parallel', 'merge', 'human-approval', 'output'] for forward-compat even though Phase 1 only uses 3 of these)"
    - "GET /workflows/templates returns a list of WorkflowTemplate dicts each including graph_nodes/graph_edges/graph_layout fields (which are None for any template whose row has these columns NULL — should be zero rows after Plan 01 migration)"
    - "GET /workflows/templates/{id} returns a single WorkflowTemplate dict with the three graph fields"
    - "frontend/src/services/workflows.ts WorkflowTemplate TypeScript interface includes graph_nodes/graph_edges/graph_layout as optional fields"
    - "frontend/src/types/api.generated.ts has been regenerated via `npm run generate:types` so the new fields appear in the OpenAPI schema types"
    - "Existing callers of listWorkflowTemplates() and the linear engine path continue to work unchanged — the graph fields are additive; legacy `steps` is still read by app/workflows/engine.py"
  artifacts:
    - path: "app/workflows/registry.py"
      provides: "GraphNode, GraphEdge, NodePosition Pydantic models; WorkflowTemplate gains graph_nodes/graph_edges/graph_layout optional fields; from_row classmethod (or equivalent) populates them from the new DB columns"
      contains: "graph_nodes: list[GraphNode] | None"
    - path: "app/routers/workflows.py"
      provides: "list_templates and get_template endpoints serialize the new graph fields. No new endpoints in this plan — just response payload widening."
      contains: "graph_nodes"
    - path: "tests/unit/workflows/test_registry_graph_fields.py"
      provides: "Tests: WorkflowTemplate round-trips graph_nodes through from_row + dict(); GraphNode rejects invalid kind via Pydantic; NodePosition requires int x/y"
      contains: "test_workflow_template_includes_graph_nodes"
    - path: "tests/unit/workflows/test_templates_api_returns_graph.py"
      provides: "API tests: GET /workflows/templates response shape includes graph_nodes for at least one template (assuming the test DB has rows post-migration)"
      contains: "test_list_templates_returns_graph_fields"
    - path: "frontend/src/services/workflows.ts"
      provides: "WorkflowTemplate interface gains graph_nodes?: GraphNode[]; graph_edges?: GraphEdge[]; graph_layout?: Record<string, {x:number; y:number}>;"
      contains: "graph_nodes?:"
    - path: "frontend/src/types/api.generated.ts"
      provides: "Regenerated from live OpenAPI schema; includes the new fields in components.schemas.WorkflowTemplate"
      contains: "graph_nodes"
  key_links:
    - from: "app/workflows/registry.py:WorkflowTemplate.from_row"
      to: "supabase/migrations/20260601000000_workflow_template_graph_projection.sql ALTER TABLE columns"
      via: "Reading graph_nodes/graph_edges/graph_layout from the row dict that supabase returns"
      pattern: "row.get(\"graph_nodes\")"
    - from: "app/routers/workflows.py:list_templates"
      to: "frontend/src/services/workflows.ts:listWorkflowTemplates"
      via: "JSON serialization passes graph_nodes through automatically once the Pydantic model knows about them; no router code change needed beyond ensuring the response_model matches"
      pattern: "response_model"
    - from: "frontend/src/services/workflows.ts:WorkflowTemplate"
      to: "frontend/src/components/workflows/editor/NodeCanvas.tsx (Plan 03)"
      via: "Plan 03's NodeCanvas takes the WorkflowTemplate, reads template.graph_nodes/edges/layout, and feeds them to React Flow"
      pattern: "graph_nodes?:"
---

<objective>
Extend the WorkflowTemplate Pydantic model with three optional fields (graph_nodes, graph_edges, graph_layout) backed by typed sub-models, expose those fields through the existing GET /workflows/templates and GET /workflows/templates/{id} endpoints, and propagate the type changes to the frontend service layer + the generated OpenAPI types. No new endpoints; this is purely widening the response payload.

Purpose: Satisfy NODEEDITOR-API-01 (backend API exposes graph fields). Phase 1's Plan 03 (frontend viewer) depends on this to render the graph.

Output: The frontend can call `await listWorkflowTemplates()` and receive `template.graph_nodes` for every template that has graph fields populated by Plan 01's migration.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/109-workflow-node-editor-viewer/109-CONTEXT.md
@.planning/phases/109-workflow-node-editor-viewer/109-01-graph-projection-migration-PLAN.md
@docs/superpowers/specs/2026-05-11-workflow-node-editor-design.md
@app/workflows/registry.py
@app/routers/workflows.py
@frontend/src/services/workflows.ts

<interfaces>
<!-- Current WorkflowTemplate shape (read from app/workflows/registry.py before editing) -->

```python
# Approximate existing shape — verify against actual file
class WorkflowTemplate(BaseModel):
    id: UUID | None
    name: str
    description: str | None
    category: str
    steps: list[dict[str, Any]]
    owner_user_id: UUID | None
    created_at: datetime | None
    updated_at: datetime | None
```

<!-- Target additions (forward-compatible kind union for Phase 3+) -->

```python
class NodePosition(BaseModel):
    x: int
    y: int

NodeKind = Literal[
    "trigger",
    "agent-action",
    "condition",          # Phase 3
    "parallel",           # Phase 4
    "merge",              # Phase 4
    "human-approval",     # Phase 4
    "output",
]

class GraphNode(BaseModel):
    id: str
    kind: NodeKind
    label: str
    config: dict[str, Any] | None = None  # per-kind shape validated in Phase 2

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    source_handle: str | None = None
    label: str | None = None

class WorkflowTemplate(BaseModel):
    # ... existing fields ...
    graph_nodes: list[GraphNode] | None = None
    graph_edges: list[GraphEdge] | None = None
    graph_layout: dict[str, NodePosition] | None = None
```
</interfaces>
</context>

<tasks>

<task id="02-01" desc="Read the current WorkflowTemplate model and identify the from_row pattern">
Read `app/workflows/registry.py` end-to-end. Note:
- The exact shape of `WorkflowTemplate` (field names + types)
- How rows are loaded from Supabase into the model (whether it's `WorkflowTemplate.model_validate(row)` or a custom `from_row` classmethod)
- Whether category is `str` or `Literal[...]` — keep consistent
- Whether `steps` is typed as `list[dict]` or has its own sub-model
</task>

<task id="02-02" desc="Add the four new Pydantic sub-models">
Add to `app/workflows/registry.py` above the WorkflowTemplate class (or in a co-located section, following the file's existing organization):

```python
from typing import Literal

class NodePosition(BaseModel):
    x: int
    y: int

NodeKind = Literal[
    "trigger",
    "agent-action",
    "condition",
    "parallel",
    "merge",
    "human-approval",
    "output",
]

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
```
</task>

<task id="02-03" desc="Extend WorkflowTemplate with the three optional graph fields">
In `app/workflows/registry.py`, add to the `WorkflowTemplate` model:

```python
graph_nodes: list[GraphNode] | None = None
graph_edges: list[GraphEdge] | None = None
graph_layout: dict[str, NodePosition] | None = None
```

If the loading pattern is `model_validate(row)` and Pydantic v2's default behavior handles JSONB→list[GraphNode] coercion automatically, no further code changes here. Otherwise update the `from_row` classmethod to explicitly pass the graph fields through.

Existing callers that construct `WorkflowTemplate(...)` without these fields continue to work — the defaults are None.
</task>

<task id="02-04" desc="Verify GET /workflows/templates endpoints serialize the new fields">
Read `app/routers/workflows.py`. The list/get template endpoints either:
- Return `WorkflowTemplate` directly (response_model=WorkflowTemplate) — no change needed; Pydantic emits the new fields automatically
- Return `WorkflowTemplate.model_dump()` manually — verify the dump includes graph_nodes/edges/layout (it will if the model has them; `model_dump()` defaults to including all fields)
- Manually construct a response dict from the row — update the dict to include the three graph fields

If you find the third case, add the fields explicitly. If you find the first two, no router change is needed.
</task>

<task id="02-05" desc="Update frontend WorkflowTemplate interface">
Edit `frontend/src/services/workflows.ts`:

```typescript
export interface NodePosition {
  x: number;
  y: number;
}

export type NodeKind =
  | 'trigger'
  | 'agent-action'
  | 'condition'
  | 'parallel'
  | 'merge'
  | 'human-approval'
  | 'output';

export interface GraphNode {
  id: string;
  kind: NodeKind;
  label: string;
  config?: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  source_handle?: string;
  label?: string;
}

export interface WorkflowTemplate {
  // ... existing fields ...
  graph_nodes?: GraphNode[];
  graph_edges?: GraphEdge[];
  graph_layout?: Record<string, NodePosition>;
}
```

The `listWorkflowTemplates()` function signature does not change — it returns `WorkflowTemplate[]` either way.
</task>

<task id="02-06" desc="Regenerate API types">
Run from the repo root:

```bash
cd frontend && npm run generate:types
```

Verify the regenerated `frontend/src/types/api.generated.ts` includes `graph_nodes` and `graph_edges` in the WorkflowTemplate schema. Commit the regenerated file. If `tsc --noEmit` flags new conflicts between the manual interface in `workflows.ts` and the generated types, prefer the manual interface (the generated one is for OpenAPI consumers; Plan 03's NodeCanvas should import from `services/workflows.ts`).
</task>

<task id="02-07" desc="Add backend unit tests">
Create `tests/unit/workflows/test_registry_graph_fields.py`:

```python
def test_workflow_template_accepts_graph_nodes(): ...
def test_workflow_template_defaults_graph_fields_to_none(): ...
def test_graph_node_rejects_invalid_kind(): ...  # Pydantic should raise on kind="invalid"
def test_node_position_requires_int_xy(): ...
def test_graph_edge_optional_source_handle_none_by_default(): ...
def test_graph_layout_dict_key_is_node_id(): ...  # smoke test for dict[str, NodePosition]
```

Create `tests/unit/workflows/test_templates_api_returns_graph.py`:

```python
async def test_list_templates_returns_graph_fields(supabase_test_client):
    # Insert a row with graph_nodes/edges/layout populated
    # Call the endpoint via TestClient
    # Assert response[0] has graph_nodes with the right shape
    ...

async def test_get_template_returns_graph_fields(supabase_test_client):
    # Same as above but single-row GET /workflows/templates/{id}
    ...
```
</task>

</tasks>

<verification>
1. `uv run pytest tests/unit/workflows/test_registry_graph_fields.py tests/unit/workflows/test_templates_api_returns_graph.py -v` — all tests pass.
2. `uv run ty check app/workflows/registry.py app/routers/workflows.py` — no type errors.
3. `cd frontend && npx tsc --noEmit` — no type errors. The regenerated api.generated.ts must be in sync (CI's "API Types Freshness Check" must pass).
4. Start the local backend, hit `GET http://localhost:8000/workflows/templates` (with auth), verify the response includes a `graph_nodes` field on at least one template (assumes local Supabase has been migrated by Plan 01).
</verification>

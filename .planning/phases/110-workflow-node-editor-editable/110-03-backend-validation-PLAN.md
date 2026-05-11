---
phase: 110-workflow-node-editor-editable
plan: 03
type: execute
wave: 2
depends_on: [110-01]
files_modified:
  - app/workflows/graph_validation.py
  - app/routers/workflows.py
  - tests/unit/workflows/test_graph_validation.py
  - tests/unit/routers/test_workflow_validate_endpoint.py
autonomous: true
requirements:
  - NODEEDITOR-VALIDATE-01
gap_closure: false

must_haves:
  truths:
    - "validate_workflow_graph(graph_nodes, graph_edges) enforces five structural rules: exactly one trigger node with zero incoming edges (rule 1); every node reachable from the trigger (rule 2); no cycles via Kahn's topological sort (rule 3); at least one output node (rule 6); each node's config passes its per-kind schema (rule 7)"
    - "Rules 4 (condition outgoing degree) and 5 (parallel/merge pairing) are NOT enforced in Phase 110 — they raise NotImplementedError only if a caller asks for `strict=True` (Phase 3/4 will flip the default)"
    - "POST /workflows/templates/{id}/validate accepts a body with graph_nodes/graph_edges and returns 200 with {errors: list[{node_id, rule, message}]} — empty list means valid; non-empty means save should be blocked client-side"
    - "Validation respects all 7 node kinds from NodeKind: trigger/agent-action/condition/parallel/merge/human-approval/output. Phase 110 visual-only kinds (condition/parallel/merge/human-approval) save with permissive placeholder schemas; Phase 3/4 will tighten them"
    - "POST /validate is callable by any authenticated user for any template they could load via GET (created_by IS NULL seeds OR created_by = user_id)"
  artifacts:
    - path: "app/workflows/graph_validation.py"
      provides: "validate_workflow_graph() + per-kind Pydantic config schemas + ValidationError typed result"
      contains: "def validate_workflow_graph"
    - path: "app/routers/workflows.py"
      provides: "POST /workflows/templates/{id}/validate endpoint + ValidateGraphRequest + ValidateGraphResponse Pydantic models"
      contains: "validate"
  key_links:
    - from: "POST /workflows/templates/{id}/validate"
      to: "validate_workflow_graph() in app/workflows/graph_validation.py"
      via: "Direct function call (sync, pure — no DB hit)"
      pattern: "validate_workflow_graph"
    - from: "validate_workflow_graph"
      to: "Per-kind config schemas (TriggerConfig, AgentActionConfig, ConditionConfig, ...)"
      via: "Pydantic model_validate on node.config based on node.kind"
      pattern: "model_validate"
---

<objective>
Ship server-side graph validation as a pure-functional module that both the new POST /validate endpoint AND the PUT save endpoint can call. Enforces 5 of the 7 spec validation rules (the 5 in scope for Phase 110: single trigger, reachability, no cycles, ≥1 output, per-kind config schema). Rules 4 (condition outgoing degree) and 5 (parallel/merge pairing) are stubbed for Phase 3/4. Plan 04's client-side useGraphValidation hook (frontend) mirrors this logic exactly so client/server agree on errors.

Purpose: Provides the canonical server enforcement layer for decision 7-aligned validation. The endpoint is what the frontend hits before allowing a Save; the same function is also called inside PUT /templates/{id} (Plan 02's save handler) to prevent direct API users from bypassing client validation.
Output: One new module (~250 lines), one new endpoint, two test files (~25-35 combined tests).
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
@app/routers/workflows.py
@app/workflows/engine.py

<interfaces>
<!-- Shared with Plan 02 (these already exist in app/routers/workflows.py post Phase 109-02): -->
class GraphNode(BaseModel):
    id: str
    kind: Literal['trigger','agent-action','condition','parallel','merge','human-approval','output']
    label: str
    config: dict[str, Any] | None = None

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    source_handle: str | None = None
    label: str | None = None

<!-- New module to be created in this plan: -->
class ValidationError(BaseModel):
    node_id: str | None        # NULL for graph-level errors (e.g., "no trigger node")
    rule: int                  # 1, 2, 3, 6, or 7
    message: str

def validate_workflow_graph(
    graph_nodes: list[dict | GraphNode],
    graph_edges: list[dict | GraphEdge],
    *, strict: bool = False
) -> list[ValidationError]:
    """Pure-functional validator. Returns empty list if graph is valid; otherwise
    a list of structural errors. strict=True (Phase 3/4) additionally enforces
    rules 4 and 5; Phase 110 callers pass strict=False (default)."""
    ...
</interfaces>

<context_notes>
- This is a SIBLING plan to Plan 02 (both depend only on Plan 01 — no schema overlap, no Pydantic model collisions). Plans 02 and 03 can run in parallel during execution as long as they go on separate worktrees or careful sequential commits. The user has indicated they may serialize Phase 110 like Phase 109; respect that choice.
- File ownership: Plan 02 adds three endpoints (PUT, GET history, POST revert) + ETag on GET. Plan 03 adds one endpoint (POST /validate). Both touch `app/routers/workflows.py`. To avoid merge conflicts, Plan 03 places its endpoint at the BOTTOM of the router (after all of Plan 02's additions). Pydantic models from this plan (ValidateGraphRequest, ValidateGraphResponse, ValidationErrorModel) are also added at the bottom of the models section.
- Plan 02's PUT /templates/{id} (Task 02-03) should call `validate_workflow_graph()` from this plan before invoking `save_template_version`. If Plan 02 ships before Plan 03 (sequential execution), Plan 02's PUT handler must be wired to call validation later — Plan 03 ships the function + endpoint, and a one-line patch to Plan 02's PUT handler adds the call. Document this as a Plan 03 follow-up if Plan 02 lands first.
- Per-kind config schemas: trigger/agent-action/output are real and tight; condition/parallel/merge/human-approval are placeholders (accept any dict; Phase 3/4 tightens). Tight schemas for the first three:
  - TriggerConfig: `{ trigger_type: Literal['manual','schedule','event'] | None, ...allow extras }`
  - AgentActionConfig: `{ tool_name: str, arguments: dict, agent_role: str | None }`
  - OutputConfig: `{ output_format: str | None, ...allow extras }`
- Cycle detection: use Kahn's algorithm (topological sort via in-degree). Pure-Python, ~30 LOC. Returns a list of node_ids involved in cycles. NetworkX would be overkill — no existing dep on it.
- Reachability: BFS from the trigger node. Any node not visited is unreachable → emit a rule-2 ValidationError with the offending node_id.
- The validate endpoint does NOT need to actually load the template from DB — it accepts the proposed graph in the request body. This lets the frontend run it on every save without a round-trip to fetch the current template. The {id} in the URL is used only for auth (the user must have read access to the template).
- Tests should cover the full grammar: valid graphs (golden cases), single-rule violations (one error at a time), multi-rule violations (verify all errors emitted, not just the first), empty/malformed inputs (raise pydantic ValidationError, NOT a silent pass).
- Branch hygiene: check current branch before every commit.
</context_notes>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 03-01: validate_workflow_graph() pure function + per-kind config schemas</name>
  <files>app/workflows/graph_validation.py, tests/unit/workflows/test_graph_validation.py</files>
  <behavior>
    Tests must assert (target 18-25 tests):
    - Rule 1 — no trigger node: returns [ValidationError(node_id=None, rule=1, message=...)]
    - Rule 1 — multiple trigger nodes: returns errors for each extra trigger (node_id set)
    - Rule 1 — trigger with incoming edge: returns error
    - Rule 2 — node unreachable from trigger: returns error keyed to the unreachable node_id
    - Rule 3 — cycle of 2 nodes: returns errors for both nodes
    - Rule 3 — cycle of 3 nodes: returns errors for all three
    - Rule 3 — DAG (no cycle) passes rule 3
    - Rule 6 — no output node: returns error
    - Rule 6 — one output passes
    - Rule 6 — multiple outputs all pass (≥1 is satisfied)
    - Rule 7 — agent-action node missing tool_name in config: returns error keyed to that node
    - Rule 7 — agent-action with extra config fields: passes (extras allowed)
    - Rule 7 — condition node with empty config: passes (Phase 110 placeholder schema)
    - Multi-rule violations: emits all errors, not just first one
    - Valid happy-path graph (trigger → agent-action → output): returns []
    - strict=True with condition node having 1 outgoing edge: NotImplementedError or rule-4 error (Phase 3/4 wiring TBD; for Phase 110, just verify strict=True is rejected with NotImplementedError so callers know it's not yet supported)
    - Empty graph_nodes list: returns rule-1 error (no trigger)
    - Malformed node (missing kind): pydantic raises ValidationError before validate_workflow_graph runs (catch at caller)
  </behavior>
  <action>
Create `app/workflows/graph_validation.py`:

```python
"""Server-side workflow graph validation — Phase 110.

Pure-functional validator. No DB access, no async, no IO. Called from:
  - POST /workflows/templates/{id}/validate (this plan)
  - PUT /workflows/templates/{id} save handler (Plan 02 — wired during integration)

Mirrors the client-side validator in frontend/src/components/workflows/editor/useGraphValidation.ts
(Plan 04). The two MUST stay in sync; if a rule's behavior diverges, the server is canonical.
"""

from __future__ import annotations
from collections import defaultdict, deque
from typing import Any, Literal

from pydantic import BaseModel, ValidationError as PydanticValidationError


NodeKind = Literal[
    'trigger', 'agent-action', 'condition', 'parallel',
    'merge', 'human-approval', 'output',
]


class ValidationError(BaseModel):
    node_id: str | None
    rule: int                # 1, 2, 3, 6, or 7
    message: str


# Per-kind config schemas (Pydantic). Phase 110 tight schemas:
class TriggerConfig(BaseModel):
    trigger_type: Literal['manual', 'schedule', 'event'] | None = None
    model_config = {'extra': 'allow'}


class AgentActionConfig(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = {}
    agent_role: str | None = None
    model_config = {'extra': 'allow'}


class OutputConfig(BaseModel):
    output_format: str | None = None
    model_config = {'extra': 'allow'}


# Placeholder schemas — Phase 3/4 will tighten these:
class _PermissiveConfig(BaseModel):
    model_config = {'extra': 'allow'}


_CONFIG_SCHEMAS: dict[str, type[BaseModel]] = {
    'trigger':         TriggerConfig,
    'agent-action':    AgentActionConfig,
    'output':          OutputConfig,
    'condition':       _PermissiveConfig,    # Phase 3 tightens
    'parallel':        _PermissiveConfig,    # Phase 4 tightens
    'merge':           _PermissiveConfig,    # Phase 4 tightens
    'human-approval':  _PermissiveConfig,    # Phase 4 tightens
}


def validate_workflow_graph(
    graph_nodes: list[dict[str, Any]],
    graph_edges: list[dict[str, Any]],
    *,
    strict: bool = False,
) -> list[ValidationError]:
    """Run all Phase 110 in-scope validation rules. Returns empty list if valid.

    Rules enforced:
        1. Single trigger with no incoming edges
        2. All nodes reachable from trigger
        3. No cycles (topological sort succeeds)
        6. At least one output node
        7. Per-node config passes its per-kind schema

    Rules deferred:
        4. Condition outgoing degree (Phase 3)
        5. Parallel/merge pairing (Phase 4)

    If strict=True, raises NotImplementedError (Phase 3/4 will flip this).
    """
    if strict:
        raise NotImplementedError("strict=True (rules 4 + 5) is Phase 3/4 work")

    errors: list[ValidationError] = []

    # --- Rule 1: single trigger with zero incoming edges ---
    triggers = [n for n in graph_nodes if n.get('kind') == 'trigger']
    if len(triggers) == 0:
        errors.append(ValidationError(node_id=None, rule=1, message='No trigger node found'))
    elif len(triggers) > 1:
        for extra in triggers[1:]:
            errors.append(ValidationError(
                node_id=extra['id'], rule=1,
                message='Multiple trigger nodes — only one is allowed',
            ))

    incoming: defaultdict[str, list[str]] = defaultdict(list)
    outgoing: defaultdict[str, list[str]] = defaultdict(list)
    for edge in graph_edges:
        incoming[edge['target']].append(edge['source'])
        outgoing[edge['source']].append(edge['target'])
    for trig in triggers:
        if incoming.get(trig['id']):
            errors.append(ValidationError(
                node_id=trig['id'], rule=1,
                message='Trigger node must have zero incoming edges',
            ))

    # --- Rule 6: at least one output ---
    outputs = [n for n in graph_nodes if n.get('kind') == 'output']
    if not outputs:
        errors.append(ValidationError(
            node_id=None, rule=6, message='At least one output node is required',
        ))

    # --- Rule 2: reachability from (first) trigger via BFS ---
    if triggers:
        reachable: set[str] = set()
        queue: deque[str] = deque([triggers[0]['id']])
        while queue:
            curr = queue.popleft()
            if curr in reachable:
                continue
            reachable.add(curr)
            for target in outgoing.get(curr, []):
                if target not in reachable:
                    queue.append(target)
        for node in graph_nodes:
            if node['id'] not in reachable:
                errors.append(ValidationError(
                    node_id=node['id'], rule=2,
                    message='Node unreachable from trigger',
                ))

    # --- Rule 3: no cycles (Kahn's algorithm) ---
    in_degree: dict[str, int] = {n['id']: 0 for n in graph_nodes}
    for edge in graph_edges:
        if edge['target'] in in_degree:
            in_degree[edge['target']] += 1
    roots: deque[str] = deque([nid for nid, d in in_degree.items() if d == 0])
    visited: int = 0
    while roots:
        curr = roots.popleft()
        visited += 1
        for target in outgoing.get(curr, []):
            in_degree[target] -= 1
            if in_degree[target] == 0:
                roots.append(target)
    if visited < len(graph_nodes):
        # Nodes with non-zero in-degree at the end are in a cycle
        for nid, d in in_degree.items():
            if d > 0:
                errors.append(ValidationError(
                    node_id=nid, rule=3,
                    message='Node is part of a cycle (graph must be a DAG)',
                ))

    # --- Rule 7: per-kind config validation ---
    for node in graph_nodes:
        kind = node.get('kind')
        if kind not in _CONFIG_SCHEMAS:
            continue   # Unknown kinds caught earlier by Pydantic NodeKind enforcement
        schema = _CONFIG_SCHEMAS[kind]
        config = node.get('config') or {}
        try:
            schema.model_validate(config)
        except PydanticValidationError as exc:
            errors.append(ValidationError(
                node_id=node['id'], rule=7,
                message=f'Config invalid for {kind}: {exc.errors()[0]["msg"] if exc.errors() else str(exc)}',
            ))

    return errors
```

Tests at `tests/unit/workflows/test_graph_validation.py` (target 18-25 tests, all sync, no asyncio). Use minimal dict-based test fixtures — no need for actual GraphNode/GraphEdge Pydantic instances. Mirror the test layout from `tests/unit/workflows/test_registry_graph_fields.py` (Phase 109-02).
  </action>
  <verify>
    <automated>uv run pytest tests/unit/workflows/test_graph_validation.py -v 2>&1 | tail -30</automated>
  </verify>
  <done>Module exists; >=18 tests pass; ruff clean; ty clean (or documented absent like 109-02); algorithm correctness verified for all 5 rules + multi-error cases + happy path.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 03-02: POST /workflows/templates/{id}/validate endpoint + auth wiring</name>
  <files>app/routers/workflows.py, tests/unit/routers/test_workflow_validate_endpoint.py</files>
  <behavior>
    Tests must assert (target 8-12 tests):
    - POST with valid graph returns 200 with {errors: []}
    - POST with invalid graph (e.g. cycle) returns 200 with {errors: [...]} non-empty
    - POST against a template owned by another user returns 403 (auth check mirrors GET)
    - POST against a seed template (created_by IS NULL) succeeds for any authenticated user (read-only-seeds policy)
    - POST against non-existent template returns 404
    - POST with malformed body (graph_nodes not a list) returns 422 (Pydantic validation)
    - POST with node kind not in the 7-kind Literal returns 422
    - Endpoint does NOT call any DB write — only loads the template metadata for auth
    - Endpoint is rate-limited via existing limiter.limit decorator (same pattern as other workflow endpoints)
  </behavior>
  <action>
In `app/routers/workflows.py` (appending to the BOTTOM of the existing routes — past Plan 02's PUT/history/revert additions if they landed first):

1. Add Pydantic request/response models near the other models:

```python
class ValidateGraphRequest(BaseModel):
    graph_nodes: list[GraphNode]
    graph_edges: list[GraphEdge]

class ValidationErrorItem(BaseModel):
    node_id: str | None
    rule: int
    message: str

class ValidateGraphResponse(BaseModel):
    errors: list[ValidationErrorItem]
```

2. Add the endpoint:

```python
@router.post("/templates/{template_id}/validate", response_model=ValidateGraphResponse)
@limiter.limit(get_user_persona_limit)
async def validate_template_graph(
    request: Request,
    template_id: str,
    body: ValidateGraphRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Validate a proposed workflow graph against Phase 110 in-scope rules.

    Phase 110 enforces rules 1, 2, 3, 6, 7. Rules 4 and 5 are Phase 3/4.
    Returns 200 with {errors: [...]} — empty list means valid; non-empty
    means the frontend should block Save and render red node badges.
    """
    from app.workflows.graph_validation import validate_workflow_graph

    engine = get_workflow_engine()
    tmpl = await engine.get_template(template_id)
    if "error" in tmpl:
        raise HTTPException(status_code=404, detail=tmpl.get("error", "Template not found"))

    # Auth: same shape as GET /templates/{id} — seed templates (created_by IS NULL)
    # are world-readable; user templates require created_by = user_id
    if tmpl.get("created_by") is not None and tmpl.get("created_by") != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    errors = validate_workflow_graph(
        [n.model_dump() for n in body.graph_nodes],
        [e.model_dump() for e in body.graph_edges],
    )
    return ValidateGraphResponse(
        errors=[ValidationErrorItem(**e.model_dump()) for e in errors],
    )
```

3. Tests at `tests/unit/routers/test_workflow_validate_endpoint.py` follow the FastAPI TestClient + dependency_overrides pattern from Phase 109-02's `test_templates_api_returns_graph.py`. Mount only the workflows router; override get_current_user_id; patch get_workflow_engine.

Important: the endpoint is purely additive — does NOT modify Plan 02's PUT/GET/POST endpoints. If Plan 02 has shipped its PUT endpoint by the time this plan runs, you may ALSO add a one-line patch inside Plan 02's PUT handler to call `validate_workflow_graph()` and reject 400 if errors are non-empty. If Plan 02 has NOT yet shipped, leave that wiring for Plan 02 to absorb (the merge is straightforward; cite this plan's `validate_workflow_graph` function in the Plan 02 follow-up).
  </action>
  <verify>
    <automated>uv run pytest tests/unit/routers/test_workflow_validate_endpoint.py -v 2>&1 | tail -20</automated>
  </verify>
  <done>Endpoint exists at POST /workflows/templates/{template_id}/validate; >=8 tests pass; auth checks mirror GET /templates/{id}; pure function delegation (no DB write).</done>
</task>

<task type="auto">
  <name>Task 03-03: Regenerate OpenAPI types + named TS exports for ValidationErrorItem</name>
  <files>frontend/src/types/api.generated.ts, frontend/src/services/workflows.ts</files>
  <action>
1. From the project root, run `cd frontend && npm run generate:types` (or the equivalent path from Plan 02 if it landed first).
2. Verify `ValidateGraphRequest`, `ValidationErrorItem`, `ValidateGraphResponse` appear in `api.generated.ts`.
3. Add a named TS export in `frontend/src/services/workflows.ts` (next to the existing GraphNode/GraphEdge exports):

```typescript
export type ValidationError = components['schemas']['ValidationErrorItem'];
export type ValidateGraphResponse = components['schemas']['ValidateGraphResponse'];
```

This lets Plan 04's useGraphValidation hook import the type by name instead of via components['schemas'] indexing.

4. Do NOT add the `validateTemplate(id, graph)` service function in this plan — that's Plan 04's frontend integration responsibility.
5. Verify TypeScript: `cd frontend && npx tsc --noEmit`.
  </action>
  <verify>
    <automated>grep -c "ValidationErrorItem\|ValidateGraphResponse\|ValidateGraphRequest" frontend/src/types/api.generated.ts; grep -c "ValidationError\|ValidateGraphResponse" frontend/src/services/workflows.ts</automated>
  </verify>
  <done>api.generated.ts contains the three new schemas; services/workflows.ts has named TS type aliases; tsc clean.</done>
</task>

</tasks>

<verification>
End-to-end checks:

1. `validate_workflow_graph()` is importable + callable: `python -c "from app.workflows.graph_validation import validate_workflow_graph; print(validate_workflow_graph([{'id':'t','kind':'trigger','label':'T'},{'id':'o','kind':'output','label':'O'}], [{'id':'e1','source':'t','target':'o'}]))"` returns `[]`.
2. Same call with a cycle returns errors with rule=3.
3. POST /workflows/templates/{id}/validate with valid graph returns `{"errors":[]}` (200).
4. POST with cycle returns `{"errors":[{"node_id":"...","rule":3,"message":"..."}]}` (200, NOT 4xx — the endpoint always returns 200 for permission-passing reqs; the validation result lives in the body).
5. Frontend tsc clean.
6. All unit tests pass: `uv run pytest tests/unit/workflows/test_graph_validation.py tests/unit/routers/test_workflow_validate_endpoint.py -v`.
7. Ruff + format clean.
8. Branch hygiene: `git branch --show-current` confirms correct branch before every commit.
</verification>

<success_criteria>
This plan ships when:
- One new module: `app/workflows/graph_validation.py` (~200-300 lines).
- One new endpoint added to `app/routers/workflows.py`: POST /templates/{id}/validate.
- Three new Pydantic models: `ValidateGraphRequest`, `ValidationErrorItem`, `ValidateGraphResponse` (additional, not modifying Plan 02's models).
- Regenerated `api.generated.ts` includes them.
- Two named TS type aliases in `services/workflows.ts`.
- Two test files with combined >=26 passing tests.
- Plan SUMMARY committed.
- Addresses roadmap success criterion #8 (server-side validation enforces same rules, returns structured errors).
</success_criteria>

<output>
After completion, create `.planning/phases/110-workflow-node-editor-editable/110-03-SUMMARY.md` with the standard sections. Specifically document: (a) whether Plan 02's PUT was patched to call validate_workflow_graph or whether that wiring was left as a Plan 02 follow-up, (b) how the deferred rules 4 and 5 surface to callers (NotImplementedError on strict=True), (c) per-kind config schema tradeoffs (tight for kinds that execute today, permissive for Phase 3/4 kinds).
</output>

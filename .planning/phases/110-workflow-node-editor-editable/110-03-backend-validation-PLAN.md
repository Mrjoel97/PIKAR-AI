---
phase: 110-workflow-node-editor-editable
plan: 03
type: execute
wave: 3
depends_on: [110-01, 110-02]
files_modified:
  - app/workflows/graph_validation.py
  - app/routers/workflows.py
  - tests/unit/workflows/test_graph_validation.py
  - tests/unit/routers/test_workflow_validate_endpoint.py
  - tests/fixtures/graph_validation_cases.json
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
    - "Server's validate_workflow_graph() is wired into Plan 02's PUT handler — every save call goes through validation before save_template_version() (no conditional / follow-up; Plan 02 has already shipped by Wave 3)"
    - "Server and client validators agree byte-for-byte on the same input via a shared JSON fixture at tests/fixtures/graph_validation_cases.json — Plan 03 server tests parametrize over it; Plan 04 client tests load the same file and parametrize their validateGraphClient() tests over the same cases"
  artifacts:
    - path: "app/workflows/graph_validation.py"
      provides: "validate_workflow_graph() + per-kind Pydantic config schemas + ValidationError typed result"
      contains: "def validate_workflow_graph"
    - path: "app/routers/workflows.py"
      provides: "POST /workflows/templates/{id}/validate endpoint + ValidateGraphRequest + ValidateGraphResponse Pydantic models; PUT /templates/{id} handler updated to call validate_workflow_graph() before save_template_version()"
      contains: "validate"
    - path: "tests/fixtures/graph_validation_cases.json"
      provides: "Shared canonical test cases for graph validation — used by Plan 03 server tests (pytest parametrize) AND Plan 04 client tests (vitest parametrize). Single source of truth for client/server parity (B-4)."
      contains: "valid_minimal"
  key_links:
    - from: "POST /workflows/templates/{id}/validate"
      to: "validate_workflow_graph() in app/workflows/graph_validation.py"
      via: "Direct function call (sync, pure — no DB hit)"
      pattern: "validate_workflow_graph"
    - from: "validate_workflow_graph"
      to: "Per-kind config schemas (TriggerConfig, AgentActionConfig, ConditionConfig, ...)"
      via: "Pydantic model_validate on node.config based on node.kind"
      pattern: "model_validate"
    - from: "PUT /workflows/templates/{template_id} handler"
      to: "validate_workflow_graph() (unconditional wire — Plan 02 already shipped)"
      via: "Direct call inside the handler; 400 returned if errors list non-empty before save_template_version() runs"
      pattern: "validate_workflow_graph"
    - from: "tests/fixtures/graph_validation_cases.json"
      to: "Plan 03 pytest parametrize + Plan 04 vitest parametrize"
      via: "Single canonical JSON file; both test suites import + parametrize over the same cases"
      pattern: "graph_validation_cases.json"
---

<objective>
Ship server-side graph validation as a pure-functional module that both the new POST /validate endpoint AND the PUT save endpoint can call. Enforces 5 of the 7 spec validation rules (the 5 in scope for Phase 110: single trigger, reachability, no cycles, ≥1 output, per-kind config schema). Rules 4 (condition outgoing degree) and 5 (parallel/merge pairing) are stubbed for Phase 3/4.

B-1 fix: Plan 03 runs in Wave 3 (after Plan 02) because both modify `app/routers/workflows.py`. Sequential safety beats parallel risk — Phase 109 was burned by exactly this pattern.

B-4 fix: Plan 03 produces `tests/fixtures/graph_validation_cases.json` as the SHARED single source of truth for client/server validation parity. Plan 04's `validateGraphClient()` vitest tests parametrize over the same fixture.
Output: One new module (~250 lines), one new endpoint, one shared JSON fixture, two test files (~25-35 combined tests, parametrized over the fixture).
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
@.planning/phases/110-workflow-node-editor-editable/110-02-SUMMARY.md
@app/routers/workflows.py
@app/workflows/engine.py

<interfaces>
<!-- Shared with Plan 02 (these already exist in app/routers/workflows.py post Phase 109-02 + Plan 02): -->
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

<!-- Plan 02 already shipped (Wave 2 → Plan 03 runs in Wave 3 after Plan 02 lands): -->
@router.put("/templates/{template_id}", response_model=SaveTemplateSuccessResponse)
async def update_template(...):
    # Plan 02 handler. Plan 03 INSERTS a validate_workflow_graph() call here before
    # save_template_version() — see Task 03-02 below for the exact patch.

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
- **B-1 fix: this plan moved from Wave 2 to Wave 3.** Both Plan 02 AND Plan 03 modify `app/routers/workflows.py`. Phase 109 shipped a similar burn where two parallel plans touched the same file — that's the lesson. Sequential is safer. Plan 03 runs AFTER Plan 02 fully ships (depends_on: [110-01, 110-02]).
- **No more "if Plan 02 has shipped..." conditional language in Task 03-02.** By Wave 3, Plan 02 has definitely shipped. Plan 03 directly wires `validate_workflow_graph()` into the PUT handler that Plan 02 created. The patch is unconditional.
- File ownership rule (with Plan 02 already on disk): Plan 03 places its endpoint at the BOTTOM of the router (after all of Plan 02's additions: PUT, GET history, POST revert, ETag helper, all Pydantic models). Plan 03's Pydantic models (ValidateGraphRequest, ValidateGraphResponse, ValidationErrorItem) are also added at the bottom of the models section.
- Per-kind config schemas: trigger/agent-action/output are real and tight; condition/parallel/merge/human-approval are placeholders (accept any dict; Phase 3/4 tightens). Tight schemas for the first three:
  - TriggerConfig: `{ trigger_type: Literal['manual','schedule','event'] | None, ...allow extras }`
  - AgentActionConfig: `{ tool_name: str, arguments: dict, agent_role: str | None }`
  - OutputConfig: `{ output_format: str | None, ...allow extras }`
- Cycle detection: use Kahn's algorithm (topological sort via in-degree). Pure-Python, ~30 LOC. Returns a list of node_ids involved in cycles. NetworkX would be overkill — no existing dep on it.
- Reachability: BFS from the trigger node. Any node not visited is unreachable → emit a rule-2 ValidationError with the offending node_id.
- The validate endpoint does NOT need to actually load the template from DB — it accepts the proposed graph in the request body. This lets the frontend run it on every save without a round-trip to fetch the current template. The {id} in the URL is used only for auth (the user must have read access to the template).
- **B-4 shared fixture file:** `tests/fixtures/graph_validation_cases.json` is the canonical source of truth for validation behavior. Plan 03's pytest suite parametrizes over it; Plan 04's vitest suite loads the same file and parametrizes its `validateGraphClient()` tests over the same cases. Both assert `expected_errors` matches actual. ANY change to validation behavior must update this fixture, and both test suites will catch divergence automatically.
- Branch hygiene: every task includes an automated branch-check verify step (W-6).
</context_notes>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 03-01: validate_workflow_graph() pure function + per-kind config schemas + shared JSON fixture (B-4)</name>
  <files>app/workflows/graph_validation.py, tests/unit/workflows/test_graph_validation.py, tests/fixtures/graph_validation_cases.json</files>
  <behavior>
    Tests must assert (target 18-25 tests, MANY parametrized over the shared fixture):
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
    - strict=True with condition node having 1 outgoing edge: NotImplementedError (Phase 3/4 wiring TBD)
    - Empty graph_nodes list: returns rule-1 error (no trigger)
    - Malformed node (missing kind): pydantic raises ValidationError before validate_workflow_graph runs (catch at caller)
    - **B-4 parametrized:** every named case in tests/fixtures/graph_validation_cases.json must produce the documented `expected_errors` list (one pytest parametrize over the fixture).
  </behavior>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted (W-6).

**STEP A — Create the shared fixture file** at `tests/fixtures/graph_validation_cases.json` (B-4). This is the canonical source of truth for client/server validation parity:

```json
[
  {
    "name": "valid_minimal",
    "description": "Trigger → agent-action → output. Simplest valid linear graph.",
    "input": {
      "graph_nodes": [
        {"id": "t1", "kind": "trigger", "label": "Start", "config": {"trigger_type": "manual"}},
        {"id": "a1", "kind": "agent-action", "label": "Run", "config": {"tool_name": "noop"}},
        {"id": "o1", "kind": "output", "label": "Done", "config": {}}
      ],
      "graph_edges": [
        {"id": "e1", "source": "t1", "target": "a1"},
        {"id": "e2", "source": "a1", "target": "o1"}
      ]
    },
    "expected_errors": []
  },
  {
    "name": "no_trigger",
    "description": "Graph has no trigger node at all.",
    "input": {
      "graph_nodes": [
        {"id": "a1", "kind": "agent-action", "label": "Run", "config": {"tool_name": "noop"}},
        {"id": "o1", "kind": "output", "label": "Done", "config": {}}
      ],
      "graph_edges": [
        {"id": "e1", "source": "a1", "target": "o1"}
      ]
    },
    "expected_errors": [
      {"node_id": null, "rule": 1, "message_contains": "No trigger"}
    ]
  },
  {
    "name": "two_triggers",
    "description": "Two trigger nodes — second one flagged.",
    "input": {
      "graph_nodes": [
        {"id": "t1", "kind": "trigger", "label": "S1", "config": {}},
        {"id": "t2", "kind": "trigger", "label": "S2", "config": {}},
        {"id": "o1", "kind": "output", "label": "Done", "config": {}}
      ],
      "graph_edges": [
        {"id": "e1", "source": "t1", "target": "o1"},
        {"id": "e2", "source": "t2", "target": "o1"}
      ]
    },
    "expected_errors": [
      {"node_id": "t2", "rule": 1, "message_contains": "Multiple trigger"}
    ]
  },
  {
    "name": "trigger_with_incoming_edge",
    "description": "Trigger has an incoming edge — invalid.",
    "input": {
      "graph_nodes": [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "a1", "kind": "agent-action", "label": "A", "config": {"tool_name": "noop"}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}}
      ],
      "graph_edges": [
        {"id": "e1", "source": "t1", "target": "a1"},
        {"id": "e2", "source": "a1", "target": "t1"},
        {"id": "e3", "source": "a1", "target": "o1"}
      ]
    },
    "expected_errors": [
      {"node_id": "t1", "rule": 1, "message_contains": "zero incoming"}
    ]
  },
  {
    "name": "unreachable_node",
    "description": "agent-action 'orphan' not reachable from trigger.",
    "input": {
      "graph_nodes": [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "a1", "kind": "agent-action", "label": "A", "config": {"tool_name": "noop"}},
        {"id": "orphan", "kind": "agent-action", "label": "Orphan", "config": {"tool_name": "noop"}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}}
      ],
      "graph_edges": [
        {"id": "e1", "source": "t1", "target": "a1"},
        {"id": "e2", "source": "a1", "target": "o1"}
      ]
    },
    "expected_errors": [
      {"node_id": "orphan", "rule": 2, "message_contains": "unreachable"}
    ]
  },
  {
    "name": "cycle_two_nodes",
    "description": "Two-node cycle a1 ↔ a2 between trigger and output.",
    "input": {
      "graph_nodes": [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "a1", "kind": "agent-action", "label": "A1", "config": {"tool_name": "noop"}},
        {"id": "a2", "kind": "agent-action", "label": "A2", "config": {"tool_name": "noop"}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}}
      ],
      "graph_edges": [
        {"id": "e1", "source": "t1", "target": "a1"},
        {"id": "e2", "source": "a1", "target": "a2"},
        {"id": "e3", "source": "a2", "target": "a1"},
        {"id": "e4", "source": "a2", "target": "o1"}
      ]
    },
    "expected_errors": [
      {"node_id": "a1", "rule": 3, "message_contains": "cycle"},
      {"node_id": "a2", "rule": 3, "message_contains": "cycle"}
    ]
  },
  {
    "name": "no_output",
    "description": "Graph has trigger and actions but no output node.",
    "input": {
      "graph_nodes": [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "a1", "kind": "agent-action", "label": "A", "config": {"tool_name": "noop"}}
      ],
      "graph_edges": [
        {"id": "e1", "source": "t1", "target": "a1"}
      ]
    },
    "expected_errors": [
      {"node_id": null, "rule": 6, "message_contains": "output"}
    ]
  },
  {
    "name": "bad_agent_action_config",
    "description": "agent-action node missing required tool_name.",
    "input": {
      "graph_nodes": [
        {"id": "t1", "kind": "trigger", "label": "T", "config": {}},
        {"id": "a1", "kind": "agent-action", "label": "A", "config": {"agent_role": "marketer"}},
        {"id": "o1", "kind": "output", "label": "O", "config": {}}
      ],
      "graph_edges": [
        {"id": "e1", "source": "t1", "target": "a1"},
        {"id": "e2", "source": "a1", "target": "o1"}
      ]
    },
    "expected_errors": [
      {"node_id": "a1", "rule": 7, "message_contains": "tool_name"}
    ]
  }
]
```

The `message_contains` field is a substring check (NOT exact match) — this lets server and client phrase messages naturally without forced literal equality, while still asserting the message conveys the right concept.

**STEP B — Create the validator** at `app/workflows/graph_validation.py`:

```python
"""Server-side workflow graph validation — Phase 110.

Pure-functional validator. No DB access, no async, no IO. Called from:
  - POST /workflows/templates/{id}/validate (this plan)
  - PUT /workflows/templates/{id} save handler (Plan 02 — wired unconditionally in Task 03-02 below)

Mirrors the client-side validator in frontend/src/components/workflows/editor/useGraphValidation.ts
(Plan 04). The two MUST stay in sync; the canonical test fixture lives at
tests/fixtures/graph_validation_cases.json — both server (pytest) and client (vitest) tests
parametrize over it.
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


class _PermissiveConfig(BaseModel):
    model_config = {'extra': 'allow'}


_CONFIG_SCHEMAS: dict[str, type[BaseModel]] = {
    'trigger':         TriggerConfig,
    'agent-action':    AgentActionConfig,
    'output':          OutputConfig,
    'condition':       _PermissiveConfig,
    'parallel':        _PermissiveConfig,
    'merge':           _PermissiveConfig,
    'human-approval':  _PermissiveConfig,
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
            continue
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

**STEP C — Tests** at `tests/unit/workflows/test_graph_validation.py` (target 18-25 tests, all sync, no asyncio).

Add a parametrize fixture loader:

```python
import json
from pathlib import Path

FIXTURE_PATH = Path(__file__).parents[2] / "fixtures" / "graph_validation_cases.json"


def _load_cases():
    with FIXTURE_PATH.open() as f:
        return json.load(f)


CASES = _load_cases()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_fixture_case(case):
    """Parametrized: every case in graph_validation_cases.json must produce its expected_errors."""
    actual = validate_workflow_graph(case["input"]["graph_nodes"], case["input"]["graph_edges"])
    expected = case["expected_errors"]
    assert len(actual) == len(expected), f"Error count mismatch for case {case['name']}: got {actual}, expected {expected}"
    for e_expected, e_actual in zip(expected, actual, strict=False):
        assert e_actual.node_id == e_expected["node_id"], f"node_id mismatch for case {case['name']}"
        assert e_actual.rule == e_expected["rule"], f"rule mismatch for case {case['name']}"
        if "message_contains" in e_expected:
            assert e_expected["message_contains"].lower() in e_actual.message.lower(), \
                f"message_contains '{e_expected['message_contains']}' not in '{e_actual.message}' for case {case['name']}"
```

Plus individual tests for edge cases NOT in the fixture (e.g. strict=True NotImplementedError, empty list, malformed node missing kind). Mirror the test layout from `tests/unit/workflows/test_registry_graph_fields.py` (Phase 109-02).
  </action>
  <verify>
    <automated>uv run pytest tests/unit/workflows/test_graph_validation.py -v 2>&1 | tail -30</automated>
    <automated>test -f tests/fixtures/graph_validation_cases.json && python -c "import json; cases=json.load(open('tests/fixtures/graph_validation_cases.json')); print(f'Fixture cases: {len(cases)}'); assert len(cases) >= 7, 'Need at least 7 named cases'; assert all('name' in c and 'input' in c and 'expected_errors' in c for c in cases), 'All cases need name, input, expected_errors'"</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Module exists; fixture JSON has >=7 named cases with name/input/expected_errors structure; >=18 tests pass (including parametrized fixture cases); ruff clean; algorithm correctness verified for all 5 rules + multi-error cases + happy path. Plan 04 will load the same fixture for client parity.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 03-02: POST /workflows/templates/{id}/validate endpoint + WIRE validation into Plan 02's PUT handler (unconditional)</name>
  <files>app/routers/workflows.py, tests/unit/routers/test_workflow_validate_endpoint.py</files>
  <behavior>
    Tests must assert (target 10-14 tests):
    - POST with valid graph returns 200 with {errors: []}
    - POST with invalid graph (e.g. cycle) returns 200 with {errors: [...]} non-empty
    - POST against a template owned by another user returns 403 (auth check mirrors GET)
    - POST against a seed template (created_by IS NULL) succeeds for any authenticated user (read-only-seeds policy)
    - POST against non-existent template returns 404
    - POST with malformed body (graph_nodes not a list) returns 422 (Pydantic validation)
    - POST with node kind not in the 7-kind Literal returns 422
    - Endpoint does NOT call any DB write — only loads the template metadata for auth
    - Endpoint is rate-limited via existing limiter.limit decorator (same pattern as other workflow endpoints)
    - **NEW (B-1 wave-3 wiring):** PUT /workflows/templates/{id} with an invalid graph body (e.g. cycle) returns 400 BEFORE save_template_version() is called — verify by asserting save_template_version mock was NOT invoked when validation fails
    - **NEW (B-1 wave-3 wiring):** PUT /workflows/templates/{id} with a valid graph body proceeds normally through save_template_version() (validation passes silently)
  </behavior>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted (W-6).

Plan 02 has already shipped (Wave 2 → Plan 03 is Wave 3 — B-1). The PUT handler exists in `app/routers/workflows.py`. Plan 03 now:

**STEP A — Append the validate endpoint and request/response models** at the BOTTOM of `app/routers/workflows.py` (after all of Plan 02's additions):

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

**STEP B — Wire validation into Plan 02's PUT handler (UNCONDITIONAL — no "if Plan 02 has shipped" hedge; by Wave 3 it has).**

In the existing PUT handler that Plan 02 created (`@router.put("/templates/{template_id}", ...)`), insert a call to `validate_workflow_graph` BEFORE the call to `save_template_version`. Pattern:

```python
# Plan 02's PUT handler body, with Plan 03's insertion:
from app.workflows.graph_validation import validate_workflow_graph  # add this import near top of file

# (after parsing body, after auth checks, BEFORE save_template_version call)
validation_errors = validate_workflow_graph(
    [n.model_dump() for n in body.graph_nodes],
    [e.model_dump() for e in body.graph_edges],
)
if validation_errors:
    raise HTTPException(
        status_code=400,
        detail={
            "error": "validation_failed",
            "errors": [
                {"node_id": e.node_id, "rule": e.rule, "message": e.message}
                for e in validation_errors
            ],
        },
    )

# Plan 02's save_template_version call continues here, unchanged.
```

Plan 02's existing tests for the PUT handler need an update: add two new assertions to `tests/unit/routers/test_workflow_save_endpoint.py` (or in this plan's new file — choose based on convention):

- `test_put_with_invalid_graph_returns_400_and_skips_save` — submit a body with a cycle; assert 400 and assert `save_template_version` mock was NOT called.
- `test_put_with_valid_graph_proceeds_to_save` — submit a valid linear graph; assert 200 and `save_template_version` mock was called exactly once.

If updating Plan 02's existing test file feels invasive, place these two tests in this plan's `test_workflow_validate_endpoint.py` and name them clearly.

**STEP C — Tests** at `tests/unit/routers/test_workflow_validate_endpoint.py`. FastAPI TestClient + dependency_overrides pattern from Phase 109-02's `test_templates_api_returns_graph.py`. Mount only the workflows router; override get_current_user_id; patch get_workflow_engine. Target 10-14 tests including the two new B-1 wave-3 wiring tests above.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/routers/test_workflow_validate_endpoint.py -v 2>&1 | tail -25</automated>
    <automated>grep -c "validate_workflow_graph" app/routers/workflows.py</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>POST /templates/{id}/validate endpoint exists; PUT handler from Plan 02 now calls validate_workflow_graph() unconditionally before save_template_version(); >=10 tests pass; PUT-with-invalid-graph returns 400 and skips save (asserted via mock).</done>
</task>

<task type="auto">
  <name>Task 03-03: Regenerate OpenAPI types + named TS exports for ValidationErrorItem</name>
  <files>frontend/src/types/api.generated.ts, frontend/src/services/workflows.ts</files>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

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
    <automated>grep -c "ValidationErrorItem\|ValidateGraphResponse\|ValidateGraphRequest" frontend/src/types/api.generated.ts</automated>
    <automated>grep -c "ValidationError\|ValidateGraphResponse" frontend/src/services/workflows.ts</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>api.generated.ts contains the three new schemas; services/workflows.ts has named TS type aliases; tsc clean.</done>
</task>

</tasks>

<verification>
End-to-end checks:

1. `validate_workflow_graph()` is importable + callable: `python -c "from app.workflows.graph_validation import validate_workflow_graph; print(validate_workflow_graph([{'id':'t','kind':'trigger','label':'T'},{'id':'o','kind':'output','label':'O'}], [{'id':'e1','source':'t','target':'o'}]))"` returns `[]`.
2. Same call with a cycle returns errors with rule=3.
3. POST /workflows/templates/{id}/validate with valid graph returns `{"errors":[]}` (200).
4. POST with cycle returns `{"errors":[{"node_id":"...","rule":3,"message":"..."}]}` (200, NOT 4xx).
5. PUT /workflows/templates/{id} with invalid graph returns 400 BEFORE save_template_version runs (B-1 wave-3 wiring).
6. Shared fixture `tests/fixtures/graph_validation_cases.json` has >=7 named cases; Plan 04 will load this same file.
7. Frontend tsc clean.
8. All unit tests pass: `uv run pytest tests/unit/workflows/test_graph_validation.py tests/unit/routers/test_workflow_validate_endpoint.py -v`.
9. Ruff + format clean.
10. Branch hygiene: `git branch --show-current` confirms correct branch before every commit (W-6, automated in every task).
</verification>

<success_criteria>
This plan ships when:
- One new module: `app/workflows/graph_validation.py` (~200-300 lines).
- One new endpoint added to `app/routers/workflows.py`: POST /templates/{id}/validate.
- Plan 02's existing PUT handler in `app/routers/workflows.py` updated to call `validate_workflow_graph()` BEFORE `save_template_version()` (B-1 wave-3 wiring — unconditional).
- Three new Pydantic models: `ValidateGraphRequest`, `ValidationErrorItem`, `ValidateGraphResponse` (additional, not modifying Plan 02's models).
- One new shared fixture file: `tests/fixtures/graph_validation_cases.json` with >=7 canonical cases (B-4 — Plan 04 will load this same file for client/server parity tests).
- Regenerated `api.generated.ts` includes the three new schemas.
- Two named TS type aliases in `services/workflows.ts`.
- Two test files with combined >=26 passing tests, many parametrized over the shared fixture.
- Plan SUMMARY committed.
- Addresses roadmap success criterion #8 (server-side validation enforces same rules, returns structured errors; AND wired into save path so direct API users cannot bypass).
</success_criteria>

<output>
After completion, create `.planning/phases/110-workflow-node-editor-editable/110-03-SUMMARY.md` with the standard sections. Specifically document: (a) the unconditional wiring of validate_workflow_graph into Plan 02's PUT handler (no longer conditional — Wave 3 means Plan 02 has shipped), (b) how the deferred rules 4 and 5 surface to callers (NotImplementedError on strict=True), (c) per-kind config schema tradeoffs (tight for kinds that execute today, permissive for Phase 3/4 kinds), (d) the canonical fixture file at tests/fixtures/graph_validation_cases.json as the contract Plan 04 must satisfy.
</output>
</content>
</invoke>
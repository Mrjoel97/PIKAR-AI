---
phase: 111-workflow-node-editor-branching-execution
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - app/workflows/graph_validation.py
  - tests/fixtures/graph_validation_cases.json
  - tests/unit/workflows/test_graph_validation.py
autonomous: true
gap_closure: false
requirements:
  - NODEEDITOR-VALIDATE-02

must_haves:
  truths:
    - "validate_workflow_graph() enforces rule 4 by default (without strict=True) — a condition node MUST have exactly 2 outgoing edges with source_handle set forming {'true', 'false'} (set equality)"
    - "The shared fixture file tests/fixtures/graph_validation_cases.json contains 5 NEW cases driving rule 4: condition_no_outgoing, condition_one_outgoing, condition_three_outgoing, condition_wrong_source_handles, condition_valid_two_handles — preserving all 8 existing cases"
    - "Pytest parametrizes over the same fixture and 13 fixture-driven cases pass (8 existing + 5 new)"
    - "When the strict flag was previously gating rule 4 (NotImplementedError), Plan 02 removes the strict gate for rule 4 ONLY; rule 5 (parallel/merge pairing) remains stubbed under strict=True per Phase 4 deferral"
    - "ValidationError emitted for a rule-4 violation has rule=4 and a message starting with 'Condition' so client message_contains substrings match"
    - "A condition node with kind='condition' but with NO outgoing edges yields exactly one rule-4 ValidationError keyed to that node_id"
    - "A condition node with 2 outgoing edges where source_handle values are {None, None} or {'true', None} yields a rule-4 ValidationError (the set-equality test catches missing handles)"
    - "The existing 8 fixture cases (Phase 110 Plan 03) still pass byte-for-byte — no regression in rules 1/2/3/6/7"
    - "The new fixture cases are syntactically valid JSON parseable by both `python -c 'import json; json.load(open(...))'` AND vitest's built-in JSON loader (Plan 04 will consume the same file)"
    - "The PUT save handler in app/routers/workflows.py is NOT modified — it already calls validate_workflow_graph() unconditionally (Plan 110-03 wired this) and rule 4 enforcement is automatic via the validator extension"
  artifacts:
    - path: "app/workflows/graph_validation.py"
      provides: "Rule 4 implementation (condition outgoing degree) — function added at module scope, called from validate_workflow_graph() before/after rule 7"
      contains: "_validate_rule_4_condition_outgoing_degree"
    - path: "tests/fixtures/graph_validation_cases.json"
      provides: "5 new rule-4 cases + 8 preserved cases = 13 total"
      contains: "condition_valid_two_handles"
    - path: "tests/unit/workflows/test_graph_validation.py"
      provides: "5 new rule-4 specific tests + parametrized fixture loop now sees 13 cases (8 + 5)"
      contains: "test_rule_4_"
  key_links:
    - from: "app/workflows/graph_validation.py:validate_workflow_graph"
      to: "_validate_rule_4_condition_outgoing_degree"
      via: "in-module function call, always executed (not gated by strict=True)"
      pattern: "_validate_rule_4_condition_outgoing_degree\\("
    - from: "tests/unit/workflows/test_graph_validation.py"
      to: "tests/fixtures/graph_validation_cases.json"
      via: "fixture load + pytest.mark.parametrize (preserves Phase 110 pattern)"
      pattern: "graph_validation_cases.json"
---

<objective>
Extend `validate_workflow_graph()` (Phase 110 Plan 03's pure-functional validator) with rule 4: a `condition` node MUST have exactly 2 outgoing edges with `source_handle` values forming the set `{'true', 'false'}`. Add 5 new cases to the shared `tests/fixtures/graph_validation_cases.json` so both pytest (this plan) and vitest (Plan 04 client validator) catch divergence. Flip the existing `strict=True` NotImplementedError gate for rule 4 only — rule 5 (parallel/merge pairing) remains deferred to Phase 4.

Purpose: Close ROADMAP criterion 5. The PUT save handler (Phase 110 Plan 03 wired) already calls `validate_workflow_graph()` unconditionally, so this plan's extension automatically enforces rule 4 on every Save without additional router changes. The shared fixture is the contract — Plan 04 will mirror behavior client-side and the same JSON file drives both test runners.

Output: ~50 line extension to `graph_validation.py`, 5 new fixture cases, 5+ new pytest cases. Zero new endpoints, zero migrations, zero new files.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/111-workflow-node-editor-branching-execution/111-CONTEXT.md
@.planning/phases/110-workflow-node-editor-editable/110-03-SUMMARY.md
@app/workflows/graph_validation.py
@tests/fixtures/graph_validation_cases.json
@tests/unit/workflows/test_graph_validation.py
@CLAUDE.md

<interfaces>
<!-- Current shape of validate_workflow_graph (Phase 110 Plan 03) — extend, don't replace. -->

```python
def validate_workflow_graph(
    graph_nodes: list[dict[str, Any]],
    graph_edges: list[dict[str, Any]],
    *,
    strict: bool = False,
) -> list[ValidationError]:
    if strict:
        raise NotImplementedError(
            "strict=True (rules 4 + 5) is Phase 3/4 work"
        )
    # ... rules 1, 2, 3, 6, 7 implemented ...
```

After this plan:
```python
def validate_workflow_graph(
    graph_nodes: list[dict[str, Any]],
    graph_edges: list[dict[str, Any]],
    *,
    strict: bool = False,
) -> list[ValidationError]:
    # Rule 5 (parallel/merge pairing) still stubbed for Phase 4:
    if strict:
        raise NotImplementedError(
            "strict=True (rule 5 — parallel/merge pairing) is Phase 4 work"
        )
    # ... rules 1, 2, 3, 6, 7 unchanged ...
    # NEW: rule 4 always executed (no strict gate)
    errors.extend(_validate_rule_4_condition_outgoing_degree(graph_nodes, graph_edges))
    return errors
```

ValidationError shape (unchanged):
```python
class ValidationError(BaseModel):
    node_id: str | None
    rule: int       # now includes 4
    message: str
```

Shared fixture format (preserved):
```json
{
  "name": "case_name",
  "description": "...",
  "input": {"graph_nodes": [...], "graph_edges": [...]},
  "expected_errors": [
    {"node_id": "c1", "rule": 4, "message_contains": "Condition"}
  ]
}
```
</interfaces>

<context_notes>
**Existing rule order in validate_workflow_graph (per Phase 110 Plan 03 SUMMARY):** 1 → 6 → 2 → 3 → 7. Append rule 4 logic AFTER rule 7 so the existing test assertions on error order don't shift. Rule 4 errors come last in the returned list. Confirm by re-reading the current file and inserting at the right spot.

**The PUT handler is NOT modified.** Per Plan 110-03 SUMMARY, the PUT handler in `app/routers/workflows.py` already calls `validate_workflow_graph(req.graph_nodes, req.graph_edges)` unconditionally before save_template_version. Extending the validator means PUT automatically enforces rule 4. Verify this by grep before/after Plan 02 changes: `grep -n "validate_workflow_graph" app/routers/workflows.py` — should be 2 matches (the import and the call), unchanged before and after.

**Discretion #5 from Phase 110 — strict flag semantics:** Phase 110 documented "strict=True raises NotImplementedError" for both rule 4 AND rule 5. Phase 111 implements rule 4 unconditionally (not behind strict) and updates the docstring + NotImplementedError message to ONLY mention rule 5. Plan 03's wired call site uses `strict=False` (default), so this change is transparent to existing callers.

**No migrations, no new dependencies, no router changes.** This plan is the smallest in Phase 111 — pure logic extension + fixture additions + tests.

**Fixture file is load-bearing for client parity:** Plan 04 (Wave 3) parametrizes vitest over `tests/fixtures/graph_validation_cases.json`. Plan 02's 5 new cases will be picked up automatically by vitest — Plan 04 must add the corresponding client-side rule 4 implementation. Plan 02 + Plan 04 share the contract.

**Edge source_handle convention check at runtime:** Edges may carry `source_handle` as a string, `None`, or omit the key entirely. The set-equality test must handle all three. Recommended pattern:
```python
handles = {e.get("source_handle") for e in outgoing_edges}
if handles != {"true", "false"}:
    # emit rule 4 error
```
This treats `None` and missing-key identically (both produce `None` in the set), and the set comparison naturally catches `{None}`, `{"true"}`, `{"true", "false", "maybe"}`, etc.

**Determinism:** Phase 110 Plan 03 documented "Cycle error emission walks graph_nodes in order (not set iteration)" — apply the same pattern. Iterate `graph_nodes` (not the set of conditions) when emitting errors so multiple condition violations come out in declaration order, deterministic across Python runs.

**Branch hygiene:** `git branch --show-current` before EVERY commit — must be `plan-109-spec-b-phase-1`.

**CLAUDE.md conventions:** Ruff E/W/F/I/N/D/UP/B/C4/SIM/ARG/PIE/PERF/RUF. Google-style docstring on the new helper. NO bare except. NO print().
</context_notes>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 02-01: Extend shared fixture with 5 rule-4 cases</name>
  <files>tests/fixtures/graph_validation_cases.json</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`.
    Verify Phase 110 Plan 03's 8 existing cases are intact: `python -c "import json; cases = json.load(open('tests/fixtures/graph_validation_cases.json')); print(len(cases)); assert len(cases) == 8"`.
  </precondition>
  <behavior>
    Add EXACTLY these 5 cases to the existing JSON array (preserve all 8 prior cases; total = 13 after this task):

    1. **`condition_no_outgoing`** — graph: trigger t1 → condition c1, output o1. Edges: t1→c1. No edges from c1. expected_errors:
       - `{node_id: "o1", rule: 2, message_contains: "unreachable"}` (o1 is unreachable since c1 has no outgoing)
       - `{node_id: "c1", rule: 4, message_contains: "Condition"}` (the new rule)
    2. **`condition_one_outgoing`** — graph: t1 → c1 → o1, with edge c1→o1 carrying `source_handle: "true"`. Only one outgoing from c1. expected_errors:
       - `{node_id: "c1", rule: 4, message_contains: "Condition"}` (handle set is `{"true"}`, not `{"true", "false"}`)
    3. **`condition_three_outgoing`** — graph: t1 → c1, c1 → o1 (handle 'true'), c1 → o2 (handle 'false'), c1 → o3 (handle 'maybe'); o1, o2, o3 all output kind. expected_errors:
       - `{node_id: "c1", rule: 4, message_contains: "Condition"}` (3 outgoing, set has 3 elements not 2)
    4. **`condition_wrong_source_handles`** — graph: t1 → c1, c1 → o1 (handle 'left'), c1 → o2 (handle 'right'). expected_errors:
       - `{node_id: "c1", rule: 4, message_contains: "Condition"}` (2 outgoing but set = `{"left", "right"}` not `{"true", "false"}`)
    5. **`condition_valid_two_handles`** — graph: t1 → c1, c1 → o1 (handle 'true'), c1 → o2 (handle 'false'). c1 has `config: {"expression": {">": [{"var": "x"}, 0]}}` so rule 7 (per-kind config) doesn't fire on the PermissiveConfigSchema — but DOUBLE-CHECK: at Plan 02 time, condition's schema is still `_PermissiveConfig` (Plan 04 will tighten it). expected_errors: `[]` (valid graph).

    CRITICAL: cases must NOT trigger rule 2 (unreachability) or other rules unintentionally. Use full trigger → condition → output paths with both 'true' and 'false' branches terminating in output nodes where applicable. The exception is case 1 (`condition_no_outgoing`) where the unreachable o1 is EXPECTED — the test's `expected_errors` covers it.

    Verify the file parses: `python -c "import json; cases = json.load(open('tests/fixtures/graph_validation_cases.json')); assert len(cases) == 13"`.

    Commit message: `test(111-02): add 5 rule-4 fixture cases for condition outgoing degree`
  </behavior>
  <action>
    Read the current file. Append the 5 new cases AFTER the existing 8 (preserving order so test assertions stay stable). Use 2-space indentation matching the existing file. Verify JSON validity post-write.

    DO NOT modify any existing case's input or expected_errors — Phase 110's 8 cases are load-bearing. Strictly additive change.

    DO NOT add a trailing comma to the last element (JSON forbids).
  </action>
  <verify>
    <automated>.venv/Scripts/python -c "import json; cases = json.load(open('tests/fixtures/graph_validation_cases.json')); assert len(cases) == 13; assert any(c['name'] == 'condition_valid_two_handles' for c in cases); print('OK', len(cases))"</automated>
    <automated>.venv/Scripts/python -c "import json; cases = json.load(open('tests/fixtures/graph_validation_cases.json')); names = [c['name'] for c in cases]; new = ['condition_no_outgoing', 'condition_one_outgoing', 'condition_three_outgoing', 'condition_wrong_source_handles', 'condition_valid_two_handles']; assert all(n in names for n in new), f'Missing: {set(new) - set(names)}'"</automated>
  </verify>
  <done>
    - File parses as valid JSON.
    - 13 cases total.
    - 5 new case names present.
    - 8 Phase 110 cases byte-for-byte preserved (verify via grep on a unique substring from each).
    - One commit on `plan-109-spec-b-phase-1` with message `test(111-02): add 5 rule-4 fixture cases for condition outgoing degree`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 02-02: Implement rule 4 in graph_validation.py + parametrize 13 fixture cases</name>
  <files>app/workflows/graph_validation.py, tests/unit/workflows/test_graph_validation.py</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`. Verify Task 02-01 (5 new fixture cases) is committed.
  </precondition>
  <behavior>
    **RED phase — extend tests/unit/workflows/test_graph_validation.py:**

    The Phase 110 Plan 03 test file already has a parametrized loop over the shared fixture (look for `@pytest.mark.parametrize` or similar). Adding the 5 new cases to the JSON should make them auto-pickup. After Task 02-01, those 5 new tests will be RED because the validator doesn't implement rule 4 yet.

    Additionally, add 4 explicit non-fixture rule-4 tests for edge-case coverage:

    1. `test_rule_4_handle_set_with_none_value` — condition with 2 outgoing where one has `source_handle = None` (explicitly null): set = `{"true", None}` ≠ `{"true", "false"}` → rule-4 error.
    2. `test_rule_4_handle_set_with_missing_key` — condition with 2 outgoing edges where one omits the `source_handle` key entirely: same as None → rule-4 error.
    3. `test_rule_4_condition_without_outgoing_AND_no_unreachable_collision` — assert rule 4 fires INDEPENDENTLY of rule 2 (a condition can have 0 outgoing AND trigger rule 4 even if every other node is reachable — covers the case where rule 2 might mask rule 4).
    4. `test_rule_4_with_two_conditions_emits_two_errors` — graph with two invalid condition nodes; assert TWO rule-4 errors, ordered by node appearance in graph_nodes (determinism check).

    Commit RED: `test(111-02): add failing rule-4 tests for condition outgoing degree`. Run pytest — confirm 9 RED (5 fixture cases + 4 explicit).

    **GREEN phase — extend app/workflows/graph_validation.py:**

    1. Add `_validate_rule_4_condition_outgoing_degree(graph_nodes, graph_edges) -> list[ValidationError]` at module scope (after the existing `_PermissiveConfig` block, before `validate_workflow_graph`). Google-style docstring. Implementation:

    ```python
    def _validate_rule_4_condition_outgoing_degree(
        graph_nodes: list[dict[str, Any]],
        graph_edges: list[dict[str, Any]],
    ) -> list[ValidationError]:
        """Rule 4: a condition node MUST have exactly 2 outgoing edges with
        source_handle values forming the set {'true', 'false'} (set equality).

        Args:
            graph_nodes: as in validate_workflow_graph.
            graph_edges: as in validate_workflow_graph.

        Returns:
            list of ValidationError(rule=4, node_id=condition_id, message=...)
            for each violating condition node. Empty if all conditions valid.
            Errors emitted in graph_nodes declaration order (deterministic).
        """
        errors: list[ValidationError] = []
        outgoing_by_source: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for edge in graph_edges:
            src = edge.get("source")
            if src is not None:
                outgoing_by_source[src].append(edge)
        # Iterate nodes in order (determinism)
        for node in graph_nodes:
            if node.get("kind") != "condition":
                continue
            node_id = node.get("id")
            if not node_id:
                continue
            out_edges = outgoing_by_source.get(node_id, [])
            handles = {e.get("source_handle") for e in out_edges}
            if len(out_edges) != 2 or handles != {"true", "false"}:
                errors.append(
                    ValidationError(
                        node_id=node_id,
                        rule=4,
                        message=(
                            "Condition node must have exactly 2 outgoing edges "
                            "with source_handle set to 'true' and 'false' "
                            f"(got {len(out_edges)} edges with handles "
                            f"{sorted(repr(h) for h in handles)})"
                        ),
                    )
                )
        return errors
    ```

    2. In `validate_workflow_graph()`, AFTER the existing rule 7 loop, add:
    ```python
    # --- Rule 4: condition outgoing degree ---
    errors.extend(_validate_rule_4_condition_outgoing_degree(graph_nodes, graph_edges))
    ```

    3. Update the docstring of `validate_workflow_graph` to move rule 4 OUT of "Phase 3/4 deferred" and INTO "Rules enforced (always)". Update the NotImplementedError message to ONLY mention rule 5 ("strict=True (rule 5 — parallel/merge pairing) is Phase 4 work"). Update the module-level docstring at top of file similarly (the "Phase 110 in-scope rules" / "Phase 3/4 deferred rules" sections).

    Commit GREEN: `feat(111-02): implement validation rule 4 (condition outgoing degree)`.

    Verify all tests GREEN: `.venv/Scripts/python -m pytest tests/unit/workflows/test_graph_validation.py -v --tb=short` — MUST be all-green (Phase 110's 30 + Plan 02's 9 = 39 tests).

    Also verify the existing wired call site doesn't break: `.venv/Scripts/python -m pytest tests/unit/routers/test_workflow_save_endpoint.py tests/unit/routers/test_workflow_validate_endpoint.py -v` — Phase 110's 15 + 12 = 27 tests still GREEN (rule 4 is now part of the validation that the PUT path runs unconditionally, but the existing tests don't use condition nodes so behavior shouldn't change for them).
  </behavior>
  <action>
    Follow the behavior block exactly. RED commit → run pytest (must be 9 failures from new tests + existing 30 passing) → GREEN commit → run pytest (must be 39 passing, 0 new failures).

    Ruff: `.venv/Scripts/python -m ruff check app/workflows/graph_validation.py tests/unit/workflows/test_graph_validation.py` clean.
  </action>
  <verify>
    <automated>.venv/Scripts/python -m pytest tests/unit/workflows/test_graph_validation.py -v --tb=short</automated>
    <automated>.venv/Scripts/python -m pytest tests/unit/routers/test_workflow_save_endpoint.py tests/unit/routers/test_workflow_validate_endpoint.py -v --tb=short -q</automated>
    <automated>.venv/Scripts/python -m ruff check app/workflows/graph_validation.py tests/unit/workflows/test_graph_validation.py</automated>
    <automated>grep -c "rule=4" app/workflows/graph_validation.py</automated>
    <automated>grep -c "rule 5" app/workflows/graph_validation.py</automated>
  </verify>
  <done>
    - `_validate_rule_4_condition_outgoing_degree` function exists in `app/workflows/graph_validation.py` with docstring.
    - `validate_workflow_graph` calls it unconditionally (no strict gate for rule 4).
    - NotImplementedError under `strict=True` now mentions ONLY rule 5.
    - 39 tests GREEN in `test_graph_validation.py` (30 existing + 9 new — 5 fixture-driven + 4 explicit).
    - 27 tests GREEN in `test_workflow_save_endpoint.py` + `test_workflow_validate_endpoint.py` (no regression).
    - `grep "rule=4"` returns ≥ 1 in graph_validation.py.
    - Ruff clean on both modified files.
    - Two commits on `plan-109-spec-b-phase-1`: RED test, GREEN feat.
  </done>
</task>

</tasks>

<verification>
**Plan-level checks before SUMMARY:**

1. `git branch --show-current` returns `plan-109-spec-b-phase-1`.
2. `.venv/Scripts/python -m pytest tests/unit/workflows/test_graph_validation.py -v --tb=short` — all GREEN (~39 tests).
3. `.venv/Scripts/python -m pytest tests/unit/routers/test_workflow_save_endpoint.py tests/unit/routers/test_workflow_validate_endpoint.py -v -q` — Plan 110-02 + 110-03 tests still GREEN (27 tests).
4. `python -c "import json; cases = json.load(open('tests/fixtures/graph_validation_cases.json')); print(len(cases))"` prints `13`.
5. `grep -c '"name":' tests/fixtures/graph_validation_cases.json` = 13.
6. `grep -n "Rule 5" app/workflows/graph_validation.py | head -3` shows the strict-gate-only-rule-5 update landed.
7. Sanity: load the fixture and run validate_workflow_graph against each case's input, assert expected_errors match (this is what the parametrized test does — make sure all 13 pass).
8. PUT handler unchanged: `git diff origin/main -- app/routers/workflows.py | head -20` should NOT show changes from THIS plan (Plan 110-03 already wired the call).
</verification>

<success_criteria>
- ROADMAP criterion 5 SHIPPED on the server side: `validate_workflow_graph` enforces rule 4 unconditionally; PUT save handler (Phase 110 Plan 03 wired) automatically blocks invalid condition graphs with HTTP 400 + structured errors.
- Shared fixture parity contract preserved: `tests/fixtures/graph_validation_cases.json` now has 13 cases; Plan 04 (Wave 3) will pick up all 13 in vitest and mirror server behavior client-side.
- 9 new pytest cases GREEN (5 fixture-driven + 4 explicit) verifying:
  - Zero outgoing edges → rule 4 fires
  - One outgoing edge → rule 4 fires
  - Three outgoing edges → rule 4 fires
  - Two outgoing with wrong handles → rule 4 fires
  - Two outgoing with correct handles → no rule-4 error
  - source_handle = None or missing → caught by set-equality
  - Two condition violations → two rule-4 errors in graph_nodes order (determinism)
- Rule 5 (parallel/merge pairing) still stubbed under strict=True with updated message — Phase 4 inherits a clean slate.
- 2-3 atomic commits on `plan-109-spec-b-phase-1`.
</success_criteria>

<output>
After completion, create `.planning/phases/111-workflow-node-editor-branching-execution/111-02-SUMMARY.md` mirroring Phase 110 Plan 03's SUMMARY structure.
</output>

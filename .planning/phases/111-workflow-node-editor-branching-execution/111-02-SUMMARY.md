---
phase: 111-workflow-node-editor-branching-execution
plan: 02
subsystem: api
tags: [workflow-validation, graph-validation, condition-node, jsonlogic, shared-fixture, pytest-parametrize, server-side-validation]

# Dependency graph
requires:
  - phase: 110-workflow-node-editor-editable
    provides: validate_workflow_graph() pure-functional validator with rules 1/2/3/6/7 + shared fixture (8 cases) + PUT save handler wired to validator (Plan 110-03)
provides:
  - "app/workflows/graph_validation.py - _validate_rule_4_condition_outgoing_degree helper + rule-4 enforcement unconditionally wired into validate_workflow_graph (no strict gate)"
  - "tests/fixtures/graph_validation_cases.json extended from 8 to 13 cases (5 new condition_* rule-4 cases) - canonical contract for Plan 04 client parity"
  - "10 new pytest cases in tests/unit/workflows/test_graph_validation.py (5 fixture-auto-parametrized + 5 explicit including the Warning #4 standalone zero-error assertion)"
  - "Rule 5 (parallel/merge pairing) remains stubbed under strict=True with updated NotImplementedError message that mentions ONLY rule 5"
affects: [111-04-frontend-condition-properties-editor, 111-05-frontend-graph-run-widget]

# Tech tracking
tech-stack:
  added: []  # Pure-Python extension; no new deps. Builds on Phase 110's pydantic + collections.
  patterns:
    - "Rule-extension via module-scope helper + append-at-end wiring - preserves Phase 110's existing error-order assertions (rules 1/6/2/3/7) byte-for-byte"
    - "Strict-flag narrowing - Phase 110 introduced strict=True as a Phase-3/4 NotImplementedError stub for rules 4 AND 5; Phase 111 implements rule 4 unconditionally and narrows the NotImplementedError to ONLY rule 5"
    - "Set-equality on edge.get('source_handle') - handles None, missing key, and wrong-value uniformly via dict.get(default=None) + set comparison"
    - "Belt-and-suspenders explicit test alongside parametrized fixture - test_rule_4_condition_valid_two_handles_passes loads the named fixture case directly and asserts zero rule-4 errors, surviving any future refactor of the fixture-loop machinery"

key-files:
  created: []  # No new files
  modified:
    - app/workflows/graph_validation.py
    - tests/fixtures/graph_validation_cases.json
    - tests/unit/workflows/test_graph_validation.py

key-decisions:
  - "Rule 4 always executed (no strict gate) - Phase 110 left it stubbed under strict=True NotImplementedError. Phase 111 implements unconditionally so the PUT save handler (Phase 110 Plan 03 wired) automatically enforces it on every save without router changes"
  - "Append rule 4 logic AFTER the existing rule-7 loop - preserves Phase 110's error-order in test assertions (rules emit in order 1/6/2/3/7/4)"
  - "Set-equality via edge.get('source_handle') - handles missing key, None, and wrong-string-value uniformly. Test cases test_rule_4_handle_set_with_none_value and test_rule_4_handle_set_with_missing_key verify both pathways"
  - "Iterate graph_nodes in declaration order for determinism - matches Phase 110 Plan 03's cycle-error emission pattern. test_rule_4_with_two_conditions_emits_two_errors verifies"
  - "PUT handler at app/routers/workflows.py NOT modified - Plan 110-03 already wired validate_workflow_graph() unconditionally. Rule 4 enforcement is automatic"
  - "Rule 5 (parallel/merge pairing) remains stubbed under strict=True - NotImplementedError message narrowed to mention ONLY rule 5 (was 'rules 4 + 5'). Phase 4 inherits a clean slate"

patterns-established:
  - "Append-at-end rule wiring: when extending a validator with new rules, append the call AFTER existing rules so error-order assertions in test fixtures stay stable across phases"
  - "Strict-flag narrowing across phase boundaries: Phase N+1 implementing a deferred rule narrows the NotImplementedError stub to mention only the remaining unimplemented rules"
  - "Warning #4 belt-and-suspenders pattern: parametrized fixture loop + standalone explicit named test for the valid case - the explicit test survives fixture-loop refactors and makes the contract obvious in test output"

requirements-completed: [NODEEDITOR-VALIDATE-02]

# Metrics
duration: 14min
completed: 2026-05-12
---

# Phase 111 Plan 02: Validation Rule 4 (Condition Outgoing Degree) Summary

**Pure-functional extension of validate_workflow_graph() implementing rule 4 (condition node must have exactly 2 outgoing edges with source_handle set equal to {'true', 'false'}), driven by 5 new shared-fixture cases that auto-parametrize the existing pytest loop, with the PUT save handler enforcing rule 4 automatically via Plan 110-03's existing wiring.**

## Performance

- **Duration:** ~14 min
- **Started:** 2026-05-12T00:58:00Z (approx; first read in this session)
- **Completed:** 2026-05-12T01:11:48Z
- **Tasks:** 2 (3 atomic commits: 1 fixture extension + 1 RED + 1 GREEN)
- **Files modified:** 3 (no new files)

## Accomplishments

- **Rule 4 implementation** in `app/workflows/graph_validation.py` — new `_validate_rule_4_condition_outgoing_degree(graph_nodes, graph_edges)` helper at module scope, wired into `validate_workflow_graph()` unconditionally AFTER the existing rule-7 loop. For each `condition` node: collect outgoing edges (`edge.source == node.id`), build `handles = {e.get('source_handle') for e in outgoing}`, emit `ValidationError(rule=4, node_id=condition_id, ...)` if `len != 2` OR `handles != {'true', 'false'}`. Errors emitted in graph_nodes declaration order (deterministic).

- **Shared fixture extended from 8 to 13 cases** at `tests/fixtures/graph_validation_cases.json`. The 5 new cases (preserving the existing 8 byte-for-byte): `condition_no_outgoing` (0 outgoing + unreachable o1 → rule 4 + rule 2), `condition_one_outgoing` (1 outgoing with handle 'true' → rule 4), `condition_three_outgoing` (3 outgoing with handles {'true','false','maybe'} → rule 4), `condition_wrong_source_handles` (2 outgoing with {'left','right'} → rule 4), `condition_valid_two_handles` (2 outgoing with {'true','false'} → zero errors). Plan 04 (Wave 3) will pick up all 13 in vitest.

- **10 new pytest cases** in `tests/unit/workflows/test_graph_validation.py`:
  - 5 fixture-auto-parametrized cases via the existing `@pytest.mark.parametrize("case", CASES, ids=...)` loop — no test-file changes needed for auto-pickup beyond fixture JSON additions
  - 5 explicit named tests for edge-case coverage:
    - `test_rule_4_handle_set_with_none_value` — explicit `source_handle: None` caught by set-equality
    - `test_rule_4_handle_set_with_missing_key` — omitted `source_handle` key caught (same pathway via `.get()`)
    - `test_rule_4_condition_without_outgoing_AND_no_unreachable_collision` — rule 4 fires independently of rule 2
    - `test_rule_4_with_two_conditions_emits_two_errors` — graph_nodes-order determinism check
    - `test_rule_4_condition_valid_two_handles_passes` — **explicit zero-error assertion on the valid fixture case (Warning #4 belt-and-suspenders alongside the parametrized loop)**

- **Strict-flag narrowing** — `validate_workflow_graph(strict=True)` NotImplementedError message changed from `"strict=True (rules 4 + 5) is Phase 3/4 work"` → `"strict=True (rule 5 - parallel/merge pairing) is Phase 4 work"`. Module-level and function docstrings updated accordingly: rule 4 moved INTO `Rules enforced (always)`; only rule 5 remains in the deferred section.

- **No regression** — 27 Plan 110-02/03 endpoint tests still GREEN (`test_workflow_save_endpoint.py` 15 + `test_workflow_validate_endpoint.py` 12). PUT handler at `app/routers/workflows.py:748` (Plan 110-03 wired) unchanged; rule 4 enforcement is automatic via the validator extension.

- **Total test suite:** 40 GREEN in `test_graph_validation.py` (30 existing + 5 fixture + 5 explicit). Ruff clean on both modified files.

## Task Commits

Each task was committed atomically. Task 02-02 split into RED+GREEN per TDD:

1. **Task 02-01: 5 new fixture cases** — `baa82bf9` (test)
2. **Task 02-02 RED: 5 explicit rule-4 tests** — `e39cc346` (test)
3. **Task 02-02 GREEN: rule-4 implementation + docstring/NotImplementedError narrowing** — `7b3ded83` (feat)

**Plan metadata commit:** _pending_ (final commit follows this SUMMARY.md write)

## Files Created/Modified

**Created (0 files):** none — this plan is purely an extension of Phase 110 artifacts.

**Modified (3 files):**

- `app/workflows/graph_validation.py` — Added `_validate_rule_4_condition_outgoing_degree` helper (~58 lines including docstring); added one-line call after rule-7 loop inside `validate_workflow_graph()`; updated module-level docstring (rule 4 moved from "Phase 3/4 deferred" to "Rules enforced (always)"); updated `validate_workflow_graph` docstring similarly; narrowed NotImplementedError message to mention only rule 5. (+83 lines, -12 lines net)
- `tests/fixtures/graph_validation_cases.json` — Appended 5 new cases preserving the 8 existing ones byte-for-byte. (+96 lines)
- `tests/unit/workflows/test_graph_validation.py` — Appended 5 explicit rule-4 tests under a new `# ---------- Rule 4 ----------` section. The existing parametrized fixture loop auto-picks up the 5 new JSON cases. (+125 lines)

## Decisions Made

1. **Rule 4 always executed (no strict gate).** Phase 110 left rule 4 stubbed under `strict=True` NotImplementedError. Phase 111 implements unconditionally — the PUT save handler in `app/routers/workflows.py` (Plan 110-03 wired) automatically enforces rule 4 on every save without router changes. Direct API users can no longer save condition graphs with wrong outgoing degree.

2. **Append rule 4 logic AFTER the existing rule-7 loop.** Preserves the error-order in test assertions for Phase 110's existing cases (rules emit in order 1/6/2/3/7/4). The Phase 110 fixture cases that don't touch condition nodes are byte-for-byte unchanged; their assertions on error order remain valid.

3. **Set-equality via `edge.get('source_handle')`.** Edges may carry `source_handle` as a string, `None`, or omit the key entirely. The `.get()` call returns `None` for both missing-key and explicit-null pathways, and the set comparison `handles == {'true', 'false'}` catches all three failure modes uniformly: `{'true'}`, `{'true', None}`, `{'left', 'right'}`, `{'true', 'false', 'maybe'}` all fail set-equality.

4. **Iterate graph_nodes in declaration order for determinism.** Matches Phase 110 Plan 03's cycle-error emission pattern. Without this, two-condition-violation cases could emit errors in random order depending on Python's hash randomization. `test_rule_4_with_two_conditions_emits_two_errors` verifies the ordering contract.

5. **PUT handler at `app/routers/workflows.py` NOT modified.** Plan 110-03 already wired `validate_workflow_graph()` unconditionally (between auth check and `save_template_version()`). Extending the validator means PUT automatically enforces rule 4 without router changes. The 12 Plan 110-03 validate-endpoint tests + 15 Plan 110-02 save-endpoint tests stay GREEN — no regression.

6. **Rule 5 stays stubbed under strict=True.** Phase 4 inherits a clean slate: just implement the rule 5 body and remove the NotImplementedError. The current NotImplementedError message says exactly that: `"strict=True (rule 5 - parallel/merge pairing) is Phase 4 work"`.

7. **Warning #4 belt-and-suspenders test pattern.** The plan-checker iteration 1 specifically asked for an explicit standalone test alongside the parametrized fixture loop. `test_rule_4_condition_valid_two_handles_passes` loads the `condition_valid_two_handles` fixture case by name and asserts `[e for e in errors if e.rule == 4] == []`. The parametrized loop covers the same case, but the explicit test makes the contract obvious in test output (no "test_fixture_case[condition_valid_two_handles]" indirection) and survives any future refactor of the fixture-loop machinery.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] In-tree file revert during GREEN commit race**

- **Found during:** Task 02-02 GREEN commit attempt
- **Issue:** During the initial GREEN commit attempt, I issued the commit and `git rev-parse` calls in parallel, and the first commit invocation also produced output reporting "no changes added to commit" — the `app/workflows/graph_validation.py` working-tree changes had been silently reverted before the `git add` reached the staging step. Most likely cause: a concurrent process (possibly the Plan 01 executor running in parallel on Wave 1) or a linter touched the file. This is the same class of pollution documented in `project_branch_pollution_2026_05_09.md` — the parallel automation hazard.
- **Fix:** Re-applied the four GREEN edits to `app/workflows/graph_validation.py` (module docstring, `_validate_rule_4_condition_outgoing_degree` helper, function docstring + NotImplementedError, rule-4 call after rule-7). Ran the test suite to confirm GREEN before staging. Issued `git add` and `git commit` sequentially (no parallel calls) to avoid the race.
- **Files modified:** `app/workflows/graph_validation.py` (re-applied edits)
- **Verification:** 40 tests GREEN in `test_graph_validation.py`; `git log --oneline -3` shows `7b3ded83` (GREEN) on top of `e39cc346` (RED) on top of `baa82bf9` (fixture).
- **Committed in:** `7b3ded83` (Task 02-02 GREEN)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minimal — the file-revert race was caught immediately by the post-commit `git log` check showing my GREEN commit hadn't actually landed. Re-applied the edits via sequential (non-parallel) commands and the GREEN commit went through cleanly. No data loss; no scope creep.

### Branch hygiene incidents

**Concurrent Plan 01 modifications to `pyproject.toml` and `uv.lock`.** Plan 01 was running in parallel and adding the `json-logic` dependency. Its modifications appeared as unstaged changes in my `git status` output throughout the session. I staged ONLY the files this plan owns (`tests/fixtures/graph_validation_cases.json`, `tests/unit/workflows/test_graph_validation.py`, `app/workflows/graph_validation.py`) and let Plan 01 commit its own pyproject/lockfile changes. The final `git log` shows clean interleaving: `baa82bf9` (this plan) → `e39cc346` (this plan) → `7b3ded83` (this plan) → `f7b4db4f` (Plan 01 GREEN for json-logic dep). No cross-contamination.

**Branch check before EVERY commit.** All three commits in this plan are preceded by `git branch --show-current` returning `plan-109-spec-b-phase-1`. No drift to other branches detected (which would have caused at least the 7th branch-pollution incident this session — the project memory now counts SIX prior incidents).

## Issues Encountered

**Plan 01 running in parallel on Wave 1.** Both Plan 01 and Plan 02 declared themselves Wave 1 in their PLAN frontmatter and have disjoint file ownership. Plan 01 modifies `pyproject.toml` and `uv.lock`; Plan 02 modifies `app/workflows/graph_validation.py`, `tests/fixtures/graph_validation_cases.json`, `tests/unit/workflows/test_graph_validation.py`. The only collision was the GREEN-commit race documented as the deviation above — staging discipline (never `git add .`, always staged specific files) prevented cross-contamination.

**Ruff not on PATH inside the venv.** The plan's verification script called `.venv/Scripts/python -m ruff check ...` but ruff wasn't installed in the venv. Worked around by `pip install ruff --quiet` (transient, no pyproject changes) and re-running. Same workaround captured in Phase 110's `project_workflow_node_editor_phase1.md` memory — `uv` CLI is not on PATH on this Windows workstation; transient ruff install fills the gap.

**One-off file-revert race documented as Deviation #1 above.** Not a true issue — caught and recovered cleanly via re-apply + sequential commit.

## User Setup Required

None — pure validator extension. After this plan merges to main:

1. The PUT endpoint at `PUT /workflows/templates/{template_id}` automatically enforces rule 4 on every save (returns HTTP 400 with `detail={error: 'validation_failed', errors: [{rule: 4, node_id: ..., message: 'Condition node must have...'}]}` for condition nodes with wrong outgoing degree).
2. The POST `/workflows/templates/{template_id}/validate` endpoint also surfaces rule 4 violations in its `{errors: [...]}` response.
3. Frontend Plan 04 (Wave 3) will mirror rule 4 client-side by reading the same shared fixture and implementing matching JavaScript logic.

No new env vars, no dashboard configuration, no third-party services. No migrations.

## Next Phase Readiness

**Ready for Plan 111-04** (frontend condition properties editor + client-side rule 4):

- Shared fixture at `tests/fixtures/graph_validation_cases.json` now has 13 cases (8 from Phase 110 + 5 new rule-4 cases). Plan 04's vitest suite will parametrize over the SAME file via `import fixtures from '../../../../tests/fixtures/graph_validation_cases.json'` or equivalent. Any divergence between client and server rule-4 behavior will be caught by either suite.
- Server contract documented: `ValidationError(rule=4, node_id=condition_id, message="Condition node must have exactly 2 outgoing edges with source_handle set to 'true' and 'false' ...")`. The `message_contains: "Condition"` substring assertion lets the client phrase its message naturally while still asserting the contract.
- Plan 04 must implement the same algorithm in `frontend/src/components/workflows/editor/useGraphValidation.ts`: for each `condition` node, collect outgoing edges, check `length === 2 && new Set(edges.map(e => e.source_handle)) deep-equals new Set(['true', 'false'])`. Emit a matching client-side ValidationError if not.

**Ready for Plan 111-05** (frontend WorkflowGraphRunWidget):

- No direct dependency on this plan. 111-05 consumes runtime SSE events; this plan is save-time only.

**Rule 5 (parallel/merge pairing) inherits clean slate for Phase 4.** The `validate_workflow_graph(strict=True)` NotImplementedError message now mentions ONLY rule 5: `"strict=True (rule 5 - parallel/merge pairing) is Phase 4 work"`. Phase 4 just needs to implement the rule 5 body, remove the NotImplementedError, and the strict-gate machinery is in place.

**ROADMAP criterion 5 SHIPPED on the server side.** `validate_workflow_graph` enforces rule 4 unconditionally; PUT save handler automatically blocks invalid condition graphs with HTTP 400 + structured errors. Plan 04 will close the loop client-side.

---

## Self-Check: PASSED

Verified post-write (all paths absolute):

- [x] `C:/Users/expert/documents/pka/pikar-ai/app/workflows/graph_validation.py` modified on disk — `_validate_rule_4_condition_outgoing_degree` present (grep -c "rule=4" returns 2; grep -c "rule 5" returns 2 in docstring + NotImplementedError)
- [x] `C:/Users/expert/documents/pka/pikar-ai/tests/fixtures/graph_validation_cases.json` has 13 cases (verified via Python json.load + len())
- [x] `C:/Users/expert/documents/pka/pikar-ai/tests/unit/workflows/test_graph_validation.py` has the 5 new explicit rule-4 tests (lines 435, 463, 488, 513, 533) including `test_rule_4_condition_valid_two_handles_passes` (line 533)
- [x] Commit `baa82bf9` exists on `plan-109-spec-b-phase-1` (Task 02-01: fixture extension)
- [x] Commit `e39cc346` exists on `plan-109-spec-b-phase-1` (Task 02-02 RED: 5 explicit tests)
- [x] Commit `7b3ded83` exists on `plan-109-spec-b-phase-1` (Task 02-02 GREEN: rule-4 implementation)
- [x] 40 tests GREEN in `tests/unit/workflows/test_graph_validation.py` (30 existing + 5 fixture + 5 explicit)
- [x] 27 tests GREEN in `tests/unit/routers/test_workflow_save_endpoint.py` (15) + `tests/unit/routers/test_workflow_validate_endpoint.py` (12) — no regression on Plan 110-02/03
- [x] Combined: 67 tests GREEN
- [x] `test_rule_4_condition_valid_two_handles_passes` passes (explicit zero-error assertion on the valid fixture case)
- [x] Ruff clean on `app/workflows/graph_validation.py` and `tests/unit/workflows/test_graph_validation.py`
- [x] PUT handler unchanged: `app/routers/workflows.py` import + 2 call sites of `validate_workflow_graph` (same as before Plan 02; Plan 02 does not modify the router)
- [x] Branch is `plan-109-spec-b-phase-1` after all 3 commits (verified post each commit)
- [x] No frontend code modified
- [x] No DB schema changes / migrations
- [x] No new files created

---

*Phase: 111-workflow-node-editor-branching-execution*
*Completed: 2026-05-12*

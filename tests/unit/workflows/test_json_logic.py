"""Isolated json-logic dependency sanity test (Phase 111-01).

ROADMAP criterion 6 deliverable: prove the JSONLogic library evaluates the
canonical expression {">": [{"var": "x"}, 5]} truthy against {"x": 10} and
falsy against {"x": 3}. Also pin down the operator semantics our condition
authoring UX (Plan 04 — Guided form / Advanced JSON tab) will rely on.

The PyPI package is ``json-logic-qubit`` (Python 3 fork). The upstream
``json-logic`` 0.6.3 is Python 2 only — Phase 111 plan-checker iteration 1
Info #8 verified the package name; iteration 2 (during Plan 01 execution)
discovered upstream's Python 3 incompatibility and switched to the qubit
fork, which exposes the same ``from json_logic import jsonLogic`` import.

These tests are pure-functional: no fixtures, no DB, no async.
"""

# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from __future__ import annotations

from json_logic import jsonLogic

# ---------- ROADMAP criterion 6: canonical {">":[{"var":"x"},5]} -----------


def test_basic_equality() -> None:
    """`{"==": [1, 1]}` is True; `{"==": [1, 2]}` is False."""
    assert jsonLogic({"==": [1, 1]}) is True
    assert jsonLogic({"==": [1, 2]}) is False


def test_greater_than_with_var() -> None:
    """ROADMAP criterion 6 exact deliverable.

    `{">": [{"var": "x"}, 5]}` returns True against `{"x": 10}` and
    False against `{"x": 3}`.
    """
    expression = {">": [{"var": "x"}, 5]}
    assert jsonLogic(expression, {"x": 10}) is True
    assert jsonLogic(expression, {"x": 3}) is False


def test_revenue_50000_example() -> None:
    """ROADMAP criterion 4 round-trip canonical example.

    Decision 1 UAT criterion: "if revenue > 50000 then escalate" — the
    Guided form must emit `{">": [{"var": "revenue"}, 50000]}`. Verify
    it evaluates correctly across both branches.
    """
    expression = {">": [{"var": "revenue"}, 50000]}
    assert jsonLogic(expression, {"revenue": 75000}) is True
    assert jsonLogic(expression, {"revenue": 25000}) is False


# ---------- Missing-var semantics (load-bearing for graph_executor) --------


def test_missing_var_is_falsy() -> None:
    """A missing var must NOT raise; result must be falsy.

    json_logic resolves missing vars to ``None``; comparing ``None > 0``
    yields a falsy result (TypeError caught internally OR False). This
    behavior is load-bearing for graph_executor's missing-var → 'false'
    branch routing.
    """
    result = jsonLogic({">": [{"var": "missing"}, 0]}, {})
    assert bool(result) is False


# ---------- "in" operator: array membership AND string contains -----------


def test_in_for_array_membership() -> None:
    """`{"in": [value, [array, ...]]}` is True iff value is in the array."""
    assert jsonLogic({"in": ["b", ["a", "b", "c"]]}, {}) is True
    assert jsonLogic({"in": ["x", ["a", "b"]]}, {}) is False


def test_in_for_string_contains() -> None:
    """`{"in": [substring, "fullstring"]}` is True iff substring appears.

    Plan 04 Guided→JSONLogic translator collapses both "contains" and
    "in" operators onto json-logic's single ``in`` op; the value type
    dictates the runtime semantic (array membership vs substring).
    """
    assert jsonLogic({"in": ["lo", "hello"]}, {}) is True
    assert jsonLogic({"in": ["zz", "hello"]}, {}) is False

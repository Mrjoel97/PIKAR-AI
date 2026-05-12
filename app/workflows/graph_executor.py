"""Pure-functional graph execution layer — Phase 111.

Sits alongside :mod:`app.workflows.step_executor`. The engine
(:mod:`app.workflows.engine`, Plan 03 wiring) dispatches to one or the other
based on whether the template's ``graph_nodes`` contains any non-linear
node kinds (specifically ``condition`` / ``parallel`` / ``merge`` /
``human-approval``).

This module is **purely synchronous and side-effect-free**:

  * No DB access (no database driver imports, no Supabase calls).
  * No SSE emission, no ``OutcomeWriter`` calls, no logging side effects.
  * No async I/O — ``decide_next_nodes`` is a regular sync function.

All "what runs next" decisions are made here from a synthesized in-memory
``ExecutionContext`` dict. Plan 03's engine wiring is responsible for:

  * Reading completed ``workflow_steps`` rows and synthesizing
    ``previous_outcomes`` (keyed by ``output_data._execution_meta.graph_node_id``
    per Spec B Decision 8 revision 2026-05-12 — there is NO
    ``workflow_steps.node_id`` column).
  * Calling :func:`decide_next_nodes` to compute the next graph node.
  * Inserting ``workflow_steps`` rows for the chosen node(s) and dispatching
    to ``step_executor.execute_step``.

Public surface (all importable from ``app.workflows.graph_executor``):

  * :data:`NodeKind` — typing.Literal of the 7 NodeKind variants
    (mirrors :mod:`app.workflows.graph_validation`).
  * :data:`NON_LINEAR_KINDS` — frozenset of kinds that flip dispatch on.
  * :class:`ExecutionContext` — TypedDict locking the
    ``{previous_outcomes, current_step, user_context}`` shape (ROADMAP
    criterion 7).
  * :class:`GraphExecutorError` — typed exception raised on topology /
    config violations (defense-in-depth, ROADMAP criterion 11).
  * :func:`_template_requires_graph_executor` — Discretion #5 Option A
    dispatch predicate.
  * :func:`decide_next_nodes` — main routing function.

Phase 111 in-scope kinds: ``trigger`` / ``agent-action`` / ``output``
(linear), and ``condition`` (JSONLogic-driven branching). Phase 4 will
extend this module to execute ``parallel`` / ``merge`` / ``human-approval``;
those kinds currently raise ``NotImplementedError``.
"""

# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from __future__ import annotations

from typing import Any, Literal, TypedDict

from json_logic import jsonLogic

# --- Type aliases ------------------------------------------------------------

NodeKind = Literal[
    "trigger",
    "agent-action",
    "condition",
    "parallel",
    "merge",
    "human-approval",
    "output",
]

_KNOWN_KINDS: frozenset[str] = frozenset(
    {
        "trigger",
        "agent-action",
        "condition",
        "parallel",
        "merge",
        "human-approval",
        "output",
    }
)

NON_LINEAR_KINDS: frozenset[str] = frozenset(
    {"condition", "parallel", "merge", "human-approval"}
)
"""Kinds that require the graph_executor codepath (Discretion #5 Option A).

Linear kinds (``trigger`` / ``agent-action`` / ``output``) can be executed
by the existing ``step_executor`` codepath without graph-aware routing.
"""


class ExecutionContext(TypedDict):
    """Locked execution-context shape (ROADMAP criterion 7).

    Keys:
        previous_outcomes: Mapping from completed graph node id (string UUID)
            to that node's outcome dict (typically the workflow_steps row's
            ``output_data`` JSONB column, with ``outcome_text`` and any
            tool-emitted structured fields). JSONLogic var resolution can
            walk into this via dotted paths, e.g.
            ``{"var": "previous_outcomes.<node_id>.lead_score"}``.
        current_step: Metadata about the node currently being evaluated
            (Plan 03 populates from the engine's in-flight workflow_steps
            row — exact shape is engine-defined, not graph_executor's
            concern).
        user_context: User-supplied start-time context, propagated from
            ``workflow_executions.user_context`` (Plan 03 wiring) so the
            user can write expressions like ``{"var": "tenant_tier"}``.
    """

    previous_outcomes: dict[str, Any]
    current_step: dict[str, Any]
    user_context: dict[str, Any]


class GraphExecutorError(Exception):
    """Raised when graph topology or node config violates a runtime invariant.

    Used for defense-in-depth: Plan 02's save-time validation
    (rule 4 — condition outgoing degree, rule 7 — per-kind config schemas)
    should prevent these cases from ever reaching execution, but the engine
    MUST fail loudly rather than silently no-op if a bad graph slips through
    (ROADMAP criterion 11).

    Phase 4 work (``parallel`` / ``merge`` / ``human-approval`` execution)
    is intentionally surfaced as ``NotImplementedError``, NOT as
    GraphExecutorError, so callers can distinguish "graph is invalid"
    from "this kind isn't built yet".
    """


# --- Dispatch helper ---------------------------------------------------------


def _template_requires_graph_executor(
    graph_nodes: list[dict[str, Any]],
) -> bool:
    """Return True iff this template requires the graph_executor codepath.

    Discretion #5 Option A: scan node kinds (not edge topology). Future-proof
    for Phase 4 — adding ``parallel`` / ``merge`` / ``human-approval`` to
    NON_LINEAR_KINDS automatically extends dispatch without re-engineering.

    Args:
        graph_nodes: List of node dicts as stored in
            ``workflow_template_versions.graph_nodes`` (a JSONB array of
            ``{id, kind, label, config, ...}`` dicts). Missing / unknown
            ``kind`` values are treated as linear (defensive default).

    Returns:
        True if any node has ``kind in NON_LINEAR_KINDS``. False otherwise
        (including the empty-list case — empty graphs are linear by default
        and trip the existing linear-executor path's "no steps" handling).
    """
    return any(n.get("kind") in NON_LINEAR_KINDS for n in graph_nodes)


# --- Internal helpers --------------------------------------------------------


def _find_node(
    graph_nodes: list[dict[str, Any]], node_id: str
) -> dict[str, Any] | None:
    """Linear scan for a node by id. None when not present."""
    for node in graph_nodes:
        if node.get("id") == node_id:
            return node
    return None


def _outgoing_edges(
    graph_edges: list[dict[str, Any]], source_id: str
) -> list[dict[str, Any]]:
    """Return all edges with ``source == source_id``, preserving input order."""
    return [e for e in graph_edges if e.get("source") == source_id]


def _build_merged_context(
    execution_context: ExecutionContext,
) -> dict[str, Any]:
    """Build the dict JSONLogic resolves ``{"var": "..."}`` references against.

    Precedence (rightmost wins on key collisions):
        1. ``user_context`` (start-time)
        2. ``previous_outcomes`` (completed upstream node outputs)
        3. ``current_step`` (in-flight metadata)

    Plus the three keys themselves are exposed at top level so authors can
    write either ``{"var": "score"}`` (shorthand against the merged dict) or
    ``{"var": "previous_outcomes.<node_id>.score"}`` (explicit dotted path).
    Both styles are supported; the dotted-path form is preferred for
    cross-node references and is what the Plan 04 Guided→JSONLogic
    translator emits.
    """
    merged: dict[str, Any] = {}
    merged.update(execution_context.get("user_context") or {})
    merged.update(execution_context.get("previous_outcomes") or {})
    merged.update(execution_context.get("current_step") or {})
    # Also expose the named sub-dicts so dotted-path resolution works.
    merged["previous_outcomes"] = execution_context.get(
        "previous_outcomes"
    ) or {}
    merged["current_step"] = execution_context.get("current_step") or {}
    merged["user_context"] = execution_context.get("user_context") or {}
    return merged


def _evaluate_condition(
    node: dict[str, Any], merged_context: dict[str, Any]
) -> bool:
    """Evaluate a condition node's JSONLogic expression. Return bool result.

    Raises:
        GraphExecutorError: If the node has no ``config.expression``, the
            expression is not a dict, or the JSONLogic evaluation raises
            any exception. The message includes the node id so callers
            can surface it as a workflow failure.
    """
    node_id = node.get("id", "<unknown>")
    config = node.get("config") or {}
    if not isinstance(config, dict):
        raise GraphExecutorError(
            f"Condition node {node_id}: config must be a dict, got "
            f"{type(config).__name__}"
        )
    expression = config.get("expression")
    if expression is None:
        raise GraphExecutorError(
            f"Condition node {node_id}: missing config.expression "
            f"(JSONLogic dict required for runtime evaluation)"
        )
    if not isinstance(expression, dict):
        raise GraphExecutorError(
            f"Condition node {node_id}: config.expression must be a "
            f"JSONLogic dict, got {type(expression).__name__}"
        )
    try:
        result = jsonLogic(expression, merged_context)
    except Exception as exc:
        raise GraphExecutorError(
            f"Condition node {node_id}: JSONLogic evaluation failed — "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    return bool(result)


def _route_condition(
    node: dict[str, Any],
    outgoing: list[dict[str, Any]],
    merged_context: dict[str, Any],
) -> list[str]:
    """Pick the 'true' or 'false' outgoing edge target.

    Args:
        node: The condition node dict (used only for its id in error
            messages and for the config.expression lookup).
        outgoing: Outgoing edges from this node. Must include exactly one
            edge with ``source_handle == 'true'`` AND exactly one with
            ``source_handle == 'false'``. Plan 02's validation rule 4
            enforces this at save time; this function defends at runtime.
        merged_context: Flat dict passed to JSONLogic for var resolution.

    Returns:
        Single-element list ``[target_id]`` of the chosen edge's target.

    Raises:
        GraphExecutorError: If the matching source_handle has no edge, or
            the expression is missing/malformed (delegated to
            :func:`_evaluate_condition`).
    """
    node_id = node.get("id", "<unknown>")
    result = _evaluate_condition(node, merged_context)
    target_handle = "true" if result else "false"
    matches = [
        edge for edge in outgoing if edge.get("source_handle") == target_handle
    ]
    if not matches:
        existing_handles = sorted(
            {str(e.get("source_handle")) for e in outgoing}
        )
        raise GraphExecutorError(
            f"Condition node {node_id}: no outgoing edge with "
            f"source_handle='{target_handle}' (existing handles: "
            f"{existing_handles}). Plan 02 validation rule 4 should "
            f"have rejected this graph at save time."
        )
    # Multiple matches with the same handle is also invalid (Plan 02
    # rule 4 enforces uniqueness), but if it happens we take the first
    # in input order rather than raising — this keeps the engine moving
    # in degraded scenarios. Future cleanup may tighten this.
    return [matches[0]["target"]]


# --- Main entry point --------------------------------------------------------


def decide_next_nodes(
    graph_nodes: list[dict[str, Any]],
    graph_edges: list[dict[str, Any]],
    *,
    current_node_id: str,
    execution_context: ExecutionContext,
    completed_node_ids: set[str],
) -> list[str]:
    """Return the next graph node ids to execute given current state.

    Args:
        graph_nodes: All nodes in the workflow template (from
            ``workflow_template_versions.graph_nodes``).
        graph_edges: All edges in the workflow template (from
            ``workflow_template_versions.graph_edges``).
        current_node_id: The node whose execution just completed; the
            engine asks "what runs next?"
        execution_context: Merged context dict — see :class:`ExecutionContext`.
            JSONLogic ``{"var": "..."}`` references resolve against the flat
            merge of user_context + previous_outcomes + current_step, with
            the three named sub-dicts also exposed at top level for
            dotted-path resolution.
        completed_node_ids: Set of node ids that have already finished
            executing. Currently unused for ``condition`` routing (the
            JSONLogic expression already encodes "what we depend on"), but
            Phase 4's parallel/merge logic will use it to gate merge nodes.

    Returns:
        List of next-node ids to enqueue. Empty list means "execution is
        complete from this node" (e.g. an output node with no outgoing
        edges). The engine inserts a workflow_steps row for each returned
        id and dispatches to step_executor.execute_step.

    Raises:
        GraphExecutorError: If the current node is missing from
            graph_nodes, has an unknown kind, has a malformed condition
            config, has a JSONLogic evaluation failure, or has condition
            outgoing edges with handles that don't include 'true' or
            'false' for the evaluated result. ROADMAP criterion 11.
        NotImplementedError: If the current node has kind ``parallel`` /
            ``merge`` / ``human-approval``. Phase 4 work — distinguishable
            from GraphExecutorError so callers can surface "feature not
            yet implemented" separately from "graph is invalid".
    """
    # completed_node_ids is reserved for Phase 4 merge/join logic. Keep it
    # in the public signature now so Plan 03 + Phase 4 don't have to
    # re-engineer the call site.
    _ = completed_node_ids  # intentionally unused (reserved for Phase 4)

    current = _find_node(graph_nodes, current_node_id)
    if current is None:
        raise GraphExecutorError(
            f"Current node id '{current_node_id}' not found in graph_nodes "
            f"(phantom node — engine state corruption?)"
        )

    kind = current.get("kind")
    outgoing = _outgoing_edges(graph_edges, current_node_id)

    # Linear kinds: collect all outgoing targets in input order.
    if kind in ("trigger", "agent-action", "output"):
        return [edge["target"] for edge in outgoing]

    # Condition: JSONLogic evaluation + true/false handle routing.
    if kind == "condition":
        merged = _build_merged_context(execution_context)
        return _route_condition(current, outgoing, merged)

    # Phase 4 work: parallel / merge / human-approval.
    if kind in ("parallel", "merge", "human-approval"):
        raise NotImplementedError(
            f"Phase 4: kind={kind!r} executor not yet implemented "
            f"(node {current_node_id})"
        )

    # Unknown kind — not in NodeKind set.
    raise GraphExecutorError(
        f"Unknown node kind {kind!r} for node {current_node_id} "
        f"(expected one of: {sorted(_KNOWN_KINDS)})"
    )

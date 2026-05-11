"""Server-side workflow graph validation - Phase 110.

Pure-functional validator. No DB access, no async, no IO. Called from:
  - POST /workflows/templates/{id}/validate
  - PUT /workflows/templates/{id} save handler (wired in Task 03-02)

Mirrors the client-side validator in
``frontend/src/components/workflows/editor/useGraphValidation.ts`` (Plan 04).
The two MUST stay in sync; the canonical test fixture lives at
``tests/fixtures/graph_validation_cases.json`` - both server (pytest) and
client (vitest) tests parametrize over it.

Phase 110 in-scope rules:
    1. Single trigger node with zero incoming edges
    2. Every node reachable from trigger (BFS)
    3. No cycles (Kahn's topological sort)
    6. At least one output node
    7. Per-node config passes its per-kind Pydantic schema

Phase 3/4 deferred rules (raise NotImplementedError when strict=True):
    4. Condition outgoing degree (Phase 3)
    5. Parallel/merge pairing (Phase 4)

Per-kind config schemas:
    - TriggerConfig: optional trigger_type + extras allowed
    - AgentActionConfig: required tool_name + extras allowed
    - OutputConfig: optional output_format + extras allowed
    - condition/parallel/merge/human-approval: permissive placeholder
      (Phase 3/4 will tighten these)
"""

# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Literal

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

NodeKind = Literal[
    "trigger",
    "agent-action",
    "condition",
    "parallel",
    "merge",
    "human-approval",
    "output",
]


class ValidationError(BaseModel):
    """One structural error returned by ``validate_workflow_graph``.

    ``node_id`` is ``None`` for graph-level errors (e.g. "no trigger node").
    ``rule`` is one of 1, 2, 3, 6, 7 (Phase 110 in-scope rules).
    """

    node_id: str | None
    rule: int
    message: str


# --- Per-kind config schemas -------------------------------------------------


class TriggerConfig(BaseModel):
    """Phase 110 trigger config: tight on trigger_type, permissive on extras."""

    trigger_type: Literal["manual", "schedule", "event"] | None = None
    model_config = {"extra": "allow"}


class AgentActionConfig(BaseModel):
    """Phase 110 agent-action config: tool_name is required."""

    tool_name: str
    arguments: dict[str, Any] = {}
    agent_role: str | None = None
    model_config = {"extra": "allow"}


class OutputConfig(BaseModel):
    """Phase 110 output config: optional output_format, permissive on extras."""

    output_format: str | None = None
    model_config = {"extra": "allow"}


class _PermissiveConfig(BaseModel):
    """Placeholder for condition/parallel/merge/human-approval (Phase 3/4)."""

    model_config = {"extra": "allow"}


_CONFIG_SCHEMAS: dict[str, type[BaseModel]] = {
    "trigger": TriggerConfig,
    "agent-action": AgentActionConfig,
    "output": OutputConfig,
    "condition": _PermissiveConfig,
    "parallel": _PermissiveConfig,
    "merge": _PermissiveConfig,
    "human-approval": _PermissiveConfig,
}


# --- Main entry point --------------------------------------------------------


def validate_workflow_graph(
    graph_nodes: list[dict[str, Any]],
    graph_edges: list[dict[str, Any]],
    *,
    strict: bool = False,
) -> list[ValidationError]:
    """Run Phase 110 in-scope validation rules. Return empty list if valid.

    Rules enforced (always):
        1. Single trigger node with zero incoming edges
        2. All nodes reachable from the trigger via directed BFS
        3. No cycles (Kahn's topological sort succeeds)
        6. At least one output node
        7. Each node's config passes its per-kind Pydantic schema

    Rules deferred to Phase 3/4 (raise NotImplementedError if ``strict=True``):
        4. Condition node outgoing degree (Phase 3)
        5. Parallel/merge pairing (Phase 4)

    Args:
        graph_nodes: list of node dicts with keys ``id``, ``kind``, ``label``,
            ``config`` (optional). Phase 109's seven NodeKind values are
            accepted; unknown kinds skip rule-7 silently.
        graph_edges: list of edge dicts with keys ``id``, ``source``,
            ``target`` (optional ``source_handle``, ``label``).
        strict: when True, raise NotImplementedError to surface that rules 4
            and 5 are Phase 3/4 work. Phase 110 callers pass ``strict=False``
            (the default).

    Returns:
        list of ValidationError instances. Empty when the graph is valid.
        A non-empty list MUST block save - both the POST /validate endpoint
        and the PUT save endpoint translate this into a 422/400 response.
    """
    if strict:
        raise NotImplementedError(
            "strict=True (rules 4 + 5) is Phase 3/4 work"
        )

    errors: list[ValidationError] = []

    # Build adjacency maps once - used by rules 1, 2, 3.
    incoming: defaultdict[str, list[str]] = defaultdict(list)
    outgoing: defaultdict[str, list[str]] = defaultdict(list)
    for edge in graph_edges:
        src = edge.get("source")
        tgt = edge.get("target")
        if src is None or tgt is None:
            continue
        incoming[tgt].append(src)
        outgoing[src].append(tgt)

    # --- Rule 1: exactly one trigger node with zero incoming edges ---
    triggers = [n for n in graph_nodes if n.get("kind") == "trigger"]
    if len(triggers) == 0:
        errors.append(
            ValidationError(
                node_id=None, rule=1, message="No trigger node found"
            )
        )
    elif len(triggers) > 1:
        for extra in triggers[1:]:
            errors.append(
                ValidationError(
                    node_id=extra["id"],
                    rule=1,
                    message="Multiple trigger nodes - only one is allowed",
                )
            )
    for trig in triggers:
        if incoming.get(trig["id"]):
            errors.append(
                ValidationError(
                    node_id=trig["id"],
                    rule=1,
                    message="Trigger node must have zero incoming edges",
                )
            )

    # --- Rule 6: at least one output node ---
    outputs = [n for n in graph_nodes if n.get("kind") == "output"]
    if not outputs:
        errors.append(
            ValidationError(
                node_id=None,
                rule=6,
                message="At least one output node is required",
            )
        )

    # --- Rule 2: reachability from ANY trigger via BFS ---
    # Use all triggers as BFS seeds so that an "extra trigger" (rule 1
    # violation) isn't double-flagged as unreachable.
    if triggers:
        reachable: set[str] = set()
        queue: deque[str] = deque(t["id"] for t in triggers)
        while queue:
            curr = queue.popleft()
            if curr in reachable:
                continue
            reachable.add(curr)
            for target in outgoing.get(curr, []):
                if target not in reachable:
                    queue.append(target)
        for node in graph_nodes:
            if node["id"] not in reachable:
                errors.append(
                    ValidationError(
                        node_id=node["id"],
                        rule=2,
                        message="Node unreachable from trigger",
                    )
                )

    # --- Rule 3: no cycles (Kahn's algorithm + SCC refinement) ---
    # Kahn's algorithm finds nodes that participate in any cycle OR are
    # downstream of one (any node still with positive in-degree after the
    # algorithm terminates). For user-facing error messages we only want to
    # flag nodes that ACTUALLY sit on a cycle - "downstream of cycle" should
    # not produce a rule-3 error for that node because fixing the cycle
    # automatically fixes its downstream nodes.
    in_degree: dict[str, int] = {n["id"]: 0 for n in graph_nodes}
    for edge in graph_edges:
        tgt = edge.get("target")
        if tgt in in_degree:
            in_degree[tgt] += 1
    roots: deque[str] = deque(
        nid for nid, d in in_degree.items() if d == 0
    )
    topo_visited: set[str] = set()
    while roots:
        curr = roots.popleft()
        topo_visited.add(curr)
        for target in outgoing.get(curr, []):
            if target in in_degree:
                in_degree[target] -= 1
                if in_degree[target] == 0:
                    roots.append(target)
    leftover = {n["id"] for n in graph_nodes} - topo_visited
    if leftover:
        # A leftover node is IN a cycle iff it can reach itself via outgoing
        # edges restricted to the leftover set. (A pure downstream-of-cycle
        # node cannot reach itself because it has no path back upstream.)
        in_cycle: set[str] = set()
        for start in leftover:
            if start in in_cycle:
                continue
            stack = list(outgoing.get(start, []))
            seen: set[str] = set()
            found = False
            while stack:
                node_id = stack.pop()
                if node_id == start:
                    found = True
                    break
                if node_id in seen or node_id not in leftover:
                    continue
                seen.add(node_id)
                stack.extend(outgoing.get(node_id, []))
            if found:
                in_cycle.add(start)
        # Emit cycle errors in the same order the nodes appear in graph_nodes
        # so results are deterministic across runs (set iteration order varies
        # in some Python implementations / between test sessions).
        for node in graph_nodes:
            if node["id"] in in_cycle:
                errors.append(
                    ValidationError(
                        node_id=node["id"],
                        rule=3,
                        message=(
                            "Node is part of a cycle (graph must be a DAG)"
                        ),
                    )
                )

    # --- Rule 7: per-kind config validation ---
    for node in graph_nodes:
        kind = node.get("kind")
        if kind not in _CONFIG_SCHEMAS:
            continue
        schema = _CONFIG_SCHEMAS[kind]
        config = node.get("config") or {}
        try:
            schema.model_validate(config)
        except PydanticValidationError as exc:
            err_list = exc.errors()
            # Surface the first field name in the message so it's clear which
            # key failed (rule 7 errors for agent-action commonly point at
            # tool_name).
            msg_parts: list[str] = [f"Config invalid for {kind}"]
            if err_list:
                first = err_list[0]
                loc = first.get("loc", ())
                if loc:
                    msg_parts.append(str(loc[0]))
                msg_parts.append(first.get("msg", ""))
            errors.append(
                ValidationError(
                    node_id=node["id"],
                    rule=7,
                    message=": ".join(p for p in msg_parts if p),
                )
            )

    return errors

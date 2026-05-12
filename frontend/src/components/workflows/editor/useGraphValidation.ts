// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview Client-side workflow graph validator — Phase 110 Plan 04.
 *
 * Pure-functional validator mirroring ``app/workflows/graph_validation.py``
 * (Plan 03) line-by-line. Both sides MUST stay in sync; parity is enforced
 * by the shared canonical fixture at ``tests/fixtures/graph_validation_cases.json``
 * which both pytest and vitest parametrize over (B-4 contract).
 *
 * Rules enforced (always):
 *   1. Single trigger node with zero incoming edges
 *   2. Every node reachable from trigger (BFS)
 *   3. No cycles (Kahn's algorithm + SCC refinement)
 *   4. Condition outgoing degree (Phase 111 Plan 04 — mirrors Plan 02's
 *      server-side `_validate_rule_4_condition_outgoing_degree` byte-for-byte
 *      via the shared fixture)
 *   6. At least one output node
 *   7. Each node's config passes its per-kind Zod schema
 *
 * Rule 5 (parallel/merge pairing) is still Phase 4 work — not enforced here.
 */

import type {
    GraphNode,
    GraphEdge,
    NodeKind,
    ValidationError,
} from '@/services/workflows';
import { validateNodeConfig } from './useGraphSchema';

/**
 * Run Phase 110 in-scope validation rules. Returns empty list when valid.
 *
 * Output is deterministic across runs: nodes are walked in their
 * ``graph_nodes`` order, not in hash order. This matches the server's
 * ordering so the shared fixture's per-case ``expected_errors`` array
 * passes both pytest and vitest assertions byte-for-byte.
 */
export function validateGraph(
    graph_nodes: GraphNode[],
    graph_edges: GraphEdge[],
): ValidationError[] {
    const errors: ValidationError[] = [];

    // Build adjacency maps once — used by rules 1, 2, 3.
    const incoming = new Map<string, string[]>();
    const outgoing = new Map<string, string[]>();
    for (const edge of graph_edges) {
        const src = edge.source;
        const tgt = edge.target;
        if (src == null || tgt == null) continue;
        if (!incoming.has(tgt)) incoming.set(tgt, []);
        incoming.get(tgt)!.push(src);
        if (!outgoing.has(src)) outgoing.set(src, []);
        outgoing.get(src)!.push(tgt);
    }

    // --- Rule 1: exactly one trigger node with zero incoming edges ---
    const triggers = graph_nodes.filter((n) => n.kind === 'trigger');
    if (triggers.length === 0) {
        errors.push({
            node_id: null,
            rule: 1,
            message: 'No trigger node found',
        });
    } else if (triggers.length > 1) {
        for (const extra of triggers.slice(1)) {
            errors.push({
                node_id: extra.id,
                rule: 1,
                message: 'Multiple trigger nodes - only one is allowed',
            });
        }
    }
    for (const trig of triggers) {
        if ((incoming.get(trig.id) ?? []).length > 0) {
            errors.push({
                node_id: trig.id,
                rule: 1,
                message: 'Trigger node must have zero incoming edges',
            });
        }
    }

    // --- Rule 6: at least one output node ---
    const outputs = graph_nodes.filter((n) => n.kind === 'output');
    if (outputs.length === 0) {
        errors.push({
            node_id: null,
            rule: 6,
            message: 'At least one output node is required',
        });
    }

    // --- Rule 2: reachability from ANY trigger via BFS ---
    // Seed from all triggers so an extra trigger (rule 1) doesn't double-flag
    // as unreachable.
    if (triggers.length > 0) {
        const reachable = new Set<string>();
        const queue: string[] = triggers.map((t) => t.id);
        while (queue.length > 0) {
            const curr = queue.shift()!;
            if (reachable.has(curr)) continue;
            reachable.add(curr);
            for (const target of outgoing.get(curr) ?? []) {
                if (!reachable.has(target)) {
                    queue.push(target);
                }
            }
        }
        for (const node of graph_nodes) {
            if (!reachable.has(node.id)) {
                errors.push({
                    node_id: node.id,
                    rule: 2,
                    message: 'Node unreachable from trigger',
                });
            }
        }
    }

    // --- Rule 3: no cycles (Kahn's algorithm + SCC refinement) ---
    // Same algorithm as graph_validation.py. Naive Kahn leftover flags both
    // cycle members AND downstream-of-cycle nodes; we restrict the second
    // pass to leftover nodes and check self-reachability to identify only
    // the true cycle members.
    const inDegree = new Map<string, number>();
    for (const n of graph_nodes) inDegree.set(n.id, 0);
    for (const edge of graph_edges) {
        if (inDegree.has(edge.target)) {
            inDegree.set(edge.target, (inDegree.get(edge.target) ?? 0) + 1);
        }
    }
    const roots: string[] = [];
    for (const [nid, d] of inDegree.entries()) {
        if (d === 0) roots.push(nid);
    }
    const topoVisited = new Set<string>();
    while (roots.length > 0) {
        const curr = roots.shift()!;
        topoVisited.add(curr);
        for (const target of outgoing.get(curr) ?? []) {
            if (inDegree.has(target)) {
                inDegree.set(target, inDegree.get(target)! - 1);
                if (inDegree.get(target) === 0) {
                    roots.push(target);
                }
            }
        }
    }
    const leftover = new Set<string>();
    for (const n of graph_nodes) {
        if (!topoVisited.has(n.id)) leftover.add(n.id);
    }
    if (leftover.size > 0) {
        const inCycle = new Set<string>();
        for (const start of leftover) {
            if (inCycle.has(start)) continue;
            // DFS through outgoing edges restricted to the leftover set —
            // if we can reach `start` from `start`, it's in a cycle.
            const stack: string[] = [...(outgoing.get(start) ?? [])];
            const seen = new Set<string>();
            let found = false;
            while (stack.length > 0) {
                const nodeId = stack.pop()!;
                if (nodeId === start) {
                    found = true;
                    break;
                }
                if (seen.has(nodeId) || !leftover.has(nodeId)) continue;
                seen.add(nodeId);
                stack.push(...(outgoing.get(nodeId) ?? []));
            }
            if (found) inCycle.add(start);
        }
        // Emit in graph_nodes order for determinism (set iteration is
        // implementation-defined; we must match the server's emission order).
        for (const node of graph_nodes) {
            if (inCycle.has(node.id)) {
                errors.push({
                    node_id: node.id,
                    rule: 3,
                    message: 'Node is part of a cycle (graph must be a DAG)',
                });
            }
        }
    }

    // --- Rule 7: per-kind config validation ---
    for (const node of graph_nodes) {
        const kind = node.kind as NodeKind;
        const result = validateNodeConfig(kind, node.config ?? {});
        if (!result.success) {
            // Surface the first failing field name so the message matches
            // the server's "Config invalid for {kind}: {field}: {msg}" shape.
            const firstIssue = result.error.issues[0];
            const parts: string[] = [`Config invalid for ${kind}`];
            if (firstIssue) {
                const loc = firstIssue.path?.[0];
                if (loc != null) parts.push(String(loc));
                parts.push(firstIssue.message ?? '');
            }
            errors.push({
                node_id: node.id,
                rule: 7,
                message: parts.filter((p) => p && p.length > 0).join(': '),
            });
        }
    }

    // --- Rule 4: condition outgoing degree (Phase 111 Plan 04) ---
    // Appended AFTER rule 7 so the existing Phase 110 rule-emission order
    // (1/6/2/3/7) stays byte-for-byte stable. Mirrors the server's
    // `_validate_rule_4_condition_outgoing_degree` algorithm in
    // app/workflows/graph_validation.py: for each condition node, collect
    // outgoing edges and check `length === 2 && handles == {'true', 'false'}`.
    errors.push(...validateRule4(graph_nodes, graph_edges));

    return errors;
}

/**
 * Rule 4: a `condition` node MUST have exactly 2 outgoing edges with
 * `source_handle` values forming the set {'true', 'false'}.
 *
 * Mirrors `app/workflows/graph_validation.py:_validate_rule_4_condition_outgoing_degree`
 * byte-for-byte. The shared fixture `tests/fixtures/graph_validation_cases.json`
 * (Plan 02 extended to 13 cases) parametrizes both pytest and vitest — any
 * divergence is caught by one of the two suites.
 *
 * Iterates `graph_nodes` in declaration order for determinism (matches
 * server-side ordering so the fixture's per-case `expected_errors` array
 * passes both runners byte-for-byte).
 */
function validateRule4(
    graph_nodes: GraphNode[],
    graph_edges: GraphEdge[],
): ValidationError[] {
    const errors: ValidationError[] = [];

    // Bucket outgoing edges by source for O(1) lookup per condition node.
    // Note: edges without a source are silently ignored (rule 1 / rule 2
    // catch malformed graphs elsewhere).
    const outgoingBySource = new Map<string, GraphEdge[]>();
    for (const edge of graph_edges) {
        if (edge.source == null) continue;
        const arr = outgoingBySource.get(edge.source);
        if (arr) {
            arr.push(edge);
        } else {
            outgoingBySource.set(edge.source, [edge]);
        }
    }

    for (const node of graph_nodes) {
        if (node.kind !== 'condition') continue;
        const outEdges = outgoingBySource.get(node.id) ?? [];
        // Mirror server's `set(e.get('source_handle') for e in outgoing)`.
        // Missing key, null, and explicit string-value all flow through
        // uniformly via `?? null`. Set-equality with {'true', 'false'}
        // catches:
        //   - wrong count (0, 1, 3+ outgoing)
        //   - wrong handles ({'left', 'right'}, {'true', null}, etc.)
        //   - duplicate handles ({'true', 'true'} → size 1 != 2)
        const handles = new Set<string | null>();
        for (const e of outEdges) {
            handles.add(e.source_handle ?? null);
        }
        const isValid =
            outEdges.length === 2 &&
            handles.size === 2 &&
            handles.has('true') &&
            handles.has('false');

        if (!isValid) {
            // Build a stable, sortable handle representation for the message
            // so identical inputs produce identical strings across runs.
            const handlesList = [...handles]
                .map((h) => (h === null ? 'null' : JSON.stringify(h)))
                .sort()
                .join(', ');
            errors.push({
                node_id: node.id,
                rule: 4,
                message:
                    `Condition node must have exactly 2 outgoing edges ` +
                    `with source_handle set to 'true' and 'false' ` +
                    `(got ${outEdges.length} edges with handles [${handlesList}])`,
            });
        }
    }

    return errors;
}

/**
 * Convenience: bucket validation errors by ``node_id``. Useful when
 * rendering red badges on custom React Flow node components — each node
 * component reads ``data.validationErrors`` (filtered to its own id).
 *
 * Graph-level errors (``node_id: null``) are returned under the empty
 * string key so callers can render them separately.
 */
export function bucketErrorsByNode(
    errors: ValidationError[],
): Map<string, ValidationError[]> {
    const result = new Map<string, ValidationError[]>();
    for (const e of errors) {
        const key = e.node_id ?? '';
        if (!result.has(key)) result.set(key, []);
        result.get(key)!.push(e);
    }
    return result;
}

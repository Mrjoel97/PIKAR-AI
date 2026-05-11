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
 * Phase 110 in-scope rules:
 *   1. Single trigger node with zero incoming edges
 *   2. Every node reachable from trigger (BFS)
 *   3. No cycles (Kahn's algorithm + SCC refinement)
 *   6. At least one output node
 *   7. Each node's config passes its per-kind Zod schema
 *
 * Rules 4 (condition outgoing degree) and 5 (parallel/merge pairing) are
 * Phase 3/4 work — not enforced here.
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

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview Helpers that map workflow-run state to visual styles.
 *
 * Phase 111 Plan 05 — Discretion #7 (active-node visual treatment).
 *
 * Two pure helpers:
 *   - `getNodeRunStateClasses(runState)` returns a Tailwind classname
 *     string for the outermost wrapper of each node component. The 7 node
 *     components (TriggerNode, AgentActionNode, OutputNode, ConditionNode,
 *     ParallelNode, MergeNode, HumanApprovalNode) append this to their
 *     existing className when `data.runState` is set. Editor (Phase 110)
 *     never sets `data.runState`, so existing visuals are unchanged.
 *   - `getEdgeRunStateStyle(runState)` returns a React Flow Edge `style`
 *     object. Used by WorkflowGraphRunWidget (Task 05-03) to mark the edge
 *     taken by a condition node (emerald + thicker) and mute the other
 *     edge (slate + opacity 0.3 + dashed).
 *
 * Why module-scoped, pure functions?
 *   - The 7 node components each compose their existing wrapper className
 *     with this helper's output. A switch-on-runState in a shared module
 *     means the visual contract lives in ONE place; per-file edits are
 *     mechanical 2-line additions (import + appended class).
 *   - Edge styles are also passed inline on each React Flow `Edge` object
 *     in the widget's `useMemo`. The widget computes a `RunStateMap.edges`
 *     keyed by edge id and applies this helper per edge.
 */

/** All run-state values a node can be in during workflow execution. */
export type NodeRunState =
    | 'pending'
    | 'active'
    | 'completed'
    | 'skipped'
    | 'failed';

/** All run-state values an edge can be in during workflow execution. */
export type EdgeRunState = 'pending' | 'taken' | 'not_taken';

/**
 * Maps a node's live `runState` to a Tailwind className string for the
 * outermost wrapper element of each node component.
 *
 * Discretion #7: active nodes use `animate-pulse` + `ring-2 ring-amber-500`
 * to draw the eye to whatever the engine is currently executing. Completed
 * nodes get a subtle `ring-1 ring-emerald-500`. Pending (not-yet-executed)
 * nodes are muted via `opacity-50`. Skipped nodes (e.g. the not-taken
 * branch of a condition) drop to `opacity-30 grayscale`. Failed nodes get
 * a prominent `ring-2 ring-red-500`.
 *
 * Returns the empty string for `undefined` so node components in the editor
 * (which never set runState) keep their existing visuals.
 */
export function getNodeRunStateClasses(
    runState: NodeRunState | undefined,
): string {
    switch (runState) {
        case 'active':
            return 'animate-pulse ring-2 ring-amber-500';
        case 'completed':
            return 'ring-1 ring-emerald-500';
        case 'pending':
            return 'opacity-50';
        case 'skipped':
            return 'opacity-30 grayscale';
        case 'failed':
            return 'ring-2 ring-red-500';
        default:
            return '';
    }
}

/**
 * React Flow Edge `style` properties for the taken / not-taken / pending
 * edge visual treatment. Pending and undefined return an empty object
 * (React Flow falls back to its default edge styling).
 *
 * `taken` = bright emerald (#10b981) + thicker stroke. Drawn from a
 * condition node to the branch the engine actually executed.
 *
 * `not_taken` = slate (#94a3b8) + opacity 0.3 + dashed strokeDasharray.
 * Marks the other outgoing edge from a condition node — visible but
 * clearly de-emphasized.
 */
export function getEdgeRunStateStyle(
    runState: EdgeRunState | undefined,
): {
    stroke?: string;
    strokeWidth?: number;
    opacity?: number;
    strokeDasharray?: string;
} {
    switch (runState) {
        case 'taken':
            return { stroke: '#10b981', strokeWidth: 2.5 };
        case 'not_taken':
            return {
                stroke: '#94a3b8',
                opacity: 0.3,
                strokeDasharray: '6,4',
            };
        case 'pending':
        default:
            return {};
    }
}

'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview Right-rail node properties drawer for the workflow editor.
 *
 * Phase 110 Plan 04 + Phase 111 Plan 04. Renders a per-kind editable form
 * for the selected node. Calls onUpdate(id, updates) on every change,
 * lifting state up to the editor page. Per Claude's Discretion #2 from
 * 110-CONTEXT.md + CONTEXT.md decision 1:
 *
 *   - trigger / agent-action / output: real editable fields
 *   - condition (Phase 111 Plan 04): full dual-tab ConditionPropertiesEditor
 *     (Guided form + Advanced JSONLogic editor via CodeMirror 6)
 *   - parallel / merge / human-approval: placeholder body
 *     ("Coming in Phase 4 — node saves but won't execute yet")
 *
 * Uses raw <input> + useState + Zod safeParse on change (no react-hook-form
 * per the same decision — simpler, fewer deps, matches existing patterns).
 */

import React, { useCallback, useMemo } from 'react';

import { X } from 'lucide-react';

import type { GraphNode, GraphEdge } from '@/services/workflows';
import { NODE_OUTPUT_KEYS, validateNodeConfig } from './useGraphSchema';
import { ConditionPropertiesEditor } from './ConditionPropertiesEditor';

interface Props {
    node: GraphNode | null;
    onUpdate: (id: string, updates: Partial<GraphNode>) => void;
    onClose: () => void;
    /**
     * Optional full graph context — required for the
     * ConditionPropertiesEditor field selector (Phase 111 Plan 04). The
     * drawer walks the upstream subgraph from the selected condition node
     * and emits `previous_outcomes.{node_id}.{output_key}` options.
     *
     * Defaults to empty arrays for backward-compat with Phase 110 callers
     * that didn't pass graph context. In that case the condition editor's
     * field selector only exposes the "Custom field…" sentinel.
     */
    nodes?: GraphNode[];
    edges?: GraphEdge[];
}

// Phase 111 Plan 04: condition kind is no longer a placeholder — it now
// renders ConditionPropertiesEditor. Only parallel/merge/human-approval
// remain Phase 4 placeholders.
const PHASE_4_KINDS = new Set(['parallel', 'merge', 'human-approval']);

/**
 * Walk the upstream subgraph from `nodeId` and return the union of
 * `previous_outcomes.{upstream_id}.{output_key}` options for the Field
 * selector. Static per-kind output keys come from
 * `useGraphSchema.NODE_OUTPUT_KEYS` (Discretion #4 Option A).
 */
function computeUpstreamFields(
    nodes: GraphNode[],
    edges: GraphEdge[],
    nodeId: string,
): string[] {
    // Build target → sources map for backward BFS.
    const incoming = new Map<string, string[]>();
    for (const e of edges) {
        if (!e.source || !e.target) continue;
        const arr = incoming.get(e.target);
        if (arr) arr.push(e.source);
        else incoming.set(e.target, [e.source]);
    }

    // BFS backward from nodeId, collecting upstream node ids.
    const visited = new Set<string>();
    const upstreamIds: string[] = [];
    const queue: string[] = [nodeId];
    while (queue.length > 0) {
        const curr = queue.shift()!;
        for (const src of incoming.get(curr) ?? []) {
            if (visited.has(src)) continue;
            visited.add(src);
            upstreamIds.push(src);
            queue.push(src);
        }
    }

    // Look up each upstream node, emit `previous_outcomes.{id}.{key}` for
    // each static output key declared by its kind.
    const fields: string[] = [];
    const nodesById = new Map(nodes.map((n) => [n.id, n]));
    for (const upId of upstreamIds) {
        const upNode = nodesById.get(upId);
        if (!upNode) continue;
        const keys = NODE_OUTPUT_KEYS[upNode.kind] ?? [];
        for (const k of keys) {
            fields.push(`previous_outcomes.${upId}.${k}`);
        }
    }
    return fields;
}

export function NodePropertiesDrawer({
    node,
    onUpdate,
    onClose,
    nodes = [],
    edges = [],
}: Props) {
    if (!node) {
        return (
            <aside
                className="w-80 shrink-0 overflow-y-auto border-l border-slate-200 bg-white p-4"
                data-testid="properties-drawer"
                aria-label="Node properties"
            >
                <p className="text-sm text-slate-500">
                    Select a node to edit its properties.
                </p>
            </aside>
        );
    }

    const handleLabelChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        onUpdate(node.id, { label: e.target.value });
    };

    const updateConfigKey = useCallback(
        (key: string, value: unknown) => {
            const baseConfig =
                node.config && typeof node.config === 'object'
                    ? (node.config as Record<string, unknown>)
                    : {};
            const newConfig = { ...baseConfig, [key]: value };
            onUpdate(node.id, { config: newConfig });
        },
        [node.id, node.config, onUpdate],
    );

    const configValidation = validateNodeConfig(
        node.kind,
        node.config ?? {},
    );
    const configError = !configValidation.success
        ? configValidation.error.issues[0]
        : null;
    const errorMessage = configError
        ? `${String(configError.path?.[0] ?? 'config')}: ${configError.message}`
        : null;

    // Phase 111 Plan 04: condition kind gets its own dual-tab editor.
    // The ConditionPropertiesEditor handles its own label input and config
    // mutations — the standard drawer body is bypassed entirely.
    const upstreamFields = useMemo(
        () =>
            node.kind === 'condition'
                ? computeUpstreamFields(nodes, edges, node.id)
                : [],
        [node.kind, node.id, nodes, edges],
    );

    if (node.kind === 'condition') {
        return (
            <aside
                className="w-80 shrink-0 overflow-y-auto border-l border-slate-200 bg-white p-4"
                data-testid="properties-drawer"
                aria-label="Node properties"
            >
                <div className="mb-3 flex items-center justify-between">
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                        {node.kind}
                    </p>
                    <button
                        type="button"
                        onClick={onClose}
                        className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                        aria-label="Close properties drawer"
                        data-testid="drawer-close"
                    >
                        <X className="h-4 w-4" aria-hidden="true" />
                    </button>
                </div>
                <ConditionPropertiesEditor
                    node={{
                        id: node.id,
                        kind: 'condition',
                        label: node.label,
                        config:
                            (node.config as { expression?: unknown } | null) ??
                            {},
                    }}
                    upstreamFields={upstreamFields}
                    onChange={(next) => {
                        const updates: Partial<GraphNode> = {};
                        if (next.label !== undefined) updates.label = next.label;
                        if (next.config !== undefined) {
                            const baseConfig =
                                node.config && typeof node.config === 'object'
                                    ? (node.config as Record<string, unknown>)
                                    : {};
                            updates.config = {
                                ...baseConfig,
                                ...next.config,
                            };
                        }
                        if (Object.keys(updates).length > 0) {
                            onUpdate(node.id, updates);
                        }
                    }}
                />
            </aside>
        );
    }

    return (
        <aside
            className="w-80 shrink-0 overflow-y-auto border-l border-slate-200 bg-white p-4"
            data-testid="properties-drawer"
            aria-label="Node properties"
        >
            <div className="mb-3 flex items-center justify-between">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                    {node.kind}
                </p>
                <button
                    type="button"
                    onClick={onClose}
                    className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                    aria-label="Close properties drawer"
                    data-testid="drawer-close"
                >
                    <X className="h-4 w-4" aria-hidden="true" />
                </button>
            </div>

            <div className="space-y-3">
                <div>
                    <label
                        htmlFor={`drawer-label-${node.id}`}
                        className="mb-1 block text-xs font-medium text-slate-600"
                    >
                        Label
                    </label>
                    <input
                        id={`drawer-label-${node.id}`}
                        type="text"
                        value={node.label}
                        onChange={handleLabelChange}
                        className="w-full rounded-md border border-slate-200 px-2.5 py-1.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
                        data-testid="drawer-label-input"
                    />
                </div>

                {node.kind === 'trigger' && (
                    <div>
                        <label
                            htmlFor={`drawer-trigger-type-${node.id}`}
                            className="mb-1 block text-xs font-medium text-slate-600"
                        >
                            Trigger type
                        </label>
                        <select
                            id={`drawer-trigger-type-${node.id}`}
                            value={
                                (node.config as Record<string, unknown> | null)
                                    ?.trigger_type as string | undefined ??
                                ''
                            }
                            onChange={(e) =>
                                updateConfigKey(
                                    'trigger_type',
                                    e.target.value || undefined,
                                )
                            }
                            className="w-full rounded-md border border-slate-200 px-2.5 py-1.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
                            data-testid="drawer-trigger-type-select"
                        >
                            <option value="">— select —</option>
                            <option value="manual">Manual</option>
                            <option value="schedule">Schedule</option>
                            <option value="event">Event</option>
                        </select>
                    </div>
                )}

                {node.kind === 'agent-action' && (
                    <>
                        <div>
                            <label
                                htmlFor={`drawer-tool-${node.id}`}
                                className="mb-1 block text-xs font-medium text-slate-600"
                            >
                                Tool name
                                <span className="ml-1 text-red-500">*</span>
                            </label>
                            <input
                                id={`drawer-tool-${node.id}`}
                                type="text"
                                value={
                                    ((node.config as Record<string, unknown> | null)
                                        ?.tool_name as string | undefined) ??
                                    ''
                                }
                                onChange={(e) =>
                                    updateConfigKey('tool_name', e.target.value)
                                }
                                placeholder="e.g. send_gmail"
                                className="w-full rounded-md border border-slate-200 px-2.5 py-1.5 font-mono text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
                                data-testid="drawer-tool-name-input"
                            />
                        </div>
                        <div>
                            <label
                                htmlFor={`drawer-agent-role-${node.id}`}
                                className="mb-1 block text-xs font-medium text-slate-600"
                            >
                                Agent role (optional)
                            </label>
                            <input
                                id={`drawer-agent-role-${node.id}`}
                                type="text"
                                value={
                                    ((node.config as Record<string, unknown> | null)
                                        ?.agent_role as string | undefined) ??
                                    ''
                                }
                                onChange={(e) =>
                                    updateConfigKey(
                                        'agent_role',
                                        e.target.value || undefined,
                                    )
                                }
                                placeholder="e.g. marketing"
                                className="w-full rounded-md border border-slate-200 px-2.5 py-1.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
                                data-testid="drawer-agent-role-input"
                            />
                        </div>
                    </>
                )}

                {node.kind === 'output' && (
                    <p className="text-xs text-slate-500">
                        Output nodes emit the final workflow result. No
                        additional config is required.
                    </p>
                )}

                {PHASE_4_KINDS.has(node.kind) && (
                    <div
                        className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800"
                        data-testid="drawer-phase-placeholder"
                    >
                        <p className="font-medium">
                            Coming in Phase 4
                        </p>
                        <p className="mt-1 leading-relaxed">
                            This node saves but won&rsquo;t execute yet. The
                            workflow engine will ignore it until Phase 4
                            adds parallel / merge / human-approval execution.
                        </p>
                    </div>
                )}

                {errorMessage && (
                    <div
                        className="rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-700"
                        data-testid="drawer-config-error"
                        role="alert"
                    >
                        {errorMessage}
                    </div>
                )}
            </div>
        </aside>
    );
}

export default NodePropertiesDrawer;

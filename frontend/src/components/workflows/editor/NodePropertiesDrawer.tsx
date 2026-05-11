'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview Right-rail node properties drawer for the workflow editor.
 *
 * Phase 110 Plan 04. Renders a per-kind editable form for the selected
 * node. Calls onUpdate(id, updates) on every change, lifting state up to
 * the editor page. Per Claude's Discretion #2 from 110-CONTEXT.md:
 *
 *   - trigger / agent-action / output: real editable fields
 *   - condition / parallel / merge / human-approval: placeholder body
 *     ("Coming in Phase 3/4 — node saves but won't execute yet")
 *
 * Uses raw <input> + useState + Zod safeParse on change (no react-hook-form
 * per the same decision — simpler, fewer deps, matches existing patterns).
 */

import React, { useCallback } from 'react';

import { X } from 'lucide-react';

import type { GraphNode } from '@/services/workflows';
import { validateNodeConfig } from './useGraphSchema';

interface Props {
    node: GraphNode | null;
    onUpdate: (id: string, updates: Partial<GraphNode>) => void;
    onClose: () => void;
}

const PHASE_3_4_KINDS = new Set([
    'condition',
    'parallel',
    'merge',
    'human-approval',
]);

export function NodePropertiesDrawer({ node, onUpdate, onClose }: Props) {
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
        ? `${configError.path?.[0] ?? 'config'}: ${configError.message}`
        : null;

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

                {PHASE_3_4_KINDS.has(node.kind) && (
                    <div
                        className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800"
                        data-testid="drawer-phase-placeholder"
                    >
                        <p className="font-medium">
                            Coming in Phase 3/4
                        </p>
                        <p className="mt-1 leading-relaxed">
                            This node saves but won&rsquo;t execute yet. The
                            workflow engine will ignore it until Phase 3/4
                            adds branching / parallel / merge / human-approval
                            execution.
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
